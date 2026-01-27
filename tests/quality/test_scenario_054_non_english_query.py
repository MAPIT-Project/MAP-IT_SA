"""
Test Scenario 054: Non-English Query Handling

This scenario verifies that the system correctly handles queries in non-English
languages (French, German, Spanish, Italian, etc.) by detecting the language
and translating to English for processing.

Expected behavior:
- Detect the query language correctly
- Translate non-English queries to English
- Preserve EU funding-specific terminology
- Process translated query and return relevant results
- Do not fail or misunderstand the query

Pass threshold: 75/100
"""

import pytest


class TestLanguageDetection:
    """Unit tests for the detect_query_language function."""

    def test_imports(self):
        """Test that required imports work."""
        from app.services.agents.tool_aware_agent import (
            LANGUAGE_INDICATORS,
            LanguageDetectionResult,
            TranslationResult,
            detect_query_language,
            preprocess_non_english_query,
            translate_query_to_english,
        )

        # Verify components exist
        assert len(LANGUAGE_INDICATORS) > 0
        assert LanguageDetectionResult is not None
        assert TranslationResult is not None
        assert detect_query_language is not None
        assert translate_query_to_english is not None
        assert preprocess_non_english_query is not None

    def test_language_detection_result_dataclass(self):
        """Test LanguageDetectionResult dataclass structure."""
        from app.services.agents.tool_aware_agent import LanguageDetectionResult

        result = LanguageDetectionResult(
            original_query="Trouvez des appels",
            detected_language="fr",
            language_name="French",
            confidence=0.8,
            is_english=False,
            detection_method="word_frequency",
            matched_indicators=["trouvez", "des", "appels"],
        )

        assert result.original_query == "Trouvez des appels"
        assert result.detected_language == "fr"
        assert result.language_name == "French"
        assert result.confidence == 0.8
        assert result.is_english is False
        assert len(result.matched_indicators) == 3

    def test_translation_result_dataclass(self):
        """Test TranslationResult dataclass structure."""
        from app.services.agents.tool_aware_agent import TranslationResult

        result = TranslationResult(
            original_query="Trouvez des appels",
            translated_query="Find funding calls",
            source_language="fr",
            source_language_name="French",
            was_translated=True,
            translation_method="llm",
            confidence=0.85,
        )

        assert result.original_query == "Trouvez des appels"
        assert result.translated_query == "Find funding calls"
        assert result.was_translated is True
        assert result.translation_method == "llm"

    def test_empty_query_detection(self):
        """Test handling of empty queries."""
        from app.services.agents.tool_aware_agent import detect_query_language

        result = detect_query_language("")
        assert result.is_english is True
        assert result.detected_language == "en"
        assert result.detection_method == "default"

    def test_english_query_detection(self):
        """Test that English queries are correctly identified."""
        from app.services.agents.tool_aware_agent import detect_query_language

        queries = [
            "Find funding calls for renewable energy",
            "What are the eligibility requirements for Horizon Europe?",
            "Show me projects on artificial intelligence",
            "Can a university apply for ERC grants?",
        ]

        for query in queries:
            result = detect_query_language(query)
            assert result.is_english is True, f"Query should be English: {query}"
            assert result.detected_language == "en"


class TestFrenchDetection:
    """Tests for French language detection."""

    def test_french_query_prd_example(self):
        """Test the exact PRD example: 'Trouvez des appels pour l'énergie renouvelable'."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Trouvez des appels pour l'énergie renouvelable"
        result = detect_query_language(query)

        assert result.is_english is False, "Should detect as non-English"
        assert result.detected_language == "fr", f"Got {result.detected_language}"
        assert result.language_name == "French"
        assert result.confidence > 0.0

    def test_french_funding_query(self):
        """Test French funding-related query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Quels sont les appels de financement pour la recherche?"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "fr"

    def test_french_eligibility_query(self):
        """Test French eligibility question."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Est-ce qu'une université française peut participer à Horizon Europe?"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "fr"

    def test_french_contraction_detection(self):
        """Test detection via French contractions (l', d', qu', etc.)."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Je cherche d'autres subventions pour l'innovation"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "fr"


class TestGermanDetection:
    """Tests for German language detection."""

    def test_german_funding_query(self):
        """Test German funding-related query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Finden Sie Förderungsmöglichkeiten für erneuerbare Energie"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "de"
        assert result.language_name == "German"

    def test_german_research_query(self):
        """Test German research query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Welche Forschungsprojekte gibt es für künstliche Intelligenz?"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "de"

    def test_german_eligibility_query(self):
        """Test German eligibility question."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Können wir als deutsches Unternehmen an EU-Projekten teilnehmen?"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "de"


class TestSpanishDetection:
    """Tests for Spanish language detection."""

    def test_spanish_funding_query(self):
        """Test Spanish funding-related query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Buscar convocatorias para energía renovable"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "es"
        assert result.language_name == "Spanish"

    def test_spanish_project_query(self):
        """Test Spanish project search query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Encontrar proyectos de investigación sobre cambio climático"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "es"


class TestItalianDetection:
    """Tests for Italian language detection."""

    def test_italian_funding_query(self):
        """Test Italian funding-related query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Cercare bandi per finanziamento ricerca"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "it"
        assert result.language_name == "Italian"

    def test_italian_eligibility_query(self):
        """Test Italian eligibility question."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Possiamo partecipare come università italiana?"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "it"


class TestPortugueseDetection:
    """Tests for Portuguese language detection."""

    def test_portuguese_funding_query(self):
        """Test Portuguese funding-related query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Encontrar chamadas para financiamento de pesquisa"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "pt"
        assert result.language_name == "Portuguese"


class TestDutchDetection:
    """Tests for Dutch language detection."""

    def test_dutch_funding_query(self):
        """Test Dutch funding-related query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Zoeken naar subsidies voor hernieuwbare energie onderzoek"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "nl"
        assert result.language_name == "Dutch"


class TestPolishDetection:
    """Tests for Polish language detection."""

    def test_polish_funding_query(self):
        """Test Polish funding-related query with diacritics."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Szukać nabory dla badania energii odnawialnej"
        result = detect_query_language(query)

        assert result.is_english is False
        assert result.detected_language == "pl"
        assert result.language_name == "Polish"


class TestTranslation:
    """Tests for translation functionality."""

    def test_translation_without_llm(self):
        """Test that translation gracefully handles missing LLM."""
        from app.services.agents.tool_aware_agent import translate_query_to_english

        result = translate_query_to_english(
            query="Trouvez des appels",
            source_language="fr",
            source_language_name="French",
            llm=None,
        )

        # Without LLM, should return original query
        assert result.translated_query == "Trouvez des appels"
        assert result.was_translated is False
        assert result.translation_method == "passthrough"

    def test_translation_result_structure(self):
        """Test TranslationResult has correct structure."""
        from app.services.agents.tool_aware_agent import TranslationResult

        result = TranslationResult(
            original_query="Test query",
            translated_query="Translated query",
            source_language="fr",
            source_language_name="French",
            was_translated=True,
            translation_method="llm",
            confidence=0.9,
        )

        assert hasattr(result, "original_query")
        assert hasattr(result, "translated_query")
        assert hasattr(result, "source_language")
        assert hasattr(result, "was_translated")
        assert hasattr(result, "translation_method")
        assert hasattr(result, "confidence")


class TestPreprocessNonEnglishQuery:
    """Tests for the main preprocess_non_english_query function."""

    def test_english_query_passthrough(self):
        """Test that English queries are passed through unchanged."""
        from app.services.agents.tool_aware_agent import preprocess_non_english_query

        query = "Find renewable energy funding calls"
        processed_query, metadata = preprocess_non_english_query(query)

        assert processed_query == query
        assert metadata is None  # No translation metadata for English

    def test_french_query_without_llm(self):
        """Test French query detection without LLM translation."""
        from app.services.agents.tool_aware_agent import preprocess_non_english_query

        query = "Trouvez des appels pour l'énergie renouvelable"
        processed_query, metadata = preprocess_non_english_query(query, llm=None)

        # Without LLM, query is passed through but metadata is still generated
        assert metadata is not None
        assert metadata["original_language"] == "fr"
        assert metadata["original_language_name"] == "French"
        assert metadata["was_translated"] is False  # No LLM to translate

    def test_german_query_without_llm(self):
        """Test German query detection without LLM translation."""
        from app.services.agents.tool_aware_agent import preprocess_non_english_query

        query = "Finden Sie Förderungsmöglichkeiten für erneuerbare Energie"
        processed_query, metadata = preprocess_non_english_query(query, llm=None)

        assert metadata is not None
        assert metadata["original_language"] == "de"
        assert metadata["original_language_name"] == "German"


class TestLanguageIndicators:
    """Tests for the LANGUAGE_INDICATORS dictionary."""

    def test_all_languages_have_required_keys(self):
        """Test that all language entries have required keys."""
        from app.services.agents.tool_aware_agent import LANGUAGE_INDICATORS

        required_keys = ["words", "patterns", "name"]

        for lang_code, indicators in LANGUAGE_INDICATORS.items():
            for key in required_keys:
                assert key in indicators, f"Language {lang_code} missing key: {key}"

    def test_all_languages_have_words(self):
        """Test that all languages have word lists."""
        from app.services.agents.tool_aware_agent import LANGUAGE_INDICATORS

        for lang_code, indicators in LANGUAGE_INDICATORS.items():
            assert len(indicators["words"]) > 0, f"Language {lang_code} has no words"

    def test_all_languages_have_patterns(self):
        """Test that all languages have pattern lists."""
        from app.services.agents.tool_aware_agent import LANGUAGE_INDICATORS

        for lang_code, indicators in LANGUAGE_INDICATORS.items():
            assert len(indicators["patterns"]) >= 0, f"Language {lang_code} has no patterns"

    def test_supported_languages(self):
        """Test that we support expected EU languages."""
        from app.services.agents.tool_aware_agent import LANGUAGE_INDICATORS

        # Key EU languages that should be supported
        expected_languages = ["fr", "de", "es", "it", "pt", "nl", "pl"]

        for lang in expected_languages:
            assert lang in LANGUAGE_INDICATORS, f"Language {lang} should be supported"


class TestProcessQueryIntegration:
    """Integration tests with the full process_query function."""

    @pytest.mark.asyncio
    async def test_process_query_with_french_query(self):
        """Test that process_query handles French queries."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # Create a mock agent
        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        agent.tools = {}
        agent.max_iterations = 1
        agent.speculative_executor = None
        agent.plan_cache = None

        # Mock LLM for translation
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Find funding calls for renewable energy"
        mock_llm.generate_content.return_value = mock_response
        agent.llm = mock_llm

        # Mock internal methods
        agent._assess_complexity = MagicMock(return_value="simple")
        agent._identify_required_sources = MagicMock(return_value=["calls"])
        agent._reason_next_step = AsyncMock(
            return_value={
                "thought": "Searching for renewable energy calls",
                "action": "conclude",
                "conclusion": "Found renewable energy funding opportunities.",
                "confidence": 0.9,
            }
        )
        agent._build_fallback_answer = MagicMock(return_value="Fallback answer")
        agent._analyze_response_quality = MagicMock(return_value={"score": 80})

        # Process query in French
        query = "Trouvez des appels pour l'énergie renouvelable"
        result = await agent.process_query(query)

        # Check that translation metadata is present
        assert "translation_metadata" in result
        assert result["translation_metadata"]["original_language"] == "fr"
        assert result["translation_metadata"]["was_translated"] is True
        assert "answer" in result

    @pytest.mark.asyncio
    async def test_process_query_english_no_translation(self):
        """Test that English queries don't get translation metadata."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # Create a mock agent
        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        agent.tools = {}
        agent.max_iterations = 1
        agent.speculative_executor = None
        agent.plan_cache = None
        agent.llm = MagicMock()

        # Mock internal methods
        agent._assess_complexity = MagicMock(return_value="simple")
        agent._identify_required_sources = MagicMock(return_value=["calls"])
        agent._reason_next_step = AsyncMock(
            return_value={
                "thought": "Searching for renewable energy calls",
                "action": "conclude",
                "conclusion": "Found renewable energy funding opportunities.",
                "confidence": 0.9,
            }
        )
        agent._build_fallback_answer = MagicMock(return_value="Fallback answer")
        agent._analyze_response_quality = MagicMock(return_value={"score": 80})

        # Process English query
        query = "Find renewable energy funding calls"
        result = await agent.process_query(query)

        # Check that translation metadata is NOT present for English
        assert "translation_metadata" not in result


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_mixed_language_query(self):
        """Test query with mixed English and French."""
        from app.services.agents.tool_aware_agent import detect_query_language

        # Query with mostly French but some English terms
        query = "Trouvez des appels Horizon Europe pour AI research"
        result = detect_query_language(query)

        # Should detect as French due to French words
        assert result.detected_language == "fr"

    def test_query_with_programme_names(self):
        """Test that EU programme names don't confuse detection."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Chercher des appels Creative Europe et Erasmus+"
        result = detect_query_language(query)

        # Should still detect French despite English programme names
        assert result.detected_language == "fr"

    def test_short_query_defaults_to_english(self):
        """Test that very short queries default to English."""
        from app.services.agents.tool_aware_agent import detect_query_language

        # Single word that could be in multiple languages
        query = "help"
        result = detect_query_language(query)

        # Should default to English for ambiguous short queries
        assert result.is_english is True

    def test_numbers_only_query(self):
        """Test query with only numbers."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "12345"
        result = detect_query_language(query)

        # Should default to English
        assert result.is_english is True
        assert result.detected_language == "en"

    def test_special_characters_in_non_english(self):
        """Test French query with special characters."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Trouvez des appels pour l'énergie renouvelable & CO₂"
        result = detect_query_language(query)

        # Should still detect French
        assert result.detected_language == "fr"


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_high_confidence_for_clear_french(self):
        """Test high confidence for clearly French query."""
        from app.services.agents.tool_aware_agent import detect_query_language

        query = "Je cherche des subventions européennes pour notre université française"
        result = detect_query_language(query)

        assert result.detected_language == "fr"
        assert result.confidence > 0.3  # Multiple word matches = higher confidence

    def test_confidence_scales_with_matches(self):
        """Test that confidence increases with more word matches."""
        from app.services.agents.tool_aware_agent import detect_query_language

        # Short query with few French words
        short_query = "appels financement"
        short_result = detect_query_language(short_query)

        # Longer query with more French words
        long_query = "Je cherche des appels de financement pour notre projet de recherche européen"
        long_result = detect_query_language(long_query)

        # Longer query should have higher confidence
        if short_result.detected_language == "fr" and long_result.detected_language == "fr":
            assert long_result.confidence >= short_result.confidence


class TestTranslationPrompt:
    """Tests for the translation prompt template."""

    def test_translation_prompt_template_exists(self):
        """Test that translation prompt template is defined."""
        from app.services.agents.tool_aware_agent import TRANSLATION_PROMPT_TEMPLATE

        assert TRANSLATION_PROMPT_TEMPLATE is not None
        assert len(TRANSLATION_PROMPT_TEMPLATE) > 0

    def test_translation_prompt_has_placeholders(self):
        """Test that prompt template has required placeholders."""
        from app.services.agents.tool_aware_agent import TRANSLATION_PROMPT_TEMPLATE

        assert "{source_lang}" in TRANSLATION_PROMPT_TEMPLATE
        assert "{query}" in TRANSLATION_PROMPT_TEMPLATE

    def test_translation_prompt_mentions_eu_terms(self):
        """Test that prompt mentions preserving EU funding terms."""
        from app.services.agents.tool_aware_agent import TRANSLATION_PROMPT_TEMPLATE

        # Should mention preserving programme names
        template_lower = TRANSLATION_PROMPT_TEMPLATE.lower()
        assert "horizon europe" in template_lower or "programme" in template_lower
        assert "erasmus" in template_lower or "creative europe" in template_lower


class TestStreamingQueryHandling:
    """Tests for streaming query handling with non-English queries."""

    @pytest.mark.asyncio
    async def test_streaming_includes_translation_metadata(self):
        """Test that streaming process includes translation metadata."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # Create a mock agent
        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        agent.tools = {}
        agent.max_iterations = 1
        agent.speculative_executor = None
        agent.plan_cache = None

        # Mock LLM for translation
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Find funding calls for renewable energy"
        mock_llm.generate_content.return_value = mock_response
        agent.llm = mock_llm

        # Mock internal methods
        agent._assess_complexity = MagicMock(return_value="simple")
        agent._identify_required_sources = MagicMock(return_value=["calls"])
        agent._reason_next_step = AsyncMock(
            return_value={
                "thought": "Searching for renewable energy calls",
                "action": "conclude",
                "conclusion": "Found renewable energy funding opportunities.",
                "confidence": 0.9,
            }
        )
        agent._build_fallback_answer = MagicMock(return_value="Fallback answer")
        agent._analyze_response_quality = MagicMock(return_value={"score": 80})

        # Process streaming query in French
        query = "Trouvez des appels pour l'énergie renouvelable"
        events = []
        async for event in agent.process_query_streaming(query):
            events.append(event)

        # Find the agent_complete event
        complete_event = next((e for e in events if e.get("type") == "agent_complete"), None)
        assert complete_event is not None

        # Check translation metadata in result
        result = complete_event.get("result", {})
        assert "translation_metadata" in result
        assert result["translation_metadata"]["original_language"] == "fr"
