"""
Digital Europe Eligibility Checker Tool

Checks organization eligibility for Digital Europe Programme actions based on:
- Organization type (SME, research, public authority, EDIH, etc.)
- Country (EU Member States + EEA + associated countries)
- Specific Objective (HPC, AI, Cybersecurity, Skills, Deployment)
- Action type (grant, procurement, etc.)
"""

from dataclasses import dataclass, field
import logging
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    """Result of eligibility check."""

    eligible: bool
    objective: str
    objective_name: str
    requirements_met: list[str]
    requirements_missing: list[str]
    warnings: list[str]
    recommendations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "objective": self.objective,
            "objective_name": self.objective_name,
            "requirements_met": self.requirements_met,
            "requirements_missing": self.requirements_missing,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class DigitalEuropeEligibilityTool:
    """Tool for checking Digital Europe Programme eligibility."""

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
    EEA_COUNTRIES = ["Iceland", "Liechtenstein", "Norway"]

    # Associated Countries for Digital Europe
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

    # Partially Associated (specific objectives only)
    PARTIALLY_ASSOCIATED = {
        "Switzerland": ["AI", "HPC"],  # Switzerland participates in AI and HPC
    }

    # All participating countries (full participation)
    PARTICIPATING_COUNTRIES = EU_MEMBER_STATES + EEA_COUNTRIES + ASSOCIATED_COUNTRIES

    # Organization types
    ORG_TYPES = {
        "SME": "Small/Medium Enterprise",
        "STARTUP": "Startup/Scaleup",
        "LARGE_ENTERPRISE": "Large Enterprise",
        "RESEARCH": "Research Institution",
        "UNIVERSITY": "University/Higher Education",
        "PUBLIC_AUTHORITY": "Public Authority/Government Body",
        "EDIH": "European Digital Innovation Hub",
        "HPC_CENTER": "High Performance Computing Center",
        "NGO": "Non-Governmental Organization",
        "COMPETENCE_CENTER": "Digital Competence Center",
        "INTERNATIONAL_ORG": "International Organization",
        "HEALTHCARE": "Healthcare Provider (for digital health)",
        "EDUCATION_PROVIDER": "Education/Training Provider",
    }

    # Digital Europe Specific Objectives
    OBJECTIVES = {
        "HPC": {
            "name": "High Performance Computing",
            "description": "Supercomputing, EuroHPC, data infrastructure",
            "budget": "€2.227 billion",
            "funding_rate": "50%",
            "funding_rate_notes": "Up to 100% for supercomputer acquisition",
        },
        "AI": {
            "name": "Artificial Intelligence",
            "description": "AI testing facilities, data spaces, AI factories",
            "budget": "€2.062 billion",
            "funding_rate": "50%",
            "funding_rate_notes": "SMEs may receive higher rates",
        },
        "CYBERSECURITY": {
            "name": "Cybersecurity and Trust",
            "description": "Cybersecurity infrastructure, SOCs, ECCC initiatives",
            "budget": "€1.650 billion",
            "funding_rate": "50%",
            "funding_rate_notes": "Managed jointly with ECCC",
        },
        "SKILLS": {
            "name": "Advanced Digital Skills",
            "description": "Training, education, certifications in digital technologies",
            "budget": "€577 million",
            "funding_rate": "50%",
            "funding_rate_notes": "Focus on specialized skills programs",
        },
        "DEPLOYMENT": {
            "name": "Deployment and Best Use",
            "description": "EDIHs, digital transformation, interoperability",
            "budget": "€1.072 billion",
            "funding_rate": "50%",
            "funding_rate_notes": "EDIHs receive specific funding",
        },
        "SEMICONDUCTORS": {
            "name": "Semiconductors (Chips Act)",
            "description": "Chip design, pilot lines, competence centers",
            "budget": "Additional funding via Chips Act",
            "funding_rate": "50%",
            "funding_rate_notes": "Part of European Chips Act initiative",
        },
    }

    # Action type rules by objective
    OBJECTIVE_RULES = {
        "HPC": {
            "org_types": [
                "RESEARCH",
                "UNIVERSITY",
                "HPC_CENTER",
                "PUBLIC_AUTHORITY",
                "SME",
                "LARGE_ENTERPRISE",
                "COMPETENCE_CENTER",
            ],
            "country_rule": "participating_plus_swiss",
            "min_partners": 1,
            "action_types": ["grant", "procurement"],
            "notes": "EuroHPC JU manages HPC infrastructure. "
            "National competence centers key actors.",
        },
        "AI": {
            "org_types": [
                "SME",
                "STARTUP",
                "RESEARCH",
                "UNIVERSITY",
                "LARGE_ENTERPRISE",
                "PUBLIC_AUTHORITY",
                "EDIH",
                "HEALTHCARE",
            ],
            "country_rule": "participating_plus_swiss",
            "min_partners": 1,
            "action_types": ["grant", "procurement"],
            "notes": "AI Factories initiative. Testing and Experimentation Facilities (TEFs) key.",
        },
        "CYBERSECURITY": {
            "org_types": [
                "RESEARCH",
                "UNIVERSITY",
                "PUBLIC_AUTHORITY",
                "SME",
                "LARGE_ENTERPRISE",
                "COMPETENCE_CENTER",
            ],
            "country_rule": "participating",
            "min_partners": 1,
            "action_types": ["grant", "procurement"],
            "notes": "ECCC manages cybersecurity actions. National Coordination Centres involved.",
        },
        "SKILLS": {
            "org_types": [
                "UNIVERSITY",
                "EDUCATION_PROVIDER",
                "RESEARCH",
                "SME",
                "LARGE_ENTERPRISE",
                "PUBLIC_AUTHORITY",
                "NGO",
                "EDIH",
            ],
            "country_rule": "participating",
            "min_partners": 1,
            "action_types": ["grant"],
            "notes": "Focus on specialized courses in HPC, AI, cybersecurity, data.",
        },
        "DEPLOYMENT": {
            "org_types": [
                "EDIH",
                "SME",
                "STARTUP",
                "PUBLIC_AUTHORITY",
                "RESEARCH",
                "UNIVERSITY",
                "COMPETENCE_CENTER",
            ],
            "country_rule": "participating",
            "min_partners": 1,
            "action_types": ["grant", "procurement"],
            "notes": "EDIHs central to deployment. Multi-country projects prioritized.",
        },
        "SEMICONDUCTORS": {
            "org_types": [
                "RESEARCH",
                "UNIVERSITY",
                "SME",
                "LARGE_ENTERPRISE",
                "COMPETENCE_CENTER",
                "PUBLIC_AUTHORITY",
            ],
            "country_rule": "participating",
            "min_partners": 1,
            "action_types": ["grant", "procurement"],
            "notes": "Part of Chips Act. Design competence centers and pilot lines.",
        },
    }

    def check_eligibility(
        self,
        org_type: str,
        country: str,
        objective: str,
        action_type: str | None = None,
    ) -> EligibilityResult:
        """
        Check if an organization is eligible for a Digital Europe objective.

        Args:
            org_type: Organization type
            country: Country of the organization
            objective: Digital Europe objective (HPC, AI, CYBERSECURITY, etc.)
            action_type: Optional action type filter (grant, procurement)

        Returns:
            EligibilityResult with detailed eligibility information
        """
        requirements_met = []
        requirements_missing = []
        warnings = []
        recommendations = []

        # Normalize objective
        objective = objective.upper().replace(" ", "_").replace("-", "_")

        # Handle common aliases
        objective_aliases = {
            "CYBER": "CYBERSECURITY",
            "DIGITAL_SKILLS": "SKILLS",
            "ADVANCED_SKILLS": "SKILLS",
            "EDIH": "DEPLOYMENT",
            "BEST_USE": "DEPLOYMENT",
            "BESTUSE": "DEPLOYMENT",
            "CHIPS": "SEMICONDUCTORS",
        }
        objective = objective_aliases.get(objective, objective)

        # Get objective info
        objective_info = self.OBJECTIVES.get(objective)
        rules = self.OBJECTIVE_RULES.get(objective)

        if not objective_info or not rules:
            return EligibilityResult(
                eligible=False,
                objective=objective,
                objective_name="Unknown Objective",
                requirements_met=[],
                requirements_missing=[f"Unknown objective: {objective}"],
                warnings=[],
                recommendations=[
                    "Valid objectives: HPC, AI, CYBERSECURITY, SKILLS, DEPLOYMENT, SEMICONDUCTORS"
                ],
                metadata={"error": "unknown_objective"},
            )

        objective_name = objective_info["name"]

        # Check 1: Organization type
        org_type_upper = org_type.upper().replace(" ", "_").replace("-", "_")

        # Handle aliases
        # Note: STARTUPs are treated as SMEs for eligibility checks where SME is allowed
        # but STARTUP is not explicitly listed. They can participate wherever SMEs can.
        org_aliases = {
            "SMALL_MEDIUM_ENTERPRISE": "SME",
            "HIGH_EDUCATION": "UNIVERSITY",
            "HIGHER_EDUCATION": "UNIVERSITY",
            "GOVERNMENT": "PUBLIC_AUTHORITY",
            "PUBLIC_BODY": "PUBLIC_AUTHORITY",
            "INNOVATION_HUB": "EDIH",
            "DIGITAL_INNOVATION_HUB": "EDIH",
        }
        org_type_upper = org_aliases.get(org_type_upper, org_type_upper)

        # Special handling: STARTUPs are SMEs, so if the org_type is STARTUP
        # and STARTUP is not in the rules but SME is, treat as SME
        original_org_type = org_type_upper
        startup_not_in_rules = "STARTUP" not in rules["org_types"]
        sme_in_rules = "SME" in rules["org_types"]
        if org_type_upper == "STARTUP" and startup_not_in_rules and sme_in_rules:
            org_type_upper = "SME"

        if org_type_upper in rules["org_types"]:
            # If startup was treated as SME, mention both in the message
            if original_org_type == "STARTUP" and org_type_upper == "SME":
                msg = f'Organization "Startup/Scaleup" (as SME) eligible for {objective_name}'
                requirements_met.append(msg)
            else:
                org_desc = self.ORG_TYPES.get(org_type_upper, org_type)
                msg = f'Organization type "{org_desc}" is eligible for {objective_name}'
                requirements_met.append(msg)
        else:
            eligible_types = [self.ORG_TYPES.get(t, t) for t in rules["org_types"]]
            requirements_missing.append(
                f"Organization type not eligible for {objective_name}. "
                f'Eligible types: {", ".join(eligible_types)}'
            )

        # Check 2: Country eligibility
        is_participating = country in self.PARTICIPATING_COUNTRIES
        is_eu_member = country in self.EU_MEMBER_STATES
        is_eea = country in self.EEA_COUNTRIES
        is_associated = country in self.ASSOCIATED_COUNTRIES
        is_partially_associated = country in self.PARTIALLY_ASSOCIATED

        country_rule = rules["country_rule"]

        if country_rule == "participating_plus_swiss":
            if is_participating:
                requirements_met.append(f"{country} is a participating country")
                if is_associated:
                    msg = f"{country} is an associated country. Check call for restrictions."
                    warnings.append(msg)
            elif is_partially_associated:
                allowed_objectives = self.PARTIALLY_ASSOCIATED.get(country, [])
                if objective in allowed_objectives:
                    requirements_met.append(
                        f"{country} participates in {objective_name} under partial association"
                    )
                    objectives_list = ", ".join(allowed_objectives)
                    warnings.append(f"{country} only participates in: {objectives_list}")
                else:
                    requirements_missing.append(
                        f"{country} does not participate in {objective_name}. "
                        f'Switzerland only participates in: {", ".join(allowed_objectives)}'
                    )
            else:
                requirements_missing.append(
                    f"{country} is not eligible. Eligible: EU Member States, EEA countries, "
                    f"associated countries, and Switzerland (for HPC/AI only)."
                )
        elif country_rule == "participating":
            if is_participating:
                requirements_met.append(f"{country} is a participating country")
                if is_associated:
                    warnings.append(
                        f"{country} is an associated country. Check specific call conditions."
                    )
            else:
                requirements_missing.append(
                    f"{country} is not a Digital Europe participating country. "
                    f"Eligible: EU Member States, EEA countries, and associated countries."
                )

        # Add funding information
        recommendations.append(f'Standard funding rate: {objective_info["funding_rate"]}')
        if objective_info.get("funding_rate_notes"):
            recommendations.append(objective_info["funding_rate_notes"])

        # Add objective-specific notes
        if rules.get("notes"):
            recommendations.append(rules["notes"])

        # Add SME-specific information
        if org_type_upper in ["SME", "STARTUP"]:
            recommendations.append(
                "SMEs often receive priority and higher funding rates in Digital Europe calls"
            )

        # Add EDIH-specific information
        if org_type_upper == "EDIH" and objective != "DEPLOYMENT":
            msg = "EDIHs primarily funded under Deployment but can participate elsewhere"
            warnings.append(msg)

        # Add budget information
        recommendations.append(f'Objective budget: {objective_info["budget"]}')

        # Determine overall eligibility
        eligible = len(requirements_missing) == 0

        return EligibilityResult(
            eligible=eligible,
            objective=objective,
            objective_name=objective_name,
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
                "funding_rate": objective_info["funding_rate"],
                "implementing_agency": "DG CONNECT / HaDEA",
            },
        )

    def get_eligible_objectives(
        self,
        org_type: str,
        country: str,
    ) -> list[dict[str, Any]]:
        """
        Get all Digital Europe objectives an organization is eligible for.

        Args:
            org_type: Organization type
            country: Country name

        Returns:
            List of eligible objectives with details
        """
        eligible_objectives = []

        for objective_code in self.OBJECTIVES.keys():
            result = self.check_eligibility(
                org_type=org_type,
                country=country,
                objective=objective_code,
            )

            if result.eligible:
                objective_info = self.OBJECTIVES[objective_code]
                eligible_objectives.append(
                    {
                        "objective": objective_code,
                        "objective_name": result.objective_name,
                        "description": objective_info.get("description"),
                        "budget": objective_info.get("budget"),
                        "funding_rate": objective_info.get("funding_rate"),
                        "warnings": result.warnings,
                        "notes": result.recommendations,
                    }
                )

        return eligible_objectives

    def get_participating_countries(self) -> dict[str, list[str]]:
        """Get participating countries by category."""
        return {
            "eu_member_states": self.EU_MEMBER_STATES.copy(),
            "eea": self.EEA_COUNTRIES.copy(),
            "associated": self.ASSOCIATED_COUNTRIES.copy(),
            "partially_associated": dict(self.PARTIALLY_ASSOCIATED),
        }

    def get_objectives(self) -> dict[str, dict]:
        """Get Digital Europe objectives."""
        return self.OBJECTIVES.copy()


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
    "Liechtenstein": "LI",
    "Norway": "NO",
    "Ukraine": "UA",
    "Moldova": "MD",
    "Montenegro": "ME",
    "North Macedonia": "MK",
    "Serbia": "RS",
    "Albania": "AL",
    "Kosovo": "XK",
    "Türkiye": "TR",
    "Bosnia and Herzegovina": "BA",
    "Switzerland": "CH",
}


async def check_digital_europe_eligibility_execute(
    org_type: str,
    country: str,
    objective: str | None = None,
    action_type: str | None = None,
) -> dict[str, Any]:
    """
    Check Digital Europe eligibility for an organization.

    Args:
        org_type: Organization type (SME, RESEARCH, UNIVERSITY, EDIH, etc.)
        country: Country of the organization
        objective: Specific objective to check (HPC, AI, CYBERSECURITY, etc.) or None for all
        action_type: Optional action type filter (grant, procurement)

    Returns:
        Eligibility result with requirements and recommendations
    """
    tool = DigitalEuropeEligibilityTool()

    if objective:
        # Check specific objective
        result = tool.check_eligibility(
            org_type=org_type,
            country=country,
            objective=objective,
            action_type=action_type,
        )

        return {
            "success": True,
            "result": result.to_dict(),
            "metadata": {
                "tool": "check_digital_europe_eligibility",
                "query_type": "specific_objective",
                "programme": "digital_europe",
                "implementing_agency": "DG CONNECT / HaDEA",
                "programme_budget": "€7.588 billion (2021-2027)",
            },
        }
    else:
        # Get all eligible objectives
        eligible_objectives = tool.get_eligible_objectives(
            org_type=org_type,
            country=country,
        )

        return {
            "success": True,
            "eligible_objectives": eligible_objectives,
            "total_eligible": len(eligible_objectives),
            "participating_countries": tool.get_participating_countries(),
            "objectives": tool.get_objectives(),
            "metadata": {
                "tool": "check_digital_europe_eligibility",
                "query_type": "all_objectives",
                "org_type": org_type,
                "country": country,
                "programme": "digital_europe",
                "implementing_agency": "DG CONNECT / HaDEA",
                "programme_budget": "€7.588 billion (2021-2027)",
            },
        }
