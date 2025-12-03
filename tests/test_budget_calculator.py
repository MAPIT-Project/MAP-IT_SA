"""
Comprehensive tests for the BudgetCalculatorTool.

Tests:
- Budget calculation for different action types
- Cost ratio application
- Person-month cost calculations
- Budget benchmarks (percentile-based)
- Recommendations generation
- Country tier mappings
- Funding rate calculations
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.tools.budget_calculator import (
    BudgetCalculatorTool,
    calculate_budget_execute
)


class TestBudgetCalculatorCostRatios:
    """Tests for cost ratio configurations."""

    def test_ria_cost_ratios_sum_to_one(self):
        """Test RIA cost ratios sum to approximately 1.0."""
        tool = BudgetCalculatorTool()
        ratios = tool.COST_RATIOS['RIA']

        total = sum(ratios.values())
        assert abs(total - 1.0) < 0.01, f"RIA ratios sum to {total}, expected ~1.0"

    def test_ia_cost_ratios_sum_to_one(self):
        """Test IA cost ratios sum to approximately 1.0."""
        tool = BudgetCalculatorTool()
        ratios = tool.COST_RATIOS['IA']

        total = sum(ratios.values())
        assert abs(total - 1.0) < 0.01

    def test_csa_cost_ratios_sum_to_one(self):
        """Test CSA cost ratios sum to approximately 1.0."""
        tool = BudgetCalculatorTool()
        ratios = tool.COST_RATIOS['CSA']

        total = sum(ratios.values())
        assert abs(total - 1.0) < 0.01

    def test_erc_cost_ratios_sum_to_one(self):
        """Test ERC cost ratios sum to approximately 1.0."""
        tool = BudgetCalculatorTool()

        for grant_type in ['ERC-STG', 'ERC-COG', 'ERC-ADG']:
            ratios = tool.COST_RATIOS[grant_type]
            total = sum(ratios.values())
            assert abs(total - 1.0) < 0.01, f"{grant_type} ratios sum to {total}"

    def test_all_action_types_have_required_categories(self):
        """Test all action types have all required cost categories."""
        tool = BudgetCalculatorTool()
        required_categories = ['personnel', 'equipment', 'travel', 'subcontracting', 'other_direct', 'indirect']

        for action_type, ratios in tool.COST_RATIOS.items():
            for category in required_categories:
                assert category in ratios, f"{action_type} missing {category}"

    def test_ria_higher_personnel_than_ia(self):
        """Test RIA has higher personnel ratio than IA."""
        tool = BudgetCalculatorTool()

        assert tool.COST_RATIOS['RIA']['personnel'] > tool.COST_RATIOS['IA']['personnel']

    def test_csa_highest_personnel_ratio(self):
        """Test CSA has highest personnel ratio among standard types."""
        tool = BudgetCalculatorTool()

        csa_personnel = tool.COST_RATIOS['CSA']['personnel']
        ria_personnel = tool.COST_RATIOS['RIA']['personnel']
        ia_personnel = tool.COST_RATIOS['IA']['personnel']

        assert csa_personnel > ria_personnel
        assert csa_personnel > ia_personnel

    def test_erc_no_subcontracting(self):
        """Test ERC grants typically have no subcontracting."""
        tool = BudgetCalculatorTool()

        for grant_type in ['ERC-STG', 'ERC-COG', 'ERC-ADG']:
            assert tool.COST_RATIOS[grant_type]['subcontracting'] == 0.0


class TestPersonMonthCosts:
    """Tests for person-month cost calculations."""

    def test_tier1_countries(self):
        """Test tier 1 country PM costs."""
        tool = BudgetCalculatorTool()

        tier1_countries = ['DE', 'FR', 'NL', 'BE', 'AT', 'DK', 'SE', 'FI', 'LU', 'NO', 'CH']
        for country in tier1_countries:
            assert country in tool.COUNTRY_TIERS['tier1']

        assert tool.PM_COSTS['tier1'] == 8500

    def test_tier2_countries(self):
        """Test tier 2 country PM costs."""
        tool = BudgetCalculatorTool()

        tier2_countries = ['ES', 'IT', 'PT', 'IE', 'CZ', 'SI', 'EE', 'GR', 'CY', 'MT']
        for country in tier2_countries:
            assert country in tool.COUNTRY_TIERS['tier2']

        assert tool.PM_COSTS['tier2'] == 6500

    def test_tier3_countries(self):
        """Test tier 3 country PM costs."""
        tool = BudgetCalculatorTool()

        tier3_countries = ['PL', 'HU', 'RO', 'BG', 'HR', 'SK', 'LT', 'LV']
        for country in tier3_countries:
            assert country in tool.COUNTRY_TIERS['tier3']

        assert tool.PM_COSTS['tier3'] == 4500

    def test_default_pm_cost(self):
        """Test default PM cost for unknown countries."""
        tool = BudgetCalculatorTool()
        assert tool.PM_COSTS['default'] == 7000

    def test_average_pm_cost_single_tier1(self):
        """Test average PM cost for single tier 1 country."""
        tool = BudgetCalculatorTool()
        avg = tool._calculate_avg_pm_cost(['DE'])
        assert avg == 8500

    def test_average_pm_cost_mixed_tiers(self):
        """Test average PM cost for mixed tier countries."""
        tool = BudgetCalculatorTool()
        # DE (8500) + PL (4500) = 13000 / 2 = 6500
        avg = tool._calculate_avg_pm_cost(['DE', 'PL'])
        assert avg == 6500

    def test_average_pm_cost_all_tiers(self):
        """Test average PM cost across all tiers."""
        tool = BudgetCalculatorTool()
        # DE (8500) + ES (6500) + PL (4500) = 19500 / 3 = 6500
        avg = tool._calculate_avg_pm_cost(['DE', 'ES', 'PL'])
        assert avg == 6500

    def test_average_pm_cost_no_countries(self):
        """Test average PM cost when no countries provided."""
        tool = BudgetCalculatorTool()
        avg = tool._calculate_avg_pm_cost(None)
        assert avg == 7000  # Default

    def test_average_pm_cost_unknown_country(self):
        """Test average PM cost for unknown country uses default."""
        tool = BudgetCalculatorTool()
        avg = tool._calculate_avg_pm_cost(['XX'])  # Unknown country
        assert avg == 7000


class TestFundingRates:
    """Tests for funding rate configurations."""

    def test_ria_100_percent(self):
        """Test RIA has 100% funding rate."""
        tool = BudgetCalculatorTool()
        assert tool.FUNDING_RATES['RIA'] == 1.0

    def test_ia_70_percent(self):
        """Test IA has 70% funding rate."""
        tool = BudgetCalculatorTool()
        assert tool.FUNDING_RATES['IA'] == 0.7

    def test_csa_100_percent(self):
        """Test CSA has 100% funding rate."""
        tool = BudgetCalculatorTool()
        assert tool.FUNDING_RATES['CSA'] == 1.0

    def test_erc_100_percent(self):
        """Test all ERC grants have 100% funding rate."""
        tool = BudgetCalculatorTool()

        for grant_type in ['ERC-STG', 'ERC-COG', 'ERC-ADG']:
            assert tool.FUNDING_RATES[grant_type] == 1.0

    def test_eic_blended_rate(self):
        """Test EIC has blended rate."""
        tool = BudgetCalculatorTool()
        assert tool.FUNDING_RATES['EIC'] == 0.7


class TestBudgetCalculation:
    """Tests for budget calculation logic."""

    def test_calculate_basic_ria_budget(self):
        """Test basic RIA budget calculation."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        assert result['success'] == True
        assert result['calculated_budget']['total_cost'] == 5_000_000
        assert result['calculated_budget']['eu_contribution'] == 5_000_000  # 100% for RIA
        assert result['calculated_budget']['funding_rate'] == '100%'

    def test_calculate_ia_budget_with_70_percent(self):
        """Test IA budget calculation with 70% funding."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='IA',
            duration_months=36,
            num_partners=10,
            target_budget=10_000_000
        )

        assert result['calculated_budget']['total_cost'] == 10_000_000
        assert result['calculated_budget']['eu_contribution'] == 7_000_000  # 70% for IA
        assert result['calculated_budget']['funding_rate'] == '70%'

    def test_calculate_from_person_months(self):
        """Test budget calculation from total person-months."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            total_person_months=200,
            countries=['DE', 'FR', 'ES']  # Mix of tier 1 and 2
        )

        assert result['success'] == True
        assert result['effort_summary']['total_person_months'] == 200
        assert result['calculated_budget']['total_cost'] > 0

    def test_breakdown_includes_all_categories(self):
        """Test breakdown includes all cost categories."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000,
            include_breakdown=True
        )

        breakdown = result['breakdown']
        expected_categories = ['personnel', 'equipment', 'travel', 'subcontracting', 'other_direct', 'indirect']

        for category in expected_categories:
            assert category in breakdown
            assert 'amount' in breakdown[category]
            assert 'percentage' in breakdown[category]
            assert 'description' in breakdown[category]

    def test_breakdown_amounts_sum_to_total(self):
        """Test breakdown amounts sum to total budget."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        breakdown = result['breakdown']
        total_from_breakdown = sum(cat['amount'] for cat in breakdown.values())

        # Should be close to total (allowing for rounding)
        assert abs(total_from_breakdown - 5_000_000) < 1000

    def test_per_partner_distribution(self):
        """Test per-partner budget distribution."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=10,
            target_budget=10_000_000
        )

        per_partner = result['per_partner']

        assert per_partner['average'] == 1_000_000  # 10M / 10 partners
        assert per_partner['coordinator_typical'] == 2_000_000  # 20% of total
        assert 'partner_typical' in per_partner
        assert 'pms_per_partner' in per_partner

    def test_effort_summary(self):
        """Test effort summary calculation."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        effort = result['effort_summary']

        assert effort['total_person_months'] > 0
        assert effort['person_months_per_partner'] > 0
        assert effort['avg_pm_cost_used'] > 0
        assert effort['pm_per_month'] > 0


class TestBudgetBenchmarks:
    """Tests for budget benchmarks (percentile-based)."""

    def test_fallback_benchmarks_structure(self):
        """Test fallback benchmark structure for each action type."""
        tool = BudgetCalculatorTool()

        action_types = ['RIA', 'IA', 'CSA', 'ERC-STG', 'ERC-COG', 'ERC-ADG']

        for action_type in action_types:
            benchmarks = tool._get_budget_benchmarks(action_type)

            assert 'min' in benchmarks
            assert 'max' in benchmarks
            assert 'median' in benchmarks
            assert benchmarks['min'] < benchmarks['max']
            assert benchmarks['min'] <= benchmarks['median'] <= benchmarks['max']

    def test_ria_benchmark_range(self):
        """Test RIA fallback benchmark range."""
        tool = BudgetCalculatorTool()
        benchmarks = tool._get_budget_benchmarks('RIA')

        # Fallback values
        assert benchmarks['min'] == 2_000_000
        assert benchmarks['max'] == 12_000_000
        assert benchmarks['median'] == 5_000_000

    def test_erc_stg_benchmark_range(self):
        """Test ERC-StG has capped benchmark range."""
        tool = BudgetCalculatorTool()
        benchmarks = tool._get_budget_benchmarks('ERC-STG')

        # ERC grants have strict caps
        assert benchmarks['max'] <= 1_500_000

    def test_erc_adg_higher_than_stg(self):
        """Test ERC-ADG has higher budget than ERC-STG."""
        tool = BudgetCalculatorTool()

        stg = tool._get_budget_benchmarks('ERC-STG')
        adg = tool._get_budget_benchmarks('ERC-ADG')

        assert adg['max'] > stg['max']

    def test_benchmark_comparison_in_result(self):
        """Test benchmark comparison is included in result."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        benchmarks = result['benchmarks']

        assert 'typical_range' in benchmarks
        assert 'median' in benchmarks
        assert 'your_budget_vs_median' in benchmarks
        assert result['benchmarks']['your_budget_vs_median'] in ['within range', 'below typical', 'above typical']


class TestRecommendations:
    """Tests for recommendation generation."""

    def test_recommendations_generated(self):
        """Test that recommendations are generated."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        assert 'recommendations' in result
        assert isinstance(result['recommendations'], list)
        assert len(result['recommendations']) > 0

    def test_low_budget_warning(self):
        """Test warning for budget below typical range."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=500_000  # Very low
        )

        recommendations = result['recommendations']
        low_budget_warning = any('below typical' in r.lower() for r in recommendations)

        assert low_budget_warning

    def test_high_budget_warning(self):
        """Test warning for budget above typical range."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=50_000_000  # Very high
        )

        recommendations = result['recommendations']
        high_budget_warning = any('above typical' in r.lower() for r in recommendations)

        assert high_budget_warning

    def test_duration_warning_over_48_months(self):
        """Test warning for projects over 48 months."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=60,
            num_partners=8,
            target_budget=5_000_000
        )

        recommendations = result['recommendations']
        duration_warning = any('48 months' in r for r in recommendations)

        assert duration_warning

    def test_ia_funding_rate_note(self):
        """Test IA includes funding rate note."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='IA',
            duration_months=36,
            num_partners=10,
            target_budget=10_000_000
        )

        recommendations = result['recommendations']
        ia_note = any('70%' in r for r in recommendations)

        assert ia_note

    def test_erc_single_pi_note(self):
        """Test ERC includes single PI note."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='ERC-STG',
            duration_months=60,
            num_partners=1,
            target_budget=1_500_000
        )

        recommendations = result['recommendations']
        erc_note = any('single PI' in r for r in recommendations)

        assert erc_note

    def test_low_partner_budget_warning(self):
        """Test warning for low per-partner budget."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=20,  # Many partners
            target_budget=2_000_000  # 100k per partner
        )

        recommendations = result['recommendations']
        low_partner_warning = any('per-partner' in r.lower() for r in recommendations)

        assert low_partner_warning


class TestActionTypeNormalization:
    """Tests for action type case handling."""

    def test_lowercase_action_type(self):
        """Test lowercase action type is handled."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='ria',  # lowercase
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        assert result['success'] == True
        assert result['input_parameters']['action_type'] == 'RIA'

    def test_mixed_case_action_type(self):
        """Test mixed case action type is handled."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='Ria',  # Mixed
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        assert result['success'] == True

    def test_unknown_action_type_uses_ria_defaults(self):
        """Test unknown action type falls back to RIA ratios."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='UNKNOWN',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        # Should succeed using RIA defaults
        assert result['success'] == True


class TestAsyncWrapper:
    """Tests for the async wrapper function."""

    def test_calculate_budget_execute(self):
        """Test async execute wrapper."""
        params = {
            'action_type': 'RIA',
            'duration_months': 36,
            'num_partners': 8,
            'target_budget': 5_000_000
        }
        context = {}

        result = asyncio.run(calculate_budget_execute(params, context))

        assert result['success'] == True
        assert result['tool_name'] == 'calculate_budget'

    def test_execute_with_defaults(self):
        """Test execute uses defaults for missing params."""
        params = {}  # All defaults
        context = {}

        result = asyncio.run(calculate_budget_execute(params, context))

        assert result['success'] == True
        assert result['input_parameters']['action_type'] == 'RIA'
        assert result['input_parameters']['duration_months'] == 36
        assert result['input_parameters']['num_partners'] == 8


class TestBudgetCalculatorEdgeCases:
    """Tests for edge cases."""

    def test_single_partner_project(self):
        """Test budget calculation for single partner (e.g., ERC)."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='ERC-STG',
            duration_months=60,
            num_partners=1,
            target_budget=1_500_000
        )

        assert result['success'] == True
        assert result['per_partner']['average'] == 1_500_000

    def test_many_partners(self):
        """Test budget calculation for large consortium."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=48,
            num_partners=25,
            target_budget=15_000_000
        )

        assert result['success'] == True
        assert result['per_partner']['average'] == 600_000

    def test_short_duration(self):
        """Test budget for short duration project."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='CSA',
            duration_months=12,
            num_partners=5,
            target_budget=1_000_000
        )

        assert result['success'] == True

    def test_no_breakdown_option(self):
        """Test calculation without detailed breakdown."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000,
            include_breakdown=False
        )

        assert result['success'] == True
        assert result['breakdown'] == {}

    def test_result_has_timestamp(self):
        """Test result includes timestamp."""
        tool = BudgetCalculatorTool()

        result = tool.calculate_budget(
            action_type='RIA',
            duration_months=36,
            num_partners=8,
            target_budget=5_000_000
        )

        assert 'timestamp' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
