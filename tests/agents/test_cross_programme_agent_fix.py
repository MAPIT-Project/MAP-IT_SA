# isort: skip_file
"""
Tests for CrossProgrammeAgent funding rate vs success rate distinction fix.

This test verifies that the CrossProgrammeAgent correctly distinguishes between:
- Funding rates (RIA=100%, IA=70%): % of eligible costs funded by EU
- Success rates (~10-15%): % of proposals that get funded

Issue: The validator was flagging success rate mentions like "RIA success rate is 12%"
as incorrect facts because it expected the funding rate of 100%.
"""

import pytest

from tests.agents.cross_programme_agent import CrossProgrammeAgent


class TestFundingRateSuccessRateDistinction:
    """Tests for funding rate vs success rate distinction."""

    @pytest.fixture
    def agent(self):
        """Create a CrossProgrammeAgent instance."""
        return CrossProgrammeAgent(use_llm=False)  # Use rule-based for deterministic tests

    @pytest.mark.asyncio
    async def test_success_rate_not_flagged_as_incorrect_funding_rate(self, agent):
        """Test that success rate mentions are not flagged as incorrect funding rates."""
        # Response that mentions success rates (NOT funding rates)
        response = """
        The success rates for Horizon Europe vary by instrument type:
        - RIA success rate is approximately 12%
        - IA success rate is around 10%
        - ERC grants have a success rate of about 10%
        - MSCA fellowships have a success rate of 15%

        These success rates mean that only about 10-15% of proposals get funded.
        """

        result = await agent.validate_programme_facts(response, "horizon_europe")

        # Should NOT have any incorrect facts about funding rates
        funding_rate_errors = [
            f for f in result.facts_incorrect if "rate:" in f.lower() or "_rate:" in f.lower()
        ]
        assert (
            len(funding_rate_errors) == 0
        ), f"Success rates incorrectly flagged as wrong funding rates: {funding_rate_errors}"

    @pytest.mark.asyncio
    async def test_funding_rate_correctly_validated(self, agent):
        """Test that actual funding rate mentions are correctly validated."""
        # Response with correct funding rates
        response = """
        Horizon Europe funding rates differ by action type:
        - RIA: 100% funding rate (full cost reimbursement)
        - IA: 70% funding rate (70% of eligible costs)
        - CSA: 100% funding rate
        """

        result = await agent.validate_programme_facts(response, "horizon_europe")

        # Should have correct facts about funding rates
        assert result.score >= 0.7, f"Correct funding rates should score >= 0.7, got {result.score}"
        assert (
            len(result.facts_incorrect) == 0
        ), f"Correct funding rates flagged as incorrect: {result.facts_incorrect}"

    @pytest.mark.asyncio
    async def test_incorrect_funding_rate_still_flagged(self, agent):
        """Test that actually incorrect funding rates are still flagged."""
        # Response with incorrect funding rate using a pattern that should be detected
        # "RIA: 70%" should be flagged since RIA funding rate is 100%
        response = """
        Horizon Europe funding rates:
        - RIA: 70% funding rate
        """

        result = await agent.validate_programme_facts(response, "horizon_europe")

        # Should flag the incorrect funding rate
        funding_rate_errors = [f for f in result.facts_incorrect if "RIA_rate" in f]
        # This test verifies that when a funding rate IS mentioned incorrectly, it gets flagged
        assert len(funding_rate_errors) == 1, (
            f"Incorrect RIA funding rate (70% instead of 100%) should be flagged. "
            f"Got errors: {result.facts_incorrect}"
        )

    @pytest.mark.asyncio
    async def test_mixed_success_and_funding_rates(self, agent):
        """Test handling of response with both success and funding rates."""
        response = """
        Horizon Europe RIA projects:
        - Funding rate: 100% of eligible costs covered
        - Success rate: approximately 12% of proposals funded

        For IA projects:
        - Funding rate: up to 70% of eligible costs
        - Success rate: around 10%
        """

        result = await agent.validate_programme_facts(response, "horizon_europe")

        # Should NOT flag success rates as incorrect funding rates
        funding_rate_errors = [
            f for f in result.facts_incorrect if "rate:" in f.lower() or "_rate:" in f.lower()
        ]
        assert (
            len(funding_rate_errors) == 0
        ), f"Mixed response incorrectly flagged: {funding_rate_errors}"

    @pytest.mark.asyncio
    async def test_success_rate_with_various_phrasings(self, agent):
        """Test that various success rate phrasings are not flagged."""
        # Different ways success rates might be mentioned
        test_responses = [
            "RIA projects have a success rate of about 12%",
            "The overall success rate for RIA is 12%",
            "Only 12% of RIA proposals are selected for funding",
            "RIA grants have around 12% success rate",
            "About 12% of RIA applications are awarded funding",
        ]

        for response in test_responses:
            result = await agent.validate_programme_facts(response, "horizon_europe")

            funding_rate_errors = [
                f for f in result.facts_incorrect if "rate:" in f.lower() or "_rate:" in f.lower()
            ]
            assert (
                len(funding_rate_errors) == 0
            ), f"Response '{response}' incorrectly flagged: {funding_rate_errors}"

    @pytest.mark.asyncio
    async def test_comparison_response_not_flagged(self, agent):
        """Test that comparison responses (from scenario results) are not flagged."""
        # This is similar to actual response from programme_comparison scenario
        response = """
        The success rates for Horizon Europe and Erasmus+ differ significantly because they
        fund different types of activities (highly competitive research vs. capacity building
        and mobility). Generally, Erasmus+ has much higher success rates than Horizon Europe.

        Here is a comparison of typical success rate ranges for the main actions relevant
        to university collaboration:

        ## Success Rate Comparison: Horizon Europe vs. Erasmus+

        | Programme | Typical Overall Success Rate | Key Determinant |
        | Horizon Europe RIA | 12% | Highly competitive |
        | Horizon Europe IA | 12% | Highly competitive |
        | Horizon Europe ERC | 10% | Excellence-based |
        | Horizon Europe MSCA | 15% | Fellowship competition |
        | Erasmus+ KA1 | 50%+ | Accreditation helps |
        | Erasmus+ KA2 | 25-35% | Less competitive |
        """

        result = await agent.validate_programme_facts(response, "horizon_europe")

        # Should NOT have any incorrect funding rate facts
        funding_rate_errors = [
            f for f in result.facts_incorrect if "rate:" in f.lower() or "_rate:" in f.lower()
        ]
        assert (
            len(funding_rate_errors) == 0
        ), f"Comparison response incorrectly flagged: {funding_rate_errors}"


class TestProgrammeMentionDetection:
    """Tests for programme mention detection."""

    @pytest.fixture
    def agent(self):
        """Create a CrossProgrammeAgent instance."""
        return CrossProgrammeAgent()

    def test_horizon_europe_detection(self, agent):
        """Test detection of Horizon Europe mentions."""
        response = "Horizon Europe is the EU's key funding programme."
        result = agent.check_programme_mentions(response)
        assert "horizon_europe" in result.programmes_found

    def test_erasmus_detection(self, agent):
        """Test detection of Erasmus+ mentions."""
        response = "Erasmus+ supports student mobility across Europe."
        result = agent.check_programme_mentions(response)
        assert "erasmus_plus" in result.programmes_found

    def test_creative_europe_detection(self, agent):
        """Test detection of Creative Europe mentions."""
        response = "Creative Europe funds cultural and audiovisual projects."
        result = agent.check_programme_mentions(response)
        assert "creative_europe" in result.programmes_found

    def test_multi_programme_detection(self, agent):
        """Test detection of multiple programmes."""
        response = """
        For research, Horizon Europe is ideal. For mobility, consider Erasmus+.
        Creative Europe supports cultural projects.
        """
        result = agent.check_programme_mentions(response)
        assert result.is_multi_programme
        assert len(result.programmes_found) == 3


class TestBudgetValidation:
    """Tests for budget validation."""

    @pytest.fixture
    def agent(self):
        """Create a CrossProgrammeAgent instance."""
        return CrossProgrammeAgent(use_llm=False)

    @pytest.mark.asyncio
    async def test_correct_horizon_budget(self, agent):
        """Test that correct Horizon Europe budget is validated."""
        response = "Horizon Europe has a budget of €95.5 billion for 2021-2027."
        result = await agent.validate_programme_facts(response, "horizon_europe")

        budget_errors = [f for f in result.facts_incorrect if "budget" in f.lower()]
        assert len(budget_errors) == 0

    @pytest.mark.asyncio
    async def test_correct_erasmus_budget(self, agent):
        """Test that correct Erasmus+ budget is validated."""
        response = "Erasmus+ has a budget of €26.2 billion."
        result = await agent.validate_programme_facts(response, "erasmus_plus")

        budget_errors = [f for f in result.facts_incorrect if "budget" in f.lower()]
        assert len(budget_errors) == 0

    @pytest.mark.asyncio
    async def test_correct_creative_europe_budget(self, agent):
        """Test that correct Creative Europe budget is validated."""
        response = "Creative Europe has a budget of €2.44 billion."
        result = await agent.validate_programme_facts(response, "creative_europe")

        budget_errors = [f for f in result.facts_incorrect if "budget" in f.lower()]
        assert len(budget_errors) == 0
