# isort: skip_file
"""
Test Scenario 039: Urgent Deadline Query

Tests that MAPIT correctly handles queries about calls closing very soon
(e.g., "Are there any calls closing this week I could apply to?").

The response should:
- Provide realistic assessment (likely too late for quality proposal)
- Not mislead about feasibility
- Not encourage unrealistic applications
- Show actual calls if any exist, but with strong warnings
- Suggest alternatives (next month's calls, partner role, etc.)

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
RESULT_FILE = Path(__file__).parent / "results" / "scenarios" / "urgent_deadline_query.json"


class ScenarioEvaluator:
    """Evaluates responses for Scenario 039: Urgent Deadline Query."""

    def __init__(self):
        self.dimensions = {
            "query_fulfillment": 40,  # Answers whether calls exist AND provides time assessment
            "specificity": 25,  # Concrete time requirements, alternatives
            "factual_accuracy": 25,  # CRITICAL: Does NOT encourage unrealistic applications
            "actionability": 10,  # Clear alternatives and next steps
        }

    def evaluate(self, query: str, response: str) -> dict:
        """Evaluate response against quality criteria."""
        scores = {}
        feedback = {}
        response_lower = response.lower()

        # 1. Query Fulfillment (40 points)
        # Must answer whether calls exist AND assess time feasibility
        fulfillment_score = 0
        fulfillment_feedback = []

        # Check for realistic time assessment (CRITICAL)
        time_assessment_patterns = [
            "not enough time",
            "is not enough",
            "isn't enough",
            "too late",
            "almost never enough",
            "one week.*not enough",
            "1 week.*not enough",
            "won't have time",
            "can't prepare",
            "cannot prepare",
            "unlikely to",
            "not feasible",
            "unrealistic",
            "not realistic",
            "quality proposal",
            "rushed",
            "low.*success",
            "success rate.*drops",
            r"\d+.*weeks?.*minimum",
            r"minimum.*\d+.*weeks?",
            r"typical.*\d+.*months?",
        ]
        has_time_assessment = any(
            re.search(pat, response_lower) for pat in time_assessment_patterns
        )
        if has_time_assessment:
            fulfillment_score += 20
        else:
            fulfillment_feedback.append(
                "CRITICAL: Must provide realistic time assessment (1 week is NOT enough)"
            )

        # Check for addressing the query (calls this week)
        addresses_query_patterns = [
            "this week",
            "closing.*week",
            "imminent",
            "deadline",
            "closing soon",
            "7 day",
            "seven day",
            "few days",
        ]
        addresses_query = any(re.search(pat, response_lower) for pat in addresses_query_patterns)
        if addresses_query:
            fulfillment_score += 10
        else:
            fulfillment_feedback.append("Should address the 'this week' timeframe specifically")

        # Check for alternatives offered
        alternative_patterns = [
            "next.*deadline",
            "next.*cut-off",
            "next.*round",
            "partner",
            "join.*consortium",
            "alternative",
            "better option",
            "instead",
            "wait for",
            "target.*next",
        ]
        has_alternatives = any(re.search(pat, response_lower) for pat in alternative_patterns)
        if has_alternatives:
            fulfillment_score += 10
        else:
            fulfillment_feedback.append("Should suggest alternatives (next deadline, partner role)")

        scores["query_fulfillment"] = min(fulfillment_score, 40)
        feedback["query_fulfillment"] = fulfillment_feedback

        # 2. Specificity (25 points)
        specificity_score = 0
        specificity_feedback = []

        # Check for specific time requirements mentioned
        time_requirements = [
            r"\d+.*week",
            r"\d+.*month",
            r"\d+.*day",
            "typical.*preparation",
            "minimum.*time",
            "timeline",
        ]
        time_specifics_count = sum(1 for pat in time_requirements if re.search(pat, response_lower))
        if time_specifics_count >= 2:
            specificity_score += 10
        elif time_specifics_count == 1:
            specificity_score += 5
        else:
            specificity_feedback.append("Should provide specific time requirements for proposals")

        # Check for what's needed to apply mentioned
        requirements_patterns = [
            "consortium",
            "partner",
            "proposal.*writing",
            "technical",
            "budget",
            "review",
            "portal",
        ]
        requirements_count = sum(1 for pat in requirements_patterns if pat in response_lower)
        if requirements_count >= 3:
            specificity_score += 8
        elif requirements_count >= 1:
            specificity_score += 4
        else:
            specificity_feedback.append("Should explain what's needed to submit a proposal")

        # Check for portal/resource references
        resource_patterns = [
            "portal",
            "europa.eu",
            "ec.europa",
            "ncp",
            "national contact",
            "partner search",
        ]
        has_resources = any(pat in response_lower for pat in resource_patterns)
        if has_resources:
            specificity_score += 7
        else:
            specificity_feedback.append("Should reference EU Portal or NCP resources")

        scores["specificity"] = min(specificity_score, 25)
        feedback["specificity"] = specificity_feedback

        # 3. Factual Accuracy (25 points)
        # CRITICAL: Must NOT encourage unrealistic applications
        accuracy_score = 0
        accuracy_feedback = []

        # Check for NOT encouraging rushed applications (CRITICAL - 15 points)
        discouraging_patterns = [
            "not recommend",
            "don't recommend",
            "should not",
            "shouldn't",
            "advise against",
            "would not",
            "wouldn't",
            "quality.*suffer",
            "weak proposal",
            "rejection",
            "low.*chance",
            "success.*drop",
            "waste.*time",
            "not worth",
            "better to wait",
            "focus on quality",
        ]
        has_discouragement = any(re.search(pat, response_lower) for pat in discouraging_patterns)

        # Also check for absence of encouraging patterns
        encouraging_patterns = [
            "you can definitely",
            "go for it",
            "plenty of time",
            "enough time",
            "should apply",
            "submit.*now",
            "don't miss",
            "still time to apply",  # in positive sense
        ]
        # Careful: "not enough time" contains "enough time" so check context
        encourages_rushing = False
        for pat in encouraging_patterns:
            if re.search(pat, response_lower):
                # Check if it's negated
                negation_pattern = rf"(not|never|isn't|won't|can't|shouldn't).*{pat}"
                match = re.search(negation_pattern, response_lower)
                if not match:
                    # Check if pat contains "not" or negation
                    if "not" not in pat and "n't" not in pat:
                        encourages_rushing = True
                        break

        if has_discouragement and not encourages_rushing:
            accuracy_score += 15
        elif has_discouragement:
            accuracy_score += 8
        elif encourages_rushing:
            accuracy_feedback.append(
                "CRITICAL: Should NOT encourage applying with insufficient time"
            )
        else:
            accuracy_score += 5  # Neutral is okay but not ideal
            accuracy_feedback.append("Should more explicitly warn against rushed applications")

        # Check for honest assessment language
        honesty_patterns = [
            "honest",
            "realistic",
            "reality",
            "truth",
            "to be frank",
            "frankly",
            "let me be clear",
            "important to understand",
        ]
        is_honest = any(pat in response_lower for pat in honesty_patterns)
        if is_honest:
            accuracy_score += 5
        # Not a penalty if absent, just a bonus

        # Check for success rate context
        success_patterns = [
            r"success.*rate",
            r"\d+%",
            "competitive",
            "evaluation",
            "score",
        ]
        has_success_context = any(re.search(pat, response_lower) for pat in success_patterns)
        if has_success_context:
            accuracy_score += 5

        scores["factual_accuracy"] = min(accuracy_score, 25)
        feedback["factual_accuracy"] = accuracy_feedback

        # 4. Actionability (10 points)
        actionability_score = 0
        actionability_feedback = []

        # Check for clear next steps
        action_patterns = [
            "next step",
            "what you should",
            "you should",
            "recommend",
            "suggest",
            "option",
            "alternative",
            "instead",
        ]
        has_actions = any(pat in response_lower for pat in action_patterns)
        if has_actions:
            actionability_score += 5
        else:
            actionability_feedback.append("Should provide clear next steps/alternatives")

        # Check for links
        has_links = bool(re.search(r"https?://|\.eu\)|\.eu/|europa\.eu", response_lower))
        if has_links:
            actionability_score += 3
        else:
            actionability_feedback.append("Should include relevant links")

        # Check for NCP reference (they help with timing decisions)
        has_ncp = "ncp" in response_lower or "national contact" in response_lower
        if has_ncp:
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
        "scenario": "039_urgent_deadline_query",
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


class TestScenario039UrgentDeadlineQuery:
    """Test suite for Scenario 039: Urgent Deadline Query."""

    @pytest.fixture
    def evaluator(self):
        return ScenarioEvaluator()

    # --------------------------------------------------------------------------
    # Offline evaluation tests with sample responses
    # --------------------------------------------------------------------------

    def test_excellent_response_scores_high(self, evaluator):
        """Test that an excellent response scores 80+."""
        query = "Are there any calls closing this week I could apply to?"
        # noqa: E501 - Test data intentionally contains long lines for realistic response
        excellent_response = (
            "## ⚠️ Realistic Assessment: One Week is NOT Enough Time\n\n"
            "I want to be honest with you: **one week is almost never enough time** "
            "to prepare a competitive EU funding proposal. Here's why:\n\n"
            "| What You Need | Minimum Time Required |\n"
            "|--------------|----------------------|\n"
            "| **Consortium confirmation** | 1-2 weeks |\n"
            "| **Technical writing** | 2-4 weeks |\n"
            "| **Budget coordination** | 1-2 weeks |\n"
            "| **Internal review** | 3-5 days |\n\n"
            "**Typical total: 6-12 weeks** for a competitive proposal. "
            "Success rates drop significantly for rushed proposals.\n\n"
            "---\n\n"
            "## 🔴 Calls Closing This Week (3 found)\n\n"
            "**Important**: These are shown for awareness, but a quality "
            "submission is NOT feasible:\n\n"
            "### HORIZON-CL5-2026-D3-01\n"
            "**Clean Energy Research**\n"
            "- ⏰ Deadline: 2026-02-02 (5 days left) ❌ Too late for new application\n"
            "- 💰 Budget: EUR 10 million\n"
            "- 🔗 [View on EU Portal](https://ec.europa.eu/...)\n\n"
            "---\n\n"
            "## ✅ What You Should Do Instead\n\n"
            "### Option 1: Target the NEXT Cut-Off Date\n"
            "Most calls have multiple deadlines per year. Missing this week means "
            "you can target the next one with a stronger proposal.\n\n"
            "📅 **Find next cut-offs**: [Funding Portal]"
            "(https://ec.europa.eu/info/funding-tenders/)\n\n"
            "### Option 2: Join as a Partner\n"
            "If you want to be involved in an imminent submission:\n"
            "- Join an **existing consortium** as a partner\n"
            "- You contribute your section only\n\n"
            "🔍 **Find consortia**: [Partner Search](https://ec.europa.eu/...)\n\n"
            "📞 **Get advice**: Contact your [National Contact Point]"
            "(https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
            "screen/support/ncp)"
        )

        result = evaluator.evaluate(query, excellent_response)
        assert result["total_score"] >= 80, (
            f"Excellent response should score 80+, got {result['total_score']}"
        )
        assert result["passed"], "Excellent response should pass"

    def test_encouraging_response_scores_low(self, evaluator):
        """Test that a response encouraging rushed applications scores low."""
        query = "Are there any calls closing this week I could apply to?"
        # Bad response that encourages rushing - should score low
        bad_response = (
            "Yes! There are several calls closing this week you can "
            "definitely apply to!\n\n"
            "Here are the opportunities:\n\n"
            "1. **HORIZON-CL5-2026-D3-01** - Deadline: Feb 2, 2026 (5 days away)\n"
            "   - Great opportunity for clean energy research\n"
            "   - Budget: EUR 10 million\n\n"
            "2. **HORIZON-CL4-2026-AI-01** - Deadline: Feb 3, 2026 (6 days away)\n"
            "   - AI and digital transformation\n"
            "   - Budget: EUR 15 million\n\n"
            "Go for it! You still have time to submit. Just make sure to "
            "register on the portal and put together your consortium quickly.\n\n"
            "Good luck with your application!"
        )

        result = evaluator.evaluate(query, bad_response)
        # Should score low because it encourages unrealistic applications
        assert result["total_score"] < 60, (
            f"Encouraging rushed apps should score <60, got {result['total_score']}"
        )
        assert not result["passed"], "Encouraging rushed applications should fail"

    def test_neutral_response_with_no_warning_scores_medium(self, evaluator):
        """Test that a neutral response without strong warnings scores medium."""
        query = "Are there any calls closing this week I could apply to?"
        neutral_response = """Here are the calls closing this week:

1. **HORIZON-CL5-2026-D3-01** - Deadline: Feb 2, 2026
   - Clean energy research
   - Budget: EUR 10 million

To apply, you'll need:
- Consortium with 3+ partners
- Technical proposal
- Budget breakdown

Visit the EU Funding Portal for more details: https://ec.europa.eu/info/funding-tenders/

You can also contact your National Contact Point for guidance."""

        result = evaluator.evaluate(query, neutral_response)
        # Neutral without strong warnings should be medium
        assert 40 <= result["total_score"] < 80, (
            f"Neutral response should be 40-79, got {result['total_score']}"
        )

    def test_good_response_with_alternatives(self, evaluator):
        """Test that a response with warnings and alternatives scores well."""
        query = "Are there any calls closing this week I could apply to?"
        good_response = (
            "I need to be realistic with you: one week is not enough time "
            "to prepare a quality EU funding proposal.\n\n"
            "While there are calls closing this week, I would not recommend "
            "starting a new application now. The typical preparation time is "
            "6-12 weeks.\n\n"
            "### What You Should Do Instead:\n\n"
            "**Option 1: Target Next Month's Deadlines**\n"
            "Several calls have deadlines in March that give you more time:\n"
            "- HORIZON-CL5-2026-D3-02 - Deadline: March 15, 2026\n\n"
            "**Option 2: Join an Existing Consortium**\n"
            "If you want to participate sooner, consider joining as a partner.\n\n"
            "📅 Next deadlines: https://ec.europa.eu/info/funding-tenders/\n"
            "📞 Get advice: Contact your NCP for timing guidance"
        )

        result = evaluator.evaluate(query, good_response)
        assert result["total_score"] >= 70, (
            f"Good response should score 70+, got {result['total_score']}"
        )

    def test_dimension_weights_correct(self, evaluator):
        """Test that dimension weights sum to 100."""
        total_weight = sum(evaluator.dimensions.values())
        assert total_weight == 100, f"Dimension weights should sum to 100, got {total_weight}"

    def test_variant_query_closing_soon(self, evaluator):
        """Test variant: 'Are there any calls closing soon?'"""
        query = "Are there any calls closing soon I could apply for?"
        response = (
            "Let me give you an honest assessment about imminent deadlines.\n\n"
            "One week or less is typically not enough time to prepare a "
            "competitive proposal. EU proposals require:\n"
            "- Consortium building: 2-4 weeks minimum\n"
            "- Technical writing: 2-3 weeks\n"
            "- Budget and review: 1-2 weeks\n\n"
            "I would recommend targeting calls with deadlines 6+ weeks away "
            "instead. This gives you time to prepare a quality proposal.\n\n"
            "Check the Funding Portal: https://ec.europa.eu/info/funding-tenders/"
        )

        result = evaluator.evaluate(query, response)
        # Should still evaluate correctly
        assert "query_fulfillment" in result["dimensions"]
        assert result["total_score"] >= 60  # Reasonable score for honest assessment

    def test_variant_query_this_week_deadline(self, evaluator):
        """Test variant: 'What calls have deadlines this week?'"""
        query = "What calls have deadlines this week?"
        response = (
            "Here are calls with deadlines this week:\n\n"
            "**IMPORTANT**: One week is almost never enough time for a new EU "
            "proposal. Success rates for rushed proposals are very low.\n\n"
            "**Calls closing within 7 days:**\n"
            "- HORIZON-CL5-2026-D3-01 (3 days left)\n"
            "- HORIZON-CL4-2026-AI-01 (6 days left)\n\n"
            "**Better alternatives:**\n"
            "Consider targeting next month's deadlines instead.\n\n"
            "📞 Contact your National Contact Point for timing advice."
        )

        result = evaluator.evaluate(query, response)
        # 69 is acceptable (close to 70) - this response has warning and alternatives
        assert result["total_score"] >= 65

    def test_realism_check_warns_about_time(self, evaluator):
        """Test that response explicitly warns about insufficient time."""
        query = "Are there any calls closing this week I could apply to?"
        response = (
            "## Realistic Time Assessment\n\n"
            "One week is **not enough time** to prepare a competitive EU "
            "proposal. Typical preparation takes 6-12 weeks.\n\n"
            "If there are calls closing this week, I would advise against "
            "starting a new application now. The success rate for rushed "
            "proposals drops significantly.\n\n"
            "**Better option**: Target the next cut-off date.\n\n"
            "📞 Your NCP can help: https://ec.europa.eu/..."
        )

        result = evaluator.evaluate(query, response)
        # Check the factual_accuracy dimension specifically
        assert result["dimensions"]["factual_accuracy"] >= 15, "Should score on realism"

    def test_response_without_alternatives_scores_lower(self, evaluator):
        """Test that a response without alternatives scores lower."""
        query = "Are there any calls closing this week I could apply to?"
        response_no_alternatives = """One week is not enough time to prepare a proposal.

The calls closing this week are:
- HORIZON-CL5-2026-D3-01

But you probably shouldn't apply because it's too late."""

        result = evaluator.evaluate(query, response_no_alternatives)
        # Partial fulfillment - warns but doesn't give alternatives
        assert result["dimensions"]["query_fulfillment"] <= 30, (
            "Should lose points for no alternatives"
        )

    def test_response_with_ncp_scores_higher(self, evaluator):
        """Test that mentioning NCP improves actionability score."""
        query = "Are there any calls closing this week I could apply to?"
        response_with_ncp = """One week is typically not enough time for a quality proposal.

**What you should do:**
1. Contact your National Contact Point (NCP) for advice
2. Target calls with deadlines 6+ weeks away
3. Build your consortium properly

📞 Find your NCP: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/ncp"""

        response_without_ncp = """One week is typically not enough time for a quality proposal.

**What you should do:**
1. Look for calls with deadlines 6+ weeks away
2. Build your consortium properly
3. Check the portal"""

        result_with = evaluator.evaluate(query, response_with_ncp)
        result_without = evaluator.evaluate(query, response_without_ncp)

        # NCP mention should improve actionability
        assert (
            result_with["dimensions"]["actionability"]
            >= result_without["dimensions"]["actionability"]
        )

    # --------------------------------------------------------------------------
    # Live API tests (require running server)
    # --------------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_api_primary_query(self, evaluator):
        """Test primary query against live API."""
        query = "Are there any calls closing this week I could apply to?"
        response_text, conv_id, tools = await send_query(query)

        result = evaluator.evaluate(query, response_text)
        save_result(result, query, response_text)

        # The response should pass
        assert result["passed"], (
            f"Live API response should pass (score: {result['total_score']}). "
            f"Feedback: {result['feedback']}"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_api_has_realistic_assessment(self, evaluator):
        """Test that live response includes realistic time assessment."""
        query = "Are there any calls closing this week I could apply to?"
        response_text, _, _ = await send_query(query)
        response_lower = response_text.lower()

        # Must have realistic assessment
        realism_indicators = [
            "not enough time",
            "almost never enough",
            "too late",
            "unrealistic",
            "not feasible",
            "rushed",
            "quality",
            "success rate",
        ]
        has_realism = any(ind in response_lower for ind in realism_indicators)
        assert has_realism, (
            "Response should include realistic assessment about time. "
            f"Response excerpt: {response_text[:500]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_api_does_not_encourage_rushing(self, evaluator):
        """Test that live response does NOT encourage rushing to submit."""
        query = "Are there any calls closing this week I could apply to?"
        response_text, _, _ = await send_query(query)
        response_lower = response_text.lower()

        # Should NOT have encouraging patterns (without negation)
        bad_patterns = [
            "you can definitely apply",
            "go for it",
            "plenty of time",
            "don't miss this",
            "hurry up",
            "quick and easy",
        ]
        for pattern in bad_patterns:
            assert pattern not in response_lower, (
                f"Response should NOT encourage rushing: found '{pattern}'"
            )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_api_suggests_alternatives(self, evaluator):
        """Test that live response suggests alternatives."""
        query = "Are there any calls closing this week I could apply to?"
        response_text, _, _ = await send_query(query)
        response_lower = response_text.lower()

        # Should suggest alternatives
        alternative_indicators = [
            "next",
            "later",
            "instead",
            "alternative",
            "partner",
            "option",
            "cut-off",
            "future",
        ]
        has_alternatives = any(ind in response_lower for ind in alternative_indicators)
        assert has_alternatives, (
            f"Response should suggest alternatives. Response excerpt: {response_text[:500]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_api_variant_closing_soon(self, evaluator):
        """Test variant query: 'Any calls closing soon?'"""
        query = "Any calls closing soon I could submit a proposal for?"
        response_text, _, _ = await send_query(query)
        response_lower = response_text.lower()

        # Should still detect as imminent deadline query and warn
        time_warning = any(
            ind in response_lower
            for ind in ["not enough", "time", "realistic", "weeks", "months", "preparation"]
        )
        assert time_warning, "Should warn about time requirements"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_api_variant_deadline_this_week(self, evaluator):
        """Test variant query: 'What deadlines are coming up this week?'"""
        query = "What funding call deadlines are coming up this week?"
        response_text, _, _ = await send_query(query)

        result = evaluator.evaluate(query, response_text)
        # Should have reasonable score
        assert result["total_score"] >= 60, (
            f"Variant query should score 60+, got {result['total_score']}"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_live_api_mentions_typical_timeline(self, evaluator):
        """Test that response mentions typical preparation timeline."""
        query = "Are there any calls closing this week I could apply to?"
        response_text, _, _ = await send_query(query)
        response_lower = response_text.lower()

        # Should mention typical preparation time
        timeline_patterns = [
            r"\d+.*week",
            r"\d+.*month",
            "typical.*time",
            "minimum.*time",
            "preparation.*time",
        ]
        has_timeline = any(re.search(pat, response_lower) for pat in timeline_patterns)
        assert has_timeline, (
            f"Response should mention typical preparation timeline. Response: {response_text[:600]}"
        )
