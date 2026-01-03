# Phase 3: Erasmus+ Specific Tools

## Objective

Create Erasmus+-specific tools that leverage the unique characteristics of the programme:
- Lump sum/unit cost funding model
- ECHE (Erasmus Charter for Higher Education) requirements
- Sector-based eligibility (HED, VET, SCH, ADU, YOU, SPORT)
- Programme vs Partner Country rules
- Key Action structure (KA1, KA2, KA3, JMO, Sport)

## Priority: MEDIUM

These tools enhance the user experience but require Phase 1 (documents) and Phase 2 (calls) to be completed first.

## Current State

### What Exists
- Tool infrastructure: `app/services/tools/` directory
- Tool registration pattern: `app/services/tools/__init__.py`
- ToolAwareAgent: `app/services/agents/tool_aware_agent.py`
- ErasmusPlusExtractor with action types, sectors, budget ranges: `app/services/call_extractors/erasmus_plus.py`

### What's Missing
- Erasmus+ eligibility checker tool
- Lump sum budget calculator tool
- Erasmus+ partner discovery tool
- Erasmus+ statistics tool

## Tools to Implement

### Tool 1: Erasmus+ Eligibility Checker

**Purpose**: Check if an organization is eligible for specific Erasmus+ actions based on type, country, and ECHE status.

**File**: `app/services/tools/erasmus_eligibility.py`

```python
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
        'JMO-MODULE': {
            'name': 'Jean Monnet Module',
            'org_types': ['HEI'],
            'requires_eche': True,  # In Programme Countries
            'country_rule': 'worldwide',
            'min_partners': 1,
            'notes': 'HEIs worldwide eligible; ECHE required in Programme Countries',
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
                recommendations=['Check valid action types: KA1-HED, KA2-COOP, JMO-MODULE, etc.'],
                metadata={'error': 'unknown_action'}
            )

        action_name = rules['name']

        # Check 1: Organization type
        if org_type in rules['org_types']:
            requirements_met.append(f'Organization type {org_type} is eligible')
        else:
            requirements_missing.append(
                f'Organization type {org_type} not eligible. '
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
        if org_type == 'HEI' and rules.get('requires_eche'):
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
                'org_type': org_type,
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

    if action_type:
        # Check specific action
        result = tool.check_eligibility(
            org_type=org_type,
            country=country,
            action_type=action_type,
            has_eche=has_eche,
            is_coordinator=is_coordinator,
        )
        return {
            'success': True,
            'result': result.to_dict(),
            'metadata': {
                'tool': 'check_erasmus_eligibility',
                'query_type': 'specific_action',
            }
        }
    else:
        # Get all eligible actions
        eligible_actions = tool.get_eligible_actions(
            org_type=org_type,
            country=country,
            has_eche=has_eche,
        )
        return {
            'success': True,
            'eligible_actions': eligible_actions,
            'total_eligible': len(eligible_actions),
            'metadata': {
                'tool': 'check_erasmus_eligibility',
                'query_type': 'all_actions',
                'org_type': org_type,
                'country': country,
            }
        }
```

### Tool 2: Lump Sum Budget Calculator

**Purpose**: Calculate Erasmus+ lump sum grants based on action type, activities, and participant numbers.

**File**: `app/services/tools/erasmus_budget_calculator.py`

```python
"""
Erasmus+ Lump Sum Budget Calculator

Calculates grants using Erasmus+ unit costs and lump sums:
- Mobility activities: unit costs per participant/day
- Project management: lump sums based on project size
- Travel costs: distance bands
- Special needs support: actual costs

Key difference from Horizon Europe:
- Erasmus+ uses predetermined unit costs and lump sums
- No actual cost reimbursement (except exceptional costs)
- Simplified financial management
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BudgetBreakdown:
    """Detailed budget breakdown."""
    travel: float = 0.0
    individual_support: float = 0.0
    organizational_support: float = 0.0
    project_management: float = 0.0
    transnational_meetings: float = 0.0
    intellectual_outputs: float = 0.0
    special_needs: float = 0.0
    exceptional_costs: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.travel +
            self.individual_support +
            self.organizational_support +
            self.project_management +
            self.transnational_meetings +
            self.intellectual_outputs +
            self.special_needs +
            self.exceptional_costs
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            'travel': self.travel,
            'individual_support': self.individual_support,
            'organizational_support': self.organizational_support,
            'project_management': self.project_management,
            'transnational_meetings': self.transnational_meetings,
            'intellectual_outputs': self.intellectual_outputs,
            'special_needs': self.special_needs,
            'exceptional_costs': self.exceptional_costs,
            'total': self.total,
        }


class ErasmusBudgetCalculator:
    """Calculator for Erasmus+ lump sum grants."""

    # Travel distance bands (EUR per participant, round trip)
    TRAVEL_BANDS = {
        '10-99km': 23,
        '100-499km': 180,
        '500-1999km': 275,
        '2000-2999km': 360,
        '3000-3999km': 530,
        '4000-7999km': 820,
        '8000+km': 1500,
        'green_travel_bonus': 50,  # Additional for sustainable travel
    }

    # Individual support daily rates (EUR per day)
    # Varies by country group and activity type
    INDIVIDUAL_SUPPORT = {
        'staff_mobility': {
            'group1': 180,  # Denmark, Ireland, Iceland, Luxembourg, etc.
            'group2': 160,  # Austria, Belgium, Germany, France, etc.
            'group3': 140,  # Cyprus, Greece, Malta, Portugal, etc.
        },
        'student_mobility': {
            'group1': 79,
            'group2': 79,
            'group3': 79,
            'top_up': 250,  # Monthly top-up for disadvantaged
        },
        'youth_mobility': {
            'participant_day': 58,
            'leader_day': 74,
        },
    }

    # Organizational support (EUR per participant)
    ORG_SUPPORT = {
        'higher_ed': 350,
        'vet': 350,
        'school': 100,
        'adult_ed': 100,
        'youth': 0,  # Included in activity costs
    }

    # Project management lump sums (KA2)
    PROJECT_MANAGEMENT = {
        'coordinator': 500,  # EUR per month
        'partner': 250,      # EUR per month
    }

    # Transnational meeting costs (EUR per participant)
    TRANSNATIONAL_MEETINGS = {
        'local': 100,     # Same country
        'abroad': 575,    # Different country
    }

    # Intellectual output daily rates (EUR per day)
    INTELLECTUAL_OUTPUTS = {
        'manager': 294,
        'researcher': 214,
        'technician': 162,
        'administrative': 131,
    }

    # Country groups for cost rates
    COUNTRY_GROUPS = {
        'group1': ['Denmark', 'Finland', 'Iceland', 'Ireland', 'Liechtenstein',
                   'Luxembourg', 'Norway', 'Sweden'],
        'group2': ['Austria', 'Belgium', 'Cyprus', 'France', 'Germany', 'Greece',
                   'Italy', 'Malta', 'Netherlands', 'Portugal', 'Spain'],
        'group3': ['Bulgaria', 'Croatia', 'Czech Republic', 'Estonia', 'Hungary',
                   'Latvia', 'Lithuania', 'North Macedonia', 'Poland', 'Romania',
                   'Serbia', 'Slovakia', 'Slovenia', 'Turkey'],
    }

    def calculate_mobility_budget(
        self,
        action_type: str,
        participants: int,
        duration_days: int,
        destination_country: str,
        origin_country: str,
        distance_band: str = '500-1999km',
        include_org_support: bool = True,
        green_travel: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculate budget for mobility activities (KA1).

        Args:
            action_type: Type of mobility (e.g., 'staff_mobility', 'student_mobility')
            participants: Number of participants
            duration_days: Duration in days
            destination_country: Country of destination
            origin_country: Origin country
            distance_band: Travel distance band
            include_org_support: Include organizational support
            green_travel: Whether using sustainable travel

        Returns:
            Budget breakdown with total
        """
        breakdown = BudgetBreakdown()

        # Get country group for rates
        dest_group = self._get_country_group(destination_country)

        # Travel costs
        travel_rate = self.TRAVEL_BANDS.get(distance_band, 275)
        if green_travel:
            travel_rate += self.TRAVEL_BANDS['green_travel_bonus']
        breakdown.travel = travel_rate * participants

        # Individual support
        if action_type in self.INDIVIDUAL_SUPPORT:
            rates = self.INDIVIDUAL_SUPPORT[action_type]
            if dest_group in rates:
                daily_rate = rates[dest_group]
            else:
                daily_rate = rates.get('participant_day', 79)
            breakdown.individual_support = daily_rate * duration_days * participants

        # Organizational support
        if include_org_support:
            sector = self._get_sector_from_action(action_type)
            org_rate = self.ORG_SUPPORT.get(sector, 100)
            breakdown.organizational_support = org_rate * participants

        return {
            'success': True,
            'breakdown': breakdown.to_dict(),
            'parameters': {
                'action_type': action_type,
                'participants': participants,
                'duration_days': duration_days,
                'destination_country': destination_country,
                'distance_band': distance_band,
            },
            'notes': [
                'Amounts based on Erasmus+ 2024 Programme Guide unit costs',
                'Green travel bonus applied' if green_travel else '',
                f'Destination country group: {dest_group}',
            ]
        }

    def calculate_partnership_budget(
        self,
        partnership_type: str,  # 'cooperation' or 'small_scale'
        num_partners: int,
        duration_months: int,
        transnational_meetings: int = 4,
        intellectual_outputs: int = 0,
        coordinator_country: str = 'Germany',
    ) -> Dict[str, Any]:
        """
        Calculate budget for KA2 partnership projects.

        Args:
            partnership_type: 'cooperation' (120-400k) or 'small_scale' (30-60k)
            num_partners: Number of partner organizations
            duration_months: Project duration in months
            transnational_meetings: Number of transnational meetings
            intellectual_outputs: Number of intellectual outputs
            coordinator_country: Country of coordinator

        Returns:
            Budget breakdown with total
        """
        breakdown = BudgetBreakdown()

        # Project management
        breakdown.project_management = (
            self.PROJECT_MANAGEMENT['coordinator'] * duration_months +
            self.PROJECT_MANAGEMENT['partner'] * duration_months * (num_partners - 1)
        )

        # Transnational meetings (estimate 3 participants per partner per meeting)
        participants_per_meeting = num_partners * 3
        breakdown.transnational_meetings = (
            self.TRANSNATIONAL_MEETINGS['abroad'] *
            participants_per_meeting *
            transnational_meetings
        )

        # Intellectual outputs (if any)
        if intellectual_outputs > 0:
            # Estimate: 20 researcher-days per output
            breakdown.intellectual_outputs = (
                self.INTELLECTUAL_OUTPUTS['researcher'] * 20 * intellectual_outputs
            )

        # Apply partnership type limits
        if partnership_type == 'small_scale':
            max_budget = 60000
            min_budget = 30000
        else:
            max_budget = 400000
            min_budget = 120000

        total = breakdown.total

        # Adjust if over/under limits
        if total > max_budget:
            scale = max_budget / total
            breakdown.project_management *= scale
            breakdown.transnational_meetings *= scale
            breakdown.intellectual_outputs *= scale
        elif total < min_budget:
            # Add exceptional costs buffer
            breakdown.exceptional_costs = min_budget - total

        return {
            'success': True,
            'breakdown': breakdown.to_dict(),
            'parameters': {
                'partnership_type': partnership_type,
                'num_partners': num_partners,
                'duration_months': duration_months,
                'transnational_meetings': transnational_meetings,
            },
            'budget_range': {
                'min': min_budget,
                'max': max_budget,
            },
            'notes': [
                f'{partnership_type.title()} Partnership budget range: {min_budget:,} - {max_budget:,}',
                'Erasmus+ uses simplified lump sum model',
                'Actual spending flexibility within budget categories',
            ]
        }

    def _get_country_group(self, country: str) -> str:
        """Get country group for cost rates."""
        for group, countries in self.COUNTRY_GROUPS.items():
            if country in countries:
                return group
        return 'group3'  # Default

    def _get_sector_from_action(self, action_type: str) -> str:
        """Map action type to sector."""
        if 'staff' in action_type or 'student' in action_type:
            return 'higher_ed'
        elif 'vet' in action_type:
            return 'vet'
        elif 'school' in action_type:
            return 'school'
        elif 'adult' in action_type:
            return 'adult_ed'
        elif 'youth' in action_type:
            return 'youth'
        return 'higher_ed'


# Tool execution function for ToolAwareAgent
async def calculate_erasmus_budget_execute(
    action_type: str,
    num_participants: int = 10,
    duration_days: int = 14,
    duration_months: int = 24,
    num_partners: int = 3,
    destination_country: str = 'Germany',
    origin_country: str = 'Spain',
    partnership_type: str = 'cooperation',
) -> Dict[str, Any]:
    """
    Calculate Erasmus+ lump sum budget.

    Args:
        action_type: 'mobility' or 'partnership'
        num_participants: Number of participants (for mobility)
        duration_days: Duration in days (for mobility)
        duration_months: Duration in months (for partnership)
        num_partners: Number of partners (for partnership)
        destination_country: Destination country
        origin_country: Origin country
        partnership_type: 'cooperation' or 'small_scale'

    Returns:
        Budget breakdown with recommendations
    """
    calculator = ErasmusBudgetCalculator()

    if action_type == 'mobility' or 'KA1' in action_type.upper():
        result = calculator.calculate_mobility_budget(
            action_type='staff_mobility',
            participants=num_participants,
            duration_days=duration_days,
            destination_country=destination_country,
            origin_country=origin_country,
        )
    else:
        result = calculator.calculate_partnership_budget(
            partnership_type=partnership_type,
            num_partners=num_partners,
            duration_months=duration_months,
            coordinator_country=destination_country,
        )

    result['metadata'] = {
        'tool': 'calculate_erasmus_budget',
        'funding_model': 'lump_sum',
        'programme': 'erasmus_plus',
    }

    return result
```

### Tool 3: Update Tool Registry

**File**: Update `app/services/tools/__init__.py`

```python
# Add to imports
from .erasmus_eligibility import (
    ErasmusEligibilityTool,
    check_erasmus_eligibility_execute,
)
from .erasmus_budget_calculator import (
    ErasmusBudgetCalculator,
    calculate_erasmus_budget_execute,
)

# Add to __all__
__all__ = [
    # ... existing exports ...
    # Erasmus+ tools
    'ErasmusEligibilityTool',
    'check_erasmus_eligibility_execute',
    'ErasmusBudgetCalculator',
    'calculate_erasmus_budget_execute',
]
```

### Tool 4: Register Tools in ToolAwareAgent

**File**: Update `app/services/agents/tool_aware_agent.py`

Add to the `_init_tools()` method (around line 614-1097):

```python
# Erasmus+ Eligibility Tool
self.tool_registry['check_erasmus_eligibility'] = {
    'name': 'check_erasmus_eligibility',
    'description': (
        'Check if an organization is eligible for Erasmus+ actions. '
        'Considers organization type, country, ECHE status, and Key Action requirements. '
        'Use for: eligibility questions, ECHE requirements, country rules.'
    ),
    'parameters': {
        'org_type': {
            'type': 'string',
            'description': 'Organization type: HEI, SCHOOL, VET_PROVIDER, NGO, YOUTH_ORG, SPORT_ORG',
            'required': True,
        },
        'country': {
            'type': 'string',
            'description': 'Country of the organization',
            'required': True,
        },
        'action_type': {
            'type': 'string',
            'description': 'Erasmus+ action: KA1-HED, KA2-COOP, KA2-SSP, JMO-MODULE, etc.',
            'required': False,
        },
        'has_eche': {
            'type': 'boolean',
            'description': 'Whether organization has ECHE (for HEIs)',
            'required': False,
            'default': False,
        },
    },
    'execute': check_erasmus_eligibility_execute,
}

# Erasmus+ Budget Calculator Tool
self.tool_registry['calculate_erasmus_budget'] = {
    'name': 'calculate_erasmus_budget',
    'description': (
        'Calculate Erasmus+ lump sum grants using official unit costs. '
        'Handles mobility (KA1) and partnership (KA2) budgets. '
        'Uses travel bands, daily rates, and organizational support rates.'
    ),
    'parameters': {
        'action_type': {
            'type': 'string',
            'description': 'Action type: mobility, partnership, KA1-HED, KA2-COOP',
            'required': True,
        },
        'num_participants': {
            'type': 'integer',
            'description': 'Number of participants (for mobility)',
            'required': False,
            'default': 10,
        },
        'num_partners': {
            'type': 'integer',
            'description': 'Number of partner organizations (for KA2)',
            'required': False,
            'default': 3,
        },
        'duration_days': {
            'type': 'integer',
            'description': 'Duration in days (for mobility)',
            'required': False,
            'default': 14,
        },
        'duration_months': {
            'type': 'integer',
            'description': 'Project duration in months (for KA2)',
            'required': False,
            'default': 24,
        },
        'destination_country': {
            'type': 'string',
            'description': 'Destination/coordinator country',
            'required': False,
            'default': 'Germany',
        },
    },
    'execute': calculate_erasmus_budget_execute,
}
```

Add to the `_execute_single_tool()` method (around line 2369-2437):

```python
elif tool_name == 'check_erasmus_eligibility':
    return await check_erasmus_eligibility_execute(**params)

elif tool_name == 'calculate_erasmus_budget':
    return await calculate_erasmus_budget_execute(**params)
```

## Validation

### Test 1: Eligibility Checker

```python
from app.services.tools.erasmus_eligibility import check_erasmus_eligibility_execute

# Test HEI eligibility
result = await check_erasmus_eligibility_execute(
    org_type='HEI',
    country='Germany',
    action_type='KA1-HED',
    has_eche=True
)
print(result)
# Expected: eligible=True, requirements_met includes ECHE

# Test without ECHE
result = await check_erasmus_eligibility_execute(
    org_type='HEI',
    country='Germany',
    action_type='KA1-HED',
    has_eche=False
)
print(result)
# Expected: eligible=False, requirements_missing includes ECHE
```

### Test 2: Budget Calculator

```python
from app.services.tools.erasmus_budget_calculator import calculate_erasmus_budget_execute

# Test mobility budget
result = await calculate_erasmus_budget_execute(
    action_type='mobility',
    num_participants=20,
    duration_days=10,
    destination_country='France',
    origin_country='Spain'
)
print(f"Mobility budget: {result['breakdown']['total']}")

# Test partnership budget
result = await calculate_erasmus_budget_execute(
    action_type='partnership',
    num_partners=5,
    duration_months=36,
    partnership_type='cooperation'
)
print(f"Partnership budget: {result['breakdown']['total']}")
```

### Test 3: API Integration

```bash
curl -X POST http://localhost:8000/api/v3/conversation/test/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Is a German university eligible for Erasmus+ KA2 Cooperation Partnership?"}'
```

## Success Criteria

1. Eligibility tool returns correct results for all action types
2. Budget calculator produces realistic estimates matching Programme Guide
3. Tools are discoverable by ToolAwareAgent
4. API queries correctly invoke Erasmus+ tools

## Estimated Effort

- Eligibility tool: 3-4 hours
- Budget calculator: 3-4 hours
- Tool registration: 1 hour
- Testing and validation: 2 hours

## Dependencies

- Phase 1 and Phase 2 completed (documents and calls in database)
- `app/services/agents/tool_aware_agent.py` accessible
- Erasmus+ Programme Guide 2024/2025 for accurate unit costs

## Next Phase

After completing Phase 3, proceed to **Phase 4: Document Templates** for ingesting application forms and templates.
