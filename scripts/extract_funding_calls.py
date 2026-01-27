#!/usr/bin/env python3
"""
Extract Funding Calls Script

Extracts structured call data from Work Programme documents stored in the database.
This populates the `funding_calls` table with searchable call information.

Usage:
    python scripts/extract_funding_calls.py

Options:
    --programme: Only process specific programme (default: all)
    --year: Only process specific work programme year
    --force: Re-extract even if calls already exist
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings
from app.services.call_extractors import HorizonEuropeExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(settings.database_url)


def ensure_table_exists(conn):
    """Create funding_calls table if it doesn't exist."""
    sql_file = project_root / "scripts" / "create_funding_calls_table.sql"

    # Check if table exists
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'funding_calls'
        )
    """
    )

    if cursor.fetchone()[0]:
        logger.info("✅ funding_calls table exists")
        return True

    logger.info("Creating funding_calls table...")

    if sql_file.exists():
        with open(sql_file) as f:
            sql = f.read()
        cursor.execute(sql)
        conn.commit()
        logger.info("✅ Created funding_calls table")
    else:
        logger.error(f"SQL file not found: {sql_file}")
        return False

    return True


def get_work_programme_documents(conn, programme: str = None, year: int = None):
    """Get Work Programme documents to process."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT id, title, document_type, programme_year
        FROM horizon_documents
        WHERE status = 'active'
        AND (
            document_type ILIKE '%work%programme%'
            OR document_type ILIKE '%work_programme%'
            OR title ILIKE '%work%programme%'
            OR title ILIKE '%wp_%'
        )
    """

    params = []
    if year:
        query += " AND programme_year = %s"
        params.append(str(year))

    query += " ORDER BY programme_year DESC, title"

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    docs = cursor.fetchall()

    logger.info(f"Found {len(docs)} Work Programme documents")
    return docs


def get_document_chunks(conn, document_id: str):
    """Get all chunks for a document."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT id, content, section_title, page_number
        FROM document_chunks
        WHERE document_id = %s
        ORDER BY page_number, chunk_index
    """,
        (document_id,),
    )

    return cursor.fetchall()


def save_calls_to_db(conn, calls: list):
    """Save extracted calls to database."""
    cursor = conn.cursor()
    saved = 0
    updated = 0

    for call in calls:
        if not call.is_valid():
            continue

        try:
            # Check if call exists
            cursor.execute("SELECT id FROM funding_calls WHERE topic_code = %s", (call.topic_code,))
            existing = cursor.fetchone()

            if existing:
                # Update existing
                cursor.execute(
                    """
                    UPDATE funding_calls SET
                        title = %s,
                        action_type = %s,
                        call_year = %s,
                        deadline = %s,
                        status = %s,
                        budget_total = %s,
                        expected_projects = %s,
                        expected_outcome = %s,
                        scope = %s,
                        cluster = %s,
                        destination = %s,
                        programme_part = %s,
                        portal_url = %s,
                        tags = %s,
                        source_document_title = %s,
                        updated_at = NOW()
                    WHERE topic_code = %s
                """,
                    (
                        call.title,
                        call.action_type,
                        call.call_year,
                        call.deadline,
                        call.status,
                        float(call.budget_total) if call.budget_total else None,
                        call.expected_projects,
                        call.expected_outcome,
                        call.scope,
                        call.cluster,
                        call.destination,
                        call.programme_part,
                        call.portal_url,
                        call.tags,
                        call.source_document_title,
                        call.topic_code,
                    ),
                )
                updated += 1
            else:
                # Insert new
                cursor.execute(
                    """
                    INSERT INTO funding_calls (
                        programme, topic_code, title, action_type,
                        call_year, deadline, status,
                        budget_total, expected_projects,
                        expected_outcome, scope,
                        cluster, destination, programme_part,
                        work_programme_year, portal_url, tags,
                        source_document_title
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s
                    )
                """,
                    (
                        call.programme,
                        call.topic_code,
                        call.title,
                        call.action_type,
                        call.call_year,
                        call.deadline,
                        call.status,
                        float(call.budget_total) if call.budget_total else None,
                        call.expected_projects,
                        call.expected_outcome,
                        call.scope,
                        call.cluster,
                        call.destination,
                        call.programme_part,
                        call.work_programme_year,
                        call.portal_url,
                        call.tags,
                        call.source_document_title,
                    ),
                )
                saved += 1

        except Exception as e:
            logger.error(f"Failed to save {call.topic_code}: {e}")
            continue

    conn.commit()
    return saved, updated


def extract_from_documents(conn, documents: list, extractor):
    """Extract calls from all documents."""
    total_calls = []

    for doc in documents:
        doc_id = doc["id"]
        doc_title = doc["title"]

        logger.info(f"Processing: {doc_title}")

        # Get chunks
        chunks = get_document_chunks(conn, doc_id)

        if not chunks:
            logger.warning(f"  No chunks found for {doc_title}")
            continue

        # Combine all content (for better context)
        # But also process chunks individually for page numbers
        all_content = "\n\n".join([c["content"] for c in chunks])

        # Extract from combined content
        calls = extractor.extract_from_content(all_content, doc_title)

        logger.info(f"  Found {len(calls)} calls in {doc_title}")
        total_calls.extend(calls)

    return total_calls


def main():
    parser = argparse.ArgumentParser(description="Extract funding calls from Work Programmes")
    parser.add_argument("--programme", type=str, help="Only process specific programme")
    parser.add_argument("--year", type=int, help="Only process specific year")
    parser.add_argument("--force", action="store_true", help="Re-extract even if calls exist")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("FUNDING CALLS EXTRACTION")
    logger.info("=" * 60)

    # Connect to database
    conn = get_db_connection()
    logger.info("✅ Connected to database")

    # Ensure table exists
    if not ensure_table_exists(conn):
        logger.error("Failed to create funding_calls table")
        return 1

    # Get documents to process
    documents = get_work_programme_documents(conn, args.programme, args.year)

    if not documents:
        logger.warning("No Work Programme documents found")
        return 0

    # Initialize extractor
    extractor = HorizonEuropeExtractor()

    # Extract calls
    all_calls = extract_from_documents(conn, documents, extractor)

    # Deduplicate by topic code
    seen_codes = set()
    unique_calls = []
    for call in all_calls:
        if call.topic_code not in seen_codes:
            seen_codes.add(call.topic_code)
            unique_calls.append(call)

    logger.info(f"\nTotal unique calls extracted: {len(unique_calls)}")

    # Save to database
    if unique_calls:
        saved, updated = save_calls_to_db(conn, unique_calls)
        logger.info(f"✅ Saved {saved} new calls, updated {updated} existing")

    # Summary
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM funding_calls")
    total = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT call_year, COUNT(*)
        FROM funding_calls
        GROUP BY call_year
        ORDER BY call_year DESC
    """
    )
    by_year = cursor.fetchall()

    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total calls in database: {total}")
    logger.info("\nCalls by year:")
    for year, count in by_year:
        logger.info(f"  {year}: {count} calls")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
