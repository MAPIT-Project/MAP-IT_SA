#!/usr/bin/env python3
"""Publish a reviewed official-PDF manifest, preserving prior revisions.

Run inside the API environment. The manifest must contain approved entries with
download_file, page_text_file, sha256, url, title, year, type and old_records.
No download occurs here. Dry-run is the default; --apply writes to PostgreSQL.
Each document and its chunks are committed atomically after all vectors validate.
"""

import argparse
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import psycopg2
from psycopg2.extras import Json, execute_values

from app.core.config import settings
from app.services.chunking_service import TextChunker
from app.services.embedding_service import EmbeddingService

OFFICIAL_HOSTS = {
    "eur-lex.europa.eu",
    "ec.europa.eu",
    "research-and-innovation.ec.europa.eu",
    "eic.ec.europa.eu",
    "health.ec.europa.eu",
    "cybersecurity-centre.europa.eu",
    "culture.ec.europa.eu",
    "publications.europa.eu",
    "circabc.europa.eu",
}


def validate_source(row):
    parsed = urlsplit(row["url"])
    if (
        parsed.scheme != "https"
        or parsed.hostname not in OFFICIAL_HOSTS
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Source must be an official HTTPS URL")
    data = Path(row["download_file"]).read_bytes()
    if not data.startswith(b"%PDF-") or hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise ValueError("Staged PDF differs from reviewed digest")
    pages = json.loads(Path(row["page_text_file"]).read_text())
    text_digest = hashlib.sha256(json.dumps(pages, ensure_ascii=False).encode()).hexdigest()
    if text_digest != row["page_text_sha256"]:
        raise ValueError("Staged extraction differs from reviewed text")
    if not pages or sum(len(page.strip()) for page in pages) < 300:
        raise ValueError("No usable PDF text")
    return pages


def prepare_chunks(row, pages, document_id, chunker):
    chunks = []
    for number, page in enumerate(pages, 1):
        if not page.strip():
            continue
        for chunk in chunker.chunk_text(page, document_id=document_id):
            chunk["chunk_index"] = len(chunks)
            chunk["page_number"] = number
            chunk["metadata"] = {
                "source_url": row["url"],
                "document_version": row["version"],
                "programme_year": row["year"],
                "content_sha256": row["sha256"],
                "provenance_status": "verified_official_download",
            }
            chunks.append(chunk)
    if not chunks:
        raise ValueError("No searchable chunks extracted")
    return chunks


def embed_chunks(chunks, embedder, cache):
    content_hash = hashlib.sha256("\n".join(c["content"] for c in chunks).encode()).hexdigest()
    if cache.exists():
        saved = np.load(cache, allow_pickle=False)
        if str(saved["content_hash"]) != content_hash or str(saved["model"]) != embedder.model_name:
            raise ValueError("Embedding checkpoint does not match content/model")
        vectors = list(saved["vectors"])
    else:
        vectors = []
        for start in range(0, len(chunks), 20):
            texts = [c["content"] for c in chunks[start : start + 20]]
            for attempt in range(3):
                batch = embedder.generate_embeddings_batch(texts, use_cache=False)
                if len(batch) == len(texts) and all(embedder.validate_embedding(v) for v in batch):
                    break
                if attempt == 2:
                    raise ValueError(
                        f"Invalid embeddings at chunk {start}; document left unchanged"
                    )
                time.sleep(3 * (attempt + 1))
            vectors.extend(batch)
            print(
                json.dumps(
                    {
                        "event": "embedding_progress",
                        "chunks": min(start + 20, len(chunks)),
                        "total": len(chunks),
                    }
                ),
                flush=True,
            )
        np.savez_compressed(
            cache, vectors=np.asarray(vectors), content_hash=content_hash, model=embedder.model_name
        )
    if len(vectors) != len(chunks) or not all(embedder.validate_embedding(v) for v in vectors):
        raise ValueError("Incomplete or invalid embedding checkpoint")
    return vectors


def publish(conn, row, chunks, vectors, model):
    now = datetime.now(timezone.utc).isoformat()
    document_id = chunks[0]["document_id"]
    provenance = {
        "status": "verified_official_download",
        "source_url": row["url"],
        "content_sha256": row["sha256"],
        "checked_at": row["checked_at"],
        "release_date": row.get("release_date"),
        "refresh_run": row["refresh_run"],
    }
    if row.get("source_warning"):
        provenance["warning"] = row["source_warning"]
    metadata = {
        "provenance": provenance,
        "total_chunks": len(chunks),
        "page_count": row["new_pages"],
        "supersedes": row["old_records"],
        "programme": row.get("programme", "horizon_europe"),
        "version_evidence": row.get("version_evidence"),
        "extraction_note": row.get("extraction_note"),
    }
    with conn:
        with conn.cursor() as cursor:
            # Another refresh may have completed while embeddings were generated.
            cursor.execute(
                "SELECT id FROM horizon_documents WHERE file_hash=%s AND status='active'",
                (row["sha256"],),
            )
            if cursor.fetchone():
                return "already_present"
            cursor.execute(
                """INSERT INTO horizon_documents
                (id,source_type,source_url,file_path,title,document_type,programme_year,
                 language,version,status,file_hash,total_chunks,metadata,processing_completed_at)
                VALUES (%s,'pdf',%s,%s,%s,%s,%s,'en',%s,'active',%s,%s,%s,now())""",
                (
                    document_id,
                    row["url"],
                    row["download_file"],
                    row["title"],
                    row["type"],
                    row["year"],
                    row["version"],
                    row["sha256"],
                    len(chunks),
                    Json(metadata),
                ),
            )
            values = [
                (
                    c["id"],
                    document_id,
                    c["chunk_index"],
                    c.get("chunk_hash") or hashlib.sha256(c["content"].encode()).hexdigest(),
                    c["content"],
                    len(c["content"]),
                    c.get("section_title"),
                    c["page_number"],
                    Json(c["metadata"]),
                    c.get("token_count"),
                    model,
                    v.tolist(),
                )
                for c, v in zip(chunks, vectors, strict=True)
            ]
            execute_values(
                cursor,
                """INSERT INTO document_chunks
                (id,document_id,chunk_index,chunk_hash,content,content_length,section_title,
                 page_number,metadata,token_count,embedding_model,embedding) VALUES %s""",
                values,
                page_size=50,
            )
            # Only reviewed same-edition replacements are archived. New annual
            # programmes have no old_records: historical calls keep their sources.
            for old_id in row["old_records"]:
                cursor.execute(
                    """UPDATE horizon_documents SET status='archived',last_updated=now(),
                    metadata=COALESCE(metadata,'{}'::jsonb)||%s::jsonb
                    WHERE id=%s AND file_hash IS NOT DISTINCT FROM %s""",
                    (
                        Json(
                            {
                                "superseded_by": document_id,
                                "superseded_at": now,
                                "review_state": "superseded",
                            }
                        ),
                        old_id,
                        row["old_record_hashes"][old_id],
                    ),
                )
                if cursor.rowcount != 1:
                    raise ValueError("Old document changed since review; publication rolled back")
    return "published"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows = json.loads(args.manifest.read_text())
    chunker = TextChunker()
    embedder = EmbeddingService() if args.apply else None
    conn = psycopg2.connect(settings.database_url)
    try:
        if args.apply:
            with conn.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(hashtext('mapit_document_refresh'))")
                if not cursor.fetchone()[0]:
                    raise RuntimeError("Another document refresh is running")
        for row in rows:
            pages = validate_source(row)
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM horizon_documents WHERE file_hash=%s AND status='active'",
                    (row["sha256"],),
                )
                if cursor.fetchone():
                    print(
                        json.dumps({"title": row["title"], "status": "already_present"}), flush=True
                    )
                    continue
            chunks = prepare_chunks(row, pages, str(uuid.uuid4()), chunker)
            # TextChunker does not assign a primary key to chunks.
            for chunk in chunks:
                chunk["id"] = str(uuid.uuid4())
            if not args.apply:
                print(
                    json.dumps(
                        {
                            "title": row["title"],
                            "chunks": len(chunks),
                            "archive": row["old_records"],
                        }
                    ),
                    flush=True,
                )
                continue
            checkpoint = args.manifest.parent / (row["sha256"] + ".embeddings.npz")
            vectors = embed_chunks(chunks, embedder, checkpoint)
            status = publish(conn, row, chunks, vectors, embedder.model_name)
            print(
                json.dumps({"title": row["title"], "status": status, "chunks": len(chunks)}),
                flush=True,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    main()
