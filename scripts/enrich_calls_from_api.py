#!/usr/bin/env python3
"""
Enrich Funding Calls from EU Portal API

This script goes through all calls in the database that are missing
deadline or scope data and fetches the complete information from
the EU Portal API.

Usage:
    python scripts/enrich_calls_from_api.py [--limit N] [--dry-run]

Options:
    --limit N    Only process N calls (for testing)
    --dry-run    Don't update database, just show what would be done
    --force      Re-fetch even if data exists (refresh all)
"""

import argparse
import json
import logging
import os
import time
from datetime import date, datetime
from typing import Any

import httpx
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# EU Portal API endpoint
EU_PORTAL_TOPIC_DETAILS = "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails"


def get_database_url() -> str:
    """Get database URL from environment."""
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return db_url


def get_calls_to_enrich(conn, force: bool = False, limit: int | None = None) -> list[dict]:
    """Get list of calls that need enrichment."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if force:
        # Get all calls
        query = """
            SELECT topic_code, title, status, deadline, scope
            FROM funding_calls
            WHERE topic_code IS NOT NULL
            ORDER BY call_year DESC, topic_code
        """
    else:
        # Get calls missing deadline OR scope
        query = """
            SELECT topic_code, title, status, deadline, scope
            FROM funding_calls
            WHERE topic_code IS NOT NULL
            AND (
                deadline IS NULL
                OR scope IS NULL
                OR LENGTH(scope) < 50
                OR status IS NULL
            )
            ORDER BY call_year DESC, topic_code
        """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    return cursor.fetchall()


def fetch_from_api(topic_code: str, client: httpx.Client) -> dict[str, Any] | None:
    """Fetch call details from EU Portal API."""
    # API requires lowercase topic codes
    url = f"{EU_PORTAL_TOPIC_DETAILS}/{topic_code.lower()}.json"

    try:
        response = client.get(url)

        if response.status_code == 404:
            logger.debug(f"  Not found in API: {topic_code}")
            return None

        if response.status_code != 200:
            logger.warning(f"  API returned {response.status_code} for {topic_code}")
            return None

        data = response.json()
        topic_data = data.get('TopicDetails', {})

        if not topic_data:
            return None

        # Extract deadline and status from 'actions' field
        deadline = None
        status = 'unknown'
        actions = topic_data.get('actions', [])

        if actions and isinstance(actions, list) and len(actions) > 0:
            action = actions[0]

            # Get deadline from deadlineDates (Unix timestamp in milliseconds)
            deadline_dates = action.get('deadlineDates', [])
            if deadline_dates and len(deadline_dates) > 0:
                try:
                    timestamp_ms = int(deadline_dates[0])
                    deadline = datetime.fromtimestamp(timestamp_ms / 1000).date()
                except Exception as e:
                    logger.debug(f"  Could not parse deadline: {e}")

            # Get status from action.status
            status_info = action.get('status', {})
            if isinstance(status_info, dict):
                status_abbr = status_info.get('abbreviation', '').lower()
                if 'open' in status_abbr:
                    status = 'open'
                elif 'closed' in status_abbr:
                    status = 'closed'
                elif 'forthcoming' in status_abbr or 'upcoming' in status_abbr:
                    status = 'upcoming'

        # Fallback to statusOfTopic
        if status == 'unknown':
            status_data = topic_data.get('statusOfTopic', {})
            if isinstance(status_data, dict):
                status_abbr = status_data.get('abbreviation', '').lower()
                if 'open' in status_abbr:
                    status = 'open'
                elif 'closed' in status_abbr:
                    status = 'closed'
                elif 'forthcoming' in status_abbr:
                    status = 'upcoming'

        # Normalize status based on deadline
        if deadline and deadline < date.today():
            status = 'closed'

        # Extract budget
        budget = None
        budget_data = topic_data.get('budgetOverviewModel', {})
        if budget_data:
            budget = budget_data.get('budgetTopicActionValue')

        # Extract action type
        action_type = None
        action_type_data = topic_data.get('typeOfMGA', [])
        if action_type_data and isinstance(action_type_data, list) and len(action_type_data) > 0:
            action_type = action_type_data[0].get('abbreviation', '')

        return {
            'topic_code': topic_data.get('identifier', topic_code).upper(),
            'title': topic_data.get('title', ''),
            'scope': topic_data.get('description', ''),
            'expected_outcome': topic_data.get('expectedImpact', ''),
            'deadline': deadline,
            'status': status,
            'action_type': action_type,
            'budget_total': float(budget) if budget else None,
            'call_identifier': topic_data.get('callIdentifier'),
            'portal_url': f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_code.lower()}",
        }

    except httpx.TimeoutException:
        logger.warning(f"  Timeout fetching {topic_code}")
        return None
    except Exception as e:
        logger.warning(f"  Error fetching {topic_code}: {e}")
        return None


def update_call(conn, topic_code: str, data: dict[str, Any], dry_run: bool = False) -> bool:
    """Update call in database with enriched data."""
    if dry_run:
        logger.info(f"  [DRY-RUN] Would update {topic_code}:")
        logger.info(f"    deadline: {data.get('deadline')}")
        logger.info(f"    status: {data.get('status')}")
        logger.info(f"    scope: {len(data.get('scope', '') or '')} chars")
        return True

    try:
        cursor = conn.cursor()

        # Build metadata JSON properly
        enrichment_metadata = {
            "enriched_from_api": True,
            "enriched_at": datetime.now().isoformat()
        }
        metadata_json = json.dumps(enrichment_metadata)

        cursor.execute("""
            UPDATE funding_calls SET
                title = COALESCE(%s, title),
                scope = COALESCE(%s, scope),
                expected_outcome = COALESCE(%s, expected_outcome),
                deadline = COALESCE(%s, deadline),
                status = COALESCE(%s, status),
                action_type = COALESCE(%s, action_type),
                budget_total = COALESCE(%s, budget_total),
                call_identifier = COALESCE(%s, call_identifier),
                portal_url = COALESCE(%s, portal_url),
                metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb,
                updated_at = NOW()
            WHERE topic_code = %s
        """, (
            data.get('title'),
            data.get('scope'),
            data.get('expected_outcome'),
            data.get('deadline'),
            data.get('status'),
            data.get('action_type'),
            data.get('budget_total'),
            data.get('call_identifier'),
            data.get('portal_url'),
            metadata_json,
            topic_code
        ))

        conn.commit()
        return True

    except Exception as e:
        logger.error(f"  Database error updating {topic_code}: {e}")
        conn.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description='Enrich funding calls from EU Portal API')
    parser.add_argument('--limit', type=int, help='Limit number of calls to process')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t update database')
    parser.add_argument('--force', action='store_true', help='Re-fetch all calls, not just missing data')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between API calls (seconds)')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Funding Calls Enrichment Script")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")

    # Connect to database
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)

    # Get calls to enrich
    logger.info("\n📊 Finding calls that need enrichment...")
    calls = get_calls_to_enrich(conn, force=args.force, limit=args.limit)
    logger.info(f"   Found {len(calls)} calls to process")

    if not calls:
        logger.info("✅ All calls already have complete data!")
        return

    # Setup HTTP client
    client = httpx.Client(timeout=30.0)

    # Process calls
    stats = {
        'processed': 0,
        'updated': 0,
        'not_found': 0,
        'errors': 0,
        'skipped': 0
    }

    logger.info(f"\n🚀 Processing {len(calls)} calls...")
    logger.info(f"   Delay between calls: {args.delay}s")
    logger.info("")

    for i, call in enumerate(calls):
        topic_code = call['topic_code']
        stats['processed'] += 1

        # Progress indicator
        if (i + 1) % 10 == 0 or i == 0:
            logger.info(f"[{i + 1}/{len(calls)}] Processing {topic_code}...")
        else:
            logger.debug(f"[{i + 1}/{len(calls)}] Processing {topic_code}...")

        # Fetch from API
        data = fetch_from_api(topic_code, client)

        if not data:
            stats['not_found'] += 1
            continue

        # Check if we got useful data
        has_new_deadline = data.get('deadline') and not call.get('deadline')
        has_new_scope = data.get('scope') and (not call.get('scope') or len(call.get('scope', '')) < 50)
        has_new_status = data.get('status') and data.get('status') != 'unknown'

        if not (has_new_deadline or has_new_scope or has_new_status) and not args.force:
            stats['skipped'] += 1
            logger.debug("  Skipped - no new data")
            continue

        # Update database
        if update_call(conn, topic_code, data, dry_run=args.dry_run):
            stats['updated'] += 1
            if has_new_deadline:
                logger.info(f"  ✅ Updated {topic_code}: deadline={data.get('deadline')}, status={data.get('status')}")
        else:
            stats['errors'] += 1

        # Rate limiting
        if args.delay > 0:
            time.sleep(args.delay)

    # Close connections
    client.close()
    conn.close()

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📈 SUMMARY")
    logger.info("=" * 60)
    logger.info(f"   Processed:  {stats['processed']}")
    logger.info(f"   Updated:    {stats['updated']}")
    logger.info(f"   Not found:  {stats['not_found']} (not in EU Portal API)")
    logger.info(f"   Skipped:    {stats['skipped']} (no new data)")
    logger.info(f"   Errors:     {stats['errors']}")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("\n🔍 This was a DRY RUN - no changes were made")
        logger.info("   Run without --dry-run to apply changes")


if __name__ == '__main__':
    main()
