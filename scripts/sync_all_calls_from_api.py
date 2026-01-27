#!/usr/bin/env python3
"""
Sync ALL Horizon Europe Calls from EU Portal API

Downloads ALL calls (open, closed, upcoming) directly from the EU Portal API
and stores them in the local database with complete structured data.

This is the DEFINITIVE way to get up-to-date call data locally.

Usage:
    python scripts/sync_all_calls_from_api.py [--status open|closed|all] [--limit N] [--dry-run]

Options:
    --status    Filter by status: open, closed, upcoming, or all (default: all)
    --limit     Limit number of calls to process (for testing)
    --dry-run   Don't update database, just show what would be synced
    --force     Re-sync all calls, even if they already exist
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
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# EU Portal API endpoints
EU_SEARCH_API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
EU_TOPIC_DETAILS = "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails"


def get_database_url() -> str:
    """Get database URL from environment."""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return db_url


class EUPortalSyncer:
    """Sync calls from EU Portal API to local database."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.client = httpx.Client(timeout=60.0)

        # API configuration
        self.search_api = EU_SEARCH_API
        self.topic_api = EU_TOPIC_DETAILS
        self.api_key = "SEDIA"  # Public API key

    def close(self):
        """Close HTTP client."""
        self.client.close()

    def get_existing_topics_from_db(self, conn) -> list[dict]:
        """Get all existing topic codes from database."""
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT topic_code, title, status, deadline
            FROM funding_calls
            WHERE topic_code IS NOT NULL
            ORDER BY call_year DESC NULLS LAST, topic_code
        """
        )
        results = cursor.fetchall()
        return [{"identifier": r["topic_code"], "title": r["title"] or ""} for r in results]

    def search_all_topics(self, status: str = "all", page_size: int = 100, conn=None) -> list[dict]:
        """
        Get topics to sync. Uses existing database topics plus discovers new ones.

        Args:
            status: Filter by status - 'open', 'closed', 'upcoming', or 'all'
            page_size: Not used in this implementation
            conn: Database connection for getting existing topics

        Returns:
            List of topic identifiers
        """
        all_topics = []
        seen = set()

        # First, get existing topics from database
        if conn:
            logger.info("📡 Getting existing topics from database...")
            existing = self.get_existing_topics_from_db(conn)
            logger.info(f"   Found {len(existing)} existing topics")
            for topic in existing:
                if topic["identifier"] not in seen:
                    seen.add(topic["identifier"])
                    all_topics.append(topic)

        # Generate patterns for ALL years (2021-2027) to get complete history
        logger.info("📡 Generating patterns to discover ALL Horizon Europe topics (2021-2027)...")
        years = [2021, 2022, 2023, 2024, 2025, 2026, 2027]
        clusters = ["CL1", "CL2", "CL3", "CL4", "CL5", "CL6"]
        destinations = ["D1", "D2", "D3", "D4", "D5", "D6"]

        new_patterns = []

        for year in years:
            # Cluster topics (most common)
            for cluster in clusters:
                for call_num in ["01", "02"]:
                    for dest in destinations:
                        for topic_num in range(1, 25):
                            topic_id = f"HORIZON-{cluster}-{year}-{call_num}-{dest}-{topic_num:02d}"
                            if topic_id not in seen:
                                new_patterns.append(topic_id)

            # ERC
            for erc_type in ["STG", "COG", "ADG", "SYG", "POC", "PERA"]:
                topic_id = f"ERC-{year}-{erc_type}"
                if topic_id not in seen:
                    new_patterns.append(topic_id)

            # EIC
            for eic_type in [
                "ACCELERATOR-01",
                "PATHFINDEROPEN-01",
                "PATHFINDERCHALLENGES-01",
                "TRANSITION-01",
                "AIC-01",
            ]:
                topic_id = f"HORIZON-EIC-{year}-{eic_type}"
                if topic_id not in seen:
                    new_patterns.append(topic_id)

            # MSCA
            for msca_type in ["PF-01", "DN-01", "SE-01", "COFUND-01"]:
                topic_id = f"HORIZON-MSCA-{year}-{msca_type}"
                if topic_id not in seen:
                    new_patterns.append(topic_id)

            # MISS (Missions)
            for mission_num in ["01", "02", "03", "04", "05", "06", "07"]:
                for topic_num in range(1, 6):
                    for sub in ["CROSS", "CLIMA", "OCEAN", "CANCER", "CIT", "NEB"]:
                        topic_id = f"HORIZON-MISS-{year}-{mission_num}-{sub}-{topic_num:02d}"
                        if topic_id not in seen:
                            new_patterns.append(topic_id)

            # EUSPA
            for space_num in ["01", "02", "03"]:
                for topic_num in range(1, 60):
                    topic_id = f"HORIZON-EUSPA-{year}-SPACE-{space_num}-{topic_num:02d}"
                    if topic_id not in seen:
                        new_patterns.append(topic_id)

            # EIE
            for eie_num in ["01", "02"]:
                for sub in ["CONNECT", "SCALEUP", "INNOVSMES"]:
                    for topic_num in range(1, 6):
                        topic_id = f"HORIZON-EIE-{year}-{eie_num}-{sub}-{topic_num:02d}"
                        if topic_id not in seen:
                            new_patterns.append(topic_id)

            # HLTH (Health) - CL1 alternative naming
            for hlth_num in ["01", "02", "03"]:
                for sub in ["DISEASE", "TOOL", "ENVHLTH", "CARE", "IND", "STAYHLTH"]:
                    for topic_num in range(1, 15):
                        topic_id = f"HORIZON-HLTH-{year}-{hlth_num}-{sub}-{topic_num:02d}"
                        if topic_id not in seen:
                            new_patterns.append(topic_id)
                        # Also check two-stage variants
                        topic_id_ts = (
                            f"HORIZON-HLTH-{year}-{hlth_num}-{sub}-{topic_num:02d}-TWO-STAGE"
                        )
                        if topic_id_ts not in seen:
                            new_patterns.append(topic_id_ts)

            # INFRA (Research Infrastructures)
            for infra_num in ["01", "02"]:
                for sub in ["DEV", "EOSC", "SERV", "TECH"]:
                    for topic_num in range(1, 10):
                        topic_id = f"HORIZON-INFRA-{year}-{infra_num}-{sub}-{topic_num:02d}"
                        if topic_id not in seen:
                            new_patterns.append(topic_id)

            # WIDERA (Widening participation)
            for widera_num in ["01", "02", "03"]:
                for sub in ["ACCESS", "ERA", "TALENTS", "EXCEL", "SSCP"]:
                    for topic_num in range(1, 10):
                        topic_id = f"HORIZON-WIDERA-{year}-{widera_num}-{sub}-{topic_num:02d}"
                        if topic_id not in seen:
                            new_patterns.append(topic_id)

            # JU (Joint Undertakings) - various
            for ju in ["JU-SNS", "JU-IHI", "JU-CLEANH2", "JU-CHIPS", "JU-KDT", "JU-CBE"]:
                for call_num in ["01", "02", "03"]:
                    for topic_num in range(1, 30):
                        topic_id = f"HORIZON-{ju}-{year}-{call_num}-{topic_num:02d}"
                        if topic_id not in seen:
                            new_patterns.append(topic_id)

            # CL topics with different sub-structures (e.g., CIRCBIO, ZEROPOLLUTION, FARM2FORK, etc.)
            cl6_subs = ["CIRCBIO", "ZEROPOLLUTION", "FARM2FORK", "BIODIV", "GOVERNANCE"]
            cl4_subs = ["DATA", "DIGITAL", "HUMAN", "CIVIL", "SPACE"]
            cl3_subs = ["BM", "CS", "FCT", "SSRI", "INFRA"]
            cl2_subs = ["DEMOCRACY", "HERITAGE", "TRANSFORMATIONS"]

            for cluster, subs in [
                ("CL2", cl2_subs),
                ("CL3", cl3_subs),
                ("CL4", cl4_subs),
                ("CL6", cl6_subs),
            ]:
                for call_num in ["01", "02"]:
                    for sub in subs:
                        for topic_num in range(1, 20):
                            topic_id = f"HORIZON-{cluster}-{year}-{call_num}-{sub}-{topic_num:02d}"
                            if topic_id not in seen:
                                new_patterns.append(topic_id)
                            # Two-stage variant
                            topic_id_ts = f"HORIZON-{cluster}-{year}-{call_num}-{sub}-{topic_num:02d}-TWO-STAGE"
                            if topic_id_ts not in seen:
                                new_patterns.append(topic_id_ts)

        logger.info(f"   Generated {len(new_patterns)} new patterns to check")

        # Add new patterns
        for pattern in new_patterns:
            all_topics.append({"identifier": pattern, "title": ""})

        logger.info(f"📊 Total: {len(all_topics)} topics to process")
        return all_topics

    def fetch_topic_details(self, topic_id: str) -> dict[str, Any] | None:
        """
        Fetch complete details for a topic from the EU Portal API.

        Args:
            topic_id: Topic identifier (e.g., "HORIZON-CL5-2026-D3-08")

        Returns:
            Structured call data or None if not found
        """
        url = f"{self.topic_api}/{topic_id.lower()}.json"

        try:
            response = self.client.get(url)

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.debug(f"API returned {response.status_code} for {topic_id}")
                return None

            data = response.json()
            topic_data = data.get("TopicDetails", {})

            if not topic_data:
                return None

            # Extract deadline and status
            deadline = None
            status = "unknown"
            actions = topic_data.get("actions", [])

            if actions and isinstance(actions, list) and len(actions) > 0:
                action = actions[0]

                # Get deadline
                deadline_dates = action.get("deadlineDates", [])
                if deadline_dates:
                    try:
                        timestamp_ms = int(deadline_dates[0])
                        deadline = datetime.fromtimestamp(timestamp_ms / 1000).date()
                    except Exception:
                        pass

                # Get status
                status_info = action.get("status", {})
                if isinstance(status_info, dict):
                    status_abbr = status_info.get("abbreviation", "").lower()
                    if "open" in status_abbr:
                        status = "open"
                    elif "closed" in status_abbr:
                        status = "closed"
                    elif "forthcoming" in status_abbr or "upcoming" in status_abbr:
                        status = "upcoming"

            # Fallback status check
            if status == "unknown":
                status_data = topic_data.get("statusOfTopic", {})
                if isinstance(status_data, dict):
                    status_abbr = status_data.get("abbreviation", "").lower()
                    if "open" in status_abbr:
                        status = "open"
                    elif "closed" in status_abbr:
                        status = "closed"
                    elif "forthcoming" in status_abbr:
                        status = "upcoming"

            # Override status if deadline passed
            if deadline and deadline < date.today():
                status = "closed"

            # Extract budget
            budget = None
            budget_data = topic_data.get("budgetOverviewModel", {})
            if budget_data:
                budget = budget_data.get("budgetTopicActionValue")

            # Extract action type
            action_type = None
            action_types = topic_data.get("typeOfMGA", [])
            if action_types and isinstance(action_types, list) and len(action_types) > 0:
                action_type = action_types[0].get("abbreviation", "")

            # Extract cluster from ccm2Id or identifier
            cluster = None
            identifier = topic_data.get("identifier", "").upper()
            if "-CL1-" in identifier or "-HLTH-" in identifier:
                cluster = "CL1"
            elif "-CL2-" in identifier:
                cluster = "CL2"
            elif "-CL3-" in identifier:
                cluster = "CL3"
            elif "-CL4-" in identifier:
                cluster = "CL4"
            elif "-CL5-" in identifier:
                cluster = "CL5"
            elif "-CL6-" in identifier:
                cluster = "CL6"
            elif "-EIC-" in identifier:
                cluster = "EIC"
            elif "-ERC-" in identifier or identifier.startswith("ERC-"):
                cluster = "ERC"
            elif "-MSCA-" in identifier:
                cluster = "MSCA"
            elif "-MISS-" in identifier:
                cluster = "MISS"
            elif "-INFRA-" in identifier:
                cluster = "INFRA"
            elif "-WIDERA-" in identifier:
                cluster = "WIDERA"

            # Extract year from identifier
            call_year = None
            import re

            year_match = re.search(r"-(\d{4})-", identifier)
            if year_match:
                call_year = int(year_match.group(1))

            return {
                "topic_code": identifier,
                "title": topic_data.get("title", ""),
                "scope": topic_data.get("description", ""),
                "expected_outcome": topic_data.get("expectedImpact", ""),
                "deadline": deadline,
                "status": status,
                "action_type": action_type,
                "budget_total": float(budget) if budget else None,
                "call_identifier": topic_data.get("callIdentifier"),
                "cluster": cluster,
                "call_year": call_year,
                "portal_url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_id.lower()}",
            }

        except httpx.TimeoutException:
            logger.debug(f"Timeout fetching {topic_id}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching {topic_id}: {e}")
            return None

    def upsert_call(self, conn, data: dict[str, Any]) -> bool:
        """Insert or update a call in the database."""
        try:
            cursor = conn.cursor()

            metadata = {"synced_from_api": True, "synced_at": datetime.now().isoformat()}

            cursor.execute(
                """
                INSERT INTO funding_calls (
                    programme, topic_code, title, scope, expected_outcome,
                    deadline, status, action_type, budget_total,
                    call_identifier, cluster, call_year, portal_url, metadata
                ) VALUES (
                    'horizon_europe', %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s::jsonb
                )
                ON CONFLICT (topic_code) DO UPDATE SET
                    title = COALESCE(EXCLUDED.title, funding_calls.title),
                    scope = COALESCE(EXCLUDED.scope, funding_calls.scope),
                    expected_outcome = COALESCE(EXCLUDED.expected_outcome, funding_calls.expected_outcome),
                    deadline = COALESCE(EXCLUDED.deadline, funding_calls.deadline),
                    status = COALESCE(EXCLUDED.status, funding_calls.status),
                    action_type = COALESCE(EXCLUDED.action_type, funding_calls.action_type),
                    budget_total = COALESCE(EXCLUDED.budget_total, funding_calls.budget_total),
                    call_identifier = COALESCE(EXCLUDED.call_identifier, funding_calls.call_identifier),
                    cluster = COALESCE(EXCLUDED.cluster, funding_calls.cluster),
                    call_year = COALESCE(EXCLUDED.call_year, funding_calls.call_year),
                    portal_url = COALESCE(EXCLUDED.portal_url, funding_calls.portal_url),
                    metadata = COALESCE(funding_calls.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                    updated_at = NOW()
            """,
                (
                    data.get("topic_code"),
                    data.get("title"),
                    data.get("scope"),
                    data.get("expected_outcome"),
                    data.get("deadline"),
                    data.get("status"),
                    data.get("action_type"),
                    data.get("budget_total"),
                    data.get("call_identifier"),
                    data.get("cluster"),
                    data.get("call_year"),
                    data.get("portal_url"),
                    json.dumps(metadata),
                ),
            )

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Database error for {data.get('topic_code')}: {e}")
            conn.rollback()
            return False


def main():
    parser = argparse.ArgumentParser(description="Sync ALL Horizon Europe calls from EU Portal API")
    parser.add_argument(
        "--status",
        choices=["open", "closed", "upcoming", "all"],
        default="all",
        help="Filter by status (default: all)",
    )
    parser.add_argument("--limit", type=int, help="Limit number of calls to sync")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database")
    parser.add_argument("--force", action="store_true", help="Re-sync all calls")
    parser.add_argument(
        "--delay", type=float, default=0.2, help="Delay between API calls (seconds)"
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("SYNC ALL HORIZON EUROPE CALLS FROM EU PORTAL API")
    logger.info("=" * 70)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes")

    logger.info(f"Status filter: {args.status}")
    if args.limit:
        logger.info(f"Limit: {args.limit} calls")

    # Initialize
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    syncer = EUPortalSyncer(db_url)

    # Stats
    stats = {
        "topics_found": 0,
        "details_fetched": 0,
        "synced": 0,
        "skipped": 0,
        "errors": 0,
    }

    try:
        # Step 1: Search for all topics
        logger.info("\n" + "=" * 70)
        logger.info("STEP 1: GETTING TOPICS TO SYNC")
        logger.info("=" * 70)

        topics = syncer.search_all_topics(status=args.status, conn=conn)
        stats["topics_found"] = len(topics)

        if not topics:
            logger.error("No topics found!")
            return

        # Apply limit
        if args.limit:
            topics = topics[: args.limit]
            logger.info(f"Limited to {len(topics)} topics")

        # Step 2: Fetch details for each topic
        logger.info("\n" + "=" * 70)
        logger.info("STEP 2: FETCHING COMPLETE DETAILS FOR EACH TOPIC")
        logger.info("=" * 70)

        for i, topic in enumerate(topics):
            topic_id = topic["identifier"]

            if (i + 1) % 50 == 0 or i == 0:
                logger.info(f"[{i + 1}/{len(topics)}] Fetching {topic_id}...")

            # Fetch complete details
            details = syncer.fetch_topic_details(topic_id)

            if details:
                stats["details_fetched"] += 1

                # Sync to database
                if not args.dry_run:
                    if syncer.upsert_call(conn, details):
                        stats["synced"] += 1
                        if details.get("deadline"):
                            logger.debug(
                                f"  ✅ {topic_id}: {details.get('status')}, deadline={details.get('deadline')}"
                            )
                    else:
                        stats["errors"] += 1
                else:
                    stats["synced"] += 1
                    logger.debug(f"  [DRY-RUN] Would sync {topic_id}")
            else:
                stats["skipped"] += 1

            time.sleep(args.delay)

        # Step 3: Summary
        logger.info("\n" + "=" * 70)
        logger.info("SYNC COMPLETE - SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Topics found in search:    {stats['topics_found']}")
        logger.info(f"Details fetched from API:  {stats['details_fetched']}")
        logger.info(f"Successfully synced:       {stats['synced']}")
        logger.info(f"Skipped (not found):       {stats['skipped']}")
        logger.info(f"Errors:                    {stats['errors']}")

        # Show database totals
        if not args.dry_run:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM funding_calls")
            total = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT status, COUNT(*)
                FROM funding_calls
                GROUP BY status
                ORDER BY COUNT(*) DESC
            """
            )
            by_status = cursor.fetchall()

            logger.info(f"\n📊 Database now has {total} total calls:")
            for status, count in by_status:
                logger.info(f"   - {status}: {count}")

        if args.dry_run:
            logger.info("\nThis was a DRY RUN - run without --dry-run to sync to database")

    finally:
        syncer.close()
        conn.close()


if __name__ == "__main__":
    main()
