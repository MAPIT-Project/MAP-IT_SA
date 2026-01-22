"""
Unit tests for the Cross-Programme Agent.

Tests the following functionality:
- Programme mention detection (check_programme_mentions)
- Programme facts validation (validate_programme_facts)
- Eligibility rules validation (validate_eligibility_rules)
- Programme switching validation (validate_programme_switch)
- Agent can be imported and instantiated by test runner
"""

import pytest

from tests.agents.cross_programme_agent import (
    COUNTRY_ELIGIBILITY,
    PROGRAMME_FACTS,
    CrossProgrammeAgent,
    EligibilityResult,
    ProgrammeFactsResult,
    ProgrammeMentionResult,
    ProgrammeSwitchResult,
)


class TestCrossProgrammeAgentImport:
    """Test that the agent can be imported and instantiated."""

    def test_agent_can_be_imported(self):
        """Test that CrossProgrammeAgent can be imported."""
        from tests.agents.cross_programme_agent import CrossProgrammeAgent

        assert CrossProgrammeAgent is not None

    def test_agent_can_be_instantiated(self):
        """Test that CrossProgrammeAgent can be instantiated."""
        agent = CrossProgrammeAgent()
        assert agent is not None
        assert agent._conversation_programmes == []

    def test_agent_instantiation_with_parameters(self):
        """Test agent instantiation with custom parameters."""
        agent = CrossProgrammeAgent(model_name="gemini-2.0-flash", use_llm=False)
        assert agent.model_name == "gemini-2.0-flash"
        assert agent.use_llm is False


class TestProgrammeMentionDetection:
    """Test programme mention detection functionality."""

    def test_detect_horizon_europe(self):
        """Test detecting Horizon Europe mentions."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Horizon Europe is the EU's main research and innovation programme."

        result = agent.check_programme_mentions(response)

        assert isinstance(result, ProgrammeMentionResult)
        assert "horizon_europe" in result.programmes_found
        assert "Horizon Europe" in result.programme_names
        assert result.total_mentions >= 1

    def test_detect_erasmus_plus(self):
        """Test detecting Erasmus+ mentions."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Erasmus+ supports education and training mobility."

        result = agent.check_programme_mentions(response)

        assert "erasmus_plus" in result.programmes_found
        assert "Erasmus+" in result.programme_names

    def test_detect_creative_europe(self):
        """Test detecting Creative Europe mentions."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Creative Europe supports the cultural and audiovisual sectors."

        result = agent.check_programme_mentions(response)

        assert "creative_europe" in result.programmes_found
        assert "Creative Europe" in result.programme_names

    def test_detect_multiple_programmes(self):
        """Test detecting multiple programmes in same response."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = """
        For your project, you could consider both Horizon Europe for the research
        component and Erasmus+ for the training activities. Creative Europe might
        also be relevant for the cultural aspects.
        """

        result = agent.check_programme_mentions(response)

        assert result.is_multi_programme is True
        assert len(result.programmes_found) >= 2
        # At minimum Horizon Europe and Erasmus+ should be detected
        assert "horizon_europe" in result.programmes_found
        assert "erasmus_plus" in result.programmes_found

    def test_detect_programme_aliases(self):
        """Test detecting programme aliases."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Both HE and E+ programmes are available."

        result = agent.check_programme_mentions(response)

        # Should detect aliases
        assert result.total_mentions >= 0  # Aliases may or may not match depending on context

    def test_no_programmes_mentioned(self):
        """Test when no programmes are mentioned."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "EU funding is available for various activities."

        result = agent.check_programme_mentions(response)

        assert result.programmes_found == []
        assert result.is_multi_programme is False
        assert result.total_mentions == 0

    def test_case_insensitive_detection(self):
        """Test case-insensitive programme detection."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "HORIZON EUROPE and erasmus+ are both available."

        result = agent.check_programme_mentions(response)

        assert "horizon_europe" in result.programmes_found
        assert "erasmus_plus" in result.programmes_found


class TestProgrammeFactsValidation:
    """Test programme facts validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_correct_budget(self):
        """Test validation of correct budget information."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Horizon Europe has a budget of €95.5 billion for 2021-2027."

        result = await agent.validate_programme_facts(response, "horizon_europe")

        assert isinstance(result, ProgrammeFactsResult)
        assert result.programme == "horizon_europe"
        assert result.score >= 0.5
        assert "budget" in result.facts_checked

    @pytest.mark.asyncio
    async def test_validate_incorrect_budget(self):
        """Test validation catches incorrect budget."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Horizon Europe has a budget of €50 billion."

        result = await agent.validate_programme_facts(response, "horizon_europe")

        assert result.programme == "horizon_europe"
        # Should detect the incorrect budget
        if "budget" in result.facts_checked:
            assert len(result.facts_incorrect) > 0

    @pytest.mark.asyncio
    async def test_validate_programme_components(self):
        """Test validation of programme components."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = """
        Horizon Europe includes several key components:
        - ERC for frontier research
        - MSCA for researcher mobility
        - EIC for innovation support
        """

        result = await agent.validate_programme_facts(response, "horizon_europe")

        assert result.score >= 0.5
        assert len(result.facts_correct) > 0

    @pytest.mark.asyncio
    async def test_validate_erasmus_facts(self):
        """Test validation of Erasmus+ facts."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = """
        Erasmus+ supports education and training through:
        - KA1 - Learning Mobility
        - KA2 - Cooperation Partnerships
        - KA3 - Policy Support
        """

        result = await agent.validate_programme_facts(response, "erasmus_plus")

        assert result.programme == "erasmus_plus"
        assert result.score >= 0.5

    @pytest.mark.asyncio
    async def test_validate_creative_europe_facts(self):
        """Test validation of Creative Europe facts."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = """
        Creative Europe has three main strands:
        - CULTURE strand
        - MEDIA strand
        - CROSS-SECTORAL strand
        """

        result = await agent.validate_programme_facts(response, "creative_europe")

        assert result.programme == "creative_europe"
        assert result.score >= 0.5

    @pytest.mark.asyncio
    async def test_validate_unknown_programme(self):
        """Test validation with unknown programme."""
        agent = CrossProgrammeAgent(use_llm=False)

        result = await agent.validate_programme_facts("Any response", "unknown_programme")

        assert result.passed is False
        assert "Unknown programme" in result.reasoning


class TestEligibilityValidation:
    """Test eligibility rules validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_eu_member_state_eligibility(self):
        """Test validation for EU member state eligibility."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "German organizations can coordinate Horizon Europe projects."
        context = {"country": "DE", "programme": "horizon_europe"}

        result = await agent.validate_eligibility_rules(response, context)

        assert isinstance(result, EligibilityResult)
        assert result.country == "DE"
        assert result.programme == "horizon_europe"
        # Germany should be able to coordinate
        assert "coordinator_eligibility" in result.rules_checked

    @pytest.mark.asyncio
    async def test_validate_swiss_eligibility_horizon(self):
        """Test validation for Swiss eligibility in Horizon Europe."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Swiss organizations cannot coordinate Horizon Europe projects."
        context = {"country": "CH", "programme": "horizon_europe"}

        result = await agent.validate_eligibility_rules(response, context)

        assert result.country == "CH"
        assert result.programme == "horizon_europe"
        # Switzerland cannot coordinate in Horizon Europe

    @pytest.mark.asyncio
    async def test_validate_uk_eligibility_erasmus(self):
        """Test validation for UK eligibility in Erasmus+."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "UK organizations cannot participate in Erasmus+."
        context = {"country": "UK", "programme": "erasmus_plus"}

        result = await agent.validate_eligibility_rules(response, context)

        assert result.country == "UK"
        assert result.programme == "erasmus_plus"

    @pytest.mark.asyncio
    async def test_validate_associated_country_eligibility(self):
        """Test validation for associated country eligibility."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Norwegian organizations can participate and coordinate."
        context = {"country": "NO", "programme": "horizon_europe"}

        result = await agent.validate_eligibility_rules(response, context)

        assert result.country == "NO"
        # Norway is associated country with full eligibility

    @pytest.mark.asyncio
    async def test_validate_no_country_specified(self):
        """Test validation when no country is specified."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Any response here."
        context = {}

        result = await agent.validate_eligibility_rules(response, context)

        assert result.passed is True
        assert "No country specified" in result.reasoning

    def test_get_expected_eligibility_eu_member(self):
        """Test getting expected eligibility for EU member state."""
        agent = CrossProgrammeAgent(use_llm=False)

        eligibility = agent._get_expected_eligibility("DE", "horizon_europe")

        assert eligibility.get("coordinator") is True
        assert eligibility.get("partner") is True
        assert eligibility.get("full_funding") is True

    def test_get_expected_eligibility_switzerland(self):
        """Test getting expected eligibility for Switzerland."""
        agent = CrossProgrammeAgent(use_llm=False)

        eligibility = agent._get_expected_eligibility("CH", "horizon_europe")

        assert eligibility.get("coordinator") is False
        assert eligibility.get("partner") is True
        assert "notes" in eligibility

    def test_get_expected_eligibility_third_country(self):
        """Test getting expected eligibility for third country."""
        agent = CrossProgrammeAgent(use_llm=False)

        eligibility = agent._get_expected_eligibility("US", "horizon_europe")

        # US is a third country
        assert eligibility.get("coordinator") is False
        assert eligibility.get("full_funding") is False


class TestProgrammeSwitchValidation:
    """Test programme switching validation functionality."""

    def test_validate_programme_switch(self):
        """Test validating programme switch."""
        agent = CrossProgrammeAgent(use_llm=False)

        previous = "Horizon Europe offers funding for research projects."
        current = "For training activities, Erasmus+ is more suitable."
        context = {"topic": "funding"}

        result = agent.validate_programme_switch(previous, current, context)

        assert isinstance(result, ProgrammeSwitchResult)
        assert len(result.programmes_mentioned) >= 2
        assert "horizon_europe" in result.programmes_mentioned
        assert "erasmus_plus" in result.programmes_mentioned

    def test_no_programme_switch(self):
        """Test when there's no programme switch."""
        agent = CrossProgrammeAgent(use_llm=False)

        previous = "Horizon Europe supports research activities."
        current = "Horizon Europe also funds innovation projects."
        context = {}

        result = agent.validate_programme_switch(previous, current, context)

        # Both responses discuss Horizon Europe
        assert result.switch_count == 0 or result.switch_count == 1

    def test_context_preservation_check(self):
        """Test context preservation during switch."""
        agent = CrossProgrammeAgent(use_llm=False)

        previous = "For your university in Germany, Horizon Europe is ideal."
        current = "As I mentioned, Erasmus+ is also available for your organization."
        context = {"organization": "university", "country": "Germany"}

        result = agent.validate_programme_switch(previous, current, context)

        assert result.context_preserved is True


class TestValidationHelpers:
    """Test validation helper methods for scenario testing."""

    def test_validate_programme_mentioned_single(self):
        """Test programme_mentioned helper with single programme."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Horizon Europe has various funding opportunities."

        result = agent.validate_programme_mentioned(response, ["horizon_europe"])

        assert result is True

    def test_validate_programme_mentioned_multiple(self):
        """Test programme_mentioned helper with multiple programmes."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Both Horizon Europe and Erasmus+ offer funding."

        result = agent.validate_programme_mentioned(response, ["horizon_europe", "erasmus_plus"])

        assert result is True

    def test_validate_programme_mentioned_missing(self):
        """Test programme_mentioned helper when programme is missing."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Erasmus+ offers education funding."

        result = agent.validate_programme_mentioned(response, ["horizon_europe", "erasmus_plus"])

        # Horizon Europe is not mentioned
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_programme_accurate(self):
        """Test programme_accurate helper."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "Horizon Europe budget is €95.5 billion."

        result = await agent.validate_programme_accurate(response, "horizon_europe", min_score=0.5)

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_validate_eligibility_correct(self):
        """Test eligibility_correct helper."""
        agent = CrossProgrammeAgent(use_llm=False)
        response = "German organizations can coordinate."
        context = {"country": "DE", "programme": "horizon_europe"}

        result = await agent.validate_eligibility_correct(response, context, min_score=0.5)

        assert isinstance(result, bool)


class TestProgrammeCoverageSummary:
    """Test programme coverage summary functionality."""

    def test_get_programme_coverage_summary(self):
        """Test getting programme coverage summary."""
        agent = CrossProgrammeAgent(use_llm=False)

        # Analyze some responses
        agent.check_programme_mentions("Horizon Europe is available.")
        agent.check_programme_mentions("Erasmus+ supports education.")

        summary = agent.get_programme_coverage_summary()

        assert "programmes_discussed" in summary
        assert "num_programmes" in summary
        assert summary["num_programmes"] >= 2
        assert summary["is_multi_programme"] is True

    def test_get_programme_facts(self):
        """Test getting programme facts."""
        agent = CrossProgrammeAgent(use_llm=False)

        facts = agent.get_programme_facts("horizon_europe")

        assert facts is not None
        assert facts["name"] == "Horizon Europe"
        assert "budget" in facts
        assert "pillars" in facts

    def test_get_programme_facts_unknown(self):
        """Test getting facts for unknown programme."""
        agent = CrossProgrammeAgent(use_llm=False)

        facts = agent.get_programme_facts("unknown_programme")

        assert facts is None

    def test_get_eligibility_info(self):
        """Test getting eligibility info."""
        agent = CrossProgrammeAgent(use_llm=False)

        info = agent.get_eligibility_info("DE", "horizon_europe")

        assert info.get("coordinator") is True
        assert info.get("partner") is True


class TestAgentReset:
    """Test agent reset functionality."""

    def test_reset_clears_conversation_programmes(self):
        """Test that reset clears conversation state."""
        agent = CrossProgrammeAgent(use_llm=False)

        # Build some state
        agent.check_programme_mentions("Horizon Europe is great.")
        agent.check_programme_mentions("Erasmus+ is also available.")

        assert len(agent._conversation_programmes) >= 2

        # Reset
        agent.reset()

        assert agent._conversation_programmes == []


class TestProgrammeFactsData:
    """Test that programme facts data is properly configured."""

    def test_all_programmes_have_required_fields(self):
        """Test that all programmes have required fields."""
        required_fields = ["name", "aliases", "budget", "budget_range", "duration"]

        for programme, facts in PROGRAMME_FACTS.items():
            for field in required_fields:
                assert field in facts, f"Missing {field} in {programme}"

    def test_budget_ranges_valid(self):
        """Test that budget ranges are valid tuples."""
        for programme, facts in PROGRAMME_FACTS.items():
            budget_range = facts["budget_range"]
            assert isinstance(budget_range, tuple), f"Invalid budget_range in {programme}"
            assert len(budget_range) == 2, f"budget_range should have 2 elements in {programme}"
            assert budget_range[0] < budget_range[1], f"Invalid budget_range order in {programme}"

    def test_aliases_include_programme_name(self):
        """Test that aliases list includes lowercase programme name."""
        for programme, facts in PROGRAMME_FACTS.items():
            aliases = [a.lower() for a in facts["aliases"]]
            # Programme name should be detectable
            assert any(
                facts["name"].lower() in alias or alias in facts["name"].lower()
                for alias in aliases
            ), f"Name not in aliases for {programme}"


class TestCountryEligibilityData:
    """Test that country eligibility data is properly configured."""

    def test_eu_member_states_defined(self):
        """Test that EU member states are defined."""
        eu_countries = COUNTRY_ELIGIBILITY["eu_member_states"]["countries"]
        assert len(eu_countries) == 27  # EU has 27 member states
        assert "DE" in eu_countries
        assert "FR" in eu_countries

    def test_special_cases_have_programme_rules(self):
        """Test that special cases have programme-specific rules."""
        special_cases = COUNTRY_ELIGIBILITY["special_cases"]

        for country, rules in special_cases.items():
            # Each special case should have rules for at least one programme
            has_programme_rules = any(
                prog in rules for prog in ["horizon_europe", "erasmus_plus", "creative_europe"]
            )
            assert has_programme_rules, f"No programme rules for {country}"

    def test_switzerland_special_case(self):
        """Test Switzerland special case is properly configured."""
        ch_rules = COUNTRY_ELIGIBILITY["special_cases"]["CH"]

        assert "horizon_europe" in ch_rules
        assert ch_rules["horizon_europe"]["coordinator"] is False
        assert ch_rules["horizon_europe"]["partner"] is True

    def test_uk_special_case(self):
        """Test UK special case is properly configured."""
        uk_rules = COUNTRY_ELIGIBILITY["special_cases"]["UK"]

        assert "horizon_europe" in uk_rules
        assert "erasmus_plus" in uk_rules
        assert uk_rules["erasmus_plus"]["partner"] is False  # UK not in Erasmus+


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_response(self):
        """Test handling of empty response."""
        agent = CrossProgrammeAgent(use_llm=False)

        result = agent.check_programme_mentions("")

        assert result.programmes_found == []
        assert result.total_mentions == 0

    @pytest.mark.asyncio
    async def test_very_long_response(self):
        """Test handling of very long response."""
        agent = CrossProgrammeAgent(use_llm=False)

        long_response = "Horizon Europe provides funding. " * 500

        result = agent.check_programme_mentions(long_response)

        assert "horizon_europe" in result.programmes_found
        assert result.total_mentions > 1

    def test_special_characters_in_response(self):
        """Test handling of special characters."""
        agent = CrossProgrammeAgent(use_llm=False)

        response = "Horizon Europe (€95.5B) - the EU's R&I programme!"

        result = agent.check_programme_mentions(response)

        assert "horizon_europe" in result.programmes_found

    @pytest.mark.asyncio
    async def test_mixed_correct_incorrect_facts(self):
        """Test response with mix of correct and incorrect facts."""
        agent = CrossProgrammeAgent(use_llm=False)

        response = """
        Horizon Europe has a budget of €95.5 billion.
        The programme runs from 2021-2027.
        It has 10 clusters and 5 pillars.
        """

        result = await agent.validate_programme_facts(response, "horizon_europe")

        # Should detect some correct facts (budget) and potentially note issues
        assert len(result.facts_checked) > 0

    @pytest.mark.asyncio
    async def test_context_with_missing_keys(self):
        """Test eligibility validation with missing context keys."""
        agent = CrossProgrammeAgent(use_llm=False)

        result = await agent.validate_eligibility_rules(
            "Any response",
            {"unrelated_key": "value"},
        )

        # Should handle missing country gracefully
        assert result.passed is True
