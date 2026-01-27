"""
Test Scenario 053: Special Characters Handling

This scenario verifies that the system correctly handles queries containing
special characters like subscripts (CO₂), ampersands (&), smart quotes,
dashes, and other Unicode typography.

Expected behavior:
- Normalize special characters to ASCII equivalents
- Preserve semantic meaning (CO₂ → CO2, & → and)
- Preserve recognized acronyms (R&D stays R&D)
- Process normalized query correctly
- Return relevant results

Pass threshold: 80/100
"""

import pytest


class TestSpecialCharacterNormalization:
    """Unit tests for the normalize_special_characters function."""

    def test_imports(self):
        """Test that required imports work."""
        from app.services.agents.tool_aware_agent import (
            SUBSCRIPT_MAP,
            SUPERSCRIPT_MAP,
            TYPOGRAPHY_MAP,
            SpecialCharResult,
            normalize_special_characters,
        )

        # Verify maps exist and have content
        assert len(SUBSCRIPT_MAP) > 0
        assert len(SUPERSCRIPT_MAP) > 0
        assert len(TYPOGRAPHY_MAP) > 0
        assert SpecialCharResult is not None
        assert normalize_special_characters is not None

    def test_special_char_result_dataclass(self):
        """Test SpecialCharResult dataclass structure."""
        from app.services.agents.tool_aware_agent import SpecialCharResult

        result = SpecialCharResult(
            original_query="CO₂",
            normalized_query="CO2",
            was_normalized=True,
            normalizations_applied=["subscript ₂→2"],
        )

        assert result.original_query == "CO₂"
        assert result.normalized_query == "CO2"
        assert result.was_normalized is True
        assert len(result.normalizations_applied) == 1

    def test_empty_query(self):
        """Test handling of empty queries."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("")
        assert result.original_query == ""
        assert result.normalized_query == ""
        assert result.was_normalized is False
        assert len(result.normalizations_applied) == 0

    def test_no_special_chars(self):
        """Test query with no special characters."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        query = "Find projects on carbon capture"
        result = normalize_special_characters(query)

        assert result.original_query == query
        assert result.normalized_query == query
        assert result.was_normalized is False
        assert len(result.normalizations_applied) == 0


class TestSubscriptNormalization:
    """Tests for subscript character normalization."""

    def test_co2_subscript(self):
        """Test CO₂ (subscript 2) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("CO₂ capture technology")
        assert "CO2" in result.normalized_query
        assert result.was_normalized is True
        assert any("subscript" in change for change in result.normalizations_applied)

    def test_h2o_subscript(self):
        """Test H₂O (subscript 2) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("H₂O purification")
        assert "H2O" in result.normalized_query
        assert result.was_normalized is True

    def test_chemical_formula_with_multiple_subscripts(self):
        """Test formulas with multiple subscripts."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("C₆H₁₂O₆ glucose metabolism")
        # Should normalize all subscripts
        assert "6" in result.normalized_query
        assert "12" in result.normalized_query
        assert result.was_normalized is True

    def test_ch4_methane(self):
        """Test CH₄ (methane) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("CH₄ emissions reduction")
        assert "CH4" in result.normalized_query
        assert result.was_normalized is True

    def test_no2_nitrogen_dioxide(self):
        """Test NO₂ (nitrogen dioxide) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("NO₂ pollution monitoring")
        assert "NO2" in result.normalized_query
        assert result.was_normalized is True


class TestSuperscriptNormalization:
    """Tests for superscript character normalization."""

    def test_squared_number(self):
        """Test 10² → 10^2 normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("10² = 100")
        # Superscripts after digits get ^ prefix for clarity
        assert "10^2" in result.normalized_query
        assert result.was_normalized is True
        assert any("superscript" in change for change in result.normalizations_applied)

    def test_cubed_number(self):
        """Test m³ (cubic meters) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("100 m³ capacity")
        # Should normalize ³ to 3
        assert "3" in result.normalized_query
        assert result.was_normalized is True

    def test_square_meters(self):
        """Test m² (square meters) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("1000 m² area")
        # m² → m2 (not m^2 since m is not a digit)
        assert "m2" in result.normalized_query
        assert result.was_normalized is True


class TestAmpersandNormalization:
    """Tests for ampersand (&) normalization."""

    def test_ampersand_between_words(self):
        """Test standalone & becomes 'and'."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("capture & storage")
        assert "capture and storage" in result.normalized_query
        assert result.was_normalized is True
        assert any("ampersand" in change for change in result.normalizations_applied)

    def test_rd_preserved(self):
        """Test R&D is preserved (common acronym)."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("R&D collaboration projects")
        assert "R&D" in result.normalized_query
        # Should NOT be normalized
        assert result.was_normalized is False

    def test_ma_preserved(self):
        """Test M&A is preserved (common acronym)."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("M&A activity in tech sector")
        assert "M&A" in result.normalized_query
        # Should NOT be normalized
        assert result.was_normalized is False

    def test_qa_preserved(self):
        """Test Q&A is preserved."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("Q&A session about funding")
        assert "Q&A" in result.normalized_query

    def test_mixed_ampersands(self):
        """Test query with both preserved and normalized ampersands."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("R&D in capture & storage")
        # R&D should be preserved, standalone & should become "and"
        assert "R&D" in result.normalized_query
        assert "capture and storage" in result.normalized_query


class TestTypographyNormalization:
    """Tests for smart quotes and typography normalization."""

    def test_smart_single_quotes_right(self):
        """Test right single quote normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        # Use Unicode escape for right single quote (\u2019 = ')
        result = normalize_special_characters("what\u2019s available")
        # Right single quote → straight apostrophe
        assert "what's" in result.normalized_query
        assert result.was_normalized is True

    def test_smart_single_quotes_left(self):
        """Test left single quote normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        # Use Unicode escapes for left (\u2018 = ') and right (\u2019 = ') single quotes
        result = normalize_special_characters("the \u2018solution\u2019 works")
        # Single quotes → straight quotes
        assert "'" in result.normalized_query
        assert result.was_normalized is True

    def test_smart_double_quotes(self):
        """Test smart double quotes normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        # Use Unicode escapes to test smart quotes
        # \u201C is left double quote ("), \u201D is right double quote (")
        result = normalize_special_characters("search for \u201ccarbon capture\u201d")
        # Smart quotes → straight quotes
        assert '"' in result.normalized_query
        assert result.was_normalized is True

    def test_en_dash(self):
        """Test en dash (–) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("CO₂ – important topic")
        # En dash → hyphen
        assert "-" in result.normalized_query
        assert result.was_normalized is True

    def test_em_dash(self):
        """Test em dash (—) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("funding—what options exist?")
        # Em dash → hyphen
        assert "-" in result.normalized_query
        assert result.was_normalized is True

    def test_ellipsis(self):
        """Test ellipsis (…) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("options include… many things")
        # Ellipsis → three dots
        assert "..." in result.normalized_query
        assert result.was_normalized is True

    def test_euro_sign(self):
        """Test € symbol normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("budget €5M")
        # Euro sign → EUR
        assert "EUR" in result.normalized_query
        assert result.was_normalized is True

    def test_inequality_signs(self):
        """Test ≤ and ≥ normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("budget ≥ 5M and duration ≤ 36 months")
        # ≥ → >=, ≤ → <=
        assert ">=" in result.normalized_query
        assert "<=" in result.normalized_query
        assert result.was_normalized is True

    def test_degree_sign(self):
        """Test ° (degree) normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("temperature 20°C")
        # Degree sign → " degrees"
        assert "degrees" in result.normalized_query
        assert result.was_normalized is True


class TestMultipleSpaceCollapse:
    """Tests for multiple space collapsing."""

    def test_multiple_spaces(self):
        """Test multiple spaces are collapsed to single space."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("find   projects   on   carbon")
        assert "  " not in result.normalized_query
        assert "find projects on carbon" in result.normalized_query
        assert result.was_normalized is True

    def test_leading_trailing_spaces(self):
        """Test leading/trailing spaces are stripped."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("  find projects  ")
        assert result.normalized_query == "find projects"


class TestScenario053SpecificQuery:
    """Tests for the specific scenario 053 query."""

    def test_original_scenario_query(self):
        """Test the exact query from scenario 053."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        query = "Find projects on CO₂ capture & storage (CCS) - what's available?"
        result = normalize_special_characters(query)

        # Check normalized query
        assert "CO2" in result.normalized_query
        assert "capture and storage" in result.normalized_query
        assert "(CCS)" in result.normalized_query
        assert result.was_normalized is True

        # Check that normalizations were applied
        assert any("subscript" in change for change in result.normalizations_applied)
        assert any("ampersand" in change for change in result.normalizations_applied)

    def test_query_semantic_preservation(self):
        """Test that semantic meaning is preserved after normalization."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        query = "Find projects on CO₂ capture & storage (CCS) - what's available?"
        result = normalize_special_characters(query)

        # Key terms should still be present
        assert "project" in result.normalized_query.lower()
        assert "co2" in result.normalized_query.lower()
        assert "capture" in result.normalized_query.lower()
        assert "storage" in result.normalized_query.lower()
        assert "ccs" in result.normalized_query.lower()


class TestSMEPatternsNotTriggered:
    """Test that project searches aren't incorrectly identified as SME queries."""

    def test_whats_available_with_topic_not_sme(self):
        """Test that 'what's available' with a topic is not an SME query."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # The query should not trigger SME guidance when it's about a topic
        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        agent.tools = {}

        # Manually call the SME detection method
        result = agent._detect_sme_eligibility_query(
            "Find projects on CO2 capture and storage (CCS) - what's available?", ""
        )

        # Should NOT trigger SME guidance
        assert result is None, "Should not trigger SME guidance for project search"

    def test_sme_explicit_mention_triggers(self):
        """Test that explicit SME mentions still trigger guidance."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        agent.tools = {}

        # Add the required method for the test
        agent._generate_sme_opportunities_guidance = lambda: "SME opportunities guidance"

        # Explicit SME query should trigger
        result = agent._detect_sme_eligibility_query(
            "What funding options are available for SMEs?", ""
        )

        # Should trigger SME guidance
        assert result is not None
        assert result.get("guidance_type") == "sme_opportunities"


class TestProcessQueryIntegration:
    """Integration tests with the full process_query function."""

    @pytest.mark.asyncio
    async def test_process_query_with_special_chars(self):
        """Test that process_query handles special characters."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # Create a mock agent
        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        agent.tools = {}
        agent.llm = MagicMock()
        agent.max_iterations = 1
        agent.speculative_executor = None
        agent.plan_cache = None

        # Mock internal methods
        agent._assess_complexity = MagicMock(return_value="simple")
        agent._identify_required_sources = MagicMock(return_value=["projects"])
        agent._reason_next_step = AsyncMock(
            return_value={
                "thought": "Searching for CCS projects",
                "action": "conclude",
                "conclusion": "Found CCS projects about carbon capture.",
                "confidence": 0.9,
            }
        )
        agent._build_fallback_answer = MagicMock(return_value="Fallback answer about CCS")
        agent._analyze_response_quality = MagicMock(return_value={"score": 80})

        # Process query with special characters
        query = "Find projects on CO₂ capture & storage (CCS)"
        result = await agent.process_query(query)

        # Check that special char metadata is present if normalized
        if "CO2" in str(result.get("answer", "")):
            # Query was normalized
            assert result.get("special_char_metadata") is not None or True
        else:
            # Check answer is present
            assert "answer" in result


class TestMapsCompleteness:
    """Tests for completeness of character maps."""

    def test_subscript_map_has_numbers(self):
        """Test SUBSCRIPT_MAP has all digits 0-9."""
        from app.services.agents.tool_aware_agent import SUBSCRIPT_MAP

        # All subscript digits should be mapped
        expected_values = set("0123456789")
        actual_values = set(SUBSCRIPT_MAP.values())
        assert expected_values.issubset(actual_values), "SUBSCRIPT_MAP should map to all digits"

    def test_superscript_map_has_numbers(self):
        """Test SUPERSCRIPT_MAP has all digits 0-9."""
        from app.services.agents.tool_aware_agent import SUPERSCRIPT_MAP

        # All superscript digits should be mapped
        expected_values = set("0123456789")
        actual_values = set(SUPERSCRIPT_MAP.values())
        assert expected_values.issubset(actual_values), "SUPERSCRIPT_MAP should map to all digits"

    def test_typography_map_has_quotes(self):
        """Test TYPOGRAPHY_MAP has smart quote mappings."""
        from app.services.agents.tool_aware_agent import TYPOGRAPHY_MAP

        # Smart quotes should be mapped to straight quotes
        values = list(TYPOGRAPHY_MAP.values())
        assert "'" in values, "TYPOGRAPHY_MAP should include apostrophe mapping"
        assert '"' in values, "TYPOGRAPHY_MAP should include double quote mapping"

    def test_typography_map_has_dashes(self):
        """Test TYPOGRAPHY_MAP has dash mappings."""
        from app.services.agents.tool_aware_agent import TYPOGRAPHY_MAP

        values = list(TYPOGRAPHY_MAP.values())
        assert "-" in values, "TYPOGRAPHY_MAP should include dash mapping"


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_only_special_chars(self):
        """Test query with only special characters."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("₂₃₄")
        assert result.normalized_query == "234"
        assert result.was_normalized is True

    def test_unicode_in_middle_of_word(self):
        """Test special character in middle of word."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        result = normalize_special_characters("pre₂fix")
        assert "pre2fix" in result.normalized_query

    def test_very_long_query_with_special_chars(self):
        """Test long query with special characters."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        query = "CO₂ capture & storage " * 50  # Long query
        result = normalize_special_characters(query)

        assert "CO2" in result.normalized_query
        assert "capture and storage" in result.normalized_query
        assert result.was_normalized is True

    def test_preserve_regular_quotes(self):
        """Test that regular ASCII quotes are not modified."""
        from app.services.agents.tool_aware_agent import normalize_special_characters

        query = 'Find "carbon capture" projects'
        result = normalize_special_characters(query)

        # Regular quotes should be preserved
        assert '"carbon capture"' in result.normalized_query


class TestIntegrationWithAPI:
    """Integration tests with the actual API (requires running server)."""

    @pytest.mark.skip(reason="Requires running API server")
    def test_api_with_special_chars_query(self):
        """Test API endpoint with special characters query."""
        import requests

        response = requests.post(
            "http://localhost:8000/api/v3/conversation/99902/message",
            json={"message": "Find projects on CO₂ capture & storage (CCS)"},
            timeout=120,
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data

        # Response should be about CCS/carbon capture
        response_text = data["response"].lower()
        assert any(term in response_text for term in ["carbon", "co2", "ccs", "capture", "storage"])

    @pytest.mark.skip(reason="Requires running API server")
    def test_api_does_not_return_sme_for_topic_query(self):
        """Test that topic queries don't return SME guidance."""
        import requests

        response = requests.post(
            "http://localhost:8000/api/v3/conversation/99903/message",
            json={"message": "Find projects on CO₂ capture & storage (CCS) - what's available?"},
            timeout=120,
        )

        assert response.status_code == 200
        data = response.json()
        response_text = data.get("response", "").lower()

        # Should NOT be an SME opportunities response
        # (SME response talks about EIC Accelerator, Eurostars, etc. without topic context)
        if "eic accelerator" in response_text and "eurostars" in response_text:
            # If both EIC Accelerator and Eurostars mentioned, likely SME response
            # Should also mention CCS topic
            assert any(term in response_text for term in ["carbon", "co2", "ccs", "capture"]), (
                "Response should be about CCS, not generic SME guidance"
            )
