#!/usr/bin/env python3
"""
Ingest Creative Europe Reference Data into Neo4j Graph Database.

This script populates Neo4j with Creative Europe programme structure:
1. CreativeEuropeStrand nodes (CULTURE, MEDIA, CROSS-SECTORAL)
2. CreativeEuropeAction nodes (all 24 action types with full metadata)
3. ParticipatingCountry relationships (country eligibility by strand)
4. Relationships: BELONGS_TO_STRAND, ALLOWS_COORDINATOR_FROM, ALLOWS_PARTNER_FROM

Usage:
    python scripts/ingest_creative_europe_to_neo4j.py [--clear]
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.neo4j_config import neo4j_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CreativeEuropeNeo4jIngester:
    """
    Ingests Creative Europe reference data into Neo4j for enhanced eligibility
    checking and recommendation capabilities.
    """

    # Creative Europe Strands
    CREATIVE_EUROPE_STRANDS = {
        "CULTURE": {
            "code": "CULTURE",
            "name": "CULTURE Strand",
            "description": "Support for cultural and creative sectors - cooperation projects, networks, platforms, literary translation",
            "budget_share": 33,  # Percentage of total programme budget
            "org_types": ["CULTURAL_ORG", "NGO", "PUBLIC_BODY", "SME", "RESEARCH", "CONSORTIUM"],
        },
        "MEDIA": {
            "code": "MEDIA",
            "name": "MEDIA Strand",
            "description": "Support for audiovisual and film industries - development, distribution, training, festivals, cinema networks",
            "budget_share": 58,
            "org_types": [
                "PRODUCTION",
                "AUDIOVISUAL",
                "DISTRIBUTION",
                "BROADCASTER",
                "CINEMA",
                "FESTIVAL",
                "TRAINING",
                "SME",
            ],
        },
        "CROSS-SECTORAL": {
            "code": "CROSS-SECTORAL",
            "name": "Cross-Sectoral Strand",
            "description": "Cross-cutting initiatives - Creative Innovation Labs, news media partnerships, media literacy",
            "budget_share": 9,
            "org_types": [
                "CULTURAL_ORG",
                "AUDIOVISUAL",
                "SME",
                "RESEARCH",
                "NEWS_MEDIA",
                "NGO",
                "PUBLIC_BODY",
            ],
        },
    }

    # Creative Europe Actions with full metadata
    CREATIVE_EUROPE_ACTIONS = {
        # CULTURE strand actions
        "COOP-SMALL": {
            "code": "COOP-SMALL",
            "name": "European Cooperation Projects - Small Scale",
            "strand": "CULTURE",
            "description": "Smaller-scale transnational cultural cooperation projects",
            "min_partners": 3,
            "min_countries": 3,
            "grant_min": 200000,
            "grant_max": 200000,
            "funding_rate": 80,
            "duration_months_max": 48,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "NGO", "PUBLIC_BODY", "SME", "RESEARCH"],
        },
        "COOP-MEDIUM": {
            "code": "COOP-MEDIUM",
            "name": "European Cooperation Projects - Medium Scale",
            "strand": "CULTURE",
            "description": "Medium-scale transnational cultural cooperation projects",
            "min_partners": 5,
            "min_countries": 5,
            "grant_min": 1000000,
            "grant_max": 1000000,
            "funding_rate": 70,
            "duration_months_max": 48,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "NGO", "PUBLIC_BODY", "SME", "RESEARCH"],
        },
        "COOP-LARGE": {
            "code": "COOP-LARGE",
            "name": "European Cooperation Projects - Large Scale",
            "strand": "CULTURE",
            "description": "Large-scale transnational cultural cooperation projects with significant impact",
            "min_partners": 10,
            "min_countries": 10,
            "grant_min": 2000000,
            "grant_max": 2000000,
            "funding_rate": 60,
            "duration_months_max": 48,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "NGO", "PUBLIC_BODY", "SME", "RESEARCH"],
        },
        "NETWORK": {
            "code": "NETWORK",
            "name": "European Networks",
            "strand": "CULTURE",
            "description": "Networks of cultural organizations to strengthen capacity and internationalization",
            "min_partners": 15,
            "min_countries": 10,
            "grant_min": 2400000,
            "grant_max": 2400000,
            "funding_rate": 80,
            "duration_months_max": 48,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "NGO", "CONSORTIUM", "PUBLIC_BODY"],
        },
        "PLATFORM": {
            "code": "PLATFORM",
            "name": "European Platforms",
            "strand": "CULTURE",
            "description": "Platforms promoting emerging artists and their works",
            "min_partners": 12,
            "min_countries": 12,
            "grant_min": 2000000,
            "grant_max": 2000000,
            "funding_rate": 80,
            "duration_months_max": 48,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "NGO", "CONSORTIUM", "PUBLIC_BODY"],
        },
        "LITERARY": {
            "code": "LITERARY",
            "name": "European Literary Translation",
            "strand": "CULTURE",
            "description": "Translation, publication and promotion of fiction works",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 100000,
            "grant_max": 100000,
            "funding_rate": 60,
            "duration_months_max": 36,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "SME"],
        },
        # MEDIA strand - Development actions
        "DEVSLATE": {
            "code": "DEVSLATE",
            "name": "MEDIA Development - Slate Funding",
            "strand": "MEDIA",
            "description": "Support for development of a slate of 3-5 audiovisual works",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 150000,
            "grant_max": 210000,
            "funding_rate": 70,
            "duration_months_max": 36,
            "funding_model": "lump_sum",
            "org_types": ["PRODUCTION", "AUDIOVISUAL", "SME"],
        },
        "DEVSINGLE": {
            "code": "DEVSINGLE",
            "name": "MEDIA Development - Single Project",
            "strand": "MEDIA",
            "description": "Development of a single audiovisual work (film, animation, documentary)",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 30000,
            "grant_max": 60000,
            "funding_rate": 50,
            "duration_months_max": 24,
            "funding_model": "lump_sum",
            "org_types": ["PRODUCTION", "AUDIOVISUAL", "SME"],
        },
        "DEVMINISLATE": {
            "code": "DEVMINISLATE",
            "name": "MEDIA Development - Mini-Slate",
            "strand": "MEDIA",
            "description": "Development of 2-3 audiovisual works for newer companies",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 75000,
            "grant_max": 105000,
            "funding_rate": 60,
            "duration_months_max": 24,
            "funding_model": "lump_sum",
            "org_types": ["PRODUCTION", "AUDIOVISUAL", "SME"],
        },
        "CODEV": {
            "code": "CODEV",
            "name": "MEDIA Co-Development",
            "strand": "MEDIA",
            "description": "European co-development of audiovisual works",
            "min_partners": 2,
            "min_countries": 2,
            "grant_min": 60000,
            "grant_max": 100000,
            "funding_rate": 50,
            "duration_months_max": 24,
            "funding_model": "lump_sum",
            "org_types": ["PRODUCTION", "AUDIOVISUAL"],
        },
        "DEVVGIM": {
            "code": "DEVVGIM",
            "name": "MEDIA Video Games & Immersive Content",
            "strand": "MEDIA",
            "description": "Development of video games and immersive content",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 150000,
            "grant_max": 200000,
            "funding_rate": 50,
            "duration_months_max": 24,
            "funding_model": "lump_sum",
            "org_types": ["AUDIOVISUAL", "SME", "PRODUCTION"],
        },
        # MEDIA strand - Production/Content
        "TVONLINE": {
            "code": "TVONLINE",
            "name": "MEDIA TV and Online Content",
            "strand": "MEDIA",
            "description": "Production of TV series and online content with cross-border potential",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 1000000,
            "grant_max": 3000000,
            "funding_rate": 80,
            "duration_months_max": 36,
            "funding_model": "actual_costs",
            "org_types": ["PRODUCTION", "BROADCASTER", "AUDIOVISUAL"],
        },
        # MEDIA strand - Training/Markets
        "TRAINING": {
            "code": "TRAINING",
            "name": "MEDIA Training",
            "strand": "MEDIA",
            "description": "Training activities for audiovisual professionals",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 150000,
            "grant_max": 400000,
            "funding_rate": 80,
            "duration_months_max": 24,
            "funding_model": "lump_sum",
            "org_types": ["TRAINING", "AUDIOVISUAL", "NGO", "RESEARCH"],
        },
        "MARKETNET": {
            "code": "MARKETNET",
            "name": "MEDIA Markets and Networking",
            "strand": "MEDIA",
            "description": "Markets, pitching events, and industry networking activities",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 500000,
            "grant_max": 1000000,
            "funding_rate": 80,
            "duration_months_max": 36,
            "funding_model": "lump_sum",
            "org_types": ["AUDIOVISUAL", "FESTIVAL", "CONSORTIUM", "NGO"],
        },
        # MEDIA strand - Distribution
        "FILMDIST": {
            "code": "FILMDIST",
            "name": "MEDIA Film Distribution",
            "strand": "MEDIA",
            "description": "Grouping of distributors for non-national European films",
            "min_partners": 5,
            "min_countries": 5,
            "grant_min": 200000,
            "grant_max": 400000,
            "funding_rate": 60,
            "duration_months_max": 24,
            "funding_model": "unit_cost",
            "org_types": ["DISTRIBUTION", "AUDIOVISUAL"],
        },
        "FILMSALES": {
            "code": "FILMSALES",
            "name": "MEDIA Film Sales Agents",
            "strand": "MEDIA",
            "description": "Support for international sales agents of European films",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 300000,
            "grant_max": 500000,
            "funding_rate": 80,
            "duration_months_max": 24,
            "funding_model": "unit_cost",
            "org_types": ["DISTRIBUTION", "AUDIOVISUAL"],
        },
        "CINNET": {
            "code": "CINNET",
            "name": "MEDIA Cinema Networks",
            "strand": "MEDIA",
            "description": "Europa Cinemas network supporting European film exhibition",
            "min_partners": 100,
            "min_countries": 20,
            "grant_min": 5000000,
            "grant_max": 7000000,
            "funding_rate": 50,
            "duration_months_max": 24,
            "funding_model": "unit_cost",
            "org_types": ["CINEMA", "CONSORTIUM"],
        },
        # MEDIA strand - Festivals/Audience
        "FEST": {
            "code": "FEST",
            "name": "MEDIA Film Festivals",
            "strand": "MEDIA",
            "description": "European film festivals with significant European programming",
            "min_partners": 1,
            "min_countries": 1,
            "grant_min": 75000,
            "grant_max": 150000,
            "funding_rate": 80,
            "duration_months_max": 24,
            "funding_model": "lump_sum",
            "org_types": ["FESTIVAL", "CULTURAL_ORG", "NGO"],
        },
        "AUDFILMEDU": {
            "code": "AUDFILMEDU",
            "name": "MEDIA Audience Development - Film Education",
            "strand": "MEDIA",
            "description": "Film literacy and audience development projects",
            "min_partners": 3,
            "min_countries": 3,
            "grant_min": 400000,
            "grant_max": 600000,
            "funding_rate": 80,
            "duration_months_max": 36,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "TRAINING", "NGO", "RESEARCH"],
        },
        "INNOVBUSMOD": {
            "code": "INNOVBUSMOD",
            "name": "MEDIA Innovative Business Models",
            "strand": "MEDIA",
            "description": "Innovation in audiovisual value chain, promotion tools, data analytics",
            "min_partners": 3,
            "min_countries": 3,
            "grant_min": 500000,
            "grant_max": 1000000,
            "funding_rate": 70,
            "duration_months_max": 36,
            "funding_model": "lump_sum",
            "org_types": ["AUDIOVISUAL", "SME", "BROADCASTER"],
        },
        # Cross-sectoral strand
        "INNOVLAB": {
            "code": "INNOVLAB",
            "name": "Creative Innovation Lab",
            "strand": "CROSS-SECTORAL",
            "description": "Cross-sector innovation labs combining culture, technology, and media",
            "min_partners": 3,
            "min_countries": 3,
            "grant_min": 2000000,
            "grant_max": 4000000,
            "funding_rate": 60,
            "duration_months_max": 48,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "AUDIOVISUAL", "SME", "RESEARCH", "NEWS_MEDIA"],
        },
        "JOURPART": {
            "code": "JOURPART",
            "name": "News Media Partnerships",
            "strand": "CROSS-SECTORAL",
            "description": "Cross-border collaborations of news media organizations",
            "min_partners": 3,
            "min_countries": 3,
            "grant_min": 1000000,
            "grant_max": 3000000,
            "funding_rate": 80,
            "duration_months_max": 36,
            "funding_model": "lump_sum",
            "org_types": ["NEWS_MEDIA", "NGO", "RESEARCH"],
        },
        "MEDIALITERACY": {
            "code": "MEDIALITERACY",
            "name": "Media Literacy",
            "strand": "CROSS-SECTORAL",
            "description": "Media literacy projects countering disinformation",
            "min_partners": 3,
            "min_countries": 3,
            "grant_min": 500000,
            "grant_max": 2000000,
            "funding_rate": 70,
            "duration_months_max": 36,
            "funding_model": "lump_sum",
            "org_types": ["NGO", "PUBLIC_BODY", "RESEARCH", "NEWS_MEDIA"],
        },
        "MFP": {
            "code": "MFP",
            "name": "Music Moves Europe",
            "strand": "CROSS-SECTORAL",
            "description": "Music sector support including cross-border distribution, touring, training",
            "min_partners": 3,
            "min_countries": 3,
            "grant_min": 500000,
            "grant_max": 1500000,
            "funding_rate": 70,
            "duration_months_max": 36,
            "funding_model": "lump_sum",
            "org_types": ["CULTURAL_ORG", "SME", "FESTIVAL", "NGO"],
        },
    }

    # EU Member States (Creative Europe participating countries)
    EU_MEMBER_STATES = [
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    ]

    # Associated Countries (full Creative Europe participation)
    ASSOCIATED_COUNTRIES = [
        "IS",
        "LI",
        "NO",  # EEA
        "AL",
        "BA",
        "GE",
        "XK",
        "MD",
        "ME",
        "MK",
        "RS",
        "TN",
        "UA",  # Other associated
    ]

    # MEDIA sub-programme countries (more restricted - not all associated countries)
    MEDIA_COUNTRIES = EU_MEMBER_STATES + [
        "IS",
        "LI",
        "NO",  # EEA
        "AL",
        "BA",
        "GE",
        "XK",
        "ME",
        "MK",
        "RS",
        "UA",  # MEDIA participants
    ]

    # All participating countries
    ALL_PARTICIPATING = list(set(EU_MEMBER_STATES + ASSOCIATED_COUNTRIES))

    def __init__(self):
        """Initialize the Creative Europe ingester."""
        self.db = neo4j_db
        logger.info("Initialized Creative Europe Neo4j Ingester")

    def create_constraints_and_indexes(self) -> None:
        """Create Neo4j constraints and indexes for Creative Europe data."""
        logger.info("Creating Creative Europe constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT ce_strand_code IF NOT EXISTS FOR (s:CreativeEuropeStrand) REQUIRE s.code IS UNIQUE",
            "CREATE CONSTRAINT ce_action_code IF NOT EXISTS FOR (a:CreativeEuropeAction) REQUIRE a.code IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX ce_action_strand IF NOT EXISTS FOR (a:CreativeEuropeAction) ON (a.strand)",
            "CREATE INDEX ce_action_funding IF NOT EXISTS FOR (a:CreativeEuropeAction) ON (a.funding_rate)",
        ]

        for constraint in constraints:
            try:
                self.db.execute_query(constraint)
                logger.debug(f"Created: {constraint[:50]}...")
            except Exception as e:
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    logger.debug(f"Already exists: {constraint[:40]}...")
                else:
                    logger.warning(f"Constraint warning: {e}")

        for index in indexes:
            try:
                self.db.execute_query(index)
                logger.debug(f"Created: {index[:50]}...")
            except Exception as e:
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    logger.debug(f"Already exists: {index[:40]}...")
                else:
                    logger.warning(f"Index warning: {e}")

        logger.info("Constraints and indexes ready")

    def load_strands(self) -> None:
        """Load Creative Europe strand nodes."""
        logger.info("Loading Creative Europe strands...")

        for _code, info in self.CREATIVE_EUROPE_STRANDS.items():
            self.db.execute_query(
                """
                MERGE (s:CreativeEuropeStrand {code: $code})
                SET s.name = $name,
                    s.description = $description,
                    s.budget_share = $budget_share,
                    s.org_types = $org_types
            """,
                info,
            )

        logger.info(f"Loaded {len(self.CREATIVE_EUROPE_STRANDS)} strands")

    def load_actions(self) -> None:
        """Load Creative Europe action nodes with full metadata."""
        logger.info("Loading Creative Europe actions...")

        for code, info in self.CREATIVE_EUROPE_ACTIONS.items():
            # Create action node
            self.db.execute_query(
                """
                MERGE (a:CreativeEuropeAction {code: $code})
                SET a.name = $name,
                    a.strand = $strand,
                    a.description = $description,
                    a.min_partners = $min_partners,
                    a.min_countries = $min_countries,
                    a.grant_min = $grant_min,
                    a.grant_max = $grant_max,
                    a.funding_rate = $funding_rate,
                    a.duration_months_max = $duration_months_max,
                    a.funding_model = $funding_model,
                    a.org_types = $org_types
            """,
                info,
            )

            # Link to strand
            self.db.execute_query(
                """
                MATCH (a:CreativeEuropeAction {code: $action_code})
                MATCH (s:CreativeEuropeStrand {code: $strand_code})
                MERGE (a)-[:BELONGS_TO_STRAND]->(s)
            """,
                {"action_code": code, "strand_code": info["strand"]},
            )

        logger.info(f"Loaded {len(self.CREATIVE_EUROPE_ACTIONS)} actions")

    def load_country_regions(self) -> None:
        """Create country eligibility regions for Creative Europe."""
        logger.info("Loading Creative Europe country regions...")

        # Create EU+Associated region (all participating)
        self.db.execute_query(
            """
            MERGE (r:CreativeEuropeRegion {code: 'ALL_PARTICIPATING'})
            SET r.name = 'All Participating Countries',
                r.description = 'EU Member States and Associated Countries',
                r.countries = $countries
        """,
            {"countries": self.ALL_PARTICIPATING},
        )

        # Create MEDIA-specific region
        self.db.execute_query(
            """
            MERGE (r:CreativeEuropeRegion {code: 'MEDIA_COUNTRIES'})
            SET r.name = 'MEDIA Sub-programme Countries',
                r.description = 'Countries with full MEDIA sub-programme participation',
                r.countries = $countries
        """,
            {"countries": self.MEDIA_COUNTRIES},
        )

        # Create EU-only region
        self.db.execute_query(
            """
            MERGE (r:CreativeEuropeRegion {code: 'EU_MEMBERS'})
            SET r.name = 'EU Member States',
                r.description = 'EU27 Member States',
                r.countries = $countries
        """,
            {"countries": self.EU_MEMBER_STATES},
        )

        logger.info("Loaded 3 country regions")

    def create_strand_country_relationships(self) -> None:
        """Create relationships between strands and country regions."""
        logger.info("Creating strand-country relationships...")

        # CULTURE strand - all participating countries
        self.db.execute_query(
            """
            MATCH (s:CreativeEuropeStrand {code: 'CULTURE'})
            MATCH (r:CreativeEuropeRegion {code: 'ALL_PARTICIPATING'})
            MERGE (s)-[:ALLOWS_COUNTRIES]->(r)
        """
        )

        # MEDIA strand - MEDIA countries only
        self.db.execute_query(
            """
            MATCH (s:CreativeEuropeStrand {code: 'MEDIA'})
            MATCH (r:CreativeEuropeRegion {code: 'MEDIA_COUNTRIES'})
            MERGE (s)-[:ALLOWS_COUNTRIES]->(r)
        """
        )

        # Cross-sectoral - all participating countries
        self.db.execute_query(
            """
            MATCH (s:CreativeEuropeStrand {code: 'CROSS-SECTORAL'})
            MATCH (r:CreativeEuropeRegion {code: 'ALL_PARTICIPATING'})
            MERGE (s)-[:ALLOWS_COUNTRIES]->(r)
        """
        )

        logger.info("Strand-country relationships created")

    def create_action_country_relationships(self) -> None:
        """Create relationships between actions and country eligibility."""
        logger.info("Creating action-country relationships...")

        for code, info in self.CREATIVE_EUROPE_ACTIONS.items():
            strand = info["strand"]

            # Determine country region based on strand
            if strand == "MEDIA":
                region = "MEDIA_COUNTRIES"
            else:
                region = "ALL_PARTICIPATING"

            # Coordinator must be from eligible countries
            self.db.execute_query(
                """
                MATCH (a:CreativeEuropeAction {code: $action_code})
                MATCH (r:CreativeEuropeRegion {code: $region_code})
                MERGE (a)-[:ALLOWS_COORDINATOR_FROM]->(r)
            """,
                {"action_code": code, "region_code": region},
            )

            # Partners from same region
            self.db.execute_query(
                """
                MATCH (a:CreativeEuropeAction {code: $action_code})
                MATCH (r:CreativeEuropeRegion {code: $region_code})
                MERGE (a)-[:ALLOWS_PARTNER_FROM]->(r)
            """,
                {"action_code": code, "region_code": region},
            )

        logger.info("Action-country relationships created")

    def link_existing_countries(self) -> None:
        """Link existing Country nodes to Creative Europe regions."""
        logger.info("Linking countries to Creative Europe regions...")

        # Mark EU Member States
        for country in self.EU_MEMBER_STATES:
            self.db.execute_query(
                """
                MERGE (c:Country {isoCode: $country_code})
                SET c.creative_europe_eligible = true,
                    c.creative_europe_media_eligible = true
                WITH c
                MATCH (r:CreativeEuropeRegion {code: 'EU_MEMBERS'})
                MERGE (c)-[:MEMBER_OF]->(r)
            """,
                {"country_code": country},
            )

        # Mark Associated Countries
        for country in self.ASSOCIATED_COUNTRIES:
            is_media = country in self.MEDIA_COUNTRIES
            self.db.execute_query(
                """
                MERGE (c:Country {isoCode: $country_code})
                SET c.creative_europe_eligible = true,
                    c.creative_europe_media_eligible = $is_media
                WITH c
                MATCH (r:CreativeEuropeRegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r)
            """,
                {"country_code": country, "is_media": is_media},
            )

        # Link MEDIA countries to MEDIA region
        for country in self.MEDIA_COUNTRIES:
            self.db.execute_query(
                """
                MATCH (c:Country {isoCode: $country_code})
                MATCH (r:CreativeEuropeRegion {code: 'MEDIA_COUNTRIES'})
                MERGE (c)-[:MEMBER_OF]->(r)
            """,
                {"country_code": country},
            )

        logger.info("Country-region relationships created")

    def clear_creative_europe_data(self) -> None:
        """Clear only Creative Europe specific nodes and relationships."""
        logger.warning("Clearing Creative Europe data from Neo4j...")

        queries = [
            "MATCH (a:CreativeEuropeAction) DETACH DELETE a",
            "MATCH (s:CreativeEuropeStrand) DETACH DELETE s",
            "MATCH (r:CreativeEuropeRegion) DETACH DELETE r",
        ]

        for query in queries:
            self.db.execute_query(query)

        logger.info("Creative Europe data cleared")

    def run(self, clear_first: bool = False) -> dict[str, int]:
        """
        Run the complete Creative Europe ingestion pipeline.

        Args:
            clear_first: If True, clear Creative Europe data before ingestion

        Returns:
            Statistics dict
        """
        logger.info("=" * 60)
        logger.info("CREATIVE EUROPE -> Neo4j Reference Data Ingestion")
        logger.info("=" * 60)

        if clear_first:
            self.clear_creative_europe_data()

        # Step 1: Create constraints/indexes
        self.create_constraints_and_indexes()

        # Step 2: Load strands
        self.load_strands()

        # Step 3: Load actions
        self.load_actions()

        # Step 4: Load country regions
        self.load_country_regions()

        # Step 5: Create strand-country relationships
        self.create_strand_country_relationships()

        # Step 6: Create action-country relationships
        self.create_action_country_relationships()

        # Step 7: Link existing countries
        self.link_existing_countries()

        # Get stats
        stats = self._get_stats()
        self._print_summary(stats)

        return stats

    def _get_stats(self) -> dict[str, int]:
        """Get current Creative Europe data statistics."""
        query = """
        MATCH (s:CreativeEuropeStrand) WITH count(s) as strands
        MATCH (a:CreativeEuropeAction) WITH strands, count(a) as actions
        MATCH (r:CreativeEuropeRegion) WITH strands, actions, count(r) as regions
        OPTIONAL MATCH (:CreativeEuropeAction)-[rel:BELONGS_TO_STRAND]->()
            WITH strands, actions, regions, count(rel) as strand_rels
        OPTIONAL MATCH (:CreativeEuropeAction)-[rel2:ALLOWS_COORDINATOR_FROM]->()
            WITH strands, actions, regions, strand_rels, count(rel2) as coord_rels
        OPTIONAL MATCH (:CreativeEuropeAction)-[rel3:ALLOWS_PARTNER_FROM]->()
            WITH strands, actions, regions, strand_rels, coord_rels, count(rel3) as partner_rels
        OPTIONAL MATCH (:Country)-[rel4:MEMBER_OF]->(:CreativeEuropeRegion)
            WITH strands, actions, regions, strand_rels, coord_rels, partner_rels, count(rel4) as country_rels
        RETURN strands, actions, regions, strand_rels, coord_rels, partner_rels, country_rels
        """

        try:
            result = self.db.execute_query(query)
            if result:
                return result[0]
        except Exception as e:
            logger.error(f"Error getting stats: {e}")

        return {}

    def _print_summary(self, stats: dict[str, int]) -> None:
        """Print ingestion summary."""
        logger.info("\n" + "=" * 60)
        logger.info("CREATIVE EUROPE INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"CreativeEuropeStrand nodes: {stats.get('strands', 0)}")
        logger.info(f"CreativeEuropeAction nodes: {stats.get('actions', 0)}")
        logger.info(f"CreativeEuropeRegion nodes: {stats.get('regions', 0)}")
        logger.info(f"BELONGS_TO_STRAND relationships: {stats.get('strand_rels', 0)}")
        logger.info(f"ALLOWS_COORDINATOR_FROM relationships: {stats.get('coord_rels', 0)}")
        logger.info(f"ALLOWS_PARTNER_FROM relationships: {stats.get('partner_rels', 0)}")
        logger.info(f"Country MEMBER_OF relationships: {stats.get('country_rels', 0)}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest Creative Europe data into Neo4j")
    parser.add_argument(
        "--clear", action="store_true", help="Clear Creative Europe data before ingestion"
    )

    args = parser.parse_args()

    try:
        ingester = CreativeEuropeNeo4jIngester()
        stats = ingester.run(clear_first=args.clear)

        if stats.get("actions", 0) > 0:
            logger.info("\nCreative Europe reference data loaded successfully!")
            logger.info("You can now use graph-based eligibility checking.")
            return 0
        else:
            logger.warning("No data was loaded")
            return 1

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
