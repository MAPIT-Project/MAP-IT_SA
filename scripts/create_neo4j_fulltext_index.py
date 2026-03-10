#!/usr/bin/env python3
"""
Create Neo4j full-text indexes for Project and Organization nodes.

This script creates full-text search indexes to enable efficient text-based
queries on project titles/objectives and organization names.

Indexes created:
  - project_fulltext_search: Project nodes on [title, objective]
  - org_fulltext_search: Organization nodes on [name, shortName]

Usage:
    python scripts/create_neo4j_fulltext_index.py
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.neo4j_config import neo4j_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_fulltext_indexes() -> None:
    """Create full-text indexes on Project and Organization nodes."""

    indexes = [
        {
            "name": "project_fulltext_search",
            "query": (
                "CREATE FULLTEXT INDEX project_fulltext_search IF NOT EXISTS "
                "FOR (n:Project) ON EACH [n.title, n.objective]"
            ),
        },
        {
            "name": "org_fulltext_search",
            "query": (
                "CREATE FULLTEXT INDEX org_fulltext_search IF NOT EXISTS "
                "FOR (n:Organization) ON EACH [n.name, n.shortName]"
            ),
        },
    ]

    for index in indexes:
        logger.info(f"Creating full-text index: {index['name']}...")
        try:
            neo4j_db.execute_query(index["query"])
            logger.info(f"  Created: {index['name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                logger.info(f"  Already exists: {index['name']}")
            else:
                logger.error(f"  Failed to create {index['name']}: {e}")
                raise


def verify_indexes() -> None:
    """Verify that the full-text indexes were created by listing all indexes."""

    logger.info("Verifying indexes...")

    try:
        results = neo4j_db.execute_query("SHOW INDEXES")
        fulltext_indexes = [r for r in results if r.get("type") == "FULLTEXT"]

        if fulltext_indexes:
            logger.info(f"Found {len(fulltext_indexes)} full-text index(es):")
            for idx in fulltext_indexes:
                logger.info(
                    f"  - {idx.get('name')}: "
                    f"labels={idx.get('labelsOrTypes')}, "
                    f"properties={idx.get('properties')}, "
                    f"state={idx.get('state')}"
                )
        else:
            logger.warning("No full-text indexes found!")

    except Exception as e:
        logger.error(f"Failed to verify indexes: {e}")
        raise


def main() -> int:
    """Main entry point."""

    logger.info("=" * 60)
    logger.info("Neo4j Full-Text Index Creation")
    logger.info("=" * 60)

    try:
        # Test connection
        if not neo4j_db.test_connection():
            logger.error("Cannot connect to Neo4j. Aborting.")
            return 1

        # Create indexes
        create_fulltext_indexes()

        # Verify
        verify_indexes()

        logger.info("Full-text index creation completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
