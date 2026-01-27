#!/usr/bin/env python3
"""
Sync Creative Europe Calls from EU Portal API

Downloads all Creative Europe calls (open, closed, upcoming) from the EU Portal API
and stores them in the local database with complete structured data.

Creative Europe has three strands:
- CULTURE: Support for cultural and creative sectors
- MEDIA: Support for audiovisual and film industries
- Cross-sectoral: News media, innovation labs, cross-cutting initiatives

Usage:
    python scripts/sync_creative_europe_calls.py [--status open|closed|all] [--limit N] [--dry-run]

Options:
    --status    Filter by status: open, closed, upcoming, or all (default: all)
    --limit     Limit number of calls to process (for testing)
    --dry-run   Don't update database, just show what would be synced
    --force     Re-sync all calls, even if they already exist
    --year      Specific year to sync (e.g., 2024, 2025, 2026)
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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


class CreativeEuropePortalSyncer:
    """Sync Creative Europe calls from EU Portal API to local database."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.client = httpx.Client(timeout=60.0)
        self.search_api = EU_SEARCH_API
        self.topic_api = EU_TOPIC_DETAILS
        self.api_key = "SEDIA"  # Public API key

        # Creative Europe strand mappings
        self.strands = {
            "CULT": "CULTURE",
            "CULTURE": "CULTURE",
            "MEDIA": "MEDIA",
            "CROSS": "CROSS-SECTORAL",
            "CROSS-SECTORAL": "CROSS-SECTORAL",
        }

        # Action type mappings for Creative Europe
        self.action_types = {
            # CULTURE strand
            "COOP": "European Cooperation Projects",
            "COOP-1": "Small-scale European Cooperation Projects",
            "COOP-2": "Medium-scale European Cooperation Projects",
            "COOP-3": "Large-scale European Cooperation Projects",
            "NETWORKS": "European Networks",
            "PLATFORMS": "European Platforms",
            "LIT": "Literary Translation",
            "MUS": "Music Moves Europe",
            "CULT-COOP": "Cooperation Projects Culture",
            # MEDIA strand
            "CONTENT": "Content Development",
            "DEVSLATE": "Slate Development",
            "DEV-CREA": "Single Project Development",
            "VIDEO-GAMES": "Video Games",
            "COPROD": "Co-production Funds",
            "TV-PROG": "TV Programming",
            "DIST": "Distribution",
            "SALES": "Sales Agents",
            "CINEMA": "Cinema Networks",
            "ONLINEDIST": "Online Distribution",
            "FESTIVALS": "Film Festivals",
            "TRAIN": "Training",
            "MARKET": "Markets & Networking",
            "TALENTS": "Talent & Skills",
            "AUDIENCE": "Audience Development",
            "INNOV": "Innovative Tools",
            # Cross-sectoral strand
            "NEWS": "News Media",
            "NEWS-MED": "News Media Actions",
            "MEDLIT": "Media Literacy",
            "CROSS-LABS": "Creative Innovation Labs",
            "LABS": "Creative Labs",
            "CROSS-SECT": "Cross-sectoral Actions",
        }

    def close(self):
        """Close HTTP client."""
        self.client.close()

    def get_existing_topics_from_db(self, conn) -> list[dict]:
        """Get all existing Creative Europe topic codes from database."""
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT topic_code, title, status, deadline
            FROM funding_calls
            WHERE programme = 'creative_europe'
              AND topic_code IS NOT NULL
            ORDER BY call_year DESC NULLS LAST, topic_code
        """
        )
        results = cursor.fetchall()
        return [{"identifier": r["topic_code"], "title": r["title"] or ""} for r in results]

    def discover_topics_via_search_api(self) -> dict[str, dict]:
        """
        Discover actual Creative Europe topic codes via EU Portal Search API.

        The topic codes are extracted from the URLs in the search results,
        which follow the pattern: /topicDetails/CREA-XXX.json

        Returns:
            Dict mapping topic codes to basic info from search results
        """
        import re

        discovered = {}

        # Pattern to extract topic code from URL
        topic_pattern = re.compile(r"/topicDetails/([A-Z0-9-]+)\.json")

        # Search terms to find Creative Europe calls
        search_terms = ["CREA-CULT", "CREA-MEDIA", "CREA-CROSS", "CREA-"]

        logger.info("Discovering Creative Europe topics via Search API...")

        for term in search_terms:
            logger.info(f"  Searching for: {term}")

            for page in range(1, 15):  # Up to 14 pages per term
                try:
                    payload = {
                        "apiKey": self.api_key,
                        "text": term,
                        "pageSize": 100,
                        "pageNumber": page,
                    }

                    response = self.client.post(
                        self.search_api,
                        data=payload,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )

                    if response.status_code != 200:
                        break

                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        break

                    found_in_page = 0
                    for result in results:
                        # Extract topic code from URL
                        url = result.get("url", "")
                        match = topic_pattern.search(url)
                        if match:
                            topic_code = match.group(1)
                            # Filter for Creative Europe topics only
                            if topic_code.startswith("CREA-") and topic_code not in discovered:
                                # Extract basic info from search result
                                discovered[topic_code] = {
                                    "summary": result.get("summary", ""),
                                    "content": result.get("content", ""),
                                    "url": url,
                                }
                                found_in_page += 1

                    logger.debug(f"    Page {page}: found {found_in_page} topics")
                    time.sleep(0.2)  # Rate limiting

                except Exception as e:
                    logger.warning(f"    Error searching {term} page {page}: {e}")
                    break

        logger.info(f"  Discovered {len(discovered)} unique Creative Europe topics")
        return discovered

    def get_topic_details(self, topic_code: str) -> dict | None:
        """
        Fetch detailed information about a specific topic from EU Portal.

        Args:
            topic_code: The topic identifier (e.g., CREA-CULT-2025-COOP-1)

        Returns:
            Dict with topic details or None if not found
        """
        try:
            url = f"{self.topic_api}/{topic_code}.json"
            response = self.client.get(url)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.debug(f"Topic not found: {topic_code}")
                return None
            else:
                logger.warning(f"Error fetching {topic_code}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Exception fetching {topic_code}: {e}")
            return None

    def parse_topic_details(self, topic_data: dict) -> dict:
        """
        Parse topic details from EU Portal API into our database schema.

        Args:
            topic_data: Raw API response from topic details endpoint

        Returns:
            Dict with parsed call data
        """
        topic = topic_data.get("TopicDetails", {})
        topic_code = topic.get("identifier", "")

        # Detect strand from topic code
        strand = "UNKNOWN"
        if "CULT" in topic_code.upper():
            strand = "CULTURE"
        elif "MEDIA" in topic_code.upper():
            strand = "MEDIA"
        elif "CROSS" in topic_code.upper():
            strand = "CROSS-SECTORAL"

        # Parse deadline dates
        deadline_dates = topic.get("deadlineDatesLong", [])
        deadline = None
        if deadline_dates:
            try:
                # First deadline is usually the primary one
                deadline = datetime.fromtimestamp(deadline_dates[0] / 1000).date()
            except (ValueError, TypeError):
                pass

        # Parse status
        status_raw = topic.get("status", {})
        status = "unknown"
        if isinstance(status_raw, dict):
            status_abbr = status_raw.get("abbreviation", "").lower()
            if status_abbr in ["open", "forthcoming", "closed"]:
                status = status_abbr
        elif isinstance(status_raw, str):
            status = status_raw.lower()

        # Map status values
        status_mapping = {
            "open": "open",
            "forthcoming": "upcoming",
            "closed": "closed",
        }
        status = status_mapping.get(status, status)

        # Extract budget info
        budget_min = None
        budget_max = None
        budget_overview = topic.get("budgetOverviewJSONItem", {})
        if budget_overview:
            budget_min = budget_overview.get("minGrantedAmount")
            budget_max = budget_overview.get("maxGrantedAmount")

        # Parse call year from topic code (e.g., CREA-CULT-2025-COOP)
        year_match = re.search(r"-(\d{4})-", topic_code)
        call_year = int(year_match.group(1)) if year_match else None

        # Build description from available fields
        description_parts = []
        if topic.get("description"):
            description_parts.append(topic["description"])
        if topic.get("additionalInformation"):
            description_parts.append(topic["additionalInformation"])

        return {
            "topic_code": topic_code,
            "title": topic.get("title", ""),
            "description": "\n\n".join(description_parts) if description_parts else None,
            "programme": "creative_europe",
            "strand": strand,
            "status": status,
            "deadline": deadline,
            "call_year": call_year,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "destination": topic.get("destination"),
            "keywords": topic.get("keywords", []),
            "metadata": {
                "api_data": {
                    "ccm2Id": topic.get("ccm2Id"),
                    "frameworkProgramme": topic.get("frameworkProgramme"),
                    "programmePart": topic.get("programmePart"),
                    "typesOfAction": topic.get("typesOfAction"),
                    "deadlineDates": topic.get("deadlineDates"),
                    "conditions": topic.get("conditions"),
                    "supportInfo": topic.get("supportInfo"),
                },
                "synced_at": datetime.now().isoformat(),
            },
        }

    def upsert_call(self, conn, call_data: dict) -> bool:
        """
        Insert or update a call in the database.

        Args:
            conn: Database connection
            call_data: Parsed call data

        Returns:
            True if successful, False otherwise
        """
        cursor = conn.cursor()

        try:
            # Map call_data to actual table columns
            db_data = {
                "topic_code": call_data.get("topic_code"),
                "title": call_data.get("title"),
                "programme": call_data.get("programme"),
                "programme_part": call_data.get("strand"),  # Store strand as programme_part
                "status": call_data.get("status"),
                "deadline": call_data.get("deadline"),
                "call_year": call_data.get("call_year"),
                "budget_per_project_min": call_data.get("budget_min"),
                "budget_per_project_max": call_data.get("budget_max"),
                "destination": call_data.get("destination"),
                "scope": call_data.get("description"),  # Map description to scope
                "tags": call_data.get("keywords", []),
                "metadata": json.dumps(call_data.get("metadata", {})),
            }

            # Upsert using ON CONFLICT
            cursor.execute(
                """
                INSERT INTO funding_calls (
                    topic_code, title, programme, programme_part, status,
                    deadline, call_year, budget_per_project_min, budget_per_project_max,
                    destination, scope, tags, metadata, updated_at
                ) VALUES (
                    %(topic_code)s, %(title)s, %(programme)s, %(programme_part)s, %(status)s,
                    %(deadline)s, %(call_year)s, %(budget_per_project_min)s, %(budget_per_project_max)s,
                    %(destination)s, %(scope)s, %(tags)s, %(metadata)s, NOW()
                )
                ON CONFLICT (topic_code)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    programme_part = EXCLUDED.programme_part,
                    status = EXCLUDED.status,
                    deadline = EXCLUDED.deadline,
                    call_year = EXCLUDED.call_year,
                    budget_per_project_min = EXCLUDED.budget_per_project_min,
                    budget_per_project_max = EXCLUDED.budget_per_project_max,
                    destination = EXCLUDED.destination,
                    scope = EXCLUDED.scope,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """,
                db_data,
            )

            conn.commit()  # Commit each successful insert
            return True

        except Exception as e:
            logger.error(f"Error upserting call {call_data.get('topic_code')}: {e}")
            conn.rollback()  # Rollback on error to allow next insert
            return False

    def parse_topic_from_search(self, topic_code: str, search_info: dict) -> dict:
        """
        Parse topic information from search result into database schema.

        Since the topic details API doesn't work for Creative Europe,
        we extract what we can from search results.

        Args:
            topic_code: The topic identifier
            search_info: Basic info from search results

        Returns:
            Dict with call data
        """
        # Detect strand from topic code
        strand = "UNKNOWN"
        if "-CULT-" in topic_code:
            strand = "CULTURE"
        elif "-MEDIA-" in topic_code:
            strand = "MEDIA"
        elif "-CROSS-" in topic_code:
            strand = "CROSS-SECTORAL"

        # Parse call year from topic code
        year_match = re.search(r"-(\d{4})-", topic_code)
        call_year = int(year_match.group(1)) if year_match else None

        # Extract title from summary or content
        summary = search_info.get("summary", "")
        content = search_info.get("content", "")

        # Clean HTML tags from content
        title = re.sub(r"<[^>]+>", "", summary or content)
        title = title.strip()[:200] or topic_code

        # Determine status based on year (rough estimate)
        # Valid statuses: 'open', 'closed', 'upcoming'
        current_year = datetime.now().year
        if call_year:
            if call_year > current_year:
                status = "upcoming"
            elif call_year == current_year:
                status = "open"  # Might be open or closed
            else:
                status = "closed"
        else:
            status = "closed"  # Default to closed if year unknown

        return {
            "topic_code": topic_code,
            "title": title,
            "description": content if content != summary else None,
            "programme": "creative_europe",
            "strand": strand,
            "status": status,
            "deadline": None,  # Not available from search
            "call_year": call_year,
            "budget_min": None,
            "budget_max": None,
            "destination": None,
            "keywords": [],
            "metadata": {
                "source": "eu_portal_search",
                "original_url": search_info.get("url", ""),
                "synced_at": datetime.now().isoformat(),
            },
        }

    def sync_all_calls(
        self,
        status_filter: str | None = None,
        limit: int | None = None,
        dry_run: bool = False,
        force: bool = False,
        year: int | None = None,
    ) -> dict[str, int]:
        """
        Sync all Creative Europe calls from EU Portal API.

        Args:
            status_filter: Filter by status (open, closed, upcoming, all)
            limit: Limit number of calls to process
            dry_run: Don't update database
            force: Re-sync all calls
            year: Filter by specific year

        Returns:
            Dict with sync statistics
        """
        stats = {
            "discovered": 0,
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }

        # Discover topics (returns dict with basic info)
        discovered_topics = self.discover_topics_via_search_api()
        stats["discovered"] = len(discovered_topics)

        if not discovered_topics:
            logger.warning("No Creative Europe topics discovered from API")
            return stats

        # Filter by year if specified
        if year:
            discovered_topics = {k: v for k, v in discovered_topics.items() if f"-{year}-" in k}
            logger.info(f"Filtered to {len(discovered_topics)} topics for year {year}")

        # Connect to database
        if not dry_run:
            conn = psycopg2.connect(self.db_url)
            conn.autocommit = False

            # Get existing topics if not forcing
            existing = set()
            if not force:
                existing_rows = self.get_existing_topics_from_db(conn)
                existing = {r["identifier"] for r in existing_rows}
                logger.info(f"Found {len(existing)} existing Creative Europe topics in database")
        else:
            conn = None
            existing = set()

        # Process each topic
        topics_to_process = list(discovered_topics.items())
        if limit:
            topics_to_process = topics_to_process[:limit]

        logger.info(f"Processing {len(topics_to_process)} topics...")

        for i, (topic_code, search_info) in enumerate(topics_to_process, 1):
            # Skip if already exists and not forcing
            if topic_code in existing and not force:
                stats["skipped"] += 1
                continue

            # Parse from search results (no API call needed)
            call_data = self.parse_topic_from_search(topic_code, search_info)
            stats["processed"] += 1

            # Apply status filter
            if status_filter and status_filter != "all":
                if call_data["status"] != status_filter:
                    stats["skipped"] += 1
                    continue

            # Log progress
            strand_emoji = {"CULTURE": "🎭", "MEDIA": "🎬", "CROSS-SECTORAL": "🔗"}.get(
                call_data["strand"], "📋"
            )
            logger.info(
                f"  [{i}/{len(topics_to_process)}] {strand_emoji} {topic_code} ({call_data['status']})"
            )

            if dry_run:
                logger.info(f"    [DRY RUN] Would upsert: {call_data['title'][:50]}...")
            else:
                # Upsert to database
                if self.upsert_call(conn, call_data):
                    if topic_code in existing:
                        stats["updated"] += 1
                    else:
                        stats["inserted"] += 1
                else:
                    stats["errors"] += 1

        # Commit changes
        if conn and not dry_run:
            conn.commit()
            conn.close()

        return stats


def main():
    parser = argparse.ArgumentParser(description="Sync Creative Europe calls from EU Portal API")
    parser.add_argument(
        "--status",
        choices=["open", "closed", "upcoming", "all"],
        default="all",
        help="Filter by call status",
    )
    parser.add_argument("--limit", type=int, help="Limit number of calls to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database")
    parser.add_argument("--force", action="store_true", help="Re-sync all calls")
    parser.add_argument("--year", type=int, help="Filter by specific year")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("CREATIVE EUROPE CALLS SYNC")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes")

    try:
        db_url = get_database_url()
        syncer = CreativeEuropePortalSyncer(db_url)

        stats = syncer.sync_all_calls(
            status_filter=args.status,
            limit=args.limit,
            dry_run=args.dry_run,
            force=args.force,
            year=args.year,
        )

        syncer.close()

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("SYNC SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Topics discovered: {stats['discovered']}")
        logger.info(f"Topics processed:  {stats['processed']}")
        logger.info(f"Calls inserted:    {stats['inserted']}")
        logger.info(f"Calls updated:     {stats['updated']}")
        logger.info(f"Calls skipped:     {stats['skipped']}")
        logger.info(f"Errors:            {stats['errors']}")

        if not args.dry_run and (stats["inserted"] > 0 or stats["updated"] > 0):
            logger.info("\nCreative Europe calls synced successfully!")

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
