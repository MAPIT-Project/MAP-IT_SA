#!/usr/bin/env python3
"""Backfill current project text vectors; reject failed batches and concurrent edits."""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from app.core.config import settings
from app.services.embedding_service import EmbeddingService


def validated_vectors(embeddings, expected, embedder):
    if len(embeddings) != expected or any(
        e is None or not embedder.validate_embedding(e) for e in embeddings
    ):
        raise ValueError("Embedding batch invalid; no vectors from this batch saved")
    return [e.tolist() for e in embeddings]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 100:
        parser.error("batch-size must be between 1 and 100")
    embedder = EmbeddingService()
    with psycopg2.connect(settings.database_url) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""SELECT p.id,p.title,p.objective,
                md5(coalesce(p.title,'') || chr(10) || coalesce(p.objective,'')) AS text_hash
                FROM projects p LEFT JOIN project_embeddings e ON e.project_id=p.id
                WHERE (e.project_id IS NULL OR e.embedding_status <> 'completed' OR e.combined_embedding IS NULL)
                  AND length(p.title)>10 AND length(p.objective)>50 ORDER BY p.id""")
            projects = cursor.fetchall()
        conn.commit()
        print(json.dumps({"pending": len(projects)}), flush=True)
        saved = 0
        for start in range(0, len(projects), args.batch_size):
            batch = projects[start : start + args.batch_size]
            texts = [f"{p['title']}. {p['objective']}" for p in batch]
            texts = [text[:1997] + "..." if len(text) > 2000 else text for text in texts]
            vectors = validated_vectors(
                embedder.generate_embeddings_batch(texts, False), len(batch), embedder
            )
            values = [
                (p["id"], json.dumps(v), p["text_hash"], len(t), settings.embedding_model)
                for p, v, t in zip(batch, vectors, texts)
            ]
            with conn.cursor() as cursor:
                updated = execute_values(
                    cursor,
                    """INSERT INTO project_embeddings
                    (project_id,combined_embedding,text_length,model_version,embedding_status,updated_at,error_message)
                    SELECT p.id,v.vector::vector,v.text_length,v.model,'completed',now(),NULL
                    FROM (VALUES %s) AS v(id,vector,text_hash,text_length,model)
                    JOIN projects p ON p.id=v.id
                    WHERE md5(coalesce(p.title,'') || chr(10) || coalesce(p.objective,''))=v.text_hash
                    ON CONFLICT(project_id) DO UPDATE SET combined_embedding=excluded.combined_embedding,
                      text_length=excluded.text_length,model_version=excluded.model_version,
                      embedding_status='completed',updated_at=now(),error_message=NULL
                    RETURNING project_id""",
                    values,
                    fetch=True,
                )
                saved += len(updated)
            conn.commit()
            print(
                json.dumps(
                    {
                        "processed": min(start + args.batch_size, len(projects)),
                        "total": len(projects),
                        "saved": saved,
                    }
                ),
                flush=True,
            )
        print(json.dumps({"complete": True, "saved": saved}), flush=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
