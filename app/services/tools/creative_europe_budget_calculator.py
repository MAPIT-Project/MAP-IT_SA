"""
Creative Europe Budget Calculator

Calculates grant amounts for Creative Europe actions based on:
- Strand (CULTURE, MEDIA, Cross-sectoral)
- Action type (cooperation projects, development, distribution, etc.)
- Project parameters (partners, duration, costs)

Key characteristics:
- CULTURE strand: Lump sum grants based on project scale
- MEDIA strand: Mix of lump sums and actual costs depending on action
- Cross-sectoral: Typically lump sum with co-financing requirements
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BudgetBreakdown:
    """Detailed budget breakdown."""

    eu_grant: float = 0.0
    co_financing: float = 0.0
    total_budget: float = 0.0
    funding_rate: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "eu_grant": round(self.eu_grant, 2),
            "co_financing": round(self.co_financing, 2),
            "total_budget": round(self.total_budget, 2),
            "funding_rate_percent": round(self.funding_rate, 2),
        }


class CreativeEuropeBudgetCalculator:
    """Calculator for Creative Europe grants."""

    # Budget configurations by action type
    ACTION_BUDGETS = {
        # CULTURE strand
        "COOP-SMALL": {
            "strand": "CULTURE",
            "name": "European Cooperation Projects - Small Scale",
            "grant_max": 200000,
            "funding_rate": 80,
            "duration_months": 48,
            "model": "lump_sum",
        },
        "COOP-MEDIUM": {
            "strand": "CULTURE",
            "name": "European Cooperation Projects - Medium Scale",
            "grant_max": 1000000,
            "funding_rate": 70,
            "duration_months": 48,
            "model": "lump_sum",
        },
        "COOP-LARGE": {
            "strand": "CULTURE",
            "name": "European Cooperation Projects - Large Scale",
            "grant_max": 2000000,
            "funding_rate": 60,
            "duration_months": 48,
            "model": "lump_sum",
        },
        "NETWORK": {
            "strand": "CULTURE",
            "name": "European Networks",
            "grant_max": 2400000,
            "funding_rate": 80,
            "duration_months": 48,
            "model": "lump_sum",
        },
        "PLATFORM": {
            "strand": "CULTURE",
            "name": "European Platforms",
            "grant_max": 2000000,
            "funding_rate": 80,
            "duration_months": 48,
            "model": "lump_sum",
        },
        "LITERARY": {
            "strand": "CULTURE",
            "name": "European Literary Translation",
            "grant_max": 100000,
            "funding_rate": 60,
            "duration_months": 36,
            "model": "lump_sum",
        },
        # MEDIA strand - Development
        "DEVSLATE": {
            "strand": "MEDIA",
            "name": "Development - Slate Funding",
            "grant_min": 150000,
            "grant_max": 210000,
            "funding_rate": 70,
            "duration_months": 36,
            "model": "lump_sum",
            "per_project_cap": 50000,  # Per project in slate
        },
        "DEVSINGLE": {
            "strand": "MEDIA",
            "name": "Development - Single Project",
            "grant_min": 30000,
            "grant_max": 60000,
            "funding_rate": 50,
            "duration_months": 24,
            "model": "lump_sum",
        },
        "DEVMINISLATE": {
            "strand": "MEDIA",
            "name": "Development - Mini-Slate",
            "grant_min": 75000,
            "grant_max": 105000,
            "funding_rate": 60,
            "duration_months": 24,
            "model": "lump_sum",
        },
        "CODEV": {
            "strand": "MEDIA",
            "name": "Co-Development",
            "grant_min": 60000,
            "grant_max": 100000,
            "funding_rate": 50,
            "duration_months": 24,
            "model": "lump_sum",
        },
        "DEVVGIM": {
            "strand": "MEDIA",
            "name": "Video Games & Immersive Content",
            "grant_min": 150000,
            "grant_max": 200000,
            "funding_rate": 50,
            "duration_months": 24,
            "model": "lump_sum",
        },
        # MEDIA strand - Production/Content
        "TVONLINE": {
            "strand": "MEDIA",
            "name": "TV and Online Content",
            "grant_min": 1000000,
            "grant_max": 3000000,
            "funding_rate": 80,
            "duration_months": 36,
            "model": "actual_costs",
        },
        # MEDIA strand - Training/Markets
        "TRAINING": {
            "strand": "MEDIA",
            "name": "Training",
            "grant_min": 150000,
            "grant_max": 400000,
            "funding_rate": 80,
            "duration_months": 24,
            "model": "lump_sum",
        },
        "MARKETNET": {
            "strand": "MEDIA",
            "name": "Markets and Networking",
            "grant_min": 500000,
            "grant_max": 1000000,
            "funding_rate": 80,
            "duration_months": 36,
            "model": "lump_sum",
        },
        # MEDIA strand - Distribution
        "FILMDIST": {
            "strand": "MEDIA",
            "name": "Film Distribution",
            "grant_min": 200000,
            "grant_max": 400000,
            "funding_rate": 60,
            "duration_months": 24,
            "model": "unit_cost",  # Per film/territory
        },
        "FILMSALES": {
            "strand": "MEDIA",
            "name": "Film Sales Agents",
            "grant_min": 300000,
            "grant_max": 500000,
            "funding_rate": 80,
            "duration_months": 24,
            "model": "unit_cost",
        },
        "CINNET": {
            "strand": "MEDIA",
            "name": "Cinema Networks (Europa Cinemas)",
            "grant_min": 5000000,
            "grant_max": 7000000,
            "funding_rate": 50,
            "duration_months": 24,
            "model": "unit_cost",  # Per screening
        },
        # MEDIA strand - Festivals/Audience
        "FEST": {
            "strand": "MEDIA",
            "name": "Film Festivals",
            "grant_min": 75000,
            "grant_max": 150000,
            "funding_rate": 80,
            "duration_months": 24,
            "model": "lump_sum",
        },
        "AUDFILMEDU": {
            "strand": "MEDIA",
            "name": "Audience Development - Film Education",
            "grant_min": 400000,
            "grant_max": 600000,
            "funding_rate": 80,
            "duration_months": 36,
            "model": "lump_sum",
        },
        "INNOVBUSMOD": {
            "strand": "MEDIA",
            "name": "Innovative Business Models",
            "grant_min": 500000,
            "grant_max": 1000000,
            "funding_rate": 70,
            "duration_months": 36,
            "model": "lump_sum",
        },
        # Cross-sectoral strand
        "INNOVLAB": {
            "strand": "CROSS-SECTORAL",
            "name": "Creative Innovation Lab",
            "grant_min": 2000000,
            "grant_max": 4000000,
            "funding_rate": 60,
            "duration_months": 48,
            "model": "lump_sum",
        },
        "JOURPART": {
            "strand": "CROSS-SECTORAL",
            "name": "News Media Partnerships",
            "grant_min": 1000000,
            "grant_max": 3000000,
            "funding_rate": 80,
            "duration_months": 36,
            "model": "lump_sum",
        },
        "MEDIALITERACY": {
            "strand": "CROSS-SECTORAL",
            "name": "Media Literacy",
            "grant_min": 500000,
            "grant_max": 2000000,
            "funding_rate": 70,
            "duration_months": 36,
            "model": "lump_sum",
        },
        "MFP": {
            "strand": "CROSS-SECTORAL",
            "name": "Music Moves Europe",
            "grant_min": 500000,
            "grant_max": 1500000,
            "funding_rate": 70,
            "duration_months": 36,
            "model": "lump_sum",
        },
    }

    # Typical cost categories for CULTURE projects
    CULTURE_COST_CATEGORIES = {
        "staff_costs": 0.45,  # 45% of total
        "travel_costs": 0.15,
        "equipment": 0.05,
        "subcontracting": 0.15,
        "other_direct": 0.10,
        "indirect_costs": 0.10,  # Usually 7% flat rate or actual
    }

    # MEDIA development cost categories
    MEDIA_DEV_CATEGORIES = {
        "option_rights": 0.10,
        "script_development": 0.35,
        "producer_fee": 0.15,
        "legal_finance": 0.10,
        "travel": 0.10,
        "market_promotion": 0.10,
        "overhead": 0.10,
    }

    def calculate_budget(
        self,
        action_type: str,
        requested_amount: float | None = None,
        project_scale: str = "medium",  # 'small', 'medium', 'large'
        num_partners: int = 3,
        duration_months: int | None = None,
    ) -> dict[str, Any]:
        """
        Calculate budget for a Creative Europe action.

        Args:
            action_type: Creative Europe action type
            requested_amount: Requested EU grant (optional)
            project_scale: 'small', 'medium', or 'large'
            num_partners: Number of consortium partners
            duration_months: Project duration (optional, uses default)

        Returns:
            Budget breakdown with recommendations
        """
        action_type = action_type.upper().replace("_", "-")
        config = self.ACTION_BUDGETS.get(action_type)

        if not config:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}",
                "valid_actions": list(self.ACTION_BUDGETS.keys()),
            }

        # Determine grant amount
        grant_max = config["grant_max"]
        grant_min = config.get("grant_min", grant_max)
        funding_rate = config["funding_rate"]
        default_duration = config["duration_months"]

        # Calculate based on scale
        if requested_amount:
            eu_grant = min(max(requested_amount, grant_min), grant_max)
        else:
            if project_scale == "small":
                eu_grant = grant_min
            elif project_scale == "large":
                eu_grant = grant_max
            else:
                eu_grant = (grant_min + grant_max) / 2

        # Calculate total budget and co-financing
        total_budget = eu_grant / (funding_rate / 100)
        co_financing = total_budget - eu_grant

        breakdown = BudgetBreakdown(
            eu_grant=eu_grant,
            co_financing=co_financing,
            total_budget=total_budget,
            funding_rate=funding_rate,
        )

        # Generate cost category breakdown
        if config["strand"] == "CULTURE":
            cost_categories = self._calculate_culture_breakdown(total_budget)
        elif action_type in ["DEVSLATE", "DEVSINGLE", "DEVMINISLATE", "CODEV", "DEVVGIM"]:
            cost_categories = self._calculate_media_dev_breakdown(total_budget)
        else:
            cost_categories = self._calculate_generic_breakdown(total_budget)

        # Determine actual duration
        duration = duration_months if duration_months else default_duration

        # Generate recommendations
        recommendations = []
        if config["strand"] == "CULTURE":
            recommendations.append(
                f"CULTURE projects require strong European dimension with {num_partners}+ partners"
            )
            if action_type.startswith("COOP"):
                recommendations.append(
                    "Consider including diverse sectors: visual arts, music, heritage, design"
                )
        elif config["strand"] == "MEDIA":
            recommendations.append(
                "MEDIA projects must demonstrate commercial potential and audience reach"
            )
            if "DEV" in action_type:
                recommendations.append(
                    "Development grants require demonstrable market interest and financing plan"
                )

        if co_financing > 0:
            recommendations.append(
                f"Co-financing of {co_financing:,.0f} required ({100 - funding_rate}% of total)"
            )

        return {
            "success": True,
            "action_type": action_type,
            "action_name": config["name"],
            "strand": config["strand"],
            "breakdown": breakdown.to_dict(),
            "cost_categories": cost_categories,
            "parameters": {
                "project_scale": project_scale,
                "num_partners": num_partners,
                "duration_months": duration,
            },
            "budget_range": {
                "min_grant": grant_min,
                "max_grant": grant_max,
            },
            "funding_model": config["model"],
            "recommendations": recommendations,
            "notes": [
                f"Max EU grant: {grant_max:,.0f}",
                f"Funding rate: {funding_rate}%",
                f"Duration: up to {default_duration} months",
                f"Funding model: {config['model']}",
            ],
        }

    def _calculate_culture_breakdown(self, total: float) -> dict[str, float]:
        """Calculate CULTURE strand cost breakdown."""
        return {
            "staff_costs": round(total * self.CULTURE_COST_CATEGORIES["staff_costs"], 2),
            "travel_and_subsistence": round(
                total * self.CULTURE_COST_CATEGORIES["travel_costs"], 2
            ),
            "equipment": round(total * self.CULTURE_COST_CATEGORIES["equipment"], 2),
            "subcontracting": round(total * self.CULTURE_COST_CATEGORIES["subcontracting"], 2),
            "other_direct_costs": round(total * self.CULTURE_COST_CATEGORIES["other_direct"], 2),
            "indirect_costs": round(total * self.CULTURE_COST_CATEGORIES["indirect_costs"], 2),
        }

    def _calculate_media_dev_breakdown(self, total: float) -> dict[str, float]:
        """Calculate MEDIA development cost breakdown."""
        return {
            "option_rights": round(total * self.MEDIA_DEV_CATEGORIES["option_rights"], 2),
            "script_development": round(total * self.MEDIA_DEV_CATEGORIES["script_development"], 2),
            "producer_fee": round(total * self.MEDIA_DEV_CATEGORIES["producer_fee"], 2),
            "legal_and_finance": round(total * self.MEDIA_DEV_CATEGORIES["legal_finance"], 2),
            "travel_and_markets": round(total * self.MEDIA_DEV_CATEGORIES["travel"], 2),
            "market_promotion": round(total * self.MEDIA_DEV_CATEGORIES["market_promotion"], 2),
            "overhead": round(total * self.MEDIA_DEV_CATEGORIES["overhead"], 2),
        }

    def _calculate_generic_breakdown(self, total: float) -> dict[str, float]:
        """Calculate generic cost breakdown."""
        return {
            "personnel": round(total * 0.50, 2),
            "travel": round(total * 0.10, 2),
            "external_services": round(total * 0.20, 2),
            "equipment": round(total * 0.05, 2),
            "other_costs": round(total * 0.08, 2),
            "indirect_costs": round(total * 0.07, 2),
        }

    def get_action_budgets_by_strand(self, strand: str) -> list[dict[str, Any]]:
        """Get budget information for all actions in a strand."""
        strand_upper = strand.upper()
        actions = []

        for action_type, config in self.ACTION_BUDGETS.items():
            if config["strand"] == strand_upper:
                actions.append(
                    {
                        "action_type": action_type,
                        "action_name": config["name"],
                        "grant_min": config.get("grant_min", config["grant_max"]),
                        "grant_max": config["grant_max"],
                        "funding_rate": config["funding_rate"],
                        "duration_months": config["duration_months"],
                        "funding_model": config["model"],
                    }
                )

        return actions


# Tool execution function for ToolAwareAgent
async def calculate_creative_europe_budget_execute(
    action_type: str,
    requested_amount: float | None = None,
    project_scale: str = "medium",
    num_partners: int = 3,
    duration_months: int | None = None,
    strand: str | None = None,
) -> dict[str, Any]:
    """
    Calculate Creative Europe grant budget.

    Args:
        action_type: Action type (e.g., 'COOP-SMALL', 'DEVSLATE', 'INNOVLAB')
        requested_amount: Requested EU grant amount (optional)
        project_scale: 'small', 'medium', or 'large'
        num_partners: Number of consortium partners
        duration_months: Project duration in months
        strand: Filter by strand if getting overview

    Returns:
        Budget breakdown with cost categories and recommendations
    """
    calculator = CreativeEuropeBudgetCalculator()

    if action_type.upper() == "OVERVIEW" and strand:
        # Return overview of all actions in strand
        actions = calculator.get_action_budgets_by_strand(strand)
        return {
            "success": True,
            "strand": strand.upper(),
            "actions": actions,
            "total_actions": len(actions),
            "metadata": {
                "tool": "calculate_creative_europe_budget",
                "query_type": "strand_overview",
                "programme": "creative_europe",
            },
        }

    result = calculator.calculate_budget(
        action_type=action_type,
        requested_amount=requested_amount,
        project_scale=project_scale,
        num_partners=num_partners,
        duration_months=duration_months,
    )

    result["metadata"] = {
        "tool": "calculate_creative_europe_budget",
        "programme": "creative_europe",
    }

    return result
