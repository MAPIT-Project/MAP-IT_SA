#!/usr/bin/env python3
"""
Ingest LIFE Programme Reference Data into Neo4j Graph Database.

This script populates Neo4j with LIFE programme structure:
1. LIFESubprogramme nodes (NAT, ENV, CCA, CET)
2. LIFEProjectType nodes (SAP, SIP, SNAP, TA, OG)
3. ParticipatingCountry relationships (country eligibility)
4. Relationships: BELONGS_TO_SUBPROGRAMME, ALLOWS_COORDINATOR_FROM, ALLOWS_PARTNER_FROM

Usage:
    python scripts/ingest_life_to_neo4j.py [--clear]
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.neo4j_config import neo4j_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class LIFENeo4jIngester:
    """
    Ingests LIFE Programme reference data into Neo4j for enhanced eligibility
    checking and recommendation capabilities.
    """

    # LIFE Sub-programmes
    LIFE_SUBPROGRAMMES = {
        "NAT": {
            "code": "NAT",
            "name": "Nature and Biodiversity",
            "description": "Conservation of nature, Natura 2000 network, species and habitats protection",
            "funding_rate": 75,
            "funding_rate_notes": "Up to 75% for priority species/habitats, 60% for other nature projects",
            "objectives": [
                "Protect and restore biodiversity",
                "Implement Natura 2000 network",
                "Combat invasive alien species",
                "Support green infrastructure",
            ],
            "priority_areas": [
                "Natura_2000",
                "species_conservation",
                "habitat_restoration",
                "invasive_species",
                "green_infrastructure",
            ],
        },
        "ENV": {
            "code": "ENV",
            "name": "Circular Economy and Quality of Life",
            "description": "Waste prevention, water, air, soil, chemicals, noise, resource efficiency",
            "funding_rate": 60,
            "funding_rate_notes": "Standard 60% EU co-financing",
            "objectives": [
                "Promote circular economy",
                "Improve water quality and management",
                "Improve air quality",
                "Protect and restore soil",
            ],
            "priority_areas": [
                "circular_economy",
                "waste_prevention",
                "water_management",
                "air_quality",
                "soil_protection",
                "chemicals",
            ],
        },
        "CCA": {
            "code": "CCA",
            "name": "Climate Change Mitigation and Adaptation",
            "description": "Reducing greenhouse gas emissions and adapting to climate change impacts",
            "funding_rate": 60,
            "funding_rate_notes": "Standard 60% EU co-financing",
            "objectives": [
                "Reduce greenhouse gas emissions",
                "Increase climate resilience",
                "Support climate adaptation strategies",
                "Promote sustainable land use",
            ],
            "priority_areas": [
                "GHG_reduction",
                "climate_adaptation",
                "resilience",
                "sustainable_agriculture",
                "urban_adaptation",
            ],
        },
        "CET": {
            "code": "CET",
            "name": "Clean Energy Transition",
            "description": "Supporting the transition to clean, efficient, renewable energy systems",
            "funding_rate": 95,
            "funding_rate_notes": "Up to 95% EU co-financing for coordination and support actions",
            "objectives": [
                "Accelerate clean energy transition",
                "Improve energy efficiency",
                "Increase renewable energy deployment",
                "Address energy poverty",
            ],
            "priority_areas": [
                "renewable_energy",
                "energy_efficiency",
                "energy_poverty",
                "building_renovation",
                "local_energy_communities",
            ],
        },
    }

    # LIFE Project Types
    LIFE_PROJECT_TYPES = {
        "SAP": {
            "code": "SAP",
            "name": "Standard Action Projects",
            "description": "Best practice, demonstration, pilot, and information projects",
            "subprogrammes": ["NAT", "ENV", "CCA", "CET"],
            "min_partners": 1,
            "typical_budget_min": 1000000,
            "typical_budget_max": 5000000,
            "typical_duration_months": 36,
            "notes": "Most common project type. Focus on testing and demonstrating solutions.",
        },
        "SIP": {
            "code": "SIP",
            "name": "Strategic Integrated Projects",
            "description": "Large-scale implementation of environmental/climate strategies and plans",
            "subprogrammes": ["ENV", "CCA"],
            "min_partners": 3,
            "min_countries": 2,
            "typical_budget_min": 10000000,
            "typical_budget_max": 30000000,
            "typical_duration_months": 72,
            "notes": "Requires alignment with approved national/regional strategies (e.g., waste, water, air, climate).",
        },
        "SNAP": {
            "code": "SNAP",
            "name": "Strategic Nature Projects",
            "description": "Large-scale implementation of Prioritised Action Frameworks for Natura 2000",
            "subprogrammes": ["NAT"],
            "min_partners": 3,
            "min_countries": 2,
            "typical_budget_min": 10000000,
            "typical_budget_max": 30000000,
            "typical_duration_months": 72,
            "notes": "Focus on Prioritised Action Frameworks (PAFs) for Natura 2000.",
        },
        "TA": {
            "code": "TA",
            "name": "Technical Assistance",
            "description": "Preparation of SIP/SNAP proposals and capacity building",
            "subprogrammes": ["NAT", "ENV", "CCA"],
            "min_partners": 1,
            "typical_budget_min": 500000,
            "typical_budget_max": 1000000,
            "typical_duration_months": 24,
            "notes": "Helps authorities prepare large strategic project proposals.",
        },
        "OG": {
            "code": "OG",
            "name": "Operating Grants",
            "description": "Support for NGO operations at EU level",
            "subprogrammes": ["NAT", "ENV", "CCA"],
            "min_partners": 1,
            "typical_budget_min": 200000,
            "typical_budget_max": 700000,
            "typical_duration_months": 12,
            "notes": "For EU-level environmental NGOs. Requires Framework Partnership Agreement.",
        },
    }

    # EU Member States (27)
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

    # EEA Countries (participate in LIFE under EEA Agreement)
    EEA_COUNTRIES = ["IS", "LI", "NO"]

    # Associated Countries
    ASSOCIATED_COUNTRIES = [
        "UA",
        "MD",
        "ME",
        "MK",
        "RS",
        "AL",
        "XK",
        "TR",
        "BA",
    ]

    # All participating countries
    ALL_PARTICIPATING = EU_MEMBER_STATES + EEA_COUNTRIES + ASSOCIATED_COUNTRIES

    # Country name mapping
    COUNTRY_NAMES = {
        "AT": "Austria",
        "BE": "Belgium",
        "BG": "Bulgaria",
        "HR": "Croatia",
        "CY": "Cyprus",
        "CZ": "Czech Republic",
        "DK": "Denmark",
        "EE": "Estonia",
        "FI": "Finland",
        "FR": "France",
        "DE": "Germany",
        "GR": "Greece",
        "HU": "Hungary",
        "IE": "Ireland",
        "IT": "Italy",
        "LV": "Latvia",
        "LT": "Lithuania",
        "LU": "Luxembourg",
        "MT": "Malta",
        "NL": "Netherlands",
        "PL": "Poland",
        "PT": "Portugal",
        "RO": "Romania",
        "SK": "Slovakia",
        "SI": "Slovenia",
        "ES": "Spain",
        "SE": "Sweden",
        "IS": "Iceland",
        "LI": "Liechtenstein",
        "NO": "Norway",
        "UA": "Ukraine",
        "MD": "Moldova",
        "ME": "Montenegro",
        "MK": "North Macedonia",
        "RS": "Serbia",
        "AL": "Albania",
        "XK": "Kosovo",
        "TR": "Türkiye",
        "BA": "Bosnia and Herzegovina",
    }

    def __init__(self):
        """Initialize the LIFE ingester."""
        self.db = neo4j_db
        logger.info("Initialized LIFE Neo4j Ingester")

    def create_constraints_and_indexes(self) -> None:
        """Create Neo4j constraints and indexes for LIFE data."""
        logger.info("Creating LIFE constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT life_subprog_code IF NOT EXISTS FOR (s:LIFESubprogramme) REQUIRE s.code IS UNIQUE",
            "CREATE CONSTRAINT life_project_type_code IF NOT EXISTS FOR (p:LIFEProjectType) REQUIRE p.code IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX life_subprog_funding IF NOT EXISTS FOR (s:LIFESubprogramme) ON (s.funding_rate)",
            "CREATE INDEX life_project_budget IF NOT EXISTS FOR (p:LIFEProjectType) ON (p.typical_budget_max)",
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

    def load_subprogrammes(self) -> None:
        """Load LIFE sub-programme nodes."""
        logger.info("Loading LIFE sub-programmes...")

        for _code, info in self.LIFE_SUBPROGRAMMES.items():
            self.db.execute_query(
                """
                MERGE (s:LIFESubprogramme {code: $code})
                SET s.name = $name,
                    s.description = $description,
                    s.funding_rate = $funding_rate,
                    s.funding_rate_notes = $funding_rate_notes,
                    s.objectives = $objectives,
                    s.priority_areas = $priority_areas
            """,
                info,
            )

        logger.info(f"Loaded {len(self.LIFE_SUBPROGRAMMES)} sub-programmes")

    def load_project_types(self) -> None:
        """Load LIFE project type nodes with full metadata."""
        logger.info("Loading LIFE project types...")

        for code, info in self.LIFE_PROJECT_TYPES.items():
            # Create project type node
            self.db.execute_query(
                """
                MERGE (p:LIFEProjectType {code: $code})
                SET p.name = $name,
                    p.description = $description,
                    p.min_partners = $min_partners,
                    p.min_countries = $min_countries,
                    p.typical_budget_min = $typical_budget_min,
                    p.typical_budget_max = $typical_budget_max,
                    p.typical_duration_months = $typical_duration_months,
                    p.notes = $notes
            """,
                {
                    **info,
                    "min_countries": info.get("min_countries", 1),
                },
            )

            # Link to sub-programmes
            for subprog_code in info["subprogrammes"]:
                self.db.execute_query(
                    """
                    MATCH (p:LIFEProjectType {code: $project_code})
                    MATCH (s:LIFESubprogramme {code: $subprog_code})
                    MERGE (p)-[:AVAILABLE_IN]->(s)
                """,
                    {"project_code": code, "subprog_code": subprog_code},
                )

        logger.info(f"Loaded {len(self.LIFE_PROJECT_TYPES)} project types")

    def load_country_regions(self) -> None:
        """Create country eligibility regions for LIFE."""
        logger.info("Loading LIFE country regions...")

        # Create EU Member States region
        self.db.execute_query(
            """
            MERGE (r:LIFERegion {code: 'EU_MEMBERS'})
            SET r.name = 'EU Member States',
                r.description = 'EU27 Member States - eligible for all LIFE calls',
                r.countries = $countries
        """,
            {"countries": self.EU_MEMBER_STATES},
        )

        # Create EEA region
        self.db.execute_query(
            """
            MERGE (r:LIFERegion {code: 'EEA'})
            SET r.name = 'EEA Countries',
                r.description = 'Iceland, Liechtenstein, Norway - participate under EEA Agreement',
                r.countries = $countries
        """,
            {"countries": self.EEA_COUNTRIES},
        )

        # Create Associated Countries region
        self.db.execute_query(
            """
            MERGE (r:LIFERegion {code: 'ASSOCIATED'})
            SET r.name = 'Associated Countries',
                r.description = 'Countries with association agreements',
                r.countries = $countries
        """,
            {"countries": self.ASSOCIATED_COUNTRIES},
        )

        # Create All Participating region
        self.db.execute_query(
            """
            MERGE (r:LIFERegion {code: 'ALL_PARTICIPATING'})
            SET r.name = 'All Participating Countries',
                r.description = 'EU27 + EEA + Associated Countries eligible for LIFE',
                r.countries = $countries
        """,
            {"countries": self.ALL_PARTICIPATING},
        )

        logger.info("Loaded 4 country regions")

    def create_project_country_relationships(self) -> None:
        """Create relationships between project types and country eligibility."""
        logger.info("Creating project type-country relationships...")

        for code in self.LIFE_PROJECT_TYPES.keys():
            # All participating countries can be coordinators/partners
            self.db.execute_query(
                """
                MATCH (p:LIFEProjectType {code: $project_code})
                MATCH (r:LIFERegion {code: 'ALL_PARTICIPATING'})
                MERGE (p)-[:ALLOWS_COORDINATOR_FROM]->(r)
                MERGE (p)-[:ALLOWS_PARTNER_FROM]->(r)
            """,
                {"project_code": code},
            )

        logger.info("Project type-country relationships created")

    def link_existing_countries(self) -> None:
        """Link existing Country nodes to LIFE regions."""
        logger.info("Linking countries to LIFE regions...")

        # Mark EU Member States
        for country in self.EU_MEMBER_STATES:
            self.db.execute_query(
                """
                MERGE (c:Country {isoCode: $country_code})
                SET c.life_eligible = true,
                    c.name = $country_name
                WITH c
                MATCH (r:LIFERegion {code: 'EU_MEMBERS'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:LIFERegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """,
                {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)},
            )

        # Mark EEA Countries
        for country in self.EEA_COUNTRIES:
            self.db.execute_query(
                """
                MERGE (c:Country {isoCode: $country_code})
                SET c.life_eligible = true,
                    c.name = $country_name
                WITH c
                MATCH (r:LIFERegion {code: 'EEA'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:LIFERegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """,
                {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)},
            )

        # Mark Associated Countries
        for country in self.ASSOCIATED_COUNTRIES:
            self.db.execute_query(
                """
                MERGE (c:Country {isoCode: $country_code})
                SET c.life_eligible = true,
                    c.name = $country_name
                WITH c
                MATCH (r:LIFERegion {code: 'ASSOCIATED'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:LIFERegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """,
                {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)},
            )

        logger.info("Country-region relationships created")

    def create_programme_metadata(self) -> None:
        """Create LIFE programme metadata node."""
        logger.info("Creating LIFE programme metadata...")

        self.db.execute_query(
            """
            MERGE (p:Programme {code: 'LIFE'})
            SET p.name = 'LIFE',
                p.full_name = 'LIFE Programme for Environment and Climate Action 2021-2027',
                p.budget = 5432000000,
                p.budget_formatted = '€5.432 billion',
                p.start_year = 2021,
                p.end_year = 2027,
                p.implementing_agency = 'CINEA',
                p.implementing_agency_full = 'European Climate, Infrastructure and Environment Executive Agency',
                p.legal_basis = 'Regulation (EU) 2021/783',
                p.website = 'https://cinea.ec.europa.eu/programmes/life_en',
                p.description = 'EU funding instrument for the environment and climate action'
        """
        )

        # Link sub-programmes to programme
        for subprog_code in self.LIFE_SUBPROGRAMMES.keys():
            self.db.execute_query(
                """
                MATCH (p:Programme {code: 'LIFE'})
                MATCH (s:LIFESubprogramme {code: $subprog_code})
                MERGE (s)-[:PART_OF]->(p)
            """,
                {"subprog_code": subprog_code},
            )

        logger.info("Programme metadata created")

    def create_synergies(self) -> None:
        """Create synergy relationships with other programmes."""
        logger.info("Creating programme synergy relationships...")

        synergies = [
            ("HORIZON_EUROPE", "Horizon Europe", "Research and innovation synergies"),
            (
                "ERDF",
                "European Regional Development Fund",
                "Regional environment and climate investments",
            ),
            ("CAP", "Common Agricultural Policy", "Agri-environment and climate measures"),
            (
                "EMFAF",
                "European Maritime and Fisheries Fund",
                "Marine environment and biodiversity",
            ),
        ]

        for prog_code, prog_name, synergy_desc in synergies:
            self.db.execute_query(
                """
                MERGE (p2:Programme {code: $prog_code})
                SET p2.name = $prog_name
                WITH p2
                MATCH (p1:Programme {code: 'LIFE'})
                MERGE (p1)-[s:HAS_SYNERGY_WITH]->(p2)
                SET s.description = $synergy_desc
            """,
                {"prog_code": prog_code, "prog_name": prog_name, "synergy_desc": synergy_desc},
            )

        logger.info(f"Created {len(synergies)} synergy relationships")

    def clear_life_data(self) -> None:
        """Clear only LIFE specific nodes and relationships."""
        logger.warning("Clearing LIFE data from Neo4j...")

        queries = [
            "MATCH (p:LIFEProjectType) DETACH DELETE p",
            "MATCH (s:LIFESubprogramme) DETACH DELETE s",
            "MATCH (r:LIFERegion) DETACH DELETE r",
            "MATCH (p:Programme {code: 'LIFE'}) DETACH DELETE p",
        ]

        for query in queries:
            self.db.execute_query(query)

        logger.info("LIFE data cleared")

    def run(self, clear_first: bool = False) -> dict[str, int]:
        """
        Run the complete LIFE ingestion pipeline.

        Args:
            clear_first: If True, clear LIFE data before ingestion

        Returns:
            Statistics dict
        """
        logger.info("=" * 60)
        logger.info("LIFE PROGRAMME -> Neo4j Reference Data Ingestion")
        logger.info("=" * 60)

        if clear_first:
            self.clear_life_data()

        # Step 1: Create constraints/indexes
        self.create_constraints_and_indexes()

        # Step 2: Load sub-programmes
        self.load_subprogrammes()

        # Step 3: Load project types
        self.load_project_types()

        # Step 4: Load country regions
        self.load_country_regions()

        # Step 5: Create project type-country relationships
        self.create_project_country_relationships()

        # Step 6: Link existing countries
        self.link_existing_countries()

        # Step 7: Create programme metadata
        self.create_programme_metadata()

        # Step 8: Create synergies
        self.create_synergies()

        # Get stats
        stats = self._get_stats()
        self._print_summary(stats)

        return stats

    def _get_stats(self) -> dict[str, int]:
        """Get current LIFE data statistics."""
        query = """
        MATCH (s:LIFESubprogramme) WITH count(s) as subprogrammes
        MATCH (p:LIFEProjectType) WITH subprogrammes, count(p) as project_types
        MATCH (r:LIFERegion) WITH subprogrammes, project_types, count(r) as regions
        OPTIONAL MATCH (:LIFEProjectType)-[rel:AVAILABLE_IN]->()
            WITH subprogrammes, project_types, regions, count(rel) as available_rels
        OPTIONAL MATCH (:LIFEProjectType)-[rel2:ALLOWS_COORDINATOR_FROM]->()
            WITH subprogrammes, project_types, regions, available_rels, count(rel2) as coord_rels
        OPTIONAL MATCH (:LIFEProjectType)-[rel3:ALLOWS_PARTNER_FROM]->()
            WITH subprogrammes, project_types, regions, available_rels, coord_rels, count(rel3) as partner_rels
        OPTIONAL MATCH (:Country)-[rel4:MEMBER_OF]->(:LIFERegion)
            WITH subprogrammes, project_types, regions, available_rels, coord_rels, partner_rels, count(rel4) as country_rels
        OPTIONAL MATCH (prog:Programme {code: 'LIFE'})
            WITH subprogrammes, project_types, regions, available_rels, coord_rels, partner_rels, country_rels, count(prog) as programme
        OPTIONAL MATCH (:Programme {code: 'LIFE'})-[syn:HAS_SYNERGY_WITH]->()
            WITH subprogrammes, project_types, regions, available_rels, coord_rels, partner_rels, country_rels, programme, count(syn) as synergies
        RETURN subprogrammes, project_types, regions, available_rels, coord_rels, partner_rels, country_rels, programme, synergies
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
        logger.info("LIFE INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"LIFESubprogramme nodes: {stats.get('subprogrammes', 0)}")
        logger.info(f"LIFEProjectType nodes: {stats.get('project_types', 0)}")
        logger.info(f"LIFERegion nodes: {stats.get('regions', 0)}")
        logger.info(f"Programme nodes: {stats.get('programme', 0)}")
        logger.info(f"AVAILABLE_IN relationships: {stats.get('available_rels', 0)}")
        logger.info(f"ALLOWS_COORDINATOR_FROM relationships: {stats.get('coord_rels', 0)}")
        logger.info(f"ALLOWS_PARTNER_FROM relationships: {stats.get('partner_rels', 0)}")
        logger.info(f"Country MEMBER_OF relationships: {stats.get('country_rels', 0)}")
        logger.info(f"Programme synergies: {stats.get('synergies', 0)}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest LIFE Programme data into Neo4j")
    parser.add_argument("--clear", action="store_true", help="Clear LIFE data before ingestion")

    args = parser.parse_args()

    try:
        ingester = LIFENeo4jIngester()
        stats = ingester.run(clear_first=args.clear)

        if stats.get("subprogrammes", 0) > 0:
            logger.info("\nLIFE Programme reference data loaded successfully!")
            logger.info("You can now use graph-based eligibility checking for LIFE.")
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
