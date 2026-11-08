#!/usr/bin/env python3
"""Check imported source values, graph consistency, vector coverage and real retrieval."""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings
from app.core.neo4j_config import neo4j_db
from app.services.cordis_det import parse_det_json
from app.services.data.cordis_repository import CordisProjectRepository
from app.services.project_coverage import project_database_coverage
from app.services.tools.partner_discovery import PartnerDiscoveryTool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export")
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-task-id", type=int, help="Optional CORDIS task ID for provenance")
    args = parser.parse_args()
    if args.source_task_id is not None and args.source_task_id <= 0:
        parser.error("source-task-id must be positive")
    source, org_source = parse_det_json(args.export)
    with (
        psycopg2.connect(settings.database_url) as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cur,
    ):
        cur.execute('SELECT * FROM projects WHERE "frameworkProgramme"=%s', ("HORIZON",))
        projects = {p["id"]: dict(p) for p in cur.fetchall()}
        cur.execute(
            'SELECT o.* FROM organizations o JOIN projects p ON p.id=o."projectID" WHERE p."frameworkProgramme"=%s',
            ("HORIZON",),
        )
        organizations = cur.fetchall()
        cur.execute(
            """SELECT count(*) AS eligible,
            count(*) FILTER(WHERE e.embedding_status='completed' AND e.combined_embedding IS NOT NULL AND vector_dims(e.combined_embedding)=%s) AS embedded
            FROM projects p LEFT JOIN project_embeddings e ON e.project_id=p.id
            WHERE length(p.title)>10 AND length(p.objective)>50""",
            (settings.embedding_dimension,),
        )
        embeddings = dict(cur.fetchone())
    older, accepted, problems = 0, set(), []
    for expected in source:
        current = projects.get(expected["id"])
        if current is None:
            problems.append({"missing_project": expected["id"]})
            continue
        if current["contentUpdateDate"] > expected["contentUpdateDate"]:
            older += 1
            continue
        # A newer consortium can cause the whole incoming project to be skipped.
        if any(current.get(k) != v for k, v in expected.items()):
            problems.append({"project_source_mismatch": expected["id"]})
            continue
        accepted.add(expected["id"])

    def org_key(o):
        return tuple(o.get(k) for k in ("projectID", "organisationID", "role", "order"))

    expected_orgs = {org_key(o): o for o in org_source if o["projectID"] in accepted}
    actual_orgs = {org_key(o): o for o in organizations if o["projectID"] in accepted}
    if expected_orgs.keys() != actual_orgs.keys():
        problems.append("consortium source identities differ")
    for key, expected in expected_orgs.items():
        actual = actual_orgs.get(key)
        if actual is not None and any(actual.get(k) != v for k, v in expected.items()):
            problems.append({"consortium_source_mismatch": key})
    graph_ids = {
        int(p["id"])
        for p in neo4j_db.execute_query(
            'MATCH (p:Project) WHERE p.frameworkProgramme="HORIZON" RETURN p.id AS id'
        )
    }
    graph_pairs = {
        (int(r["pid"]), r["oid"])
        for r in neo4j_db.execute_query(
            'MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project) WHERE p.frameworkProgramme="HORIZON" RETURN p.id AS pid,o.id AS oid'
        )
    }
    pg_pairs = {(r["projectID"], r["organisationID"]) for r in organizations}
    if graph_ids != set(projects):
        problems.append("PostgreSQL and Neo4j project IDs differ")
    if graph_pairs != pg_pairs:
        problems.append("PostgreSQL and Neo4j consortium pairs differ")
    repository = CordisProjectRepository()
    try:
        # Choose a project from this export rather than a previous refresh's ID.
        example_id = max(source, key=lambda row: (row["contentUpdateDate"], row["id"]))["id"]
        example = repository.get_project_by_id(str(example_id))
        keyword, total = repository.search_projects(
            ["artificial", "intelligence", "healthcare"], {"programme": "HORIZON"}, limit=3
        )
        if example is None:
            problems.append("new project not found by production repository")
        if not keyword:
            problems.append("keyword retrieval returned no examples")
        retrieval = {
            "new_project": example.to_dict() if example else None,
            "keyword_total": total,
            "keyword_project_ids": [p.id for p in keyword],
        }
    finally:
        repository.close()
    partners = PartnerDiscoveryTool().find_partners(
        "artificial intelligence healthcare",
        country="NL",
        min_projects=1,
        limit=3,
        include_2hop=False,
        programme="HORIZON",
    )
    retrieval["partner_result_keys"] = list(partners)
    retrieval["partner_count"] = len(partners.get("experienced_partners", []))
    from app.services.local_project_search_service import LocalProjectSearchService

    search = LocalProjectSearchService()
    try:
        vector_results = asyncio.run(
            search._search_vector(
                "artificial intelligence in healthcare", {"programme": "HORIZON"}, 3
            )
        )
        retrieval["semantic_project_ids"] = [r["id"] for r in vector_results]
        if not vector_results:
            problems.append("production semantic retrieval failed")
    finally:
        if search._postgres_repo:
            search._postgres_repo.close()
    if partners.get("error") or not retrieval["partner_count"]:
        problems.append("production partner retrieval failed")
    with open(args.export, "rb") as handle:
        source_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source_task_id": args.source_task_id,
        "source_sha256": source_digest,
        "source_projects": len(source),
        "source_organization_rows": len(org_source),
        "newer_project_versions_preserved": older,
        "source_matching_projects": len(accepted),
        "coverage": project_database_coverage(),
        "organizations_distinct": len({o["organisationID"] for o in organizations}),
        "graph_projects": len(graph_ids),
        "graph_consortium_pairs": len(graph_pairs),
        "postgres_consortium_pairs": len(pg_pairs),
        "embeddings": embeddings,
        "retrieval": retrieval,
        "problems": problems,
        "complete": not problems and embeddings["eligible"] == embeddings["embedded"],
    }
    path = Path(args.output)
    with path.open("w") as handle:
        path.chmod(0o600)
        json.dump(report, handle, default=str, indent=2)
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ("retrieval", "source_sha256")},
            default=str,
        )
    )
    if not report["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
