#!/usr/bin/env python3
"""
Ingest Erasmus+ Reference Data into Neo4j Graph Database.

This script populates Neo4j with Erasmus+ programme structure:
1. ErasmusAction nodes (KA1, KA2, KA3, Jean Monnet, Sport actions)
2. ErasmusSector nodes (HED, VET, SCH, ADU, YOU, SPORT)
3. PartnerRegion nodes (Programme Countries, Partner Countries, Worldwide)
4. Relationships: AVAILABLE_IN, REQUIRES_COUNTRY, ALLOWS_COUNTRY, TYPICAL_PARTNERS

Usage:
    python scripts/ingest_erasmus_to_neo4j.py [--clear]
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


class ErasmusNeo4jIngester:
    """
    Ingests Erasmus+ reference data into Neo4j for enhanced eligibility
    checking and recommendation capabilities.
    """

    # Erasmus+ Key Actions and sub-actions
    ERASMUS_ACTIONS = {
        # KA1 - Learning Mobility
        'KA1-HED': {
            'code': 'KA1-HED',
            'name': 'KA1 Higher Education Mobility',
            'key_action': 'KA1',
            'description': 'Learning mobility for higher education students and staff',
            'min_partners': 1,
            'min_countries': 1,
            'requires_eche': True,
            'coordinator_countries': 'programme',
            'partner_countries': 'worldwide',
            'duration_months_min': 2,
            'duration_months_max': 12,
            'typical_budget_min': 50000,
            'typical_budget_max': 500000,
            'funding_model': 'lump_sum',
        },
        'KA1-VET': {
            'code': 'KA1-VET',
            'name': 'KA1 VET Mobility',
            'key_action': 'KA1',
            'description': 'Learning mobility for VET learners and staff',
            'min_partners': 1,
            'min_countries': 1,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'worldwide',
            'duration_months_min': 1,
            'duration_months_max': 12,
            'typical_budget_min': 30000,
            'typical_budget_max': 300000,
            'funding_model': 'lump_sum',
        },
        'KA1-SCH': {
            'code': 'KA1-SCH',
            'name': 'KA1 School Education Mobility',
            'key_action': 'KA1',
            'description': 'Learning mobility for school pupils and staff',
            'min_partners': 1,
            'min_countries': 1,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 1,
            'duration_months_max': 12,
            'typical_budget_min': 20000,
            'typical_budget_max': 200000,
            'funding_model': 'lump_sum',
        },
        'KA1-ADU': {
            'code': 'KA1-ADU',
            'name': 'KA1 Adult Education Mobility',
            'key_action': 'KA1',
            'description': 'Learning mobility for adult education staff',
            'min_partners': 1,
            'min_countries': 1,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 1,
            'duration_months_max': 12,
            'typical_budget_min': 20000,
            'typical_budget_max': 150000,
            'funding_model': 'lump_sum',
        },
        'KA1-YOU': {
            'code': 'KA1-YOU',
            'name': 'KA1 Youth Mobility',
            'key_action': 'KA1',
            'description': 'Youth exchanges and mobility of youth workers',
            'min_partners': 2,
            'min_countries': 2,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'worldwide',
            'duration_months_min': 5,
            'duration_months_max': 60,
            'typical_budget_min': 10000,
            'typical_budget_max': 150000,
            'funding_model': 'lump_sum',
        },

        # KA2 - Cooperation Partnerships
        'KA2-COOP-HED': {
            'code': 'KA2-COOP-HED',
            'name': 'KA2 Cooperation Partnership Higher Education',
            'key_action': 'KA2',
            'description': 'Cooperation partnerships in higher education',
            'min_partners': 3,
            'min_countries': 3,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'worldwide',
            'duration_months_min': 12,
            'duration_months_max': 36,
            'typical_budget_min': 120000,
            'typical_budget_max': 400000,
            'funding_model': 'lump_sum',
        },
        'KA2-COOP-VET': {
            'code': 'KA2-COOP-VET',
            'name': 'KA2 Cooperation Partnership VET',
            'key_action': 'KA2',
            'description': 'Cooperation partnerships in vocational education',
            'min_partners': 3,
            'min_countries': 3,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'worldwide',
            'duration_months_min': 12,
            'duration_months_max': 36,
            'typical_budget_min': 120000,
            'typical_budget_max': 400000,
            'funding_model': 'lump_sum',
        },
        'KA2-COOP-SCH': {
            'code': 'KA2-COOP-SCH',
            'name': 'KA2 Cooperation Partnership School Education',
            'key_action': 'KA2',
            'description': 'Cooperation partnerships in school education',
            'min_partners': 3,
            'min_countries': 3,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 12,
            'duration_months_max': 36,
            'typical_budget_min': 120000,
            'typical_budget_max': 400000,
            'funding_model': 'lump_sum',
        },
        'KA2-COOP-ADU': {
            'code': 'KA2-COOP-ADU',
            'name': 'KA2 Cooperation Partnership Adult Education',
            'key_action': 'KA2',
            'description': 'Cooperation partnerships in adult education',
            'min_partners': 3,
            'min_countries': 3,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 12,
            'duration_months_max': 36,
            'typical_budget_min': 120000,
            'typical_budget_max': 400000,
            'funding_model': 'lump_sum',
        },
        'KA2-COOP-YOU': {
            'code': 'KA2-COOP-YOU',
            'name': 'KA2 Cooperation Partnership Youth',
            'key_action': 'KA2',
            'description': 'Cooperation partnerships in youth',
            'min_partners': 3,
            'min_countries': 3,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'worldwide',
            'duration_months_min': 12,
            'duration_months_max': 36,
            'typical_budget_min': 120000,
            'typical_budget_max': 400000,
            'funding_model': 'lump_sum',
        },

        # KA2 - Small-Scale Partnerships
        'KA2-SSP-HED': {
            'code': 'KA2-SSP-HED',
            'name': 'KA2 Small-Scale Partnership Higher Education',
            'key_action': 'KA2',
            'description': 'Small-scale partnerships in higher education',
            'min_partners': 2,
            'min_countries': 2,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 6,
            'duration_months_max': 24,
            'typical_budget_min': 30000,
            'typical_budget_max': 60000,
            'funding_model': 'lump_sum',
        },
        'KA2-SSP-VET': {
            'code': 'KA2-SSP-VET',
            'name': 'KA2 Small-Scale Partnership VET',
            'key_action': 'KA2',
            'description': 'Small-scale partnerships in vocational education',
            'min_partners': 2,
            'min_countries': 2,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 6,
            'duration_months_max': 24,
            'typical_budget_min': 30000,
            'typical_budget_max': 60000,
            'funding_model': 'lump_sum',
        },
        'KA2-SSP-SCH': {
            'code': 'KA2-SSP-SCH',
            'name': 'KA2 Small-Scale Partnership School Education',
            'key_action': 'KA2',
            'description': 'Small-scale partnerships in school education',
            'min_partners': 2,
            'min_countries': 2,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 6,
            'duration_months_max': 24,
            'typical_budget_min': 30000,
            'typical_budget_max': 60000,
            'funding_model': 'lump_sum',
        },
        'KA2-SSP-ADU': {
            'code': 'KA2-SSP-ADU',
            'name': 'KA2 Small-Scale Partnership Adult Education',
            'key_action': 'KA2',
            'description': 'Small-scale partnerships in adult education',
            'min_partners': 2,
            'min_countries': 2,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 6,
            'duration_months_max': 24,
            'typical_budget_min': 30000,
            'typical_budget_max': 60000,
            'funding_model': 'lump_sum',
        },
        'KA2-SSP-YOU': {
            'code': 'KA2-SSP-YOU',
            'name': 'KA2 Small-Scale Partnership Youth',
            'key_action': 'KA2',
            'description': 'Small-scale partnerships in youth',
            'min_partners': 2,
            'min_countries': 2,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 6,
            'duration_months_max': 24,
            'typical_budget_min': 30000,
            'typical_budget_max': 60000,
            'funding_model': 'lump_sum',
        },

        # KA2 - Capacity Building
        'KA2-CBHE': {
            'code': 'KA2-CBHE',
            'name': 'KA2 Capacity Building Higher Education',
            'key_action': 'KA2',
            'description': 'Capacity building in higher education with third countries',
            'min_partners': 4,
            'min_countries': 3,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'partner_regions',
            'duration_months_min': 24,
            'duration_months_max': 36,
            'typical_budget_min': 500000,
            'typical_budget_max': 1000000,
            'funding_model': 'lump_sum',
        },

        # Jean Monnet Actions
        'JMO-MODULE': {
            'code': 'JMO-MODULE',
            'name': 'Jean Monnet Module',
            'key_action': 'JMO',
            'description': 'Short teaching programme on EU studies',
            'min_partners': 1,
            'min_countries': 1,
            'requires_eche': False,
            'coordinator_countries': 'worldwide',
            'partner_countries': 'worldwide',
            'duration_months_min': 36,
            'duration_months_max': 36,
            'typical_budget_min': 30000,
            'typical_budget_max': 30000,
            'funding_model': 'lump_sum',
        },
        'JMO-CHAIR': {
            'code': 'JMO-CHAIR',
            'name': 'Jean Monnet Chair',
            'key_action': 'JMO',
            'description': 'Teaching post with specialization in EU studies',
            'min_partners': 1,
            'min_countries': 1,
            'requires_eche': False,
            'coordinator_countries': 'worldwide',
            'partner_countries': 'worldwide',
            'duration_months_min': 36,
            'duration_months_max': 36,
            'typical_budget_min': 50000,
            'typical_budget_max': 50000,
            'funding_model': 'lump_sum',
        },
        'JMO-COE': {
            'code': 'JMO-COE',
            'name': 'Jean Monnet Centre of Excellence',
            'key_action': 'JMO',
            'description': 'Focal point of knowledge on EU subjects',
            'min_partners': 1,
            'min_countries': 1,
            'requires_eche': False,
            'coordinator_countries': 'worldwide',
            'partner_countries': 'worldwide',
            'duration_months_min': 36,
            'duration_months_max': 36,
            'typical_budget_min': 100000,
            'typical_budget_max': 100000,
            'funding_model': 'lump_sum',
        },

        # Sport Actions
        'SPORT-COOP': {
            'code': 'SPORT-COOP',
            'name': 'Sport Cooperation Partnership',
            'key_action': 'SPORT',
            'description': 'Cooperation partnerships in grassroots sport',
            'min_partners': 3,
            'min_countries': 3,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 12,
            'duration_months_max': 36,
            'typical_budget_min': 120000,
            'typical_budget_max': 400000,
            'funding_model': 'lump_sum',
        },
        'SPORT-SSP': {
            'code': 'SPORT-SSP',
            'name': 'Sport Small-Scale Partnership',
            'key_action': 'SPORT',
            'description': 'Small-scale partnerships in grassroots sport',
            'min_partners': 2,
            'min_countries': 2,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 6,
            'duration_months_max': 24,
            'typical_budget_min': 30000,
            'typical_budget_max': 60000,
            'funding_model': 'lump_sum',
        },
        'SPORT-EVENT': {
            'code': 'SPORT-EVENT',
            'name': 'Sport Not-for-profit Event',
            'key_action': 'SPORT',
            'description': 'Not-for-profit European sport events',
            'min_partners': 3,
            'min_countries': 3,
            'requires_eche': False,
            'coordinator_countries': 'programme',
            'partner_countries': 'programme',
            'duration_months_min': 12,
            'duration_months_max': 18,
            'typical_budget_min': 200000,
            'typical_budget_max': 450000,
            'funding_model': 'lump_sum',
        },
    }

    # Erasmus+ Sectors
    ERASMUS_SECTORS = {
        'HED': {
            'code': 'HED',
            'name': 'Higher Education',
            'description': 'Universities and higher education institutions',
            'org_types': ['HEI', 'UNIVERSITY', 'COLLEGE'],
        },
        'VET': {
            'code': 'VET',
            'name': 'Vocational Education and Training',
            'description': 'VET providers and training organizations',
            'org_types': ['VET_PROVIDER', 'TRAINING_CENTRE', 'COMPANY'],
        },
        'SCH': {
            'code': 'SCH',
            'name': 'School Education',
            'description': 'Primary and secondary schools',
            'org_types': ['SCHOOL', 'PRIMARY_SCHOOL', 'SECONDARY_SCHOOL'],
        },
        'ADU': {
            'code': 'ADU',
            'name': 'Adult Education',
            'description': 'Adult learning providers',
            'org_types': ['ADULT_EDUCATION', 'LIFELONG_LEARNING', 'COMMUNITY_ORG'],
        },
        'YOU': {
            'code': 'YOU',
            'name': 'Youth',
            'description': 'Youth organizations and non-formal learning',
            'org_types': ['NGO', 'YOUTH_ORG', 'SOCIAL_ENTERPRISE'],
        },
        'SPORT': {
            'code': 'SPORT',
            'name': 'Sport',
            'description': 'Sport organizations and clubs',
            'org_types': ['SPORT_CLUB', 'SPORT_FEDERATION', 'NGO'],
        },
    }

    # Erasmus+ Programme Countries (EU + EEA + acceding)
    PROGRAMME_COUNTRIES = [
        # EU Member States
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE",
        # EEA Countries
        "IS", "LI", "NO",
        # Other Programme Countries
        "MK", "RS", "TR",
    ]

    # Partner Country Regions
    PARTNER_REGIONS = {
        'WESTERN_BALKANS': ['AL', 'BA', 'ME', 'XK'],
        'EASTERN_PARTNERSHIP': ['AM', 'AZ', 'BY', 'GE', 'MD', 'UA'],
        'SOUTHERN_MEDITERRANEAN': ['DZ', 'EG', 'IL', 'JO', 'LB', 'LY', 'MA', 'PS', 'SY', 'TN'],
        'RUSSIA': ['RU'],
        'ASIA': ['AF', 'BD', 'BT', 'CN', 'IN', 'ID', 'JP', 'KR', 'MY', 'MM', 'NP', 'PK', 'PH', 'SG', 'LK', 'TW', 'TH', 'VN'],
        'CENTRAL_ASIA': ['KZ', 'KG', 'TJ', 'TM', 'UZ'],
        'LATIN_AMERICA': ['AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'SV', 'GT', 'HT', 'HN', 'MX', 'NI', 'PA', 'PY', 'PE', 'UY', 'VE'],
        'AFRICA': ['AO', 'BJ', 'BW', 'BF', 'BI', 'CM', 'CV', 'CF', 'TD', 'KM', 'CD', 'CG', 'CI', 'DJ', 'GQ', 'ER', 'SZ', 'ET', 'GA', 'GM', 'GH', 'GN', 'GW', 'KE', 'LS', 'LR', 'MG', 'MW', 'ML', 'MR', 'MU', 'MZ', 'NA', 'NE', 'NG', 'RW', 'ST', 'SN', 'SC', 'SL', 'SO', 'ZA', 'SS', 'SD', 'TZ', 'TG', 'UG', 'ZM', 'ZW'],
        'CARIBBEAN': ['AG', 'BS', 'BB', 'BZ', 'DM', 'GD', 'GY', 'JM', 'KN', 'LC', 'VC', 'SR', 'TT'],
        'PACIFIC': ['AU', 'FJ', 'KI', 'MH', 'FM', 'NR', 'NZ', 'PW', 'PG', 'WS', 'SB', 'TO', 'TV', 'VU'],
        'OTHER_INDUSTRIALIZED': ['CA', 'US', 'CH', 'UK'],
    }

    def __init__(self):
        """Initialize the Erasmus+ ingester."""
        self.db = neo4j_db
        logger.info("Initialized Erasmus+ Neo4j Ingester")

    def create_constraints_and_indexes(self) -> None:
        """Create Neo4j constraints and indexes for Erasmus+ data."""
        logger.info("Creating Erasmus+ constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT erasmus_action_code IF NOT EXISTS FOR (a:ErasmusAction) REQUIRE a.code IS UNIQUE",
            "CREATE CONSTRAINT erasmus_sector_code IF NOT EXISTS FOR (s:ErasmusSector) REQUIRE s.code IS UNIQUE",
            "CREATE CONSTRAINT partner_region_code IF NOT EXISTS FOR (r:PartnerRegion) REQUIRE r.code IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX erasmus_action_key_action IF NOT EXISTS FOR (a:ErasmusAction) ON (a.key_action)",
            "CREATE INDEX erasmus_action_sector IF NOT EXISTS FOR (a:ErasmusAction) ON (a.sector)",
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

    def load_erasmus_sectors(self) -> None:
        """Load Erasmus+ sector nodes."""
        logger.info("Loading Erasmus+ sectors...")

        for code, info in self.ERASMUS_SECTORS.items():
            self.db.execute_query("""
                MERGE (s:ErasmusSector {code: $code})
                SET s.name = $name,
                    s.description = $description,
                    s.org_types = $org_types
            """, info)

        logger.info(f"Loaded {len(self.ERASMUS_SECTORS)} sectors")

    def load_erasmus_actions(self) -> None:
        """Load Erasmus+ action nodes with full metadata."""
        logger.info("Loading Erasmus+ actions...")

        for code, info in self.ERASMUS_ACTIONS.items():
            # Extract sector from action code if present
            sector = None
            for s in ['HED', 'VET', 'SCH', 'ADU', 'YOU', 'SPORT']:
                if s in code:
                    sector = s
                    break

            action_data = {
                **info,
                'sector': sector,
            }

            # Create action node
            self.db.execute_query("""
                MERGE (a:ErasmusAction {code: $code})
                SET a.name = $name,
                    a.key_action = $key_action,
                    a.description = $description,
                    a.min_partners = $min_partners,
                    a.min_countries = $min_countries,
                    a.requires_eche = $requires_eche,
                    a.coordinator_countries = $coordinator_countries,
                    a.partner_countries = $partner_countries,
                    a.duration_months_min = $duration_months_min,
                    a.duration_months_max = $duration_months_max,
                    a.typical_budget_min = $typical_budget_min,
                    a.typical_budget_max = $typical_budget_max,
                    a.funding_model = $funding_model,
                    a.sector = $sector
            """, action_data)

            # Link to sector if applicable
            if sector:
                self.db.execute_query("""
                    MATCH (a:ErasmusAction {code: $action_code})
                    MATCH (s:ErasmusSector {code: $sector_code})
                    MERGE (a)-[:AVAILABLE_IN]->(s)
                """, {"action_code": code, "sector_code": sector})

        logger.info(f"Loaded {len(self.ERASMUS_ACTIONS)} actions")

    def load_partner_regions(self) -> None:
        """Load partner region nodes."""
        logger.info("Loading partner regions...")

        # Create Programme Countries region
        self.db.execute_query("""
            MERGE (r:PartnerRegion {code: 'PROGRAMME'})
            SET r.name = 'Programme Countries',
                r.description = 'EU Member States, EEA, and acceding countries',
                r.countries = $countries
        """, {"countries": self.PROGRAMME_COUNTRIES})

        # Create partner regions
        for region_code, countries in self.PARTNER_REGIONS.items():
            self.db.execute_query("""
                MERGE (r:PartnerRegion {code: $code})
                SET r.name = $name,
                    r.countries = $countries
            """, {
                "code": region_code,
                "name": region_code.replace('_', ' ').title(),
                "countries": countries,
            })

        # Create Worldwide region
        all_partner_countries = []
        for countries in self.PARTNER_REGIONS.values():
            all_partner_countries.extend(countries)

        self.db.execute_query("""
            MERGE (r:PartnerRegion {code: 'WORLDWIDE'})
            SET r.name = 'Worldwide',
                r.description = 'All countries worldwide',
                r.countries = $countries
        """, {"countries": self.PROGRAMME_COUNTRIES + all_partner_countries})

        logger.info(f"Loaded {len(self.PARTNER_REGIONS) + 2} partner regions")

    def create_action_country_relationships(self) -> None:
        """Create relationships between actions and country regions."""
        logger.info("Creating action-country relationships...")

        for code, info in self.ERASMUS_ACTIONS.items():
            coordinator_countries = info['coordinator_countries']
            partner_countries = info['partner_countries']

            # Map country rules to regions
            region_mapping = {
                'programme': 'PROGRAMME',
                'worldwide': 'WORLDWIDE',
                'partner_regions': 'WORLDWIDE',
            }

            # Coordinator countries
            if coordinator_countries in region_mapping:
                self.db.execute_query("""
                    MATCH (a:ErasmusAction {code: $action_code})
                    MATCH (r:PartnerRegion {code: $region_code})
                    MERGE (a)-[:REQUIRES_COORDINATOR_FROM]->(r)
                """, {
                    "action_code": code,
                    "region_code": region_mapping[coordinator_countries],
                })

            # Partner countries
            if partner_countries in region_mapping:
                self.db.execute_query("""
                    MATCH (a:ErasmusAction {code: $action_code})
                    MATCH (r:PartnerRegion {code: $region_code})
                    MERGE (a)-[:ALLOWS_PARTNERS_FROM]->(r)
                """, {
                    "action_code": code,
                    "region_code": region_mapping[partner_countries],
                })

        logger.info("Action-country relationships created")

    def link_existing_countries(self) -> None:
        """Link existing Country nodes to PartnerRegions."""
        logger.info("Linking countries to regions...")

        # Link programme countries
        for country in self.PROGRAMME_COUNTRIES:
            self.db.execute_query("""
                MATCH (c:Country {isoCode: $country_code})
                MATCH (r:PartnerRegion {code: 'PROGRAMME'})
                MERGE (c)-[:MEMBER_OF]->(r)
                SET c.erasmus_programme_country = true
            """, {"country_code": country})

        # Link partner region countries
        for region_code, countries in self.PARTNER_REGIONS.items():
            for country in countries:
                self.db.execute_query("""
                    MERGE (c:Country {isoCode: $country_code})
                    SET c.erasmus_partner_country = true
                    WITH c
                    MATCH (r:PartnerRegion {code: $region_code})
                    MERGE (c)-[:MEMBER_OF]->(r)
                """, {"country_code": country, "region_code": region_code})

        logger.info("Country-region relationships created")

    def clear_erasmus_data(self) -> None:
        """Clear only Erasmus+ specific nodes and relationships."""
        logger.warning("Clearing Erasmus+ data from Neo4j...")

        queries = [
            "MATCH (a:ErasmusAction) DETACH DELETE a",
            "MATCH (s:ErasmusSector) DETACH DELETE s",
            "MATCH (r:PartnerRegion) DETACH DELETE r",
        ]

        for query in queries:
            self.db.execute_query(query)

        logger.info("Erasmus+ data cleared")

    def run(self, clear_first: bool = False) -> dict[str, int]:
        """
        Run the complete Erasmus+ ingestion pipeline.

        Args:
            clear_first: If True, clear Erasmus+ data before ingestion

        Returns:
            Statistics dict
        """
        logger.info("=" * 60)
        logger.info("ERASMUS+ -> Neo4j Reference Data Ingestion")
        logger.info("=" * 60)

        if clear_first:
            self.clear_erasmus_data()

        # Step 1: Create constraints/indexes
        self.create_constraints_and_indexes()

        # Step 2: Load sectors
        self.load_erasmus_sectors()

        # Step 3: Load actions
        self.load_erasmus_actions()

        # Step 4: Load partner regions
        self.load_partner_regions()

        # Step 5: Create action-country relationships
        self.create_action_country_relationships()

        # Step 6: Link existing countries
        self.link_existing_countries()

        # Get stats
        stats = self._get_stats()
        self._print_summary(stats)

        return stats

    def _get_stats(self) -> dict[str, int]:
        """Get current Erasmus+ data statistics."""
        query = """
        MATCH (a:ErasmusAction) WITH count(a) as actions
        MATCH (s:ErasmusSector) WITH actions, count(s) as sectors
        MATCH (r:PartnerRegion) WITH actions, sectors, count(r) as regions
        OPTIONAL MATCH (:ErasmusAction)-[rel:AVAILABLE_IN]->() WITH actions, sectors, regions, count(rel) as action_sector_rels
        OPTIONAL MATCH (:ErasmusAction)-[rel2:REQUIRES_COORDINATOR_FROM]->() WITH actions, sectors, regions, action_sector_rels, count(rel2) as coord_rels
        OPTIONAL MATCH (:ErasmusAction)-[rel3:ALLOWS_PARTNERS_FROM]->() WITH actions, sectors, regions, action_sector_rels, coord_rels, count(rel3) as partner_rels
        RETURN actions, sectors, regions, action_sector_rels, coord_rels, partner_rels
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
        logger.info("ERASMUS+ INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"ErasmusAction nodes: {stats.get('actions', 0)}")
        logger.info(f"ErasmusSector nodes: {stats.get('sectors', 0)}")
        logger.info(f"PartnerRegion nodes: {stats.get('regions', 0)}")
        logger.info(f"AVAILABLE_IN relationships: {stats.get('action_sector_rels', 0)}")
        logger.info(f"REQUIRES_COORDINATOR_FROM relationships: {stats.get('coord_rels', 0)}")
        logger.info(f"ALLOWS_PARTNERS_FROM relationships: {stats.get('partner_rels', 0)}")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest Erasmus+ data into Neo4j")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear Erasmus+ data before ingestion"
    )

    args = parser.parse_args()

    try:
        ingester = ErasmusNeo4jIngester()
        stats = ingester.run(clear_first=args.clear)

        if stats.get('actions', 0) > 0:
            logger.info("\nErasmus+ reference data loaded successfully!")
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
