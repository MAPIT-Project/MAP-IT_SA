#!/usr/bin/env python3
"""
Ingest EU4Health Reference Data into Neo4j Graph Database.

This script populates Neo4j with EU4Health programme structure:
1. EU4HealthStrand nodes (Crisis, Prevention, Health Systems, Digital)
2. EU4HealthAction nodes (AG, JA, DG, OG, FPA, PROC with full metadata)
3. ParticipatingCountry relationships (country eligibility by action type)
4. Relationships: BELONGS_TO_STRAND, ALLOWS_COORDINATOR_FROM, ALLOWS_PARTNER_FROM

Usage:
    python scripts/ingest_eu4health_to_neo4j.py [--clear]
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.neo4j_config import neo4j_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EU4HealthNeo4jIngester:
    """
    Ingests EU4Health reference data into Neo4j for enhanced eligibility
    checking and recommendation capabilities.
    """

    # EU4Health Strands (Thematic Areas)
    EU4HEALTH_STRANDS = {
        'CRISIS': {
            'code': 'CRISIS',
            'name': 'Crisis Preparedness',
            'description': 'Health security, emergency preparedness, medical countermeasures (HERA), AMR',
            'objectives': [
                'Strengthen EU health crisis preparedness',
                'Support HERA and MCM stockpiling',
                'Combat antimicrobial resistance (AMR)',
                'Improve cross-border health threat response',
            ],
            'priority_areas': ['HERA', 'MCM', 'AMR', 'emergency_response', 'health_security'],
        },
        'PREVENTION': {
            'code': 'PREVENTION',
            'name': 'Disease Prevention',
            'description': 'Cancer (Beating Cancer Plan), NCDs, infectious diseases, health promotion',
            'objectives': [
                'Implement Europe Beating Cancer Plan',
                'Reduce burden of NCDs',
                'Improve vaccination coverage',
                'Promote healthy lifestyles',
            ],
            'priority_areas': ['cancer', 'NCDs', 'vaccination', 'screening', 'HIV', 'health_promotion'],
        },
        'HEALTH_SYSTEMS': {
            'code': 'HEALTH_SYSTEMS',
            'name': 'Health Systems',
            'description': 'Healthcare workforce, HTA, medicines supply, pharmaceuticals, mental health',
            'objectives': [
                'Strengthen health workforce',
                'Improve access to medicines',
                'Support health technology assessment (HTA)',
                'Address medicines shortages',
            ],
            'priority_areas': ['workforce', 'HTA', 'medicines', 'pharmaceuticals', 'mental_health', 'shortages'],
        },
        'DIGITAL': {
            'code': 'DIGITAL',
            'name': 'Digital Health',
            'description': 'EHDS, eHealth infrastructure, telemedicine, AI in healthcare, health data',
            'objectives': [
                'Support European Health Data Space (EHDS)',
                'Develop eHealth infrastructure',
                'Enable cross-border healthcare',
                'Leverage AI and data for health',
            ],
            'priority_areas': ['EHDS', 'eHealth', 'telemedicine', 'AI', 'health_data', 'interoperability'],
        },
    }

    # EU4Health Action Types with full metadata
    EU4HEALTH_ACTIONS = {
        'AG': {
            'code': 'AG',
            'name': 'Action Grant',
            'description': 'Project grants for health initiatives with EU co-financing',
            'strands': ['CRISIS', 'PREVENTION', 'HEALTH_SYSTEMS', 'DIGITAL'],
            'funding_rate_min': 60,
            'funding_rate_max': 80,
            'funding_rate_notes': '60% standard, up to 80% for exceptional utility',
            'min_partners': 1,
            'min_countries': 1,
            'typical_consortium': '3-10 partners from 3+ countries',
            'country_rule': 'participating',
            'org_types': [
                'HEALTHCARE_PROVIDER', 'RESEARCH', 'UNIVERSITY', 'PUBLIC_AUTHORITY',
                'NGO', 'PATIENT_ORG', 'PROFESSIONAL_ORG', 'ENTERPRISE', 'SME'
            ],
            'notes': 'Most common EU4Health grant type. Open to wide range of entities.',
        },
        'PJ': {
            'code': 'PJ',
            'name': 'Project Grant',
            'description': 'Project grants (equivalent to Action Grant in some calls)',
            'strands': ['CRISIS', 'PREVENTION', 'HEALTH_SYSTEMS', 'DIGITAL'],
            'funding_rate_min': 60,
            'funding_rate_max': 80,
            'funding_rate_notes': '60% standard, up to 80% for exceptional utility',
            'min_partners': 1,
            'min_countries': 1,
            'typical_consortium': '3-10 partners from 3+ countries',
            'country_rule': 'participating',
            'org_types': [
                'HEALTHCARE_PROVIDER', 'RESEARCH', 'UNIVERSITY', 'PUBLIC_AUTHORITY',
                'NGO', 'PATIENT_ORG', 'PROFESSIONAL_ORG', 'ENTERPRISE', 'SME'
            ],
            'notes': 'Same as Action Grant. Topic code format: EU4H-YYYY-PJ-XX-Y',
        },
        'JA': {
            'code': 'JA',
            'name': 'Joint Action',
            'description': 'Actions with EU Member State competent authorities',
            'strands': ['CRISIS', 'PREVENTION', 'HEALTH_SYSTEMS', 'DIGITAL'],
            'funding_rate_min': 60,
            'funding_rate_max': 60,
            'funding_rate_notes': '60% EU co-financing, Member States provide rest',
            'min_partners': 3,
            'min_countries': 3,
            'typical_consortium': '20-50 Member State authorities',
            'country_rule': 'member_states_only',
            'org_types': ['PUBLIC_AUTHORITY'],
            'notes': 'Only EU Member State authorities can be beneficiaries. Large-scale policy implementation.',
        },
        'DG': {
            'code': 'DG',
            'name': 'Direct Grant',
            'description': 'Grants to specific entities designated in the Work Programme',
            'strands': ['CRISIS', 'PREVENTION', 'HEALTH_SYSTEMS', 'DIGITAL'],
            'funding_rate_min': 60,
            'funding_rate_max': 100,
            'funding_rate_notes': 'Varies by specific action, typically 60-100%',
            'min_partners': 1,
            'min_countries': 1,
            'typical_consortium': 'Designated entities (WHO, ECDC, etc.)',
            'country_rule': 'participating',
            'org_types': ['PUBLIC_AUTHORITY', 'INTERNATIONAL_ORG'],
            'notes': 'Not open for applications. Awarded to entities named in Annual Work Programme.',
        },
        'OG': {
            'code': 'OG',
            'name': 'Operating Grant',
            'description': 'Grants for NGO operating costs and core activities',
            'strands': ['PREVENTION', 'HEALTH_SYSTEMS'],
            'funding_rate_min': 60,
            'funding_rate_max': 60,
            'funding_rate_notes': '60% EU co-financing for operating costs',
            'min_partners': 1,
            'min_countries': 1,
            'typical_consortium': 'Single EU-level health NGO/network',
            'country_rule': 'participating',
            'org_types': ['NGO', 'PATIENT_ORG', 'PROFESSIONAL_ORG'],
            'notes': 'For EU-level health NGOs. Requires Framework Partnership Agreement.',
        },
        'FPA': {
            'code': 'FPA',
            'name': 'Framework Partnership Agreement',
            'description': 'Long-term partnership agreement with the European Commission',
            'strands': ['PREVENTION', 'HEALTH_SYSTEMS'],
            'funding_rate_min': 60,
            'funding_rate_max': 60,
            'funding_rate_notes': '60% EU co-financing for specific grants',
            'min_partners': 1,
            'min_countries': 1,
            'typical_consortium': 'EU-level umbrella organizations/networks',
            'country_rule': 'participating',
            'org_types': ['NGO', 'PATIENT_ORG', 'PROFESSIONAL_ORG'],
            'notes': 'Multi-year agreement for recurring grants. Selected via competitive call.',
        },
        'PROC': {
            'code': 'PROC',
            'name': 'Procurement',
            'description': 'Public procurement contracts for services, supplies, or works',
            'strands': ['CRISIS', 'PREVENTION', 'HEALTH_SYSTEMS', 'DIGITAL'],
            'funding_rate_min': 100,
            'funding_rate_max': 100,
            'funding_rate_notes': '100% - Full payment for contract deliverables',
            'min_partners': 1,
            'min_countries': 1,
            'typical_consortium': 'Single contractor or consortium',
            'country_rule': 'participating',
            'org_types': [
                'HEALTHCARE_PROVIDER', 'RESEARCH', 'UNIVERSITY', 'PUBLIC_AUTHORITY',
                'ENTERPRISE', 'SME', 'INTERNATIONAL_ORG'
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

    # EEA Countries (full participation in EU4Health)
    EEA_COUNTRIES = ['IS', 'NO']

    # Associated Countries for EU4Health (as of 2024)
    ASSOCIATED_COUNTRIES = [
        'UA',  # Ukraine
        'MD',  # Moldova
        'ME',  # Montenegro
        'BA',  # Bosnia and Herzegovina
        'RS',  # Serbia
    ]

    # All participating countries
    ALL_PARTICIPATING = EU_MEMBER_STATES + EEA_COUNTRIES + ASSOCIATED_COUNTRIES

    # Country name to ISO mapping for reference
    COUNTRY_NAMES = {
        'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'HR': 'Croatia',
        'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'EE': 'Estonia',
        'FI': 'Finland', 'FR': 'France', 'DE': 'Germany', 'GR': 'Greece',
        'HU': 'Hungary', 'IE': 'Ireland', 'IT': 'Italy', 'LV': 'Latvia',
        'LT': 'Lithuania', 'LU': 'Luxembourg', 'MT': 'Malta', 'NL': 'Netherlands',
        'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania', 'SK': 'Slovakia',
        'SI': 'Slovenia', 'ES': 'Spain', 'SE': 'Sweden',
        'IS': 'Iceland', 'NO': 'Norway',
        'UA': 'Ukraine', 'MD': 'Moldova', 'ME': 'Montenegro',
        'BA': 'Bosnia and Herzegovina', 'RS': 'Serbia',
    }

    def __init__(self):
        """Initialize the EU4Health ingester."""
        self.db = neo4j_db
        logger.info("Initialized EU4Health Neo4j Ingester")

    def create_constraints_and_indexes(self) -> None:
        """Create Neo4j constraints and indexes for EU4Health data."""
        logger.info("Creating EU4Health constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT eu4h_strand_code IF NOT EXISTS FOR (s:EU4HealthStrand) REQUIRE s.code IS UNIQUE",
            "CREATE CONSTRAINT eu4h_action_code IF NOT EXISTS FOR (a:EU4HealthAction) REQUIRE a.code IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX eu4h_action_funding IF NOT EXISTS FOR (a:EU4HealthAction) ON (a.funding_rate_max)",
            "CREATE INDEX eu4h_action_country_rule IF NOT EXISTS FOR (a:EU4HealthAction) ON (a.country_rule)",
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
        """Load EU4Health strand nodes."""
        logger.info("Loading EU4Health strands...")

        for code, info in self.EU4HEALTH_STRANDS.items():
            self.db.execute_query("""
                MERGE (s:EU4HealthStrand {code: $code})
                SET s.name = $name,
                    s.description = $description,
                    s.objectives = $objectives,
                    s.priority_areas = $priority_areas
            """, info)

        logger.info(f"Loaded {len(self.EU4HEALTH_STRANDS)} strands")

    def load_actions(self) -> None:
        """Load EU4Health action nodes with full metadata."""
        logger.info("Loading EU4Health actions...")

        for code, info in self.EU4HEALTH_ACTIONS.items():
            # Create action node
            self.db.execute_query("""
                MERGE (a:EU4HealthAction {code: $code})
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

            # Link to strands
            for strand_code in info['strands']:
                self.db.execute_query("""
                    MATCH (a:EU4HealthAction {code: $action_code})
                    MATCH (s:EU4HealthStrand {code: $strand_code})
                    MERGE (a)-[:BELONGS_TO_STRAND]->(s)
                """, {"action_code": code, "strand_code": strand_code})

        logger.info(f"Loaded {len(self.EU4HEALTH_ACTIONS)} actions")

    def load_country_regions(self) -> None:
        """Create country eligibility regions for EU4Health."""
        logger.info("Loading EU4Health country regions...")

        # Create EU Member States region
        self.db.execute_query("""
            MERGE (r:EU4HealthRegion {code: 'EU_MEMBERS'})
            SET r.name = 'EU Member States',
                r.description = 'EU27 Member States - eligible for all EU4Health actions',
                r.countries = $countries
        """, {"countries": self.EU_MEMBER_STATES})

        # Create EEA region
        self.db.execute_query("""
            MERGE (r:EU4HealthRegion {code: 'EEA'})
            SET r.name = 'EEA Countries',
                r.description = 'Iceland and Norway - full participation in EU4Health',
                r.countries = $countries
        """, {"countries": self.EEA_COUNTRIES})

        # Create Associated Countries region
        self.db.execute_query("""
            MERGE (r:EU4HealthRegion {code: 'ASSOCIATED'})
            SET r.name = 'Associated Countries',
                r.description = 'Ukraine, Moldova, Montenegro, Bosnia and Herzegovina, Serbia',
                r.countries = $countries
        """, {"countries": self.ASSOCIATED_COUNTRIES})

        # Create All Participating region
        self.db.execute_query("""
            MERGE (r:EU4HealthRegion {code: 'ALL_PARTICIPATING'})
            SET r.name = 'All Participating Countries',
                r.description = 'EU27 + EEA + Associated Countries eligible for EU4Health',
                r.countries = $countries
        """, {"countries": self.ALL_PARTICIPATING})

        logger.info("Loaded 4 country regions")

    def create_action_country_relationships(self) -> None:
        """Create relationships between actions and country eligibility."""
        logger.info("Creating action-country relationships...")

        for code, info in self.EU4HEALTH_ACTIONS.items():
            country_rule = info['country_rule']

            # Determine which region based on country rule
            if country_rule == 'member_states_only':
                # Joint Actions - only EU Member States
                region = 'EU_MEMBERS'
            else:
                # All other actions - all participating countries
                region = 'ALL_PARTICIPATING'

            # Coordinator eligibility
            self.db.execute_query("""
                MATCH (a:EU4HealthAction {code: $action_code})
                MATCH (r:EU4HealthRegion {code: $region_code})
                MERGE (a)-[:ALLOWS_COORDINATOR_FROM]->(r)
            """, {"action_code": code, "region_code": region})

            # Partner eligibility (same as coordinator for EU4Health)
            self.db.execute_query("""
                MATCH (a:EU4HealthAction {code: $action_code})
                MATCH (r:EU4HealthRegion {code: $region_code})
                MERGE (a)-[:ALLOWS_PARTNER_FROM]->(r)
            """, {"action_code": code, "region_code": region})

        logger.info("Action-country relationships created")

    def link_existing_countries(self) -> None:
        """Link existing Country nodes to EU4Health regions."""
        logger.info("Linking countries to EU4Health regions...")

        # Mark EU Member States
        for country in self.EU_MEMBER_STATES:
            self.db.execute_query("""
                MERGE (c:Country {isoCode: $country_code})
                SET c.eu4health_eligible = true,
                    c.eu4health_joint_action_eligible = true,
                    c.name = $country_name
                WITH c
                MATCH (r:EU4HealthRegion {code: 'EU_MEMBERS'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:EU4HealthRegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """, {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)})

        # Mark EEA Countries
        for country in self.EEA_COUNTRIES:
            self.db.execute_query("""
                MERGE (c:Country {isoCode: $country_code})
                SET c.eu4health_eligible = true,
                    c.eu4health_joint_action_eligible = false,
                    c.name = $country_name
                WITH c
                MATCH (r:EU4HealthRegion {code: 'EEA'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:EU4HealthRegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """, {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)})

        # Mark Associated Countries
        for country in self.ASSOCIATED_COUNTRIES:
            self.db.execute_query("""
                MERGE (c:Country {isoCode: $country_code})
                SET c.eu4health_eligible = true,
                    c.eu4health_joint_action_eligible = false,
                    c.name = $country_name
                WITH c
                MATCH (r:EU4HealthRegion {code: 'ASSOCIATED'})
                MERGE (c)-[:MEMBER_OF]->(r)
                WITH c
                MATCH (r2:EU4HealthRegion {code: 'ALL_PARTICIPATING'})
                MERGE (c)-[:MEMBER_OF]->(r2)
            """, {"country_code": country, "country_name": self.COUNTRY_NAMES.get(country, country)})

        logger.info("Country-region relationships created")

    def create_programme_metadata(self) -> None:
        """Create EU4Health programme metadata node."""
        logger.info("Creating EU4Health programme metadata...")

        self.db.execute_query("""
            MERGE (p:Programme {code: 'EU4HEALTH'})
            SET p.name = 'EU4Health',
                p.full_name = 'EU4Health Programme 2021-2027',
                p.budget = 5100000000,
                p.budget_formatted = '5.1 billion EUR',
                p.start_year = 2021,
                p.end_year = 2027,
                p.implementing_agency = 'HaDEA',
                p.implementing_agency_full = 'European Health and Digital Executive Agency',
                p.legal_basis = 'Regulation (EU) 2021/522',
                p.website = 'https://health.ec.europa.eu/funding/eu4health-programme-2021-2027_en',
                p.description = 'EU health programme to strengthen health systems, support crisis preparedness, and improve health for all EU citizens'
        """)

        # Link strands to programme
        for strand_code in self.EU4HEALTH_STRANDS.keys():
            self.db.execute_query("""
                MATCH (p:Programme {code: 'EU4HEALTH'})
                MATCH (s:EU4HealthStrand {code: $strand_code})
                MERGE (s)-[:PART_OF]->(p)
            """, {"strand_code": strand_code})

        logger.info("Programme metadata created")

    def clear_eu4health_data(self) -> None:
        """Clear only EU4Health specific nodes and relationships."""
        logger.warning("Clearing EU4Health data from Neo4j...")

        queries = [
            "MATCH (a:EU4HealthAction) DETACH DELETE a",
            "MATCH (s:EU4HealthStrand) DETACH DELETE s",
            "MATCH (r:EU4HealthRegion) DETACH DELETE r",
            "MATCH (p:Programme {code: 'EU4HEALTH'}) DETACH DELETE p",
        ]

        for query in queries:
            self.db.execute_query(query)

        logger.info("EU4Health data cleared")

    def run(self, clear_first: bool = False) -> Dict[str, int]:
        """
        Run the complete EU4Health ingestion pipeline.

        Args:
            clear_first: If True, clear EU4Health data before ingestion

        Returns:
            Statistics dict
        """
        logger.info("=" * 60)
        logger.info("EU4HEALTH -> Neo4j Reference Data Ingestion")
        logger.info("=" * 60)

        if clear_first:
            self.clear_eu4health_data()

        # Step 1: Create constraints/indexes
        self.create_constraints_and_indexes()

        # Step 2: Load strands
        self.load_strands()

        # Step 3: Load actions
        self.load_actions()

        # Step 4: Load country regions
        self.load_country_regions()

        # Step 5: Create action-country relationships
        self.create_action_country_relationships()

        # Step 6: Link existing countries
        self.link_existing_countries()

        # Step 7: Create programme metadata
        self.create_programme_metadata()

        # Get stats
        stats = self._get_stats()
        self._print_summary(stats)

        return stats

    def _get_stats(self) -> Dict[str, int]:
        """Get current EU4Health data statistics."""
        query = """
        MATCH (s:EU4HealthStrand) WITH count(s) as strands
        MATCH (a:EU4HealthAction) WITH strands, count(a) as actions
        MATCH (r:EU4HealthRegion) WITH strands, actions, count(r) as regions
        OPTIONAL MATCH (:EU4HealthAction)-[rel:BELONGS_TO_STRAND]->()
            WITH strands, actions, regions, count(rel) as strand_rels
        OPTIONAL MATCH (:EU4HealthAction)-[rel2:ALLOWS_COORDINATOR_FROM]->()
            WITH strands, actions, regions, strand_rels, count(rel2) as coord_rels
        OPTIONAL MATCH (:EU4HealthAction)-[rel3:ALLOWS_PARTNER_FROM]->()
            WITH strands, actions, regions, strand_rels, coord_rels, count(rel3) as partner_rels
        OPTIONAL MATCH (:Country)-[rel4:MEMBER_OF]->(:EU4HealthRegion)
            WITH strands, actions, regions, strand_rels, coord_rels, partner_rels, count(rel4) as country_rels
        OPTIONAL MATCH (p:Programme {code: 'EU4HEALTH'})
            WITH strands, actions, regions, strand_rels, coord_rels, partner_rels, country_rels, count(p) as programme
        RETURN strands, actions, regions, strand_rels, coord_rels, partner_rels, country_rels, programme
        """

        try:
            result = self.db.execute_query(query)
            if result:
                return result[0]
        except Exception as e:
            logger.error(f"Error getting stats: {e}")

        return {}

    def _print_summary(self, stats: Dict[str, int]) -> None:
        """Print ingestion summary."""
        logger.info("\n" + "=" * 60)
        logger.info("EU4HEALTH INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"EU4HealthStrand nodes: {stats.get('strands', 0)}")
        logger.info(f"EU4HealthAction nodes: {stats.get('actions', 0)}")
        logger.info(f"EU4HealthRegion nodes: {stats.get('regions', 0)}")
        logger.info(f"Programme nodes: {stats.get('programme', 0)}")
        logger.info(f"BELONGS_TO_STRAND relationships: {stats.get('strand_rels', 0)}")
        logger.info(f"ALLOWS_COORDINATOR_FROM relationships: {stats.get('coord_rels', 0)}")
        logger.info(f"ALLOWS_PARTNER_FROM relationships: {stats.get('partner_rels', 0)}")
        logger.info(f"Country MEMBER_OF relationships: {stats.get('country_rels', 0)}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest EU4Health data into Neo4j")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear EU4Health data before ingestion"
    )

    args = parser.parse_args()

    try:
        ingester = EU4HealthNeo4jIngester()
        stats = ingester.run(clear_first=args.clear)

        if stats.get('actions', 0) > 0:
            logger.info("\nEU4Health reference data loaded successfully!")
            logger.info("You can now use graph-based eligibility checking for EU4Health.")
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
