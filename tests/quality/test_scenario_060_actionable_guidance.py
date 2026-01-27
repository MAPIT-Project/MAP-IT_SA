# isort: skip_file
"""
Test Scenario 060: Actionable Guidance

Tests that MAPIT provides step-by-step guidance with links and concrete actions
when users ask how to apply for EU funding programmes.

PRD Reference:
- Query: "How do I apply for Horizon Europe?"
- Expected: Step-by-step guidance, links, concrete actions
- Verify: User could follow steps
- Fix if: Vague, no clear actions
- Pass threshold: 80/100

The response should:
1. Provide clear step-by-step instructions
2. Include links to official resources (EU Portal, NCP)
3. Have concrete, actionable steps
4. Mention EU Login and PIC registration
5. Include deadlines or timing guidance
6. Not be vague or general
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

# Test configuration
API_BASE_URL = "http://localhost:8000"
CONVERSATION_ENDPOINT = "/api/v3/conversation"
PASS_THRESHOLD = 80
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "actionable_guidance.json"


class ActionableGuidanceEvaluator:
    """Evaluates responses for Scenario 060: Actionable Guidance."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Answers "How do I apply?" completely
            "specificity": 25,  # Concrete details (steps, links, resources)
            "factual_accuracy": 25,  # Correct information about application process
            "actionability": 10,  # Clear next steps user can follow
        }

    def evaluate(self, query: str, response: str) -> dict[str, Any]:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Must provide clear guidance on how to apply
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check for step-by-step structure (15 points)
        step_patterns = [
            r"step\s*\d",
            r"step\s+1",
            r"step\s+one",
            r"first,?\s+(you|create|register|visit)",
            r"1\.\s+",
            r"\*\*1\.",
            r"first step",
            r"to start",
            r"##\s*step",
        ]
        has_steps = any(re.search(pat, response_lower) for pat in step_patterns)
        if has_steps:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append("Should provide step-by-step guidance")

        # Check for registration process explanation (15 points)
        registration_patterns = [
            "eu login",
            "create.*account",
            "register",
            "pic",
            "participant identification code",
            "sign up",
        ]
        registration_found = sum(1 for pat in registration_patterns if pat in response_lower)
        if registration_found >= 3:
            fulfillment_score += 15
        elif registration_found >= 2:
            fulfillment_score += 10
        elif registration_found >= 1:
            fulfillment_score += 5
        else:
            fulfillment_feedback.append("Should explain registration process (EU Login, PIC)")

        # Check for call/opportunity finding guidance (10 points)
        call_patterns = [
            "funding.*call",
            "open call",
            "topic",
            "find.*opportunit",
            "browse.*call",
            "search.*call",
            "portal",
            "tender",
        ]
        has_call_guidance = any(pat in response_lower for pat in call_patterns)
        if has_call_guidance:
            fulfillment_score += 10
        else:
            fulfillment_feedback.append("Should explain how to find calls/opportunities")

        scores["query_fulfillment"] = min(fulfillment_score, 40)
        feedback["query_fulfillment"] = fulfillment_feedback

        # 2. Specificity (25 points)
        specificity_score = 0
        specificity_feedback = []

        # Check for EU Portal link (8 points)
        portal_patterns = [
            r"ec\.europa\.eu",
            r"europa\.eu",
            r"funding.*tenders.*portal",
            r"participant.*portal",
            r"\[.*portal.*\]\(http",
        ]
        has_portal_link = any(re.search(pat, response_lower) for pat in portal_patterns)
        if has_portal_link:
            specificity_score += 8
        else:
            specificity_feedback.append("Should include EU Portal link")

        # Check for NCP mention (7 points)
        ncp_patterns = [
            "ncp",
            "national contact point",
        ]
        has_ncp = any(pat in response_lower for pat in ncp_patterns)
        if has_ncp:
            specificity_score += 7
        else:
            specificity_feedback.append("Should mention National Contact Points (NCPs)")

        # Check for specific tools/resources (5 points)
        resource_patterns = [
            "partner search",
            "cordis",
            "work programme",
            "info day",
        ]
        resources_found = sum(1 for pat in resource_patterns if pat in response_lower)
        if resources_found >= 2:
            specificity_score += 5
        elif resources_found >= 1:
            specificity_score += 3
        else:
            specificity_feedback.append(
                "Could mention more resources (Partner Search, CORDIS, Work Programmes)"
            )

        # Check for consortium/partnership mention (5 points)
        partnership_patterns = [
            "consortium",
            "partner",
            "collaboration",
            "countries",
        ]
        has_partnership = any(pat in response_lower for pat in partnership_patterns)
        if has_partnership:
            specificity_score += 5
        else:
            specificity_feedback.append("Should mention consortium/partnership requirements")

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        accuracy_score = 0
        accuracy_feedback = []

        # Correct registration sequence (10 points)
        # EU Login first, then PIC/organization registration
        has_eu_login = "eu login" in response_lower or "ecas" in response_lower
        has_pic = "pic" in response_lower or "participant identification" in response_lower
        if has_eu_login and has_pic:
            accuracy_score += 10
        elif has_eu_login or has_pic:
            accuracy_score += 5
        else:
            accuracy_feedback.append("Should mention EU Login and PIC registration steps")

        # Correct programme information (10 points)
        # Horizon Europe is collaborative, requires partners, etc.
        programme_facts = [
            ("horizon europe" in response_lower, 3),
            ("international" in response_lower or "partner" in response_lower, 3),
            ("deadline" in response_lower or "call" in response_lower, 2),
            ("proposal" in response_lower or "application" in response_lower, 2),
        ]
        for has_fact, points in programme_facts:
            if has_fact:
                accuracy_score += points

        # Should NOT contain obvious errors or outdated info
        error_patterns = [
            "horizon 2020",  # Outdated programme (unless explicitly comparing)
            "fp7",  # Very old framework
        ]
        for error in error_patterns:
            if error in response_lower and "previous" not in response_lower:
                accuracy_score -= 5
                accuracy_feedback.append(f"Contains potentially outdated reference: {error}")

        accuracy_score = max(0, accuracy_score)
        scores["factual_accuracy"] = min(accuracy_score, 25)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        actionability_score = 0
        actionability_feedback = []

        # Clear call-to-action (4 points)
        cta_patterns = [
            "your next",
            "next step",
            "start by",
            "you should",
            "we recommend",
            "first thing",
            "get started",
            "begin with",
        ]
        has_cta = any(pat in response_lower for pat in cta_patterns)
        if has_cta:
            actionability_score += 4
        else:
            actionability_feedback.append("Should have a clear call-to-action")

        # Links present (3 points)
        has_links = bool(
            re.search(r"https?://|\.eu\)|\.eu/|europa\.eu|\[.*\]\(http", response_lower)
        )
        if has_links:
            actionability_score += 3
        else:
            actionability_feedback.append("Should include clickable links")

        # Concrete timing (3 points)
        timing_patterns = [
            r"\d+\s*minute",
            r"\d+\s*hour",
            r"\d+\s*day",
            r"\d+\s*week",
            r"\d+\s*month",
            "immediately",
            "right away",
            "quickly",
        ]
        has_timing = any(re.search(pat, response_lower) for pat in timing_patterns)
        if has_timing:
            actionability_score += 3

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


async def send_query(query: str, conversation_id: int | None = None) -> tuple[str, int, list]:
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
        "scenario": "060_actionable_guidance",
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


class TestScenario060ActionableGuidance:
    """Test suite for Scenario 060: Actionable Guidance."""

    @pytest.fixture
    def evaluator(self):
        return ActionableGuidanceEvaluator()

    # --------------------------------------------------------------------------
    # Offline evaluation tests with sample responses
    # --------------------------------------------------------------------------

    def test_excellent_response_scores_high(self, evaluator):
        """Test that an excellent response scores 80+."""
        query = "How do I apply for Horizon Europe?"
        excellent_response = """Here's a **step-by-step guide** to applying for \
Horizon Europe funding:

## Step 1: Create Your EU Login Account (5 minutes)

Your first step is to create an EU Login account - this is your personal access to all EU services.

**How to do it:**
1. Go to [EU Login](https://webgate.ec.europa.eu/cas/)
2. Enter your email and create a password
3. Verify your email

---

## Step 2: Register Your Organization & Get a PIC (15-30 minutes)

The **PIC (Participant Identification Code)** is your organization's unique identifier.

1. Log into the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/)
2. Go to "My Organisation" → "Register Organisation"
3. Enter your organization's legal details
4. Receive your 9-digit PIC number

---

## Step 3: Find Suitable Calls

1. Browse the [EU Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search)
2. Filter by Horizon Europe and your research area
3. Check the Work Programme for detailed topic descriptions

---

## Step 4: Build Your Consortium

Most Horizon Europe calls require international partnerships \
(3+ organizations from different EU countries).

**Where to find partners:**
- [Partner Search Tool](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/partner-search)
- [CORDIS](https://cordis.europa.eu/) - Find active project coordinators

---

## Step 5: Contact Your National Contact Point (NCP)

**NCPs are FREE expert advisors** who can:
- Help you find the right call
- Review your proposal draft
- Connect you with partners

Find your NCP: [NCP Network Directory](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)

---

## Step 6: Prepare and Submit Your Proposal

1. Download the proposal template from the call page
2. Complete all sections following the evaluation criteria
3. Submit via the Funding & Tenders Portal before the deadline

---

🎯 **Your Next Step:** Start by creating your \
[EU Login account](https://webgate.ec.europa.eu/cas/) - it only takes 5 minutes!"""

        result = evaluator.evaluate(query, excellent_response)
        assert (
            result["total_score"] >= 80
        ), f"Excellent response scored {result['total_score']}, expected 80+"
        assert result["passed"], "Excellent response should pass"

    def test_vague_response_scores_low(self, evaluator):
        """Test that a vague response without concrete steps scores low."""
        query = "How do I apply for Horizon Europe?"
        vague_response = """To apply for Horizon Europe, you need to find a suitable call and
submit a proposal. The process involves registration and preparation.
Good luck with your application!"""

        result = evaluator.evaluate(query, vague_response)
        assert (
            result["total_score"] < 60
        ), f"Vague response scored {result['total_score']}, expected < 60"
        assert not result["passed"], "Vague response should not pass"

    def test_partial_response_scores_medium(self, evaluator):
        """Test that a partial response scores in the middle."""
        query = "How do I apply for Horizon Europe?"
        partial_response = """To apply for Horizon Europe, follow these steps:

1. Create an EU Login account
2. Register your organization and get a PIC number
3. Find a suitable call on the EU Portal
4. Build a consortium with partners from different countries
5. Submit your proposal

Visit the Funding & Tenders Portal at ec.europa.eu for more details."""

        result = evaluator.evaluate(query, partial_response)
        # Should score reasonably but not perfectly (missing links, NCP, detailed guidance)
        assert (
            50 <= result["total_score"] < 85
        ), f"Partial response scored {result['total_score']}, expected 50-85"

    def test_no_links_response_penalized(self, evaluator):
        """Test that a response without links scores lower on actionability."""
        query = "How do I apply for Horizon Europe?"
        no_links_response = """To apply for Horizon Europe:

Step 1: Create an EU Login account on the European Commission website
Step 2: Register your organization and get a PIC number
Step 3: Find open calls in your research area
Step 4: Build a consortium with international partners
Step 5: Contact your National Contact Point for guidance
Step 6: Submit your proposal before the deadline"""

        result = evaluator.evaluate(query, no_links_response)
        # Should have lower actionability score due to missing links
        assert (
            result["dimensions"]["actionability"] <= 7
        ), "Response without links should have limited actionability score"

    def test_dimension_weights_are_correct(self, evaluator):
        """Test that dimension weights sum to 100."""
        assert sum(evaluator.dimensions.values()) == 100
        assert evaluator.dimensions["query_fulfillment"] == 40
        assert evaluator.dimensions["specificity"] == 25
        assert evaluator.dimensions["factual_accuracy"] == 25
        assert evaluator.dimensions["actionability"] == 10

    # --------------------------------------------------------------------------
    # Query variants tests
    # --------------------------------------------------------------------------

    def test_variant_apply_to_horizon(self, evaluator):
        """Test variant: How can I apply to Horizon Europe?"""
        query = "How can I apply to Horizon Europe?"
        good_response = """Here's how to apply to Horizon Europe:

## Step 1: Create EU Login Account
Go to [EU Login](https://webgate.ec.europa.eu/cas/) and create your account.

## Step 2: Register for a PIC
Register your organization on the \
[Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/) \
to get your Participant Identification Code.

## Step 3: Find Calls
Browse open calls at ec.europa.eu/info/funding-tenders/

## Step 4: Build Consortium
Find partners through the Partner Search tool. \
Most calls require 3+ organizations from different countries.

## Step 5: Contact NCP
Your National Contact Point can review your proposal for free.

## Step 6: Submit
Prepare and submit your proposal via the portal before the deadline.

**Next step:** Create your EU Login account today!"""

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 70, f"Variant scored {result['total_score']}"

    def test_variant_erasmus_application(self, evaluator):
        """Test that the evaluator works for other programmes too."""
        query = "How do I apply for Erasmus+?"
        good_response = """Here's how to apply for Erasmus+ funding:

## Step 1: Create an EU Login Account (5 minutes)
Visit [EU Login](https://webgate.ec.europa.eu/cas/) to create your personal access.

## Step 2: Register Your Organization
Get your PIC (Participant Identification Code) on the Funding & Tenders Portal at ec.europa.eu.

## Step 3: Find the Right Action
Erasmus+ has multiple Key Actions:
- KA1: Learning Mobility
- KA2: Partnerships
- KA3: Policy Support

## Step 4: Check Deadlines
Deadlines vary by action - check the Programme Guide for exact dates.

## Step 5: Contact Your National Agency
For KA1 and KA2, contact your National Agency (NCP equivalent) for guidance.

## Step 6: Submit Your Application
Prepare your proposal following the Programme Guide and submit before the deadline.

**Your next step:** Create your EU Login account and identify which \
Erasmus+ action fits your project!"""

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 65, f"Erasmus variant scored {result['total_score']}"

    # --------------------------------------------------------------------------
    # Specific requirement checks
    # --------------------------------------------------------------------------

    def test_steps_detection(self, evaluator):
        """Test that step-by-step structure is properly detected."""
        query = "How do I apply?"

        with_steps = """Step 1: Create EU Login
Step 2: Register organization
Step 3: Find calls"""
        without_steps = "You need to register and find calls."

        result_with = evaluator.evaluate(query, with_steps)
        result_without = evaluator.evaluate(query, without_steps)

        assert (
            result_with["dimensions"]["query_fulfillment"]
            > result_without["dimensions"]["query_fulfillment"]
        ), "Step-by-step structure should improve fulfillment score"

    def test_eu_portal_link_detection(self, evaluator):
        """Test that EU Portal links are properly detected."""
        query = "How do I apply?"

        with_link = "Visit the portal at https://ec.europa.eu/info/funding-tenders/"
        without_link = "Visit the EU funding portal."

        result_with = evaluator.evaluate(query, with_link)
        result_without = evaluator.evaluate(query, without_link)

        assert (
            result_with["dimensions"]["specificity"] > result_without["dimensions"]["specificity"]
        ), "EU Portal link should improve specificity score"

    def test_ncp_mention_detection(self, evaluator):
        """Test that NCP mention is properly scored."""
        query = "How do I apply?"

        with_ncp = "Contact your National Contact Point (NCP) for guidance."
        without_ncp = "Submit your proposal to the EU."

        result_with = evaluator.evaluate(query, with_ncp)
        result_without = evaluator.evaluate(query, without_ncp)

        assert (
            result_with["dimensions"]["specificity"] > result_without["dimensions"]["specificity"]
        ), "NCP mention should improve specificity score"

    def test_registration_steps_detection(self, evaluator):
        """Test that registration steps (EU Login, PIC) are detected."""
        query = "How do I apply?"

        with_registration = """
1. Create your EU Login account
2. Register your organization and get a PIC number
3. Find and apply to calls"""
        without_registration = "Find calls and submit proposals."

        result_with = evaluator.evaluate(query, with_registration)
        result_without = evaluator.evaluate(query, without_registration)

        assert (
            result_with["dimensions"]["query_fulfillment"]
            > result_without["dimensions"]["query_fulfillment"]
        ), "Registration steps should improve fulfillment score"

    def test_call_to_action_detection(self, evaluator):
        """Test that clear call-to-action is detected."""
        query = "How do I apply?"

        with_cta = "Your next step: Create your EU Login account today!"
        without_cta = "The portal has more information."

        result_with = evaluator.evaluate(query, with_cta)
        result_without = evaluator.evaluate(query, without_cta)

        assert (
            result_with["dimensions"]["actionability"]
            > result_without["dimensions"]["actionability"]
        ), "Call-to-action should improve actionability score"

    # --------------------------------------------------------------------------
    # Live API tests
    # --------------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("httpx", reason="httpx required"),
        reason="httpx not available",
    )
    async def test_live_api_primary_query(self, evaluator):
        """Test the live API with primary application guidance query."""
        query = "How do I apply for Horizon Europe?"

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

        assert (
            result["total_score"] >= PASS_THRESHOLD
        ), f"Score {result['total_score']} below threshold {PASS_THRESHOLD}"

    @pytest.mark.asyncio
    async def test_live_api_has_steps(self, evaluator):
        """Verify the response has step-by-step structure."""
        query = "How do I apply for Horizon Europe?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should have step-by-step structure
        step_indicators = [
            "step 1",
            "step 2",
            "first",
            "second",
            "1.",
            "2.",
            "**1",
            "## step",
        ]
        has_steps = any(ind in response_lower for ind in step_indicators)
        assert has_steps, "Response should provide step-by-step guidance"

    @pytest.mark.asyncio
    async def test_live_api_mentions_registration(self, evaluator):
        """Verify the response explains EU Login and PIC registration."""
        query = "How do I apply for Horizon Europe?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should mention registration
        has_eu_login = "eu login" in response_lower
        has_pic = "pic" in response_lower

        assert (
            has_eu_login or has_pic
        ), "Response should explain registration process (EU Login, PIC)"

    @pytest.mark.asyncio
    async def test_live_api_mentions_ncp(self, evaluator):
        """Verify the response mentions National Contact Points."""
        query = "How do I apply for Horizon Europe?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should mention NCP
        has_ncp = "ncp" in response_lower or "national contact point" in response_lower
        assert has_ncp, "Response should mention National Contact Points (NCPs)"

    @pytest.mark.asyncio
    async def test_live_api_has_links(self, evaluator):
        """Verify the response includes relevant links."""
        query = "How do I apply for Horizon Europe?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        # Should have links
        has_links = bool(re.search(r"https?://|europa\.eu|\[.*\]\(http", response.lower()))
        assert has_links, "Response should include links to official resources"

    @pytest.mark.asyncio
    async def test_live_api_mentions_consortium(self, evaluator):
        """Verify the response mentions consortium/partnership requirements."""
        query = "How do I apply for Horizon Europe?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should mention consortium/partners
        partnership_patterns = ["consortium", "partner", "collaboration", "countries"]
        has_partnership = any(pat in response_lower for pat in partnership_patterns)
        assert has_partnership, "Response should mention consortium/partnership requirements"

    @pytest.mark.asyncio
    async def test_live_api_has_call_to_action(self, evaluator):
        """Verify the response has a clear call-to-action."""
        query = "How do I apply for Horizon Europe?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should have CTA
        cta_patterns = [
            "your next",
            "next step",
            "start by",
            "you should",
            "get started",
            "begin with",
            "first thing",
        ]
        has_cta = any(pat in response_lower for pat in cta_patterns)
        assert has_cta, "Response should have a clear call-to-action"

    @pytest.mark.asyncio
    async def test_live_api_variant_what_steps(self, evaluator):
        """Test variant: What are the steps to apply?"""
        query = "What are the steps to apply for Horizon Europe funding?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        assert len(response) > 100, "Response too short"

        result = evaluator.evaluate(query, response)

        # Should still score reasonably well
        assert result["total_score"] >= 60, f"Variant scored {result['total_score']}"

    @pytest.mark.asyncio
    async def test_live_api_variant_application_process(self, evaluator):
        """Test variant: Explain the application process."""
        query = "Can you explain the Horizon Europe application process?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        assert len(response) > 100, "Response too short"

        result = evaluator.evaluate(query, response)

        # Should still score reasonably well
        assert result["total_score"] >= 60, f"Variant scored {result['total_score']}"


# ==============================================================================
# Run tests directly
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
