"""
Budget Assistant

Helps create budget tables and justifications for Horizon Europe proposals.
"""

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class BudgetAssistant:
    """
    Generate and validate budget tables for proposals
    """

    # Horizon Europe funding rates by entity type
    FUNDING_RATES = {
        "RIA": {
            "HES": 1.00,  # Higher education
            "REC": 1.00,  # Research organizations
            "PRC": 1.00,  # Private companies (100% for RIA)
            "OTH": 1.00,  # Other
        },
        "IA": {
            "HES": 1.00,
            "REC": 1.00,
            "PRC": 0.70,  # Private companies (70% for IA)
            "OTH": 1.00,
        },
        "CSA": {
            "HES": 1.00,
            "REC": 1.00,
            "PRC": 1.00,
            "OTH": 1.00,
        },
    }

    def __init__(self, db_pool=None):
        self.db_pool = db_pool

    async def generate_budget_table(
        self, call_id: str, proposal_type: str, project_params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate budget breakdown table

        Args:
            call_id: Call identifier
            proposal_type: 'RIA', 'IA', or 'CSA'
            project_params: {
                "duration_months": 36,
                "partners": [
                    {
                        "name": "TU Munich",
                        "country": "DE",
                        "type": "HES",
                        "person_months": 48,
                        "avg_monthly_rate": 5000
                    },
                    ...
                ],
                "total_budget": 2000000  # Optional constraint
            }

        Returns:
            Budget table with all categories and calculations
        """

        logger.info(f"Generating budget for {call_id} ({proposal_type})")

        partners = project_params.get("partners", [])
        duration = project_params.get("duration_months", 36)

        # Calculate budget per partner
        partner_budgets = []
        total_eligible = Decimal("0")
        total_funding = Decimal("0")

        for partner in partners:
            budget = self._calculate_partner_budget(partner, proposal_type, duration)
            partner_budgets.append(budget)
            total_eligible += budget["total_eligible_costs"]
            total_funding += budget["requested_funding"]

        # Check against budget constraints
        budget_constraint = project_params.get("total_budget")
        compliance = self._check_budget_compliance(total_funding, budget_constraint)

        # Generate justification guidance
        justification = self._generate_budget_justification(partner_budgets, proposal_type)

        return {
            "partner_budgets": partner_budgets,
            "summary": {
                "total_eligible_costs": float(total_eligible),
                "total_requested_funding": float(total_funding),
                "average_funding_rate": (
                    float(total_funding / total_eligible) if total_eligible > 0 else 0
                ),
            },
            "compliance": compliance,
            "justification_guidance": justification,
            "budget_table_formatted": self._format_budget_table(partner_budgets),
        }

    def _calculate_partner_budget(
        self, partner: dict[str, Any], proposal_type: str, duration_months: int
    ) -> dict[str, Any]:
        """
        Calculate budget for a single partner
        """

        # Personnel costs
        person_months = Decimal(str(partner.get("person_months", 24)))
        avg_rate = Decimal(str(partner.get("avg_monthly_rate", 5000)))
        personnel_costs = person_months * avg_rate

        # Subcontracting costs (if any)
        subcontracting = Decimal(str(partner.get("subcontracting_costs", 0)))

        # Equipment costs
        equipment = Decimal(str(partner.get("equipment_costs", 0)))

        # Other direct costs
        other_direct = Decimal(str(partner.get("other_direct_costs", 0)))

        # Calculate total direct costs
        total_direct = personnel_costs + subcontracting + equipment + other_direct

        # Indirect costs (25% flat rate on direct costs excluding subcontracting)
        indirect_base = personnel_costs + equipment + other_direct
        indirect_costs = indirect_base * Decimal("0.25")

        # Total eligible costs
        total_eligible = total_direct + indirect_costs

        # Get funding rate for this partner type
        partner_type = partner.get("type", "HES")
        funding_rate = Decimal(
            str(self.FUNDING_RATES.get(proposal_type, {}).get(partner_type, 1.0))
        )

        # Calculate requested funding
        requested_funding = total_eligible * funding_rate

        return {
            "partner_name": partner.get("name", "Unknown"),
            "country": partner.get("country", "Unknown"),
            "partner_type": partner_type,
            "costs": {
                "personnel": float(personnel_costs),
                "subcontracting": float(subcontracting),
                "equipment": float(equipment),
                "other_direct": float(other_direct),
                "indirect": float(indirect_costs),
            },
            "total_eligible_costs": total_eligible,
            "funding_rate": float(funding_rate),
            "requested_funding": requested_funding,
            "person_months": float(person_months),
        }

    def _check_budget_compliance(
        self, total_funding: Decimal, budget_constraint: float = None
    ) -> dict[str, Any]:
        """
        Check budget compliance with call requirements
        """

        issues = []
        warnings = []

        # Check against call budget constraint if provided
        if budget_constraint:
            constraint = Decimal(str(budget_constraint))
            if total_funding > constraint:
                issues.append(
                    f"Total funding (€{total_funding:,}) exceeds call maximum (€{constraint:,})"
                )
            elif total_funding < constraint * Decimal("0.5"):
                warnings.append(
                    f"Total funding seems low compared to call budget (€{constraint:,})"
                )

        return {"compliant": len(issues) == 0, "issues": issues, "warnings": warnings}

    def _generate_budget_justification(
        self, partner_budgets: list[dict], proposal_type: str
    ) -> dict[str, str]:
        """
        Generate guidance for budget justification
        """

        total_person_months = sum(p["person_months"] for p in partner_budgets)

        justification = {
            "personnel": f"""
Personnel costs are calculated based on {total_person_months:.0f} person-months
distributed across {len(partner_budgets)} partners. The allocation reflects the
work package distribution and expertise required for each task.

Key considerations:
- Senior researchers allocated to WP1 (methodology development)
- PhD students and postdocs for experimental work (WP2-3)
- Project management (0.2 FTE throughout project)
""",
            "equipment": """
Equipment costs are justified as follows:
- Essential for achieving project objectives
- Not available at partner institutions
- Will be used >50% for project activities
- Cost-benefit analysis supports purchase over rental
""",
            "other_direct": """
Other direct costs include:
- Travel and accommodation for consortium meetings (4 meetings/year)
- Dissemination activities (conference attendance, publications)
- Consumables and materials for experiments
- SME instrument costs (if applicable)
""",
            "indirect": """
Indirect costs are calculated at the Horizon Europe flat rate of 25% on
direct costs (excluding subcontracting), covering overhead, administration,
and infrastructure costs.
""",
        }

        return justification

    def _format_budget_table(self, partner_budgets: list[dict]) -> str:
        """
        Format budget as a detailed text table for display
        """

        lines = []
        lines.append("DETAILED BUDGET BREAKDOWN")
        lines.append("=" * 120)
        lines.append("")

        # Header with all categories
        header = f"{'Partner':<25} {'Type':<6} {'Country':<8} {'Personnel':>12} {'Equip.':>10} {'Subcont.':>10} {'Other':>10} {'Indirect':>10} {'Total':>12} {'Funding':>12} {'Rate':>6}"
        lines.append(header)
        lines.append("-" * 120)

        # Partner rows
        total_eligible = Decimal("0")
        total_funding = Decimal("0")
        total_personnel = Decimal("0")
        total_equipment = Decimal("0")
        total_subcontracting = Decimal("0")
        total_other = Decimal("0")
        total_indirect = Decimal("0")

        for budget in partner_budgets:
            name = budget["partner_name"][:23]  # Truncate if too long
            partner_type = budget["partner_type"]
            country = budget["country"]
            costs = budget["costs"]

            line = f"{name:<25} {partner_type:<6} {country:<8} €{costs['personnel']:>11,.0f} €{costs.get('subcontracting', 0):>9,.0f} €{costs['equipment']:>9,.0f} €{costs['other_direct']:>9,.0f} €{costs['indirect']:>9,.0f} €{budget['total_eligible_costs']:>11,.0f} €{budget['requested_funding']:>11,.0f} {budget['funding_rate'] * 100:>5.0f}%"
            lines.append(line)

            total_eligible += Decimal(str(budget["total_eligible_costs"]))
            total_funding += Decimal(str(budget["requested_funding"]))
            total_personnel += Decimal(str(costs["personnel"]))
            total_equipment += Decimal(str(costs["equipment"]))
            total_subcontracting += Decimal(str(costs.get("subcontracting", 0)))
            total_other += Decimal(str(costs["other_direct"]))
            total_indirect += Decimal(str(costs["indirect"]))

        # Footer with totals
        lines.append("-" * 120)
        footer = f"{'TOTAL':<25} {'':<14} {'':<8} €{total_personnel:>11,.0f} €{total_subcontracting:>9,.0f} €{total_equipment:>9,.0f} €{total_other:>9,.0f} €{total_indirect:>9,.0f} €{total_eligible:>11,.0f} €{total_funding:>11,.0f} {'':>6}"
        lines.append(footer)
        lines.append("")

        # Detailed summary
        avg_rate = (total_funding / total_eligible * 100) if total_eligible > 0 else 0
        lines.append("BUDGET SUMMARY:")
        lines.append("-" * 40)
        lines.append(f"Total Eligible Costs:     €{total_eligible:,.2f}")
        lines.append(f"Total Requested Funding:  €{total_funding:,.2f}")
        lines.append(f"Average Funding Rate:     {avg_rate:.1f}%")
        lines.append(f"Number of Partners:       {len(partner_budgets)}")

        # Cost breakdown percentages
        if total_eligible > 0:
            lines.append("")
            lines.append("COST BREAKDOWN (% of total):")
            lines.append("-" * 40)
            lines.append(f"Personnel Costs:        {(total_personnel / total_eligible * 100):.1f}%")
            lines.append(f"Equipment Costs:        {(total_equipment / total_eligible * 100):.1f}%")
            lines.append(
                f"Subcontracting:         {(total_subcontracting / total_eligible * 100):.1f}%"
            )
            lines.append(f"Other Direct Costs:     {(total_other / total_eligible * 100):.1f}%")
            lines.append(f"Indirect Costs:         {(total_indirect / total_eligible * 100):.1f}%")

        return "\n".join(lines)
