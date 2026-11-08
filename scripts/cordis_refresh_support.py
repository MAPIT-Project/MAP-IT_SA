#!/usr/bin/env python3
"""Small operational stages shared by the CORDIS refresh runner."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def refresh_indexes():
    import psycopg2
    from app.core.config import settings

    connection = psycopg2.connect(settings.database_url)
    connection.autocommit = True  # CONCURRENTLY cannot run inside a transaction.
    try:
        with connection.cursor() as cursor:
            statements = (ROOT / "scripts/sql/cordis_retrieval_indexes.sql").read_text().split(";")
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)
            for table in ("projects", "organizations"):
                cursor.execute("ANALYZE " + table)
    finally:
        connection.close()
    return {"indexes_refreshed": True}


def invalidate_results(client=None):
    if client is None:
        import redis
        from app.core.config import settings

        client = redis.Redis.from_url(settings.redis_url)
    types = (
        "programme_statistics",
        "country_statistics",
        "cluster_statistics",
        "budget_benchmark",
        "consortium_patterns",
        "call_history",
        "projects",
        "similar_projects",
        "experienced_partners",
    )
    patterns = [f"result:{name}:*" for name in types] + ["merged_projects*", "query_plan:*"]
    removed = {}
    for pattern in patterns:
        # Delete bounded batches; leave conversations, sessions and other data alone.
        removed[pattern] = 0
        batch = []
        for key in client.scan_iter(match=pattern, count=200):
            batch.append(key)
            if len(batch) == 200:
                removed[pattern] += client.delete(*batch)
                batch.clear()
        if batch:
            removed[pattern] += client.delete(*batch)
    return {"removed": removed, "conversation_data_preserved": True}


def record_snapshot(run_directory):
    from app.services.project_coverage import write_snapshot_provenance

    manifest = json.loads((run_directory / "manifest.json").read_text())
    report = json.loads((run_directory / "verification.json").read_text())
    if report.get("source_sha256") != manifest["source_sha256"]:
        raise ValueError("Verification and run export digests differ")
    if manifest["stages"].get("import", {}).get("status") != "complete":
        raise ValueError("Import stage has not completed")
    return write_snapshot_provenance(report, manifest["stages"]["import"]["finished_at"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["indexes", "cache", "snapshot"])
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    if args.stage == "snapshot" and args.run_dir is None:
        parser.error("snapshot requires --run-dir")
    if args.stage == "indexes":
        result = refresh_indexes()
    elif args.stage == "cache":
        result = invalidate_results()
    else:
        result = record_snapshot(args.run_dir)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
