"""
Erasmus+ Eligibility Checker Tool

Checks organization eligibility for Erasmus+ actions based on:
- Organization type (HEI, school, NGO, public body, etc.)
- Country (Programme Country vs Partner Country)
- ECHE status (for higher education)
- Key Action requirements
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    """Result of eligibility check."""
    eligible: bool
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
            'action_type': self.action_type,
            'action_name': self.action_name,
            'requirements_met': self.requirements_met,
            'requirements_missing': self.requirements_missing,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'metadata': self.metadata,
        }


class ErasmusEligibilityTool:
    """Tool for checking Erasmus+ eligibility."""

    # EU Member States
    EU_MEMBER_STATES = [
        'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
        'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
        'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta',
        'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
        'Spain', 'Sweden',
    ]

    # Associated Countries (full participants)
    ASSOCIATED_COUNTRIES = [
        'Iceland', 'Liechtenstein', 'Norway',  # EEA
        'North Macedonia', 'Serbia', 'Turkey',  # Candidate countries
    ]

    # Programme Countries = EU + Associated
    PROGRAMME_COUNTRIES = EU_MEMBER_STATES + ASSOCIATED_COUNTRIES

    # Partner Countries (partial participation)
    PARTNER_REGIONS = {
        'Western Balkans': ['Albania', 'Bosnia and Herzegovina', 'Kosovo', 'Montenegro'],
        'Eastern Partnership': ['Armenia', 'Azerbaijan', 'Belarus', 'Georgia', 'Moldova', 'Ukraine'],
        'Southern Mediterranean': ['Algeria', 'Egypt', 'Israel', 'Jordan', 'Lebanon', 'Libya', 'Morocco', 'Palestine', 'Syria', 'Tunisia'],
        'Other': ['All other countries'],
    }

    # Organization types
    ORG_TYPES = {
        'HEI': 'Higher Education Institution',
        'SCHOOL': 'School (primary/secondary)',
        'VET_PROVIDER': 'VET Training Provider',
        'ADULT_ED': 'Adult Education Provider',
        'YOUTH_ORG': 'Youth Organization',
        'NGO': 'Non-Governmental Organization',
        'PUBLIC_BODY': 'Public Body',
        'ENTERPRISE': 'Enterprise/Company',
        'SPORT_ORG': 'Sport Organization',
        'RESEARCH': 'Research Organization',
    }

    # Action eligibility rules
    ACTION_RULES = {
        'KA1-HED': {
            'name': 'Higher Education Mobility',
            'org_types': ['HEI'],
            'requires_eche': True,
            'country_rule': 'programme_or_partner',
            'min_partners': 1,
            'notes': 'ECHE required for HEIs in Programme Countries',
        },
        'KA1-VET': {
            'name': 'VET Mobility',
            'org_types': ['VET_PROVIDER', 'ENTERPRISE', 'PUBLIC_BODY'],
            'requires_eche': False,
            'country_rule': 'programme_only',
            'min_partners': 1,
            'notes': 'Applicant must be from Programme Country',
        },
        'KA1-SCH': {
            'name': 'School Staff Mobility',
            'org_types': ['SCHOOL', 'PUBLIC_BODY'],
            'requires_eche': False,
            'country_rule': 'programme_only',
            'min_partners': 1,
            'notes': 'Schools and school authorities eligible',
        },
        'KA1-ADU': {
            'name': 'Adult Education Mobility',
            'org_types': ['ADULT_ED', 'NGO', 'PUBLIC_BODY'],
            'requires_eche': False,
            'country_rule': 'programme_only',
            'min_partners': 1,
            'notes': 'Adult learning organizations eligible',
        },
        'KA1-YOU': {
            'name': 'Youth Mobility',
            'org_types': ['YOUTH_ORG', 'NGO', 'PUBLIC_BODY'],
            'requires_eche': False,
            'country_rule': 'programme_or_partner',
            'min_partners': 1,
            'notes': 'Youth exchanges and volunteering',
        },
        'KA2-COOP': {
            'name': 'Cooperation Partnership',
            'org_types': ['HEI', 'SCHOOL', 'VET_PROVIDER', 'ADULT_ED', 'YOUTH_ORG', 'NGO', 'PUBLIC_BODY', 'ENTERPRISE'],
            'requires_eche': True,  # Only for HEIs
            'country_rule': 'programme_only',
            'min_partners': 3,
            'min_countries': 3,
            'notes': 'Minimum 3 organizations from 3 different Programme Countries',
        },
        'KA2-SSP': {
            'name': 'Small-Scale Partnership',
            'org_types': ['HEI', 'SCHOOL', 'VET_PROVIDER', 'ADULT_ED', 'YOUTH_ORG', 'NGO', 'PUBLIC_BODY'],
            'requires_eche': True,  # Only for HEIs
            'country_rule': 'programme_only',
            'min_partners': 2,
            'min_countries': 2,
            'notes': 'Minimum 2 organizations from 2 different Programme Countries',
        },
        'KA2-CBHE': {
            'name': 'Capacity Building Higher Education',
            'org_types': ['HEI'],
            'requires_eche': True,
            'country_rule': 'programme_and_partner',
            'min_partners': 4,
            'notes': 'Consortium must include HEIs from Partner Countries',
        },
        'KA2-ALLIANCES': {
            'name': 'Alliances for Innovation',
            'org_types': ['HEI', 'VET_PROVIDER', 'ENTERPRISE', 'RESEARCH'],
            'requires_eche': True,
            'country_rule': 'programme_only',
            'min_partners': 4,
            'min_countries': 3,
            'notes': 'HEIs/VET + business/industry partnership required',
        },
        'KA2-COE': {
            'name': 'Centres of Vocational Excellence',
            'org_types': ['VET_PROVIDER', 'ENTERPRISE', 'PUBLIC_BODY', 'RESEARCH'],
            'requires_eche': False,
            'country_rule': 'programme_only',
            'min_partners': 4,
            'min_countries': 4,
            'notes': 'Multi-stakeholder VET partnerships',
        },
        'JMO-MODULE': {
            'name': 'Jean Monnet Module',
            'org_types': ['HEI'],
            'requires_eche': True,  # In Programme Countries
            'country_rule': 'worldwide',
            'min_partners': 1,
            'notes': 'HEIs worldwide eligible; ECHE required in Programme Countries',
        },
        'JMO-CHAIR': {
            'name': 'Jean Monnet Chair',
            'org_types': ['HEI'],
            'requires_eche': True,
            'country_rule': 'worldwide',
            'min_partners': 1,
            'notes': 'Teaching positions on EU studies',
        },
        'JMO-COE': {
            'name': 'Jean Monnet Centre of Excellence',
            'org_types': ['HEI'],
            'requires_eche': True,
            'country_rule': 'worldwide',
            'min_partners': 1,
            'notes': 'Centres gathering EU studies expertise',
        },
        'SPORT-COOP': {
            'name': 'Sport Cooperation Partnership',
            'org_types': ['SPORT_ORG', 'NGO', 'PUBLIC_BODY'],
            'requires_eche': False,
            'country_rule': 'programme_only',
            'min_partners': 3,
            'min_countries': 3,
            'notes': 'Sport organizations and clubs eligible',
        },
        'SPORT-SSCP': {
            'name': 'Sport Small-Scale Partnership',
            'org_types': ['SPORT_ORG', 'NGO', 'PUBLIC_BODY'],
            'requires_eche': False,
            'country_rule': 'programme_only',
            'min_partners': 2,
            'min_countries': 2,
            'notes': 'Smaller sport partnerships',
        },
    }

    def check_eligibility(
        self,
        org_type: str,
        country: str,
        action_type: str,
        has_eche: bool = False,
        is_coordinator: bool = True,
    ) -> EligibilityResult:
        """
        Check if an organization is eligible for a specific Erasmus+ action.

        Args:
            org_type: Organization type (e.g., 'HEI', 'SCHOOL', 'NGO')
            country: Country name
            action_type: Erasmus+ action type (e.g., 'KA1-HED', 'KA2-COOP')
            has_eche: Whether the organization has ECHE (for HEIs)
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
                action_type=action_type,
                action_name='Unknown Action',
                requirements_met=[],
                requirements_missing=[f'Unknown action type: {action_type}'],
                warnings=[],
                recommendations=[
                    'Valid action types: KA1-HED, KA1-VET, KA1-SCH, KA1-ADU, KA1-YOU, '
                    'KA2-COOP, KA2-SSP, KA2-CBHE, KA2-ALLIANCES, KA2-COE, '
                    'JMO-MODULE, JMO-CHAIR, JMO-COE, SPORT-COOP, SPORT-SSCP'
                ],
                metadata={'error': 'unknown_action'}
            )

        action_name = rules['name']

        # Check 1: Organization type
        org_type_upper = org_type.upper().replace(' ', '_')
        if org_type_upper in rules['org_types']:
            requirements_met.append(f'Organization type {org_type_upper} is eligible')
        else:
            requirements_missing.append(
                f'Organization type {org_type_upper} not eligible. '
                f'Eligible types: {", ".join(rules["org_types"])}'
            )

        # Check 2: Country eligibility
        is_programme_country = country in self.PROGRAMME_COUNTRIES
        is_partner_country = not is_programme_country

        country_rule = rules['country_rule']

        if country_rule == 'programme_only':
            if is_programme_country:
                requirements_met.append(f'{country} is a Programme Country')
            else:
                requirements_missing.append(
                    f'{country} is not a Programme Country. '
                    f'Only Programme Countries can participate in {action_name}'
                )
        elif country_rule == 'programme_or_partner':
            requirements_met.append(f'{country} can participate')
            if is_partner_country:
                warnings.append(
                    f'{country} is a Partner Country. '
                    f'Some restrictions may apply.'
                )
        elif country_rule == 'programme_and_partner':
            requirements_met.append(f'{country} can participate')
            if is_programme_country:
                recommendations.append(
                    'Consider including Partner Country organizations in your consortium'
                )
        elif country_rule == 'worldwide':
            requirements_met.append(f'{country} is eligible (worldwide action)')

        # Check 3: ECHE requirement (only for HEIs)
        if org_type_upper == 'HEI' and rules.get('requires_eche'):
            if is_programme_country:
                if has_eche:
                    requirements_met.append('ECHE (Erasmus Charter) held')
                else:
                    requirements_missing.append(
                        'ECHE (Erasmus Charter for Higher Education) required. '
                        'Apply for ECHE before submitting Erasmus+ application.'
                    )
                    recommendations.append(
                        'Apply for ECHE at: https://erasmus-plus.ec.europa.eu/eche'
                    )

        # Check 4: Coordinator vs Partner rules
        if is_coordinator:
            if country_rule == 'programme_only' and not is_programme_country:
                if 'Coordinator must be from a Programme Country' not in requirements_missing:
                    requirements_missing.append(
                        'Coordinator must be from a Programme Country'
                    )
        else:
            # Partner rules are usually more flexible
            if requirements_missing:
                # Check if partner participation is allowed
                if country_rule in ['programme_or_partner', 'programme_and_partner', 'worldwide']:
                    requirements_met.append('Eligible as consortium partner')

        # Add consortium notes
        if rules.get('min_partners'):
            recommendations.append(
                f'Minimum {rules["min_partners"]} organizations required in consortium'
            )
        if rules.get('min_countries'):
            recommendations.append(
                f'Partners must be from at least {rules["min_countries"]} different countries'
            )

        # Add action-specific notes
        if rules.get('notes'):
            recommendations.append(rules['notes'])

        # Determine overall eligibility
        eligible = len(requirements_missing) == 0

        return EligibilityResult(
            eligible=eligible,
            action_type=action_type,
            action_name=action_name,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            warnings=warnings,
            recommendations=recommendations,
            metadata={
                'org_type': org_type_upper,
                'country': country,
                'is_programme_country': is_programme_country,
                'has_eche': has_eche,
                'is_coordinator': is_coordinator,
            }
        )

    def get_eligible_actions(
        self,
        org_type: str,
        country: str,
        has_eche: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all Erasmus+ actions an organization is eligible for.

        Args:
            org_type: Organization type
            country: Country name
            has_eche: Whether organization has ECHE

        Returns:
            List of eligible actions with details
        """
        eligible_actions = []

        for action_type in self.ACTION_RULES.keys():
            result = self.check_eligibility(
                org_type=org_type,
                country=country,
                action_type=action_type,
                has_eche=has_eche,
                is_coordinator=True,
            )

            if result.eligible:
                eligible_actions.append({
                    'action_type': action_type,
                    'action_name': result.action_name,
                    'warnings': result.warnings,
                    'notes': result.recommendations,
                })

        return eligible_actions

    def get_programme_countries(self) -> List[str]:
        """Get list of all Programme Countries."""
        return self.PROGRAMME_COUNTRIES.copy()

    def get_partner_countries(self) -> Dict[str, List[str]]:
        """Get Partner Countries by region."""
        return self.PARTNER_REGIONS.copy()


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
    # Other Programme Countries
    'North Macedonia': 'MK', 'Serbia': 'RS', 'Turkey': 'TR',
    # Common variations
    'UK': 'GB', 'United Kingdom': 'GB', 'Switzerland': 'CH',
}


def _try_graph_eligibility_check(
    country: str,
    action_type: Optional[str] = None,
    role: str = "coordinator"
) -> Optional[Dict[str, Any]]:
    """
    Try to use Neo4j graph for eligibility check.

    Returns None if Neo4j data not available, otherwise returns graph results.
    """
    try:
        from app.services.data_intelligence.graph_service import GraphSearchService
        graph = GraphSearchService()

        # Convert country name to ISO code
        country_code = COUNTRY_NAME_TO_ISO.get(country, country.upper()[:2])

        if action_type:
            # Check specific action eligibility
            result = graph.get_erasmus_action_details(action_type)
            if result:
                country_result = graph.check_erasmus_country_eligibility(country_code, action_type)
                return {
                    'action_details': result,
                    'country_eligibility': country_result,
                    'source': 'neo4j_graph'
                }
        else:
            # Get all eligible actions for this country
            actions = graph.find_eligible_erasmus_actions(country_code, role=role)
            if actions:
                return {
                    'eligible_actions': actions,
                    'country_code': country_code,
                    'source': 'neo4j_graph'
                }

    except Exception as e:
        logger.debug(f"Neo4j eligibility check not available: {e}")

    return None


# Tool execution function for ToolAwareAgent
async def check_erasmus_eligibility_execute(
    org_type: str,
    country: str,
    action_type: Optional[str] = None,
    has_eche: bool = False,
    is_coordinator: bool = True,
) -> Dict[str, Any]:
    """
    Check Erasmus+ eligibility for an organization.

    Uses Neo4j graph database when available for dynamic eligibility data,
    with fallback to hardcoded rules.

    Args:
        org_type: Organization type (HEI, SCHOOL, VET_PROVIDER, NGO, etc.)
        country: Country of the organization
        action_type: Specific action to check (or None for all actions)
        has_eche: Whether organization has ECHE (for HEIs)
        is_coordinator: Whether checking as coordinator

    Returns:
        Eligibility result with requirements and recommendations
    """
    tool = ErasmusEligibilityTool()
    source = 'hardcoded_rules'

    # Try Neo4j first for enriched data
    role = "coordinator" if is_coordinator else "participant"
    graph_result = _try_graph_eligibility_check(country, action_type, role)

    if action_type:
        # Check specific action
        result = tool.check_eligibility(
            org_type=org_type,
            country=country,
            action_type=action_type,
            has_eche=has_eche,
            is_coordinator=is_coordinator,
        )

        response = {
            'success': True,
            'result': result.to_dict(),
            'metadata': {
                'tool': 'check_erasmus_eligibility',
                'query_type': 'specific_action',
                'programme': 'erasmus_plus',
                'source': source,
            }
        }

        # Enrich with graph data if available
        if graph_result and 'action_details' in graph_result:
            action_details = graph_result['action_details']
            response['action_details'] = {
                'min_partners': action_details.get('requirements', {}).get('min_partners'),
                'min_countries': action_details.get('requirements', {}).get('min_countries'),
                'duration_months': action_details.get('duration'),
                'typical_budget': action_details.get('budget'),
                'sector': action_details.get('sector'),
            }
            response['country_eligibility'] = graph_result.get('country_eligibility')
            response['metadata']['source'] = 'hybrid_graph_rules'

        return response
    else:
        # Get all eligible actions
        eligible_actions = tool.get_eligible_actions(
            org_type=org_type,
            country=country,
            has_eche=has_eche,
        )

        response = {
            'success': True,
            'eligible_actions': eligible_actions,
            'total_eligible': len(eligible_actions),
            'metadata': {
                'tool': 'check_erasmus_eligibility',
                'query_type': 'all_actions',
                'org_type': org_type,
                'country': country,
                'programme': 'erasmus_plus',
                'source': source,
            }
        }

        # Enrich with graph data if available
        if graph_result and 'eligible_actions' in graph_result:
            graph_actions = graph_result['eligible_actions']
            # Add budget and duration info from graph
            action_map = {a['code']: a for a in graph_actions}
            for action in response['eligible_actions']:
                code = action['action_type']
                if code in action_map:
                    graph_action = action_map[code]
                    action['typical_budget'] = graph_action.get('typical_budget')
                    action['requirements'] = graph_action.get('requirements')
            response['metadata']['source'] = 'hybrid_graph_rules'

        return response
