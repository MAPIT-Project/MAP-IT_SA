#!/usr/bin/env python3
"""Register reviewed source evidence without approving unresolved legal revisions.

Candidate PDFs are archived and excluded from ordinary retrieval. Official
metadata-only notices are searchable with an explicit warning. Byte-identical
existing documents can receive a verified origin. No existing text is replaced.
"""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

from app.core.config import settings
from app.services.document_source_discovery import OFFICIAL_PUBLISHERS, official_https_url
from app.services.embedding_service import EmbeddingService


def validate_evidence(row):
    if row["kind"] not in {"candidate", "identical", "metadata_notice"}:
        raise ValueError("Unknown evidence kind")
    if not official_https_url(row["source_url"], row["source_url"], OFFICIAL_PUBLISHERS):
        raise ValueError("Untrusted source URL")
    data = Path(row["file_path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != row["file_hash"]:
        raise ValueError("Evidence file changed since review")
    if row["kind"] in ("candidate", "identical") and not data.startswith(b"%PDF-"):
        raise ValueError("Evidence is not a PDF")
    if row["kind"] == "metadata_notice":
        metadata = json.loads(data)
        for field, value in row["evidence_fields"].items():
            if metadata.get(field) != value:
                raise ValueError("Notice does not match official metadata")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows = json.loads(args.manifest.read_text())
    for row in rows:
        validate_evidence(row)
    if not args.apply:
        print(json.dumps({"validated_sources": len(rows), "writes": False}))
        return
    conn = psycopg2.connect(settings.database_url)
    try:
        for row in rows:
            if row["kind"] == "identical":
                with conn:
                    with conn.cursor() as cursor:
                        for old_id, expected_hash in row["old_record_hashes"].items():
                            cursor.execute(
                                """UPDATE horizon_documents SET source_url=%s,version=%s,
                                metadata=COALESCE(metadata,'{}'::jsonb)||%s::jsonb
                                WHERE id=%s AND file_hash IS NOT DISTINCT FROM %s AND status='active'""",
                                (
                                    row["source_url"],
                                    row["version"],
                                    Json({"provenance": row["provenance"]}),
                                    old_id,
                                    expected_hash,
                                ),
                            )
                            if cursor.rowcount != 1:
                                raise ValueError("Existing source changed since review")
                print(json.dumps({"kind": "verified_unchanged", "title": row["title"]}), flush=True)
                continue
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM horizon_documents WHERE file_hash=%s", (row["file_hash"],)
                )
                if cursor.fetchone():
                    print(
                        json.dumps({"kind": "already_recorded", "title": row["title"]}), flush=True
                    )
                    continue
            vector = None
            if row["kind"] == "metadata_notice":
                embedder = EmbeddingService()
                vectors = embedder.generate_embeddings_batch([row["content"]], use_cache=False)
                if len(vectors) != 1 or not embedder.validate_embedding(vectors[0]):
                    raise ValueError("Metadata notice embedding failed")
                vector = vectors[0]
            document_id = str(uuid.uuid4())
            metadata = {
                "review_state": "pending",
                "programme": row["programme"],
                "provenance": row["provenance"],
                "review_run": "20261108-followup",
            }
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO horizon_documents
                        (id,source_type,source_url,file_path,title,document_type,programme_year,
                         language,version,status,file_hash,total_chunks,metadata)
                        VALUES (%s,%s,%s,%s,%s,'policy',%s,'en',%s,%s,%s,%s,%s)""",
                        (
                            document_id,
                            "web" if vector is not None else "pdf",
                            row["source_url"],
                            row["file_path"],
                            row["title"],
                            row["year"],
                            row["version"],
                            "active" if vector is not None else "archived",
                            row["file_hash"],
                            1 if vector is not None else 0,
                            Json(metadata),
                        ),
                    )
                    if vector is not None:
                        cursor.execute(
                            """INSERT INTO document_chunks
                            (id,document_id,chunk_index,chunk_hash,content,content_length,
                             metadata,embedding_model,embedding) VALUES (%s,%s,0,%s,%s,%s,%s,%s,%s)""",
                            (
                                str(uuid.uuid4()),
                                document_id,
                                hashlib.sha256(row["content"].encode()).hexdigest(),
                                row["content"],
                                len(row["content"]),
                                Json(
                                    {
                                        "source_url": row["source_url"],
                                        "provenance_status": "verified_official_metadata_only",
                                        "source_warning": row["provenance"]["warning"],
                                    }
                                ),
                                embedder.model_name,
                                vector.tolist(),
                            ),
                        )
                    # Flag the old edition too, so retrieving it carries the caveat.
                    for old_id, expected_hash in row.get("old_record_hashes", {}).items():
                        cursor.execute(
                            """UPDATE horizon_documents SET
                            metadata=jsonb_set(COALESCE(metadata,'{}'::jsonb),'{provenance}',
                                COALESCE(metadata->'provenance','{}'::jsonb)||%s::jsonb)
                            WHERE id=%s AND file_hash IS NOT DISTINCT FROM %s""",
                            (
                                Json(
                                    {
                                        "warning": row["provenance"]["warning"],
                                        "status": "current_revision_unconfirmed",
                                    }
                                ),
                                old_id,
                                expected_hash,
                            ),
                        )
                        if cursor.rowcount != 1:
                            raise ValueError("Old source changed since review")
            print(
                json.dumps({"kind": row["kind"], "title": row["title"], "id": document_id}),
                flush=True,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
