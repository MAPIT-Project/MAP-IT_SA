#!/usr/bin/env python3
"""
Sync Erasmus+ Calls from EU Portal API

Downloads all Erasmus+ calls (open, closed, upcoming) from the EU Portal API
and stores them in the local database with complete structured data.

This mirrors the Horizon Europe sync script but uses Erasmus+ topic patterns.

Usage:
    python scripts/sync_erasmus_calls_from_api.py [--status open|closed|all] [--limit N] [--dry-run]

Options:
    --status    Filter by status: open, closed, upcoming, or all (default: all)
    --limit     Limit number of calls to process (for testing)
    --dry-run   Don't update database, just show what would be synced
    --force     Re-sync all calls, even if they already exist
    --year      Specific year to sync (e.g., 2025, 2026)
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# EU Portal API endpoints (same as Horizon Europe)
EU_SEARCH_API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
EU_TOPIC_DETAILS = "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails"


def get_database_url() -> str:
    """Get database URL from environment."""
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return db_url


class ErasmusPlusPortalSyncer:
    """Sync Erasmus+ calls from EU Portal API to local database."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.client = httpx.Client(timeout=60.0)
        self.search_api = EU_SEARCH_API
        self.topic_api = EU_TOPIC_DETAILS
        self.api_key = "SEDIA"  # Public API key

        # Erasmus+ action type mappings (from ErasmusPlusExtractor)
        self.action_types = {
            'KA1-HED': 'Higher Education Mobility',
            'KA1-VET': 'VET Learners and Staff Mobility',
            'KA1-SCH': 'School Education Staff Mobility',
            'KA1-ADU': 'Adult Education Staff Mobility',
            'KA1-YOU': 'Youth Mobility',
            'KA1-DEGREE': 'Joint Master Degree',
            'KA1-ICM': 'International Credit Mobility',
            'KA2-COOP': 'Cooperation Partnership',
            'KA2-SSP': 'Small-Scale Partnership',
            'KA2-CBHE': 'Capacity Building Higher Education',
            'KA2-ALLIANCES': 'Alliances for Innovation',
            'KA2-COE': 'Centres of Vocational Excellence',
            'KA3-INC-SOC': 'Social Inclusion',
            'KA3-YOUTH-TOG': 'Youth Together',
            'JMO-MODULE': 'Jean Monnet Module',
            'JMO-CHAIR': 'Jean Monnet Chair',
            'SPORT-COOP': 'Cooperation Partnership Sport',
            'SPORT-SSCP': 'Small-Scale Partnership Sport',
        }

        # Sector mappings
        self.sectors = {
            'HED': 'Higher Education',
            'VET': 'Vocational Education and Training',
            'SCH': 'School Education',
            'ADU': 'Adult Education',
            'YOU': 'Youth',
            'SPORT': 'Sport',
        }

    def close(self):
        """Close HTTP client."""
        self.client.close()

    def get_existing_topics_from_db(self, conn) -> list[dict]:
        """Get all existing Erasmus+ topic codes from database."""
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT topic_code, title, status, deadline
            FROM funding_calls
            WHERE programme = 'erasmus'
              AND topic_code IS NOT NULL
            ORDER BY call_year DESC NULLS LAST, topic_code
        """)
        results = cursor.fetchall()
        return [{"identifier": r["topic_code"], "title": r["title"] or ""} for r in results]

    def generate_topic_patterns(self, years: list[int]) -> list[str]:
        """
        Generate all possible Erasmus+ topic code patterns.

        Erasmus+ topic codes follow the pattern:
        ERASMUS-{DOMAIN}-{YEAR}-{ACTION}

        Domains: EDU, SPORT, JMO, YOUTH

        Based on discovered patterns from EU Portal API.
        """
        patterns = []

        for year in years:
            # Education patterns (EDU domain)
            edu_patterns = [
                # Capacity Building
                'CBHE', 'CBHE-STRAND-1', 'CBHE-STRAND-2', 'CBHE-STRAND-3',
                'CBVET', 'CB-VET',
                # Centres of Excellence & Alliances
                'COE', 'PI-COVE', 'PI-ALLIANCES', 'ALLIANCES',
                # Forward Looking & Teacher Academies
                'FORWARD', 'TEACHER-ACADEMIES', 'TEACH-ACAD',
                # Virtual Exchanges
                'VIRT-EXCH', 'VIRTUAL-EXCHANGES',
                # Policy & Experimental
                'POL-EXP', 'POL-EXP-EU', 'POL-NET',
                # Accreditation & Mobility
                'AM', 'AM-EB', 'AM-EB-MU', 'KA131-HE', 'KA171-HE',
                # Cooperation Partnerships (various sectors)
                'KA220-HED', 'KA220-VET', 'KA220-SCH', 'KA220-ADU', 'KA220-YOU',
                'KA210-HED', 'KA210-VET', 'KA210-SCH', 'KA210-ADU', 'KA210-YOU',
                # PPI and CSA
                'PPI', 'CSA', 'CSAI', 'RSC',
                # Innovet & Platforms
                'INNOVET', 'PLATFORM',
                # European Universities
                'EUR-UNIV', 'EU-UNIV', 'EUROPEAN-UNIVERSITIES',
                # Digital Education
                'DIGITAL', 'DIG-ED',
                # Inclusion & Social
                'INC-SOC', 'INCL',
            ]

            for action in edu_patterns:
                patterns.append(f"ERASMUS-EDU-{year}-{action}")

            # Sport patterns
            sport_patterns = [
                'SCP',           # Cooperation Partnerships (main pattern)
                'SSCP',          # Small-scale Partnerships
                'NFPE', 'NPE',   # Non-profit Events
                'COOP', 'COOP-PART',
                'BE-ACTIVE', 'BEACTIVE',
                'EWS', 'EWOS',   # European Week of Sport
            ]

            for action in sport_patterns:
                patterns.append(f"ERASMUS-SPORT-{year}-{action}")

            # Jean Monnet patterns
            jmo_patterns = [
                'MODULE',        # JM Modules
                'CHAIR',         # JM Chairs
                'COE',           # JM Centres of Excellence
                'NETWORKS', 'NETWORK',
                'PROJECT', 'PROJECTS',
                'OFET-HEI', 'OFET',
                'LEARN-EU', 'LEARNING-EU',
                'POLICY-DEBATE', 'POL-DEB',
                'TEACHER-TRAINING', 'TT',
            ]

            for action in jmo_patterns:
                patterns.append(f"ERASMUS-JMO-{year}-{action}")

            # Youth patterns
            youth_patterns = [
                'YOUTH-TOG', 'YOUTH-TOGETHER',
                'YOUTH-PART', 'YOUTH-PARTICIPATION',
                'DISCO', 'DISCOVEREU',
                'SOLIDARITY',
                'PART-NGO', 'ACCR-NGO',
                'EYD', 'EU-YOUTH-DIALOGUE',
                'CB-YOUTH', 'CAPACITY-BUILDING',
            ]

            for action in youth_patterns:
                patterns.append(f"ERASMUS-YOUTH-{year}-{action}")

        return patterns

    def discover_topics_via_search_api(self) -> set:
        """
        Discover actual Erasmus+ topic codes via EU Portal Search API.

        This approach is much more reliable than pattern generation because
        it finds real topic codes that exist in the EU Portal.

        Returns:
            Set of discovered topic codes
        """
        discovered = set()
        search_terms = [
            'ERASMUS-EDU', 'ERASMUS-SPORT', 'ERASMUS-JMO', 'ERASMUS-YOUTH'
        ]

        logger.info("Discovering Erasmus+ topics via Search API...")

        for term in search_terms:
            logger.info(f"  Searching for: {term}")

            for page in range(1, 10):  # Up to 9 pages per term
                try:
                    payload = {
                        'apiKey': self.api_key,
                        'text': term,
                        'pageSize': 100,
                        'pageNumber': page,
                    }

                    response = self.client.post(
                        self.search_api,
                        data=payload,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    )

                    if response.status_code != 200:
                        break

                    data = response.json()
                    results = data.get('results', [])

                    if not results:
                        break

                    for result in results:
                        source = str(result.get('source', ''))
                        # Extract topic codes using regex
                        matches = re.findall(
                            r'ERASMUS-(?:EDU|SPORT|JMO|YOUTH)-\d{4}-[A-Z0-9-]+',
                            source.upper()
                        )
                        for m in matches:
                            # Clean up any trailing timestamps
                            clean = re.sub(r'\d{13,}.*', '', m).rstrip('-')
                            if clean and len(clean) > 15:  # Valid topic codes
                                discovered.add(clean)

                    time.sleep(0.2)  # Rate limiting

                except Exception as e:
                    logger.debug(f"Search error for {term} page {page}: {e}")
                    break

        logger.info(f"  Discovered {len(discovered)} unique topics via Search API")
        return discovered

    def search_all_topics(
        self,
        status: str = "all",
        conn=None,
        years: list[int] | None = None
    ) -> list[dict]:
        """
        Get all Erasmus+ topics to sync using hybrid approach:
        1. Discover topics via EU Portal Search API (most reliable)
        2. Add existing topics from database
        3. Generate additional patterns for coverage

        Args:
            status: Filter by status (not used for pattern generation)
            conn: Database connection for existing topics
            years: Years to sync (default: 2024-2027)

        Returns:
            List of topic identifiers
        """
        all_topics = []
        seen = set()

        # Default years for Erasmus+ 2021-2027 programme
        if years is None:
            years = [2024, 2025, 2026, 2027]

        # Step 1: Discover topics via Search API (most reliable)
        discovered = self.discover_topics_via_search_api()
        for topic_code in discovered:
            if topic_code not in seen:
                seen.add(topic_code)
                all_topics.append({"identifier": topic_code, "title": ""})
        logger.info(f"Added {len(discovered)} topics from Search API discovery")

        # Step 2: Get existing topics from database
        if conn:
            logger.info("Getting existing Erasmus+ topics from database...")
            existing = self.get_existing_topics_from_db(conn)
            logger.info(f"  Found {len(existing)} existing topics")
            for topic in existing:
                if topic["identifier"] not in seen:
                    seen.add(topic["identifier"])
                    all_topics.append(topic)

        # Step 3: Generate patterns for additional coverage
        logger.info(f"Generating Erasmus+ topic patterns for years {years}...")
        patterns = self.generate_topic_patterns(years)
        new_patterns = 0
        for pattern in patterns:
            if pattern not in seen:
                seen.add(pattern)
                all_topics.append({"identifier": pattern, "title": ""})
                new_patterns += 1
        logger.info(f"  Added {new_patterns} new patterns from generation")

        logger.info(f"Total: {len(all_topics)} unique topics to process")
        return all_topics

    def fetch_topic_details(self, topic_id: str) -> dict[str, Any] | None:
        """
        Fetch complete details for an Erasmus+ topic from the EU Portal API.

        Args:
            topic_id: Topic identifier (e.g., "ERASMUS-EDU-2025-KA1-HED-DEGREE")

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
            status = 'unknown'
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

            # Extract action type from topic code
            identifier = topic_data.get("identifier", "").upper()
            action_type = self._extract_action_type(identifier)

            # Extract sector (using cluster field)
            sector = self._extract_sector(identifier)

            # Extract key action
            key_action = self._extract_key_action(identifier)

            # Extract year from topic code
            call_year = None
            year_match = re.search(r'-(\d{4})-', identifier)
            if year_match:
                call_year = int(year_match.group(1))

            return {
                "programme": "erasmus",  # Must match DB constraint
                "topic_code": identifier,
                "title": topic_data.get("title", ""),
                "scope": topic_data.get("description", ""),
                "expected_outcome": topic_data.get("expectedImpact", ""),
                "deadline": deadline,
                "status": status,
                "action_type": action_type,
                "budget_total": float(budget) if budget else None,
                "call_identifier": topic_data.get("callIdentifier"),
                "cluster": sector,  # Using cluster field for sector
                "call_year": call_year,
                "portal_url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_id.lower()}",
                "metadata": {
                    "key_action": key_action,
                    "sector": sector,
                    "funding_model": "lump_sum",
                    "synced_from_api": True,
                    "synced_at": datetime.now().isoformat()
                }
            }

        except httpx.TimeoutException:
            logger.debug(f"Timeout fetching {topic_id}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching {topic_id}: {e}")
            return None

    def _extract_action_type(self, topic_code: str) -> str | None:
        """Extract action type from Erasmus+ topic code."""
        topic_upper = topic_code.upper()

        # Match known action types
        for action_code in self.action_types.keys():
            action_parts = action_code.replace('-', '')
            if action_parts in topic_upper.replace('-', ''):
                return action_code

        # Try to construct from parts
        if 'KA1' in topic_upper:
            for sector in ['HED', 'VET', 'SCH', 'ADU', 'YOU']:
                if sector in topic_upper:
                    return f"KA1-{sector}"
            return 'KA1'
        elif 'KA2' in topic_upper:
            if 'COOP' in topic_upper:
                return 'KA2-COOP'
            elif 'SSP' in topic_upper:
                return 'KA2-SSP'
            return 'KA2'
        elif 'KA3' in topic_upper:
            return 'KA3'
        elif 'JMO' in topic_upper:
            if 'MODULE' in topic_upper:
                return 'JMO-MODULE'
            elif 'CHAIR' in topic_upper:
                return 'JMO-CHAIR'
            return 'JMO'
        elif 'SPORT' in topic_upper:
            if 'COOP' in topic_upper:
                return 'SPORT-COOP'
            elif 'SSCP' in topic_upper:
                return 'SPORT-SSCP'
            return 'SPORT'

        return None

    def _extract_sector(self, topic_code: str) -> str | None:
        """Extract sector from topic code."""
        topic_upper = topic_code.upper()
        for sector_code in self.sectors.keys():
            if sector_code in topic_upper:
                return sector_code
        if 'SPORT' in topic_upper:
            return 'SPORT'
        return None

    def _extract_key_action(self, topic_code: str) -> str | None:
        """Extract key action from topic code."""
        topic_upper = topic_code.upper()
        if 'KA1' in topic_upper:
            return 'KA1'
        elif 'KA2' in topic_upper:
            return 'KA2'
        elif 'KA3' in topic_upper:
            return 'KA3'
        elif 'JMO' in topic_upper:
            return 'JMO'
        elif 'SPORT' in topic_upper:
            return 'SPORT'
        return None

    def upsert_call(self, conn, data: dict[str, Any]) -> bool:
        """Insert or update an Erasmus+ call in the database."""
        try:
            cursor = conn.cursor()

            metadata = data.get("metadata", {})
            metadata["synced_from_api"] = True
            metadata["synced_at"] = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO funding_calls (
                    programme, topic_code, title, scope, expected_outcome,
                    deadline, status, action_type, budget_total,
                    call_identifier, cluster, call_year, portal_url, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s::jsonb
                )
                ON CONFLICT (topic_code) DO UPDATE SET
                    programme = EXCLUDED.programme,
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
            """, (
                data.get("programme", "erasmus"),
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
                json.dumps(metadata)
            ))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Database error for {data.get('topic_code')}: {e}")
            conn.rollback()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Sync Erasmus+ calls from EU Portal API"
    )
    parser.add_argument(
        "--status",
        choices=["open", "closed", "upcoming", "all"],
        default="all",
        help="Filter by status (default: all)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of calls to sync"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't update database"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-sync all calls"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Delay between API calls (seconds)"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Specific year to sync"
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("SYNC ERASMUS+ CALLS FROM EU PORTAL API")
    logger.info("=" * 70)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes")

    logger.info(f"Status filter: {args.status}")
    if args.limit:
        logger.info(f"Limit: {args.limit} calls")

    # Initialize
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    syncer = ErasmusPlusPortalSyncer(db_url)

    # Years to sync
    years = [args.year] if args.year else [2024, 2025, 2026, 2027]

    # Stats
    stats = {
        "topics_found": 0,
        "details_fetched": 0,
        "synced": 0,
        "skipped": 0,
        "errors": 0,
    }

    try:
        # Step 1: Get topics to sync
        logger.info("\n" + "=" * 70)
        logger.info("STEP 1: GETTING TOPICS TO SYNC")
        logger.info("=" * 70)

        topics = syncer.search_all_topics(
            status=args.status,
            conn=conn,
            years=years
        )
        stats["topics_found"] = len(topics)

        if not topics:
            logger.error("No topics found!")
            return

        # Apply limit
        if args.limit:
            topics = topics[:args.limit]
            logger.info(f"Limited to {len(topics)} topics")

        # Step 2: Fetch details for each topic
        logger.info("\n" + "=" * 70)
        logger.info("STEP 2: FETCHING DETAILS FROM API")
        logger.info("=" * 70)

        for i, topic in enumerate(topics):
            topic_id = topic["identifier"]

            if (i + 1) % 25 == 0 or i == 0:
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
                                f"  {topic_id}: {details.get('status')}, "
                                f"deadline={details.get('deadline')}"
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
        logger.info(f"Topics found in patterns:  {stats['topics_found']}")
        logger.info(f"Details fetched from API:  {stats['details_fetched']}")
        logger.info(f"Successfully synced:       {stats['synced']}")
        logger.info(f"Skipped (not found):       {stats['skipped']}")
        logger.info(f"Errors:                    {stats['errors']}")

        # Show database totals
        if not args.dry_run:
            cursor = conn.cursor()

            # Total Erasmus+ calls
            cursor.execute("""
                SELECT COUNT(*)
                FROM funding_calls
                WHERE programme = 'erasmus'
            """)
            total = cursor.fetchone()[0]

            # By status
            cursor.execute("""
                SELECT status, COUNT(*)
                FROM funding_calls
                WHERE programme = 'erasmus'
                GROUP BY status
                ORDER BY COUNT(*) DESC
            """)
            by_status = cursor.fetchall()

            # By sector
            cursor.execute("""
                SELECT cluster, COUNT(*)
                FROM funding_calls
                WHERE programme = 'erasmus'
                GROUP BY cluster
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            by_sector = cursor.fetchall()

            logger.info(f"\nDatabase now has {total} Erasmus+ calls:")
            logger.info("\nBy status:")
            for status, count in by_status:
                logger.info(f"   - {status or 'unknown'}: {count}")

            logger.info("\nBy sector:")
            for sector, count in by_sector:
                logger.info(f"   - {sector or 'unknown'}: {count}")

        if args.dry_run:
            logger.info("\nThis was a DRY RUN - run without --dry-run to sync to database")

    finally:
        syncer.close()
        conn.close()


if __name__ == "__main__":
    main()
