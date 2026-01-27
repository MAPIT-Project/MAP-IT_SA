"""
EU4Health Eligibility Checker Tool

Checks organization eligibility for EU4Health actions based on:
- Organization type (healthcare provider, research, NGO, etc.)
- Country (EU Member States + associated countries)
- Action type (Action Grants, Joint Actions, etc.)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    """Result of eligibility check."""

    eligible: bool
    action_type: str
    action_name: str
    requirements_met: list[str]
    requirements_missing: list[str]
    warnings: list[str]
    recommendations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "action_type": self.action_type,
            "action_name": self.action_name,
            "requirements_met": self.requirements_met,
            "requirements_missing": self.requirements_missing,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class EU4HealthEligibilityTool:
    """Tool for checking EU4Health eligibility."""

    # EU Member States (27)
    EU_MEMBER_STATES = [
        "Austria",
        "Belgium",
        "Bulgaria",
        "Croatia",
        "Cyprus",
        "Czech Republic",
        "Denmark",
        "Estonia",
        "Finland",
        "France",
        "Germany",
        "Greece",
        "Hungary",
        "Ireland",
        "Italy",
        "Latvia",
        "Lithuania",
        "Luxembourg",
        "Malta",
        "Netherlands",
        "Poland",
        "Portugal",
        "Romania",
        "Slovakia",
        "Slovenia",
        "Spain",
        "Sweden",
    ]

    # EEA Countries (full participation)
    EEA_COUNTRIES = ["Iceland", "Norway"]

    # Associated Countries for EU4Health
    ASSOCIATED_COUNTRIES = [
        "Ukraine",
        "Moldova",
        "Montenegro",
        "Bosnia and Herzegovina",
        "Serbia",
    ]

    # All participating countries
    PARTICIPATING_COUNTRIES = EU_MEMBER_STATES + EEA_COUNTRIES + ASSOCIATED_COUNTRIES

    # Organization types
    ORG_TYPES = {
        "HEALTHCARE_PROVIDER": "Hospital/Healthcare Provider",
        "RESEARCH": "Research Institution",
        "UNIVERSITY": "University/Higher Education",
        "PUBLIC_AUTHORITY": "Public Authority/Government Body",
        "NGO": "Non-Governmental Organization (health sector)",
        "PATIENT_ORG": "Patient Organization",
        "PROFESSIONAL_ORG": "Healthcare Professional Organization",
        "ENTERPRISE": "Private Enterprise (health sector)",
        "SME": "Small/Medium Enterprise (health sector)",
        "INTERNATIONAL_ORG": "International Organization",
    }

    # EU4Health strands (thematic areas)
    STRANDS = {
        "CRISIS": {
            "name": "Crisis Preparedness",
            "description": "Health security, emergency preparedness, medical countermeasures",
        },
        "PREVENTION": {
            "name": "Disease Prevention",
            "description": "Cancer, NCDs, infectious diseases, health promotion",
        },
        "HEALTH_SYSTEMS": {
            "name": "Health Systems",
            "description": "Healthcare workforce, digital health, HTA, medicines",
        },
        "DIGITAL": {
            "name": "Digital Health",
            "description": "EHDS, eHealth infrastructure, AI in health",
        },
    }

    # Action type rules
    ACTION_RULES = {
        "AG": {
            "name": "Action Grant",
            "description": "Project grants for health initiatives (60-80% EU co-financing)",
            "org_types": [
                "HEALTHCARE_PROVIDER",
                "RESEARCH",
                "UNIVERSITY",
                "PUBLIC_AUTHORITY",
                "NGO",
                "PATIENT_ORG",
                "PROFESSIONAL_ORG",
                "ENTERPRISE",
                "SME",
            ],
            "country_rule": "participating",
            "co_financing_rate": "60-80%",
            "min_partners": 1,
            "notes": "Most common EU4Health grant type. Open to wide range of entities.",
        },
        "PJ": {
            "name": "Project Grant",
            "description": "Project grants (same as Action Grant)",
            "org_types": [
                "HEALTHCARE_PROVIDER",
                "RESEARCH",
                "UNIVERSITY",
                "PUBLIC_AUTHORITY",
                "NGO",
                "PATIENT_ORG",
                "PROFESSIONAL_ORG",
                "ENTERPRISE",
                "SME",
            ],
            "country_rule": "participating",
            "co_financing_rate": "60-80%",
            "min_partners": 1,
            "notes": "Equivalent to Action Grant. Check specific call for requirements.",
        },
        "JA": {
            "name": "Joint Action",
            "description": "Actions with Member State authorities (60% EU co-financing)",
            "org_types": ["PUBLIC_AUTHORITY"],
            "country_rule": "member_states_only",
            "co_financing_rate": "60%",
            "min_partners": 3,
            "min_countries": 3,
            "notes": "Only Member State authorities can be beneficiaries. Affiliated entities can participate.",
        },
        "DG": {
            "name": "Direct Grant",
            "description": "Grants to specific entities without call for proposals",
            "org_types": ["PUBLIC_AUTHORITY", "INTERNATIONAL_ORG"],
            "country_rule": "participating",
            "co_financing_rate": "varies",
            "min_partners": 1,
            "notes": "Awarded to specific entities mentioned in Work Programme. Not open for applications.",
        },
        "OG": {
            "name": "Operating Grant",
            "description": "Grants for NGO operating costs (60% EU co-financing)",
            "org_types": ["NGO", "PATIENT_ORG", "PROFESSIONAL_ORG"],
            "country_rule": "participating",
            "co_financing_rate": "60%",
            "min_partners": 1,
            "notes": "For EU-level health NGOs. Requires Framework Partnership Agreement.",
        },
        "FPA": {
            "name": "Framework Partnership Agreement",
            "description": "Long-term partnership with Commission",
            "org_types": ["NGO", "PATIENT_ORG", "PROFESSIONAL_ORG"],
            "country_rule": "participating",
            "co_financing_rate": "varies",
            "min_partners": 1,
            "notes": "Multi-year agreement for recurring grants. Typically for umbrella organizations.",
        },
        "PROC": {
            "name": "Procurement",
            "description": "Public procurement contracts (service, supply, works)",
            "org_types": [
                "HEALTHCARE_PROVIDER",
                "RESEARCH",
                "UNIVERSITY",
                "PUBLIC_AUTHORITY",
                "ENTERPRISE",
                "SME",
                "INTERNATIONAL_ORG",
            ],
            "country_rule": "participating",
            "co_financing_rate": "100% (contract)",
            "min_partners": 1,
            "notes": "Tendering procedure, not a grant. Full payment for deliverables.",
        },
    }

    def check_eligibility(
        self,
        org_type: str,
        country: str,
        action_type: str,
        strand: str | None = None,
    ) -> EligibilityResult:
        """
        Check if an organization is eligible for an EU4Health action.

        Args:
            org_type: Organization type
            country: Country of the organization
            action_type: EU4Health action type (AG, JA, DG, OG, PROC)
            strand: Optional strand filter (CRISIS, PREVENTION, etc.)

        Returns:
            EligibilityResult with detailed eligibility information
        """
        requirements_met = []
        requirements_missing = []
        warnings = []
        recommendations = []

        # Normalize action type
        action_type = action_type.upper().replace("-", "").replace("_", "")

        # Handle common patterns
        if action_type.startswith("EU4H"):
            # Extract from topic code like EU4H-2024-PJ-03-1
            parts = action_type.split("-")
            if len(parts) >= 3:
                action_type = parts[2]

        # Get action rules
        rules = self.ACTION_RULES.get(action_type)
        if not rules:
            return EligibilityResult(
                eligible=False,
                action_type=action_type,
                action_name="Unknown Action",
                requirements_met=[],
                requirements_missing=[f"Unknown action type: {action_type}"],
                warnings=[],
                recommendations=[
                    "Valid action types: AG (Action Grant), JA (Joint Action), "
                    "DG (Direct Grant), OG (Operating Grant), PROC (Procurement)"
                ],
                metadata={"error": "unknown_action"},
            )

        action_name = rules["name"]

        # Check 1: Organization type
        org_type_upper = org_type.upper().replace(" ", "_")
        if org_type_upper in rules["org_types"]:
            requirements_met.append(
                f'Organization type "{self.ORG_TYPES.get(org_type_upper, org_type)}" is eligible'
            )
        else:
            eligible_types = [self.ORG_TYPES.get(t, t) for t in rules["org_types"]]
            requirements_missing.append(
                f"Organization type not eligible for {action_name}. "
                f"Eligible types: {', '.join(eligible_types)}"
            )

        # Check 2: Country eligibility
        is_participating = country in self.PARTICIPATING_COUNTRIES
        is_eu_member = country in self.EU_MEMBER_STATES
        is_associated = country in self.ASSOCIATED_COUNTRIES

        country_rule = rules["country_rule"]

        if country_rule == "member_states_only":
            if is_eu_member:
                requirements_met.append(f"{country} is an EU Member State")
            else:
                requirements_missing.append(
                    f"{country} is not an EU Member State. "
                    f"Only EU Member State authorities can participate in Joint Actions."
                )
        elif country_rule == "participating":
            if is_participating:
                requirements_met.append(f"{country} is a participating country")
                if is_associated:
                    warnings.append(
                        f"{country} is an associated country. Check specific call for any restrictions."
                    )
            else:
                requirements_missing.append(
                    f"{country} is not an EU4Health participating country. "
                    f"Eligible: EU Member States, Iceland, Norway, Ukraine, Moldova, Montenegro, "
                    f"Bosnia and Herzegovina, Serbia."
                )

        # Add co-financing information
        if rules.get("co_financing_rate"):
            recommendations.append(f"EU co-financing rate: {rules['co_financing_rate']}")

        # Add consortium requirements
        if rules.get("min_partners"):
            if rules["min_partners"] > 1:
                recommendations.append(
                    f"Minimum {rules['min_partners']} organizations required in consortium"
                )
        if rules.get("min_countries"):
            recommendations.append(
                f"Partners must be from at least {rules['min_countries']} different countries"
            )

        # Add strand-specific notes
        if strand and strand.upper() in self.STRANDS:
            strand_info = self.STRANDS[strand.upper()]
            recommendations.append(f"{strand_info['name']}: {strand_info['description']}")

        # Add action-specific notes
        if rules.get("notes"):
            recommendations.append(rules["notes"])

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
                "org_type": org_type_upper,
                "country": country,
                "is_eu_member": is_eu_member,
                "is_associated": is_associated,
                "strand": strand,
                "co_financing": rules.get("co_financing_rate"),
            },
        )

    def get_eligible_actions(
        self,
        org_type: str,
        country: str,
    ) -> list[dict[str, Any]]:
        """
        Get all EU4Health actions an organization is eligible for.

        Args:
            org_type: Organization type
            country: Country name

        Returns:
            List of eligible actions with details
        """
        eligible_actions = []

        for action_type in self.ACTION_RULES.keys():
            result = self.check_eligibility(
                org_type=org_type,
                country=country,
                action_type=action_type,
            )

            if result.eligible:
                rules = self.ACTION_RULES[action_type]
                eligible_actions.append(
                    {
                        "action_type": action_type,
                        "action_name": result.action_name,
                        "description": rules.get("description"),
                        "co_financing": rules.get("co_financing_rate"),
                        "warnings": result.warnings,
                        "notes": result.recommendations,
                    }
                )

        return eligible_actions

    def get_participating_countries(self) -> dict[str, list[str]]:
        """Get participating countries by category."""
        return {
            "eu_member_states": self.EU_MEMBER_STATES.copy(),
            "eea": self.EEA_COUNTRIES.copy(),
            "associated": self.ASSOCIATED_COUNTRIES.copy(),
        }

    def get_strands(self) -> dict[str, dict]:
        """Get EU4Health strands."""
        return self.STRANDS.copy()


# Country name to ISO code mapping
COUNTRY_NAME_TO_ISO = {
    "Austria": "AT",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Denmark": "DK",
    "Estonia": "EE",
    "Finland": "FI",
    "France": "FR",
    "Germany": "DE",
    "Greece": "GR",
    "Hungary": "HU",
    "Ireland": "IE",
    "Italy": "IT",
    "Latvia": "LV",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Malta": "MT",
    "Netherlands": "NL",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Spain": "ES",
    "Sweden": "SE",
    "Iceland": "IS",
    "Norway": "NO",
    "Ukraine": "UA",
    "Moldova": "MD",
    "Montenegro": "ME",
    "Bosnia and Herzegovina": "BA",
    "Serbia": "RS",
}


async def check_eu4health_eligibility_execute(
    org_type: str,
    country: str,
    action_type: str | None = None,
    strand: str | None = None,
) -> dict[str, Any]:
    """
    Check EU4Health eligibility for an organization.

    Args:
        org_type: Organization type (HEALTHCARE_PROVIDER, RESEARCH, NGO, etc.)
        country: Country of the organization
        action_type: Specific action to check (AG, JA, OG, etc.) or None for all
        strand: Optional strand filter (CRISIS, PREVENTION, HEALTH_SYSTEMS, DIGITAL)

    Returns:
        Eligibility result with requirements and recommendations
    """
    tool = EU4HealthEligibilityTool()

    if action_type:
        # Check specific action
        result = tool.check_eligibility(
            org_type=org_type,
            country=country,
            action_type=action_type,
            strand=strand,
        )

        return {
            "success": True,
            "result": result.to_dict(),
            "metadata": {
                "tool": "check_eu4health_eligibility",
                "query_type": "specific_action",
                "programme": "eu4health",
                "implementing_agency": "HaDEA",
            },
        }
    else:
        # Get all eligible actions
        eligible_actions = tool.get_eligible_actions(
            org_type=org_type,
            country=country,
        )

        return {
            "success": True,
            "eligible_actions": eligible_actions,
            "total_eligible": len(eligible_actions),
            "participating_countries": tool.get_participating_countries(),
            "strands": tool.get_strands(),
            "metadata": {
                "tool": "check_eu4health_eligibility",
                "query_type": "all_actions",
                "org_type": org_type,
                "country": country,
                "programme": "eu4health",
                "implementing_agency": "HaDEA",
            },
        }
