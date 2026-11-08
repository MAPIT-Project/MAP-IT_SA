#!/usr/bin/env python3
"""Mirror published, verified revisions into the call-specific document store.

Old shared records are retained. Mappings to a replaced same-edition document
move to its new revision; annual programmes do not replace other years.
"""

import argparse
import json
import re
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

from app.core.config import settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", type=Path)
    args = parser.parse_args()
    conn = psycopg2.connect(settings.database_url)
    try:
        for manifest in args.manifests:
            for row in json.loads(manifest.read_text()):
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT id,metadata,version FROM horizon_documents WHERE file_hash=%s AND status='active'",
                            (row["sha256"],),
                        )
                        source = cursor.fetchone()
                        if not source:
                            raise ValueError(f"Revision not published: {row['title']}")
                        key = "official_" + row["sha256"][:40]
                        cursor.execute(
                            "SELECT id FROM shared_documents WHERE document_key=%s", (key,)
                        )
                        if cursor.fetchone():
                            continue
                        cluster = re.search(r"Cluster ([1-6])", row["title"])
                        scope_id = f"CLUSTER-{cluster.group(1)}" if cluster else None
                        kind = (
                            "general_annexes" if "General annexes" in row["title"] else row["type"]
                        )
                        metadata = {
                            **source[1],
                            "programme_year": row["year"],
                            "horizon_document_id": source[0],
                            "full_document_version": source[2],
                        }
                        pages = json.loads(Path(row["page_text_file"]).read_text())
                        cursor.execute(
                            """INSERT INTO shared_documents
                            (document_key,document_type,document_title,document_version,scope,
                             scope_identifier,document_content,document_url,file_path,file_hash,last_updated,metadata)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s) RETURNING id""",
                            (
                                key,
                                kind,
                                row["title"],
                                source[2] if not source[2] or len(source[2]) <= 50 else source[2][:49] + "…",
                                "cluster" if cluster else "global",
                                scope_id,
                                "\n".join(pages),
                                row["url"],
                                row["download_file"],
                                row["sha256"],
                                Json(metadata),
                            ),
                        )
                        new_id = cursor.fetchone()[0]
                        cursor.execute(
                            "SELECT content,chunk_index,token_count,section_title,page_number,metadata FROM document_chunks WHERE document_id=%s ORDER BY chunk_index",
                            (source[0],),
                        )
                        chunks = cursor.fetchall()
                        if not chunks:
                            raise ValueError("Published document has no chunks")
                        execute_values(
                            cursor,
                            """INSERT INTO shared_document_chunks
                            (document_id,chunk_text,chunk_index,token_count,section_title,page_numbers,metadata)
                            VALUES %s""",
                            [(new_id, c[0], c[1], c[2], c[3], [c[4]], Json(c[5])) for c in chunks],
                            page_size=100,
                        )
                        for old_id in row.get("old_shared_records", []):
                            cursor.execute(
                                "SELECT file_hash FROM shared_documents WHERE id=%s FOR UPDATE",
                                (old_id,),
                            )
                            predecessor = cursor.fetchone()
                            if not predecessor or predecessor[0] != row["old_sha256"]:
                                raise ValueError("Shared predecessor changed since review")
                            cursor.execute(
                                """INSERT INTO call_document_mappings
                                (call_identifier,document_id,relevance_score,is_primary,mapping_source)
                                SELECT call_identifier,%s,relevance_score,is_primary,'verified_revision_refresh'
                                FROM call_document_mappings WHERE document_id=%s
                                ON CONFLICT (call_identifier,document_id) DO NOTHING""",
                                (new_id, old_id),
                            )
                            cursor.execute(
                                "DELETE FROM call_document_mappings WHERE document_id=%s", (old_id,)
                            )
                            cursor.execute(
                                """UPDATE shared_documents SET metadata=COALESCE(metadata,'{}'::jsonb)||%s::jsonb
                                WHERE id=%s""",
                                (
                                    Json({"superseded_by": new_id, "refresh_run": "20261108"}),
                                    old_id,
                                ),
                            )
                        print(
                            json.dumps(
                                {
                                    "title": row["title"],
                                    "shared_document_id": new_id,
                                    "chunks": len(chunks),
                                }
                            ),
                            flush=True,
                        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
