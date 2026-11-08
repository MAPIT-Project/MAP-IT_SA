#!/usr/bin/env python3
import asyncio
import argparse
import logging
import os
import sys

from dotenv import load_dotenv
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.embedding_service import EmbeddingService
from app.core.config import settings

load_dotenv()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validated_updates(calls, embeddings, embedder):
    """Reject provider failures before writing any result from this batch."""
    if len(calls) != len(embeddings) or any(
        emb is None or not embedder.validate_embedding(emb) for emb in embeddings
    ):
        raise RuntimeError(
            "Embedding batch failed validation; no vectors from this batch were saved"
        )
    return [
        (emb.tolist(), call["id"], call["content_hash"]) for call, emb in zip(calls, embeddings)
    ]


async def reembed_nulls(limit=500, include_closed=False, batch_size=20, dry_run=False):
    db_url = settings.database_url
    pool = SimpleConnectionPool(1, 5, db_url)
    embedder = EmbeddingService()

    conn = pool.getconn()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        # Get funding calls with null embeddings
        # We combine fields the same way the ingestion does (title + scope + expected_outcome)
        cursor.execute(
            """
            SELECT id,
                   COALESCE(title, '') || ' ' ||
                   COALESCE(scope, '') || ' ' ||
                   COALESCE(expected_outcome, '') as content,
                   md5(COALESCE(title, '') || ' ' || COALESCE(scope, '') || ' ' ||
                       COALESCE(expected_outcome, '')) as content_hash
            FROM funding_calls
            WHERE embedding IS NULL
            AND (%s OR (status IN ('open', 'upcoming')
                AND (deadline IS NULL OR deadline >= CURRENT_DATE)
                AND COALESCE(metadata->>'portal_missing_from_snapshot', 'false') <> 'true'))
            ORDER BY deadline ASC NULLS LAST, id
            LIMIT %s;
        """,
            (include_closed, limit),
        )
        calls = cursor.fetchall()
        logger.info(f"Found {len(calls)} funding calls missing embeddings.")

        if not calls or dry_run:
            return

        # Process in batches
        updated = 0
        for i in range(0, len(calls), batch_size):
            batch = [c for c in calls[i : i + batch_size] if c["content"] and c["content"].strip()]
            texts = [c["content"][:8000] for c in batch]

            if not texts:
                continue

            logger.info(
                f"Processing batch {i//batch_size + 1}/{(len(calls) + batch_size - 1)//batch_size}"
            )

            # Generate embeddings
            embeddings = await asyncio.to_thread(embedder.generate_embeddings_batch, texts, False)
            updates = validated_updates(batch, embeddings, embedder)

            # Update DB
            update_cursor = conn.cursor()
            for values in updates:
                update_cursor.execute(
                    """UPDATE funding_calls SET embedding = %s::vector, embedding_updated_at = NOW()
                       WHERE id = %s AND embedding IS NULL
                       AND md5(COALESCE(title, '') || ' ' || COALESCE(scope, '') || ' ' ||
                               COALESCE(expected_outcome, '')) = %s""",
                    values,
                )
                updated += update_cursor.rowcount
            conn.commit()
            update_cursor.close()
        logger.info(
            "Saved %s validated embeddings; concurrent content changes were skipped.", updated
        )

    finally:
        cursor.close()
        pool.putconn(conn)
        pool.closeall()

    logger.info("Done generating missing funding call embeddings.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill missing call embeddings with validation."
    )
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--include-closed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.limit < 1 or not 1 <= args.batch_size <= 100:
        parser.error("limit must be positive and batch-size must be between 1 and 100")
    asyncio.run(reembed_nulls(args.limit, args.include_closed, args.batch_size, args.dry_run))
