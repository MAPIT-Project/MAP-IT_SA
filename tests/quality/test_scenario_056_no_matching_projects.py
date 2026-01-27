"""
Test Scenario 056: No Matching Projects

Tests that MAPIT handles the case of no matching projects gracefully by:
- Acknowledging that no results were found (not empty response)
- Suggesting spelling checks (especially for organization names)
- Recommending alternative search approaches
- Providing links to helpful resources (CORDIS, Partner Search)
- NOT just saying "no results found" without context

Pass threshold: 80/100

Query: "Find projects by organization 'XYZ123NotReal Inc'"
Expected: Explains no results, suggests checking spelling
"""

import json
import re
from datetime import datetime
from pathlib import Path

import httpx
import pytest

# Test configuration
API_BASE_URL = "http://localhost:8000"
CONVERSATION_ENDPOINT = "/api/v3/conversation"
PASS_THRESHOLD = 80
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "no_matching_projects.json"

# The test query - deliberately uses fake organization to get no results
TEST_QUERY = "Find projects by organization 'XYZ123NotReal Inc'"
TEST_ORGANIZATION = "XYZ123NotReal Inc"


class ScenarioEvaluator:
    """Evaluates responses for Scenario 056: No Matching Projects."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Acknowledges no results, doesn't claim to have found any
            "specificity": 25,  # Provides specific suggestions and alternatives
            "factual_accuracy": 25,  # Doesn't hallucinate fake projects
            "actionability": 10,  # Clear next steps for user
        }

    def evaluate(self, query: str, response: str) -> dict:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Must acknowledge no results and NOT claim to have found matching projects
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check that response acknowledges no results
        no_results_indicators = [
            "no matching",
            "no projects found",
            "couldn't find",
            "could not find",
            "no results",
            "unable to find",
            "not find any",
            "no projects for",
        ]
        acknowledges_no_results = any(
            indicator in response_lower for indicator in no_results_indicators
        )

        if acknowledges_no_results:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append(
                "Should clearly acknowledge that no matching projects were found"
            )

        # Check that it does NOT claim to have found matching projects
        # First check for legitimate "found no" / "found 0" patterns that are OK
        legitimate_no_results = re.search(
            r"(found\s+no\s+|found\s+0\s+|didn't find|did not find)", response_lower
        )

        false_positive_indicators = [
            "here are",
            "the following projects",
            "matching projects:",
            "relevant projects:",
            "funded projects:",
        ]
        claims_results = any(indicator in response_lower for indicator in false_positive_indicators)

        # Check for "I found X" where X is a number > 0
        found_with_number = re.search(r"found\s+\*?\*?(\d+)", response_lower)
        if found_with_number and found_with_number.group(1) != "0":
            claims_results = True

        # "I found" is only a problem if NOT followed by "no" or if claiming success
        if "i found" in response_lower and not legitimate_no_results:
            # Check if it's claiming to have found actual projects
            if not acknowledges_no_results:
                claims_results = True

        if not claims_results:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append(
                "Should not claim to have found matching projects when none exist"
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

        # Check for spelling/organization name suggestions (very important for org search)
        spelling_terms = [
            "spelling",
            "check",
            "verify",
            "name",
            "abbreviation",
            "acronym",
            "official",
            "registered",
            "shorter",
        ]
        suggests_spelling_check = sum(1 for term in spelling_terms if term in response_lower)
        if suggests_spelling_check >= 2:
            specificity_score += 10
        elif suggests_spelling_check >= 1:
            specificity_score += 5
            specificity_feedback.append("Should suggest more ways to check organization name")
        else:
            specificity_feedback.append(
                "Should suggest checking spelling or organization name variations"
            )

        # Check for alternative search suggestions
        alternative_terms = [
            "try",
            "consider",
            "alternative",
            "broader",
            "related",
            "instead",
            "different",
            "search",
            "browse",
        ]
        suggests_alternatives = sum(1 for term in alternative_terms if term in response_lower)
        if suggests_alternatives >= 3:
            specificity_score += 8
        elif suggests_alternatives >= 1:
            specificity_score += 4
            specificity_feedback.append("Could provide more alternative search suggestions")
        else:
            specificity_feedback.append("Should suggest alternative search approaches")

        # Check for data source mentions (CORDIS, Partner Search, etc.)
        source_mentions = [
            "cordis",
            "partner search",
            "participant register",
            "pic",
            "database",
        ]
        mentions_sources = sum(1 for s in source_mentions if s in response_lower)
        if mentions_sources >= 2:
            specificity_score += 7
        elif mentions_sources >= 1:
            specificity_score += 4
            specificity_feedback.append("Could mention more data sources/tools")
        else:
            specificity_feedback.append("Should mention relevant data sources like CORDIS")

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        # Does NOT hallucinate fake projects
        accuracy_score = 25  # Start with full score, deduct for issues
        accuracy_feedback = []

        # Check for hallucinated project IDs (fake IDs)
        fake_project_pattern = re.compile(
            r"project\s+id[:\s]+\d{6,}",
            re.IGNORECASE,
        )
        potential_fake_projects = fake_project_pattern.findall(response)
        if potential_fake_projects:
            accuracy_score -= 10
            accuracy_feedback.append(
                f"Appears to hallucinate project IDs: {potential_fake_projects[:3]}"
            )

        # Check for hallucinated project acronyms (all caps 3-10 letters)
        # Only flag if combined with budget/coordinator info suggesting a specific project
        hallucinated_project_pattern = re.compile(
            r"\*\*[A-Z0-9-]{3,10}\*\*[:\s]+",
            re.IGNORECASE,
        )
        potential_acronyms = hallucinated_project_pattern.findall(response)
        if potential_acronyms:
            # Check if there are budget figures or coordinator names nearby
            budget_pattern = re.compile(r"(EUR|€)\s*[\d,]+", re.IGNORECASE)
            if budget_pattern.search(response):
                accuracy_score -= 10
                accuracy_feedback.append(
                    "Appears to include project details for non-existent projects"
                )

        # Check for hallucinated organization participation claims
        participation_claims = [
            "participated in",
            "coordinated",
            "partner in",
            "involved in",
        ]
        for claim in participation_claims:
            # Only flag if claim is about the fake organization
            if (
                claim in response_lower
                and "xyz123notreal" in response_lower
                and "no" not in response_lower.split(claim)[0][-50:]
            ):
                accuracy_score -= 5
                accuracy_feedback.append(
                    f"Should not claim fake organization "
                    f"'{TEST_ORGANIZATION}' participated in projects"
                )
                break

        if accuracy_score == 25:
            accuracy_feedback.append("Good - no hallucinated projects detected")

        scores["factual_accuracy"] = max(accuracy_score, 0)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        # Clear next steps for user
        actionability_score = 0
        actionability_feedback = []

        # Check for links
        has_links = (
            "http" in response_lower
            or "https" in response_lower
            or ".eu" in response_lower
            or "cordis.europa" in response_lower
        )
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
            "search",
            "browse",
            "explore",
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
        response = """## No Projects Found for XYZ123NotReal Inc

I searched through the CORDIS database, but couldn't find any projects for an
organization matching "XYZ123NotReal Inc".

### Suggestions

**1. Check Your Search Terms**
- Verify the organization name spelling
- Try using official/registered organization names
- Try a shorter name (e.g., abbreviations or acronyms)

**2. Try Different Search Approaches**
- Try removing 'Inc' from the name
- Try an abbreviation or acronym
- Search in the organization's original language

**3. Browse by Category**
- Search by country instead
- Browse by research topic or cluster

**4. Consider Data Coverage**
- The organization may not have participated in EU-funded projects yet
- Very recent projects may not be in the database

### Helpful Resources
- [CORDIS Project Database](https://cordis.europa.eu/search)
- [Partner Search Tool](https://ec.europa.eu/info/funding-tenders/partner-search)
- [Participant Register](https://ec.europa.eu/info/funding-tenders/participant-register)

### Next Steps
1. Search CORDIS directly with variations of the organization name
2. Check if the organization is registered in the Participant Register (PIC number)
3. Contact the organization directly for project references
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["query_fulfillment"] >= 35, "Should score high on fulfillment"
        assert result["scores"]["specificity"] >= 20, "Should score high on specificity"
        assert result["scores"]["factual_accuracy"] == 25, "Should have perfect accuracy"
        assert result["scores"]["actionability"] >= 8, "Should score high on actionability"
        assert result["total_score"] >= PASS_THRESHOLD, "Should pass threshold"

    def test_poor_no_results_response(self, evaluator):
        """Test scoring of a poor (too brief) no-results response."""
        response = "No projects found."

        result = evaluator.evaluate(TEST_QUERY, response)

        # Brief response acknowledges no results (30 pts max) but lacks detail
        assert result["scores"]["query_fulfillment"] <= 30, "Brief response limited fulfillment"
        assert result["scores"]["specificity"] <= 10, "No suggestions should score low"
        assert result["scores"]["actionability"] <= 5, "No links/steps should score low"
        assert result["total_score"] < PASS_THRESHOLD, "Should not pass threshold"

    def test_hallucinated_projects_response(self, evaluator):
        """Test scoring penalizes hallucinated project information."""
        response = """I found several projects for XYZ123NotReal Inc:

1. **FAKEPROJECT**: Advanced Research Initiative
   - Project ID: 123456789
   - Budget: EUR 5,000,000
   - Coordinator: XYZ123NotReal Inc

2. **NOTREAL**: Innovation in Technology
   - Budget: EUR 3,000,000
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["query_fulfillment"] <= 20, "Should penalize claiming results"
        assert result["scores"]["factual_accuracy"] <= 15, "Should heavily penalize hallucinations"
        assert result["total_score"] < PASS_THRESHOLD, "Should not pass threshold"

    def test_moderate_response(self, evaluator):
        """Test scoring of a moderate response that mentions some alternatives."""
        response = """No projects found for "XYZ123NotReal Inc" in the database.

This organization doesn't appear in the CORDIS project database.

You could try:
- Checking the spelling of the organization name
- Searching with a shorter name or abbreviation
- Browsing projects by country or topic instead

Visit https://cordis.europa.eu for more search options.
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        # This is actually a good response with clear suggestions and links
        assert result["total_score"] >= 60, "Moderate response should score decently"
        assert result["scores"]["factual_accuracy"] == 25, "No hallucinations"

    def test_detects_false_positives(self, evaluator):
        """Test that evaluator detects false positive claims."""
        response = """I found **15 funded projects** for XYZ123NotReal Inc:

The organization has participated in several EU research projects.
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["query_fulfillment"] <= 20, "Should detect false positive"

    def test_accepts_zero_found(self, evaluator):
        """Test that 'found 0' or 'found no' is accepted as valid."""
        response = """I found no projects matching your search for XYZ123NotReal Inc.

The organization doesn't appear in the CORDIS database. Try checking the spelling
or using an abbreviation.

Visit https://cordis.europa.eu to search directly.
"""
        result = evaluator.evaluate(TEST_QUERY, response)

        # "found no" is correctly detected as not claiming success
        # Score is limited because response is short (5 lines gets +5, not +10)
        assert result["scores"]["query_fulfillment"] >= 20, "Should accept 'found no' as valid"
        # Importantly, it should NOT be penalized for claiming false results
        assert "Should not claim to have found" not in str(result["feedback"])


# ============================================================================
# Unit Tests for V3ResponseFormatter
# ============================================================================


class TestV3ResponseFormatterNoMatchingProjects:
    """Test the V3ResponseFormatter.format_no_matching_projects() method."""

    @pytest.fixture
    def formatter(self):
        from app.services.response.v3_response_formatter import V3ResponseFormatter

        return V3ResponseFormatter()

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    def test_format_no_matching_projects_basic(self, formatter):
        """Test basic no-results formatting without organization name."""
        response = formatter.format_no_matching_projects("machine learning projects")

        assert "No Matching Projects Found" in response
        assert "couldn't find" in response.lower()
        assert "cordis" in response.lower()
        assert "suggestions" in response.lower()
        assert "next steps" in response.lower()

    def test_format_no_matching_projects_with_organization(self, formatter):
        """Test no-results formatting for organization search."""
        response = formatter.format_no_matching_projects(
            TEST_QUERY, organization_name=TEST_ORGANIZATION
        )

        assert TEST_ORGANIZATION in response
        assert "couldn't find" in response.lower()
        assert "spelling" in response.lower()
        assert "abbreviation" in response.lower() or "shorter" in response.lower()
        assert "cordis" in response.lower()
        assert "participant register" in response.lower() or "pic" in response.lower()

    def test_format_no_matching_projects_has_links(self, formatter):
        """Test that response includes helpful links."""
        response = formatter.format_no_matching_projects(TEST_QUERY)

        assert "https://" in response or "http://" in response
        assert "cordis.europa.eu" in response.lower()

    def test_format_no_matching_projects_has_next_steps(self, formatter):
        """Test that response includes actionable next steps."""
        response = formatter.format_no_matching_projects(TEST_QUERY)

        assert "next steps" in response.lower() or "recommended" in response.lower()
        # Should have numbered steps or bullet points
        assert re.search(r"(^|\n)\d\.", response) or re.search(r"(^|\n)•", response)

    def test_format_no_matching_projects_scores_passing(self, formatter, evaluator):
        """Test that formatted response scores above threshold."""
        response = formatter.format_no_matching_projects(
            TEST_QUERY, organization_name=TEST_ORGANIZATION
        )
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["passed"], f"Response should pass threshold. Score: {result['total_score']}"
        assert result["total_score"] >= PASS_THRESHOLD

    def test_format_no_matching_projects_organization_search_scores_passing(
        self, formatter, evaluator
    ):
        """Test that organization-specific response scores above threshold."""
        response = formatter.format_no_matching_projects(
            "Find projects by Fake Organization GmbH", organization_name="Fake Organization GmbH"
        )
        result = evaluator.evaluate("Find projects by Fake Organization GmbH", response)

        assert result["total_score"] >= PASS_THRESHOLD, (
            f"Score: {result['total_score']}, Feedback: {result['feedback']}"
        )

    def test_format_no_matching_projects_no_hallucinations(self, formatter, evaluator):
        """Test that response doesn't hallucinate projects."""
        response = formatter.format_no_matching_projects(
            TEST_QUERY, organization_name=TEST_ORGANIZATION
        )
        result = evaluator.evaluate(TEST_QUERY, response)

        assert result["scores"]["factual_accuracy"] == 25, "Should not hallucinate any projects"


class TestSuggestAlternativeOrganizationNames:
    """Test the _suggest_alternative_organization_names helper method."""

    @pytest.fixture
    def formatter(self):
        from app.services.response.v3_response_formatter import V3ResponseFormatter

        return V3ResponseFormatter()

    def test_suggests_removing_inc(self, formatter):
        """Test that it suggests removing Inc suffix."""
        suggestions = formatter._suggest_alternative_organization_names("XYZ Company Inc")

        assert any("inc" in s.lower() for s in suggestions)

    def test_suggests_removing_gmbh(self, formatter):
        """Test that it suggests removing GmbH suffix."""
        suggestions = formatter._suggest_alternative_organization_names("Firma Test GmbH")

        assert any("gmbh" in s.lower() for s in suggestions)

    def test_suggests_abbreviation_for_long_names(self, formatter):
        """Test that it suggests abbreviations for long names."""
        suggestions = formatter._suggest_alternative_organization_names(
            "Technical University of Munich Department of Computer Science"
        )

        assert any("abbreviation" in s.lower() or "acronym" in s.lower() for s in suggestions)

    def test_suggests_removing_the(self, formatter):
        """Test that it suggests removing 'The' prefix."""
        suggestions = formatter._suggest_alternative_organization_names(
            "The National Research Institute"
        )

        assert any("the" in s.lower() for s in suggestions)

    def test_suggests_full_name_for_abbreviation(self, formatter):
        """Test that it suggests full name for abbreviations."""
        suggestions = formatter._suggest_alternative_organization_names("MIT")

        assert any("full" in s.lower() for s in suggestions)

    def test_returns_max_four_suggestions(self, formatter):
        """Test that it returns at most 4 suggestions."""
        suggestions = formatter._suggest_alternative_organization_names(
            "The Very Long Organization Name Inc. & Co."
        )

        assert len(suggestions) <= 4


class TestSuggestAlternativeProjectSearchTerms:
    """Test the _suggest_alternative_project_search_terms helper method."""

    @pytest.fixture
    def formatter(self):
        from app.services.response.v3_response_formatter import V3ResponseFormatter

        return V3ResponseFormatter()

    def test_suggests_ai_alternatives(self, formatter):
        """Test that it suggests AI-related alternatives."""
        suggestions = formatter._suggest_alternative_project_search_terms("ai research")

        assert any(
            "artificial intelligence" in s.lower() or "machine learning" in s.lower()
            for s in suggestions
        )

    def test_suggests_hydrogen_alternatives(self, formatter):
        """Test that it suggests hydrogen-related alternatives."""
        suggestions = formatter._suggest_alternative_project_search_terms("hydrogen energy")

        assert any("green hydrogen" in s.lower() or "fuel cell" in s.lower() for s in suggestions)

    def test_suggests_general_advice_for_long_queries(self, formatter):
        """Test that it suggests simplifying long queries."""
        suggestions = formatter._suggest_alternative_project_search_terms(
            "very specific long query with many keywords that is unlikely to match"
        )

        assert any("fewer" in s.lower() or "general" in s.lower() for s in suggestions)

    def test_returns_empty_for_empty_query(self, formatter):
        """Test that empty query returns empty suggestions."""
        suggestions = formatter._suggest_alternative_project_search_terms("")

        assert suggestions == []


# ============================================================================
# Integration Tests (require running API)
# ============================================================================


@pytest.mark.integration
class TestScenario056Integration:
    """Integration tests that require the API to be running."""

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    @pytest.mark.asyncio
    async def test_scenario_056_live_api(self, evaluator):
        """Test the actual API response for no matching projects."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create a new conversation
            conv_response = await client.post(
                f"{API_BASE_URL}{CONVERSATION_ENDPOINT}",
                json={"user_id": 1},
            )
            if conv_response.status_code != 200:
                pytest.skip("API not available")

            conv_id = conv_response.json().get("conversation_id")

            # Send the test query
            response = await client.post(
                f"{API_BASE_URL}{CONVERSATION_ENDPOINT}/{conv_id}/message",
                json={"message": TEST_QUERY, "user_id": 1},
            )

            if response.status_code != 200:
                pytest.skip(f"API returned {response.status_code}")

            result = response.json()
            response_text = result.get("response", "")

            # Evaluate the response
            evaluation = evaluator.evaluate(TEST_QUERY, response_text)

            # Save results
            RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(RESULT_FILE, "w") as f:
                json.dump(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "query": TEST_QUERY,
                        "response": response_text,
                        "evaluation": evaluation,
                    },
                    f,
                    indent=2,
                )

            # Assert passing score
            assert evaluation["passed"], (
                f"Score {evaluation['total_score']}/{PASS_THRESHOLD} - "
                f"Feedback: {evaluation['feedback']}"
            )

    @pytest.mark.asyncio
    async def test_scenario_056_streaming(self, evaluator):
        """Test the streaming API response for no matching projects."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create a new conversation
            conv_response = await client.post(
                f"{API_BASE_URL}{CONVERSATION_ENDPOINT}",
                json={"user_id": 1},
            )
            if conv_response.status_code != 200:
                pytest.skip("API not available")

            conv_id = conv_response.json().get("conversation_id")

            # Send the test query via streaming
            response_text = ""
            async with client.stream(
                "POST",
                f"{API_BASE_URL}{CONVERSATION_ENDPOINT}/{conv_id}/message/stream",
                json={"message": TEST_QUERY, "user_id": 1},
            ) as response:
                if response.status_code != 200:
                    pytest.skip(f"API returned {response.status_code}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            if event.get("type") == "token":
                                response_text += event.get("content", "")
                        except json.JSONDecodeError:
                            continue

            # Evaluate the response
            evaluation = evaluator.evaluate(TEST_QUERY, response_text)

            assert evaluation["passed"], (
                f"Score {evaluation['total_score']}/{PASS_THRESHOLD} - "
                f"Feedback: {evaluation['feedback']}"
            )

    @pytest.mark.asyncio
    async def test_generic_project_search_no_results(self, evaluator):
        """Test generic project search that returns no results."""
        query = "Find projects about underwater telepathic communication"

        async with httpx.AsyncClient(timeout=60.0) as client:
            conv_response = await client.post(
                f"{API_BASE_URL}{CONVERSATION_ENDPOINT}",
                json={"user_id": 1},
            )
            if conv_response.status_code != 200:
                pytest.skip("API not available")

            conv_id = conv_response.json().get("conversation_id")

            response = await client.post(
                f"{API_BASE_URL}{CONVERSATION_ENDPOINT}/{conv_id}/message",
                json={"message": query, "user_id": 1},
            )

            if response.status_code != 200:
                pytest.skip(f"API returned {response.status_code}")

            result = response.json()
            response_text = result.get("response", "")

            evaluation = evaluator.evaluate(query, response_text)

            # Should handle gracefully
            assert evaluation["scores"]["factual_accuracy"] >= 20, "Should not hallucinate"

    @pytest.mark.asyncio
    async def test_organization_with_special_characters(self, evaluator):
        """Test organization search with special characters."""
        query = "Find projects by organization 'Test & Fake GmbH'"

        async with httpx.AsyncClient(timeout=60.0) as client:
            conv_response = await client.post(
                f"{API_BASE_URL}{CONVERSATION_ENDPOINT}",
                json={"user_id": 1},
            )
            if conv_response.status_code != 200:
                pytest.skip("API not available")

            conv_id = conv_response.json().get("conversation_id")

            response = await client.post(
                f"{API_BASE_URL}{CONVERSATION_ENDPOINT}/{conv_id}/message",
                json={"message": query, "user_id": 1},
            )

            if response.status_code != 200:
                pytest.skip(f"API returned {response.status_code}")

            result = response.json()
            response_text = result.get("response", "")

            # Should handle special characters gracefully
            assert "error" not in response_text.lower() or "not find" in response_text.lower()
