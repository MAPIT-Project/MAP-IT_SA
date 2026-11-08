#!/usr/bin/env python3
"""Refresh the CORDIS graph from validated PostgreSQL records, preserving other nodes."""

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
import gzip
import json
import re
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings
from app.core.neo4j_config import neo4j_db


def extract_cluster_from_topic(topic):
    code = topic.upper()
    match = re.search(r"HORIZON-CL([1-6])", code)
    if match:
        return "CLUSTER-" + match.group(1)
    if "HLTH" in code or "HEALTH" in code:
        return "CLUSTER-1"
    for programme in ("ERC", "MSCA", "INFRA", "EIC", "EIT", "WIDERA", "HLTH", "DATA", "HUMAN"):
        if programme in code:
            return programme
    return None


def value(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", default="data/cordis_backups")
    args = parser.parse_args()
    with (
        psycopg2.connect(settings.database_url) as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        cursor.execute(
            'SELECT * FROM projects WHERE "frameworkProgramme"=%s ORDER BY id', ("HORIZON",)
        )
        projects = cursor.fetchall()
        cursor.execute(
            'SELECT o.* FROM organizations o JOIN projects p ON p.id=o."projectID" WHERE p."frameworkProgramme"=%s ORDER BY o."contentUpdateDate" NULLS FIRST,o.id',
            ("HORIZON",),
        )
        organizations = cursor.fetchall()
    print(
        json.dumps(
            {
                "projects": len(projects),
                "participation_rows": len(organizations),
                "writes": args.apply,
            }
        ),
        flush=True,
    )
    if not args.apply:
        return
    directory = Path(args.backup_dir)
    directory.mkdir(parents=True, exist_ok=True)
    backup = directory / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-graph-"
        + uuid.uuid4().hex
        + ".jsonl.gz"
    )
    with backup.open("xb") as handle:
        backup.chmod(0o600)
        with (
            gzip.GzipFile(fileobj=handle, mode="wb", compresslevel=3) as archive,
            neo4j_db.get_session() as session,
        ):
            for query in [
                "MATCH (n) RETURN elementId(n) AS id,labels(n) AS labels,properties(n) AS properties",
                "MATCH (a)-[r]->(b) RETURN elementId(r) AS id,elementId(a) AS start,elementId(b) AS end,type(r) AS type,properties(r) AS properties",
            ]:
                for row in session.run(query):
                    archive.write((json.dumps(row.data(), default=str) + "\n").encode())
    print(json.dumps({"graph_backup": str(backup)}), flush=True)
    by_project = defaultdict(list)
    org_latest = {}
    for org in organizations:
        by_project[org["projectID"]].append(org)
        org_latest[org["organisationID"]] = org
    for offset in range(0, len(projects), 300):
        rows, links, participations = [], [], []
        for project in projects[offset : offset + 300]:
            pid = str(project["id"])
            props = {k: value(v) for k, v in project.items() if k != "id"}
            rows.append({"id": pid, "props": props})
            for topic in (project["topics"] or "").split(";"):
                if topic:
                    cluster = extract_cluster_from_topic(topic)
                    links.append(
                        {
                            "id": pid,
                            "topic": topic,
                            "clusters": [cluster]
                            if cluster and cluster.startswith("CLUSTER")
                            else [],
                            "programmes": [cluster]
                            if cluster and not cluster.startswith("CLUSTER")
                            else [],
                        }
                    )
            grouped = defaultdict(list)
            for org in by_project[project["id"]]:
                grouped[org["organisationID"]].append(org)
            for oid, records in grouped.items():
                roles = sorted({r["role"] for r in records if r["role"]})
                role = next(
                    (
                        r
                        for r in ("coordinator", "participant", "associatedPartner", "thirdParty")
                        if r in roles
                    ),
                    None,
                )
                contributions = [
                    r["ecContribution"] for r in records if r["ecContribution"] is not None
                ]
                participations.append(
                    {
                        "pid": pid,
                        "oid": oid,
                        "role": role,
                        "roles": roles,
                        "ecContribution": float(sum(contributions)) if contributions else None,
                        "contentUpdateDate": value(project["contentUpdateDate"]),
                    }
                )
        with neo4j_db.get_session() as session, session.begin_transaction() as tx:
            tx.run(
                "UNWIND $rows AS row MERGE (p:Project {id:row.id}) SET p += row.props", rows=rows
            ).consume()
            tx.run(
                "UNWIND $ids AS id MATCH (p:Project {id:id}) OPTIONAL MATCH (p)-[r:FUNDED_UNDER|TARGETS]-() DELETE r",
                ids=[r["id"] for r in rows],
            ).consume()
            tx.run(
                "UNWIND $rows AS row MATCH (p:Project {id:row.id}) MERGE (t:Topic {code:row.topic}) MERGE (p)-[:FUNDED_UNDER]->(t) FOREACH (code IN row.clusters | MERGE (c:Cluster {code:code}) MERGE (p)-[:TARGETS]->(c)) FOREACH (code IN row.programmes | MERGE (pr:Programme {code:code}) MERGE (p)-[:TARGETS]->(pr))",
                rows=links,
            ).consume()
            tx.run(
                "UNWIND $ids AS id MATCH (p:Project {id:id}) OPTIONAL MATCH ()-[r:PARTICIPATES_IN]->(p) DELETE r",
                ids=[r["id"] for r in rows],
            ).consume()
            tx.run(
                "UNWIND $rows AS row MERGE (o:Organization {id:row.oid}) WITH row,o MATCH (p:Project {id:row.pid}) MERGE (o)-[r:PARTICIPATES_IN]->(p) SET r.role=row.role,r.roles=row.roles,r.ecContribution=row.ecContribution,r.contentUpdateDate=row.contentUpdateDate",
                rows=participations,
            ).consume()
            tx.commit()
        print(json.dumps({"graph_projects_synced": min(offset + 300, len(projects))}), flush=True)
    orgs = []
    for oid, org in org_latest.items():
        orgs.append(
            {
                "id": oid,
                "props": {
                    "name": org["name"],
                    "shortName": org["shortName"],
                    "country": org["country"],
                    "city": org["city"],
                    "activityType": org["activityType"],
                    "sme": org["SME"],
                    "contentUpdateDate": value(org["contentUpdateDate"]),
                },
                "countries": [org["country"]] if org["country"] else [],
                "types": [org["activityType"]] if org["activityType"] else [],
            }
        )
    for offset in range(0, len(orgs), 500):
        with neo4j_db.get_session() as session, session.begin_transaction() as tx:
            batch = orgs[offset : offset + 500]
            tx.run(
                "UNWIND $rows AS row MATCH (o:Organization {id:row.id}) SET o += row.props WITH o OPTIONAL MATCH (o)-[r:LOCATED_IN|IS_TYPE]->() DELETE r",
                rows=batch,
            ).consume()
            tx.run(
                "UNWIND $rows AS row MATCH (o:Organization {id:row.id}) FOREACH (code IN row.countries | MERGE (c:Country {isoCode:code}) MERGE (o)-[:LOCATED_IN]->(c)) FOREACH (code IN row.types | MERGE (t:EntityType {code:code}) MERGE (o)-[:IS_TYPE]->(t))",
                rows=batch,
            ).consume()
            tx.commit()
    # These relationships are derived entirely from PARTICIPATES_IN. Recompute
    # in one transaction so removed consortium memberships cannot leave stale edges.
    with neo4j_db.get_session() as session, session.begin_transaction() as tx:
        tx.run("MATCH ()-[r:PARTNERS_WITH]->() DELETE r").consume()
        result = tx.run(
            "MATCH (a:Organization)-[:PARTICIPATES_IN]->(p:Project)<-[:PARTICIPATES_IN]-(b:Organization) WHERE a.id<b.id WITH a,b,count(DISTINCT p) AS projectCount,sum(p.ecMaxContribution) AS totalValue WHERE projectCount>=2 MERGE (a)-[r:PARTNERS_WITH]->(b) SET r.projectCount=projectCount,r.totalValue=totalValue,r.updatedAt=datetime() RETURN count(r) AS partnerships"
        ).single()
        partnerships = result["partnerships"]
        tx.commit()
    neo4j_db.execute_query("CALL db.awaitIndexes(300)")
    print(
        json.dumps(
            {
                "complete": True,
                "projects": len(projects),
                "organizations": len(orgs),
                "partnerships": partnerships,
                "backup": str(backup),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
