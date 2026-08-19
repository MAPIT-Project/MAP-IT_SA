"""
Incremental Embedding Update Service

Detects and processes new/modified projects that need embeddings.
Designed to be run as a scheduled task via Celery or cron.
"""

import logging
import os
from datetime import datetime
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

load_dotenv()
logger = logging.getLogger(__name__)


class IncrementalEmbeddingService:
    """Service for incremental embedding updates."""

    _instance = None
    _pool = None

    def __new__(cls):
        """Singleton pattern for shared connection pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the embedding service."""
        if self._initialized:
            return

        self.db_url = os.getenv("DATABASE_URL")
        self.google_api_key = os.getenv("GOOGLE_EMBEDDING_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.batch_size = 50
        # Embedding model config
        self.embedding_model = "models/gemini-embedding-001"
        self.embedding_dimension = 3072
        self.enabled = bool(self.db_url) and bool(self.google_api_key)

        if self.enabled:
            try:
                self._init_pool()
                self._init_embedding_client()
                logger.info("✅ Incremental embedding service initialized")
            except Exception as e:
                logger.warning(f"⚠️ Embedding service disabled: {e}")
                self.enabled = False

        self._initialized = True

    def _init_pool(self):
        """Initialize database connection pool."""
        if IncrementalEmbeddingService._pool is None:
            IncrementalEmbeddingService._pool = pool.SimpleConnectionPool(1, 5, self.db_url)

    def _init_embedding_client(self):
        """Initialize the embedding client."""
        genai.configure(api_key=self.google_api_key)

    def _get_connection(self):
        """Get a connection from the pool."""
        if IncrementalEmbeddingService._pool:
            return IncrementalEmbeddingService._pool.getconn()
        return None

    def _put_connection(self, conn):
        """Return a connection to the pool."""
        if IncrementalEmbeddingService._pool and conn:
            IncrementalEmbeddingService._pool.putconn(conn)

    def get_projects_needing_embeddings(self, limit: int = 500) -> list[dict]:
        """
        Find projects that need embeddings:
        1. New projects without embeddings
        2. Projects where content changed (objective updated)
        3. Failed embeddings to retry
        """
        if not self.enabled:
            return []

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return []

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                WITH projects_status AS (
                    SELECT
                        p.id,
                        p.title,
                        p.objective,
                        pe.embedding_status,
                        pe.text_length as embedded_text_length,
                        LENGTH(COALESCE(p.title, '') || '. ' || COALESCE(p.objective, '')) as current_text_length
                    FROM projects p
                    LEFT JOIN project_embeddings pe ON p.id = pe.project_id
                    WHERE p.title IS NOT NULL
                      AND p.objective IS NOT NULL
                      AND LENGTH(p.title) > 10
                      AND LENGTH(p.objective) > 50
                )
                SELECT id, title, objective
                FROM projects_status
                WHERE
                    -- No embedding yet
                    embedding_status IS NULL
                    -- Or embedding failed
                    OR embedding_status = 'failed'
                    -- Or content changed significantly (text length different by >100 chars)
                    OR (embedding_status = 'completed'
                        AND ABS(current_text_length - COALESCE(embedded_text_length, 0)) > 100)
                ORDER BY
                    CASE
                        WHEN embedding_status IS NULL THEN 1  -- New projects first
                        WHEN embedding_status = 'failed' THEN 2  -- Then retries
                        ELSE 3  -- Then updates
                    END,
                    id
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            return results

        except Exception as e:
            logger.error(f"Error getting projects needing embeddings: {e}")
            return []
        finally:
            self._put_connection(conn)

    def get_embedding_stats(self) -> dict[str, Any]:
        """Get current embedding statistics."""
        if not self.enabled:
            return {"error": "Embedding service not enabled"}

        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return {"error": "Database connection failed"}

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Total projects with valid content
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM projects
                WHERE title IS NOT NULL AND objective IS NOT NULL
                  AND LENGTH(title) > 10 AND LENGTH(objective) > 50
            """
            )
            total = cursor.fetchone()["count"]

            # By status
            cursor.execute(
                """
                SELECT embedding_status, COUNT(*) as count
                FROM project_embeddings
                GROUP BY embedding_status
            """
            )
            by_status = {row["embedding_status"]: row["count"] for row in cursor.fetchall()}

            # Needing update
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM projects p
                LEFT JOIN project_embeddings pe ON p.id = pe.project_id
                WHERE p.title IS NOT NULL AND p.objective IS NOT NULL
                  AND (pe.project_id IS NULL OR pe.embedding_status = 'failed')
            """
            )
            needing_update = cursor.fetchone()["count"]

            cursor.close()

            completed = by_status.get("completed", 0)
            coverage = round(completed / total * 100, 1) if total > 0 else 0

            return {
                "total_projects": total,
                "embedded": completed,
                "failed": by_status.get("failed", 0),
                "pending": by_status.get("pending", 0),
                "needing_update": needing_update,
                "coverage_pct": coverage,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting embedding stats: {e}")
            return {"error": str(e)}
        finally:
            self._put_connection(conn)

    def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for a text using Google's embedding model."""
        if not text or len(text.strip()) < 20:
            return None

        try:
            # Truncate text if too long (embedding models have limits)
            max_chars = 10000
            if len(text) > max_chars:
                text = text[:max_chars]

            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=self.embedding_dimension,
            )

            return result["embedding"]

        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return None

    def process_project_batch(self, projects: list[dict]) -> dict[str, int]:
        """Process a batch of projects and generate/store embeddings."""
        if not self.enabled:
            return {"processed": 0, "success": 0, "failed": 0}

        conn = None
        processed = 0
        success = 0
        failed = 0

        try:
            conn = self._get_connection()
            if not conn:
                return {"processed": 0, "success": 0, "failed": 0, "error": "No connection"}

            cursor = conn.cursor()

            for project in projects:
                project_id = project["id"]
                title = project.get("title", "")
                objective = project.get("objective", "")

                # Combine title and objective for embedding
                text = f"{title}. {objective}"
                text_length = len(text)

                # Generate embedding
                embedding = self.generate_embedding(text)
                processed += 1

                if embedding:
                    # Upsert embedding
                    cursor.execute(
                        """
                        INSERT INTO project_embeddings
                        (project_id, combined_embedding, model_version, text_length, embedding_status, updated_at)
                        VALUES (%s, %s, %s, %s, 'completed', NOW())
                        ON CONFLICT (project_id)
                        DO UPDATE SET
                            combined_embedding = EXCLUDED.combined_embedding,
                            model_version = EXCLUDED.model_version,
                            text_length = EXCLUDED.text_length,
                            embedding_status = 'completed',
                            updated_at = NOW()
                    """,
                        (project_id, embedding, self.embedding_model, text_length),
                    )
                    success += 1
                else:
                    # Mark as failed
                    cursor.execute(
                        """
                        INSERT INTO project_embeddings
                        (project_id, text_length, embedding_status, updated_at)
                        VALUES (%s, %s, 'failed', NOW())
                        ON CONFLICT (project_id)
                        DO UPDATE SET
                            embedding_status = 'failed',
                            updated_at = NOW()
                    """,
                        (project_id, text_length),
                    )
                    failed += 1

                # Commit in batches
                if processed % 10 == 0:
                    conn.commit()

            # Final commit
            conn.commit()
            cursor.close()

            logger.info(
                f"📊 Embedding batch: processed={processed}, success={success}, failed={failed}"
            )

        except Exception as e:
            logger.error(f"Error processing embedding batch: {e}")
            if conn:
                conn.rollback()
            return {"processed": processed, "success": success, "failed": failed, "error": str(e)}
        finally:
            self._put_connection(conn)

        return {"processed": processed, "success": success, "failed": failed}

    def run_incremental_update(self, max_projects: int = 500) -> dict[str, Any]:
        """
        Run incremental embedding update.

        Args:
            max_projects: Maximum number of projects to process in this run

        Returns:
            Summary of the update operation
        """
        if not self.enabled:
            return {"error": "Embedding service not enabled", "processed": 0}

        start_time = datetime.now()

        # Get projects needing embeddings
        projects = self.get_projects_needing_embeddings(limit=max_projects)

        if not projects:
            return {
                "status": "complete",
                "message": "No projects need embedding updates",
                "processed": 0,
                "duration_seconds": 0,
            }

        logger.info(f"🔄 Starting incremental embedding update for {len(projects)} projects")

        # Process in batches
        total_results = {"processed": 0, "success": 0, "failed": 0}

        for i in range(0, len(projects), self.batch_size):
            batch = projects[i : i + self.batch_size]
            batch_results = self.process_project_batch(batch)

            total_results["processed"] += batch_results.get("processed", 0)
            total_results["success"] += batch_results.get("success", 0)
            total_results["failed"] += batch_results.get("failed", 0)

            logger.info(f"Processed batch {i // self.batch_size + 1}")

        duration = (datetime.now() - start_time).total_seconds()

        return {
            "status": "complete",
            "processed": total_results["processed"],
            "success": total_results["success"],
            "failed": total_results["failed"],
            "duration_seconds": round(duration, 1),
            "rate_per_second": (
                round(total_results["processed"] / duration, 1) if duration > 0 else 0
            ),
            "timestamp": datetime.now().isoformat(),
        }


# Singleton instance
_embedding_service = None


def get_embedding_service() -> IncrementalEmbeddingService:
    """Get the singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = IncrementalEmbeddingService()
    return _embedding_service
