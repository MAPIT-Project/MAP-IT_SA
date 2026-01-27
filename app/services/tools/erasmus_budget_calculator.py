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
from dataclasses import dataclass
from typing import Any

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
            self.travel
            + self.individual_support
            + self.organizational_support
            + self.project_management
            + self.transnational_meetings
            + self.intellectual_outputs
            + self.special_needs
            + self.exceptional_costs
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "travel": round(self.travel, 2),
            "individual_support": round(self.individual_support, 2),
            "organizational_support": round(self.organizational_support, 2),
            "project_management": round(self.project_management, 2),
            "transnational_meetings": round(self.transnational_meetings, 2),
            "intellectual_outputs": round(self.intellectual_outputs, 2),
            "special_needs": round(self.special_needs, 2),
            "exceptional_costs": round(self.exceptional_costs, 2),
            "total": round(self.total, 2),
        }


class ErasmusBudgetCalculator:
    """Calculator for Erasmus+ lump sum grants."""

    # Travel distance bands (EUR per participant, round trip)
    TRAVEL_BANDS = {
        "10-99km": 23,
        "100-499km": 180,
        "500-1999km": 275,
        "2000-2999km": 360,
        "3000-3999km": 530,
        "4000-7999km": 820,
        "8000+km": 1500,
        "green_travel_bonus": 50,  # Additional for sustainable travel
    }

    # Individual support daily rates (EUR per day)
    # Based on Erasmus+ 2024-2027 Programme Guide
    INDIVIDUAL_SUPPORT = {
        "staff_mobility": {
            "group1": 180,  # Denmark, Ireland, Iceland, Luxembourg, etc.
            "group2": 160,  # Austria, Belgium, Germany, France, etc.
            "group3": 140,  # Cyprus, Greece, Malta, Portugal, etc.
        },
        "student_mobility": {
            "group1": 79,  # Long-term mobility
            "group2": 79,
            "group3": 79,
            "top_up": 250,  # Monthly top-up for disadvantaged students
        },
        "youth_mobility": {
            "participant_day": 58,
            "leader_day": 74,
        },
        "trainee_mobility": {
            "group1": 79,
            "group2": 79,
            "group3": 79,
            "top_up": 150,  # Top-up for traineeships
        },
    }

    # Organizational support (EUR per participant)
    ORG_SUPPORT = {
        "higher_ed": 350,  # Per participant
        "vet": 350,  # Per participant
        "school": 100,  # Per participant
        "adult_ed": 100,  # Per participant
        "youth": 0,  # Included in activity costs
    }

    # Project management lump sums (KA2)
    PROJECT_MANAGEMENT = {
        "coordinator": 500,  # EUR per month
        "partner": 250,  # EUR per month
    }

    # Transnational meeting costs (EUR per participant)
    TRANSNATIONAL_MEETINGS = {
        "local": 100,  # Same country (up to 575km)
        "abroad": 575,  # Different country
    }

    # Intellectual output daily rates (EUR per day)
    INTELLECTUAL_OUTPUTS = {
        "manager": 294,
        "researcher": 214,
        "technician": 162,
        "administrative": 131,
    }

    # Country groups for cost rates (2024-2027)
    COUNTRY_GROUPS = {
        "group1": [
            "Denmark",
            "Finland",
            "Iceland",
            "Ireland",
            "Liechtenstein",
            "Luxembourg",
            "Norway",
            "Sweden",
        ],
        "group2": [
            "Austria",
            "Belgium",
            "Cyprus",
            "France",
            "Germany",
            "Greece",
            "Italy",
            "Malta",
            "Netherlands",
            "Portugal",
            "Spain",
        ],
        "group3": [
            "Bulgaria",
            "Croatia",
            "Czech Republic",
            "Estonia",
            "Hungary",
            "Latvia",
            "Lithuania",
            "North Macedonia",
            "Poland",
            "Romania",
            "Serbia",
            "Slovakia",
            "Slovenia",
            "Turkey",
        ],
    }

    # Budget ranges for partnership types
    PARTNERSHIP_BUDGETS = {
        "cooperation": {
            "min": 120000,
            "max": 400000,
            "typical_small": 120000,
            "typical_medium": 250000,
            "typical_large": 400000,
        },
        "small_scale": {
            "min": 30000,
            "max": 60000,
            "typical_small": 30000,
            "typical_medium": 45000,
            "typical_large": 60000,
        },
        "alliances": {
            "min": 1000000,
            "max": 1500000,
        },
        "cbhe": {
            "min": 200000,
            "max": 1000000,
        },
    }

    def calculate_mobility_budget(
        self,
        action_type: str,
        participants: int,
        duration_days: int,
        destination_country: str,
        origin_country: str,
        distance_band: str = "500-1999km",
        include_org_support: bool = True,
        green_travel: bool = False,
        include_disadvantaged_top_up: int = 0,
    ) -> dict[str, Any]:
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
            include_disadvantaged_top_up: Number of participants with top-up

        Returns:
            Budget breakdown with total
        """
        breakdown = BudgetBreakdown()

        # Get country group for rates
        dest_group = self._get_country_group(destination_country)

        # Travel costs
        travel_rate = self.TRAVEL_BANDS.get(distance_band, 275)
        if green_travel:
            travel_rate += self.TRAVEL_BANDS["green_travel_bonus"]
        breakdown.travel = travel_rate * participants

        # Individual support
        mobility_type = action_type.lower().replace("-", "_")
        if mobility_type in self.INDIVIDUAL_SUPPORT:
            rates = self.INDIVIDUAL_SUPPORT[mobility_type]
            if dest_group in rates:
                daily_rate = rates[dest_group]
            else:
                daily_rate = rates.get("participant_day", 79)
            breakdown.individual_support = daily_rate * duration_days * participants

            # Add top-up for disadvantaged participants
            if include_disadvantaged_top_up > 0:
                top_up = rates.get("top_up", 0)
                # Convert days to months for top-up calculation
                months = max(1, duration_days / 30)
                breakdown.individual_support += top_up * months * include_disadvantaged_top_up
        else:
            # Default rates
            breakdown.individual_support = 79 * duration_days * participants

        # Organizational support
        if include_org_support:
            sector = self._get_sector_from_action(action_type)
            org_rate = self.ORG_SUPPORT.get(sector, 100)
            breakdown.organizational_support = org_rate * participants

        notes = [
            "Amounts based on Erasmus+ 2024-2027 Programme Guide unit costs",
            f"Destination country group: {dest_group}",
        ]
        if green_travel:
            notes.append(f"Green travel bonus: +{self.TRAVEL_BANDS['green_travel_bonus']}")
        if include_disadvantaged_top_up > 0:
            notes.append(
                f"Disadvantaged participant top-up included for {include_disadvantaged_top_up} participants"
            )

        return {
            "success": True,
            "breakdown": breakdown.to_dict(),
            "parameters": {
                "action_type": action_type,
                "participants": participants,
                "duration_days": duration_days,
                "destination_country": destination_country,
                "origin_country": origin_country,
                "distance_band": distance_band,
                "green_travel": green_travel,
            },
            "notes": notes,
            "funding_model": "unit_cost",
        }

    def calculate_partnership_budget(
        self,
        partnership_type: str,  # 'cooperation' or 'small_scale'
        num_partners: int,
        duration_months: int,
        transnational_meetings: int = 4,
        intellectual_outputs: int = 0,
        coordinator_country: str = "Germany",
        target_budget: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate budget for KA2 partnership projects.

        Args:
            partnership_type: 'cooperation' (120-400k) or 'small_scale' (30-60k)
            num_partners: Number of partner organizations
            duration_months: Project duration in months
            transnational_meetings: Number of transnational meetings
            intellectual_outputs: Number of intellectual outputs
            coordinator_country: Country of coordinator
            target_budget: Target budget amount (optional)

        Returns:
            Budget breakdown with total
        """
        breakdown = BudgetBreakdown()

        # Get budget range
        budget_range = self.PARTNERSHIP_BUDGETS.get(
            partnership_type.lower(), self.PARTNERSHIP_BUDGETS["cooperation"]
        )

        # Project management
        breakdown.project_management = self.PROJECT_MANAGEMENT[
            "coordinator"
        ] * duration_months + self.PROJECT_MANAGEMENT["partner"] * duration_months * (
            num_partners - 1
        )

        # Transnational meetings (estimate 3 participants per partner per meeting)
        participants_per_meeting = num_partners * 3
        breakdown.transnational_meetings = (
            self.TRANSNATIONAL_MEETINGS["abroad"]
            * participants_per_meeting
            * transnational_meetings
        )

        # Intellectual outputs (if any)
        if intellectual_outputs > 0:
            # Estimate: 20 researcher-days per output
            breakdown.intellectual_outputs = (
                self.INTELLECTUAL_OUTPUTS["researcher"] * 20 * intellectual_outputs
            )

        # Calculate current total
        current_total = breakdown.total
        max_budget = budget_range["max"]
        min_budget = budget_range["min"]

        # Adjust to target or fit within range
        if target_budget:
            target = min(max(target_budget, min_budget), max_budget)
            if current_total > 0:
                scale = target / current_total
                breakdown.project_management *= scale
                breakdown.transnational_meetings *= scale
                breakdown.intellectual_outputs *= scale
        else:
            # Adjust if over/under limits
            if current_total > max_budget:
                scale = max_budget / current_total
                breakdown.project_management *= scale
                breakdown.transnational_meetings *= scale
                breakdown.intellectual_outputs *= scale
            elif current_total < min_budget:
                # Add exceptional costs buffer
                breakdown.exceptional_costs = min_budget - current_total

        # Provide budget options
        budget_options = []
        if partnership_type.lower() == "cooperation":
            budget_options = [
                {
                    "label": "Small",
                    "amount": 120000,
                    "description": "Minimum cooperation partnership",
                },
                {
                    "label": "Medium",
                    "amount": 250000,
                    "description": "Standard cooperation partnership",
                },
                {
                    "label": "Large",
                    "amount": 400000,
                    "description": "Maximum cooperation partnership",
                },
            ]
        elif partnership_type.lower() == "small_scale":
            budget_options = [
                {
                    "label": "Small",
                    "amount": 30000,
                    "description": "Minimum small-scale partnership",
                },
                {
                    "label": "Large",
                    "amount": 60000,
                    "description": "Maximum small-scale partnership",
                },
            ]

        return {
            "success": True,
            "breakdown": breakdown.to_dict(),
            "parameters": {
                "partnership_type": partnership_type,
                "num_partners": num_partners,
                "duration_months": duration_months,
                "transnational_meetings": transnational_meetings,
                "intellectual_outputs": intellectual_outputs,
            },
            "budget_range": {
                "min": min_budget,
                "max": max_budget,
            },
            "budget_options": budget_options,
            "notes": [
                f"{partnership_type.title()} Partnership budget range: {min_budget:,.0f} - {max_budget:,.0f}",
                "Erasmus+ uses simplified lump sum model",
                "Actual spending flexibility within budget categories",
                f"Recommended: {num_partners} partners x {duration_months} months",
            ],
            "funding_model": "lump_sum",
        }

    def calculate_jean_monnet_budget(
        self,
        action_type: str,  # 'module', 'chair', 'coe', 'network', 'project'
        duration_years: int = 3,
    ) -> dict[str, Any]:
        """
        Calculate budget for Jean Monnet actions.

        Args:
            action_type: Type of Jean Monnet action
            duration_years: Duration in years

        Returns:
            Budget breakdown
        """
        breakdown = BudgetBreakdown()

        # Jean Monnet budgets (lump sums)
        jm_budgets = {
            "module": {"total": 30000, "duration": 3, "type": "Teaching Module"},
            "chair": {"total": 50000, "duration": 3, "type": "Chair"},
            "coe": {"total": 100000, "duration": 3, "type": "Centre of Excellence"},
            "network": {"total": 300000, "duration": 3, "type": "Network"},
            "project": {"total": 60000, "duration": 2, "type": "Policy Debate"},
        }

        jm_config = jm_budgets.get(action_type.lower(), jm_budgets["module"])
        breakdown.project_management = jm_config["total"]

        return {
            "success": True,
            "breakdown": breakdown.to_dict(),
            "parameters": {
                "action_type": f"Jean Monnet {jm_config['type']}",
                "duration_years": jm_config["duration"],
            },
            "notes": [
                f"Jean Monnet {jm_config['type']} grant: {jm_config['total']:,.0f}",
                f"Standard duration: {jm_config['duration']} years",
                "Fixed lump sum - simplified management",
            ],
            "funding_model": "lump_sum",
        }

    def calculate_sport_budget(
        self,
        partnership_type: str,  # 'cooperation' or 'small_scale'
        num_partners: int,
        duration_months: int = 24,
    ) -> dict[str, Any]:
        """
        Calculate budget for Sport actions.

        Args:
            partnership_type: 'cooperation' or 'small_scale'
            num_partners: Number of partner organizations
            duration_months: Project duration

        Returns:
            Budget breakdown
        """
        breakdown = BudgetBreakdown()

        if partnership_type.lower() == "small_scale":
            budget_range = {"min": 30000, "max": 60000}
        else:
            budget_range = {"min": 120000, "max": 400000}

        # Simplified calculation
        typical_budget = (budget_range["min"] + budget_range["max"]) / 2
        breakdown.project_management = typical_budget

        return {
            "success": True,
            "breakdown": breakdown.to_dict(),
            "parameters": {
                "partnership_type": f"Sport {partnership_type.title()} Partnership",
                "num_partners": num_partners,
                "duration_months": duration_months,
            },
            "budget_range": budget_range,
            "notes": [
                f"Sport {partnership_type.title()} Partnership: {budget_range['min']:,.0f} - {budget_range['max']:,.0f}",
                f"Recommended: {num_partners} partners from {num_partners} countries minimum",
            ],
            "funding_model": "lump_sum",
        }

    def _get_country_group(self, country: str) -> str:
        """Get country group for cost rates."""
        for group, countries in self.COUNTRY_GROUPS.items():
            if country in countries:
                return group
        return "group3"  # Default for non-EU countries

    def _get_sector_from_action(self, action_type: str) -> str:
        """Map action type to sector."""
        action_lower = action_type.lower()
        if "staff" in action_lower or "student" in action_lower or "hed" in action_lower:
            return "higher_ed"
        elif "vet" in action_lower or "trainee" in action_lower:
            return "vet"
        elif "school" in action_lower or "sch" in action_lower:
            return "school"
        elif "adult" in action_lower or "adu" in action_lower:
            return "adult_ed"
        elif "youth" in action_lower or "you" in action_lower:
            return "youth"
        return "higher_ed"


# Tool execution function for ToolAwareAgent
async def calculate_erasmus_budget_execute(
    action_type: str,
    num_participants: int = 10,
    duration_days: int = 14,
    duration_months: int = 24,
    num_partners: int = 3,
    destination_country: str = "Germany",
    origin_country: str = "Spain",
    partnership_type: str = "cooperation",
    distance_band: str = "500-1999km",
    green_travel: bool = False,
    target_budget: float | None = None,
) -> dict[str, Any]:
    """
    Calculate Erasmus+ lump sum budget.

    Args:
        action_type: 'mobility', 'partnership', 'jean_monnet', 'sport', or specific KA codes
        num_participants: Number of participants (for mobility)
        duration_days: Duration in days (for mobility)
        duration_months: Duration in months (for partnership)
        num_partners: Number of partners (for partnership)
        destination_country: Destination/coordinator country
        origin_country: Origin country (for mobility)
        partnership_type: 'cooperation' or 'small_scale'
        distance_band: Travel distance band for mobility
        green_travel: Whether using sustainable travel
        target_budget: Target budget amount (for partnership)

    Returns:
        Budget breakdown with recommendations
    """
    calculator = ErasmusBudgetCalculator()
    action_upper = action_type.upper()

    # Determine action category
    # KA1 Mobility includes: staff_mobility, student_mobility, trainee_mobility, youth_mobility
    mobility_keywords = [
        "MOBILITY",
        "KA1",
        "STUDENT",
        "STAFF",
        "TRAINEE",
        "YOUTH",
        "VET_MOBILITY",
        "HED_MOBILITY",
    ]
    is_mobility = any(kw in action_upper for kw in mobility_keywords)

    if is_mobility:
        # Determine specific mobility type
        if "STUDENT" in action_upper or "HED" in action_upper:
            mobility_type = "student_mobility"
        elif "TRAINEE" in action_upper or "VET" in action_upper:
            mobility_type = "trainee_mobility"
        elif "YOUTH" in action_upper:
            mobility_type = "youth_mobility"
        else:
            mobility_type = "staff_mobility"  # Default for KA1/MOBILITY

        result = calculator.calculate_mobility_budget(
            action_type=mobility_type,
            participants=num_participants,
            duration_days=duration_days,
            destination_country=destination_country,
            origin_country=origin_country,
            distance_band=distance_band,
            green_travel=green_travel,
        )
    elif action_upper in ["JEAN_MONNET", "JMO"] or "JMO" in action_upper:
        jm_type = "module"
        if "CHAIR" in action_upper:
            jm_type = "chair"
        elif "COE" in action_upper:
            jm_type = "coe"
        elif "NETWORK" in action_upper:
            jm_type = "network"
        result = calculator.calculate_jean_monnet_budget(
            action_type=jm_type,
        )
    elif action_upper in ["SPORT"] or "SPORT" in action_upper:
        result = calculator.calculate_sport_budget(
            partnership_type=partnership_type,
            num_partners=num_partners,
            duration_months=duration_months,
        )
    else:
        # Default to partnership (KA2)
        result = calculator.calculate_partnership_budget(
            partnership_type=partnership_type,
            num_partners=num_partners,
            duration_months=duration_months,
            coordinator_country=destination_country,
            target_budget=target_budget,
        )

    result["metadata"] = {
        "tool": "calculate_erasmus_budget",
        "funding_model": result.get("funding_model", "lump_sum"),
        "programme": "erasmus_plus",
    }

    return result
