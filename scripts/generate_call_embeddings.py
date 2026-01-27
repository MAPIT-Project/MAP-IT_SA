#!/usr/bin/env python3
"""
Generate Embeddings for Funding Calls

This script generates vector embeddings for all funding calls in the database
to enable semantic search. Uses Google's text-embedding-004 model.

Usage:
    python scripts/generate_call_embeddings.py [--limit N] [--force]

Options:
    --limit N    Only process N calls (for testing)
    --force      Re-generate embeddings even if they exist
"""

import argparse
import logging
import os
import sys
from typing import Any

import numpy as np
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor, execute_values

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.embedding_service import EmbeddingService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment."""
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return db_url


def create_call_text(call: dict[str, Any]) -> str:
    """
    Create a rich text representation of a call for embedding.

    Combines title, scope, expected outcome, and metadata into a single
    text that captures the semantic meaning of the call.
    """
    parts = []

    # Title is most important
    if call.get('title'):
        parts.append(f"Title: {call['title']}")

    # Topic code provides context
    if call.get('topic_code'):
        parts.append(f"Call ID: {call['topic_code']}")

    # Cluster/destination for domain context
    if call.get('cluster'):
        cluster_names = {
            'CL1': 'Health',
            'CL2': 'Culture, Creativity and Inclusive Society',
            'CL3': 'Civil Security for Society',
            'CL4': 'Digital, Industry and Space',
            'CL5': 'Climate, Energy and Mobility',
            'CL6': 'Food, Bioeconomy, Natural Resources, Agriculture and Environment'
        }
        cluster_name = cluster_names.get(call['cluster'], call['cluster'])
        parts.append(f"Research Area: {cluster_name}")

    if call.get('destination'):
        parts.append(f"Destination: {call['destination']}")

    # Action type
    if call.get('action_type'):
        action_descriptions = {
            'RIA': 'Research and Innovation Action',
            'IA': 'Innovation Action',
            'CSA': 'Coordination and Support Action',
            'COFUND': 'Co-funded Action'
        }
        action_desc = action_descriptions.get(call['action_type'], call['action_type'])
        parts.append(f"Action Type: {action_desc}")

    # Scope is the main content - clean HTML tags
    if call.get('scope'):
        scope = call['scope']
        # Basic HTML tag removal
        import re
        scope = re.sub(r'<[^>]+>', ' ', scope)
        scope = re.sub(r'\s+', ' ', scope).strip()
        # Limit scope length to avoid token limits
        if len(scope) > 3000:
            scope = scope[:3000] + "..."
        parts.append(f"Scope: {scope}")

    # Expected outcome adds context about goals
    if call.get('expected_outcome'):
        outcome = call['expected_outcome']
        import re
        outcome = re.sub(r'<[^>]+>', ' ', outcome)
        outcome = re.sub(r'\s+', ' ', outcome).strip()
        if len(outcome) > 1500:
            outcome = outcome[:1500] + "..."
        parts.append(f"Expected Outcomes: {outcome}")

    return "\n\n".join(parts)


def get_calls_to_embed(
    conn,
    force: bool = False,
    limit: int | None = None
) -> list[dict]:
    """Get list of calls that need embeddings."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if force:
        # Get all calls with scope or title
        query = """
            SELECT id, topic_code, title, scope, expected_outcome,
                   cluster, destination, action_type
            FROM funding_calls
            WHERE (scope IS NOT NULL AND LENGTH(scope) > 50)
               OR (title IS NOT NULL AND LENGTH(title) > 10)
            ORDER BY call_year DESC NULLS LAST, topic_code
        """
    else:
        # Get calls without embeddings
        query = """
            SELECT id, topic_code, title, scope, expected_outcome,
                   cluster, destination, action_type
            FROM funding_calls
            WHERE embedding IS NULL
            AND ((scope IS NOT NULL AND LENGTH(scope) > 50)
                 OR (title IS NOT NULL AND LENGTH(title) > 10))
            ORDER BY call_year DESC NULLS LAST, topic_code
        """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    return cursor.fetchall()


def update_call_embedding(
    conn,
    call_id: str,
    embedding: np.ndarray
) -> bool:
    """Update a call's embedding in the database."""
    try:
        cursor = conn.cursor()

        # Convert numpy array to list for PostgreSQL
        embedding_list = embedding.tolist()

        cursor.execute("""
            UPDATE funding_calls
            SET embedding = %s::vector,
                embedding_updated_at = NOW()
            WHERE id = %s
        """, (embedding_list, call_id))

        conn.commit()
        return True

    except Exception as e:
        logger.error(f"Database error updating embedding: {e}")
        conn.rollback()
        return False


def update_embeddings_batch(
    conn,
    updates: list[tuple]  # List of (call_id, embedding_list)
) -> int:
    """Update multiple call embeddings in a single transaction."""
    try:
        cursor = conn.cursor()

        # Use execute_values for efficient batch update
        query = """
            UPDATE funding_calls AS fc
            SET embedding = v.embedding::vector,
                embedding_updated_at = NOW()
            FROM (VALUES %s) AS v(id, embedding)
            WHERE fc.id = v.id::uuid
        """

        execute_values(cursor, query, updates, template="(%s, %s)")
        conn.commit()
        return len(updates)

    except Exception as e:
        logger.error(f"Batch update error: {e}")
        conn.rollback()
        return 0


def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for funding calls')
    parser.add_argument('--limit', type=int, help='Limit number of calls to process')
    parser.add_argument('--force', action='store_true', help='Re-generate all embeddings')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size for processing')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Funding Calls Embedding Generator")
    logger.info("=" * 60)

    # Initialize services
    try:
        embedding_service = EmbeddingService()
        logger.info(f"✅ Embedding service initialized (model: {embedding_service.model_name})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize embedding service: {e}")
        return

    # Connect to database
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)

    # Check if embedding column exists
    cursor = conn.cursor()
    cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'funding_calls' AND column_name = 'embedding'
    """)
    if not cursor.fetchone():
        logger.error("❌ Embedding column not found. Run migration first:")
        logger.error("   psql $DATABASE_URL < migration/010_call_embeddings.sql")
        return

    # Get calls to process
    logger.info("\n📊 Finding calls that need embeddings...")
    calls = get_calls_to_embed(conn, force=args.force, limit=args.limit)
    logger.info(f"   Found {len(calls)} calls to process")

    if not calls:
        logger.info("✅ All calls already have embeddings!")
        return

    # Process calls
    stats = {
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0
    }

    logger.info(f"\n🚀 Processing {len(calls)} calls...")
    logger.info(f"   Batch size: {args.batch_size}")
    logger.info("")

    batch_texts = []
    batch_calls = []

    for i, call in enumerate(calls):
        stats['processed'] += 1
        topic_code = call.get('topic_code', 'UNKNOWN')

        # Progress indicator
        if (i + 1) % 10 == 0 or i == 0:
            logger.info(f"[{i + 1}/{len(calls)}] Processing {topic_code}...")

        # Create text for embedding
        text = create_call_text(call)

        if len(text) < 50:
            logger.debug(f"  Skipping {topic_code} - insufficient text")
            stats['skipped'] += 1
            continue

        batch_texts.append(text)
        batch_calls.append(call)

        # Process batch when full
        if len(batch_texts) >= args.batch_size:
            try:
                embeddings = embedding_service.generate_embeddings_batch(batch_texts, use_cache=False)

                updates = []
                for j, (c, emb) in enumerate(zip(batch_calls, embeddings, strict=False)):
                    if embedding_service.validate_embedding(emb) and not np.all(emb == 0):
                        updates.append((str(c['id']), emb.tolist()))
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1

                if updates:
                    update_embeddings_batch(conn, updates)
                    logger.info(f"  ✅ Batch update: {len(updates)} embeddings saved")

            except Exception as e:
                logger.error(f"  ❌ Batch processing failed: {e}")
                stats['failed'] += len(batch_texts)

            batch_texts = []
            batch_calls = []

    # Process remaining batch
    if batch_texts:
        try:
            embeddings = embedding_service.generate_embeddings_batch(batch_texts, use_cache=False)

            updates = []
            for c, emb in zip(batch_calls, embeddings, strict=False):
                if embedding_service.validate_embedding(emb) and not np.all(emb == 0):
                    updates.append((str(c['id']), emb.tolist()))
                    stats['success'] += 1
                else:
                    stats['failed'] += 1

            if updates:
                update_embeddings_batch(conn, updates)
                logger.info(f"  ✅ Final batch update: {len(updates)} embeddings saved")

        except Exception as e:
            logger.error(f"  ❌ Final batch processing failed: {e}")
            stats['failed'] += len(batch_texts)

    # Close connection
    conn.close()

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📈 SUMMARY")
    logger.info("=" * 60)
    logger.info(f"   Processed: {stats['processed']}")
    logger.info(f"   Success:   {stats['success']}")
    logger.info(f"   Failed:    {stats['failed']}")
    logger.info(f"   Skipped:   {stats['skipped']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
