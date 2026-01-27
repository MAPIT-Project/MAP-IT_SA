#!/usr/bin/env python3
"""
Generate vector embeddings for all projects in the database.

This script:
1. Fetches all projects from PostgreSQL
2. Generates embeddings for title + objective
3. Stores embeddings in project_embeddings table
4. Handles errors and retries
5. Provides progress tracking

Usage:
    python scripts/generate_project_embeddings.py [--batch-size N] [--max-batches M] [--test]

Examples:
    # Test with 10 projects
    python scripts/generate_project_embeddings.py --test

    # Process 1000 projects (20 batches of 50)
    python scripts/generate_project_embeddings.py --batch-size 50 --max-batches 20

    # Process all remaining projects
    python scripts/generate_project_embeddings.py
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.embedding_service import EmbeddingService

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProjectEmbeddingGenerator:
    """Generate and store project embeddings."""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL required")

        self.db_pool = SimpleConnectionPool(1, 5, self.db_url)
        self.embedding_service = EmbeddingService()
        self.batch_size = 50  # Process in batches
        self.max_retries = 3
        self.rate_limit_delay = 0.5  # seconds between batches

    def get_projects_needing_embeddings(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Get projects that don't have embeddings yet or have failed."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor(cursor_factory=DictCursor)

        try:
            query = """
            SELECT p.id, p.title, p.objective
            FROM projects p
            LEFT JOIN project_embeddings pe ON p.id = pe.project_id
            WHERE (pe.project_id IS NULL OR pe.embedding_status IN ('failed', 'pending'))
              AND p.title IS NOT NULL
              AND p.objective IS NOT NULL
              AND LENGTH(p.title) > 10
              AND LENGTH(p.objective) > 50
            ORDER BY p.id
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    def get_total_projects_count(self) -> int:
        """Get total number of projects with valid content."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM projects
                WHERE title IS NOT NULL
                  AND objective IS NOT NULL
                  AND LENGTH(title) > 10
                  AND LENGTH(objective) > 50
            """)
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    def get_embedded_count(self) -> int:
        """Get number of projects that already have successful embeddings."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM project_embeddings
                WHERE embedding_status = 'completed'
                  AND combined_embedding IS NOT NULL
            """)
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    def prepare_text_for_embedding(self, title: str, objective: str) -> str:
        """
        Combine title and objective for embedding.
        Limit to first 2000 chars to stay within model limits.
        """
        combined = f"{title}. {objective}"
        # Truncate to 2000 chars (safely under model limits)
        if len(combined) > 2000:
            combined = combined[:1997] + "..."
        return combined

    async def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for text using EmbeddingService."""
        for attempt in range(self.max_retries):
            try:
                embedding = await asyncio.to_thread(self.embedding_service.generate_embedding, text)
                if embedding is not None and embedding.any():
                    return embedding.tolist()
                else:
                    logger.warning(f"Attempt {attempt + 1}: Empty embedding generated")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"All {self.max_retries} attempts failed for text: {text[:100]}...")
        return None

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float] | None]:
        """Generate embeddings for multiple texts in a single API call (much faster)."""
        try:
            embeddings = await asyncio.to_thread(
                self.embedding_service.generate_embeddings_batch,
                texts
            )
            results = []
            for emb in embeddings:
                if emb is not None and hasattr(emb, 'any') and emb.any():
                    results.append(emb.tolist())
                elif emb is not None and len(emb) > 0:
                    results.append(list(emb))
                else:
                    results.append(None)
            return results
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # Fall back to individual embeddings
            results = []
            for text in texts:
                emb = await self.generate_embedding(text)
                results.append(emb)
            return results

    def store_embedding(
        self,
        project_id: int,
        text: str,
        combined_embedding: list[float] | None,
        model_version: str = "text-embedding-004"
    ) -> bool:
        """Store embedding in database with status tracking."""
        conn = self.db_pool.getconn()
        cursor = conn.cursor()

        try:
            if combined_embedding is None:
                # Mark as failed
                query = """
                INSERT INTO project_embeddings
                    (project_id, embedding_status, error_message, text_length, updated_at)
                VALUES (%s, 'failed', 'Embedding generation failed', %s, NOW())
                ON CONFLICT (project_id)
                DO UPDATE SET
                    embedding_status = 'failed',
                    error_message = 'Embedding generation failed',
                    text_length = %s,
                    updated_at = NOW()
                """
                cursor.execute(query, (project_id, len(text), len(text)))
            else:
                # Store successful embedding
                query = """
                INSERT INTO project_embeddings
                    (project_id, combined_embedding, model_version, text_length,
                     embedding_status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'completed', NOW(), NOW())
                ON CONFLICT (project_id)
                DO UPDATE SET
                    combined_embedding = EXCLUDED.combined_embedding,
                    model_version = EXCLUDED.model_version,
                    text_length = EXCLUDED.text_length,
                    embedding_status = 'completed',
                    error_message = NULL,
                    updated_at = NOW()
                """
                cursor.execute(query, (project_id, combined_embedding, model_version, len(text)))

            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store embedding for {project_id}: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            self.db_pool.putconn(conn)

    async def process_batch(self, projects: list[dict[str, Any]]) -> tuple[int, int]:
        """Process a batch of projects using batch embedding API (much faster)."""
        success_count = 0
        fail_count = 0

        # Prepare all texts for batch embedding
        valid_projects = []
        texts = []

        for project in projects:
            project_id = project['id']
            title = project.get('title', '') or ''
            objective = project.get('objective', '') or ''

            if not title and not objective:
                logger.warning(f"Skipping project {project_id}: no title or objective")
                fail_count += 1
                continue

            text = self.prepare_text_for_embedding(title, objective)
            valid_projects.append((project_id, text))
            texts.append(text)

        if not texts:
            return success_count, fail_count

        # Generate all embeddings in one batch API call
        embeddings = await self.generate_embeddings_batch(texts)

        # Store each embedding
        for i, (project_id, text) in enumerate(valid_projects):
            embedding = embeddings[i] if i < len(embeddings) else None

            if self.store_embedding(project_id, text, embedding):
                if embedding is not None:
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1

        return success_count, fail_count

    async def run(self, batch_size: int = 50, max_batches: int | None = None, test_mode: bool = False):
        """Main execution loop."""
        total_projects = self.get_total_projects_count()
        embedded_count = self.get_embedded_count()
        remaining = total_projects - embedded_count

        logger.info(f"📊 Total projects: {total_projects}")
        logger.info(f"📊 Already embedded: {embedded_count}")
        logger.info(f"📊 Remaining: {remaining}")

        if remaining == 0:
            logger.info("✅ All projects already have embeddings!")
            return

        if test_mode:
            logger.info("🧪 TEST MODE: Processing only first 10 projects")
            max_batches = 1
            batch_size = 10

        processed = 0
        batch_num = 0
        total_success = 0
        total_fail = 0

        while True:
            if max_batches and batch_num >= max_batches:
                logger.info(f"Reached max batches limit: {max_batches}")
                break

            # Get next batch
            projects = self.get_projects_needing_embeddings(limit=batch_size)

            if not projects:
                logger.info("✅ No more projects to process!")
                break

            logger.info(f"🔄 Processing batch {batch_num + 1}: {len(projects)} projects")

            # Process batch
            success, fail = await self.process_batch(projects)
            total_success += success
            total_fail += fail
            processed += len(projects)

            logger.info(f"✅ Batch {batch_num + 1} complete: {success} successful, {fail} failed")
            logger.info(f"📊 Progress: {total_success}/{remaining} ({total_success/remaining*100:.1f}%)")

            batch_num += 1

            # Small delay to avoid rate limiting
            if not test_mode:
                await asyncio.sleep(self.rate_limit_delay)

        logger.info(f"🎉 Complete! Processed {processed} projects")
        logger.info(f"✅ Successful: {total_success}")
        logger.info(f"❌ Failed: {total_fail}")

        # Print summary
        if total_fail > 0:
            logger.warning(f"⚠️ {total_fail} projects failed. Check logs for details.")

        # Suggest next steps
        if not test_mode and total_success < remaining:
            logger.info(f"📋 Next: Run script again to process remaining {remaining - total_success} projects")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate project embeddings")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size (default: 50)")
    parser.add_argument("--max-batches", type=int, help="Maximum number of batches to process")
    parser.add_argument("--test", action="store_true", help="Test mode (process only 10 projects)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        generator = ProjectEmbeddingGenerator()

        if args.test:
            logger.info("Starting in test mode...")
            await generator.run(batch_size=10, max_batches=1, test_mode=True)
        else:
            logger.info("Starting embedding generation...")
            await generator.run(batch_size=args.batch_size, max_batches=args.max_batches)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())