"""
Creative Europe Eligibility Checker Tool

Checks organization eligibility for Creative Europe actions based on:
- Organization type (cultural organization, audiovisual company, NGO, etc.)
- Country (EU Member States, Associated Countries)
- Strand (CULTURE, MEDIA, Cross-sectoral)
- Specific action requirements

Creative Europe 2021-2027 has three strands:
- CULTURE: Support for cultural and creative sectors
- MEDIA: Support for audiovisual and film industries
- Cross-sectoral: News media, innovation labs, cross-cutting initiatives
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    """Result of eligibility check."""
    eligible: bool
    strand: str
    action_type: str
    action_name: str
    requirements_met: List[str]
    requirements_missing: List[str]
    warnings: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'eligible': self.eligible,
            'strand': self.strand,
            'action_type': self.action_type,
            'action_name': self.action_name,
            'requirements_met': self.requirements_met,
            'requirements_missing': self.requirements_missing,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'metadata': self.metadata,
        }


class CreativeEuropeEligibilityTool:
    """Tool for checking Creative Europe eligibility."""

    # EU Member States (Creative Europe participating countries)
    EU_MEMBER_STATES = [
        'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
        'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
        'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta',
        'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
        'Spain', 'Sweden',
    ]

    # Associated Countries (full participants in Creative Europe)
    ASSOCIATED_COUNTRIES = [
        'Iceland', 'Liechtenstein', 'Norway',  # EEA
        'Albania', 'Bosnia and Herzegovina', 'Georgia', 'Kosovo',
        'Moldova', 'Montenegro', 'North Macedonia', 'Serbia', 'Tunisia', 'Ukraine',
    ]

    # MEDIA sub-programme participating countries (more restricted)
    MEDIA_COUNTRIES = EU_MEMBER_STATES + [
        'Iceland', 'Liechtenstein', 'Norway', 'Albania', 'Bosnia and Herzegovina',
        'Georgia', 'Kosovo', 'Montenegro', 'North Macedonia', 'Serbia', 'Ukraine',
    ]

    # All participating countries
    PARTICIPATING_COUNTRIES = list(set(EU_MEMBER_STATES + ASSOCIATED_COUNTRIES))

    # Organization types
    ORG_TYPES = {
        'CULTURAL_ORG': 'Cultural Organization',
        'AUDIOVISUAL': 'Audiovisual/Film Company',
        'PRODUCTION': 'Production Company',
        'DISTRIBUTION': 'Distribution Company',
        'BROADCASTER': 'Broadcaster/VOD Platform',
        'CINEMA': 'Cinema/Exhibition Venue',
        'FESTIVAL': 'Festival Organizer',
        'TRAINING': 'Training Provider',
        'NGO': 'Non-Governmental Organization',
        'PUBLIC_BODY': 'Public Authority',
        'SME': 'Small/Medium Enterprise',
        'CONSORTIUM': 'Consortium/Network',
        'NEWS_MEDIA': 'News Media Organization',
        'RESEARCH': 'Research Organization',
    }

    # Creative Europe action eligibility rules
    ACTION_RULES = {
        # CULTURE strand actions
        'COOP-SMALL': {
            'name': 'European Cooperation Projects - Small Scale',
            'strand': 'CULTURE',
            'org_types': ['CULTURAL_ORG', 'NGO', 'PUBLIC_BODY', 'SME', 'RESEARCH'],
            'min_partners': 3,
            'min_countries': 3,
            'coordinator_eu': True,
            'budget_range': (200000, 200000),
            'duration_months': 48,
            'funding_rate': 80,
            'notes': 'Minimum 3 partners from 3 different eligible countries. Max 80% co-financing.',
        },
        'COOP-MEDIUM': {
            'name': 'European Cooperation Projects - Medium Scale',
            'strand': 'CULTURE',
            'org_types': ['CULTURAL_ORG', 'NGO', 'PUBLIC_BODY', 'SME', 'RESEARCH'],
            'min_partners': 5,
            'min_countries': 5,
            'coordinator_eu': True,
            'budget_range': (1000000, 1000000),
            'duration_months': 48,
            'funding_rate': 70,
            'notes': 'Minimum 5 partners from 5 different eligible countries. Max 70% co-financing.',
        },
        'COOP-LARGE': {
            'name': 'European Cooperation Projects - Large Scale',
            'strand': 'CULTURE',
            'org_types': ['CULTURAL_ORG', 'NGO', 'PUBLIC_BODY', 'SME', 'RESEARCH'],
            'min_partners': 10,
            'min_countries': 10,
            'coordinator_eu': True,
            'budget_range': (2000000, 2000000),
            'duration_months': 48,
            'funding_rate': 60,
            'notes': 'Minimum 10 partners from 10 different eligible countries. Max 60% co-financing.',
        },
        'NETWORK': {
            'name': 'European Networks',
            'strand': 'CULTURE',
            'org_types': ['CULTURAL_ORG', 'NGO', 'CONSORTIUM', 'PUBLIC_BODY'],
            'min_partners': 15,
            'min_countries': 10,
            'coordinator_eu': True,
            'budget_range': (2400000, 2400000),
            'duration_months': 48,
            'funding_rate': 80,
            'notes': 'Networks of cultural organizations. 15+ members from 10+ countries.',
        },
        'PLATFORM': {
            'name': 'European Platforms',
            'strand': 'CULTURE',
            'org_types': ['CULTURAL_ORG', 'NGO', 'CONSORTIUM', 'PUBLIC_BODY'],
            'min_partners': 12,
            'min_countries': 12,
            'coordinator_eu': True,
            'budget_range': (2000000, 2000000),
            'duration_months': 48,
            'funding_rate': 80,
            'notes': 'Platforms promoting emerging artists. 12+ members from 12+ countries.',
        },
        'LITERARY': {
            'name': 'European Literary Translation',
            'strand': 'CULTURE',
            'org_types': ['CULTURAL_ORG', 'SME'],  # Publishers
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (100000, 100000),
            'duration_months': 36,
            'funding_rate': 60,
            'notes': 'Publishers translating and promoting fiction. Single applicant.',
        },
        # MEDIA strand actions
        'DEVSLATE': {
            'name': 'MEDIA Development - Slate Funding',
            'strand': 'MEDIA',
            'org_types': ['PRODUCTION', 'AUDIOVISUAL', 'SME'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (150000, 210000),
            'duration_months': 36,
            'funding_rate': 70,
            'notes': 'Audiovisual production companies with track record. Slate of 3-5 projects.',
        },
        'DEVSINGLE': {
            'name': 'MEDIA Development - Single Project',
            'strand': 'MEDIA',
            'org_types': ['PRODUCTION', 'AUDIOVISUAL', 'SME'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (30000, 60000),
            'duration_months': 24,
            'funding_rate': 50,
            'notes': 'Development of single audiovisual work (film, series, VG).',
        },
        'DEVMINISLATE': {
            'name': 'MEDIA Development - Mini-Slate',
            'strand': 'MEDIA',
            'org_types': ['PRODUCTION', 'AUDIOVISUAL', 'SME'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (75000, 105000),
            'duration_months': 24,
            'funding_rate': 60,
            'notes': 'Development of 2-3 projects. For newer companies.',
        },
        'CODEV': {
            'name': 'MEDIA Co-Development',
            'strand': 'MEDIA',
            'org_types': ['PRODUCTION', 'AUDIOVISUAL'],
            'min_partners': 2,
            'min_countries': 2,
            'coordinator_eu': True,
            'budget_range': (60000, 100000),
            'duration_months': 24,
            'funding_rate': 50,
            'notes': 'European co-development of audiovisual work. Min 2 companies from 2 countries.',
        },
        'TVONLINE': {
            'name': 'MEDIA TV and Online Content',
            'strand': 'MEDIA',
            'org_types': ['PRODUCTION', 'BROADCASTER', 'AUDIOVISUAL'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (1000000, 3000000),
            'duration_months': 36,
            'funding_rate': 80,
            'notes': 'Production of TV series and online content with cross-border potential.',
        },
        'TRAINING': {
            'name': 'MEDIA Training',
            'strand': 'MEDIA',
            'org_types': ['TRAINING', 'AUDIOVISUAL', 'NGO', 'RESEARCH'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (150000, 400000),
            'duration_months': 24,
            'funding_rate': 80,
            'notes': 'Training activities for audiovisual professionals. European dimension required.',
        },
        'MARKETNET': {
            'name': 'MEDIA Markets and Networking',
            'strand': 'MEDIA',
            'org_types': ['AUDIOVISUAL', 'FESTIVAL', 'CONSORTIUM', 'NGO'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (500000, 1000000),
            'duration_months': 36,
            'funding_rate': 80,
            'notes': 'Markets, pitching events, and industry networking activities.',
        },
        'FILMDIST': {
            'name': 'MEDIA Film Distribution',
            'strand': 'MEDIA',
            'org_types': ['DISTRIBUTION', 'AUDIOVISUAL'],
            'min_partners': 5,
            'min_countries': 5,
            'coordinator_eu': True,
            'budget_range': (200000, 400000),
            'duration_months': 24,
            'funding_rate': 60,
            'notes': 'Grouping of distributors for non-national European films.',
        },
        'FILMSALES': {
            'name': 'MEDIA Film Sales Agents',
            'strand': 'MEDIA',
            'org_types': ['DISTRIBUTION', 'AUDIOVISUAL'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (300000, 500000),
            'duration_months': 24,
            'funding_rate': 80,
            'notes': 'Support for international sales agents of European films.',
        },
        'CINNET': {
            'name': 'MEDIA Cinema Networks',
            'strand': 'MEDIA',
            'org_types': ['CINEMA', 'CONSORTIUM'],
            'min_partners': 100,  # 100 cinemas
            'min_countries': 20,
            'coordinator_eu': True,
            'budget_range': (5000000, 7000000),
            'duration_months': 24,
            'funding_rate': 50,
            'notes': 'Europa Cinemas network. 100+ screens across 20+ countries.',
        },
        'FEST': {
            'name': 'MEDIA Film Festivals',
            'strand': 'MEDIA',
            'org_types': ['FESTIVAL', 'CULTURAL_ORG', 'NGO'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (75000, 150000),
            'duration_months': 24,
            'funding_rate': 80,
            'notes': 'European film festivals with significant European programming.',
        },
        'AUDFILMEDU': {
            'name': 'MEDIA Audience Development - Film Education',
            'strand': 'MEDIA',
            'org_types': ['CULTURAL_ORG', 'TRAINING', 'NGO', 'RESEARCH'],
            'min_partners': 3,
            'min_countries': 3,
            'coordinator_eu': True,
            'budget_range': (400000, 600000),
            'duration_months': 36,
            'funding_rate': 80,
            'notes': 'Film literacy and audience development projects.',
        },
        'INNOVBUSMOD': {
            'name': 'MEDIA Innovative Business Models',
            'strand': 'MEDIA',
            'org_types': ['AUDIOVISUAL', 'SME', 'BROADCASTER'],
            'min_partners': 3,
            'min_countries': 3,
            'coordinator_eu': True,
            'budget_range': (500000, 1000000),
            'duration_months': 36,
            'funding_rate': 70,
            'notes': 'Innovation in audiovisual value chain. Promotion tools, data analytics.',
        },
        'DEVVGIM': {
            'name': 'MEDIA Video Games & Immersive Content',
            'strand': 'MEDIA',
            'org_types': ['AUDIOVISUAL', 'SME', 'PRODUCTION'],
            'min_partners': 1,
            'min_countries': 1,
            'coordinator_eu': True,
            'budget_range': (150000, 200000),
            'duration_months': 24,
            'funding_rate': 50,
            'notes': 'Development of video games and immersive content.',
        },
        # Cross-sectoral actions
        'INNOVLAB': {
            'name': 'Creative Innovation Lab',
            'strand': 'CROSS-SECTORAL',
            'org_types': ['CULTURAL_ORG', 'AUDIOVISUAL', 'SME', 'RESEARCH', 'NEWS_MEDIA'],
            'min_partners': 3,
            'min_countries': 3,
            'coordinator_eu': True,
            'budget_range': (2000000, 4000000),
            'duration_months': 48,
            'funding_rate': 60,
            'notes': 'Cross-sector innovation labs. Combine culture, tech, and media.',
        },
        'JOURPART': {
            'name': 'News Media Partnerships',
            'strand': 'CROSS-SECTORAL',
            'org_types': ['NEWS_MEDIA', 'NGO', 'RESEARCH'],
            'min_partners': 3,
            'min_countries': 3,
            'coordinator_eu': True,
            'budget_range': (1000000, 3000000),
            'duration_months': 36,
            'funding_rate': 80,
            'notes': 'Cross-border collaborations of news media organizations.',
        },
        'MEDIALITERACY': {
            'name': 'Media Literacy',
            'strand': 'CROSS-SECTORAL',
            'org_types': ['NGO', 'PUBLIC_BODY', 'RESEARCH', 'NEWS_MEDIA'],
            'min_partners': 3,
            'min_countries': 3,
            'coordinator_eu': True,
            'budget_range': (500000, 2000000),
            'duration_months': 36,
            'funding_rate': 70,
            'notes': 'Media literacy projects. Countering disinformation.',
        },
        'MFP': {
            'name': 'Music Moves Europe',
            'strand': 'CROSS-SECTORAL',
            'org_types': ['CULTURAL_ORG', 'SME', 'FESTIVAL', 'NGO'],
            'min_partners': 3,
            'min_countries': 3,
            'coordinator_eu': True,
            'budget_range': (500000, 1500000),
            'duration_months': 36,
            'funding_rate': 70,
            'notes': 'Music sector support. Cross-border distribution, touring, training.',
        },
    }

    def check_eligibility(
        self,
        org_type: str,
        country: str,
        action_type: str,
        is_coordinator: bool = True,
    ) -> EligibilityResult:
        """
        Check if an organization is eligible for a specific Creative Europe action.

        Args:
            org_type: Organization type (e.g., 'CULTURAL_ORG', 'PRODUCTION', 'NGO')
            country: Country name
            action_type: Creative Europe action type (e.g., 'COOP-SMALL', 'DEVSLATE')
            is_coordinator: Whether checking as coordinator or partner

        Returns:
            EligibilityResult with detailed eligibility information
        """
        requirements_met = []
        requirements_missing = []
        warnings = []
        recommendations = []

        # Normalize action type
        action_type = action_type.upper().replace('_', '-')

        # Get action rules
        rules = self.ACTION_RULES.get(action_type)
        if not rules:
            return EligibilityResult(
                eligible=False,
                strand='UNKNOWN',
                action_type=action_type,
                action_name='Unknown Action',
                requirements_met=[],
                requirements_missing=[f'Unknown action type: {action_type}'],
                warnings=[],
                recommendations=[
                    'Valid CULTURE actions: COOP-SMALL, COOP-MEDIUM, COOP-LARGE, NETWORK, PLATFORM, LITERARY',
                    'Valid MEDIA actions: DEVSLATE, DEVSINGLE, DEVMINISLATE, CODEV, TVONLINE, TRAINING, MARKETNET, FILMDIST, FILMSALES, CINNET, FEST, AUDFILMEDU, INNOVBUSMOD, DEVVGIM',
                    'Valid Cross-sectoral actions: INNOVLAB, JOURPART, MEDIALITERACY, MFP'
                ],
                metadata={'error': 'unknown_action'}
            )

        action_name = rules['name']
        strand = rules['strand']

        # Check 1: Organization type
        org_type_upper = org_type.upper().replace(' ', '_')
        if org_type_upper in rules['org_types']:
            requirements_met.append(f'Organization type {self.ORG_TYPES.get(org_type_upper, org_type_upper)} is eligible')
        else:
            eligible_types = [self.ORG_TYPES.get(t, t) for t in rules['org_types']]
            requirements_missing.append(
                f'Organization type not eligible. '
                f'Eligible types: {", ".join(eligible_types)}'
            )

        # Check 2: Country eligibility
        is_participating = country in self.PARTICIPATING_COUNTRIES

        # MEDIA has more restricted country eligibility
        if strand == 'MEDIA':
            is_media_country = country in self.MEDIA_COUNTRIES
            if is_media_country:
                requirements_met.append(f'{country} participates in MEDIA sub-programme')
            else:
                requirements_missing.append(
                    f'{country} does not fully participate in MEDIA sub-programme. '
                    f'Check specific action requirements.'
                )
        else:
            if is_participating:
                requirements_met.append(f'{country} is a Creative Europe participating country')
            else:
                requirements_missing.append(
                    f'{country} is not a Creative Europe participating country'
                )

        # Check 3: Coordinator requirements
        if is_coordinator and rules.get('coordinator_eu'):
            if country in self.EU_MEMBER_STATES + self.ASSOCIATED_COUNTRIES:
                requirements_met.append('Can act as project coordinator')
            else:
                requirements_missing.append(
                    'Coordinator must be from EU Member State or Associated Country'
                )

        # Check 4: Consortium requirements
        min_partners = rules.get('min_partners', 1)
        min_countries = rules.get('min_countries', 1)

        if min_partners > 1:
            recommendations.append(
                f'Consortium requires minimum {min_partners} organizations from {min_countries} different countries'
            )

        # Add budget and funding information
        budget_range = rules.get('budget_range')
        funding_rate = rules.get('funding_rate', 50)
        duration = rules.get('duration_months', 24)

        recommendations.append(
            f'EU grant: up to {budget_range[1]:,.0f} ({funding_rate}% funding rate)'
        )
        recommendations.append(
            f'Duration: up to {duration} months'
        )

        # Add action-specific notes
        if rules.get('notes'):
            recommendations.append(rules['notes'])

        # Add warnings for specific strands
        if strand == 'MEDIA' and org_type_upper == 'PRODUCTION':
            warnings.append(
                'Production companies may need to demonstrate track record (previous audiovisual works)'
            )

        if strand == 'CULTURE':
            warnings.append(
                'CULTURE projects must demonstrate strong European dimension and cross-border cooperation'
            )

        # Determine overall eligibility
        eligible = len(requirements_missing) == 0

        return EligibilityResult(
            eligible=eligible,
            strand=strand,
            action_type=action_type,
            action_name=action_name,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            warnings=warnings,
            recommendations=recommendations,
            metadata={
                'org_type': org_type_upper,
                'country': country,
                'is_coordinator': is_coordinator,
                'budget_range': budget_range,
                'funding_rate': funding_rate,
                'duration_months': duration,
            }
        )

    def get_eligible_actions(
        self,
        org_type: str,
        country: str,
        strand: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all Creative Europe actions an organization is eligible for.

        Args:
            org_type: Organization type
            country: Country of the organization
            strand: Filter by strand (CULTURE, MEDIA, CROSS-SECTORAL)

        Returns:
            List of eligible actions with details
        """
        eligible_actions = []

        for action_type, rules in self.ACTION_RULES.items():
            # Filter by strand if specified
            if strand and rules['strand'].upper() != strand.upper():
                continue

            result = self.check_eligibility(
                org_type=org_type,
                country=country,
                action_type=action_type,
                is_coordinator=True,
            )

            if result.eligible:
                eligible_actions.append({
                    'action_type': action_type,
                    'action_name': result.action_name,
                    'strand': result.strand,
                    'budget_range': rules.get('budget_range'),
                    'funding_rate': rules.get('funding_rate'),
                    'duration_months': rules.get('duration_months'),
                    'warnings': result.warnings,
                    'notes': rules.get('notes'),
                })

        return eligible_actions

    def get_participating_countries(self) -> Dict[str, List[str]]:
        """Get participating countries by category."""
        return {
            'eu_member_states': self.EU_MEMBER_STATES.copy(),
            'associated_countries': self.ASSOCIATED_COUNTRIES.copy(),
            'media_countries': self.MEDIA_COUNTRIES.copy(),
        }

    def get_strands(self) -> List[Dict[str, Any]]:
        """Get overview of Creative Europe strands."""
        return [
            {
                'strand': 'CULTURE',
                'description': 'Support for cultural and creative sectors',
                'actions': ['COOP-SMALL', 'COOP-MEDIUM', 'COOP-LARGE', 'NETWORK', 'PLATFORM', 'LITERARY'],
            },
            {
                'strand': 'MEDIA',
                'description': 'Support for audiovisual and film industries',
                'actions': ['DEVSLATE', 'DEVSINGLE', 'DEVMINISLATE', 'CODEV', 'TVONLINE', 'TRAINING',
                           'MARKETNET', 'FILMDIST', 'FILMSALES', 'CINNET', 'FEST', 'AUDFILMEDU',
                           'INNOVBUSMOD', 'DEVVGIM'],
            },
            {
                'strand': 'CROSS-SECTORAL',
                'description': 'Cross-cutting support for innovation, media, and music',
                'actions': ['INNOVLAB', 'JOURPART', 'MEDIALITERACY', 'MFP'],
            },
        ]


# Tool execution function for ToolAwareAgent
async def check_creative_europe_eligibility_execute(
    org_type: str,
    country: str,
    action_type: Optional[str] = None,
    strand: Optional[str] = None,
    is_coordinator: bool = True,
) -> Dict[str, Any]:
    """
    Check Creative Europe eligibility for an organization.

    Args:
        org_type: Organization type (CULTURAL_ORG, PRODUCTION, AUDIOVISUAL, NGO, etc.)
        country: Country of the organization
        action_type: Specific action to check (or None for all actions)
        strand: Filter by strand (CULTURE, MEDIA, CROSS-SECTORAL)
        is_coordinator: Whether checking as coordinator

    Returns:
        Eligibility result with requirements and recommendations
    """
    tool = CreativeEuropeEligibilityTool()

    if action_type:
        # Check specific action
        result = tool.check_eligibility(
            org_type=org_type,
            country=country,
            action_type=action_type,
            is_coordinator=is_coordinator,
        )

        response = {
            'success': True,
            'result': result.to_dict(),
            'metadata': {
                'tool': 'check_creative_europe_eligibility',
                'query_type': 'specific_action',
                'programme': 'creative_europe',
                'source': 'hardcoded_rules',
            }
        }

        # Try to enrich with Neo4j graph data
        graph_result = _try_graph_eligibility_check(country, action_type=action_type)
        if graph_result:
            response['graph_data'] = graph_result
            response['metadata']['source'] = 'hybrid_graph_rules'

        return response
    else:
        # Get all eligible actions
        eligible_actions = tool.get_eligible_actions(
            org_type=org_type,
            country=country,
            strand=strand,
        )

        response = {
            'success': True,
            'eligible_actions': eligible_actions,
            'total_eligible': len(eligible_actions),
            'strands': tool.get_strands(),
            'metadata': {
                'tool': 'check_creative_europe_eligibility',
                'query_type': 'all_actions',
                'org_type': org_type,
                'country': country,
                'strand_filter': strand,
                'programme': 'creative_europe',
                'source': 'hardcoded_rules',
            }
        }

        # Try to enrich with Neo4j graph data
        graph_result = _try_graph_eligibility_check(country, strand=strand)
        if graph_result:
            response['graph_data'] = graph_result
            response['metadata']['source'] = 'hybrid_graph_rules'

        return response


# Country name to ISO code mapping for Neo4j lookups
COUNTRY_NAME_TO_ISO = {
    # EU Member States
    'Austria': 'AT', 'Belgium': 'BE', 'Bulgaria': 'BG', 'Croatia': 'HR',
    'Cyprus': 'CY', 'Czech Republic': 'CZ', 'Denmark': 'DK', 'Estonia': 'EE',
    'Finland': 'FI', 'France': 'FR', 'Germany': 'DE', 'Greece': 'GR',
    'Hungary': 'HU', 'Ireland': 'IE', 'Italy': 'IT', 'Latvia': 'LV',
    'Lithuania': 'LT', 'Luxembourg': 'LU', 'Malta': 'MT', 'Netherlands': 'NL',
    'Poland': 'PL', 'Portugal': 'PT', 'Romania': 'RO', 'Slovakia': 'SK',
    'Slovenia': 'SI', 'Spain': 'ES', 'Sweden': 'SE',
    # EEA
    'Iceland': 'IS', 'Liechtenstein': 'LI', 'Norway': 'NO',
    # Other Associated Countries
    'Albania': 'AL', 'Bosnia and Herzegovina': 'BA', 'Georgia': 'GE',
    'Kosovo': 'XK', 'Moldova': 'MD', 'Montenegro': 'ME',
    'North Macedonia': 'MK', 'Serbia': 'RS', 'Tunisia': 'TN', 'Ukraine': 'UA',
    # Common variations
    'UK': 'GB', 'United Kingdom': 'GB', 'Switzerland': 'CH',
}


def _try_graph_eligibility_check(
    country: str,
    action_type: Optional[str] = None,
    strand: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Try to use Neo4j graph for Creative Europe eligibility check.

    Returns None if Neo4j data not available, otherwise returns graph results.
    """
    try:
        from app.core.neo4j_config import neo4j_db

        # Convert country name to ISO code
        country_code = COUNTRY_NAME_TO_ISO.get(country, country.upper()[:2])

        if action_type:
            # Get action details from graph
            result = neo4j_db.execute_query("""
                MATCH (a:CreativeEuropeAction {code: $action_code})
                OPTIONAL MATCH (a)-[:BELONGS_TO_STRAND]->(s:CreativeEuropeStrand)
                OPTIONAL MATCH (a)-[:ALLOWS_COORDINATOR_FROM]->(r:CreativeEuropeRegion)
                RETURN a {
                    .code, .name, .description, .min_partners, .min_countries,
                    .grant_min, .grant_max, .funding_rate, .duration_months_max,
                    .funding_model, .org_types
                } as action,
                s.code as strand,
                r.countries as eligible_countries
            """, {"action_code": action_type.upper()})

            if result:
                action_data = result[0]
                eligible_countries = action_data.get('eligible_countries', [])
                is_eligible = country_code in eligible_countries

                return {
                    'action_details': action_data.get('action'),
                    'strand': action_data.get('strand'),
                    'country_eligible': is_eligible,
                    'country_code': country_code,
                    'source': 'neo4j_graph'
                }

        elif strand:
            # Get strand details and eligible actions from graph
            result = neo4j_db.execute_query("""
                MATCH (s:CreativeEuropeStrand {code: $strand_code})
                OPTIONAL MATCH (a:CreativeEuropeAction)-[:BELONGS_TO_STRAND]->(s)
                OPTIONAL MATCH (s)-[:ALLOWS_COUNTRIES]->(r:CreativeEuropeRegion)
                RETURN s {.code, .name, .description, .budget_share, .org_types} as strand,
                       collect(a {.code, .name, .grant_max, .funding_rate}) as actions,
                       r.countries as eligible_countries
            """, {"strand_code": strand.upper()})

            if result:
                strand_data = result[0]
                eligible_countries = strand_data.get('eligible_countries', [])
                is_eligible = country_code in eligible_countries

                return {
                    'strand_details': strand_data.get('strand'),
                    'actions': strand_data.get('actions'),
                    'country_eligible': is_eligible,
                    'country_code': country_code,
                    'source': 'neo4j_graph'
                }

        else:
            # Get all strands and country eligibility
            result = neo4j_db.execute_query("""
                MATCH (c:Country {isoCode: $country_code})
                RETURN c.creative_europe_eligible as eligible,
                       c.creative_europe_media_eligible as media_eligible
            """, {"country_code": country_code})

            if result:
                country_data = result[0]
                return {
                    'country_code': country_code,
                    'eligible': country_data.get('eligible', False),
                    'media_eligible': country_data.get('media_eligible', False),
                    'source': 'neo4j_graph'
                }

    except Exception as e:
        logger.debug(f"Neo4j eligibility check not available: {e}")

    return None
