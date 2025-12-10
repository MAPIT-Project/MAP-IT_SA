#!/usr/bin/env python3
"""
Batch Enrich and Cleanup Funding Calls

This script performs comprehensive cleanup and enrichment of funding calls:
1. Identifies calls with invalid/incomplete topic codes
2. Removes or flags calls that can't be found in the EU Portal API
3. Enriches valid calls with complete data (title, scope, deadline, status)
4. Cleans up garbled titles from PDF extraction issues

Usage:
    python scripts/batch_enrich_and_cleanup_calls.py [--dry-run] [--limit N]

Options:
    --dry-run    Show what would be done without making changes
    --limit N    Only process N calls (for testing)
    --force      Re-fetch all calls, even those with complete data
    --cleanup    Remove calls that can't be found in API (use with caution)
    --verbose    Show detailed progress
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

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


def is_valid_topic_code(topic_code: str) -> Tuple[bool, str]:
    """
    Check if a topic code is valid and complete.

    Returns:
        Tuple of (is_valid, reason)
    """
    if not topic_code:
        return False, "Empty topic code"

    # Check for trailing dash (incomplete code)
    if topic_code.endswith('-'):
        return False, "Incomplete code (trailing dash)"

    # Check for minimum length
    if len(topic_code) < 15:
        return False, "Code too short"

    # Check for valid prefix
    valid_prefixes = ['HORIZON-', 'ERC-', 'EIC-', 'MSCA-']
    has_valid_prefix = any(topic_code.upper().startswith(p) for p in valid_prefixes)
    if not has_valid_prefix:
        return False, "Invalid prefix"

    # Check for year (should have 4-digit year)
    year_match = re.search(r'-(\d{4})-', topic_code)
    if not year_match:
        return False, "No year found in code"

    year = int(year_match.group(1))
    if year < 2021 or year > 2030:
        return False, f"Invalid year: {year}"

    return True, "Valid"


def is_garbled_title(title: str) -> bool:
    """Check if a title appears to be garbled from PDF extraction."""
    if not title:
        return True

    # Check for common garbled patterns
    garbled_patterns = [
        r'^Overview of this call',
        r'^Topics Type Budgets',
        r'^Proposals are invited',
        r'^\d+\s+Proposals',
        r'^EUR\s+million',
        r'^\s*\d+\.\d+\s*$',  # Just numbers
        r'^The Director-General',
        r'^Legal and financial',
    ]

    for pattern in garbled_patterns:
        if re.match(pattern, title, re.IGNORECASE):
            return True

    # Title is same as topic code
    if title.upper().startswith('HORIZON-') and '-' in title and len(title) < 40:
        return True

    return False


def needs_enrichment(call: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if a call needs enrichment and why.

    Returns:
        Tuple of (needs_enrichment, list of reasons)
    """
    reasons = []

    # Check topic code validity
    is_valid, validity_reason = is_valid_topic_code(call.get('topic_code', ''))
    if not is_valid:
        reasons.append(f"Invalid topic code: {validity_reason}")

    # Check title
    title = call.get('title', '')
    if not title or len(title) < 10:
        reasons.append("Missing or short title")
    elif is_garbled_title(title):
        reasons.append("Garbled title")

    # Check deadline
    if not call.get('deadline'):
        reasons.append("Missing deadline")

    # Check scope
    scope = call.get('scope', '') or ''
    if len(scope) < 50:
        reasons.append("Missing or short scope")

    # Check status
    if not call.get('status') or call.get('status') == 'unknown':
        reasons.append("Missing status")

    return len(reasons) > 0, reasons


def fetch_from_api(topic_code: str, client: httpx.Client) -> Optional[Dict[str, Any]]:
    """Fetch call details from EU Portal API."""
    # API requires lowercase topic codes
    url = f"{EU_PORTAL_TOPIC_DETAILS}/{topic_code.lower()}.json"

    try:
        response = client.get(url)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            logger.debug(f"  API returned {response.status_code} for {topic_code}")
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
                except Exception:
                    pass

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
        logger.debug(f"  Timeout fetching {topic_code}")
        return None
    except Exception as e:
        logger.debug(f"  Error fetching {topic_code}: {e}")
        return None


def update_call(conn, topic_code: str, data: Dict[str, Any], dry_run: bool = False) -> bool:
    """Update call in database with enriched data."""
    if dry_run:
        return True

    try:
        cursor = conn.cursor()

        enrichment_metadata = {
            "enriched_from_api": True,
            "enriched_at": datetime.now().isoformat(),
            "batch_cleanup": True
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


def delete_call(conn, topic_code: str, dry_run: bool = False) -> bool:
    """Delete invalid call from database."""
    if dry_run:
        return True

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM funding_calls WHERE topic_code = %s", (topic_code,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"  Database error deleting {topic_code}: {e}")
        conn.rollback()
        return False


def get_all_calls(conn, force: bool = False, limit: Optional[int] = None) -> List[Dict]:
    """Get all calls from database."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT topic_code, title, status, deadline, scope, action_type, expected_outcome
        FROM funding_calls
        WHERE topic_code IS NOT NULL
        ORDER BY call_year DESC NULLS LAST, topic_code
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    return cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description='Batch enrich and cleanup funding calls')
    parser.add_argument('--limit', type=int, help='Limit number of calls to process')
    parser.add_argument('--dry-run', action='store_true', help='Don\'t update database')
    parser.add_argument('--force', action='store_true', help='Re-fetch all calls')
    parser.add_argument('--cleanup', action='store_true', help='Remove invalid calls not found in API')
    parser.add_argument('--verbose', action='store_true', help='Show detailed progress')
    parser.add_argument('--delay', type=float, default=0.3, help='Delay between API calls (seconds)')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 70)
    logger.info("BATCH FUNDING CALLS ENRICHMENT AND CLEANUP")
    logger.info("=" * 70)

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    if args.cleanup:
        logger.info("CLEANUP MODE - Invalid calls will be removed")

    # Connect to database
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)

    # Get all calls
    logger.info("\nFetching calls from database...")
    calls = get_all_calls(conn, force=args.force, limit=args.limit)
    logger.info(f"Found {len(calls)} calls to analyze")

    # Setup HTTP client
    client = httpx.Client(timeout=30.0)

    # Statistics
    stats = {
        'total': len(calls),
        'valid_no_enrichment': 0,
        'enriched': 0,
        'not_found_in_api': 0,
        'deleted': 0,
        'invalid_code': 0,
        'errors': 0,
    }

    # Categorize calls
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 1: ANALYZING CALLS")
    logger.info("=" * 70)

    calls_to_enrich = []
    invalid_calls = []

    for call in calls:
        topic_code = call['topic_code']

        # Check if topic code is valid
        is_valid, validity_reason = is_valid_topic_code(topic_code)

        if not is_valid:
            invalid_calls.append((call, validity_reason))
            stats['invalid_code'] += 1
            continue

        # Check if needs enrichment
        needs_enrich, reasons = needs_enrichment(call)

        if needs_enrich or args.force:
            calls_to_enrich.append((call, reasons))
        else:
            stats['valid_no_enrichment'] += 1

    logger.info(f"\nAnalysis complete:")
    logger.info(f"  - Valid, complete: {stats['valid_no_enrichment']}")
    logger.info(f"  - Needs enrichment: {len(calls_to_enrich)}")
    logger.info(f"  - Invalid topic code: {len(invalid_calls)}")

    # Show sample of invalid calls
    if invalid_calls and args.verbose:
        logger.info("\nSample invalid calls:")
        for call, reason in invalid_calls[:5]:
            logger.info(f"  - {call['topic_code']}: {reason}")

    # Phase 2: Handle invalid calls
    if invalid_calls:
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 2: HANDLING INVALID TOPIC CODES")
        logger.info("=" * 70)

        for call, reason in invalid_calls:
            topic_code = call['topic_code']

            # Try to find in API anyway (maybe we can fix the code)
            api_data = fetch_from_api(topic_code, client)

            if api_data:
                # API found it! Update with correct data
                logger.info(f"  {topic_code}: Found in API despite invalid code - updating")
                if update_call(conn, topic_code, api_data, args.dry_run):
                    stats['enriched'] += 1
            elif args.cleanup:
                # Not in API and cleanup mode - delete
                logger.info(f"  {topic_code}: Not in API, deleting ({reason})")
                if delete_call(conn, topic_code, args.dry_run):
                    stats['deleted'] += 1
            else:
                logger.debug(f"  {topic_code}: Invalid and not in API ({reason})")
                stats['not_found_in_api'] += 1

            time.sleep(args.delay)

    # Phase 3: Enrich valid calls
    if calls_to_enrich:
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 3: ENRICHING CALLS FROM EU PORTAL API")
        logger.info("=" * 70)
        logger.info(f"Processing {len(calls_to_enrich)} calls...")

        for i, (call, reasons) in enumerate(calls_to_enrich):
            topic_code = call['topic_code']

            if (i + 1) % 20 == 0 or i == 0:
                logger.info(f"[{i + 1}/{len(calls_to_enrich)}] Processing {topic_code}...")

            # Fetch from API
            api_data = fetch_from_api(topic_code, client)

            if api_data:
                # Check what we got
                got_title = bool(api_data.get('title'))
                got_deadline = bool(api_data.get('deadline'))
                got_scope = bool(api_data.get('scope'))

                if args.verbose:
                    logger.debug(f"  Got: title={got_title}, deadline={got_deadline}, scope={len(api_data.get('scope', '') or '')}")

                if update_call(conn, topic_code, api_data, args.dry_run):
                    stats['enriched'] += 1
                    if got_deadline:
                        logger.info(f"  {topic_code}: Enriched (deadline={api_data.get('deadline')}, status={api_data.get('status')})")
                else:
                    stats['errors'] += 1
            else:
                stats['not_found_in_api'] += 1
                if args.verbose:
                    logger.debug(f"  {topic_code}: Not found in API")

            time.sleep(args.delay)

    # Close connections
    client.close()
    conn.close()

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total calls analyzed:     {stats['total']}")
    logger.info(f"Already complete:         {stats['valid_no_enrichment']}")
    logger.info(f"Successfully enriched:    {stats['enriched']}")
    logger.info(f"Not found in EU Portal:   {stats['not_found_in_api']}")
    logger.info(f"Invalid codes:            {stats['invalid_code']}")
    if args.cleanup:
        logger.info(f"Deleted (cleanup):        {stats['deleted']}")
    logger.info(f"Errors:                   {stats['errors']}")
    logger.info("=" * 70)

    if args.dry_run:
        logger.info("\nThis was a DRY RUN - no changes were made")
        logger.info("Run without --dry-run to apply changes")


if __name__ == '__main__':
    main()
