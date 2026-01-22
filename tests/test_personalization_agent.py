"""
Unit tests for the Personalization Agent.

Tests the following functionality:
- Profile extraction from conversation turns
- Context accumulation validation (validate_context_accumulation)
- Personalization validation (validate_personalization)
- Profile usage validation (validate_profile_usage)
- Agent can be imported and instantiated by test runner
"""

import pytest

from tests.agents.personalization_agent import (
    AccumulationResult,
    PersonalizationAgent,
    PersonalizationResult,
    ProfileUsageResult,
    UserProfile,
)


class TestPersonalizationAgentImport:
    """Test that the agent can be imported and instantiated."""

    def test_agent_can_be_imported(self):
        """Test that PersonalizationAgent can be imported."""
        from tests.agents.personalization_agent import PersonalizationAgent

        assert PersonalizationAgent is not None

    def test_agent_can_be_instantiated(self):
        """Test that PersonalizationAgent can be instantiated."""
        agent = PersonalizationAgent()
        assert agent is not None
        assert agent._profile is not None
        assert agent._turns == []
        assert agent._preferences == []

    def test_agent_instantiation_with_parameters(self):
        """Test agent instantiation with custom parameters."""
        agent = PersonalizationAgent(model_name="gemini-2.0-flash", use_llm=False)
        assert agent.model_name == "gemini-2.0-flash"
        assert agent.use_llm is False


class TestProfileExtraction:
    """Test profile extraction from conversation turns."""

    def test_extract_organization_type_university(self):
        """Test extracting university organization type."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="I'm from a university research department",
            response="Great, as a university...",
        )

        assert "organization_type" in turn.extracted_fields
        assert turn.extracted_fields["organization_type"] == "university"
        assert agent.get_profile().organization_type == "university"

    def test_extract_organization_type_sme(self):
        """Test extracting SME organization type."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We're a small SME in the tech sector",
            response="As an SME...",
        )

        assert turn.extracted_fields.get("organization_type") == "sme"

    def test_extract_sector_energy(self):
        """Test extracting energy sector."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We work on hydrogen and renewable energy",
            response="For energy research...",
        )

        assert "sector" in turn.extracted_fields
        assert turn.extracted_fields["sector"] == "energy"

    def test_extract_sector_health(self):
        """Test extracting health sector."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We focus on medical devices and healthcare innovation",
            response="In the health sector...",
        )

        assert turn.extracted_fields.get("sector") == "health"

    def test_extract_country(self):
        """Test extracting country."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We're based in Germany",
            response="For organizations in Germany...",
        )

        assert turn.extracted_fields.get("country") == "DE"

    def test_extract_multiple_countries(self):
        """Test that a country is extracted when multiple are mentioned."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We're based in Portugal but have partners in Spain",
            response="For Portuguese organizations...",
        )

        # Either country should be extracted - depends on pattern order
        assert turn.extracted_fields.get("country") in ["PT", "ES"]

    def test_extract_experience_level_newcomer(self):
        """Test extracting newcomer experience level."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="This is our first time applying for EU funding",
            response="As a first-time applicant...",
        )

        assert turn.extracted_fields.get("experience_level") == "newcomer"

    def test_extract_experience_level_experienced(self):
        """Test extracting experienced level."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We've coordinated many projects before",
            response="Given your experience...",
        )

        assert turn.extracted_fields.get("experience_level") == "experienced"

    def test_extract_organization_size_from_employees(self):
        """Test extracting organization size from employee count."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We have 50 employees",
            response="For a medium-sized organization...",
        )

        # 50 employees = medium (50-249 is medium per EU SME definition)
        assert turn.extracted_fields.get("organization_size") == "medium"

    def test_extract_organization_size_large(self):
        """Test extracting large organization size from employee count."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We have 500 employees",
            response="For a large organization...",
        )

        assert turn.extracted_fields.get("organization_size") == "large"

    def test_extract_target_programme(self):
        """Test extracting target programme."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We want to apply to Horizon Europe",
            response="For Horizon Europe...",
        )

        assert turn.extracted_fields.get("target_programme") == "horizon_europe"

    def test_extract_role_preference_coordinator(self):
        """Test extracting coordinator role preference."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We want to be the coordinator",
            response="As a coordinator...",
        )

        assert turn.extracted_fields.get("role_preference") == "coordinator"

    def test_extract_role_preference_partner(self):
        """Test extracting partner role preference."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We'd like to join as a partner",
            response="As a partner...",
        )

        assert turn.extracted_fields.get("role_preference") == "partner"

    def test_extract_preferences(self):
        """Test extracting user preferences."""
        agent = PersonalizationAgent(use_llm=False)
        turn = agent.add_turn(
            query="We prefer calls with high funding rates and don't want lump sum funding",
            response="Based on your preferences...",
        )

        assert len(turn.preferences) >= 1
        assert len(agent._preferences) >= 1


class TestContextAccumulation:
    """Test context accumulation across conversation turns."""

    def test_accumulate_multiple_turns(self):
        """Test that context accumulates across multiple turns."""
        agent = PersonalizationAgent(use_llm=False)

        agent.add_turn("I'm from a university in Germany", "For German universities...")
        agent.add_turn("We work on renewable energy", "In the energy sector...")
        agent.add_turn("This is our first EU project", "For newcomers...")

        result = agent.validate_context_accumulation()

        assert isinstance(result, AccumulationResult)
        assert result.passed is True
        assert result.total_fields_accumulated >= 3

    def test_profile_builds_over_time(self):
        """Test that profile builds correctly over time."""
        agent = PersonalizationAgent(use_llm=False)

        # First turn - add organization type
        agent.add_turn("We're an SME", "As an SME...")
        profile1 = agent.get_profile()
        assert profile1.organization_type == "sme"
        assert profile1.country is None

        # Second turn - add country
        agent.add_turn("Based in France", "In France...")
        profile2 = agent.get_profile()
        assert profile2.organization_type == "sme"  # Still there
        assert profile2.country == "FR"

        # Third turn - add sector
        agent.add_turn("We focus on AI technology", "For digital innovation...")
        profile3 = agent.get_profile()
        assert profile3.organization_type == "sme"
        assert profile3.country == "FR"
        assert profile3.sector == "digital"

    def test_fields_by_turn_tracking(self):
        """Test that fields are tracked by turn."""
        agent = PersonalizationAgent(use_llm=False)

        agent.add_turn("We're a university", "For universities...")
        agent.add_turn("Based in Spain working on health", "In Spain, health...")

        result = agent.validate_context_accumulation()

        assert 1 in result.fields_by_turn
        assert 2 in result.fields_by_turn
        assert "organization_type" in result.fields_by_turn[1]
        assert "country" in result.fields_by_turn[2] or "sector" in result.fields_by_turn[2]

    def test_profile_completeness_score(self):
        """Test profile completeness calculation."""
        agent = PersonalizationAgent(use_llm=False)

        # Empty profile
        assert agent.get_profile().completeness_score() == 0.0

        # Add some fields
        agent.add_turn("We're a German university", "For German universities...")
        completeness = agent.get_profile().completeness_score()
        assert completeness > 0.0
        assert completeness < 1.0

    def test_empty_accumulation(self):
        """Test accumulation with no turns."""
        agent = PersonalizationAgent(use_llm=False)

        result = agent.validate_context_accumulation()

        assert result.passed is True
        assert result.total_fields_accumulated == 0
        assert "No turns to analyze" in result.reasoning


class TestPersonalizationValidation:
    """Test personalization validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_personalization_with_matching_response(self):
        """Test validation with a personalized response."""
        agent = PersonalizationAgent(use_llm=False)

        # Build profile
        agent.add_turn("We're an SME from Germany", "Noted...")
        agent.add_turn("We work on energy research", "For energy...")

        # Validate personalized response
        response = """
        As an SME from Germany in the energy sector, you have several options.
        For your organization type, we recommend starting as a partner.
        Given your German location, you can coordinate under Horizon Europe.
        """

        result = await agent.validate_personalization(response)

        assert isinstance(result, PersonalizationResult)
        assert result.score > 0.3
        assert len(result.personalization_indicators) > 0

    @pytest.mark.asyncio
    async def test_validate_personalization_with_generic_response(self):
        """Test validation with a generic, non-personalized response."""
        agent = PersonalizationAgent(use_llm=False)

        # Build profile
        agent.add_turn("We're a university from Spain", "Noted...")

        # Validate generic response
        response = """
        EU funding is available through various programmes.
        Organizations can apply through the Funding Portal.
        Please check the official website for more information.
        """

        result = await agent.validate_personalization(response)

        assert isinstance(result, PersonalizationResult)
        # Generic response should have lower score
        assert result.score < 0.8

    @pytest.mark.asyncio
    async def test_validate_personalization_no_profile(self):
        """Test validation with no profile built."""
        agent = PersonalizationAgent(use_llm=False)

        result = await agent.validate_personalization("Any response here.")

        assert result.passed is True
        assert result.score == 1.0
        assert "No profile fields" in result.reasoning


class TestProfileUsageValidation:
    """Test profile usage validation functionality."""

    def test_validate_profile_usage_all_fields_used(self):
        """Test validation when all profile fields are used."""
        agent = PersonalizationAgent(use_llm=False)

        # Build profile
        agent.add_turn("We're a German university", "For German universities...")

        response = """
        For academic institutions in Germany, there are excellent opportunities.
        Universities can apply for research funding through various programmes.
        """

        result = agent.validate_profile_usage(response)

        assert isinstance(result, ProfileUsageResult)
        assert result.usage_score > 0.0

    def test_validate_profile_usage_partial(self):
        """Test validation when only some fields are used."""
        agent = PersonalizationAgent(use_llm=False)

        # Build profile with multiple fields
        agent.add_turn("We're a German university in health research", "Noted...")

        # Response only mentions university
        response = """
        Universities have various funding options available.
        Academic institutions can apply for grants.
        """

        result = agent.validate_profile_usage(response)

        assert result.usage_score < 1.0
        has_university = "university" in [f.lower() for f in result.fields_used]
        assert has_university or len(result.fields_used) > 0

    def test_validate_profile_usage_with_expected_fields(self):
        """Test validation with specific expected fields."""
        agent = PersonalizationAgent(use_llm=False)

        agent.add_turn("We're an SME from Germany", "For SMEs...")

        response = "For small companies in the German market..."

        result = agent.validate_profile_usage(
            response, expected_fields=["organization_type", "country"]
        )

        assert len(result.expected_fields) == 2

    def test_validate_profile_usage_no_expected_fields(self):
        """Test validation with no expected fields."""
        agent = PersonalizationAgent(use_llm=False)

        result = agent.validate_profile_usage("Any response", expected_fields=[])

        assert result.passed is True
        assert result.usage_score == 1.0


class TestValidationHelpers:
    """Test validation helper methods for scenario testing."""

    @pytest.mark.asyncio
    async def test_validate_personalization_applied(self):
        """Test the personalization_applied helper."""
        agent = PersonalizationAgent(use_llm=False)

        agent.add_turn("We're a university", "For universities...")

        response = "For academic institutions and universities, funding is available."

        result = await agent.validate_personalization_applied(response, min_score=0.3)

        assert isinstance(result, bool)

    def test_validate_context_accumulated(self):
        """Test the context_accumulated helper."""
        agent = PersonalizationAgent(use_llm=False)

        # No context yet
        assert agent.validate_context_accumulated(min_fields=1) is False

        # Add some context
        agent.add_turn("We're a German SME", "As a German SME...")

        assert agent.validate_context_accumulated(min_fields=1) is True
        assert agent.validate_context_accumulated(min_fields=2) is True

    def test_validate_profile_used_helper(self):
        """Test the profile_used helper."""
        agent = PersonalizationAgent(use_llm=False)

        agent.add_turn("We're from Germany", "In Germany...")

        response = "For organizations in Germany, there are several options."

        result = agent.validate_profile_used(response, min_usage=0.3)

        assert isinstance(result, bool)


class TestUserProfile:
    """Test UserProfile dataclass functionality."""

    def test_profile_get_filled_fields(self):
        """Test getting filled fields from profile."""
        profile = UserProfile(
            organization_type="university",
            country="DE",
        )

        filled = profile.get_filled_fields()

        assert "organization_type" in filled
        assert "country" in filled
        assert "sector" not in filled

    def test_profile_to_dict(self):
        """Test converting profile to dictionary."""
        profile = UserProfile(
            organization_type="sme",
            sector="energy",
            country="FR",
        )

        profile_dict = profile.to_dict()

        assert profile_dict["organization_type"] == "sme"
        assert profile_dict["sector"] == "energy"
        assert profile_dict["country"] == "FR"
        assert profile_dict["experience_level"] is None

    def test_profile_completeness_score(self):
        """Test profile completeness calculation."""
        # Empty profile
        empty_profile = UserProfile()
        assert empty_profile.completeness_score() == 0.0

        # Partial profile
        partial_profile = UserProfile(
            organization_type="university",
            sector="health",
        )
        score = partial_profile.completeness_score()
        assert 0.0 < score < 1.0


class TestAgentReset:
    """Test agent reset functionality."""

    def test_reset_clears_state(self):
        """Test that reset clears all agent state."""
        agent = PersonalizationAgent(use_llm=False)

        # Build some state
        agent.add_turn("We're a German SME in energy", "For German SMEs...")

        # Verify state exists
        assert len(agent._turns) > 0
        assert agent._profile.organization_type is not None

        # Reset
        agent.reset()

        # Verify state is cleared
        assert agent._turns == []
        assert agent._preferences == []
        assert agent._profile.organization_type is None
        assert agent._profile.country is None


class TestContextSummary:
    """Test context summary generation."""

    def test_get_context_summary(self):
        """Test getting context summary."""
        agent = PersonalizationAgent(use_llm=False)

        agent.add_turn("We're a German university", "For universities...")
        agent.add_turn("We prefer high funding rates", "Based on preferences...")

        summary = agent.get_context_summary()

        assert "profile" in summary
        assert "preferences" in summary
        assert "turns_analyzed" in summary
        assert summary["turns_analyzed"] == 2
        assert "fields_accumulated" in summary
        assert "profile_completeness" in summary

    def test_get_accumulated_profile_dict(self):
        """Test getting accumulated profile as dict."""
        agent = PersonalizationAgent(use_llm=False)

        agent.add_turn("We're an SME from Portugal", "As a Portuguese SME...")

        profile_dict = agent.get_accumulated_profile_dict()

        assert isinstance(profile_dict, dict)
        assert profile_dict["organization_type"] == "sme"
        assert profile_dict["country"] == "PT"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query(self):
        """Test handling of empty query."""
        agent = PersonalizationAgent(use_llm=False)

        turn = agent.add_turn(query="", response="Hello!")

        assert turn.turn_number == 1
        assert turn.extracted_fields == {}

    def test_very_long_query(self):
        """Test handling of very long query."""
        agent = PersonalizationAgent(use_llm=False)

        long_query = "We're a university in Germany working on health " * 100

        turn = agent.add_turn(query=long_query, response="Understood.")

        assert turn.turn_number == 1
        # Should still extract fields
        profile = agent.get_profile()
        assert profile.organization_type is not None or profile.country is not None

    def test_mixed_case_extraction(self):
        """Test extraction with mixed case text."""
        agent = PersonalizationAgent(use_llm=False)

        turn = agent.add_turn(
            query="We're a UNIVERSITY from GERMANY working on ENERGY",
            response="For German universities...",
        )

        assert turn.extracted_fields.get("organization_type") == "university"
        assert turn.extracted_fields.get("country") == "DE"
        assert turn.extracted_fields.get("sector") == "energy"

    def test_multiple_values_same_field(self):
        """Test when multiple values match same field."""
        agent = PersonalizationAgent(use_llm=False)

        # Query mentions both university and SME
        turn = agent.add_turn(
            query="We're a university spin-off SME",
            response="Interesting combination...",
        )

        # Should extract one of them (first match)
        assert turn.extracted_fields.get("organization_type") in ["university", "sme"]

    @pytest.mark.asyncio
    async def test_validation_with_none_profile(self):
        """Test validation when profile fields are None."""
        agent = PersonalizationAgent(use_llm=False)

        # Don't add any turns
        result = await agent.validate_personalization("Any response here")

        assert result.passed is True


class TestProfileFieldDefinitions:
    """Test that profile field definitions are properly configured."""

    def test_all_field_patterns_are_tuples(self):
        """Test that all field patterns are properly formatted."""
        from tests.agents.personalization_agent import PROFILE_FIELDS

        for field_name, config in PROFILE_FIELDS.items():
            assert "patterns" in config, f"Missing patterns in {field_name}"
            assert "weight" in config, f"Missing weight in {field_name}"

            for pattern_tuple in config["patterns"]:
                assert len(pattern_tuple) == 2, f"Invalid pattern tuple in {field_name}"
                pattern, value = pattern_tuple
                assert isinstance(pattern, str), f"Pattern should be string in {field_name}"
                assert isinstance(value, str), f"Value should be string in {field_name}"

    def test_field_weights_in_range(self):
        """Test that all field weights are in valid range."""
        from tests.agents.personalization_agent import PROFILE_FIELDS

        for field_name, config in PROFILE_FIELDS.items():
            weight = config["weight"]
            assert 0.0 <= weight <= 1.0, f"Weight out of range for {field_name}"
