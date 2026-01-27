#!/usr/bin/env python3
"""
Ingest Digital Europe Reference Data into Neo4j Graph Database.

This script populates Neo4j with Digital Europe programme structure:
1. DigitalEuropeObjective nodes (HPC, AI, Cybersecurity, Skills, Deployment, Semiconductors)
2. DigitalEuropeAction nodes (Grant, Procurement with full metadata)
3. ParticipatingCountry relationships (country eligibility by objective)
4. Relationships: BELONGS_TO_OBJECTIVE, ALLOWS_COORDINATOR_FROM, ALLOWS_PARTNER_FROM

Usage:
    python scripts/ingest_digital_europe_to_neo4j.py [--clear]
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.neo4j_config import neo4j_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DigitalEuropeNeo4jIngester:
    """
    Ingests Digital Europe reference data into Neo4j for enhanced eligibility
    checking and recommendation capabilities.
    """

    # Digital Europe Specific Objectives
    DIGITAL_EUROPE_OBJECTIVES = {
        'HPC': {
            'code': 'HPC',
            'name': 'High Performance Computing',
            'description': 'Supercomputing infrastructure, EuroHPC JU, data infrastructure',
            'budget': 2227000000,
            'budget_formatted': '€2.227 billion',
            'objectives': [
                'Acquire world-class supercomputers',
                'Develop European HPC infrastructure',
                'Support HPC competence centers',
                'Enable industrial and scientific applications',
            ],
            'priority_areas': ['supercomputing', 'EuroHPC', 'exascale', 'data_infrastructure', 'HPC_centers'],
            'funding_rate': 50,
            'funding_rate_notes': 'Up to 100% for supercomputer acquisition',
        },
        'AI': {
            'code': 'AI',
            'name': 'Artificial Intelligence',
            'description': 'AI testing facilities, data spaces, AI factories, AI Act support',
            'budget': 2062000000,
            'budget_formatted': '€2.062 billion',
            'objectives': [
                'Develop AI testing and experimentation facilities (TEFs)',
                'Create common European data spaces',
                'Support AI factories initiative',
                'Implement AI Act requirements',
            ],
            'priority_areas': ['AI_testing', 'data_spaces', 'TEFs', 'AI_factories', 'trustworthy_AI'],
            'funding_rate': 50,
            'funding_rate_notes': 'SMEs may receive higher rates',
        },
        'CYBERSECURITY': {
            'code': 'CYBERSECURITY',
            'name': 'Cybersecurity and Trust',
            'description': 'Cybersecurity infrastructure, SOCs, ECCC initiatives, NIS2 support',
            'budget': 1650000000,
            'budget_formatted': '€1.650 billion',
            'objectives': [
                'Build EU cybersecurity capacity',
                'Support Security Operation Centres (SOCs)',
                'Strengthen ECCC and NCCs',
                'Develop cybersecurity tools and services',
            ],
            'priority_areas': ['SOCs', 'ECCC', 'NCCs', 'cyber_resilience', 'NIS2'],
            'funding_rate': 50,
            'funding_rate_notes': 'Managed jointly with ECCC',
        },
        'SKILLS': {
            'code': 'SKILLS',
            'name': 'Advanced Digital Skills',
            'description': 'Specialized training in HPC, AI, cybersecurity, data',
            'budget': 577000000,
            'budget_formatted': '€577 million',
            'objectives': [
                'Develop specialized digital skills programs',
                'Train workforce in advanced technologies',
                'Create certification programs',
                'Support digital skills academies',
            ],
            'priority_areas': ['digital_training', 'certifications', 'academies', 'workforce'],
            'funding_rate': 50,
            'funding_rate_notes': 'Focus on specialized skills programs',
        },
        'DEPLOYMENT': {
            'code': 'DEPLOYMENT',
            'name': 'Deployment and Best Use',
            'description': 'EDIHs, digital transformation, interoperability, multi-country projects',
            'budget': 1072000000,
            'budget_formatted': '€1.072 billion',
            'objectives': [
                'Support European Digital Innovation Hubs (EDIHs)',
                'Enable digital transformation of SMEs and public sector',
                'Promote interoperability solutions',
                'Implement multi-country projects',
            ],
            'priority_areas': ['EDIHs', 'digital_transformation', 'interoperability', 'MCP'],
            'funding_rate': 50,
            'funding_rate_notes': 'EDIHs receive specific multi-year funding',
        },
        'SEMICONDUCTORS': {
            'code': 'SEMICONDUCTORS',
            'name': 'Semiconductors (Chips Act)',
            'description': 'Chip design, pilot lines, competence centers under European Chips Act',
            'budget': 0,  # Funded via Chips Act
            'budget_formatted': 'Additional funding via Chips Act',
            'objectives': [
                'Strengthen EU semiconductor ecosystem',
                'Support chip design competence centers',
                'Develop pilot lines for advanced manufacturing',
                'Build resilient supply chains',
            ],
            'priority_areas': ['chip_design', 'pilot_lines', 'competence_centers', 'supply_chain'],
            'funding_rate': 50,
            'funding_rate_notes': 'Part of European Chips Act initiative',
        },
    }

    # Digital Europe Action Types
    DIGITAL_EUROPE_ACTIONS = {
        'GRANT': {
            'code': 'GRANT',
            'name': 'Grant',
            'description': 'Grants for Digital Europe projects and initiatives',
            'objectives': ['HPC', 'AI', 'CYBERSECURITY', 'SKILLS', 'DEPLOYMENT', 'SEMICONDUCTORS'],
            'funding_rate_min': 50,
            'funding_rate_max': 100,
            'funding_rate_notes': '50% standard, up to 100% for specific actions',
            'min_partners': 1,
            'min_countries': 1,
            'typical_consortium': '1-20 partners depending on call',
            'country_rule': 'participating',
            'org_types': [
                'SME', 'STARTUP', 'LARGE_ENTERPRISE', 'RESEARCH', 'UNIVERSITY',
                'PUBLIC_AUTHORITY', 'EDIH', 'HPC_CENTER', 'NGO', 'COMPETENCE_CENTER'
            ],
            'notes': 'Main funding instrument for Digital Europe. SMEs often prioritized.',
        },
        'PROCUREMENT': {
            'code': 'PROCUREMENT',
            'name': 'Procurement',
            'description': 'Public procurement contracts for services, supplies, or works',
            'objectives': ['HPC', 'AI', 'CYBERSECURITY', 'DEPLOYMENT', 'SEMICONDUCTORS'],
            'funding_rate_min': 100,
            'funding_rate_max': 100,
            'funding_rate_notes': '100% - Full payment for contract deliverables',
            'min_partners': 1,
            'min_countries': 1,
            'typical_consortium': 'Single contractor or consortium',
            'country_rule': 'participating',
            'org_types': [
                'SME', 'STARTUP', 'LARGE_ENTERPRISE', 'RESEARCH', 'UNIVERSITY',
                'PUBLIC_AUTHORITY', 'HPC_CENTER', 'COMPETENCE_CENTER'
            ],
            'notes': 'Tendering procedure, not a grant. Competitive bidding process.',
        },
    }

    # EU Member States (27)
    EU_MEMBER_STATES = [
        'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
        'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
        'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE',
    ]

    # EEA Countries (full participation)
    EEA_COUNTRIES = ['IS', 'LI', 'NO']  # Iceland, Liechtenstein, Norway

    # Associated Countries for Digital Europe
    ASSOCIATED_COUNTRIES = [
        'UA',  # Ukraine
        'MD',  # Moldova
        'ME',  # Montenegro
        'MK',  # North Macedonia
        'RS',  # Serbia
        'AL',  # Albania
        'XK',  # Kosovo
        'TR',  # Türkiye
        'BA',  # Bosnia and Herzegovina
    ]

    # Partially Associated (specific objectives only)
    PARTIALLY_ASSOCIATED = {
        'CH': {  # Switzerland
            'name': 'Switzerland',
            'objectives': ['HPC', 'AI'],
            'notes': 'Participates in HPC and AI objectives only',
        },
    }

    # All participating countries
    ALL_PARTICIPATING = EU_MEMBER_STATES + EEA_COUNTRIES + ASSOCIATED_COUNTRIES

    # Country name to ISO mapping
    COUNTRY_NAMES = {
        'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'HR': 'Croatia',
        'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'EE': 'Estonia',
        'FI': 'Finland', 'FR': 'France', 'DE': 'Germany', 'GR': 'Greece',
        'HU': 'Hungary', 'IE': 'Ireland', 'IT': 'Italy', 'LV': 'Latvia',
        'LT': 'Lithuania', 'LU': 'Luxembourg', 'MT': 'Malta', 'NL': 'Netherlands',
        'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania', 'SK': 'Slovakia',
        'SI': 'Slovenia', 'ES': 'Spain', 'SE': 'Sweden',
        'IS': 'Iceland', 'LI': 'Liechtenstein', 'NO': 'Norway',
        'UA': 'Ukraine', 'MD': 'Moldova', 'ME': 'Montenegro',
        'MK': 'North Macedonia', 'RS': 'Serbia', 'AL': 'Albania',
        'XK': 'Kosovo', 'TR': 'Türkiye', 'BA': 'Bosnia and Herzegovina',
        'CH': 'Switzerland',
    }

    def __init__(self):
        """Initialize the Digital Europe ingester."""
        self.db = neo4j_db
        logger.info("Initialized Digital Europe Neo4j Ingester")

    def create_constraints_and_indexes(self) -> None:
        """Create Neo4j constraints and indexes for Digital Europe data."""
        logger.info("Creating Digital Europe constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT digital_objective_code IF NOT EXISTS FOR (o:DigitalEuropeObjective) REQUIRE o.code IS UNIQUE",
            "CREATE CONSTRAINT digital_action_code IF NOT EXISTS FOR (a:DigitalEuropeAction) REQUIRE a.code IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX digital_objective_budget IF NOT EXISTS FOR (o:DigitalEuropeObjective) ON (o.budget)",
            "CREATE INDEX digital_action_funding IF NOT EXISTS FOR (a:DigitalEuropeAction) ON (a.funding_rate_max)",
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

    def load_objectives(self) -> None:
        """Load Digital Europe objective nodes."""
        logger.info("Loading Digital Europe objectives...")

        for code, info in self.DIGITAL_EUROPE_OBJECTIVES.items():
            self.db.execute_query("""
                MERGE (o:DigitalEuropeObjective {code: $code})
                SET o.name = $name,
                    o.description = $description,
                    o.budget = $budget,
                    o.budget_formatted = $budget_formatted,
                    o.objectives = $objectives,
                    o.priority_areas = $priority_areas,
                    o.funding_rate = $funding_rate,
                    o.funding_rate_notes = $funding_rate_notes
            """, info)

        logger.info(f"Loaded {len(self.DIGITAL_EUROPE_OBJECTIVES)} objectives")

    def load_actions(self) -> None:
        """Load Digital Europe action nodes with full metadata."""
        logger.info("Loading Digital Europe actions...")

        for code, info in self.DIGITAL_EUROPE_ACTIONS.items():
            # Create action node
            self.db.execute_query("""
                MERGE (a:DigitalEuropeAction {code: $code})
                SET a.name = $name,
                    a.description = $description,
                    a.funding_rate_min = $funding_rate_min,
                    a.funding_rate_max = $funding_rate_max,
                    a.funding_rate_notes = $funding_rate_notes,
                    a.min_partners = $min_partners,
                    a.min_countries = $min_countries,
                    a.typical_consortium = $typical_consortium,
                    a.country_rule = $country_rule,
                    a.org_types = $org_types,
                    a.notes = $notes
            """, info)

            # Link to objectives
            for objective_code in info['objectives']:
                self.db.execute_query("""
                    MATCH (a:DigitalEuropeAction {code: $action_code})
                    MATCH (o:DigitalEuropeObjective {code: $objective_code})
                    MERGE (a)-[:BELONGS_TO_OBJECTIVE]->(o)
                """, {"action_code": code, "objective_code": objective_code})

        logger.info(f"Loaded {len(self.DIGITAL_EUROPE_ACTIONS)} actions")

    def load_country_regions(self) -> None:
        """Create country eligibility regions for Digital Europe."""
        logger.info("Loading Digital Europe country regions...")

        # Create EU Member States region
        self.db.execute_query("""
            MERGE (r:DigitalEuropeRegion {code: 'EU_MEMBERS'})
            SET r.name = 'EU Member States',
                r.description = 'EU27 Member States - eligible for all Digital Europe objectives',
                r.countries = $countries
        """, {"countries": self.EU_MEMBER_STATES})

        # Create EEA region
        self.db.execute_query("""
            MERGE (r:DigitalEuropeRegion {code: 'EEA'})
            SET r.name = 'EEA Countries',
                r.description = 'Iceland, Liechtenstein, Norway - full participation',
                r.countries = $countries
        """, {"countries": self.EEA_COUNTRIES})

        # Create Associated Countries region
        self.db.execute_query("""
            MERGE (r:DigitalEuropeRegion {code: 'ASSOCIATED'})
            SET r.name = 'Associated Countries',
                r.description = 'Countries with association agreements',
                r.countries = $countries
        """, {"countries": self.ASSOCIATED_COUNTRIES})

        # Create All Participating region
        self.db.execute_query("""
            MERGE (r:DigitalEuropeRegion {code: 'ALL_PARTICIPATING'})
            SET r.name = 'All Participating Countries',
                r.description = 'EU27 + EEA + Associated Countries eligible for Digital Europe',
                r.countries = $countries
        """, {"countries": self.ALL_PARTICIPATING})

        # Create Partially Associated region (Switzerland for HPC/AI)
        partially_associated_countries = list(self.PARTIALLY_ASSOCIATED.keys())
        self.db.execute_query("""
            MERGE (r:DigitalEuropeRegion {code: 'PARTIALLY_ASSOCIATED'})
            SET r.name = 'Partially Associated Countries',
                r.description = 'Countries with partial participation (specific objectives only)',
                r.countries = $countries
        """, {"countries": partially_associated_countries})

        logger.info("Loaded 5 country regions")

    def create_action_country_relationships(self) -> None:
        """Create relationships between actions and country eligibility."""
        logger.info("Creating action-country relationships...")

        for code, info in self.DIGITAL_EUROPE_ACTIONS.items():
            # All participating countries can be coordinators/partners
            self.db.execute_query("""
                MATCH (a:DigitalEuropeAction {code: $action_code})
                MATCH (r:DigitalEuropeRegion {code: 'ALL_PARTICIPATING'})
                MERGE (a)-[:ALLOWS_COORDINATOR_FROM]->(r)
                MERGE (a)-[:ALLOWS_PARTNER_FROM]->(r)
            """, {"action_code": code})

        logger.info("Action-country relationships created")

    def create_objective_country_relationships(self) -> None:
        """Create objective-specific country eligibility (for partially associated)."""
        logger.info("Creating objective-country relationships...")

        # For HPC and AI objectives, include partially associated countries (Switzerland)
        for objective in ['HPC', 'AI']:
            self.db.execute_query("""
                MATCH (o:DigitalEuropeObjective {code: $objective_code})
                MATCH (r:DigitalEuropeRegion {code: 'PARTIALLY_ASSOCIATED'})
                MERGE (o)-[:ALLOWS_PARTICIPATION_FROM]->(r)
            """, {"objective_code": objective})

        # All objectives allow full participation from regular regions
        for objective_code in self.DIGITAL_EUROPE_OBJECTIVES.keys():
            self.db.execute_query("""
                MATCH (o:DigitalEuropeObjective {code: $objective_code})
                MATCH (r:DigitalEuropeRegion {code: 'ALL_PARTICIPATING'})
                MERGE (o)-[:ALLOWS_PARTICIPATION_FROM]->(r)
            """, {"objective_code": objective_code})

        logger.info("Objective-country relationships created")

    def link_existing_countries(self) -> None:
        """Link existing Country nodes to Digital Europe regions."""
        logger.info("Linking countries to Digital Europe regions...")

        # Mark EU Member States
        for country in self.EU_MEMBER_STATES:
            self.db.execute_query("""
                MERGE (c:Country {isoCode: $country_code})
                SET c.digital_europe_eligible = true,
                    c.name = $country_name
                WITH c
                MATCH (r:DigitalEuropeRegion {code: 'EU_MEMBERS'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:DigitalEuropeRegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """, {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)})

        # Mark EEA Countries
        for country in self.EEA_COUNTRIES:
            self.db.execute_query("""
                MERGE (c:Country {isoCode: $country_code})
                SET c.digital_europe_eligible = true,
                    c.name = $country_name
                WITH c
                MATCH (r:DigitalEuropeRegion {code: 'EEA'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:DigitalEuropeRegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """, {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)})

        # Mark Associated Countries
        for country in self.ASSOCIATED_COUNTRIES:
            self.db.execute_query("""
                MERGE (c:Country {isoCode: $country_code})
                SET c.digital_europe_eligible = true,
                    c.name = $country_name
                WITH c
                MATCH (r:DigitalEuropeRegion {code: 'ASSOCIATED'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:DigitalEuropeRegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """, {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)})

        # Mark Partially Associated (Switzerland)
        for country, info in self.PARTIALLY_ASSOCIATED.items():
            self.db.execute_query("""
                MERGE (c:Country {isoCode: $country_code})
                SET c.digital_europe_eligible = true,
                    c.digital_europe_partial = true,
                    c.digital_europe_objectives = $objectives,
                    c.name = $country_name
                WITH c
                MATCH (r:DigitalEuropeRegion {code: 'PARTIALLY_ASSOCIATED'})
                MERGE (c)-[:MEMBER_OF]->(r)
            """, {
                "country_code": country,
                "country_name": info['name'],
                "objectives": info['objectives'],
            })

        logger.info("Country-region relationships created")

    def create_programme_metadata(self) -> None:
        """Create Digital Europe programme metadata node."""
        logger.info("Creating Digital Europe programme metadata...")

        self.db.execute_query("""
            MERGE (p:Programme {code: 'DIGITAL_EUROPE'})
            SET p.name = 'Digital Europe',
                p.full_name = 'Digital Europe Programme 2021-2027',
                p.budget = 7588000000,
                p.budget_formatted = '€7.588 billion',
                p.start_year = 2021,
                p.end_year = 2027,
                p.implementing_agency = 'DG CONNECT / HaDEA',
                p.implementing_agency_full = 'DG Communications Networks, Content and Technology / European Health and Digital Executive Agency',
                p.legal_basis = 'Regulation (EU) 2021/694',
                p.website = 'https://digital-strategy.ec.europa.eu/en/activities/digital-programme',
                p.description = 'EU programme to bring digital technology to businesses, citizens and public administrations'
        """)

        # Link objectives to programme
        for objective_code in self.DIGITAL_EUROPE_OBJECTIVES.keys():
            self.db.execute_query("""
                MATCH (p:Programme {code: 'DIGITAL_EUROPE'})
                MATCH (o:DigitalEuropeObjective {code: $objective_code})
                MERGE (o)-[:PART_OF]->(p)
            """, {"objective_code": objective_code})

        logger.info("Programme metadata created")

    def create_synergies(self) -> None:
        """Create synergy relationships with other programmes."""
        logger.info("Creating programme synergy relationships...")

        synergies = [
            ('HORIZON_EUROPE', 'Horizon Europe', 'Research and innovation synergies'),
            ('CEF_DIGITAL', 'CEF Digital', 'Connectivity infrastructure synergies'),
            ('RECOVERY_FUND', 'Recovery and Resilience Facility', 'Digital transition investments'),
            ('ERASMUS_PLUS', 'Erasmus+', 'Digital skills and education synergies'),
        ]

        for prog_code, prog_name, synergy_desc in synergies:
            self.db.execute_query("""
                MERGE (p2:Programme {code: $prog_code})
                SET p2.name = $prog_name
                WITH p2
                MATCH (p1:Programme {code: 'DIGITAL_EUROPE'})
                MERGE (p1)-[s:HAS_SYNERGY_WITH]->(p2)
                SET s.description = $synergy_desc
            """, {"prog_code": prog_code, "prog_name": prog_name, "synergy_desc": synergy_desc})

        logger.info(f"Created {len(synergies)} synergy relationships")

    def clear_digital_europe_data(self) -> None:
        """Clear only Digital Europe specific nodes and relationships."""
        logger.warning("Clearing Digital Europe data from Neo4j...")

        queries = [
            "MATCH (a:DigitalEuropeAction) DETACH DELETE a",
            "MATCH (o:DigitalEuropeObjective) DETACH DELETE o",
            "MATCH (r:DigitalEuropeRegion) DETACH DELETE r",
            "MATCH (p:Programme {code: 'DIGITAL_EUROPE'}) DETACH DELETE p",
        ]

        for query in queries:
            self.db.execute_query(query)

        logger.info("Digital Europe data cleared")

    def run(self, clear_first: bool = False) -> dict[str, int]:
        """
        Run the complete Digital Europe ingestion pipeline.

        Args:
            clear_first: If True, clear Digital Europe data before ingestion

        Returns:
            Statistics dict
        """
        logger.info("=" * 60)
        logger.info("DIGITAL EUROPE -> Neo4j Reference Data Ingestion")
        logger.info("=" * 60)

        if clear_first:
            self.clear_digital_europe_data()

        # Step 1: Create constraints/indexes
        self.create_constraints_and_indexes()

        # Step 2: Load objectives
        self.load_objectives()

        # Step 3: Load actions
        self.load_actions()

        # Step 4: Load country regions
        self.load_country_regions()

        # Step 5: Create action-country relationships
        self.create_action_country_relationships()

        # Step 6: Create objective-country relationships
        self.create_objective_country_relationships()

        # Step 7: Link existing countries
        self.link_existing_countries()

        # Step 8: Create programme metadata
        self.create_programme_metadata()

        # Step 9: Create synergies
        self.create_synergies()

        # Get stats
        stats = self._get_stats()
        self._print_summary(stats)

        return stats

    def _get_stats(self) -> dict[str, int]:
        """Get current Digital Europe data statistics."""
        query = """
        MATCH (o:DigitalEuropeObjective) WITH count(o) as objectives
        MATCH (a:DigitalEuropeAction) WITH objectives, count(a) as actions
        MATCH (r:DigitalEuropeRegion) WITH objectives, actions, count(r) as regions
        OPTIONAL MATCH (:DigitalEuropeAction)-[rel:BELONGS_TO_OBJECTIVE]->()
            WITH objectives, actions, regions, count(rel) as objective_rels
        OPTIONAL MATCH (:DigitalEuropeAction)-[rel2:ALLOWS_COORDINATOR_FROM]->()
            WITH objectives, actions, regions, objective_rels, count(rel2) as coord_rels
        OPTIONAL MATCH (:DigitalEuropeAction)-[rel3:ALLOWS_PARTNER_FROM]->()
            WITH objectives, actions, regions, objective_rels, coord_rels, count(rel3) as partner_rels
        OPTIONAL MATCH (:Country)-[rel4:MEMBER_OF]->(:DigitalEuropeRegion)
            WITH objectives, actions, regions, objective_rels, coord_rels, partner_rels, count(rel4) as country_rels
        OPTIONAL MATCH (p:Programme {code: 'DIGITAL_EUROPE'})
            WITH objectives, actions, regions, objective_rels, coord_rels, partner_rels, country_rels, count(p) as programme
        OPTIONAL MATCH (:Programme {code: 'DIGITAL_EUROPE'})-[syn:HAS_SYNERGY_WITH]->()
            WITH objectives, actions, regions, objective_rels, coord_rels, partner_rels, country_rels, programme, count(syn) as synergies
        RETURN objectives, actions, regions, objective_rels, coord_rels, partner_rels, country_rels, programme, synergies
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
        logger.info("DIGITAL EUROPE INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"DigitalEuropeObjective nodes: {stats.get('objectives', 0)}")
        logger.info(f"DigitalEuropeAction nodes: {stats.get('actions', 0)}")
        logger.info(f"DigitalEuropeRegion nodes: {stats.get('regions', 0)}")
        logger.info(f"Programme nodes: {stats.get('programme', 0)}")
        logger.info(f"BELONGS_TO_OBJECTIVE relationships: {stats.get('objective_rels', 0)}")
        logger.info(f"ALLOWS_COORDINATOR_FROM relationships: {stats.get('coord_rels', 0)}")
        logger.info(f"ALLOWS_PARTNER_FROM relationships: {stats.get('partner_rels', 0)}")
        logger.info(f"Country MEMBER_OF relationships: {stats.get('country_rels', 0)}")
        logger.info(f"Programme synergies: {stats.get('synergies', 0)}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest Digital Europe data into Neo4j")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear Digital Europe data before ingestion"
    )

    args = parser.parse_args()

    try:
        ingester = DigitalEuropeNeo4jIngester()
        stats = ingester.run(clear_first=args.clear)

        if stats.get('objectives', 0) > 0:
            logger.info("\nDigital Europe reference data loaded successfully!")
            logger.info("You can now use graph-based eligibility checking for Digital Europe.")
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
