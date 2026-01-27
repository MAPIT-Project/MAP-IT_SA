#!/usr/bin/env python3
"""
Sync LIFE Programme funding calls from EU Portal API.

Fetches LIFE call topics from the EU Funding & Tenders Portal API
and syncs them to the local funding_calls table.

Topic code patterns for LIFE:
- LIFE-{YEAR}-{SUBPROGRAMME}-{TYPE}-{ID}
- Subprogrammes: NAT (Nature), ENV (Circular Economy), CCA (Climate), CET (Clean Energy)
- Types: SAP (Standard Action Projects), SIP (Strategic Integrated Projects), etc.

Usage:
    python scripts/sync_life_calls_from_api.py [--dry-run] [--years 2024,2025,2026]
"""

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class LIFECallSyncer:
    """Syncs LIFE calls from EU Portal API."""

    # EU Portal API endpoints
    TOPIC_DETAILS_URL = (
        "https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails/{topic_id}.json"
    )

    # LIFE Sub-programmes
    SUBPROGRAMMES = {
        "NAT": {
            "name": "Nature and Biodiversity",
            "description": "Conservation of nature and biodiversity",
            "funding_rate": 75,
        },
        "ENV": {
            "name": "Circular Economy and Quality of Life",
            "description": "Resource efficiency, waste, water, air, soil",
            "funding_rate": 60,
        },
        "CCA": {
            "name": "Climate Change Mitigation and Adaptation",
            "description": "Reducing greenhouse gas emissions and adapting to climate change",
            "funding_rate": 60,
        },
        "CET": {
            "name": "Clean Energy Transition",
            "description": "Supporting the transition to clean energy",
            "funding_rate": 95,
        },
    }

    # Project types
    PROJECT_TYPES = {
        "SAP": "Standard Action Projects",
        "SIP": "Strategic Integrated Projects",
        "SNAP": "Strategic Nature Projects",
        "TA": "Technical Assistance",
        "OG": "Operating Grants",
        "PLP": "Policy Support Projects",
        "PREP": "Preparatory Projects",
        "INFO": "Information and Governance Projects",
        "STRAT": "Strategic Projects",
        "NGO": "NGO Operating Grants",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "MAP-IT-SA/1.0 LIFE Sync",
                "Accept": "application/json",
            }
        )

    def generate_topic_patterns(self, years: list[int]) -> list[str]:
        """Generate all possible LIFE topic patterns."""
        patterns = []

        for year in years:
            # ==========================================
            # MAIN CALL PATTERNS (verified working)
            # ==========================================

            # Standard Action Projects (SAP) - main call format
            patterns.extend(
                [
                    f"LIFE-{year}-SAP-NAT-NATURE",  # Nature and Biodiversity
                    f"LIFE-{year}-SAP-ENV-ENVIRONMENT",  # Circular Economy
                    f"LIFE-{year}-SAP-CLIMA-CCA",  # Climate Change Adaptation
                    f"LIFE-{year}-SAP-CLIMA-CCM",  # Climate Change Mitigation
                ]
            )

            # Clean Energy Transition (CET) calls
            patterns.extend(
                [
                    f"LIFE-{year}-CET-SAP",
                    f"LIFE-{year}-CET-LOCAL",
                    f"LIFE-{year}-CET-POLICY",
                ]
            )

            # Strategic projects - two-stage
            patterns.extend(
                [
                    f"LIFE-{year}-STRAT-NAT-two-stage",
                    f"LIFE-{year}-STRAT-ENV-two-stage",
                    f"LIFE-{year}-STRAT-two-stage",
                ]
            )

            # NGO Operating Grants
            patterns.extend(
                [
                    f"LIFE-{year}-NGO-OG",
                    f"LIFE-{year}-NGO-OG-SGA",
                ]
            )

            # Technical Assistance
            patterns.extend(
                [
                    f"LIFE-{year}-TA-CAP",
                    f"LIFE-{year}-TA-PP",
                    f"LIFE-{year}-TA-PP-SIP-SNAP",
                ]
            )

            # ==========================================
            # FALLBACK PATTERNS (older format)
            # ==========================================
            for subprog in ["NAT", "ENV", "CCA", "CET"]:
                patterns.append(f"LIFE-{year}-{subprog}")
                for ptype in ["SAP", "SIP", "SNAP", "TA", "OG"]:
                    patterns.append(f"LIFE-{year}-{subprog}-{ptype}")

        # Remove duplicates
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

        # Determine status - check multiple possible locations
        status = None

        # Check direct status field
        if topic_details.get("status"):
            status = topic_details["status"]

        # Check actions array for status
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

        # Normalize status to valid database values
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
                status = "closed"
        else:
            status = "closed"

        # Determine sub-programme from topic ID
        subprogramme = self._detect_subprogramme(topic_id)
        subprog_info = self.SUBPROGRAMMES.get(subprogramme, {})

        # Determine project type
        project_type = self._detect_project_type(topic_id)

        return {
            "topic_id": topic_id,
            "title": title,
            "description": description[:2000] if description else None,
            "deadline": deadline,
            "publication_date": publication_date,
            "opening_date": opening_date,
            "budget_range": budget_range,
            "status": status,
            "subprogramme": subprogramme,
            "subprogramme_name": subprog_info.get("name", "General"),
            "project_type": project_type,
            "funding_rate": subprog_info.get("funding_rate", 60),
            "programme": "life",
            "url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_id}",
        }

    def _detect_subprogramme(self, topic_id: str) -> str:
        """Detect sub-programme from topic ID."""
        topic_upper = topic_id.upper()

        # Check for CLIMA patterns first (maps to CCA sub-programme)
        if "-CLIMA-" in topic_upper or "-CLIMA" in topic_upper:
            return "CCA"

        # Check for Nature pattern
        if "-NAT-NATURE" in topic_upper or "-NAT-" in topic_upper or topic_upper.endswith("-NAT"):
            return "NAT"

        # Check for Environment pattern
        if (
            "-ENV-ENVIRONMENT" in topic_upper
            or "-ENV-" in topic_upper
            or topic_upper.endswith("-ENV")
        ):
            return "ENV"

        # Check for CET pattern
        if "-CET-" in topic_upper or topic_upper.endswith("-CET"):
            return "CET"

        # Check for standard codes
        for code in self.SUBPROGRAMMES.keys():
            if f"-{code}" in topic_upper or f"-{code}-" in topic_upper:
                return code

        return "GENERAL"

    def _detect_project_type(self, topic_id: str) -> str:
        """Detect project type from topic ID."""
        topic_upper = topic_id.upper()

        for code, name in self.PROJECT_TYPES.items():
            if f"-{code}" in topic_upper or f"-{code}-" in topic_upper:
                return name

        return "Standard Action Projects"

    def upsert_call(self, conn, data: dict[str, Any]) -> bool:
        """Insert or update a LIFE call in the database."""
        try:
            cursor = conn.cursor()

            metadata = data.get("metadata", {})
            metadata["synced_from_api"] = True
            metadata["synced_at"] = datetime.now(UTC).isoformat()

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
                    data.get("programme", "life"),
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
                import re

                year_match = re.search(r"20(\d{2})", call["topic_id"])
                call_year = int(f"20{year_match.group(1)}") if year_match else None

                call_data = {
                    "programme": "life",
                    "topic_code": call["topic_id"],
                    "title": call.get("title"),
                    "scope": call.get("description"),
                    "expected_outcome": None,
                    "deadline": call.get("deadline"),
                    "status": call.get("status", "closed"),
                    "action_type": call.get("project_type"),
                    "budget_total": None,
                    "call_identifier": call.get("topic_id"),
                    "cluster": call.get("subprogramme_name"),
                    "call_year": call_year,
                    "portal_url": call.get("url"),
                    "metadata": {
                        "source": "eu_portal_api",
                        "subprogramme": call.get("subprogramme"),
                        "subprogramme_name": call.get("subprogramme_name"),
                        "funding_rate": call.get("funding_rate"),
                        "implementing_agency": "CINEA",
                    },
                }

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
        logger.info("LIFE PROGRAMME CALL SYNC")
        logger.info("=" * 60)
        logger.info(f"Years: {years}")
        logger.info(f"Dry run: {dry_run}")

        all_calls = []
        found_topics = set()

        # Pattern-based discovery
        logger.info("\n--- Pattern-based topic discovery ---")
        patterns = self.generate_topic_patterns(years)

        checked = 0
        for pattern in patterns:
            if pattern in found_topics:
                continue

            checked += 1
            if checked % 50 == 0:
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

            # Early termination
            if checked > 300 and len(found_topics) == 0:
                logger.info("  No topics found after 300 patterns, stopping")
                break

        logger.info(f"\nTotal topics found: {len(all_calls)}")

        # Analyze by sub-programme
        by_subprog = {}
        by_status = {}
        for call in all_calls:
            subprog = call.get("subprogramme", "GENERAL")
            by_subprog[subprog] = by_subprog.get(subprog, 0) + 1
            status = call.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        logger.info("\nBy sub-programme:")
        for subprog, count in sorted(by_subprog.items(), key=lambda x: -x[1]):
            name = self.SUBPROGRAMMES.get(subprog, {}).get("name", subprog)
            logger.info(f"  {subprog} ({name}): {count}")

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

        return {
            "total_found": len(all_calls),
            "by_subprogramme": by_subprog,
            "by_status": by_status,
            **result,
        }


def main():
    parser = argparse.ArgumentParser(description="Sync LIFE Programme calls from EU Portal API")
    parser.add_argument("--dry-run", action="store_true", help="Don't commit to database")
    parser.add_argument(
        "--years",
        default="2024,2025,2026",
        help="Comma-separated years to sync (default: 2024,2025,2026)",
    )

    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")]

    syncer = LIFECallSyncer()
    result = syncer.run(years=years, dry_run=args.dry_run)

    if result.get("total_found", 0) > 0:
        logger.info("\nSync completed successfully!")
        return 0
    else:
        logger.warning("\nNo topics found!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
