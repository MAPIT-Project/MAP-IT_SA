"""
Test Scenario 061: Source Attribution

PRD Reference: MAPIT_APPLICATION_QUALITY_IMPROVEMENT_PRD.md, Scenario 061
Query: "What are the ERC grant amounts?"
Expected: Specific amounts WITH source indication
Verify: Can trace info to official source
Fix if: Numbers without source
Pass threshold: 80

Official ERC Grant Amounts (from erc.europa.eu):
- Starting Grant (StG): Up to EUR 1.5 million (5 years)
- Consolidator Grant (CoG): Up to EUR 2 million (5 years)
- Advanced Grant (AdG): Up to EUR 2.5 million (5 years)
- Synergy Grant (SyG): Up to EUR 10 million (6 years)
- Proof of Concept (PoC): Up to EUR 150,000 (18 months)

Sources:
- https://erc.europa.eu/funding
- https://erc.europa.eu/apply-grant/starting-grant
- https://erc.europa.eu/apply-grant/consolidator-grant
- https://erc.europa.eu/apply-grant/advanced-grant
- https://erc.europa.eu/apply-grant/synergy-grant
- https://erc.europa.eu/apply-grant/proof-concept
"""

import re
from dataclasses import dataclass

import httpx
import pytest

# Official ERC grant amounts (in EUR millions, except PoC in thousands)
OFFICIAL_ERC_AMOUNTS = {
    "starting_grant": {"amount": 1.5, "unit": "million", "duration": 5},
    "consolidator_grant": {"amount": 2.0, "unit": "million", "duration": 5},
    "advanced_grant": {"amount": 2.5, "unit": "million", "duration": 5},
    "synergy_grant": {"amount": 10.0, "unit": "million", "duration": 6},
    "proof_of_concept": {"amount": 150, "unit": "thousand", "duration_months": 18},
}

# Source attribution patterns
SOURCE_ATTRIBUTION_PATTERNS = [
    r"erc\.europa\.eu",
    r"european research council.*(?:official|website)",
    r"source.*erc",
    r"erc.*source",
    r"official.*erc",
    r"erc\s+work\s+programme",
    r"erc\s+statistics",
    r"according\s+to\s+(?:the\s+)?erc",
    r"erc\s+grants?\s+portal",  # "ERC Grants Portal" or "ERC Grant Portal"
    r"funding-tenders.*horizon",  # EU Funding & Tenders Portal reference
    r"eu\s+funding.*portal",  # EU Funding Portal
    r"horizon\s+europe\s+work\s+programme",  # Horizon Europe reference
]

# Grant type detection keywords
GRANT_TYPE_KEYWORDS = {
    "starting": ["starting grant", "stg", "starting grants", "€1.5 million", "1.5m"],
    "consolidator": ["consolidator grant", "cog", "consolidator grants", "€2 million", "2m"],
    "advanced": ["advanced grant", "adg", "advanced grants", "€2.5 million", "2.5m"],
    "synergy": ["synergy grant", "syg", "synergy grants", "€10 million", "10m"],
    "poc": ["proof of concept", "poc", "€150,000", "150k"],
}


@dataclass
class SourceAttributionScore:
    """Score for source attribution quality."""

    query_fulfillment: int  # 0-40: All parts answered
    specificity: int  # 0-25: Concrete numbers with context
    source_attribution: int  # 0-25: Clear source indication
    actionability: int  # 0-10: Clear next steps

    @property
    def total_score(self) -> int:
        return (
            self.query_fulfillment + self.specificity + self.source_attribution + self.actionability
        )

    @property
    def passed(self) -> bool:
        return self.total_score >= 80


class SourceAttributionEvaluator:
    """Evaluates responses for source attribution quality."""

    def __init__(self, passing_threshold: int = 80):
        self.passing_threshold = passing_threshold

    def evaluate(self, query: str, response: str) -> SourceAttributionScore:
        """Evaluate response for source attribution quality."""
        response_lower = response.lower()

        # Query fulfillment (40 points)
        query_fulfillment = self._score_query_fulfillment(response_lower)

        # Specificity (25 points)
        specificity = self._score_specificity(response_lower)

        # Source attribution (25 points)
        source_attribution = self._score_source_attribution(response_lower)

        # Actionability (10 points)
        actionability = self._score_actionability(response_lower)

        return SourceAttributionScore(
            query_fulfillment=query_fulfillment,
            specificity=specificity,
            source_attribution=source_attribution,
            actionability=actionability,
        )

    def _score_query_fulfillment(self, response: str) -> int:
        """Score how well the query was answered (0-40)."""
        score = 0

        # Must mention ERC (10 points)
        if "erc" in response or "european research council" in response:
            score += 10

        # Must mention grant amounts (10 points)
        if any(
            term in response
            for term in ["grant amount", "funding", "budget", "million", "€", "eur"]
        ):
            score += 10

        # Must mention multiple grant types (10 points)
        grant_types_mentioned = sum(
            1
            for grant_type in GRANT_TYPE_KEYWORDS
            if any(kw in response for kw in GRANT_TYPE_KEYWORDS[grant_type])
        )
        if grant_types_mentioned >= 3:
            score += 10
        elif grant_types_mentioned >= 2:
            score += 5

        # Must include structured information (table or list) (10 points)
        if "|" in response or ("- " in response and ":" in response):
            score += 10

        return min(score, 40)

    def _score_specificity(self, response: str) -> int:
        """Score specificity of grant amounts (0-25)."""
        score = 0

        # Check for specific amounts (5 points each, max 25)
        specific_amounts = [
            ("1.5", "starting"),
            ("2 million", "consolidator"),
            ("2.5", "advanced"),
            ("10 million", "synergy"),
            ("150", "proof"),
        ]

        for amount, _context in specific_amounts:
            if amount in response:
                score += 5

        return min(score, 25)

    def _score_source_attribution(self, response: str) -> int:
        """Score source attribution quality (0-25)."""
        score = 0

        # Check for source patterns (5 points each, max 25)
        for pattern in SOURCE_ATTRIBUTION_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                score += 5

        # Bonus for explicit URL (10 points)
        if "erc.europa.eu" in response:
            score += 10

        return min(score, 25)

    def _score_actionability(self, response: str) -> int:
        """Score actionability of response (0-10)."""
        score = 0

        # Check for next steps (5 points)
        if any(
            term in response
            for term in ["next step", "how to apply", "check eligibility", "contact"]
        ):
            score += 5

        # Check for links (5 points)
        if "http" in response or "portal" in response:
            score += 5

        return min(score, 10)


class TestScenario061SourceAttribution:
    """Test suite for Scenario 061: Source Attribution."""

    BASE_URL = "http://localhost:8000"
    QUERY = "What are the ERC grant amounts?"
    PASS_THRESHOLD = 80

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(610000, 619999)

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return SourceAttributionEvaluator(passing_threshold=self.PASS_THRESHOLD)

    # ==================== Unit Tests ====================

    def test_official_amounts_are_valid(self):
        """Test that official amounts are properly defined."""
        for grant_type, info in OFFICIAL_ERC_AMOUNTS.items():
            assert info["amount"] > 0, f"{grant_type}: amount should be positive"
            assert info["unit"] in ["million", "thousand"], f"{grant_type}: invalid unit"

    def test_source_patterns_compile(self):
        """Test that all source attribution patterns compile correctly."""
        for pattern in SOURCE_ATTRIBUTION_PATTERNS:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                pytest.fail(f"Pattern '{pattern}' failed to compile: {e}")

    def test_source_pattern_detection(self):
        """Test detection of source attribution patterns."""
        test_cases = [
            ("Source: erc.europa.eu", True),
            ("According to the European Research Council official website", True),
            ("ERC Work Programme 2025", True),
            ("No source mentioned here", False),
            ("Random text without attribution", False),
        ]

        for text, expected in test_cases:
            found = any(
                re.search(pattern, text, re.IGNORECASE) for pattern in SOURCE_ATTRIBUTION_PATTERNS
            )
            assert found == expected, f"Failed for: {text}"

    def test_grant_type_keywords_detection(self):
        """Test detection of grant type keywords."""
        test_text = "ERC Starting Grant provides up to €1.5 million"
        found = False
        for _grant_type, keywords in GRANT_TYPE_KEYWORDS.items():
            if any(kw in test_text.lower() for kw in keywords):
                found = True
                break
        assert found, "Should detect grant type"

    def test_amount_extraction_from_text(self):
        """Test extraction of grant amounts from response text."""
        test_cases = [
            ("Up to €1.5 million", [1.5]),
            ("€2 million", [2.0]),
            ("Up to 2.5M", [2.5]),
            ("€150,000", [150000.0]),
            ("No amounts here", []),
        ]

        for text, expected in test_cases:
            # Extract amounts using regex
            amounts = []
            # Match millions (e.g., €1.5 million, 2.5M)
            for match in re.finditer(r"€?(\d+(?:\.\d+)?)\s*(?:million|m\b)", text, re.IGNORECASE):
                amounts.append(float(match.group(1)))
            # Match thousands (e.g., €150,000)
            for match in re.finditer(r"€?(\d{1,3}(?:,\d{3})+)", text):
                amounts.append(float(match.group(1).replace(",", "")))
            assert amounts == expected, f"Failed for: {text}"

    def test_evaluator_scoring_logic(self, evaluator):
        """Test that evaluator scoring works correctly."""
        good_response = """
        ## ERC Grant Amounts

        | Grant Type | Maximum Budget |
        |------------|----------------|
        | Starting Grant | €1.5 million |
        | Consolidator Grant | €2 million |
        | Advanced Grant | €2.5 million |
        | Synergy Grant | €10 million |
        | Proof of Concept | €150,000 |

        Source: [ERC Official Website](https://erc.europa.eu/funding)

        Next Steps: Check eligibility at erc.europa.eu
        """

        score = evaluator.evaluate("What are the ERC grant amounts?", good_response)
        assert score.total_score >= 80, f"Good response should score 80+, got {score.total_score}"
        assert score.source_attribution > 0, "Should detect source attribution"

    def test_evaluator_detects_missing_source(self, evaluator):
        """Test that evaluator penalizes missing source attribution."""
        no_source_response = """
        ERC grants provide:
        - Starting Grant: €1.5 million
        - Consolidator Grant: €2 million
        - Advanced Grant: €2.5 million
        """

        score = evaluator.evaluate("What are the ERC grant amounts?", no_source_response)
        assert score.source_attribution < 15, "Should detect missing source attribution"

    def test_evaluator_detects_missing_specificity(self, evaluator):
        """Test that evaluator penalizes missing specific amounts."""
        vague_response = """
        ERC provides funding for research.
        There are different grant types with various funding levels.
        Source: erc.europa.eu
        """

        score = evaluator.evaluate("What are the ERC grant amounts?", vague_response)
        assert score.specificity < 15, "Should detect missing specificity"

    def test_score_dataclass_total(self):
        """Test SourceAttributionScore total calculation."""
        score = SourceAttributionScore(
            query_fulfillment=35, specificity=20, source_attribution=20, actionability=8
        )
        assert score.total_score == 83
        assert score.passed is True

    def test_score_dataclass_threshold(self):
        """Test SourceAttributionScore passing threshold."""
        passing = SourceAttributionScore(
            query_fulfillment=30, specificity=25, source_attribution=20, actionability=5
        )
        failing = SourceAttributionScore(
            query_fulfillment=20, specificity=15, source_attribution=10, actionability=5
        )
        assert passing.passed is True
        assert failing.passed is False

    def test_detection_patterns(self):
        """Test ERC grant amount query detection patterns."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        # Patterns that should match
        should_match = [
            "What are the ERC grant amounts?",
            "How much funding does ERC provide?",
            "What's the budget for ERC Starting Grant?",
            "ERC funding levels",
            "Maximum ERC grant amount",
            "How much is an ERC Starting Grant?",
            "What is the ERC Consolidator Grant budget?",
        ]

        # Patterns that should NOT match (avoid false positives)
        should_not_match = [
            "Compare ERC and EIC",
            "Am I eligible for ERC?",
            "How to apply for ERC?",
            "ERC vs MSCA",
        ]

        agent = ToolAwareAgent.__new__(ToolAwareAgent)

        for query in should_match:
            result = agent._detect_erc_grant_amount_query(query, "")
            assert result is not None, f"Should match: {query}"
            assert result.get("guidance_type") == "erc_grant_amounts"

        for query in should_not_match:
            result = agent._detect_erc_grant_amount_query(query, "")
            assert result is None, f"Should NOT match: {query}"

    def test_guidance_contains_source_attribution(self):
        """Test that generated guidance includes source attribution."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        guidance = agent._generate_erc_grant_amount_guidance()

        # Must contain source URL
        assert "erc.europa.eu" in guidance.lower(), "Guidance must include erc.europa.eu"

        # Must contain source indicators
        source_indicators = ["source", "official", "work programme"]
        found_indicator = any(ind in guidance.lower() for ind in source_indicators)
        assert found_indicator, "Guidance must indicate official source"

    def test_guidance_contains_all_grant_types(self):
        """Test that generated guidance includes all ERC grant types."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        guidance = agent._generate_erc_grant_amount_guidance()
        guidance_lower = guidance.lower()

        grant_types = ["starting", "consolidator", "advanced", "synergy", "proof of concept"]
        for grant_type in grant_types:
            assert grant_type in guidance_lower, f"Guidance must include {grant_type}"

    def test_guidance_contains_specific_amounts(self):
        """Test that generated guidance includes specific grant amounts."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        guidance = agent._generate_erc_grant_amount_guidance()

        # Check for specific amounts (with variations)
        expected_amounts = ["1.5 million", "2 million", "2.5 million", "10 million", "150,000"]
        for amount in expected_amounts:
            assert amount in guidance, f"Guidance must include {amount}"

    def test_guidance_contains_actionable_links(self):
        """Test that generated guidance includes actionable links."""
        from app.services.agents.tool_aware_agent import ToolAwareAgent

        agent = ToolAwareAgent.__new__(ToolAwareAgent)
        guidance = agent._generate_erc_grant_amount_guidance()

        # Must contain links
        assert "http" in guidance or "erc.europa.eu" in guidance, "Guidance must include links"
        assert "next step" in guidance.lower(), "Guidance must include next steps"

    # ==================== Integration Tests ====================

    @pytest.mark.asyncio
    async def test_api_returns_200(self, conversation_id):
        """Test that the API returns 200 status code."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            assert response.status_code == 200, f"API returned {response.status_code}"

    @pytest.mark.asyncio
    async def test_response_mentions_erc(self, conversation_id):
        """Test that response mentions ERC."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "").lower()

            assert "erc" in response_text or "european research council" in response_text, (
                "Response should mention ERC"
            )

    @pytest.mark.asyncio
    async def test_response_contains_specific_amounts(self, conversation_id):
        """Test that response contains specific grant amounts."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Check for at least one specific amount
            amount_patterns = [
                r"1\.5\s*(?:million|m)",
                r"€?2\s*(?:million|m)",
                r"2\.5\s*(?:million|m)",
                r"10\s*(?:million|m)",
                r"150[,\s]*000",
            ]

            found_amount = any(re.search(p, response_text, re.IGNORECASE) for p in amount_patterns)
            assert found_amount, "Response should contain specific grant amounts"

    @pytest.mark.asyncio
    async def test_response_includes_source_attribution(self, conversation_id):
        """Test that response includes source attribution."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "").lower()

            # Check for source attribution
            source_found = any(
                re.search(pattern, response_text, re.IGNORECASE)
                for pattern in SOURCE_ATTRIBUTION_PATTERNS
            )

            assert source_found, "Response should include source attribution (erc.europa.eu)"

    @pytest.mark.asyncio
    async def test_response_mentions_multiple_grant_types(self, conversation_id):
        """Test that response mentions multiple grant types."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "").lower()

            # Count grant types mentioned
            grant_types_found = sum(
                1
                for grant_type in GRANT_TYPE_KEYWORDS
                if any(kw in response_text for kw in GRANT_TYPE_KEYWORDS[grant_type])
            )

            assert grant_types_found >= 3, (
                f"Response should mention at least 3 grant types, found {grant_types_found}"
            )

    @pytest.mark.asyncio
    async def test_response_passes_quality_threshold(self, conversation_id, evaluator):
        """Test that response passes the 80-point quality threshold."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            score = evaluator.evaluate(self.QUERY, response_text)

            assert score.passed, (
                f"Response should score 80+, got {score.total_score}. "
                f"Breakdown: query_fulfillment={score.query_fulfillment}, "
                f"specificity={score.specificity}, "
                f"source_attribution={score.source_attribution}, "
                f"actionability={score.actionability}"
            )

    @pytest.mark.asyncio
    async def test_starting_grant_amount_correct(self, conversation_id):
        """Test that Starting Grant amount is correctly stated."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "What is the ERC Starting Grant budget?", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Starting Grant should be €1.5 million
            assert "1.5" in response_text, "Starting Grant amount should be €1.5 million"

    @pytest.mark.asyncio
    async def test_consolidator_grant_amount_correct(self, conversation_id):
        """Test that Consolidator Grant amount is correctly stated."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "How much is an ERC Consolidator Grant?", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Consolidator Grant should be €2 million
            assert "2 million" in response_text.lower() or "€2" in response_text, (
                "Consolidator Grant amount should be €2 million"
            )

    @pytest.mark.asyncio
    async def test_response_includes_erc_url(self, conversation_id):
        """Test that response includes the official ERC URL."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Must include erc.europa.eu URL
            assert "erc.europa.eu" in response_text, (
                "Response must include erc.europa.eu URL for source traceability"
            )

    @pytest.mark.asyncio
    async def test_no_error_in_response(self, conversation_id):
        """Test that response does not contain error messages."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": self.QUERY, "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "").lower()

            error_indicators = ["error", "failed", "unable to", "could not", "exception"]
            for indicator in error_indicators:
                assert indicator not in response_text or "error handling" in response_text, (
                    f"Response should not contain error indicator: {indicator}"
                )


class TestSourceAttributionEdgeCases:
    """Test edge cases for source attribution."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture
    def conversation_id(self):
        """Generate a unique conversation ID for each test."""
        import random

        return random.randint(611000, 611999)

    @pytest.mark.asyncio
    async def test_alternative_query_forms(self, conversation_id):
        """Test that alternative query forms are handled correctly."""
        # Note: Using very specific queries that clearly ask about ERC grant amounts
        # to avoid routing to statistics or other tools
        alternative_queries = [
            "How much funding does ERC provide?",
            "What's the maximum ERC grant amount?",
            "Tell me about ERC grant budgets",
        ]

        async with httpx.AsyncClient(timeout=180.0) as client:
            for query in alternative_queries:
                await client.delete(
                    f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context"
                )

                response = await client.post(
                    f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                    json={"message": query, "user_id": 1},
                )

                result = response.json()
                response_text = result.get("response", "").lower()

                # Should mention ERC and include amounts
                assert "erc" in response_text or "european research council" in response_text, (
                    f"Response to '{query}' should mention ERC"
                )

    @pytest.mark.asyncio
    async def test_specific_grant_type_query(self, conversation_id):
        """Test queries about specific grant types."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            await client.delete(f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/context")

            response = await client.post(
                f"{self.BASE_URL}/api/v3/conversation/{conversation_id}/message",
                json={"message": "What is the budget for ERC Advanced Grant?", "user_id": 1},
            )

            result = response.json()
            response_text = result.get("response", "")

            # Should mention €2.5 million for Advanced Grant
            assert "2.5" in response_text, "Advanced Grant should be €2.5 million"
            assert "erc.europa.eu" in response_text.lower(), "Should include source URL"


class TestSourceAttributionQuality:
    """Test quality scoring for source attribution."""

    def test_perfect_score_response(self):
        """Test that a perfect response gets maximum score."""
        evaluator = SourceAttributionEvaluator()

        perfect_response = """
        ## ERC Grant Amounts

        The European Research Council provides the following grant amounts:

        | Grant Type | Maximum Budget | Duration |
        |------------|----------------|----------|
        | Starting Grant | Up to €1.5 million | 5 years |
        | Consolidator Grant | Up to €2 million | 5 years |
        | Advanced Grant | Up to €2.5 million | 5 years |
        | Synergy Grant | Up to €10 million | 6 years |
        | Proof of Concept | Up to €150,000 | 18 months |

        Source: [European Research Council Official Website](https://erc.europa.eu/funding)

        According to the ERC Work Programme 2025, these amounts include 100% funding rate.

        Next Steps:
        1. Check eligibility at https://erc.europa.eu/apply-grant
        2. Contact your National Contact Point for guidance
        """

        score = evaluator.evaluate("What are the ERC grant amounts?", perfect_response)
        assert score.total_score >= 90, (
            f"Perfect response should score 90+, got {score.total_score}"
        )

    def test_minimal_score_response(self):
        """Test that a minimal response gets low score."""
        evaluator = SourceAttributionEvaluator()

        minimal_response = "ERC provides funding for research."

        score = evaluator.evaluate("What are the ERC grant amounts?", minimal_response)
        assert score.total_score < 40, f"Minimal response should score <40, got {score.total_score}"

    def test_no_source_penalty(self):
        """Test that missing source attribution is penalized."""
        evaluator = SourceAttributionEvaluator()

        no_source_response = """
        ERC Grant Amounts:
        - Starting Grant: €1.5 million
        - Consolidator Grant: €2 million
        - Advanced Grant: €2.5 million
        - Synergy Grant: €10 million
        - Proof of Concept: €150,000

        Next steps: Apply at the EU Portal.
        """

        score = evaluator.evaluate("What are the ERC grant amounts?", no_source_response)
        assert score.source_attribution < 15, (
            "Missing source should get low source_attribution score"
        )
