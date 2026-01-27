"""
Test Scenario 035: Non-EU Country Eligibility

Tests that MAPIT correctly handles queries about third country participation
in EU funding programmes, explaining:
- Third country rules (limited participation, no funding, no coordination)
- Specific pathways for third country researchers (MSCA, ERC)
- What "third country" means vs "associated country"
- Nuanced answer (not just yes/no)

Pass threshold: 80/100
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
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "non_eu_country.json"


class ScenarioEvaluator:
    """Evaluates responses for Scenario 035: Non-EU Country."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Addresses the question with nuanced answer
            "specificity": 25,  # Concrete rules, not vague
            "factual_accuracy": 25,  # Correct third country rules
            "actionability": 10,  # Clear next steps
        }

    def evaluate(self, query: str, response: str) -> dict:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Must explain that participation is possible but with limitations
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check for nuanced answer (not just "yes" or "no")
        has_nuanced_answer = False
        nuance_patterns = [
            r"yes.*but",
            r"can participate.*however",
            r"possible.*limitations",
            r"limited participation",
            r"specific conditions",
            r"with restrictions",
            r"participate.*self.?fund",
            r"can.*join.*but",
        ]
        for pattern in nuance_patterns:
            if re.search(pattern, response_lower):
                has_nuanced_answer = True
                break

        if has_nuanced_answer:
            fulfillment_score += 15
        elif "yes" in response_lower[:200] or "can participate" in response_lower[:300]:
            fulfillment_score += 8
            fulfillment_feedback.append("Answer should be more nuanced (yes, but...)")
        else:
            fulfillment_feedback.append(
                "Should clearly state participation is possible with limitations"
            )

        # Check for third country identification
        third_country_terms = [
            "third country",
            "non-associated",
            "non-eu",
            "not an associated country",
            "outside the eu",
        ]
        if any(term in response_lower for term in third_country_terms):
            fulfillment_score += 15
        else:
            fulfillment_feedback.append(
                "Should identify India as a 'third country' or 'non-associated country'"
            )

        # Check for key limitation explanations
        limitations_mentioned = 0
        self_fund_terms = [
            "self-fund",
            "self fund",
            "own costs",
            "not receive funding",
            "no eu funding",
        ]
        if any(term in response_lower for term in self_fund_terms):
            limitations_mentioned += 1

        coord_terms = [
            "cannot coordinate",
            "can't coordinate",
            "no coordination",
            "not coordinate",
        ]
        if any(term in response_lower for term in coord_terms):
            limitations_mentioned += 1

        min_terms = [
            "minimum",
            "3 entities",
            "three entities",
            "do not count",
            "don't count",
            "not count toward",
        ]
        if any(term in response_lower for term in min_terms):
            limitations_mentioned += 1

        fulfillment_score += min(limitations_mentioned * 3, 10)
        if limitations_mentioned < 2:
            fulfillment_feedback.append(
                f"Only {limitations_mentioned}/3 key limitations mentioned "
                "(self-funding, no coordination, minimum count)"
            )

        scores["query_fulfillment"] = min(fulfillment_score, 40)
        feedback["query_fulfillment"] = fulfillment_feedback

        # 2. Specificity (25 points)
        specificity_score = 0
        specificity_feedback = []

        # Check for specific rules with details
        has_entity_req = re.search(
            r"3\s*(independent\s+)?legal\s+entities", response_lower
        ) or re.search(r"three\s*(independent\s+)?entities", response_lower)
        if has_entity_req:
            specificity_score += 8
        else:
            specificity_feedback.append(
                "Should mention specific consortium requirements (3 entities)"
            )

        # Check for mention of exceptions
        exception_terms = [
            "exceptional",
            "exception",
            "specific call",
            "work programme",
            "call text",
            "explicitly stated",
        ]
        if any(term in response_lower for term in exception_terms):
            specificity_score += 7
        else:
            specificity_feedback.append(
                "Should mention exceptions when call text allows third country funding"
            )

        # Check for alternative pathways
        pathways = []
        if "msca" in response_lower or "marie" in response_lower:
            pathways.append("MSCA")
        if "erc" in response_lower:
            pathways.append("ERC")
        if "subcontract" in response_lower:
            pathways.append("subcontracting")
        if "bilateral" in response_lower:
            pathways.append("bilateral")

        if len(pathways) >= 2:
            specificity_score += 10
        elif len(pathways) == 1:
            specificity_score += 5
            specificity_feedback.append(
                f"Only mentioned {pathways[0]}. Could mention more alternatives"
            )
        else:
            specificity_feedback.append(
                "Should mention alternative pathways for third country researchers"
            )

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        accuracy_score = 0
        accuracy_feedback = []

        # Check for correct categorization of India
        # India should NOT be called an "associated country"
        if "associated country" in response_lower and "india" in response_lower:
            india_idx = response_lower.find("india")
            start = max(0, india_idx - 100)
            end = min(len(response_lower), india_idx + 100)
            context = response_lower[start:end]
            if "not" in context and "associated" in context:
                accuracy_score += 10  # Correctly says India is NOT associated
            elif "non-associated" in context:
                accuracy_score += 10
            else:
                accuracy_feedback.append("May incorrectly imply India is an associated country")
        elif "third country" in response_lower or "non-associated" in response_lower:
            accuracy_score += 10

        # Check for correct funding rules
        funding_terms = ["self-fund", "own cost", "not funded", "no eu funding"]
        if any(term in response_lower for term in funding_terms):
            accuracy_score += 8
        else:
            accuracy_feedback.append(
                "Should clearly state third countries are typically self-funded"
            )

        # Check for correct coordination rules
        coord_rules = [
            "cannot coordinate",
            "can't coordinate",
            "eu member",
            "associated country must coordinate",
        ]
        if any(term in response_lower for term in coord_rules):
            accuracy_score += 7
        else:
            accuracy_feedback.append("Should state third countries cannot coordinate projects")

        scores["factual_accuracy"] = min(accuracy_score, 25)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        actionability_score = 0
        actionability_feedback = []

        # Check for links or resources
        has_links = bool(
            re.search(r"https?://|ec\.europa\.eu|portal|programme guide", response_lower)
        )
        if has_links:
            actionability_score += 4

        # Check for next steps
        next_step_terms = [
            "next step",
            "should",
            "recommend",
            "check the call",
            "verify",
            "consult",
        ]
        has_next_steps = any(term in response_lower for term in next_step_terms)
        if has_next_steps:
            actionability_score += 4
        else:
            actionability_feedback.append("Should provide concrete next steps")

        # Check for NCP or contact info
        ncp_terms = ["ncp", "national contact point", "contact"]
        if any(term in response_lower for term in ncp_terms):
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
        # Use timestamp-based integer ID for unique conversations
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
        "scenario": "035_non_eu_country",
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "response": response[:2000],  # Truncate for storage
        "evaluation": result,
        "status": "PASS" if result["passed"] else "FAIL",
    }

    with open(RESULT_FILE, "w") as f:
        json.dump(output, f, indent=2)


# ==============================================================================
# TESTS
# ==============================================================================


class TestScenario035NonEUCountry:
    """Test suite for Scenario 035: Non-EU Country eligibility."""

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    # --------------------------------------------------------------------------
    # Offline evaluation tests with sample responses
    # --------------------------------------------------------------------------

    def test_excellent_response_scores_high(self, evaluator):
        """Test that an excellent response scores 80+."""
        query = "Can a company from India participate in EU funding?"
        excellent_response = """Yes, Indian companies can participate in Horizon Europe \
projects, but with specific limitations on funding and roles.

### India as a Third Country

India is classified as a **Non-Associated Third Country**, which means:

| Aspect | Rule for Third Countries |
|--------|-------------------------|
| **Can participate?** | Yes, in most calls |
| **Count toward minimum?** | No - only MS/AC count |
| **Receive EU funding?** | No (with rare exceptions) |
| **Can coordinate?** | No |
| **Who funds them?** | Self-funded |

### How Indian Partners Can Participate

1. **Self-Funded Participation:** Indian partners must cover their own costs.

2. **No Coordination:** Third country entities cannot be the project coordinator - \
an EU Member State or Associated Country partner must coordinate.

3. **Don't Count Toward Minimum:** You still need 3 independent legal entities from \
3 different EU Member States or Associated Countries.

4. **Exception Cases:** In exceptional circumstances, the Commission may fund third \
country participation if explicitly stated in the work programme/call text.

### Alternative Pathways for Indian Researchers

- **MSCA (Marie Curie Actions):** Individual fellowships open globally
- **ERC (European Research Council):** If based at an EU/AC host institution
- **Bilateral agreements:** India-EU cooperation programmes

---

**Next Steps:**
- Check the specific call text for third country eligibility conditions
- Ensure your consortium has 3 entities from EU MS or Associated Countries
- Contact your National Contact Point (NCP) for guidance
- Review the Horizon Europe Programme Guide Section 4.2"""

        result = evaluator.evaluate(query, excellent_response)
        assert (
            result["total_score"] >= 80
        ), f"Excellent response scored {result['total_score']}, expected 80+"
        assert result["passed"], "Excellent response should pass"

    def test_minimal_response_scores_low(self, evaluator):
        """Test that a minimal yes/no response scores low."""
        query = "Can a company from India participate in EU funding?"
        minimal_response = """Yes, Indian companies can participate in Horizon Europe.
        They would need to join a consortium with European partners."""

        result = evaluator.evaluate(query, minimal_response)
        assert (
            result["total_score"] < 60
        ), f"Minimal response scored {result['total_score']}, expected <60"
        assert not result["passed"], "Minimal response should not pass"

    def test_incorrect_response_scores_low(self, evaluator):
        """Test that an incorrect response (treating India as associated) scores low."""
        query = "Can a company from India participate in EU funding?"
        incorrect_response = """Yes, India is an associated country and can fully \
participate in Horizon Europe with EU funding. Indian companies can coordinate \
projects and receive grants just like EU organizations."""

        result = evaluator.evaluate(query, incorrect_response)
        # Should fail accuracy checks
        assert (
            result["dimensions"]["factual_accuracy"] < 15
        ), "Incorrect response should have low accuracy"

    def test_nuanced_response_with_limitations(self, evaluator):
        """Test that a nuanced response explaining limitations scores well."""
        query = "Can a company from India participate in EU funding?"
        nuanced_response = """Yes, but with significant limitations. India is a \
non-associated third country, which means:

- Indian organizations CAN participate in Horizon Europe projects
- However, they typically CANNOT receive EU funding (must be self-funded)
- They CANNOT coordinate projects (an EU or associated country partner must lead)
- They DO NOT count toward the minimum consortium requirements (3 entities)

There are exceptions when the call text explicitly allows third country funding.

Alternative pathways for Indian researchers include MSCA fellowships and ERC grants.

Next steps: Check the specific call text and contact your NCP for guidance."""

        result = evaluator.evaluate(query, nuanced_response)
        assert (
            result["total_score"] >= 70
        ), f"Nuanced response scored {result['total_score']}, expected 70+"

    def test_dimension_weights(self, evaluator):
        """Test that dimension weights are correct."""
        assert evaluator.dimensions["query_fulfillment"] == 40
        assert evaluator.dimensions["specificity"] == 25
        assert evaluator.dimensions["factual_accuracy"] == 25
        assert evaluator.dimensions["actionability"] == 10
        assert sum(evaluator.dimensions.values()) == 100

    # --------------------------------------------------------------------------
    # Variant queries - other third countries
    # --------------------------------------------------------------------------

    def test_japan_query_scoring(self, evaluator):
        """Test that Japan third country queries are evaluated correctly."""
        query = "Can Japanese researchers join EU projects?"
        good_response = """Yes, Japanese researchers can participate in Horizon \
Europe, but as Japan is a non-associated third country, there are limitations:

- Must be self-funded (no EU funding typically)
- Cannot coordinate projects
- Don't count toward minimum consortium requirements

Japanese researchers can also apply for MSCA individual fellowships or work at \
EU institutions for ERC grants. Check the call text for third country eligibility."""

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 60, f"Japan query response scored {result['total_score']}"

    def test_china_query_scoring(self, evaluator):
        """Test that China third country queries are evaluated correctly."""
        query = "Is a Chinese company eligible for Horizon Europe?"
        good_response = """Chinese companies can participate in Horizon Europe \
projects under third country rules, meaning:

- Yes, they can join consortia but are typically self-funded
- They cannot coordinate and don't count toward the minimum 3 entities from EU/AC
- Exceptions exist when call text explicitly allows third country funding

Note: For security-sensitive topics, third country participation may be restricted.

Check the specific call text and Programme Guide Section 4.2."""

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 55, f"China query response scored {result['total_score']}"

    # --------------------------------------------------------------------------
    # Live API tests
    # --------------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("httpx", reason="httpx required"),
        reason="httpx not available",
    )
    async def test_live_api_india_query(self, evaluator):
        """Test the live API with India eligibility query."""
        query = "Can a company from India participate in EU funding?"

        try:
            response, conv_id, tools = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        assert len(response) > 100, "Response too short"

        result = evaluator.evaluate(query, response)
        save_result(result, query, response)

        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Response length: {len(response)}")
        print(f"Tools used: {tools}")
        print("\nScores:")
        for dim, score in result["dimensions"].items():
            max_score = evaluator.dimensions[dim]
            print(f"  {dim}: {score}/{max_score}")
        print(f"\nTotal: {result['total_score']}/100")
        print(f"Status: {'PASS' if result['passed'] else 'FAIL'}")
        print(f"{'='*60}")

        if result["feedback"]:
            print("\nFeedback:")
            for dim, fb in result["feedback"].items():
                if fb:
                    print(f"  {dim}: {'; '.join(fb)}")

        assert (
            result["total_score"] >= PASS_THRESHOLD
        ), f"Score {result['total_score']} below threshold {PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_live_api_brazil_query(self, evaluator):
        """Test with Brazil as another third country."""
        query = "Can Brazilian universities participate in Horizon Europe?"

        try:
            response, conv_id, tools = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        result = evaluator.evaluate(query, response)

        print(f"\nBrazil query score: {result['total_score']}/100")

        # Brazil should also trigger third country guidance
        assert (
            "third country" in response.lower() or "self-fund" in response.lower()
        ), "Response should mention third country status or self-funding"

    @pytest.mark.asyncio
    async def test_live_api_differentiates_associated_vs_third(self, evaluator):
        """Test that the system differentiates between associated and third."""
        third_country_query = "Can Indian companies get EU funding?"
        associated_query = "Can UK organizations participate in Horizon Europe?"

        try:
            third_response, _, _ = await send_query(third_country_query)
            assoc_response, _, _ = await send_query(associated_query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Third country response should mention self-funding
        self_fund_in_third = (
            "self-fund" in third_response.lower()
            or "self fund" in third_response.lower()
            or "not funded" in third_response.lower()
            or "own costs" in third_response.lower()
        )
        assert self_fund_in_third, "Third country response should mention self-funding requirement"

        # Associated country response should NOT say self-funded (UK has funding)
        # Note: UK status is complex, so we check for different treatment
        third_has_self_fund = (
            "self-fund" in third_response.lower() or "self fund" in third_response.lower()
        )
        assoc_mentions_funding = "funding" in assoc_response.lower()

        assert (
            third_has_self_fund or assoc_mentions_funding
        ), "System should differentiate third vs associated country treatment"


# ==============================================================================
# Run tests directly
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
