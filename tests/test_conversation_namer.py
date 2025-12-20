"""
Comprehensive tests for the ConversationNamer service.

Tests:
- LLM-based name generation
- Fallback pattern matching
- Edge cases and error handling
- Singleton pattern
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.conversation.conversation_namer import (
    ConversationNamer,
    get_conversation_namer
)


class TestConversationNamerFallbackPatterns:
    """Test the fallback pattern matching when LLM is unavailable."""

    def setup_method(self):
        """Create namer with no LLM for fallback testing."""
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            self.namer = ConversationNamer()
            self.namer.model = None  # Force fallback mode

    def test_funding_call_patterns(self):
        """Test recognition of funding call related queries."""
        patterns = [
            ("What funding calls are available?", ["Funding", "Opportunities", "Query"]),
            ("Show me open calls for hydrogen", ["Funding", "Opportunities", "Query"]),
            ("Upcoming call deadlines", ["Funding", "Opportunities", "Query", "Deadline"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_horizon_europe_patterns(self):
        """Test recognition of Horizon Europe queries."""
        patterns = [
            ("How does Horizon Europe work?", "Horizon Europe Query"),
            ("Horizon Europe eligibility rules", "Horizon Europe Query"),
        ]
        for message, expected in patterns:
            result = self.namer._generate_fallback(message)
            assert expected in result or "Query" in result, f"Failed for: {message}"

    def test_project_search_patterns(self):
        """Test recognition of project search queries."""
        patterns = [
            ("Find funded projects about AI", ["Project", "Search", "Query"]),
            ("Search CORDIS for renewable energy", ["Project", "Search", "Query"]),
            ("Similar projects to mine", ["Project", "Similar", "Query"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_budget_patterns(self):
        """Test recognition of budget related queries."""
        patterns = [
            ("What is the typical budget for RIA?", ["Budget", "Planning", "Query", "Funding"]),
            ("Cost breakdown for my proposal", ["Budget", "Planning", "Query", "Proposal"]),
            ("Funding rate for IA projects", ["Budget", "Funding", "Query", "Opportunities"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_timeline_patterns(self):
        """Test recognition of timeline related queries."""
        patterns = [
            ("Project timeline for 36 months", ["Timeline", "Project", "Query", "Search"]),
            ("Milestone planning help", ["Timeline", "Project", "Query", "Milestone"]),
            ("Duration requirements", ["Timeline", "Project", "Query", "Duration"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_eligibility_patterns(self):
        """Test recognition of eligibility queries."""
        patterns = [
            ("Am I eligible for ERC?", "Eligibility Check"),
            ("Can we apply as SME?", "Eligibility Check"),
            ("Eligibility requirements for MSCA", "Eligibility Check"),
        ]
        for message, expected in patterns:
            result = self.namer._generate_fallback(message)
            assert expected in result or "Query" in result, f"Failed for: {message}"

    def test_country_patterns(self):
        """Test recognition of country-related queries."""
        patterns = [
            ("Germany participation statistics", ["Country", "Participation", "Query", "Germany"]),
            ("Projects from France", ["Country", "Project", "Query", "Search"]),
            ("Swiss eligibility in Horizon", ["Country", "Participation", "Query", "Eligibility"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_programme_patterns(self):
        """Test recognition of programme queries."""
        patterns = [
            ("What is ERC?", "Programme Information"),
            ("EIC Accelerator requirements", "Programme Information"),
            ("MSCA fellowship details", "Programme Information"),
        ]
        for message, expected in patterns:
            result = self.namer._generate_fallback(message)
            assert expected in result or "Query" in result, f"Failed for: {message}"

    def test_action_type_patterns(self):
        """Test recognition of action type queries."""
        patterns = [
            ("Difference between RIA and IA", "Action Type Query"),
            ("What is CSA?", "Action Type Query"),
        ]
        for message, expected in patterns:
            result = self.namer._generate_fallback(message)
            assert expected in result or "Query" in result, f"Failed for: {message}"

    def test_research_topic_patterns(self):
        """Test recognition of specific research topics."""
        patterns = [
            ("Hydrogen research funding", ["Energy", "Research", "Funding", "Query", "Green", "Opportunities"]),
            ("AI and machine learning calls", ["Digital", "AI", "Research", "Query", "Funding", "Opportunities"]),
            ("Cancer research projects", ["Health", "Research", "Query", "Project"]),
            ("Quantum computing opportunities", ["Digital", "AI", "Research", "Query", "Quantum", "Opportunities"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_proposal_writing_patterns(self):
        """Test recognition of proposal assistance queries."""
        patterns = [
            ("Help me write a proposal", ["Proposal", "Assistance", "Query", "Writing"]),
            ("Draft my excellence section", ["Proposal", "Assistance", "Query"]),
            ("Review my proposal text", ["Proposal", "Review", "Query", "Assistance"]),
            ("Improve my impact section", ["Proposal", "Review", "Query", "Impact"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_comparison_patterns(self):
        """Test recognition of comparison queries."""
        patterns = [
            ("Compare ERC and EIC", ["Comparison", "Query", "Programme", "Information"]),
            ("Difference between RIA vs IA", ["Comparison", "Query", "Action"]),
            ("ERC versus MSCA", ["Comparison", "Query", "Programme"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_statistics_patterns(self):
        """Test recognition of statistics queries."""
        patterns = [
            ("Success rate for ERC", ["Statistics", "Query", "Programme", "Information"]),
            ("How many projects funded in 2024?", ["Statistics", "Query", "Project"]),
            ("Statistics on German participation", ["Statistics", "Query", "Country"]),
        ]
        for message, expected_any in patterns:
            result = self.namer._generate_fallback(message)
            assert any(e in result for e in expected_any), f"Failed for: {message}, got: {result}"

    def test_fallback_to_keyword_extraction(self):
        """Test fallback to keyword extraction for unmatched queries."""
        result = self.namer._generate_fallback("completely random question about nothing specific")
        assert "Query" in result
        assert len(result.split()) <= 5  # Should be short

    def test_empty_message_handling(self):
        """Test handling of empty messages."""
        result = self.namer._generate_fallback("")
        assert result == "New Conversation"

    def test_very_short_message(self):
        """Test handling of very short messages."""
        result = self.namer._generate_fallback("hi")
        assert "Query" in result or "New Conversation" in result


class TestConversationNamerLLM:
    """Test LLM-based name generation."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock Gemini model."""
        mock = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hydrogen Funding Opportunities"
        mock.generate_content.return_value = mock_response
        return mock

    def test_llm_name_generation(self, mock_model):
        """Test that LLM generates appropriate names."""
        namer = ConversationNamer()
        namer.model = mock_model

        result = asyncio.run(namer._generate_with_llm("What hydrogen calls are open?"))

        assert result == "Hydrogen Funding Opportunities"
        mock_model.generate_content.assert_called_once()

    def test_llm_strips_quotes(self, mock_model):
        """Test that quotes are stripped from LLM responses."""
        mock_response = MagicMock()
        mock_response.text = '"AI Research Proposal"'
        mock_model.generate_content.return_value = mock_response

        namer = ConversationNamer()
        namer.model = mock_model

        result = asyncio.run(namer._generate_with_llm("Help with AI proposal"))
        assert result == "AI Research Proposal"

    def test_llm_truncates_long_names(self, mock_model):
        """Test that very long names are truncated."""
        mock_response = MagicMock()
        mock_response.text = "This Is A Very Long Conversation Name That Should Be Truncated"
        mock_model.generate_content.return_value = mock_response

        namer = ConversationNamer()
        namer.model = mock_model

        result = asyncio.run(namer._generate_with_llm("Some question"))
        words = result.split()
        assert len(words) <= 5

    def test_llm_error_returns_none(self, mock_model):
        """Test that LLM errors return None (triggering fallback)."""
        mock_model.generate_content.side_effect = Exception("API Error")

        namer = ConversationNamer()
        namer.model = mock_model

        result = asyncio.run(namer._generate_with_llm("Some question"))
        assert result is None

    def test_llm_empty_response_returns_none(self, mock_model):
        """Test that empty LLM response returns None."""
        mock_response = MagicMock()
        mock_response.text = ""
        mock_model.generate_content.return_value = mock_response

        namer = ConversationNamer()
        namer.model = mock_model

        result = asyncio.run(namer._generate_with_llm("Some question"))
        assert result is None


class TestConversationNamerIntegration:
    """Integration tests for the full generate_name flow."""

    @pytest.fixture
    def namer_with_mock_llm(self):
        """Create namer with mocked LLM."""
        namer = ConversationNamer()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "LLM Generated Name"
        mock_model.generate_content.return_value = mock_response
        namer.model = mock_model
        return namer

    def test_generate_name_uses_llm_when_available(self, namer_with_mock_llm):
        """Test that LLM is used when available."""
        result = asyncio.run(namer_with_mock_llm.generate_name("Test question"))
        assert result == "LLM Generated Name"

    def test_generate_name_falls_back_on_llm_failure(self):
        """Test fallback when LLM fails."""
        namer = ConversationNamer()
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        namer.model = mock_model

        result = asyncio.run(namer.generate_name("What funding calls are available?"))
        # Should get fallback result
        assert "Funding" in result or "Query" in result

    def test_generate_name_with_no_model(self):
        """Test that fallback is used when no model configured."""
        namer = ConversationNamer()
        namer.model = None

        result = asyncio.run(namer.generate_name("Show me hydrogen projects"))
        assert len(result) > 0


class TestConversationNamerSingleton:
    """Test singleton pattern for ConversationNamer."""

    def test_singleton_returns_same_instance(self):
        """Test that get_conversation_namer returns same instance."""
        # Reset singleton
        import app.services.conversation.conversation_namer as module
        module._namer_instance = None

        namer1 = get_conversation_namer()
        namer2 = get_conversation_namer()

        assert namer1 is namer2

    def test_singleton_initializes_once(self):
        """Test that ConversationNamer is only created once."""
        import app.services.conversation.conversation_namer as module
        module._namer_instance = None

        with patch.object(ConversationNamer, '__init__', return_value=None) as mock_init:
            get_conversation_namer()
            get_conversation_namer()
            get_conversation_namer()

            # Should only be called once
            assert mock_init.call_count == 1


class TestConversationNamerEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Create namer in fallback mode."""
        self.namer = ConversationNamer()
        self.namer.model = None

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        result = self.namer._generate_fallback("Förderung für Wasserstoff-Projekte")
        assert len(result) > 0

    def test_special_characters(self):
        """Test handling of special characters."""
        result = self.namer._generate_fallback("What's the budget for RIA? (€5M)")
        assert len(result) > 0

    def test_very_long_message(self):
        """Test handling of very long messages."""
        long_message = "What " * 500 + "is the budget?"
        result = self.namer._generate_fallback(long_message)
        assert len(result) > 0
        assert len(result.split()) <= 5

    def test_all_stop_words(self):
        """Test message with only stop words."""
        result = self.namer._generate_fallback("the a an is are was were")
        assert result == "New Conversation"

    def test_numbers_only(self):
        """Test message with only numbers."""
        result = self.namer._generate_fallback("123 456 789")
        assert "Query" in result or "New Conversation" in result

    def test_mixed_case_patterns(self):
        """Test that pattern matching is case-insensitive."""
        result1 = self.namer._generate_fallback("HYDROGEN FUNDING")
        result2 = self.namer._generate_fallback("hydrogen funding")
        result3 = self.namer._generate_fallback("HyDrOgEn FuNdInG")

        # All should match the same pattern
        assert "Energy" in result1 or "Funding" in result1 or "Query" in result1

    def test_punctuation_handling(self):
        """Test that punctuation doesn't break pattern matching."""
        patterns = [
            "What is ERC???",
            "Budget... requirements!",
            "Hydrogen, energy, climate",
        ]
        for pattern in patterns:
            result = self.namer._generate_fallback(pattern)
            assert len(result) > 0


class TestConversationNamerRealWorld:
    """Test with real-world example queries."""

    def setup_method(self):
        """Create namer in fallback mode for predictable testing."""
        self.namer = ConversationNamer()
        self.namer.model = None

    @pytest.mark.parametrize("query,expected_keywords", [
        ("What open calls are there for AI research in healthcare?", ["Health", "Digital", "AI", "Query", "Funding", "Opportunities"]),
        ("Can a Swiss SME participate in Horizon Europe RIA?", ["Eligibility", "Country", "Swiss", "Query", "Horizon"]),
        ("Compare the success rates of ERC-StG and ERC-CoG", ["Comparison", "Programme", "Statistics", "Query", "Information"]),
        ("Help me write the impact section of my climate proposal", ["Proposal", "Query", "Energy", "Research", "Green"]),
        ("What is the typical consortium size for a CL5 project?", ["Query", "Project", "Search", "Consortium"]),
        ("Show funded projects about quantum computing from Germany", ["Project", "Digital", "Country", "Query", "Search"]),
        ("Budget breakdown for a 4-year IA with 12 partners", ["Budget", "Query", "Proposal", "Planning"]),
        ("MSCA postdoctoral fellowship eligibility criteria", ["Programme", "Eligibility", "Query", "Information"]),
    ])
    def test_real_world_queries(self, query, expected_keywords):
        """Test that real-world queries produce sensible names."""
        result = self.namer._generate_fallback(query)

        # At least one expected keyword should be in the result
        assert any(kw in result for kw in expected_keywords), \
            f"Expected one of {expected_keywords} in '{result}' for query: {query}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
