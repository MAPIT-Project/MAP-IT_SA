"""
LIFE Programme Eligibility Checker Tool

Checks organization eligibility for LIFE Programme actions based on:
- Organization type (public authority, NGO, SME, etc.)
- Country (EU Member States + EEA + associated countries)
- Sub-programme (Nature, Circular Economy, Climate, Clean Energy)
- Project type (SAP, SIP, SNAP, etc.)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    """Result of eligibility check."""

    eligible: bool
    subprogramme: str
    subprogramme_name: str
    requirements_met: list[str]
    requirements_missing: list[str]
    warnings: list[str]
    recommendations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "subprogramme": self.subprogramme,
            "subprogramme_name": self.subprogramme_name,
            "requirements_met": self.requirements_met,
            "requirements_missing": self.requirements_missing,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class LIFEEligibilityTool:
    """Tool for checking LIFE Programme eligibility."""

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

    # EEA Countries (full participation in LIFE)
    EEA_COUNTRIES = ["Iceland", "Liechtenstein", "Norway"]

    # Associated Countries for LIFE (Overseas Countries and Territories + others)
    ASSOCIATED_COUNTRIES = [
        "Ukraine",
        "Moldova",
        "Montenegro",
        "North Macedonia",
        "Serbia",
        "Albania",
        "Kosovo",
        "Türkiye",
        "Bosnia and Herzegovina",
    ]

    # All participating countries
    PARTICIPATING_COUNTRIES = EU_MEMBER_STATES + EEA_COUNTRIES + ASSOCIATED_COUNTRIES

    # Organization types
    ORG_TYPES = {
        "PUBLIC_AUTHORITY": "Public Authority/Government Body",
        "LOCAL_AUTHORITY": "Local/Regional Authority",
        "NGO": "Non-Governmental Organization",
        "ENVIRONMENTAL_NGO": "Environmental NGO",
        "RESEARCH": "Research Institution",
        "UNIVERSITY": "University/Higher Education",
        "SME": "Small/Medium Enterprise",
        "LARGE_ENTERPRISE": "Large Enterprise",
        "INTERNATIONAL_ORG": "International Organization",
        "ASSOCIATION": "Association/Network",
        "FOUNDATION": "Foundation",
        "PARK_AUTHORITY": "Nature Park/Protected Area Authority",
    }

    # LIFE Sub-programmes
    SUBPROGRAMMES = {
        "NAT": {
            "name": "Nature and Biodiversity",
            "description": "Conservation of nature, Natura 2000, biodiversity",
            "funding_rate": 75,
            "funding_rate_notes": "Up to 75% for priority species/habitats",
            "org_types": [
                "PUBLIC_AUTHORITY",
                "LOCAL_AUTHORITY",
                "NGO",
                "ENVIRONMENTAL_NGO",
                "RESEARCH",
                "UNIVERSITY",
                "SME",
                "PARK_AUTHORITY",
                "ASSOCIATION",
                "FOUNDATION",
            ],
            "priorities": [
                "Natura 2000",
                "Species conservation",
                "Habitat restoration",
                "Invasive species",
                "Green infrastructure",
            ],
        },
        "ENV": {
            "name": "Circular Economy and Quality of Life",
            "description": "Waste, water, air, soil, chemicals, noise, resource efficiency",
            "funding_rate": 60,
            "funding_rate_notes": "Standard 60% EU co-financing",
            "org_types": [
                "PUBLIC_AUTHORITY",
                "LOCAL_AUTHORITY",
                "NGO",
                "RESEARCH",
                "UNIVERSITY",
                "SME",
                "LARGE_ENTERPRISE",
                "ASSOCIATION",
            ],
            "priorities": [
                "Circular economy",
                "Waste prevention",
                "Water management",
                "Air quality",
                "Soil protection",
                "Chemicals",
            ],
        },
        "CCA": {
            "name": "Climate Change Mitigation and Adaptation",
            "description": "Reducing greenhouse gas emissions and climate adaptation",
            "funding_rate": 60,
            "funding_rate_notes": "Standard 60% EU co-financing",
            "org_types": [
                "PUBLIC_AUTHORITY",
                "LOCAL_AUTHORITY",
                "NGO",
                "RESEARCH",
                "UNIVERSITY",
                "SME",
                "LARGE_ENTERPRISE",
                "ASSOCIATION",
            ],
            "priorities": [
                "GHG reduction",
                "Energy efficiency",
                "Climate adaptation",
                "Urban adaptation",
                "Agriculture adaptation",
            ],
        },
        "CET": {
            "name": "Clean Energy Transition",
            "description": "Supporting the transition to clean, renewable energy",
            "funding_rate": 95,
            "funding_rate_notes": "Up to 95% EU co-financing (coordination & support)",
            "org_types": [
                "PUBLIC_AUTHORITY",
                "LOCAL_AUTHORITY",
                "NGO",
                "RESEARCH",
                "UNIVERSITY",
                "SME",
                "ASSOCIATION",
                "FOUNDATION",
            ],
            "priorities": [
                "Renewable energy",
                "Energy efficiency",
                "Energy poverty",
                "Building renovation",
                "Local energy communities",
            ],
        },
    }

    # Project type rules
    PROJECT_TYPES = {
        "SAP": {
            "name": "Standard Action Projects",
            "description": "Best practice, demonstration, pilot, information projects",
            "min_partners": 1,
            "typical_budget": "1-5 million EUR",
            "typical_duration": "3-5 years",
            "all_subprogrammes": True,
        },
        "SIP": {
            "name": "Strategic Integrated Projects",
            "description": "Large-scale implementation of environmental/climate plans",
            "min_partners": 3,
            "min_countries": 2,
            "typical_budget": "10-30 million EUR",
            "typical_duration": "5-10 years",
            "subprogrammes": ["ENV", "CCA"],
            "notes": "Requires alignment with approved national/regional strategies",
        },
        "SNAP": {
            "name": "Strategic Nature Projects",
            "description": "Large-scale implementation for nature/biodiversity",
            "min_partners": 3,
            "min_countries": 2,
            "typical_budget": "10-30 million EUR",
            "typical_duration": "5-10 years",
            "subprogrammes": ["NAT"],
            "notes": "Focus on Prioritised Action Frameworks",
        },
        "TA": {
            "name": "Technical Assistance",
            "description": "Preparation of SIP/SNAP proposals",
            "min_partners": 1,
            "typical_budget": "Up to 1 million EUR",
            "typical_duration": "1-2 years",
            "all_subprogrammes": True,
        },
        "OG": {
            "name": "Operating Grants",
            "description": "Support for NGO operations at EU level",
            "min_partners": 1,
            "org_types": ["NGO", "ENVIRONMENTAL_NGO", "ASSOCIATION"],
            "notes": "Requires Framework Partnership Agreement",
        },
    }

    def check_eligibility(
        self,
        org_type: str,
        country: str,
        subprogramme: str,
        project_type: str | None = None,
    ) -> EligibilityResult:
        """
        Check if an organization is eligible for a LIFE sub-programme.

        Args:
            org_type: Organization type
            country: Country of the organization
            subprogramme: LIFE sub-programme (NAT, ENV, CCA, CET)
            project_type: Optional project type filter (SAP, SIP, SNAP, etc.)

        Returns:
            EligibilityResult with detailed eligibility information
        """
        requirements_met = []
        requirements_missing = []
        warnings = []
        recommendations = []

        # Normalize sub-programme
        subprogramme = subprogramme.upper().replace(" ", "_").replace("-", "_")

        # Handle common aliases
        subprog_aliases = {
            "NATURE": "NAT",
            "BIODIVERSITY": "NAT",
            "NATURE_BIODIVERSITY": "NAT",
            "CIRCULAR": "ENV",
            "CIRCULAR_ECONOMY": "ENV",
            "ENVIRONMENT": "ENV",
            "CLIMATE": "CCA",
            "CLIMATE_ACTION": "CCA",
            "CLIMATE_CHANGE": "CCA",
            "ENERGY": "CET",
            "CLEAN_ENERGY": "CET",
            "ENERGY_TRANSITION": "CET",
        }
        subprogramme = subprog_aliases.get(subprogramme, subprogramme)

        # Get sub-programme info
        subprog_info = self.SUBPROGRAMMES.get(subprogramme)

        if not subprog_info:
            return EligibilityResult(
                eligible=False,
                subprogramme=subprogramme,
                subprogramme_name="Unknown Sub-programme",
                requirements_met=[],
                requirements_missing=[f"Unknown sub-programme: {subprogramme}"],
                warnings=[],
                recommendations=[
                    "Valid sub-programmes: NAT (Nature), ENV (Circular Economy), "
                    "CCA (Climate), CET (Clean Energy)"
                ],
                metadata={"error": "unknown_subprogramme"},
            )

        subprogramme_name = subprog_info["name"]

        # Check 1: Organization type
        org_type_upper = org_type.upper().replace(" ", "_").replace("-", "_")

        # Handle aliases
        org_aliases = {
            "SMALL_MEDIUM_ENTERPRISE": "SME",
            "GOVERNMENT": "PUBLIC_AUTHORITY",
            "PUBLIC_BODY": "PUBLIC_AUTHORITY",
            "MUNICIPALITY": "LOCAL_AUTHORITY",
            "CITY": "LOCAL_AUTHORITY",
            "REGION": "LOCAL_AUTHORITY",
            "HIGHER_EDUCATION": "UNIVERSITY",
            "NATURE_PARK": "PARK_AUTHORITY",
        }
        org_type_upper = org_aliases.get(org_type_upper, org_type_upper)

        if org_type_upper in subprog_info["org_types"]:
            requirements_met.append(
                f'Organization type "{self.ORG_TYPES.get(org_type_upper, org_type)}" is eligible'
            )
        else:
            eligible_types = [self.ORG_TYPES.get(t, t) for t in subprog_info["org_types"]]
            requirements_missing.append(
                f"Organization type not typically eligible for {subprogramme_name}. "
                f"Eligible types: {', '.join(eligible_types[:5])}..."
            )

        # Check 2: Country eligibility
        is_participating = country in self.PARTICIPATING_COUNTRIES
        is_eu_member = country in self.EU_MEMBER_STATES
        is_eea = country in self.EEA_COUNTRIES
        is_associated = country in self.ASSOCIATED_COUNTRIES

        if is_participating:
            requirements_met.append(f"{country} is a participating country")
            if is_associated:
                warnings.append(
                    f"{country} is an associated country. Check specific call for any restrictions."
                )
        else:
            requirements_missing.append(
                f"{country} is not a LIFE participating country. "
                f"Eligible: EU Member States, EEA countries, and some associated countries."
            )

        # Add funding information
        recommendations.append(f"EU co-financing rate: {subprog_info['funding_rate']}%")
        if subprog_info.get("funding_rate_notes"):
            recommendations.append(subprog_info["funding_rate_notes"])

        # Add priority areas
        if subprog_info.get("priorities"):
            recommendations.append(f"Priority areas: {', '.join(subprog_info['priorities'][:4])}")

        # Project type specific checks
        if project_type:
            project_type_upper = project_type.upper()
            ptype_info = self.PROJECT_TYPES.get(project_type_upper)
            if ptype_info:
                recommendations.append(f"Project type: {ptype_info['name']}")
                if ptype_info.get("typical_budget"):
                    recommendations.append(f"Typical budget: {ptype_info['typical_budget']}")
                if ptype_info.get("min_partners", 1) > 1:
                    recommendations.append(f"Minimum partners: {ptype_info['min_partners']}")
                if ptype_info.get("notes"):
                    recommendations.append(ptype_info["notes"])

        # Sub-programme specific notes
        if subprogramme == "NAT":
            recommendations.append(
                "Nature projects should align with Natura 2000 or national biodiversity strategies"
            )
        elif subprogramme == "CET":
            recommendations.append(
                "Clean Energy Transition focuses on policy, capacity building, not technology development"
            )

        # Determine overall eligibility
        eligible = len(requirements_missing) == 0

        return EligibilityResult(
            eligible=eligible,
            subprogramme=subprogramme,
            subprogramme_name=subprogramme_name,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            warnings=warnings,
            recommendations=recommendations,
            metadata={
                "org_type": org_type_upper,
                "country": country,
                "is_eu_member": is_eu_member,
                "is_eea": is_eea,
                "is_associated": is_associated,
                "funding_rate": subprog_info["funding_rate"],
                "implementing_agency": "CINEA",
            },
        )

    def get_eligible_subprogrammes(
        self,
        org_type: str,
        country: str,
    ) -> list[dict[str, Any]]:
        """
        Get all LIFE sub-programmes an organization is eligible for.

        Args:
            org_type: Organization type
            country: Country name

        Returns:
            List of eligible sub-programmes with details
        """
        eligible_subprogs = []

        for subprog_code in self.SUBPROGRAMMES.keys():
            result = self.check_eligibility(
                org_type=org_type,
                country=country,
                subprogramme=subprog_code,
            )

            if result.eligible:
                subprog_info = self.SUBPROGRAMMES[subprog_code]
                eligible_subprogs.append(
                    {
                        "subprogramme": subprog_code,
                        "subprogramme_name": result.subprogramme_name,
                        "description": subprog_info.get("description"),
                        "funding_rate": subprog_info.get("funding_rate"),
                        "priorities": subprog_info.get("priorities", []),
                        "warnings": result.warnings,
                        "notes": result.recommendations,
                    }
                )

        return eligible_subprogs

    def get_participating_countries(self) -> dict[str, list[str]]:
        """Get participating countries by category."""
        return {
            "eu_member_states": self.EU_MEMBER_STATES.copy(),
            "eea": self.EEA_COUNTRIES.copy(),
            "associated": self.ASSOCIATED_COUNTRIES.copy(),
        }

    def get_subprogrammes(self) -> dict[str, dict]:
        """Get LIFE sub-programmes."""
        return self.SUBPROGRAMMES.copy()

    def get_project_types(self) -> dict[str, dict]:
        """Get LIFE project types."""
        return self.PROJECT_TYPES.copy()


async def check_life_eligibility_execute(
    org_type: str,
    country: str,
    subprogramme: str | None = None,
    project_type: str | None = None,
) -> dict[str, Any]:
    """
    Check LIFE eligibility for an organization.

    Args:
        org_type: Organization type (PUBLIC_AUTHORITY, NGO, SME, etc.)
        country: Country of the organization
        subprogramme: Specific sub-programme to check (NAT, ENV, CCA, CET) or None for all
        project_type: Optional project type filter (SAP, SIP, SNAP, etc.)

    Returns:
        Eligibility result with requirements and recommendations
    """
    tool = LIFEEligibilityTool()

    if subprogramme:
        # Check specific sub-programme
        result = tool.check_eligibility(
            org_type=org_type,
            country=country,
            subprogramme=subprogramme,
            project_type=project_type,
        )

        return {
            "success": True,
            "result": result.to_dict(),
            "metadata": {
                "tool": "check_life_eligibility",
                "query_type": "specific_subprogramme",
                "programme": "life",
                "implementing_agency": "CINEA",
                "programme_budget": "€5.432 billion (2021-2027)",
            },
        }
    else:
        # Get all eligible sub-programmes
        eligible_subprogs = tool.get_eligible_subprogrammes(
            org_type=org_type,
            country=country,
        )

        return {
            "success": True,
            "eligible_subprogrammes": eligible_subprogs,
            "total_eligible": len(eligible_subprogs),
            "participating_countries": tool.get_participating_countries(),
            "subprogrammes": tool.get_subprogrammes(),
            "project_types": tool.get_project_types(),
            "metadata": {
                "tool": "check_life_eligibility",
                "query_type": "all_subprogrammes",
                "org_type": org_type,
                "country": country,
                "programme": "life",
                "implementing_agency": "CINEA",
                "programme_budget": "€5.432 billion (2021-2027)",
            },
        }
