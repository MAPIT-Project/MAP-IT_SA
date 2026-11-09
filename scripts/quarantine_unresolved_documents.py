#!/usr/bin/env python3
"""Retain unresolved public records in reversible source quarantine.

Dry run by default. Text, embeddings and mappings are never deleted. Reviewed
pending decisions and verified historical editions are not retirement candidates.
Use --restore BACKUP --apply to reverse a specific run with concurrency guards;
restoring a status does not establish provenance or bypass the retrieval policy.
"""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from app.core.config import settings
from app.services.document_trust import quarantine_candidate
from scripts.verify_document_origins import save_private

TABLES = {"horizon_documents", "shared_documents"}


def plan_quarantine(rows, timestamp):
    changes = []
    for row in rows:
        if not quarantine_candidate(row):
            continue
        metadata = row.get("metadata") or {}
        after = {
            **metadata,
            "retrieval_status": "quarantined",
            "origin_quarantine": {
                "reason": "Publication origin unresolved after official-source investigation",
                "quarantined_at": timestamp,
                "previous_status": row.get("status", "active"),
                "previous_provenance_status": (metadata.get("provenance") or {}).get(
                    "status", "source_not_verified"
                ),
            },
        }
        changes.append({**row, "metadata_after": after, "status_after": "archived"})
    return changes


def apply_changes(conn, changes, restore=False):
    with conn:
        with conn.cursor() as cursor:
            for row in changes:
                table = row["store"]
                if table not in TABLES:
                    raise ValueError("Unknown document store")
                old_metadata = row["metadata_after"] if restore else row.get("metadata") or {}
                new_metadata = row.get("metadata") or {} if restore else row["metadata_after"]
                values = [Json(new_metadata)]
                setters = "metadata=%s::jsonb"
                guard = ""
                if table == "horizon_documents":
                    setters += ",status=%s"
                    values.append(row.get("status", "active") if restore else row["status_after"])
                    guard = " AND created_by IS NULL AND status=%s"
                values += [row["id"], row.get("file_hash"), Json(old_metadata)]
                if guard:
                    values.append(row["status_after"] if restore else row.get("status", "active"))
                cursor.execute(
                    f"UPDATE {table} SET {setters} WHERE id=%s AND file_hash IS NOT DISTINCT FROM %s AND COALESCE(metadata,'{{}}'::jsonb)=%s::jsonb"
                    + guard,
                    values,
                )
                if cursor.rowcount != 1:
                    raise ValueError("Document changed; entire quarantine transaction rolled back")


def load_candidates(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            "SELECT id,title,file_hash,status,created_by,metadata FROM horizon_documents WHERE status='active' AND created_by IS NULL"
        )
        rows = [{**dict(r), "store": "horizon_documents"} for r in cursor.fetchall()]
        cursor.execute(
            "SELECT id,document_title AS title,file_hash,'active' AS status,metadata FROM shared_documents"
        )
        rows.extend({**dict(r), "store": "shared_documents"} for r in cursor.fetchall())
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--restore", type=Path, help="Private .before.json from a previous run")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    timestamp = datetime.now(timezone.utc).isoformat()
    if args.restore:
        changes = json.loads(args.restore.read_text())
    else:
        with closing(psycopg2.connect(settings.database_url)) as conn:
            conn.set_session(readonly=True)
            changes = plan_quarantine(load_candidates(conn), timestamp)
    report = {
        "at": timestamp,
        "operation": "restore" if args.restore else "quarantine",
        "records": len(changes),
        "applied": False,
        "documents": [{"store": r["store"], "id": r["id"], "title": r["title"]} for r in changes],
    }
    save_private(args.output, report)
    if args.apply and changes:
        # Backup includes expected post-state, enabling guarded restoration.
        save_private(args.output.with_suffix(".before.json"), changes)
        with closing(psycopg2.connect(settings.database_url)) as conn:
            apply_changes(conn, changes, restore=bool(args.restore))
        report["applied"] = True
        save_private(args.output, report)
    print(json.dumps({k: report[k] for k in ["operation", "records", "applied"]}))


if __name__ == "__main__":
    main()
