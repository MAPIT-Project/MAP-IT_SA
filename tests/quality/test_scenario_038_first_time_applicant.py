# isort: skip_file
"""
Test Scenario 038: First-Time Applicant

Tests that MAPIT correctly handles queries from users who have never applied
for EU funding before and need beginner-friendly guidance.

The response should:
- Be beginner-friendly and not overwhelming
- Include registration steps (EU Login, PIC)
- Include NCP (National Contact Point) referral
- Provide clear, actionable steps
- Not assume prior knowledge of EU funding terminology

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
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "first_time_applicant.json"


class ScenarioEvaluator:
    """Evaluates responses for Scenario 038: First-Time Applicant."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Addresses the "where do I start" question
            "specificity": 25,  # Concrete steps (EU Login, PIC, NCP)
            "factual_accuracy": 25,  # Correct information about registration
            "actionability": 10,  # Clear, non-overwhelming next steps
        }

    def evaluate(self, query: str, response: str) -> dict:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Must provide clear guidance for getting started
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check for step-by-step structure
        step_patterns = [
            r"step\s*\d",
            r"step\s+1",
            r"step\s+one",
            r"first,?\s+(you|create|register|visit)",
            r"1\.\s+",
            r"\*\*1\.",
            r"first step",
            r"getting started",
            r"to start",
        ]
        has_steps = any(re.search(pat, response_lower) for pat in step_patterns)
        if has_steps:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append("Should provide step-by-step guidance")

        # Check for registration/account creation guidance
        registration_patterns = [
            "eu login",
            "create.*account",
            "register",
            "sign up",
            "get.*pic",
            "pic number",
            "participant identification code",
        ]
        has_registration = any(pat in response_lower for pat in registration_patterns)
        if has_registration:
            fulfillment_score += 15
        else:
            fulfillment_feedback.append("Should explain registration process (EU Login, PIC)")

        # Check for programme overview/options
        programme_patterns = [
            "horizon europe",
            "erasmus",
            "creative europe",
            "funding programme",
            "funding opportunities",
            "types of funding",
        ]
        has_programmes = any(pat in response_lower for pat in programme_patterns)
        if has_programmes:
            fulfillment_score += 10
        else:
            fulfillment_feedback.append("Should mention available funding programmes")

        scores["query_fulfillment"] = min(fulfillment_score, 40)
        feedback["query_fulfillment"] = fulfillment_feedback

        # 2. Specificity (25 points)
        specificity_score = 0
        specificity_feedback = []

        # Check for NCP (National Contact Point) mention - CRITICAL
        ncp_patterns = [
            "ncp",
            "national contact point",
            "contact point",
        ]
        has_ncp = any(pat in response_lower for pat in ncp_patterns)
        if has_ncp:
            specificity_score += 10
        else:
            specificity_feedback.append("Should mention National Contact Points (NCPs)")

        # Check for EU Portal reference
        portal_patterns = [
            "funding.*portal",
            "tenders.*portal",
            "ec.europa.eu",
            "eu portal",
            "europa.eu",
        ]
        has_portal = any(re.search(pat, response_lower) for pat in portal_patterns)
        if has_portal:
            specificity_score += 8
        else:
            specificity_feedback.append("Should reference the EU Funding Portal")

        # Check for specific tool/resource references
        resource_patterns = [
            "partner search",
            "cordis",
            "info day",
        ]
        resources_found = sum(1 for pat in resource_patterns if pat in response_lower)
        if resources_found >= 2:
            specificity_score += 7
        elif resources_found == 1:
            specificity_score += 4
        else:
            specificity_feedback.append(
                "Could mention more specific resources (Partner Search, CORDIS, Info Days)"
            )

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        accuracy_score = 0
        accuracy_feedback = []

        # Should not assume prior knowledge (good for beginners)
        overly_technical_terms = [
            "trl",
            "deliverable",
            "work package",
            "consortium agreement",
            "grant agreement",
            "annex",
        ]
        technical_count = sum(1 for term in overly_technical_terms if term in response_lower)
        if technical_count <= 1:
            accuracy_score += 10  # Beginner-friendly
        elif technical_count <= 3:
            accuracy_score += 5
            accuracy_feedback.append("Response may be too technical for first-time applicants")
        else:
            accuracy_feedback.append(
                "Response is too technical and uses jargon without explanation"
            )

        # Correct registration sequence mentioned
        correct_sequence_indicators = [
            ("eu login" in response_lower or "account" in response_lower)
            and ("pic" in response_lower or "register.*organi" in response_lower),
        ]
        if any(correct_sequence_indicators):
            accuracy_score += 10
        else:
            accuracy_feedback.append(
                "Should explain registration sequence (account first, then org)"
            )

        # Does not make it seem overly complicated
        simplicity_indicators = [
            "simple",
            "easy",
            "straightforward",
            "don't worry",
            "it's easier than",
            "minutes",
        ]
        is_reassuring = any(ind in response_lower for ind in simplicity_indicators)
        if is_reassuring:
            accuracy_score += 5
        else:
            accuracy_feedback.append("Could be more reassuring for beginners")

        scores["factual_accuracy"] = min(accuracy_score, 25)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        actionability_score = 0
        actionability_feedback = []

        # Check for clear call-to-action
        cta_patterns = [
            "your next",
            "next step",
            "start by",
            "you should",
            "we recommend",
            "first thing",
            "checklist",
        ]
        has_cta = any(pat in response_lower for pat in cta_patterns)
        if has_cta:
            actionability_score += 5
        else:
            actionability_feedback.append("Should have a clear call-to-action")

        # Check for links
        has_links = bool(re.search(r"https?://|\.eu\)|\.eu/|europa\.eu", response_lower))
        if has_links:
            actionability_score += 3
        else:
            actionability_feedback.append("Should include relevant links")

        # Check for "what not to do" or common mistakes section (helpful for beginners)
        mistake_patterns = [
            "don't",
            "avoid",
            "mistake",
            "common error",
            "not to do",
        ]
        has_warnings = any(pat in response_lower for pat in mistake_patterns)
        if has_warnings:
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
        "scenario": "038_first_time_applicant",
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


class TestScenario038FirstTimeApplicant:
    """Test suite for Scenario 038: First-Time Applicant."""

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    # --------------------------------------------------------------------------
    # Offline evaluation tests with sample responses
    # --------------------------------------------------------------------------

    def test_excellent_response_scores_high(self, evaluator):
        """Test that an excellent response scores 80+."""
        query = "I've never applied for EU funding before. Where do I start?"
        excellent_response = """Welcome to EU funding! Here's a **simple step-by-step guide** \
to get you started. Don't worry - it's easier than it looks.

## Step 1: Create Your EU Login Account (5 minutes)

Your first step is to create an EU Login account - this is your personal access to all EU services.

**How to do it:**
1. Go to [EU Login](https://webgate.ec.europa.eu/cas/)
2. Enter your email address
3. Create a password
4. Verify your email

---

## Step 2: Register Your Organization & Get a PIC Number (15-30 minutes)

The **PIC (Participant Identification Code)** is your organization's unique identifier.

**How to register:**
1. Log into the [Funding & Tenders Portal](https://ec.europa.eu/info/funding-tenders/)
2. Go to "My Organisation" → "Register Organisation"
3. Enter your organization's legal details
4. Submit and receive your 9-digit PIC number

---

## Step 3: Contact Your National Contact Point (NCP) - Highly Recommended!

**NCPs are FREE expert advisors** funded by your national government. They can:
- Help you find the right funding programme
- Review your proposal draft
- Explain eligibility rules
- Connect you with partners

**Find your NCP:** [NCP Network Directory](https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp)

---

## Step 4: Explore Funding Opportunities

Now you're ready to browse available funding like Horizon Europe, Erasmus+, or Creative Europe.

---

## What NOT to Do (Common Mistakes)

- Don't try to coordinate your first project - start as a partner
- Don't skip the NCP consultation - they're free and helpful!

---

**Your Next Action:** Start by creating your EU Login account - it only takes 5 minutes."""

        result = evaluator.evaluate(query, excellent_response)
        assert result["total_score"] >= 80, (
            f"Excellent response scored {result['total_score']}, expected 80+"
        )
        assert result["passed"], "Excellent response should pass"

    def test_too_technical_response_scores_lower(self, evaluator):
        """Test that an overly technical response scores lower."""
        query = "I've never applied for EU funding before. Where do I start?"
        technical_response = """To participate in Horizon Europe, you need to understand \
the TRL requirements.
Your deliverables must align with the work package structure defined in the grant agreement.
The consortium agreement will specify IP ownership. Check Annex I for details.
Submit your proposal through the portal before the deadline."""

        result = evaluator.evaluate(query, technical_response)
        # Should fail accuracy because it's too technical
        assert result["dimensions"]["factual_accuracy"] < 20, (
            "Technical response should score lower on accuracy for beginners"
        )

    def test_minimal_response_scores_low(self, evaluator):
        """Test that a minimal response without guidance scores low."""
        query = "I've never applied for EU funding before. Where do I start?"
        minimal_response = """You should visit the EU portal and look at the calls."""

        result = evaluator.evaluate(query, minimal_response)
        assert result["total_score"] < 60, f"Minimal response scored {result['total_score']}"
        assert not result["passed"], "Minimal response should not pass"

    def test_good_response_with_ncp(self, evaluator):
        """Test that a good response with NCP mention scores well."""
        query = "I've never applied for EU funding before. Where do I start?"
        good_response = """Here's how to get started with EU funding:

**Step 1:** Create an EU Login account at the Funding & Tenders Portal

**Step 2:** Register your organization and get a PIC (Participant Identification Code)

**Step 3:** Contact your National Contact Point (NCP) - they provide free guidance \
for your country and can help you find programmes like Horizon Europe or Erasmus+.

**Step 4:** Browse open calls and consider starting as a partner in an existing project.

Your next step: Visit the NCP directory to find your local contact."""

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
    # Variant queries - different ways to ask "where do I start"
    # --------------------------------------------------------------------------

    def test_how_to_begin_variant(self, evaluator):
        """Test variant: How do I begin?"""
        query = "How do I begin applying for EU funding?"
        good_response = """Getting started with EU funding is straightforward! \
Here's what you need to do:

Step 1: Create an EU Login account (5 minutes)
Step 2: Register your organization and get a PIC number
Step 3: Contact your National Contact Point (NCP) for personalized advice

The NCP service is free and they can help you find the best programme for your needs.

Visit https://ec.europa.eu/info/funding-tenders/ to start the registration process."""

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 65, f"How to begin variant scored {result['total_score']}"

    def test_first_steps_variant(self, evaluator):
        """Test variant: What are the first steps?"""
        query = "I'm new to EU funding. What are the first steps I should take?"
        good_response = """Welcome! Here are your first steps:

1. Create an EU Login account
2. Register your organization for a PIC (Participant Identification Code)
3. Contact your National Contact Point (NCP) - they offer free expert advice
4. Explore funding programmes like Horizon Europe, Erasmus+, or Creative Europe

The NCP can help you understand which programme fits your needs. Find yours at the EU Portal.

Don't worry - the process is simpler than it looks once you get started!"""

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 65, f"First steps variant scored {result['total_score']}"

    # --------------------------------------------------------------------------
    # Specific requirement checks
    # --------------------------------------------------------------------------

    def test_ncp_requirement(self, evaluator):
        """Test that NCP mention is properly scored."""
        query = "Where do I start?"

        with_ncp = "Contact your National Contact Point (NCP) for free guidance."
        without_ncp = "Visit the portal and browse calls."

        result_with = evaluator.evaluate(query, with_ncp)
        result_without = evaluator.evaluate(query, without_ncp)

        assert (
            result_with["dimensions"]["specificity"] > result_without["dimensions"]["specificity"]
        ), "NCP mention should improve specificity score"

    def test_registration_steps_requirement(self, evaluator):
        """Test that registration steps (EU Login, PIC) are properly scored."""
        query = "Where do I start?"

        with_registration = (
            "Step 1: Create an EU Login account. Step 2: Register your org and get a PIC."
        )
        without_registration = "Look at the funding opportunities available."

        result_with = evaluator.evaluate(query, with_registration)
        result_without = evaluator.evaluate(query, without_registration)

        assert (
            result_with["dimensions"]["query_fulfillment"]
            > result_without["dimensions"]["query_fulfillment"]
        ), "Registration steps should improve fulfillment score"

    def test_beginner_friendly_scoring(self, evaluator):
        """Test that beginner-friendly language is rewarded."""
        query = "I've never applied before. Where do I start?"

        friendly = "Don't worry - it's easier than it looks! Here's a simple guide to get started."
        formal = "The application process requires adherence to the following procedures."

        result_friendly = evaluator.evaluate(query, friendly)
        result_formal = evaluator.evaluate(query, formal)

        assert (
            result_friendly["dimensions"]["factual_accuracy"]
            >= result_formal["dimensions"]["factual_accuracy"]
        ), "Beginner-friendly language should be rewarded"

    # --------------------------------------------------------------------------
    # Live API tests
    # --------------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.importorskip("httpx", reason="httpx required"),
        reason="httpx not available",
    )
    async def test_live_api_primary_query(self, evaluator):
        """Test the live API with primary first-time applicant query."""
        query = "I've never applied for EU funding before. Where do I start?"

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
    async def test_live_api_mentions_ncp(self, evaluator):
        """Verify the system mentions National Contact Points."""
        query = "I've never applied for EU funding before. Where do I start?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should mention NCP
        assert "ncp" in response_lower or "national contact point" in response_lower, (
            "Response should mention National Contact Points"
        )

    @pytest.mark.asyncio
    async def test_live_api_mentions_registration(self, evaluator):
        """Verify the system explains registration (EU Login, PIC)."""
        query = "I've never applied for EU funding before. Where do I start?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should mention registration steps
        has_login = "eu login" in response_lower or "account" in response_lower
        has_pic = "pic" in response_lower or "participant identification" in response_lower

        assert has_login or has_pic, "Response should explain registration process (EU Login, PIC)"

    @pytest.mark.asyncio
    async def test_live_api_provides_steps(self, evaluator):
        """Verify the response provides step-by-step guidance."""
        query = "I've never applied for EU funding before. Where do I start?"

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
            "**2",
        ]
        has_steps = any(ind in response_lower for ind in step_indicators)
        assert has_steps, "Response should provide step-by-step guidance"

    @pytest.mark.asyncio
    async def test_live_api_not_overwhelming(self, evaluator):
        """Verify the response is not overwhelming with jargon."""
        query = "I've never applied for EU funding before. Where do I start?"

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        response_lower = response.lower()

        # Should NOT overuse technical jargon without explanation
        jargon_terms = ["trl", "work package", "deliverable", "annex", "consortium agreement"]
        jargon_count = sum(1 for term in jargon_terms if term in response_lower)

        assert jargon_count <= 2, (
            f"Response uses too much unexplained jargon ({jargon_count} terms)"
        )

    @pytest.mark.asyncio
    async def test_live_api_variant_getting_started(self, evaluator):
        """Test variant: I want to get started with EU funding."""
        query = (
            "I want to get started with EU funding. I've never done this before. What should I do?"
        )

        try:
            response, _, _ = await send_query(query)
        except Exception as e:
            pytest.skip(f"API not available: {e}")

        assert len(response) > 100, "Response too short"

        response_lower = response.lower()

        # Should still provide guidance
        guidance_indicators = ["step", "first", "register", "portal", "ncp", "national contact"]
        has_guidance = any(ind in response_lower for ind in guidance_indicators)
        assert has_guidance, "Response should provide getting started guidance"

    @pytest.mark.asyncio
    async def test_live_api_variant_how_do_i_begin(self, evaluator):
        """Test variant: How do I begin?"""
        query = "How do I begin with EU research funding? I'm completely new to this."

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
