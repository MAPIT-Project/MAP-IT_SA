#!/usr/bin/env python3
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.embedding_service import EmbeddingService

load_dotenv()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def reembed_nulls():
    db_url = os.getenv("DATABASE_URL")
    pool = SimpleConnectionPool(1, 5, db_url)
    embedder = EmbeddingService()

    conn = pool.getconn()
    cursor = conn.cursor(cursor_factory=DictCursor)

    try:
        # Get chunks with null embeddings
        cursor.execute(
            "SELECT id, content FROM document_chunks WHERE embedding IS NULL LIMIT 50000;"
        )
        chunks = cursor.fetchall()
        logger.info(f"Found {len(chunks)} chunks missing embeddings.")

        if not chunks:
            return

        # Process in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c["content"] for c in batch if c["content"] and c["content"].strip()]
            ids = [c["id"] for c in batch if c["content"] and c["content"].strip()]

            if not texts:
                continue

            logger.info(
                f"Processing batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}"
            )

            # Generate embeddings
            embeddings = await asyncio.to_thread(embedder.generate_embeddings_batch, texts, False)

            # Update DB
            update_cursor = conn.cursor()
            for j, emb in enumerate(embeddings):
                if emb is not None and len(emb) > 0:
                    update_cursor.execute(
                        "UPDATE document_chunks SET embedding = %s WHERE id = %s",
                        (emb.tolist(), ids[j]),
                    )
            conn.commit()
            update_cursor.close()

    finally:
        cursor.close()
        pool.putconn(conn)

    logger.info("Done generating missing chunk embeddings.")


if __name__ == "__main__":
    asyncio.run(reembed_nulls())
