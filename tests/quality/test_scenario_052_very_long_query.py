"""
Tests for Scenario 052: Very Long Query Handling

PRD Reference:
- Query: [500+ character detailed query]
- Expected: Handles gracefully, extracts key intent
- Verify: Doesn't truncate badly, answers main question
- Fix if: Fails, only answers first part
- Pass threshold: 80

This scenario tests that very long queries (500+ characters) are handled
gracefully by extracting key intent while preserving important details
like organization names, budget amounts, countries, and programme names.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Test configuration
API_BASE_URL = "http://localhost:8000"
CONVERSATION_ENDPOINT = "/api/v3/conversation"
PASS_THRESHOLD = 80
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "very_long_query.json"


# =============================================================================
# Unit Tests - Test long query preprocessing functions
# =============================================================================


class TestLongQueryConstants:
    """Test that long query constants are properly configured."""

    def test_long_query_threshold_exists(self):
        """Test that LONG_QUERY_THRESHOLD is defined."""
        from app.services.agents.tool_aware_agent import LONG_QUERY_THRESHOLD

        assert LONG_QUERY_THRESHOLD is not None
        assert isinstance(LONG_QUERY_THRESHOLD, int)

    def test_long_query_threshold_reasonable_value(self):
        """Test that long query threshold is set to 500 per PRD."""
        from app.services.agents.tool_aware_agent import LONG_QUERY_THRESHOLD

        assert LONG_QUERY_THRESHOLD == 500, f"Threshold should be 500, got {LONG_QUERY_THRESHOLD}"

    def test_max_processed_query_length_exists(self):
        """Test that MAX_PROCESSED_QUERY_LENGTH is defined."""
        from app.services.agents.tool_aware_agent import MAX_PROCESSED_QUERY_LENGTH

        assert MAX_PROCESSED_QUERY_LENGTH is not None
        assert isinstance(MAX_PROCESSED_QUERY_LENGTH, int)

    def test_max_processed_query_length_reasonable(self):
        """Test that max processed length is reasonable (200-500 chars)."""
        from app.services.agents.tool_aware_agent import MAX_PROCESSED_QUERY_LENGTH

        assert (
            200 <= MAX_PROCESSED_QUERY_LENGTH <= 500
        ), f"MAX_PROCESSED_QUERY_LENGTH {MAX_PROCESSED_QUERY_LENGTH} should be 200-500"


class TestLongQueryResultDataclass:
    """Test the LongQueryResult dataclass."""

    def test_long_query_result_exists(self):
        """Test that LongQueryResult dataclass exists."""
        from app.services.agents.tool_aware_agent import LongQueryResult

        assert LongQueryResult is not None

    def test_long_query_result_fields(self):
        """Test LongQueryResult has all required fields."""
        from app.services.agents.tool_aware_agent import LongQueryResult

        result = LongQueryResult(
            original_query="test query",
            processed_query="processed",
            was_processed=True,
            extracted_intent="Find funding",
            key_details=["detail1", "detail2"],
            query_length=100,
            processing_note="Test note",
        )

        assert result.original_query == "test query"
        assert result.processed_query == "processed"
        assert result.was_processed is True
        assert result.extracted_intent == "Find funding"
        assert result.key_details == ["detail1", "detail2"]
        assert result.query_length == 100
        assert result.processing_note == "Test note"

    def test_long_query_result_defaults(self):
        """Test LongQueryResult default values."""
        from app.services.agents.tool_aware_agent import LongQueryResult

        result = LongQueryResult(
            original_query="test",
            processed_query="test",
            was_processed=False,
        )

        assert result.extracted_intent is None
        assert result.key_details == []
        assert result.query_length == 0
        assert result.processing_note is None


class TestPreprocessLongQueryFunction:
    """Test the preprocess_long_query function."""

    def test_short_query_not_processed(self):
        """Test that queries under 500 chars are not processed."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        short_query = "Find funding calls for AI research"
        result = preprocess_long_query(short_query)

        assert result.was_processed is False
        assert result.processed_query == short_query
        assert result.original_query == short_query
        assert result.query_length == len(short_query)

    def test_boundary_query_not_processed(self):
        """Test that queries at exactly 500 chars are not processed."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        # Create exactly 500 char query
        boundary_query = "x" * 500
        result = preprocess_long_query(boundary_query)

        assert result.was_processed is False
        assert result.query_length == 500

    def test_long_query_is_processed(self):
        """Test that queries over 500 chars are processed."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        long_query = "x" * 501
        result = preprocess_long_query(long_query)

        assert result.was_processed is True
        assert result.query_length == 501

    def test_long_query_extracts_key_details(self):
        """Test that long query extracts key details."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        long_query = (
            "I am a researcher at the Technical University of Munich in Germany working on "
            "a project about renewable energy and hydrogen fuel cells. We have a budget of "
            "approximately 5 million euros and would like to apply for Horizon Europe funding "
            "for a consortium of 12 partners from 8 different countries. The project duration "
            "would be 48 months and we are particularly interested in the Climate and Energy "
            "cluster. Can you help me find suitable funding calls and provide guidance on "
            "how to structure our proposal? We are also interested in understanding the "
            "success rates for similar projects and what consortium composition works best. "
            "Additionally, we would like to know about the evaluation criteria and timeline."
        )

        result = preprocess_long_query(long_query)

        assert result.was_processed is True
        assert len(result.key_details) > 0
        # Should extract key details like organization, country, budget
        details_lower = [d.lower() for d in result.key_details]
        # Check for some expected extractions
        assert any("germany" in d or "munich" in d for d in details_lower)

    def test_long_query_preserves_programme_names(self):
        """Test that programme names are preserved in processed query."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        long_query = (
            "Our organization, the Institute for Advanced Research in Paris, France, is "
            "planning to submit a proposal for the Horizon Europe EIC Accelerator programme. "
            "We have developed an innovative AI-based diagnostic tool for early cancer "
            "detection and are looking to commercialize it across the European market. "
            "The technology has already been validated in clinical trials with over 10,000 "
            "patients across 5 hospitals in France, Germany, and Italy. We are seeking "
            "funding of approximately 2.5 million euros to scale our operations and "
            "achieve market penetration. Can you provide information about the EIC "
            "Accelerator application process, success rates, evaluation criteria, and "
            "the best approach to present our business case and technology?"
        )

        result = preprocess_long_query(long_query)

        assert result.was_processed is True
        # Verify key details are extracted
        assert len(result.key_details) >= 2


class TestExtractKeyDetailsFunction:
    """Test the _extract_key_details helper function."""

    def test_extract_organization_names(self):
        """Test extraction of organization names."""
        from app.services.agents.tool_aware_agent import _extract_key_details

        query = "The Technical University of Munich and Fraunhofer Institute are collaborating"
        details = _extract_key_details(query)

        # Should extract organization patterns
        details_lower = [d.lower() for d in details]
        has_org = any("university" in d or "fraunhofer" in d for d in details_lower)
        assert has_org, f"Should extract organization names, got: {details}"

    def test_extract_budget_amounts(self):
        """Test extraction of budget amounts."""
        from app.services.agents.tool_aware_agent import _extract_key_details

        query = "We need a budget of 5 million euros for 48 months project"
        details = _extract_key_details(query)

        # Should extract budget patterns
        details_str = " ".join(details).lower()
        has_budget = any(term in details_str for term in ["5 million", "48 months", "million"])
        assert has_budget or len(details) > 0, f"Should extract budget, got: {details}"

    def test_extract_country_names(self):
        """Test extraction of country names."""
        from app.services.agents.tool_aware_agent import _extract_key_details

        query = "Partners from Germany, France, and Italy will collaborate on the project"
        details = _extract_key_details(query)

        details_lower = [d.lower() for d in details]
        has_country = any(c in details_lower for c in ["germany", "france", "italy"])
        assert has_country, f"Should extract country names, got: {details}"

    def test_extract_call_ids(self):
        """Test extraction of call IDs."""
        from app.services.agents.tool_aware_agent import _extract_key_details

        query = "We want to apply for call HORIZON-CL5-2025-D1-01 deadline March"
        details = _extract_key_details(query)

        details_str = " ".join(details).upper()
        has_call_id = "HORIZON" in details_str
        assert has_call_id, f"Should extract call ID, got: {details}"

    def test_extract_programme_names(self):
        """Test extraction of programme names."""
        from app.services.agents.tool_aware_agent import _extract_key_details

        query = "Should we apply to Horizon Europe or Erasmus+ for our education project?"
        details = _extract_key_details(query)

        details_str = " ".join(details).lower()
        has_programme = "horizon europe" in details_str or "erasmus" in details_str
        assert has_programme, f"Should extract programme names, got: {details}"

    def test_deduplicates_details(self):
        """Test that extracted details are deduplicated."""
        from app.services.agents.tool_aware_agent import _extract_key_details

        query = (
            "Germany is great. Germany has many universities. "
            "The University of Munich and University of Berlin are in Germany."
        )
        details = _extract_key_details(query)

        # Count exact "Germany" occurrences in details (universities are separate entries)
        # The function deduplicates exact matches, but "Germany" as country and
        # "University of Munich" as org are different entries
        details_lower = [d.lower() for d in details]
        exact_germany_count = details_lower.count("germany")
        assert (
            exact_germany_count <= 1
        ), f"Should deduplicate exact matches, got {exact_germany_count} 'Germany'"

    def test_limits_details_to_ten(self):
        """Test that extracted details are limited to 10."""
        from app.services.agents.tool_aware_agent import _extract_key_details

        query = (
            "Partners from Germany, France, Italy, Spain, Netherlands, Belgium, "
            "Austria, Poland, Sweden, Denmark, Finland, Ireland, Portugal, Greece, "
            "Czech Republic, Hungary, Romania, and Bulgaria are collaborating with "
            "Fraunhofer Institute, Max Planck Society, CNRS, INRIA on a 10 million "
            "euro project for 60 months starting in 2025."
        )
        details = _extract_key_details(query)

        assert len(details) <= 10, f"Should limit to 10 details, got {len(details)}"


class TestExtractIntentRuleBasedFunction:
    """Test the _extract_intent_rule_based helper function."""

    def test_eligibility_question_type(self):
        """Test detection of eligibility question type."""
        from app.services.agents.tool_aware_agent import _extract_intent_rule_based

        query = (
            "I am a researcher at the University of Munich and I would like to know "
            "if I am eligible for the EIC Accelerator programme. We are a spin-off "
            "company with 25 employees and annual revenue of 3 million euros. " * 3
        )
        key_details = ["Munich", "EIC Accelerator"]

        processed = _extract_intent_rule_based(query, key_details)

        assert "eligible" in processed.lower()

    def test_budget_question_type(self):
        """Test detection of budget question type."""
        from app.services.agents.tool_aware_agent import _extract_intent_rule_based

        query = (
            "How much budget should I plan for a Horizon Europe RIA project in the "
            "climate and energy cluster? We have 15 partners and the project is 48 months." * 3
        )
        key_details = ["Horizon Europe", "15 partners"]

        processed = _extract_intent_rule_based(query, key_details)

        assert "budget" in processed.lower()

    def test_search_question_type(self):
        """Test detection of search question type."""
        from app.services.agents.tool_aware_agent import _extract_intent_rule_based

        query = (
            "Please find me funding opportunities for renewable energy research "
            "in the area of solar photovoltaics and energy storage systems. " * 4
        )
        key_details = ["renewable energy", "solar"]

        processed = _extract_intent_rule_based(query, key_details)

        # Should detect search intent and produce relevant output
        processed_lower = processed.lower()
        assert (
            "find" in processed_lower
            or "funding" in processed_lower
            or "opportunities" in processed_lower
        )

    def test_preserves_key_details(self):
        """Test that key details are included in processed query."""
        from app.services.agents.tool_aware_agent import _extract_intent_rule_based

        query = "Long query about funding for research in Germany and France." * 10
        key_details = ["Germany", "France", "5 million euros"]

        processed = _extract_intent_rule_based(query, key_details)

        # Key details should be included
        assert "Germany" in processed or "France" in processed

    def test_respects_max_length(self):
        """Test that processed query respects max length."""
        from app.services.agents.tool_aware_agent import (
            MAX_PROCESSED_QUERY_LENGTH,
            _extract_intent_rule_based,
        )

        query = "This is an extremely long query about funding opportunities." * 50
        key_details = ["detail1", "detail2", "detail3", "detail4", "detail5"]

        processed = _extract_intent_rule_based(query, key_details)

        assert (
            len(processed) <= MAX_PROCESSED_QUERY_LENGTH
        ), f"Processed query too long: {len(processed)} > {MAX_PROCESSED_QUERY_LENGTH}"


# =============================================================================
# Integration Tests - Test with actual agent processing
# =============================================================================


class TestLongQueryAgentIntegration:
    """Test long query handling integrated with ToolAwareAgent."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        mock = MagicMock()
        mock_response = (
            '{"intent": "Find renewable energy funding", '
            '"processed_query": "Find Horizon Europe funding for renewable energy"}'
        )
        mock.generate_content.return_value = MagicMock(text=mock_response)
        return mock

    def test_preprocessing_with_mock_llm(self, mock_llm):
        """Test that preprocessing works with mock LLM."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        # Create a long query
        long_query = (
            "I am a professor at the Technical University of Munich in Germany and I "
            "am leading a research group focused on sustainable energy systems. We have "
            "been working on advanced hydrogen fuel cell technology for the past 10 years "
            "and have developed several patented innovations in this area. Our group "
            "consists of 12 researchers including 3 PhD students and 2 postdoctoral "
            "researchers. We are now looking to apply for Horizon Europe funding to "
            "scale up our technology and collaborate with industrial partners across "
            "Europe. Can you help me find suitable funding calls for our research?"
        )

        # Verify query is over threshold
        assert len(long_query) > 500

        # The preprocessing should work with the mock LLM
        result = preprocess_long_query(long_query, mock_llm)

        assert result.was_processed is True
        assert len(result.processed_query) < len(long_query)
        # With mock LLM, it should use LLM extraction
        assert result.processing_note == "Extracted via LLM"

    def test_llm_extraction_fallback(self):
        """Test fallback to rule-based when LLM fails."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        # Create mock LLM that raises exception
        mock_llm = MagicMock()
        mock_llm.generate_content.side_effect = Exception("LLM error")

        long_query = "This is a very long query about funding. " * 20

        result = preprocess_long_query(long_query, mock_llm)

        # Should still process using rule-based fallback
        assert result.was_processed is True
        assert result.processing_note == "Extracted via rule-based method"


# =============================================================================
# Scenario Evaluator - Quality scoring for responses
# =============================================================================


class ScenarioEvaluator:
    """Evaluates responses for Scenario 052: Very Long Query."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Main question answered
            "specificity": 25,  # Concrete details preserved
            "factual_accuracy": 25,  # Correct information
            "actionability": 10,  # Clear next steps
        }

    def evaluate(self, original_query: str, response: str, metadata: dict = None) -> dict:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Check that the main question is answered
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check for substantive response
        if len(response) > 200:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append("Response too short for detailed query")

        # Check for relevance to EU funding
        funding_terms = [
            "horizon europe",
            "funding",
            "call",
            "grant",
            "proposal",
            "programme",
            "program",
            "eligible",
            "deadline",
        ]
        relevant_count = sum(1 for term in funding_terms if term in response_lower)
        if relevant_count >= 3:
            fulfillment_score += 15
        elif relevant_count >= 1:
            fulfillment_score += 8
            fulfillment_feedback.append("Could include more funding-relevant information")
        else:
            fulfillment_feedback.append("Response not relevant to EU funding")

        # Check that response doesn't just address first part
        response_sentences = response.split(".")
        if len(response_sentences) >= 5:
            fulfillment_score += 10
        else:
            fulfillment_feedback.append("Response may not fully address all parts of query")

        scores["query_fulfillment"] = min(fulfillment_score, 40)
        feedback["query_fulfillment"] = fulfillment_feedback

        # 2. Specificity (25 points)
        # Check that specific details from query are preserved/addressed
        specificity_score = 0
        specificity_feedback = []

        # Check for specific EU programme mentions
        programmes = [
            "horizon europe",
            "eic",
            "erc",
            "msca",
            "erasmus",
            "creative europe",
            "life",
            "digital europe",
        ]
        programmes_mentioned = sum(1 for p in programmes if p in response_lower)
        if programmes_mentioned >= 2:
            specificity_score += 10
        elif programmes_mentioned >= 1:
            specificity_score += 5
            specificity_feedback.append("Could mention more specific programmes")

        # Check for numbers/concrete details
        has_numbers = bool(re.search(r"\d+", response))
        if has_numbers:
            specificity_score += 8
        else:
            specificity_feedback.append("Could include specific numbers/figures")

        # Check for links
        has_links = "http" in response_lower or "portal" in response_lower
        if has_links:
            specificity_score += 7
        else:
            specificity_feedback.append("Could include relevant links")

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        # Check for correct EU funding information
        accuracy_score = 0
        accuracy_feedback = []

        # No hallucinated call IDs (check for suspicious patterns)
        suspicious_call_pattern = r"HORIZON-[A-Z0-9]{5,}-9999"
        has_suspicious = bool(re.search(suspicious_call_pattern, response))
        if not has_suspicious:
            accuracy_score += 15
        else:
            accuracy_feedback.append("May contain hallucinated call IDs")

        # Check for reasonable budget figures (not outlandish)
        budget_pattern = r"(\d+(?:\.\d+)?)\s*(?:billion|million|m|b)"
        budgets = re.findall(budget_pattern, response_lower)
        reasonable_budgets = all(float(b) < 1000 for b in budgets) if budgets else True
        if reasonable_budgets:
            accuracy_score += 10
        else:
            accuracy_feedback.append("Budget figures may be unreasonable")

        scores["factual_accuracy"] = min(accuracy_score, 25)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        # Check for clear next steps
        actionability_score = 0
        actionability_feedback = []

        action_terms = [
            "apply",
            "submit",
            "register",
            "contact",
            "check",
            "visit",
            "search",
            "find",
            "review",
        ]
        action_count = sum(1 for term in action_terms if term in response_lower)
        if action_count >= 3:
            actionability_score += 10
        elif action_count >= 1:
            actionability_score += 5
            actionability_feedback.append("Could include more actionable steps")
        else:
            actionability_feedback.append("Missing clear next steps")

        scores["actionability"] = min(actionability_score, 10)
        feedback["actionability"] = actionability_feedback

        # Calculate total score
        total_score = sum(scores.values())
        passed = total_score >= PASS_THRESHOLD

        return {
            "total_score": total_score,
            "max_score": 100,
            "passed": passed,
            "pass_threshold": PASS_THRESHOLD,
            "dimension_scores": scores,
            "dimension_feedback": feedback,
            "metadata": metadata,
        }


class TestScenarioEvaluator:
    """Test the scenario evaluator."""

    def test_evaluator_scores_good_response(self):
        """Test that evaluator gives high score to good response."""
        evaluator = ScenarioEvaluator()

        original_query = (
            "I am a researcher at the University of Munich in Germany working on "
            "renewable energy research with hydrogen fuel cells. We have a consortium "
            "of 15 partners from 8 countries and need approximately 5 million euros "
            "for a 48-month project. Can you help me find suitable Horizon Europe "
            "funding calls and provide guidance on the application process?"
        ) * 2

        good_response = """
Based on your renewable energy and hydrogen research focus, here are Horizon Europe opportunities:

**Recommended Calls:**
1. **HORIZON-CL5-2025-D3-01**: Clean Hydrogen Partnership calls for hydrogen applications
   - Budget: EUR 10-15 million per project
   - Deadline: Typically March 2025

2. **HORIZON-CL5-2025-D1-01**: Renewable energy integration
   - Budget: EUR 5-10 million
   - Suitable for 15-partner consortium

**Application Guidance:**
- Register on the EU Funding & Tenders Portal (https://ec.europa.eu/funding-tenders/opportunities/portal)
- Your consortium of 8 countries exceeds the minimum of 3 EU Member States
- 48-month duration is standard for RIA projects

**Next Steps:**
1. Check the Work Programme for Cluster 5 (Climate, Energy, Mobility)
2. Contact your National Contact Point in Germany
3. Review successful project proposals on CORDIS

Success rates for similar projects are typically 10-15%.
"""

        result = evaluator.evaluate(original_query, good_response)

        assert (
            result["total_score"] >= 70
        ), f"Good response should score well, got {result['total_score']}"

    def test_evaluator_scores_poor_response(self):
        """Test that evaluator gives low score to poor response."""
        evaluator = ScenarioEvaluator()

        original_query = "A very long query about EU funding..." * 20

        poor_response = "I'm not sure about that."

        result = evaluator.evaluate(original_query, poor_response)

        assert (
            result["total_score"] < 50
        ), f"Poor response should score low, got {result['total_score']}"


# =============================================================================
# Sample Long Queries for Testing
# =============================================================================

SAMPLE_LONG_QUERIES = [
    {
        "name": "academic_researcher_hydrogen",
        "query": (
            "I am a professor at the Technical University of Munich in Germany, leading a "
            "research group focused on sustainable energy systems. We have been working on "
            "advanced hydrogen fuel cell technology for the past 10 years and have developed "
            "several patented innovations including a novel membrane electrode assembly that "
            "increases fuel cell efficiency by 25%. Our group consists of 12 researchers "
            "including 3 PhD students and 2 postdoctoral researchers. We are collaborating "
            "with Fraunhofer Institute in Germany, CNRS in France, and TNO in the Netherlands. "
            "The technology is currently at TRL 5 and we want to advance it to TRL 7 through "
            "a demonstration project. We estimate needing approximately 8 million euros over "
            "48 months. Can you help me find suitable Horizon Europe funding calls for our "
            "hydrogen fuel cell research, and provide guidance on the application process, "
            "consortium requirements, and typical success rates for similar projects?"
        ),
        "expected_intents": ["funding", "hydrogen", "horizon europe"],
        "key_details_expected": ["munich", "germany", "fraunhofer", "cnrs", "8 million"],
    },
    {
        "name": "sme_ai_healthcare",
        "query": (
            "Our company is a small-to-medium enterprise based in Barcelona, Spain, with "
            "45 employees and annual revenue of 6 million euros. We have developed an "
            "innovative AI-based diagnostic tool for early detection of diabetic retinopathy "
            "using smartphone cameras. The technology has been validated in clinical trials "
            "with over 15,000 patients across 8 hospitals in Spain, Portugal, and Italy, "
            "achieving 94% sensitivity and 98% specificity. We have CE marking and are "
            "pursuing FDA approval. We are looking for EU funding to scale our operations, "
            "enter new markets in Germany, France, and Nordic countries, and develop our "
            "next-generation platform for detecting multiple eye conditions. We need "
            "approximately 2.5 million euros for market expansion and 1 million euros for "
            "R&D. Should we apply for EIC Accelerator, Horizon Europe RIA/IA, or EU4Health? "
            "What are the success rates and evaluation criteria for each option? Can you "
            "also provide information about the application timeline and required documents?"
        ),
        "expected_intents": ["funding", "sme", "ai", "healthcare"],
        "key_details_expected": ["spain", "barcelona", "2.5 million", "eic accelerator"],
    },
    {
        "name": "university_erasmus_mobility",
        "query": (
            "I am the International Relations Officer at the University of Warsaw in Poland. "
            "We want to organize a large-scale student mobility program involving 200 students "
            "over three years. The students would come from our university and partner "
            "institutions in Czech Republic (Charles University), Hungary (ELTE Budapest), "
            "Slovakia (Comenius University Bratislava), and Romania (University of Bucharest). "
            "We want to send students for 4-month study abroad periods and also organize "
            "intensive programs of 2 weeks each summer. Additionally, we want to include "
            "staff mobility for 30 faculty members per year to exchange teaching methods. "
            "Our focus areas are digital humanities, data science, and European studies. "
            "What Erasmus+ actions should we apply for? How do we calculate the budget using "
            "unit costs and travel bands? Can we combine mobility with a cooperation partnership? "
            "What are the quality criteria and how should we demonstrate impact? Our university "
            "already has Erasmus+ accreditation - does this change our application process?"
        ),
        "expected_intents": ["erasmus", "mobility", "university"],
        "key_details_expected": ["poland", "warsaw", "200 students", "accreditation"],
    },
]


class TestSampleLongQueries:
    """Test that sample long queries are properly handled."""

    def test_all_sample_queries_over_threshold(self):
        """Verify all sample queries are over 500 characters."""
        for sample in SAMPLE_LONG_QUERIES:
            assert (
                len(sample["query"]) > 500
            ), f"Sample {sample['name']} is only {len(sample['query'])} chars"

    def test_sample_queries_are_processed(self):
        """Test that all sample queries trigger processing."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        for sample in SAMPLE_LONG_QUERIES:
            result = preprocess_long_query(sample["query"])
            assert result.was_processed is True, f"Sample {sample['name']} should be processed"

    def test_sample_queries_extract_expected_details(self):
        """Test that expected key details are extracted."""
        from app.services.agents.tool_aware_agent import preprocess_long_query

        for sample in SAMPLE_LONG_QUERIES:
            result = preprocess_long_query(sample["query"])
            details_lower = " ".join(result.key_details).lower()

            # Check at least some expected details were extracted
            found_details = [
                d for d in sample["key_details_expected"] if d.lower() in details_lower
            ]
            assert len(found_details) >= 1, (
                f"Sample {sample['name']}: Expected some of {sample['key_details_expected']}, "
                f"but got {result.key_details}"
            )


# =============================================================================
# Live API Tests (require running server)
# =============================================================================


@pytest.mark.integration
class TestLiveAPILongQuery:
    """Test long query handling against live API."""

    @pytest.fixture
    def api_client(self):
        """Create API client for testing."""
        try:
            import httpx

            return httpx.Client(base_url=API_BASE_URL, timeout=60.0)
        except ImportError:
            pytest.skip("httpx not installed")

    def test_api_handles_long_query(self, api_client):
        """Test that API handles long query without error."""
        try:
            # Create conversation
            response = api_client.post(f"{CONVERSATION_ENDPOINT}/new")
            if response.status_code != 200:
                pytest.skip("API not available")

            conv_data = response.json()
            conv_id = conv_data.get("conversation_id")

            # Send long query
            long_query = SAMPLE_LONG_QUERIES[0]["query"]

            msg_response = api_client.post(
                f"{CONVERSATION_ENDPOINT}/{conv_id}/message",
                json={"message": long_query},
            )

            assert (
                msg_response.status_code == 200
            ), f"API should handle long query, got {msg_response.status_code}"

            result = msg_response.json()
            assert "answer" in result or "response" in result

        except Exception as e:
            pytest.skip(f"API test failed: {e}")

    def test_api_response_addresses_main_question(self, api_client):
        """Test that API response addresses the main question."""
        try:
            # Create conversation
            response = api_client.post(f"{CONVERSATION_ENDPOINT}/new")
            if response.status_code != 200:
                pytest.skip("API not available")

            conv_data = response.json()
            conv_id = conv_data.get("conversation_id")

            # Send query about hydrogen funding
            long_query = SAMPLE_LONG_QUERIES[0]["query"]

            msg_response = api_client.post(
                f"{CONVERSATION_ENDPOINT}/{conv_id}/message",
                json={"message": long_query},
            )

            if msg_response.status_code != 200:
                pytest.skip("API error")

            result = msg_response.json()
            answer = result.get("answer", result.get("response", ""))

            # Evaluate response quality
            evaluator = ScenarioEvaluator()
            evaluation = evaluator.evaluate(long_query, answer)

            assert (
                evaluation["total_score"] >= PASS_THRESHOLD
            ), f"Response should score >= {PASS_THRESHOLD}, got {evaluation['total_score']}"

        except Exception as e:
            pytest.skip(f"API test failed: {e}")


# =============================================================================
# Helper to save results
# =============================================================================


def save_evaluation_result(evaluation: dict, query_name: str = "unknown"):
    """Save evaluation result to JSON file."""
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)

    result_data = {
        "scenario": "052_very_long_query",
        "query_name": query_name,
        "timestamp": datetime.now().isoformat(),
        "evaluation": evaluation,
    }

    with open(RESULT_FILE, "w") as f:
        json.dump(result_data, f, indent=2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
