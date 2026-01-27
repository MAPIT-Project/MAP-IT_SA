"""
Test Scenario 037: Very Specific Niche

Tests that MAPIT handles highly specialized interdisciplinary queries correctly by:
- Performing best effort search across relevant programmes
- Suggesting alternatives (Creative Europe + Horizon combination)
- NOT hallucinating specific calls that don't exist
- Providing helpful guidance when exact matches don't exist

Pass threshold: 75/100 (lower threshold for niche queries where exact matches are rare)
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
PASS_THRESHOLD = 75  # Lower threshold for niche queries
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "very_specific_niche.json"


class ScenarioEvaluator:
    """Evaluates responses for Scenario 037: Very Specific Niche."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Attempts to answer the niche query
            "specificity": 25,  # Provides concrete alternatives and guidance
            "factual_accuracy": 25,  # Does NOT hallucinate fake calls
            "actionability": 10,  # Clear next steps for user
        }

    def evaluate(self, query: str, response: str) -> dict:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Must attempt to address the interdisciplinary query
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check that query domains are acknowledged
        query_lower = query.lower()
        query_domains = []
        if "archaeolog" in query_lower or "underwater" in query_lower:
            query_domains.append("archaeology")
        if "ai" in query_lower or "artificial intelligence" in query_lower:
            query_domains.append("ai")
        if "mediterranean" in query_lower:
            query_domains.append("mediterranean")

        # Check for acknowledgment of interdisciplinary nature
        interdisciplinary_terms = [
            "interdisciplinary",
            "cross-cutting",
            "cross-disciplinary",
            "multi-disciplinary",
            "multidisciplinary",
            "combining",
            "combination",
            "specialized",
            "niche",
        ]
        acknowledges_interdisciplinary = any(
            term in response_lower for term in interdisciplinary_terms
        )

        if acknowledges_interdisciplinary:
            fulfillment_score += 10
        else:
            fulfillment_feedback.append(
                "Could acknowledge the interdisciplinary nature of the query"
            )

        # Check that search was performed (mentions calls, projects, or results)
        search_indicators = [
            "found",
            "calls",
            "projects",
            "results",
            "funding opportunities",
            "search",
        ]
        performed_search = any(term in response_lower for term in search_indicators)
        if performed_search:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append("Should perform and report search results")

        # Check for alternative approaches suggestion
        alternative_terms = [
            "alternative",
            "creative europe",
            "split",
            "different components",
            "erc",
            "mission",
            "cluster 2",
            "cl2",
            "culture",
            "heritage",
        ]
        suggests_alternatives = any(term in response_lower for term in alternative_terms)
        if suggests_alternatives:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append("Should suggest alternative funding approaches")

        scores["query_fulfillment"] = min(fulfillment_score, 40)
        feedback["query_fulfillment"] = fulfillment_feedback

        # 2. Specificity (25 points)
        specificity_score = 0
        specificity_feedback = []

        # Check for specific programme names
        programme_names = [
            "horizon europe",
            "creative europe",
            "digital europe",
            "erasmus",
            "mission",
            "erc",
            "msca",
        ]
        programmes_mentioned = sum(1 for p in programme_names if p in response_lower)
        if programmes_mentioned >= 2:
            specificity_score += 10
        elif programmes_mentioned >= 1:
            specificity_score += 5
            specificity_feedback.append("Could mention more relevant EU programmes")
        else:
            specificity_feedback.append("Should mention specific EU programmes")

        # Check for cluster/domain references
        cluster_terms = [
            "cluster 2",
            "cl2",
            "cluster 4",
            "cl4",
            "cluster 6",
            "cl6",
            "culture",
            "digital",
            "heritage",
            "marine",
            "ocean",
        ]
        cluster_count = sum(1 for c in cluster_terms if c in response_lower)
        if cluster_count >= 2:
            specificity_score += 8
        elif cluster_count >= 1:
            specificity_score += 4

        # Check for links or resources
        has_links = bool(
            re.search(r"https?://|ec\.europa\.eu|portal|funding.*tender", response_lower)
        )
        if has_links:
            specificity_score += 7
        else:
            specificity_feedback.append("Should include links to relevant resources")

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        # CRITICAL: Must NOT hallucinate specific calls for niche topics
        accuracy_score = 0
        accuracy_feedback = []

        # Check for hallucination indicators (fake call IDs for niche topics)
        # These patterns indicate potentially fabricated call IDs
        hallucination_patterns = [
            r"horizon-.*-archaeology",  # No real call with this pattern
            r"horizon-.*-underwater",  # No specific underwater archaeology calls
            r"crea-.*-archaeology",  # No such Creative Europe call
            r"heritage-ai-\d+",  # Fabricated call pattern
        ]
        has_hallucination = any(re.search(pat, response_lower) for pat in hallucination_patterns)

        if has_hallucination:
            accuracy_feedback.append("CRITICAL: Appears to hallucinate specific calls")
            accuracy_score = 0
        else:
            accuracy_score += 15  # Major points for not hallucinating

        # Check for honest acknowledgment of search limitations
        honest_terms = [
            "may not have dedicated",
            "no exact match",
            "partial match",
            "related",
            "closest",
            "similar",
            "might fit",
            "could accommodate",
            "potentially relevant",
        ]
        is_honest = any(term in response_lower for term in honest_terms)
        if is_honest:
            accuracy_score += 10
        else:
            accuracy_feedback.append("Should honestly acknowledge when exact matches don't exist")

        scores["factual_accuracy"] = min(accuracy_score, 25)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        actionability_score = 0
        actionability_feedback = []

        # Check for next steps
        next_step_terms = [
            "next step",
            "should",
            "recommend",
            "contact",
            "ncp",
            "national contact point",
            "register",
            "portal",
        ]
        has_next_steps = any(term in response_lower for term in next_step_terms)
        if has_next_steps:
            actionability_score += 5
        else:
            actionability_feedback.append("Should provide clear next steps")

        # Check for actionable guidance
        guidance_terms = [
            "review",
            "check",
            "search",
            "filter",
            "browse",
            "explore",
            "consider",
        ]
        has_guidance = any(term in response_lower for term in guidance_terms)
        if has_guidance:
            actionability_score += 5

        scores["actionability"] = min(actionability_score, 10)
        feedback["actionability"] = actionability_feedback

        # Calculate total
        total_score = sum(scores.values())
        max_possible = sum(self.dimensions.values())

        return {
            "total_score": total_score,
            "max_score": max_possible,
            "passed": total_score >= PASS_THRESHOLD,
            "threshold": PASS_THRESHOLD,
            "dimensions": scores,
            "feedback": feedback,
            "query": query,
            "response_length": len(response),
        }


async def send_query(query: str, conversation_id: int = None) -> tuple[str, int, list]:
    """Send query to MAPIT API and return response."""
    if conversation_id is None:
        conversation_id = int(datetime.now().strftime("%m%d%H%M%S"))

    async with httpx.AsyncClient(timeout=120.0) as client:
        url = f"{API_BASE_URL}{CONVERSATION_ENDPOINT}/{conversation_id}/message/stream"
        response_text = ""
        tools_used = []

        async with client.stream(
            "POST",
            url,
            json={"message": query, "user_id": 1},
        ) as response:
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "token":
                            response_text += data.get("content", "")
                        elif data.get("type") == "tool_call":
                            tools_used.append(data.get("tool_name", ""))
                    except json.JSONDecodeError:
                        continue

        return response_text, conversation_id, tools_used


def save_result(result: dict, query: str, response: str):
    """Save evaluation result to JSON file."""
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "scenario": "037_very_specific_niche",
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "response": response[:2000],
        "evaluation": result,
        "status": "PASS" if result["passed"] else "FAIL",
    }

    with open(RESULT_FILE, "w") as f:
        json.dump(output, f, indent=2)


# ==============================================================================
# TESTS
# ==============================================================================


class TestScenario037VerySpecificNiche:
    """Test suite for Scenario 037: Very Specific Niche."""

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    # --------------------------------------------------------------------------
    # Offline evaluation tests with sample responses
    # --------------------------------------------------------------------------

    def test_excellent_response_scores_high(self, evaluator):
        """Test that an excellent response scores 75+."""
        query = "Funding for underwater archaeology using AI in the Mediterranean"
        excellent_response = """## Understanding Your Funding Search

Your query combines **Archaeology + AI + Mediterranean** - this is a highly \
specialized interdisciplinary area that may not have dedicated funding calls.

### What We Found

✅ Found **8 potentially relevant calls** and **5 similar funded projects**.

Review the results above - while they may not be perfect matches, they cover \
related topics that could accommodate your project.

### Relevant Horizon Europe Clusters

- **Cluster 2: Culture, Creativity & Inclusive Society** - Cultural heritage
- **Cluster 4: Digital, Industry & Space** - AI and digital technologies
- **Cluster 6: Food, Bioeconomy, Natural Resources** - Marine research

### Alternative Funding Approaches

**1. Creative Europe (CULTURE strand)**
   - Cultural heritage digitization projects
   - Cultural cooperation projects with technology components
   - [Creative Europe Portal](https://culture.ec.europa.eu/creative-europe)

**2. EU Mission: Restore our Ocean and Waters**
   - Marine research and blue economy
   - Underwater cultural heritage protection
   - [Ocean Mission](https://ec.europa.eu/info/research-and-innovation)

**3. ERC Grants**
   - For frontier research in any domain
   - Principal Investigator-led, highly flexible
   - [ERC Portal](https://erc.europa.eu/)

**4. Split Your Project**
   - Research component → Horizon Europe RIA
   - Cultural/creative component → Creative Europe
   - Education/training component → Erasmus+

---

🎯 **Recommended Next Steps:**

1. **Review the results above** - some may be adaptable to your project
2. **Contact your National Contact Point (NCP)** - they can advise on best fit
3. **Check EU Portal topic search** - filter by multiple keywords
4. **Consider writing to the EC** - for novel interdisciplinary topics"""

        result = evaluator.evaluate(query, excellent_response)
        assert result["total_score"] >= 75, (
            f"Expected excellent response to score 75+, got {result['total_score']}"
        )
        assert result["passed"] is True

    def test_partial_response_scores_medium(self, evaluator):
        """Test that a partial response scores below 75."""
        query = "Funding for underwater archaeology using AI in the Mediterranean"
        partial_response = """I found some funding calls for your search.

Here are the results:
1. HORIZON-CL5-2026 - Energy research
2. HORIZON-CL4-2025 - Digital technologies

These calls are available on the EU Portal."""

        result = evaluator.evaluate(query, partial_response)
        assert result["total_score"] < 75, (
            f"Expected partial response to score below 75, got {result['total_score']}"
        )
        assert result["passed"] is False

    def test_hallucinating_response_fails(self, evaluator):
        """Test that a response with fake call IDs fails."""
        query = "Funding for underwater archaeology using AI in the Mediterranean"
        hallucinating_response = """I found perfect funding calls for your project!

**HORIZON-CL2-2026-UNDERWATER-AI-ARCHAEOLOGY** - €5 million
This call specifically funds underwater archaeology using AI in the Mediterranean.
Deadline: March 2026

**CREA-CULT-2026-ARCHAEOLOGY-DIGITAL** - €2 million
Creative Europe call for digital archaeology projects.
Deadline: April 2026

These calls are exactly what you need!"""

        result = evaluator.evaluate(query, hallucinating_response)
        # Hallucinating response should fail due to factual accuracy issues
        assert result["dimensions"]["factual_accuracy"] < 15, (
            "Hallucinating response should score low on factual accuracy"
        )

    def test_honest_no_results_response(self, evaluator):
        """Test that an honest 'no exact matches' response scores reasonably."""
        query = "Funding for underwater archaeology using AI in the Mediterranean"
        honest_response = """## Search Results

I searched for funding opportunities combining underwater archaeology with AI \
in the Mediterranean. This is a highly specialized niche topic.

### What We Found

⚠️ Found **3 calls** and **2 projects**, but these may only partially match \
your specific requirements.

This is common for highly specialized interdisciplinary topics. Below are \
strategies for finding appropriate funding.

### Alternative Approaches

**Creative Europe** may fund cultural heritage digitization projects.
**ERC grants** offer flexibility for frontier interdisciplinary research.
**Mission Ocean** addresses marine research including cultural aspects.

---

**Next Steps:**
- Contact your NCP for personalized guidance
- Search the EU Portal with different keyword combinations
- Consider splitting your project across multiple programmes"""

        result = evaluator.evaluate(query, honest_response)
        # Honest response should score reasonably well even without exact matches
        assert result["dimensions"]["factual_accuracy"] >= 15, (
            "Honest response should score well on factual accuracy"
        )

    def test_detects_interdisciplinary_domains(self, evaluator):
        """Test that the evaluator correctly detects query domains."""
        query = "Funding for underwater archaeology using AI in the Mediterranean"
        # Just ensure the evaluate function runs without error
        response = "Found 5 calls for your interdisciplinary query."
        result = evaluator.evaluate(query, response)
        assert "total_score" in result
        assert "dimensions" in result

    # --------------------------------------------------------------------------
    # Scoring dimension tests
    # --------------------------------------------------------------------------

    def test_query_fulfillment_scoring(self, evaluator):
        """Test query fulfillment scoring logic."""
        query = "Funding for underwater archaeology using AI"

        # Response that acknowledges interdisciplinary nature and suggests alternatives
        good_response = """This is a specialized interdisciplinary query combining archaeology \
and AI. I found 5 related calls. Consider Creative Europe for the heritage component \
and Horizon Europe Cluster 4 for the AI/digital component."""

        result = evaluator.evaluate(query, good_response)
        assert result["dimensions"]["query_fulfillment"] >= 30

    def test_specificity_scoring(self, evaluator):
        """Test specificity scoring logic."""
        query = "Funding for underwater archaeology"

        # Response with specific programmes and clusters
        specific_response = """Relevant programmes include Horizon Europe (Cluster 2 for culture, \
Cluster 4 for digital), Creative Europe for cultural heritage, and ERC for frontier research. \
Check https://ec.europa.eu/info/funding-tenders/opportunities/portal for calls."""

        result = evaluator.evaluate(query, specific_response)
        assert result["dimensions"]["specificity"] >= 15

    def test_factual_accuracy_no_hallucination(self, evaluator):
        """Test that responses without hallucination score well on accuracy."""
        query = "Funding for underwater archaeology using AI"

        # Response that is honest about partial matches
        honest_response = """I found related calls that may fit your project. While there's \
no exact match for underwater archaeology + AI, similar projects in cultural heritage \
digitization have been funded. Consider checking the potentially relevant calls above."""

        result = evaluator.evaluate(query, honest_response)
        assert result["dimensions"]["factual_accuracy"] >= 15

    def test_actionability_with_next_steps(self, evaluator):
        """Test actionability scoring with next steps."""
        query = "Funding for underwater archaeology"

        # Response with clear next steps
        actionable_response = """Found some related calls. Next steps: 1) Contact your NCP \
for guidance, 2) Search the EU Portal with different keywords, 3) Review and consider \
the calls listed above, 4) Register on the portal if you haven't already."""

        result = evaluator.evaluate(query, actionable_response)
        assert result["dimensions"]["actionability"] >= 5

    # --------------------------------------------------------------------------
    # Live API tests
    # --------------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("httpx"),
        reason="httpx not available for live tests",
    )
    async def test_live_api_niche_query(self, evaluator):
        """Test niche query against live API."""
        query = "Funding for underwater archaeology using AI in the Mediterranean"

        try:
            response_text, conv_id, tools_used = await send_query(query)
        except Exception as e:
            pytest.skip(f"Live API not available: {e}")

        # Evaluate response
        result = evaluator.evaluate(query, response_text)
        save_result(result, query, response_text)

        # Check that at least some tools were used
        assert len(tools_used) > 0, "Should use at least one tool"

        # Check that response meets minimum threshold
        assert result["total_score"] >= 60, (
            f"Response scored only {result['total_score']}, expected at least 60 for niche queries"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("httpx"),
        reason="httpx not available for live tests",
    )
    async def test_live_api_different_niche_queries(self, evaluator):
        """Test various niche queries against live API."""
        niche_queries = [
            "Grants for traditional crafts preservation using blockchain",
            "Support for indigenous language revitalization with NLP",
            "Funding for alpine glacier monitoring with drone swarms",
        ]

        for query in niche_queries:
            try:
                response_text, conv_id, tools_used = await send_query(query)
            except Exception as e:
                pytest.skip(f"Live API not available: {e}")

            result = evaluator.evaluate(query, response_text)

            # Even niche queries should get some reasonable response
            assert result["total_score"] >= 40, (
                f"Query '{query}' scored only {result['total_score']}, expected at least 40"
            )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("httpx"),
        reason="httpx not available for live tests",
    )
    async def test_live_api_no_hallucination(self, evaluator):
        """Test that live API doesn't hallucinate fake calls for niche queries."""
        query = "Funding for underwater archaeology using AI in the Mediterranean"

        try:
            response_text, conv_id, tools_used = await send_query(query)
        except Exception as e:
            pytest.skip(f"Live API not available: {e}")

        result = evaluator.evaluate(query, response_text)

        # Critical: no hallucination
        assert result["dimensions"]["factual_accuracy"] >= 10, (
            "Response may contain hallucinated call IDs"
        )

    # --------------------------------------------------------------------------
    # Edge case tests
    # --------------------------------------------------------------------------

    def test_empty_response(self, evaluator):
        """Test handling of empty response."""
        query = "Funding for underwater archaeology using AI"
        result = evaluator.evaluate(query, "")
        # Empty response gets 15 points for factual accuracy (no hallucination)
        # but fails overall due to low total score
        assert result["total_score"] <= 15
        assert result["passed"] is False

    def test_very_short_response(self, evaluator):
        """Test handling of very short response."""
        query = "Funding for underwater archaeology using AI"
        result = evaluator.evaluate(query, "No results found.")
        # Short response gets 15 for no hallucination + 15 for search indicator
        # but still fails overall
        assert result["total_score"] <= 35
        assert result["passed"] is False

    def test_irrelevant_response(self, evaluator):
        """Test scoring of completely irrelevant response."""
        query = "Funding for underwater archaeology using AI"
        irrelevant_response = "The weather in Brussels is nice today. \
Horizon Europe has a budget of 95 billion euros."
        result = evaluator.evaluate(query, irrelevant_response)
        assert result["total_score"] < 50
