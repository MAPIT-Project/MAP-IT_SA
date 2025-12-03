"""
Budget Calculator Tool for Horizon Europe Proposals.

Helps users calculate realistic budget breakdowns for their proposals
based on patterns from funded projects and Horizon Europe cost rules.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class BudgetCalculatorTool:
    """Calculate realistic budget breakdowns for Horizon Europe proposals."""

    # Typical cost category ratios by action type (from analysis of funded projects)
    COST_RATIOS = {
        'RIA': {
            'personnel': 0.55,      # 55% personnel
            'equipment': 0.10,      # 10% equipment
            'travel': 0.05,         # 5% travel
            'subcontracting': 0.10, # 10% subcontracting
            'other_direct': 0.05,   # 5% other direct
            'indirect': 0.15,       # 15% indirect (25% of direct)
        },
        'IA': {
            'personnel': 0.45,
            'equipment': 0.15,
            'travel': 0.05,
            'subcontracting': 0.15,
            'other_direct': 0.05,
            'indirect': 0.15,
        },
        'CSA': {
            'personnel': 0.65,
            'equipment': 0.02,
            'travel': 0.10,
            'subcontracting': 0.08,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
        'ERC-STG': {
            'personnel': 0.70,
            'equipment': 0.10,
            'travel': 0.05,
            'subcontracting': 0.00,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
        'ERC-COG': {
            'personnel': 0.70,
            'equipment': 0.10,
            'travel': 0.05,
            'subcontracting': 0.00,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
        'ERC-ADG': {
            'personnel': 0.70,
            'equipment': 0.10,
            'travel': 0.05,
            'subcontracting': 0.00,
            'other_direct': 0.05,
            'indirect': 0.10,
        },
    }

    # Person-month costs by country tier (EUR)
    PM_COSTS = {
        'tier1': 8500,   # DE, FR, NL, BE, AT, DK, SE, FI, LU, NO, CH
        'tier2': 6500,   # ES, IT, PT, IE, CZ, SI, EE, GR, CY, MT
        'tier3': 4500,   # PL, HU, RO, BG, HR, SK, LT, LV
        'default': 7000,
    }

    COUNTRY_TIERS = {
        'tier1': ['DE', 'FR', 'NL', 'BE', 'AT', 'DK', 'SE', 'FI', 'LU', 'NO', 'CH'],
        'tier2': ['ES', 'IT', 'PT', 'IE', 'CZ', 'SI', 'EE', 'GR', 'CY', 'MT'],
        'tier3': ['PL', 'HU', 'RO', 'BG', 'HR', 'SK', 'LT', 'LV'],
    }

    # Funding rates
    FUNDING_RATES = {
        'RIA': 1.0,       # 100%
        'IA': 0.7,        # 70% (100% for non-profit)
        'CSA': 1.0,       # 100%
        'ERC-STG': 1.0,
        'ERC-COG': 1.0,
        'ERC-ADG': 1.0,
        'EIC': 0.7,       # Blended for accelerator
    }

    def __init__(self):
        """Initialize with database connection."""
        self.db_url = os.getenv("DATABASE_URL")

    def _get_connection(self):
        """Get database connection."""
        if not self.db_url:
            return None
        return psycopg2.connect(self.db_url)

    def calculate_budget(
        self,
        action_type: str,
        duration_months: int,
        num_partners: int,
        total_person_months: Optional[int] = None,
        target_budget: Optional[float] = None,
        countries: Optional[List[str]] = None,
        include_breakdown: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate recommended budget breakdown for a Horizon Europe proposal.

        Args:
            action_type: RIA, IA, CSA, ERC-STG, ERC-COG, ERC-ADG, etc.
            duration_months: Project duration in months
            num_partners: Number of consortium partners
            total_person_months: Total PMs across all partners (optional)
            target_budget: Target total budget in EUR (optional)
            countries: List of partner country codes (optional)
            include_breakdown: Include detailed cost category breakdown

        Returns:
            Budget breakdown with recommendations
        """
        action_type = action_type.upper()
        ratios = self.COST_RATIOS.get(action_type, self.COST_RATIOS['RIA'])
        funding_rate = self.FUNDING_RATES.get(action_type, 1.0)

        # Calculate average PM cost based on country mix
        avg_pm_cost = self._calculate_avg_pm_cost(countries)

        # Calculate or estimate total budget
        if target_budget:
            total = target_budget
            estimated_pms = int(total * ratios['personnel'] / avg_pm_cost)
        elif total_person_months:
            personnel_cost = total_person_months * avg_pm_cost
            # Personnel is X% of total, so total = personnel / X
            total = personnel_cost / ratios['personnel']
            estimated_pms = total_person_months
        else:
            # Estimate based on typical budgets from database
            benchmarks = self._get_budget_benchmarks(action_type)
            total = benchmarks.get('median', 5_000_000)
            estimated_pms = int(total * ratios['personnel'] / avg_pm_cost)

        # Calculate breakdown
        breakdown = {}
        if include_breakdown:
            breakdown = {
                'personnel': {
                    'amount': round(total * ratios['personnel'], 0),
                    'percentage': round(ratios['personnel'] * 100, 1),
                    'description': 'Salaries, social charges for project staff',
                    'person_months': estimated_pms
                },
                'equipment': {
                    'amount': round(total * ratios['equipment'], 0),
                    'percentage': round(ratios['equipment'] * 100, 1),
                    'description': 'Depreciation of equipment purchased for project'
                },
                'travel': {
                    'amount': round(total * ratios['travel'], 0),
                    'percentage': round(ratios['travel'] * 100, 1),
                    'description': 'Travel and subsistence for project meetings'
                },
                'subcontracting': {
                    'amount': round(total * ratios['subcontracting'], 0),
                    'percentage': round(ratios['subcontracting'] * 100, 1),
                    'description': 'Work carried out by third parties'
                },
                'other_direct': {
                    'amount': round(total * ratios['other_direct'], 0),
                    'percentage': round(ratios['other_direct'] * 100, 1),
                    'description': 'Consumables, publications, dissemination'
                },
                'indirect': {
                    'amount': round(total * ratios['indirect'], 0),
                    'percentage': round(ratios['indirect'] * 100, 1),
                    'description': 'Indirect costs (25% flat rate of direct costs excl. subcontracting)'
                },
            }

        # Calculate per-partner distribution
        coordinator_share = 0.20  # 20% typical for coordinator
        per_partner = {
            'average': round(total / num_partners, 0),
            'coordinator_typical': round(total * coordinator_share, 0),
            'partner_typical': round((total * (1 - coordinator_share)) / max(num_partners - 1, 1), 0),
            'pms_per_partner': round(estimated_pms / num_partners, 0)
        }

        # Calculate EU contribution
        eu_contribution = total * funding_rate

        # Generate recommendations
        recommendations = self._generate_recommendations(
            action_type, total, num_partners, duration_months, estimated_pms
        )

        # Get benchmarks for context
        benchmarks = self._get_budget_benchmarks(action_type)

        return {
            "success": True,
            "tool_name": "calculate_budget",
            "input_parameters": {
                "action_type": action_type,
                "duration_months": duration_months,
                "num_partners": num_partners,
                "total_person_months": total_person_months,
                "target_budget": target_budget,
                "countries": countries
            },
            "calculated_budget": {
                "total_cost": round(total, 0),
                "eu_contribution": round(eu_contribution, 0),
                "funding_rate": f"{funding_rate * 100:.0f}%",
            },
            "breakdown": breakdown,
            "per_partner": per_partner,
            "effort_summary": {
                "total_person_months": estimated_pms,
                "person_months_per_partner": round(estimated_pms / num_partners, 0),
                "avg_pm_cost_used": round(avg_pm_cost, 0),
                "pm_per_month": round(estimated_pms / duration_months, 1)
            },
            "benchmarks": {
                "typical_range": f"€{benchmarks['min']/1_000_000:.1f}M - €{benchmarks['max']/1_000_000:.1f}M",
                "median": f"€{benchmarks['median']/1_000_000:.1f}M",
                "your_budget_vs_median": "within range" if benchmarks['min'] <= total <= benchmarks['max'] else (
                    "below typical" if total < benchmarks['min'] else "above typical"
                )
            },
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_avg_pm_cost(self, countries: Optional[List[str]]) -> float:
        """Calculate average person-month cost based on country mix."""
        if not countries:
            return self.PM_COSTS['default']

        total_cost = 0
        for country in countries:
            country_upper = country.upper()
            if country_upper in self.COUNTRY_TIERS['tier1']:
                total_cost += self.PM_COSTS['tier1']
            elif country_upper in self.COUNTRY_TIERS['tier2']:
                total_cost += self.PM_COSTS['tier2']
            elif country_upper in self.COUNTRY_TIERS['tier3']:
                total_cost += self.PM_COSTS['tier3']
            else:
                total_cost += self.PM_COSTS['default']

        return total_cost / len(countries)

    def _get_budget_benchmarks(self, action_type: str) -> Dict[str, float]:
        """Get budget benchmarks from funded projects or fallback values.

        Uses percentiles (10th-90th) to exclude outliers and provide
        meaningful ranges for budget planning.
        """
        # Try to get from database first
        try:
            conn = self._get_connection()
            if conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Map action type to funding scheme pattern
                scheme_pattern = f"%{action_type.replace('-', '%')}%"

                # Use percentiles to exclude outliers (10th to 90th percentile)
                cursor.execute("""
                    SELECT
                        PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY "ecMaxContribution") as p10_budget,
                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "ecMaxContribution") as p25_budget,
                        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY "ecMaxContribution") as median_budget,
                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "ecMaxContribution") as p75_budget,
                        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY "ecMaxContribution") as p90_budget,
                        AVG("ecMaxContribution") as avg_budget,
                        COUNT(*) as project_count
                    FROM projects
                    WHERE "frameworkProgramme" = 'HORIZON'
                      AND "fundingScheme" ILIKE %s
                      AND "ecMaxContribution" > 100000
                """, [scheme_pattern])

                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if row and row['median_budget'] and row['project_count'] > 10:
                    return {
                        'min': float(row['p10_budget']),  # 10th percentile as "typical min"
                        'max': float(row['p90_budget']),  # 90th percentile as "typical max"
                        'mean': float(row['avg_budget']),
                        'median': float(row['median_budget']),
                        'p25': float(row['p25_budget']),
                        'p75': float(row['p75_budget']),
                        'sample_size': int(row['project_count'])
                    }
        except Exception as e:
            logger.warning(f"Could not get benchmarks from DB: {e}")

        # Fallback benchmarks
        fallback = {
            'RIA': {'min': 2_000_000, 'max': 12_000_000, 'mean': 5_500_000, 'median': 5_000_000},
            'IA': {'min': 3_000_000, 'max': 20_000_000, 'mean': 9_000_000, 'median': 8_000_000},
            'CSA': {'min': 500_000, 'max': 5_000_000, 'mean': 2_000_000, 'median': 1_800_000},
            'ERC-STG': {'min': 1_000_000, 'max': 1_500_000, 'mean': 1_450_000, 'median': 1_500_000},
            'ERC-COG': {'min': 1_500_000, 'max': 2_000_000, 'mean': 1_900_000, 'median': 2_000_000},
            'ERC-ADG': {'min': 2_000_000, 'max': 2_500_000, 'mean': 2_400_000, 'median': 2_500_000},
        }

        return fallback.get(action_type.upper(), fallback['RIA'])

    def _generate_recommendations(
        self,
        action_type: str,
        total: float,
        num_partners: int,
        duration: int,
        total_pms: int
    ) -> List[str]:
        """Generate budget recommendations and warnings."""
        recommendations = []
        benchmarks = self._get_budget_benchmarks(action_type)

        # Budget range check
        if total < benchmarks['min']:
            recommendations.append(
                f"Budget (€{total/1_000_000:.1f}M) is below typical for {action_type}. "
                f"Consider increasing to at least €{benchmarks['min']/1_000_000:.1f}M"
            )
        elif total > benchmarks['max']:
            recommendations.append(
                f"Budget (€{total/1_000_000:.1f}M) is above typical for {action_type}. "
                f"Ensure strong justification for €{benchmarks['max']/1_000_000:.1f}M+ budget"
            )
        else:
            recommendations.append(
                f"Budget is within typical range for {action_type} projects"
            )

        # Per-partner budget check
        per_partner = total / num_partners
        if per_partner < 200_000:
            recommendations.append(
                "Average per-partner budget (€{:.0f}k) may be too low for meaningful contribution. "
                "Consider reducing partners or increasing total budget".format(per_partner/1000)
            )

        # Duration check
        if duration > 48:
            recommendations.append(
                "Projects over 48 months are uncommon and need strong justification"
            )
        elif duration < 24 and action_type in ['RIA', 'IA']:
            recommendations.append(
                f"{action_type} projects typically run 36-48 months. Consider if {duration} months is sufficient"
            )

        # Effort intensity check
        pm_per_partner_per_month = total_pms / num_partners / duration
        if pm_per_partner_per_month < 0.5:
            recommendations.append(
                "Low effort intensity ({:.1f} PM/partner/month). Ensure adequate commitment from each partner".format(
                    pm_per_partner_per_month
                )
            )
        elif pm_per_partner_per_month > 3:
            recommendations.append(
                "High effort intensity ({:.1f} PM/partner/month). Verify capacity of partners".format(
                    pm_per_partner_per_month
                )
            )

        # Action-type specific advice
        if action_type == 'IA':
            recommendations.append(
                "Note: IA funding rate is 70% for for-profit entities (100% for non-profit)"
            )
        elif action_type.startswith('ERC'):
            recommendations.append(
                "ERC grants support single PI - ensure budget aligns with host institution guidelines"
            )
        elif action_type == 'CSA':
            recommendations.append(
                "CSA projects typically have lower equipment costs - focus budget on personnel and events"
            )

        return recommendations


# Async wrapper for tool orchestrator compatibility
async def calculate_budget_execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute budget calculator tool.

    This tool calculates budget breakdowns for Horizon Europe proposals.
    Use it when users want to plan their budget, understand cost categories,
    or validate their budget against typical values.
    """
    tool = BudgetCalculatorTool()

    return tool.calculate_budget(
        action_type=params.get('action_type', 'RIA'),
        duration_months=params.get('duration_months', 36),
        num_partners=params.get('num_partners', 8),
        total_person_months=params.get('total_person_months'),
        target_budget=params.get('target_budget'),
        countries=params.get('countries'),
        include_breakdown=params.get('include_breakdown', True)
    )
