"""
Integration Tests for New Tools (Iterations 4-7)

Tests the following tools added to MAPIT AI:
1. Multi-Programme Search Tools (Iteration 4-5)
   - search_all_programmes
   - recommend_programmes
   - get_programme_info

2. Proposal Quality Scoring Tools (Iteration 6)
   - score_proposal_section
   - score_full_proposal
   - quick_quality_check

3. Budget Validation Tool (Iteration 7)
   - validate_budget

These tests verify:
- Tool configuration and registration
- Execute function behavior
- Result structure validation
- Edge cases and error handling
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Multi-Programme Search Tool Tests
# =============================================================================

class TestMultiProgrammeSearchConfiguration:
    """Tests for multi-programme search tool configuration."""

    def test_programme_info_has_all_programmes(self):
        """Verify all 6 EU programmes are configured."""
        from app.services.tools.multi_programme_search import PROGRAMME_INFO

        expected_programmes = [
            'horizon_europe',
            'erasmus_plus',
            'creative_europe',
            'eu4health',
            'digital_europe',
            'life',
        ]

        for programme in expected_programmes:
            assert programme in PROGRAMME_INFO, f"Missing programme: {programme}"
            assert 'name' in PROGRAMME_INFO[programme]
            assert 'budget' in PROGRAMME_INFO[programme]
            assert 'focus' in PROGRAMME_INFO[programme]
            assert 'icon' in PROGRAMME_INFO[programme]

    def test_programme_keywords_configured(self):
        """Verify programme keywords are configured for smart detection."""
        from app.services.tools.multi_programme_search import PROGRAMME_KEYWORDS

        for programme in ['horizon_europe', 'erasmus_plus', 'eu4health']:
            assert programme in PROGRAMME_KEYWORDS
            assert len(PROGRAMME_KEYWORDS[programme]) >= 10, \
                f"Programme {programme} should have at least 10 keywords"


class TestGetProgrammeInfo:
    """Tests for get_programme_info_execute function."""

    def test_get_all_programmes(self):
        """Test retrieving info for all programmes."""
        from app.services.tools.multi_programme_search import get_programme_info_execute

        result = get_programme_info_execute()

        assert result['success'] is True
        assert 'programmes' in result
        programmes = result['programmes'].get('programmes', {})
        assert len(programmes) == 6

    def test_get_specific_programme(self):
        """Test retrieving info for a specific programme."""
        from app.services.tools.multi_programme_search import get_programme_info_execute

        result = get_programme_info_execute(programme='erasmus_plus')

        assert result['success'] is True
        assert result['programme'] == 'erasmus_plus'
        assert 'info' in result
        assert result['info']['name'] == 'Erasmus+'

    def test_get_eu4health_info(self):
        """Test EU4Health programme info includes COVID-19 context."""
        from app.services.tools.multi_programme_search import get_programme_info_execute

        result = get_programme_info_execute(programme='eu4health')

        assert result['success'] is True
        assert '€5.3B' in result['info']['budget'] or 'billion' in result['info']['budget'].lower()


class TestProgrammeRecommendations:
    """Tests for get_programme_recommendations_execute function."""

    def test_research_project_recommendations(self):
        """Test recommendations for research-focused project."""
        from app.services.tools.multi_programme_search import get_programme_recommendations_execute

        result = get_programme_recommendations_execute(
            description="Develop novel AI algorithms for drug discovery and precision medicine",
            organization_type="university"
        )

        assert result['success'] is True
        assert len(result['recommendations']) > 0

        # Horizon Europe should be highly ranked for research
        top_programmes = [r['programme'] for r in result['recommendations'][:2]]
        assert 'horizon_europe' in top_programmes or 'eu4health' in top_programmes

    def test_education_project_recommendations(self):
        """Test recommendations for education-focused project."""
        from app.services.tools.multi_programme_search import get_programme_recommendations_execute

        result = get_programme_recommendations_execute(
            description="Student exchange and mobility programme between European universities",
            organization_type="university"
        )

        assert result['success'] is True
        # Erasmus+ should be top recommendation
        top_programme = result['recommendations'][0]['programme']
        assert top_programme == 'erasmus_plus'

    def test_health_project_recommendations(self):
        """Test recommendations for health-focused project."""
        from app.services.tools.multi_programme_search import get_programme_recommendations_execute

        result = get_programme_recommendations_execute(
            description="Develop pandemic preparedness systems and crisis response mechanisms",
            organization_type="hospital"
        )

        assert result['success'] is True
        # EU4Health should be highly ranked
        programmes = [r['programme'] for r in result['recommendations']]
        assert 'eu4health' in programmes


# =============================================================================
# Proposal Quality Scoring Tool Tests
# =============================================================================

class TestProposalQualityScorerConfiguration:
    """Tests for proposal quality scorer configuration."""

    def test_quality_levels_defined(self):
        """Verify quality level classifications are defined."""
        from app.services.tools.proposal_quality_scorer import QualityLevel

        levels = [QualityLevel.EXCELLENT, QualityLevel.VERY_GOOD,
                  QualityLevel.GOOD, QualityLevel.NEEDS_IMPROVEMENT, QualityLevel.WEAK]
        assert len(levels) == 5

    def test_criteria_defined_for_all_sections(self):
        """Verify criteria are defined for all proposal sections."""
        from app.services.tools.proposal_quality_scorer import ProposalQualityScorerTool

        tool = ProposalQualityScorerTool()

        assert 'excellence' in tool.CRITERIA
        assert 'impact' in tool.CRITERIA
        assert 'implementation' in tool.CRITERIA

        for section, subsections in tool.CRITERIA.items():
            assert len(subsections) >= 2, f"Section {section} needs at least 2 subsections"


class TestQuickQualityCheck:
    """Tests for quick_quality_check_execute function."""

    def test_short_text_quality(self):
        """Test quality check for short text."""
        from app.services.tools.proposal_quality_scorer import quick_quality_check_execute

        result = asyncio.run(quick_quality_check_execute(
            text="This is a short text.",
            context="objectives"
        ))

        assert result['success'] is True
        assert 'quality_estimate' in result
        assert result['quality_estimate'] < 3.0  # Should be low for short text

    def test_good_quality_text(self):
        """Test quality check for well-structured text."""
        from app.services.tools.proposal_quality_scorer import quick_quality_check_execute

        good_text = """
        The main objective of this project is to develop innovative AI solutions
        for climate monitoring. Our methodology involves using satellite imagery
        combined with machine learning algorithms to detect environmental changes.
        The expected result is a scalable platform that can be deployed across
        multiple European regions. We will measure success using quantitative
        metrics including 95% accuracy in detection and 50% reduction in response time.
        """

        result = asyncio.run(quick_quality_check_execute(
            text=good_text,
            context="objectives"
        ))

        assert result['success'] is True
        assert result['quality_estimate'] >= 3.0  # Should be reasonable for good text

    def test_quality_suggestions_provided(self):
        """Test that suggestions are provided for improvement."""
        from app.services.tools.proposal_quality_scorer import quick_quality_check_execute

        result = asyncio.run(quick_quality_check_execute(
            text="This project will do things.",
            context="general"
        ))

        assert result['success'] is True
        assert 'suggestions' in result
        # Should suggest improvements for such brief content


class TestProposalSectionScoring:
    """Tests for score_proposal_section_execute function."""

    @pytest.mark.asyncio
    async def test_score_excellence_section(self):
        """Test scoring an excellence section."""
        from app.services.tools.proposal_quality_scorer import score_proposal_section_execute

        content = """
        Our project aims to advance the state of the art in renewable energy storage.
        The methodology combines electrochemical analysis with machine learning optimization.
        We will achieve breakthrough performance in battery efficiency exceeding current
        lithium-ion technology by 40%. Our interdisciplinary approach brings together
        materials science, AI, and chemical engineering expertise.
        """

        result = await score_proposal_section_execute(
            content=content,
            section_type="excellence",
            action_type="RIA"
        )

        assert result['success'] is True
        assert 'score' in result
        assert 0 <= result['score'] <= 5.0
        assert 'quality_level' in result

    @pytest.mark.asyncio
    async def test_short_content_rejected(self):
        """Test that too-short content is rejected."""
        from app.services.tools.proposal_quality_scorer import score_proposal_section_execute

        result = await score_proposal_section_execute(
            content="Short.",
            section_type="excellence"
        )

        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_invalid_section_type_handled(self):
        """Test handling of invalid section type."""
        from app.services.tools.proposal_quality_scorer import score_proposal_section_execute

        result = await score_proposal_section_execute(
            content="Valid content that is long enough for evaluation purposes here.",
            section_type="invalid_section"
        )

        assert result['success'] is False
        assert 'error' in result


# =============================================================================
# Budget Validation Tool Tests
# =============================================================================

class TestBudgetValidatorConfiguration:
    """Tests for budget validator configuration."""

    def test_funding_rates_configured(self):
        """Verify funding rates are configured for all action types."""
        from app.services.tools.budget_validator import BudgetValidatorTool

        tool = BudgetValidatorTool()

        expected_actions = ['RIA', 'IA', 'CSA', 'ERC-STG', 'ERC-COG', 'ERC-ADG']
        for action in expected_actions:
            assert action in tool.FUNDING_RATES, f"Missing funding rate for {action}"
            assert 'default' in tool.FUNDING_RATES[action]

    def test_cost_category_limits_configured(self):
        """Verify cost category limits are configured."""
        from app.services.tools.budget_validator import BudgetValidatorTool

        tool = BudgetValidatorTool()

        for action in ['RIA', 'IA', 'CSA']:
            assert action in tool.COST_CATEGORY_LIMITS
            limits = tool.COST_CATEGORY_LIMITS[action]
            assert 'personnel' in limits
            assert 'equipment' in limits

    def test_consortium_requirements_configured(self):
        """Verify consortium requirements are configured."""
        from app.services.tools.budget_validator import BudgetValidatorTool

        tool = BudgetValidatorTool()

        assert 'RIA' in tool.CONSORTIUM_REQUIREMENTS
        assert tool.CONSORTIUM_REQUIREMENTS['RIA']['min_partners'] >= 3


class TestBudgetValidation:
    """Tests for validate_budget_execute function."""

    def test_valid_ria_budget(self):
        """Test validation of a valid RIA budget."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=4_000_000,
            eu_contribution=4_000_000,
            action_type='RIA',
            duration_months=36,
            num_partners=8
        )

        assert result['success'] is True
        assert result['valid'] is True
        assert result['compliance_score'] >= 80
        assert result['critical_count'] == 0

    def test_ia_funding_rate_warning(self):
        """Test that IA with 100% funding rate triggers warning."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=6_000_000,
            eu_contribution=6_000_000,  # 100% for IA
            action_type='IA',
            num_partners=5
        )

        assert result['success'] is True
        # Should have issues about funding rate for IA
        issues = [i for i in result['issues'] if 'funding rate' in i['message'].lower()]
        assert len(issues) > 0

    def test_insufficient_partners_critical(self):
        """Test that insufficient partners triggers critical issue."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=4_000_000,
            eu_contribution=4_000_000,
            action_type='RIA',
            num_partners=2  # Below minimum of 3
        )

        assert result['success'] is True
        assert result['critical_count'] >= 1

        critical_issues = [i for i in result['issues'] if i['level'] == 'critical']
        assert len(critical_issues) >= 1

    def test_cost_breakdown_validation(self):
        """Test validation with detailed cost breakdown."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=3_000_000,
            eu_contribution=3_000_000,
            action_type='RIA',
            num_partners=5,
            cost_breakdown={
                'personnel': 1_500_000,
                'equipment': 300_000,
                'travel': 150_000,
                'subcontracting': 300_000,
                'other_direct': 150_000,
                'indirect': 600_000,
            }
        )

        assert result['success'] is True
        assert 'passed_checks' in result
        assert len(result['passed_checks']) > 0

    def test_budget_too_high_warning(self):
        """Test warning for budget exceeding typical range."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=20_000_000,
            eu_contribution=20_000_000,
            action_type='RIA',  # Typical max is 15M
            num_partners=10
        )

        assert result['success'] is True
        # Should have warning about high budget
        budget_issues = [i for i in result['issues'] if i['category'] == 'budget_range']
        assert len(budget_issues) > 0

    def test_indirect_costs_validation(self):
        """Test that incorrect indirect costs are flagged."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=2_000_000,
            eu_contribution=2_000_000,
            action_type='RIA',
            num_partners=4,
            cost_breakdown={
                'personnel': 1_000_000,
                'equipment': 200_000,
                'travel': 100_000,
                'other_direct': 100_000,
                'indirect': 400_000,  # Should be 25% of direct = 350k
            }
        )

        assert result['success'] is True
        # Should flag indirect cost discrepancy
        indirect_issues = [i for i in result['issues'] if i['category'] == 'indirect_costs']
        assert len(indirect_issues) > 0


class TestBudgetValidatorEdgeCases:
    """Edge case tests for budget validator."""

    def test_zero_budget(self):
        """Test handling of zero budget."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=0,
            eu_contribution=0,
            action_type='RIA'
        )

        assert result['success'] is True
        assert result['critical_count'] >= 1

    def test_erc_single_pi(self):
        """Test ERC grants allow single PI."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=1_500_000,
            eu_contribution=1_500_000,
            action_type='ERC-STG',
            num_partners=1,
            duration_months=60
        )

        assert result['success'] is True
        assert result['valid'] is True
        # Single partner should be valid for ERC
        partner_issues = [i for i in result['issues']
                        if i['category'] == 'consortium' and 'partner' in i['message'].lower()]
        assert len([i for i in partner_issues if i['level'] == 'critical']) == 0

    def test_csa_different_rules(self):
        """Test CSA has different validation rules."""
        from app.services.tools.budget_validator import validate_budget_execute

        result = validate_budget_execute(
            total_cost=2_000_000,
            eu_contribution=2_000_000,
            action_type='CSA',
            num_partners=1,  # Valid for CSA
            duration_months=24
        )

        assert result['success'] is True
        assert result['valid'] is True


# =============================================================================
# ToolAwareAgent Integration Tests
# =============================================================================

class TestToolAwareAgentIntegration:
    """Tests for tool integration in ToolAwareAgent."""

    def test_new_tools_registered(self):
        """Verify new tools are registered in ToolAwareAgent."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent()

        # Check multi-programme tools
        assert 'search_all_programmes' in agent.tools
        assert 'recommend_programmes' in agent.tools
        assert 'get_programme_info' in agent.tools

        # Check proposal quality tools
        assert 'score_proposal_section' in agent.tools
        assert 'score_full_proposal' in agent.tools
        assert 'quick_quality_check' in agent.tools

        # Check budget validation tool
        assert 'validate_budget' in agent.tools

    def test_tool_methods_exist(self):
        """Verify tool implementation methods exist."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent()

        # Multi-programme tools
        assert hasattr(agent, '_tool_search_all_programmes')
        assert hasattr(agent, '_tool_recommend_programmes')
        assert hasattr(agent, '_tool_get_programme_info')

        # Proposal quality tools
        assert hasattr(agent, '_tool_score_proposal_section')
        assert hasattr(agent, '_tool_score_full_proposal')
        assert hasattr(agent, '_tool_quick_quality_check')

        # Budget validation
        assert hasattr(agent, '_tool_validate_budget')

    def test_tool_descriptions_present(self):
        """Verify all tools have descriptions for LLM."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent()

        for tool_name in ['search_all_programmes', 'validate_budget', 'score_proposal_section']:
            tool = agent.tools.get(tool_name)
            assert tool is not None, f"Tool {tool_name} not found"
            assert len(tool.description) > 50, f"Tool {tool_name} description too short"
            assert len(tool.parameters) > 0, f"Tool {tool_name} has no parameters"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
