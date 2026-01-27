"""
Test Scenario 055: No Matching Calls

Tests that MAPIT handles the case of no matching funding calls gracefully by:
- Acknowledging that no results were found (not empty response)
- Suggesting spelling checks
- Recommending alternative/related search terms
- Providing links to helpful resources
- NOT just saying "no results found" without context

Pass threshold: 80/100

Query: "Find open calls for underwater basket weaving"
Expected: Graceful "no results", suggests alternatives
"""

from datetime import datetime
import json
from pathlib import Path
import re

import httpx
import pytest

# Test configuration
API_BASE_URL = "http://localhost:8000"
CONVERSATION_ENDPOINT = "/api/v3/conversation"
PASS_THRESHOLD = 80
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "no_matching_calls.json"

# The test query - deliberately obscure to get no results
TEST_QUERY = "Find open calls for underwater basket weaving"


class ScenarioEvaluator:
    """Evaluates responses for Scenario 055: No Matching Calls."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Acknowledges no results, doesn't claim to have found any
            "specificity": 25,  # Provides specific suggestions and alternatives
            "factual_accuracy": 25,  # Doesn't hallucinate fake calls
            "actionability": 10,  # Clear next steps for user
        }

    def evaluate(self, query: str, response: str) -> dict:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Must acknowledge no results and NOT claim to have found matching calls
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check that response acknowledges no results
        no_results_indicators = [
            "no matching",
            "no funding calls",
            "couldn't find",
            "could not find",
            "no results",
            "no calls found",
            "unable to find",
            "not find any",
        ]
        acknowledges_no_results = any(
            indicator in response_lower for indicator in no_results_indicators
        )

        if acknowledges_no_results:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append(
                "Should clearly acknowledge that no matching calls were found"
            )

        # Check that it does NOT claim to have found matching calls
        false_positive_indicators = [
            "i found",
            "here are",
            "the following calls",
            "matching calls:",
            "relevant opportunities:",
        ]
        # Allow "I found 0" or "found no" but not "I found 5" etc.
        claims_results = any(indicator in response_lower for indicator in false_positive_indicators)
        # Check if any numbers with "found" that aren't zero
        found_with_number = re.search(r"found\s+(\d+)", response_lower)
        if found_with_number and found_with_number.group(1) != "0":
            claims_results = True

        if not claims_results:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append(
                "Should not claim to have found matching calls when none exist"
            )

        # Check that response is NOT just a single line
        response_lines = [line.strip() for line in response.split("\n") if line.strip()]
        if len(response_lines) >= 5:
            fulfillment_score += 10
        elif len(response_lines) >= 3:
            fulfillment_score += 5
            fulfillment_feedback.append("Response could be more detailed")
        else:
            fulfillment_feedback.append("Response is too brief - should provide helpful context")

        scores["query_fulfillment"] = min(fulfillment_score, 40)
        feedback["query_fulfillment"] = fulfillment_feedback

        # 2. Specificity (25 points)
        # Provides specific suggestions and alternatives
        specificity_score = 0
        specificity_feedback = []

        # Check for spelling/terminology suggestions
        spelling_terms = [
            "spelling",
            "check",
            "verify",
            "search term",
            "terminology",
            "keywords",
        ]
        suggests_spelling_check = any(term in response_lower for term in spelling_terms)
        if suggests_spelling_check:
            specificity_score += 8
        else:
            specificity_feedback.append("Should suggest checking spelling or search terms")

        # Check for alternative term suggestions
        alternative_terms = [
            "try",
            "consider",
            "alternative",
            "broader",
            "related",
            "instead",
            "different",
        ]
        suggests_alternatives = any(term in response_lower for term in alternative_terms)
        if suggests_alternatives:
            specificity_score += 9
        else:
            specificity_feedback.append("Should suggest alternative search terms")

        # Check for programme mentions (guides user to actual programmes)
        programme_mentions = [
            "horizon europe",
            "erasmus",
            "creative europe",
            "life programme",
            "digital europe",
            "eu4health",
        ]
        mentions_programmes = sum(1 for p in programme_mentions if p in response_lower)
        if mentions_programmes >= 2:
            specificity_score += 8
        elif mentions_programmes >= 1:
            specificity_score += 4
            specificity_feedback.append("Could mention more EU programmes as alternatives")
        else:
            specificity_feedback.append("Should mention EU programmes to explore")

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        # Does NOT hallucinate fake calls
        accuracy_score = 25  # Start with full score, deduct for issues
        accuracy_feedback = []

        # Check for hallucinated call IDs (fake HORIZON-xxx patterns)
        fake_call_pattern = re.compile(
            r"HORIZON-[A-Z0-9]+-[0-9]+-[0-9]+[A-Z0-9-]*",
            re.IGNORECASE,
        )
        potential_fake_calls = fake_call_pattern.findall(response)
        if potential_fake_calls:
            accuracy_score -= 15
            accuracy_feedback.append(f"Appears to hallucinate call IDs: {potential_fake_calls[:3]}")

        # Check for hallucinated deadlines (dates in the future with specific calls)
        # This is a red flag if combined with specific call details
        if potential_fake_calls:
            deadline_pattern = re.compile(r"deadline.*202[0-9]", re.IGNORECASE)
            if deadline_pattern.search(response):
                accuracy_score -= 10
                accuracy_feedback.append("Appears to include fake deadlines for non-existent calls")

        # Check for hallucinated budget figures associated with fake calls
        if potential_fake_calls:
            budget_pattern = re.compile(r"(EUR|€)\s*[\d,]+", re.IGNORECASE)
            if budget_pattern.search(response):
                accuracy_score -= 5
                accuracy_feedback.append("Appears to include budget figures for non-existent calls")

        if accuracy_score == 25:
            accuracy_feedback.append("Good - no hallucinated calls detected")

        scores["factual_accuracy"] = max(accuracy_score, 0)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        # Clear next steps for user
        actionability_score = 0
        actionability_feedback = []

        # Check for links
        has_links = "http" in response_lower or "https" in response_lower or ".eu" in response_lower
        if has_links:
            actionability_score += 4
        else:
            actionability_feedback.append("Should include links to helpful resources")

        # Check for next steps section
        next_steps_indicators = [
            "next step",
            "you can",
            "try",
            "recommend",
            "suggest",
            "contact",
            "ncp",
            "national contact",
        ]
        has_next_steps = sum(1 for term in next_steps_indicators if term in response_lower)
        if has_next_steps >= 3:
            actionability_score += 6
        elif has_next_steps >= 1:
            actionability_score += 3
            actionability_feedback.append("Could provide more detailed next steps")
        else:
            actionability_feedback.append("Should provide clear next steps for the user")

        scores["actionability"] = min(actionability_score, 10)
        feedback["actionability"] = actionability_feedback

        # Calculate total score
        total_score = sum(scores.values())

        return {
            "total_score": total_score,
            "passed": total_score >= PASS_THRESHOLD,
            "scores": scores,
            "feedback": feedback,
            "dimensions": self.dimensions,
            "threshold": PASS_THRESHOLD,
        }


# ============================================================================
# Unit Tests for Evaluator
# ============================================================================


class TestEvaluatorLogic:
    """Test the evaluator scoring logic."""

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    def test_excellent_no_results_response(self, evaluator):
        """Test scoring of an excellent no-results response."""
        response = """## No Matching Funding Calls Found

I searched through all available EU funding opportunities, but couldn't find any calls
matching your specific query "underwater basket weaving".

### Suggestions

**1. Check Your Search Terms**
- Verify the spelling of keywords
- Try using standard EU programme terminology

**2. Try Broader or Related Terms**
- Try searching for: **marine**, **textiles**, **heritage**
- Consider searching by Horizon Europe cluster

**3. Explore Different EU Programmes**
- **Horizon Europe**: Research and innovation
- **Erasmus+**: Education, training, youth
- **Creative Europe**: Culture, media, creative sectors

### Helpful Resources
• [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/)
• [Find Your NCP](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)

### Next Steps
1. Rephrase your query with the suggestions above
2. Contact your National Contact Point for advice
3. Browse the EU Portal by research cluster
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["query_fulfillment"] >= 35, "Should score high on fulfillment"
        assert result["scores"]["specificity"] >= 20, "Should score high on specificity"
        assert result["scores"]["factual_accuracy"] == 25, "Should have perfect accuracy"
        assert result["scores"]["actionability"] >= 8, "Should score high on actionability"
        assert result["total_score"] >= PASS_THRESHOLD, "Should pass threshold"

    def test_poor_no_results_response(self, evaluator):
        """Test scoring of a poor (too brief) no-results response."""
        response = "No funding calls found."

        result = evaluator.evaluate(TEST_QUERY, response)

        # Brief response acknowledges no results (30 pts max) but lacks detail
        assert result["scores"]["query_fulfillment"] <= 30, "Brief response limited fulfillment"
        assert result["scores"]["specificity"] <= 10, "No suggestions should score low"
        assert result["scores"]["actionability"] <= 5, "No links/steps should score low"
        assert result["total_score"] < PASS_THRESHOLD, "Should not pass threshold"

    def test_hallucinated_calls_response(self, evaluator):
        """Test scoring penalizes hallucinated call IDs."""
        response = """I found several relevant funding calls:

1. HORIZON-CL5-2026-D3-01: Underwater Technologies
   - Deadline: March 2026
   - Budget: EUR 5,000,000

2. HORIZON-FAKE-2026-01: Basket Weaving Research
   - Deadline: April 2026
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["query_fulfillment"] <= 20, "Should penalize claiming results"
        assert result["scores"]["factual_accuracy"] <= 15, "Should heavily penalize hallucinations"
        assert result["total_score"] < PASS_THRESHOLD, "Should not pass threshold"

    def test_moderate_response(self, evaluator):
        """Test scoring of a moderate response that mentions some alternatives."""
        response = """No matching funding calls were found for "underwater basket weaving".

This topic doesn't match any current EU funding opportunities.

You could try:
- Searching for related terms like "marine research" or "textiles"
- Checking Horizon Europe or Creative Europe programmes
- Contacting your National Contact Point

Visit https://ec.europa.eu/info/funding-tenders/ for more options.
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["query_fulfillment"] >= 25, "Should acknowledge no results"
        assert result["scores"]["specificity"] >= 15, "Mentions some alternatives"
        assert result["scores"]["factual_accuracy"] == 25, "No hallucinations"
        assert result["scores"]["actionability"] >= 5, "Has link and suggestions"
        # May or may not pass threshold depending on specifics

    def test_response_with_eu_portal_link(self, evaluator):
        """Test that EU Portal links contribute to actionability score."""
        response = """No funding calls found matching your search.

Try searching the EU Portal directly:
https://ec.europa.eu/info/funding-tenders/opportunities/portal/

You could also contact your National Contact Point for personalized advice.
Consider trying broader search terms.
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["actionability"] >= 6, "Should score for link and next steps"

    def test_response_with_programme_suggestions(self, evaluator):
        """Test that programme mentions contribute to specificity."""
        response = """No matching calls found.

Consider exploring these EU programmes:
- Horizon Europe for research and innovation
- Erasmus+ for education projects
- Creative Europe for cultural projects
- LIFE Programme for environment

Try broader search terms and check the EU Portal.
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["specificity"] >= 15, "Should score high for programme mentions"


# ============================================================================
# Unit Tests for V3ResponseFormatter.format_no_matching_calls
# ============================================================================


class TestNoMatchingCallsFormatter:
    """Test the format_no_matching_calls method directly."""

    @pytest.fixture
    def formatter(self):
        from app.services.response.v3_response_formatter import V3ResponseFormatter

        return V3ResponseFormatter()

    def test_basic_no_results_format(self, formatter):
        """Test basic output of format_no_matching_calls."""
        result = formatter.format_no_matching_calls("")

        assert "No Matching" in result, "Should have title"
        assert "couldn't find" in result.lower() or "no matching" in result.lower()
        assert "suggestion" in result.lower(), "Should have suggestions"
        assert "ec.europa.eu" in result, "Should have EU links"

    def test_query_included_in_output(self, formatter):
        """Test that the original query is shown in the response."""
        query = "underwater basket weaving"
        result = formatter.format_no_matching_calls(query)

        assert query in result, "Should include the original query"

    def test_alternative_suggestions_for_underwater(self, formatter):
        """Test alternative suggestions for 'underwater' keyword."""
        result = formatter.format_no_matching_calls("underwater exploration")

        # Should suggest marine/ocean-related alternatives
        result_lower = result.lower()
        has_marine_suggestion = any(
            term in result_lower for term in ["marine", "ocean", "maritime", "blue economy"]
        )
        assert has_marine_suggestion, "Should suggest marine-related alternatives"

    def test_alternative_suggestions_for_weaving(self, formatter):
        """Test alternative suggestions for craft-related keywords."""
        result = formatter.format_no_matching_calls("basket weaving crafts")

        result_lower = result.lower()
        has_craft_suggestion = any(
            term in result_lower for term in ["textiles", "crafts", "heritage", "traditional"]
        )
        assert has_craft_suggestion, "Should suggest craft-related alternatives"

    def test_programmes_listed(self, formatter):
        """Test that EU programmes are listed."""
        result = formatter.format_no_matching_calls("")

        result_lower = result.lower()
        assert "horizon europe" in result_lower, "Should mention Horizon Europe"
        assert "erasmus" in result_lower, "Should mention Erasmus+"
        assert "creative europe" in result_lower, "Should mention Creative Europe"

    def test_ncp_mentioned(self, formatter):
        """Test that NCP (National Contact Point) is mentioned."""
        result = formatter.format_no_matching_calls("")

        result_lower = result.lower()
        has_ncp = "ncp" in result_lower or "national contact" in result_lower
        assert has_ncp, "Should mention National Contact Point"

    def test_links_included(self, formatter):
        """Test that relevant links are included."""
        result = formatter.format_no_matching_calls("")

        assert "https://" in result or "http://" in result, "Should include links"
        assert "ec.europa.eu" in result, "Should include EU portal link"

    def test_response_structure(self, formatter):
        """Test that response has proper structure with headers."""
        result = formatter.format_no_matching_calls("")

        assert "##" in result or "###" in result, "Should have markdown headers"
        lines = result.split("\n")
        assert len(lines) > 10, "Should be a substantial response"

    def test_no_hallucinated_calls(self, formatter):
        """Test that formatter does not include fake call IDs."""
        result = formatter.format_no_matching_calls("underwater basket weaving")

        # Should NOT contain call IDs
        fake_call_pattern = re.compile(r"HORIZON-[A-Z0-9]+-[0-9]+-", re.IGNORECASE)
        assert not fake_call_pattern.search(result), "Should not include call IDs"


# ============================================================================
# Integration Tests with Live API
# ============================================================================


class TestLiveAPIIntegration:
    """Integration tests against the live MAPIT API."""

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    @pytest.fixture
    def api_client(self):
        return httpx.Client(base_url=API_BASE_URL, timeout=120.0)

    def _is_api_available(self, client):
        """Check if the API is available."""
        try:
            response = client.get("/api/v3/conversation/health")
            return response.status_code == 200
        except Exception:
            return False

    def _send_query_and_get_response(
        self, client, query: str, conversation_id: int = 999055
    ) -> str:
        """Send a query and collect the streaming response."""
        response = client.post(
            f"{CONVERSATION_ENDPOINT}/{conversation_id}/message/stream",
            json={"message": query},
            headers={"Accept": "text/event-stream"},
        )

        if response.status_code != 200:
            pytest.fail(f"API returned status {response.status_code}: {response.text}")

        # Collect tokens from SSE stream
        full_response = ""
        for line in response.iter_lines():
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "token":
                        full_response += data.get("content", "")
                    elif data.get("type") == "error":
                        pytest.fail(f"API error: {data.get('message')}")
                except json.JSONDecodeError:
                    continue

        return full_response

    @pytest.mark.integration
    def test_scenario_055_live_api(self, evaluator, api_client):
        """Test Scenario 055 against the live API."""
        if not self._is_api_available(api_client):
            pytest.skip("API not available")

        # Send the test query
        response = self._send_query_and_get_response(api_client, TEST_QUERY)

        # Evaluate the response
        result = evaluator.evaluate(TEST_QUERY, response)

        # Save results
        RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
        result_data = {
            "scenario": "055_no_matching_calls",
            "query": TEST_QUERY,
            "response": response,
            "evaluation": result,
            "timestamp": datetime.now().isoformat(),
        }
        with open(RESULT_FILE, "w") as f:
            json.dump(result_data, f, indent=2)

        # Assert pass threshold
        assert result["total_score"] >= PASS_THRESHOLD, (
            f"Score {result['total_score']} below threshold {PASS_THRESHOLD}. "
            f"Breakdown: {result['scores']}. Feedback: {result['feedback']}"
        )

    @pytest.mark.integration
    def test_no_hallucinated_calls_live(self, api_client):
        """Verify live API doesn't hallucinate calls for nonsense query."""
        if not self._is_api_available(api_client):
            pytest.skip("API not available")

        response = self._send_query_and_get_response(api_client, TEST_QUERY)
        response_lower = response.lower()

        # Should NOT claim to have found matching calls
        assert not (
            "i found" in response_lower and "call" in response_lower and "funding" in response_lower
        ), "Should not claim to have found matching calls"

        # Should NOT have fake call IDs
        fake_call_pattern = re.compile(r"HORIZON-[A-Z]+-[0-9]+-[0-9]+", re.IGNORECASE)
        fake_calls = fake_call_pattern.findall(response)
        assert not fake_calls, f"Should not have fake call IDs but found: {fake_calls}"

    @pytest.mark.integration
    def test_helpful_response_live(self, api_client):
        """Verify live API provides helpful response (not just 'no results')."""
        if not self._is_api_available(api_client):
            pytest.skip("API not available")

        response = self._send_query_and_get_response(api_client, TEST_QUERY)

        # Response should be substantial
        assert len(response) > 200, "Response should be more than a brief 'no results'"

        # Should have suggestions or alternatives
        response_lower = response.lower()
        has_suggestions = any(
            term in response_lower
            for term in ["suggest", "try", "consider", "alternative", "instead", "broader"]
        )
        assert has_suggestions, "Should provide suggestions for the user"

    @pytest.mark.integration
    def test_variant_queries(self, evaluator, api_client):
        """Test variant nonsense queries to ensure consistent behavior."""
        if not self._is_api_available(api_client):
            pytest.skip("API not available")

        variant_queries = [
            "Find calls for intergalactic time travel research",
            "Open funding for unicorn breeding programmes",
            "EU grants for perpetual motion machine development",
        ]

        for query in variant_queries:
            response = self._send_query_and_get_response(
                api_client, query, 999055 + (hash(query) % 10000)
            )
            result = evaluator.evaluate(query, response)

            # Should at least not hallucinate
            assert (
                result["scores"]["factual_accuracy"] >= 20
            ), f"Query '{query}' should not hallucinate"

            # Should acknowledge no results
            response_lower = response.lower()
            no_results_indicators = [
                "no matching",
                "no funding",
                "couldn't find",
                "no results",
                "unable to find",
            ]
            has_no_results = any(ind in response_lower for ind in no_results_indicators)
            assert has_no_results, f"Query '{query}' should acknowledge no matching results"


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
