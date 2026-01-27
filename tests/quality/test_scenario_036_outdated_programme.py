"""
Test Scenario 036: Outdated Programme

Tests that MAPIT correctly handles queries about closed/historical programmes
like Horizon 2020 and FP7, explaining:
- Programme is closed and no longer accepting applications
- Redirects user to current programme (Horizon Europe)
- Provides helpful transition information
- Does NOT pretend the old programme is still open

Pass threshold: 80/100
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
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "outdated_programme.json"


class ScenarioEvaluator:
    """Evaluates responses for Scenario 036: Outdated Programme."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Addresses the question clearly
            "specificity": 25,  # Concrete details about closure and alternative
            "factual_accuracy": 25,  # Correct H2020 status and HE redirect
            "actionability": 10,  # Clear next steps for user
        }

    def evaluate(self, query: str, response: str) -> dict:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Must clearly state H2020 is closed and redirect to HE
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check for clear "no" answer about H2020 applications
        closed_patterns = [
            r"no.*cannot",
            r"no.*can't",
            r"no.*not possible",
            r"cannot apply",
            r"can't apply",
            r"closed",
            r"ended",
            r"no longer",
            r"finished",
            r"concluded",
            r"not accepting",
        ]
        has_clear_no = any(re.search(pat, response_lower) for pat in closed_patterns)

        if has_clear_no:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append(
                "Should clearly state that H2020 applications are no longer possible"
            )

        # Check for H2020/Horizon 2020 mention
        h2020_mentioned = (
            "h2020" in response_lower
            or "horizon 2020" in response_lower
            or "h 2020" in response_lower
        )
        if h2020_mentioned:
            fulfillment_score += 10
        else:
            fulfillment_feedback.append("Should explicitly mention H2020/Horizon 2020")

        # Check for Horizon Europe redirect
        he_patterns = [
            "horizon europe",
            "current programme",
            "active programme",
            "2021-2027",
            "successor",
            "replacement",
        ]
        has_he_redirect = any(pat in response_lower for pat in he_patterns)
        if has_he_redirect:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append("Should redirect user to Horizon Europe")

        scores["query_fulfillment"] = min(fulfillment_score, 40)
        feedback["query_fulfillment"] = fulfillment_feedback

        # 2. Specificity (25 points)
        specificity_score = 0
        specificity_feedback = []

        # Check for specific dates/timeframes
        date_patterns = [
            r"2014.*2020",
            r"2020",
            r"2021",
            r"2021.*2027",
            r"ended in",
            r"closed in",
            r"final",
        ]
        has_dates = any(re.search(pat, response_lower) for pat in date_patterns)
        if has_dates:
            specificity_score += 8
        else:
            specificity_feedback.append("Should mention specific programme dates")

        # Check for budget or scale information about Horizon Europe
        budget_patterns = [
            r"€\s*\d+",
            r"\d+\s*(billion|million|b|m)",
            r"budget",
            r"95\.5",
        ]
        has_budget = any(re.search(pat, response_lower) for pat in budget_patterns)
        if has_budget:
            specificity_score += 7
        else:
            specificity_feedback.append(
                "Could mention Horizon Europe budget to encourage transition"
            )

        # Check for types of funding available in Horizon Europe
        funding_types = [
            "ria",
            "ia",
            "erc",
            "msca",
            "eic",
            "pillar",
            "cluster",
            "collaborative",
        ]
        types_mentioned = sum(1 for ft in funding_types if ft in response_lower)
        if types_mentioned >= 2:
            specificity_score += 10
        elif types_mentioned == 1:
            specificity_score += 5
            specificity_feedback.append("Could mention more Horizon Europe funding types")
        else:
            specificity_feedback.append("Should mention available Horizon Europe funding types")

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        accuracy_score = 0
        accuracy_feedback = []

        # Must NOT claim H2020 is still open
        open_claims = [
            "h2020 is open",
            "horizon 2020 is open",
            "can still apply to h2020",
            "can still apply to horizon 2020",
            "h2020 calls are open",
        ]
        claims_open = any(claim in response_lower for claim in open_claims)
        if claims_open:
            accuracy_feedback.append("CRITICAL: Incorrectly claims H2020 is still open")
            accuracy_score = 0
        else:
            accuracy_score += 15  # Major points for not lying

        # Check that H2020 is correctly described as closed/ended
        closed_terms = [
            "closed",
            "ended",
            "concluded",
            "finished",
            "no longer accepting",
            "permanently closed",
        ]
        correctly_closed = any(term in response_lower for term in closed_terms)
        if correctly_closed:
            accuracy_score += 10
        else:
            accuracy_feedback.append("Should explicitly state H2020 is closed/ended")

        scores["factual_accuracy"] = min(accuracy_score, 25)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        actionability_score = 0
        actionability_feedback = []

        # Check for portal/links
        has_links = bool(
            re.search(r"https?://|ec\.europa\.eu|portal|funding.*tender", response_lower)
        )
        if has_links:
            actionability_score += 4

        # Check for clear next steps
        next_step_terms = [
            "next step",
            "should",
            "recommend",
            "visit",
            "register",
            "search for",
            "find call",
        ]
        has_next_steps = any(term in response_lower for term in next_step_terms)
        if has_next_steps:
            actionability_score += 4
        else:
            actionability_feedback.append("Should provide clear next steps for user")

        # Check for NCP or support mention
        support_terms = ["ncp", "national contact point", "help", "support", "contact"]
        if any(term in response_lower for term in support_terms):
            actionability_score += 2

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
                            tools_used.append(data.get("tool", ""))
                    except json.JSONDecodeError:
                        continue

        return response_text, conversation_id, tools_used


def save_result(result: dict, query: str, response: str):
    """Save evaluation result to JSON file."""
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "scenario": "036_outdated_programme",
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


class TestScenario036OutdatedProgramme:
    """Test suite for Scenario 036: Outdated Programme."""

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    # --------------------------------------------------------------------------
    # Offline evaluation tests with sample responses
    # --------------------------------------------------------------------------

    def test_excellent_response_scores_high(self, evaluator):
        """Test that an excellent response scores 80+."""
        query = "Can I still apply to Horizon 2020?"
        excellent_response = """**No, you cannot apply to Horizon 2020.** All funding \
calls under Horizon 2020 have permanently closed.

## Programme Status

| Programme | Duration | Current Status |
|-----------|----------|----------------|
| **Horizon 2020** | 2014-2020 | **Closed** - All calls ended |
| **Horizon Europe** | 2021-2027 | **Active** - Applications open |

### What Happened to H2020?

Horizon 2020 was the EU's previous research and innovation framework programme \
running from 2014 to 2020. The final calls closed in late 2020, and all awarded \
projects are now in their final stages or completed.

### Your Alternative: Horizon Europe

Horizon Europe is the current programme with a budget of **€95.5 billion**. It offers:

- **RIA (Research and Innovation Actions)** - Collaborative research
- **IA (Innovation Actions)** - Closer to market
- **ERC Grants** - Frontier research
- **MSCA** - Researcher mobility
- **EIC Accelerator** - SME support

---

**Next Steps:**

1. Visit the [EU Funding Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal)
2. Search for open Horizon Europe calls in your topic area
3. Register and get a PIC number
4. Contact your National Contact Point for guidance"""

        result = evaluator.evaluate(query, excellent_response)
        assert result["total_score"] >= 80, (
            f"Excellent response scored {result['total_score']}, expected 80+"
        )
        assert result["passed"], "Excellent response should pass"

    def test_incorrect_response_fails_accuracy(self, evaluator):
        """Test that a response claiming H2020 is open fails accuracy."""
        query = "Can I still apply to Horizon 2020?"
        incorrect_response = """Yes, you can still apply to Horizon 2020! There \
are many open calls available. H2020 is open for applications and you should \
check the portal for current opportunities."""

        result = evaluator.evaluate(query, incorrect_response)
        assert result["dimensions"]["factual_accuracy"] < 15, (
            "Incorrect response should fail accuracy"
        )
        assert not result["passed"], "Incorrect response should not pass"

    def test_vague_response_scores_lower(self, evaluator):
        """Test that a vague response without specifics scores lower."""
        query = "Can I still apply to Horizon 2020?"
        vague_response = """Horizon 2020 has ended. You might want to look at \
other EU funding programmes that are currently available."""

        result = evaluator.evaluate(query, vague_response)
        # Should get some points for saying ended but miss specificity
        assert result["dimensions"]["specificity"] < 20, (
            "Vague response should have lower specificity"
        )

    def test_good_response_with_redirect(self, evaluator):
        """Test that a good response with clear redirect scores well."""
        query = "Can I still apply to Horizon 2020?"
        good_response = """No, Horizon 2020 calls are permanently closed. The \
programme ran from 2014-2020 and is no longer accepting applications.

The current EU research programme is **Horizon Europe** (2021-2027) with a \
budget of €95.5 billion. You should apply there instead.

Horizon Europe offers RIA, IA, ERC, and MSCA funding types.

Visit https://ec.europa.eu/info/funding-tenders/ to find open calls."""

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 70, f"Good response scored {result['total_score']}"

    def test_dimension_weights(self, evaluator):
        """Test that dimension weights are correct."""
        assert evaluator.dimensions["query_fulfillment"] == 40
        assert evaluator.dimensions["specificity"] == 25
        assert evaluator.dimensions["factual_accuracy"] == 25
        assert evaluator.dimensions["actionability"] == 10
        assert sum(evaluator.dimensions.values()) == 100

    # --------------------------------------------------------------------------
    # Variant queries - other outdated programmes
    # --------------------------------------------------------------------------

    def test_fp7_query_scoring(self, evaluator):
        """Test that FP7 queries are evaluated correctly."""
        query = "Is FP7 still accepting applications?"
        good_response = """No, FP7 (Framework Programme 7) closed in 2013. It ran \
from 2007-2013 and all projects have long since completed.

The current programme is Horizon Europe (2021-2027). Before that was Horizon 2020 \
(2014-2020), which has also closed.

You should apply to Horizon Europe for current funding opportunities."""

        result = evaluator.evaluate(query, good_response)
        # FP7 response should pass basic checks even if H2020 not explicitly mentioned
        assert result["dimensions"]["factual_accuracy"] >= 15, (
            "FP7 closure response should be accurate"
        )

    def test_combined_h2020_fp7_query(self, evaluator):
        """Test response to query about both old programmes."""
        query = "Can I apply to H2020 or FP7?"
        good_response = """No, neither H2020 nor FP7 are accepting applications:

- **FP7** (2007-2013): Closed, all projects completed
- **H2020** (2014-2020): Closed, final projects concluding

The current programme is **Horizon Europe** (2021-2027) with €95.5 billion budget.

Next steps: Visit the EU Funding Portal for open Horizon Europe calls."""

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 65, f"Combined query scored {result['total_score']}"

    # --------------------------------------------------------------------------
    # Live API tests
    # --------------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("httpx", reason="httpx required"),
        reason="httpx not available",
    )
    async def test_live_api_h2020_query(self, evaluator):
        """Test the live API with H2020 query - primary test."""
        query = "Can I still apply to Horizon 2020?"

        try:
            response, conv_id, tools = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        assert len(response) > 100, "Response too short"

        result = evaluator.evaluate(query, response)
        save_result(result, query, response)

        print(f"\n{'=' * 60}")
        print(f"Query: {query}")
        print(f"Response length: {len(response)}")
        print(f"Tools used: {tools}")
        print("\nScores:")
        for dim, score in result["dimensions"].items():
            max_score = evaluator.dimensions[dim]
            print(f"  {dim}: {score}/{max_score}")
        print(f"\nTotal: {result['total_score']}/100")
        print(f"Status: {'PASS' if result['passed'] else 'FAIL'}")
        print(f"{'=' * 60}")

        if result["feedback"]:
            print("\nFeedback:")
            for dim, fb in result["feedback"].items():
                if fb:
                    print(f"  {dim}: {'; '.join(fb)}")

        assert result["total_score"] >= PASS_THRESHOLD, (
            f"Score {result['total_score']} below threshold {PASS_THRESHOLD}"
        )

    @pytest.mark.asyncio
    async def test_live_api_does_not_claim_h2020_open(self, evaluator):
        """Verify the system never claims H2020 is open."""
        query = "Can I still apply to Horizon 2020?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Critical check: Must NOT claim H2020 is open
        open_claims = [
            "h2020 is open",
            "horizon 2020 is open",
            "yes, you can apply to h2020",
            "yes, you can apply to horizon 2020",
            "h2020 calls are open",
            "horizon 2020 calls are open",
        ]

        for claim in open_claims:
            assert claim not in response_lower, f"Response incorrectly claims: {claim}"

    @pytest.mark.asyncio
    async def test_live_api_mentions_horizon_europe(self, evaluator):
        """Verify the system redirects to Horizon Europe."""
        query = "Can I still apply to Horizon 2020?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should mention Horizon Europe as the alternative
        assert "horizon europe" in response_lower, "Response should redirect to Horizon Europe"

    @pytest.mark.asyncio
    async def test_live_api_fp7_variant(self, evaluator):
        """Test FP7 query variant."""
        query = "Is FP7 still open for applications?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should indicate FP7 is closed
        closed_indicators = ["closed", "ended", "no longer", "finished", "cannot"]
        assert any(ind in response_lower for ind in closed_indicators), (
            "FP7 response should indicate programme is closed"
        )

    @pytest.mark.asyncio
    async def test_live_api_provides_next_steps(self, evaluator):
        """Verify the response includes actionable next steps."""
        query = "Can I still apply to Horizon 2020?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should have next steps or portal reference
        action_indicators = [
            "next step",
            "portal",
            "ec.europa.eu",
            "visit",
            "register",
            "search",
            "find",
        ]
        has_action = any(ind in response_lower for ind in action_indicators)
        assert has_action, "Response should provide actionable next steps"

    @pytest.mark.asyncio
    async def test_live_api_informal_h2020_variant(self, evaluator):
        """Test informal variant of the H2020 query."""
        query = "I want to apply to H2020, is it still possible?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should still recognize H2020 is closed
        assert any(term in response_lower for term in ["closed", "ended", "no longer", "cannot"]), (
            "Response should indicate H2020 is closed"
        )

        # Should redirect to current programme
        assert "horizon europe" in response_lower, "Response should redirect to Horizon Europe"


# ==============================================================================
# Run tests directly
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
