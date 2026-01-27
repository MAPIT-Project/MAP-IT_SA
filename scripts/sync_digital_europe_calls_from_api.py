#!/usr/bin/env python3
"""
Sync Digital Europe funding calls from EU Portal API.

Fetches Digital Europe call topics from the EU Funding & Tenders Portal API
and syncs them to the local funding_calls table.

Topic code patterns for Digital Europe:
- DIGITAL-{YEAR}-{THEMATIC}-{WP_NUM}-{TOPIC}
- DIGITAL-ECCC-{YEAR}-DEPLOY-CYBER-{WP_NUM}-{TOPIC} (Cybersecurity)

Thematic areas: AI, SKILLS, BESTUSE, EDIH, CLOUD, DATA, CHIPS, ECCC

Usage:
    python scripts/sync_digital_europe_calls_from_api.py [--dry-run] [--years 2024,2025,2026]
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DigitalEuropeCallSyncer:
    """Syncs Digital Europe calls from EU Portal API."""

    # EU Portal API endpoints
    TOPIC_DETAILS_URL = (
        "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails/{topic_id}.json"
    )
    SEARCH_API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"

    # Digital Europe thematic areas
    THEMATIC_AREAS = [
        "AI",  # Artificial Intelligence
        "SKILLS",  # Advanced Digital Skills
        "BESTUSE",  # Best Use of Digital / Deployment
        "EDIH",  # European Digital Innovation Hubs
        "CLOUD",  # Cloud and Data
        "DATA",  # Data Spaces
        "CHIPS",  # Semiconductors (Chips Act)
        "HPC",  # High Performance Computing
        "ECCC",  # Cybersecurity (via ECCC)
    ]

    # Work Programme numbers by year
    WP_NUMBERS = {
        2021: ["01", "02"],
        2022: ["03", "04"],
        2023: ["05", "06"],
        2024: ["07"],
        2025: ["08"],
        2026: ["09"],
        2027: ["10"],
    }

    # Digital Europe Specific Objectives mapping
    OBJECTIVE_MAPPING = {
        "HPC": "High Performance Computing",
        "AI": "Artificial Intelligence",
        "ECCC": "Cybersecurity and Trust",
        "CYBER": "Cybersecurity and Trust",
        "SKILLS": "Advanced Digital Skills",
        "BESTUSE": "Deployment and Best Use",
        "EDIH": "European Digital Innovation Hubs",
        "CLOUD": "Cloud Infrastructure",
        "DATA": "Data Spaces",
        "CHIPS": "Semiconductors",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "MAP-IT-SA/1.0 Digital Europe Sync",
                "Accept": "application/json",
            }
        )

    def generate_topic_patterns(self, years: list[int]) -> list[str]:
        """Generate all possible Digital Europe topic patterns."""
        patterns = []

        # Common topic suffixes that are most likely to exist
        COMMON_SUFFIXES = [
            "MULTICOUNTRY",
            "LANGUAGE",
            "TRUST",
            "EDMO",
            "WALLET",
            "EID",
            "GENAI",
            "AIACT",
            "SUPPLY",
            "STEP",
            "ACADEMY",
            "FACTORY",
            "COMPLETION",
            "CONSOLIDATION",
            "KEYCAPACITY",
        ]

        for year in years:
            wp_nums = self.WP_NUMBERS.get(year, ["07", "08", "09"])

            for wp_num in wp_nums:
                # PRIORITY 1: Named topic suffixes (most likely to exist)
                for thematic in self.THEMATIC_AREAS:
                    for suffix in COMMON_SUFFIXES:
                        patterns.append(f"DIGITAL-{year}-{thematic}-{wp_num}-{suffix}")

                    # Combined thematic patterns (e.g., BESTUSE-TECH)
                    if thematic == "BESTUSE":
                        for suffix in COMMON_SUFFIXES:
                            patterns.append(f"DIGITAL-{year}-BESTUSE-TECH-{wp_num}-{suffix}")

                # PRIORITY 2: EDIH patterns
                for suffix in COMMON_SUFFIXES + [""]:
                    if suffix:
                        patterns.append(f"DIGITAL-{year}-EDIH-EU-EEA-{wp_num}-{suffix}")
                        patterns.append(f"DIGITAL-{year}-EDIH-AC-{wp_num}-{suffix}")
                    else:
                        patterns.append(f"DIGITAL-{year}-EDIH-EU-EEA-{wp_num}")
                        patterns.append(f"DIGITAL-{year}-EDIH-AC-{wp_num}")

                # PRIORITY 3: Cybersecurity patterns (ECCC)
                for suffix in ["SOCSYS", "KEYTECH", "SOCPLAT", "CYBERSEC", "TESTBED", "RESILIENCE"]:
                    patterns.append(f"DIGITAL-ECCC-{year}-DEPLOY-CYBER-{wp_num}-{suffix}")
                for num in range(1, 10):
                    patterns.append(f"DIGITAL-ECCC-{year}-DEPLOY-CYBER-{wp_num}-{num:02d}")

                # PRIORITY 4: Advanced Digital patterns
                for suffix in ["KEYCAPACITY", "SPECIALISED", "GENAI", "ACADEMY"]:
                    patterns.append(f"DIGITAL-{year}-ADVANCED-DIGITAL-{wp_num}-{suffix}")

                # PRIORITY 5: Numbered patterns (less common)
                for thematic in self.THEMATIC_AREAS:
                    for topic_num in range(1, 20):
                        patterns.append(f"DIGITAL-{year}-{thematic}-{wp_num}-{topic_num:02d}")
                        for letter in ["a", "b", "c", "d"]:
                            patterns.append(
                                f"DIGITAL-{year}-{thematic}-{wp_num}-{topic_num:02d}-{letter}"
                            )

        # Remove duplicates while preserving order
        seen = set()
        unique_patterns = []
        for p in patterns:
            if p not in seen:
                seen.add(p)
                unique_patterns.append(p)

        logger.info(f"Generated {len(unique_patterns)} unique topic patterns to try")
        return unique_patterns

    def fetch_topic_details(self, topic_id: str) -> dict[str, Any] | None:
        """Fetch topic details from EU Portal API."""
        # API requires lowercase topic IDs
        url = self.TOPIC_DETAILS_URL.format(topic_id=topic_id.lower())

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.warning(f"Unexpected status {response.status_code} for {topic_id}")
                return None
        except requests.RequestException as e:
            logger.warning(f"Error fetching {topic_id}: {e}")
            return None

    def search_topics_via_api(self, query: str = "DIGITAL") -> list[dict[str, Any]]:
        """Search for topics using the EU Portal search API."""
        try:
            params = {
                "apiKey": "SEDIA",
                "text": query,
                "pageSize": 500,
                "pageNumber": 1,
            }

            response = self.session.get(self.SEARCH_API_URL, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                logger.info(f"Search API returned {len(results)} results for '{query}'")
                return results
            else:
                logger.warning(f"Search API returned status {response.status_code}")
                return []
        except Exception as e:
            logger.warning(f"Search API error: {e}")
            return []

    def parse_topic_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse topic data into funding call format."""
        topic_details = data.get("TopicDetails", {})

        # Extract basic info
        topic_id = topic_details.get("identifier", "")
        title = topic_details.get("title", "")
        description = topic_details.get("description", "") or topic_details.get("introduction", "")

        # Extract dates
        deadline_dates = topic_details.get("deadlineDates", [])
        deadline = None
        if deadline_dates:
            # Get the latest deadline
            deadline = max(deadline_dates)

        publication_date = topic_details.get("publicationDateLong")
        opening_date = topic_details.get("plannedOpeningDate") or topic_details.get("openingDate")

        # Extract budget
        budget_info = topic_details.get("budget", {})
        budget_range = None
        if budget_info:
            budget_min = budget_info.get("budgetTopicActionMin")
            budget_max = budget_info.get("budgetTopicActionMax")
            if budget_min and budget_max:
                budget_range = f"€{budget_min:,.0f} - €{budget_max:,.0f}"
            elif budget_max:
                budget_range = f"Up to €{budget_max:,.0f}"

        # Determine status - check multiple possible locations in API response
        status = None

        # Check direct status field
        if topic_details.get("status"):
            status = topic_details["status"]

        # Check actions array for status (common API structure)
        if not status:
            actions = topic_details.get("actions", [])
            if actions and isinstance(actions, list) and len(actions) > 0:
                action = actions[0]
                if isinstance(action, dict):
                    status_obj = action.get("status", {})
                    if isinstance(status_obj, dict):
                        status = status_obj.get("abbreviation") or status_obj.get("description")
                    elif isinstance(status_obj, str):
                        status = status_obj

        # Normalize and map to valid database values
        if status:
            status = status.lower().strip()
            if status in ["open", "opening"]:
                status = "open"
            elif status in ["forthcoming", "upcoming", "planned"]:
                status = "upcoming"
            elif status in ["closed", "evaluated", "under evaluation", "awarded"]:
                status = "closed"
            elif status in ["cancelled", "withdrawn"]:
                status = "cancelled"
            else:
                # Unknown status - default to closed (most common for past calls)
                logger.debug(f"Unknown status '{status}' for {topic_id}, defaulting to 'closed'")
                status = "closed"
        else:
            # No status found - default to closed
            status = "closed"

        # Determine thematic area from topic ID
        thematic_area = self._detect_thematic_area(topic_id)
        objective = self.OBJECTIVE_MAPPING.get(thematic_area, "Digital Transformation")

        return {
            "topic_id": topic_id,
            "title": title,
            "description": description[:2000] if description else None,
            "deadline": deadline,
            "publication_date": publication_date,
            "opening_date": opening_date,
            "budget_range": budget_range,
            "status": status,
            "thematic_area": thematic_area,
            "objective": objective,
            "programme": "digital_europe",
            "url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_id}",
        }

    def _detect_thematic_area(self, topic_id: str) -> str:
        """Detect thematic area from topic ID."""
        topic_upper = topic_id.upper()

        for area in self.THEMATIC_AREAS:
            if area in topic_upper:
                return area

        if "CYBER" in topic_upper or "ECCC" in topic_upper:
            return "ECCC"
        if "ADVANCED-DIGITAL" in topic_upper:
            return "SKILLS"

        return "GENERAL"

    def upsert_call(self, conn, data: dict[str, Any]) -> bool:
        """Insert or update a Digital Europe call in the database."""
        try:
            cursor = conn.cursor()

            metadata = data.get("metadata", {})
            metadata["synced_from_api"] = True
            metadata["synced_at"] = datetime.utcnow().isoformat()

            cursor.execute(
                """
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
            """,
                (
                    data.get("programme", "digital_europe"),
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

    def sync_to_database(
        self, calls: list[dict[str, Any]], dry_run: bool = False
    ) -> dict[str, int]:
        """Sync calls to the funding_calls table."""
        if dry_run:
            logger.info("DRY RUN - Would sync these calls:")
            for call in calls[:20]:
                title = call.get("title", "No title")[:60]
                logger.info(f"  {call['topic_id']}: {title}... ({call['status']})")
            if len(calls) > 20:
                logger.info(f"  ... and {len(calls) - 20} more")
            return {"synced": 0, "dry_run": len(calls)}

        import os

        import psycopg2

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL not set")
            return {"synced": 0, "errors": len(calls)}

        try:
            conn = psycopg2.connect(database_url)
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return {"synced": 0, "errors": len(calls)}

        synced = 0
        errors = 0

        for call in calls:
            try:
                # Extract year from topic ID
                import re

                year_match = re.search(r"20(\d{2})", call["topic_id"])
                call_year = int(f"20{year_match.group(1)}") if year_match else None

                # Prepare call data for database
                call_data = {
                    "programme": "digital_europe",
                    "topic_code": call["topic_id"],
                    "title": call.get("title"),
                    "scope": call.get("description"),
                    "expected_outcome": None,
                    "deadline": call.get("deadline"),
                    "status": call.get("status", "closed"),  # Default to 'closed' (valid status)
                    "action_type": call.get("thematic_area"),
                    "budget_total": None,  # Would need parsing from budget_range
                    "call_identifier": call.get("topic_id"),
                    "cluster": call.get("objective"),
                    "call_year": call_year,
                    "portal_url": call.get("url"),
                    "metadata": {
                        "source": "eu_portal_api",
                        "thematic_area": call.get("thematic_area"),
                        "objective": call.get("objective"),
                        "budget_range": call.get("budget_range"),
                        "implementing_agency": "DG CONNECT / HaDEA",
                    },
                }

                # Upsert call
                if self.upsert_call(conn, call_data):
                    synced += 1
                else:
                    errors += 1

            except Exception as e:
                logger.warning(f"Error syncing {call['topic_id']}: {e}")
                errors += 1

        conn.close()
        return {"synced": synced, "errors": errors}

    def run(self, years: list[int], dry_run: bool = False) -> dict[str, Any]:
        """Run the sync process."""
        logger.info("=" * 60)
        logger.info("DIGITAL EUROPE CALL SYNC")
        logger.info("=" * 60)
        logger.info(f"Years: {years}")
        logger.info(f"Dry run: {dry_run}")

        all_calls = []
        found_topics = set()

        # Method 1: Search API
        logger.info("\n--- Searching via EU Portal Search API ---")
        search_results = self.search_topics_via_api("DIGITAL")

        for result in search_results:
            topic_id = result.get("identifier", "")
            if topic_id and topic_id.startswith("DIGITAL") and topic_id not in found_topics:
                # Fetch full details
                time.sleep(0.1)  # Rate limiting
                details = self.fetch_topic_details(topic_id)
                if details:
                    parsed = self.parse_topic_data(details)
                    all_calls.append(parsed)
                    found_topics.add(topic_id)
                    logger.info(f"  Found: {topic_id}")

        logger.info(f"Found {len(found_topics)} topics via search API")

        # Method 2: Pattern-based discovery
        logger.info("\n--- Pattern-based topic discovery ---")
        patterns = self.generate_topic_patterns(years)

        checked = 0
        for pattern in patterns:
            if pattern in found_topics:
                continue

            checked += 1
            if checked % 100 == 0:
                logger.info(
                    f"  Checked {checked}/{len(patterns)} patterns, found {len(found_topics)} topics"
                )

            time.sleep(0.05)  # Rate limiting
            details = self.fetch_topic_details(pattern)

            if details:
                parsed = self.parse_topic_data(details)
                all_calls.append(parsed)
                found_topics.add(pattern)
                logger.info(f"  Found: {pattern}")

            # Early termination if we've checked many patterns without finding new topics
            if checked > 2000 and len(found_topics) == 0:
                logger.info("  No topics found after 2000 patterns, stopping pattern search")
                break

        logger.info(f"\nTotal topics found: {len(all_calls)}")

        # Analyze by thematic area
        by_area = {}
        by_status = {}
        for call in all_calls:
            area = call.get("thematic_area", "GENERAL")
            by_area[area] = by_area.get(area, 0) + 1
            status = call.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        logger.info("\nBy thematic area:")
        for area, count in sorted(by_area.items(), key=lambda x: -x[1]):
            logger.info(f"  {area}: {count}")

        logger.info("\nBy status:")
        for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
            logger.info(f"  {status}: {count}")

        # Sync to database
        logger.info("\n--- Syncing to database ---")
        result = self.sync_to_database(all_calls, dry_run)

        logger.info("\n" + "=" * 60)
        logger.info("SYNC SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total topics found: {len(all_calls)}")
        logger.info(f"Synced: {result.get('synced', 0)}")
        logger.info(f"Errors: {result.get('errors', 0)}")

        return {"total_found": len(all_calls), "by_area": by_area, "by_status": by_status, **result}


def main():
    parser = argparse.ArgumentParser(description="Sync Digital Europe calls from EU Portal API")
    parser.add_argument("--dry-run", action="store_true", help="Don't commit to database")
    parser.add_argument(
        "--years",
        default="2024,2025,2026",
        help="Comma-separated years to sync (default: 2024,2025,2026)",
    )

    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")]

    syncer = DigitalEuropeCallSyncer()
    result = syncer.run(years=years, dry_run=args.dry_run)

    if result.get("total_found", 0) > 0:
        logger.info("\nSync completed successfully!")
        return 0
    else:
        logger.warning("\nNo topics found!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
