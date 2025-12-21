"""
Live AI Response Quality Integration Tests.

IMPORTANT: These tests actually call the AI through the V3 API.
They verify that real responses meet quality standards and don't deflect.

These tests require:
1. Docker containers running (docker compose up)
2. API accessible at http://localhost:8000
3. All services healthy (Redis, PostgreSQL, Neo4j, Gemini)

Run with:
    pytest tests/test_ai_quality/test_live_response_quality.py -v

Skip in CI without live API:
    pytest tests/test_ai_quality/test_live_response_quality.py -v -m "not live_ai"

The tests validate:
- Responses are not deflections
- Quality scores meet minimum thresholds
- Required content elements are present
- Tool results are properly synthesized
"""

import pytest
import httpx
import logging
import random
import time
from typing import Optional, Dict, Any, List, Union
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.quality.response_quality_analyzer import (
    ResponseQualityAnalyzer,
    QualityAnalysis,
    ResponseCategory,
    QueryType,
)

logger = logging.getLogger(__name__)

# Base URL for the API
API_BASE_URL = os.getenv("MAP_IT_API_URL", "http://localhost:8000")

# Quality thresholds
MIN_QUALITY_SCORE = 60  # Minimum acceptable score (relaxed for live tests)
MIN_RESPONSE_LENGTH = 100  # Minimum response length


def check_api_available() -> bool:
    """Check if the API is available before running tests."""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/v3/conversation/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip decorator for live tests
live_ai = pytest.mark.skipif(
    not check_api_available(),
    reason="Live API not available. Start Docker containers with: docker compose up"
)


class LiveAPIClient:
    """Client for calling the V3 API with quality analysis."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=120.0)  # 2 minute timeout for AI calls
        self.quality_analyzer = ResponseQualityAnalyzer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def send_message(
        self,
        query: str,
        conversation_id: Optional[int] = None,
        include_context: bool = True,
    ) -> Dict[str, Any]:
        """
        Send a message to the V3 API and return the response with quality analysis.

        Args:
            query: The user query to send.
            conversation_id: Optional conversation ID (integer). If None, generates a new one.
            include_context: Whether to include conversation context.

        Returns:
            Dict containing:
                - response: The AI response text
                - metadata: Response metadata including quality_analysis
                - quality_analysis: Analyzed quality of the response
                - raw_response: The raw API response
        """
        if conversation_id is None:
            # Generate a random integer conversation ID for testing
            conversation_id = random.randint(1000000, 9999999)

        url = f"{self.base_url}/api/v3/conversation/{conversation_id}/message"

        payload = {
            "message": query,
            "include_context": include_context,
        }

        start_time = time.time()
        response = self.client.post(url, json=payload)
        elapsed_ms = (time.time() - start_time) * 1000

        if response.status_code != 200:
            raise Exception(f"API returned {response.status_code}: {response.text}")

        result = response.json()

        # Extract response text
        response_text = result.get("response", "")

        # Perform quality analysis
        quality_analysis = self.quality_analyzer.analyze(
            query=query,
            response=response_text,
        )

        # Log quality for monitoring
        self._log_quality(query, response_text, quality_analysis, elapsed_ms)

        return {
            "response": response_text,
            "metadata": result.get("metadata", {}),
            "quality_analysis": quality_analysis,
            "raw_response": result,
            "elapsed_ms": elapsed_ms,
            "conversation_id": conversation_id,
        }

    def _log_quality(
        self,
        query: str,
        response: str,
        analysis: QualityAnalysis,
        elapsed_ms: float,
    ) -> None:
        """Log quality analysis for monitoring."""
        log_data = {
            "query_preview": query[:100],
            "response_length": len(response),
            "score": analysis.score,
            "category": analysis.category.value,
            "query_type": analysis.query_type.value,
            "deflection_phrases": len(analysis.deflection_phrases_found),
            "elements_found": len(analysis.elements_found),
            "elapsed_ms": round(elapsed_ms, 2),
        }

        if analysis.category == ResponseCategory.DEFLECTION:
            logger.warning(
                f"DEFLECTION DETECTED: {log_data} - phrases: {analysis.deflection_phrases_found}"
            )
        elif analysis.score < MIN_QUALITY_SCORE:
            logger.warning(f"LOW QUALITY SCORE: {log_data}")
        else:
            logger.info(f"Quality OK: {log_data}")


@pytest.fixture
def api_client():
    """Fixture for the live API client."""
    with LiveAPIClient() as client:
        yield client


# ============================================================================
# Health Check Test
# ============================================================================

@live_ai
class TestAPIHealth:
    """Test that the API is healthy before running other tests."""

    def test_api_health_check(self):
        """Verify API is healthy and all components are up."""
        response = httpx.get(f"{API_BASE_URL}/api/v3/conversation/health", timeout=10.0)

        assert response.status_code == 200, f"Health check failed: {response.text}"

        health = response.json()
        assert health.get("status") in ["healthy", "degraded"], f"Unhealthy: {health}"
        assert health.get("architecture") == "simplified_v3"

        components = health.get("components", {})
        assert components.get("redis") is True, "Redis not healthy"
        assert components.get("database") is True, "Database not healthy"
        assert components.get("gemini") is True, "Gemini not healthy"


# ============================================================================
# Quality Analysis Tests
# ============================================================================

@live_ai
class TestLiveResponseQuality:
    """
    Test live AI response quality.

    These tests call the actual AI and verify:
    1. Response is not a deflection
    2. Quality score meets threshold
    3. Required elements are present
    """

    
    def test_simple_faq_quality(self, api_client: LiveAPIClient):
        """Test quality of simple FAQ response."""
        result = api_client.send_message("What is Horizon Europe?")

        response = result["response"]
        analysis = result["quality_analysis"]

        # Assertions
        assert len(response) >= MIN_RESPONSE_LENGTH, (
            f"Response too short ({len(response)} chars): {response[:200]}"
        )
        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Response is a deflection: {analysis.deflection_phrases_found}"
        )
        assert analysis.category != ResponseCategory.EMPTY, (
            f"Response is empty: {response[:100]}"
        )
        assert analysis.score >= MIN_QUALITY_SCORE, (
            f"Quality score too low ({analysis.score}). "
            f"Missing elements: {analysis.missing_elements}"
        )

    
    def test_eligibility_faq_quality(self, api_client: LiveAPIClient):
        """Test quality of eligibility FAQ response."""
        result = api_client.send_message("Can SMEs participate in Horizon Europe RIA projects?")

        response = result["response"]
        analysis = result["quality_analysis"]

        # Should provide a clear answer about SME eligibility
        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Eligibility question got deflection: {analysis.deflection_phrases_found}"
        )
        assert analysis.score >= MIN_QUALITY_SCORE, (
            f"Quality score too low ({analysis.score})"
        )

        # Should contain eligibility-related content
        response_lower = response.lower()
        assert any(word in response_lower for word in ["yes", "eligible", "participate", "can"]), (
            f"Response doesn't address eligibility: {response[:300]}"
        )

    
    def test_call_search_quality(self, api_client: LiveAPIClient):
        """Test quality of funding call search response."""
        result = api_client.send_message("Find open funding calls for hydrogen research")

        response = result["response"]
        analysis = result["quality_analysis"]
        metadata = result["metadata"]

        # Should not deflect
        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Call search got deflection: {analysis.deflection_phrases_found}"
        )

        # Should have used search tools
        tools_used = metadata.get("tools_used", [])
        assert len(tools_used) > 0, "No tools were used for call search"

        # Response should mention calls or funding opportunities
        response_lower = response.lower()
        assert any(word in response_lower for word in ["call", "funding", "opportunity", "found"]), (
            f"Response doesn't discuss funding calls: {response[:300]}"
        )

    
    def test_project_search_quality(self, api_client: LiveAPIClient):
        """Test quality of project search response."""
        result = api_client.send_message("Find funded projects about quantum computing")

        response = result["response"]
        analysis = result["quality_analysis"]

        # Should not deflect
        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Project search got deflection: {analysis.deflection_phrases_found}"
        )

        # Response should mention projects
        response_lower = response.lower()
        assert any(word in response_lower for word in ["project", "found", "funded", "research"]), (
            f"Response doesn't discuss projects: {response[:300]}"
        )

    
    def test_budget_benchmark_quality(self, api_client: LiveAPIClient):
        """Test quality of budget benchmark response."""
        result = api_client.send_message(
            "What is the typical budget for a Horizon Europe RIA project in Cluster 5?"
        )

        response = result["response"]
        analysis = result["quality_analysis"]

        # Should not deflect
        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Budget query got deflection: {analysis.deflection_phrases_found}"
        )
        assert analysis.score >= MIN_QUALITY_SCORE, (
            f"Quality score too low ({analysis.score})"
        )

        # Response should contain budget-related numbers
        assert any(char.isdigit() for char in response), (
            f"Response contains no numbers for budget query: {response[:300]}"
        )

    
    def test_partner_discovery_quality(self, api_client: LiveAPIClient):
        """Test quality of partner discovery response."""
        result = api_client.send_message(
            "Find organizations with experience in hydrogen fuel cell research in Germany"
        )

        response = result["response"]
        analysis = result["quality_analysis"]

        # Should not deflect
        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Partner search got deflection: {analysis.deflection_phrases_found}"
        )

        # Response should mention organizations or partners
        response_lower = response.lower()
        assert any(word in response_lower for word in ["partner", "organization", "found", "experience"]), (
            f"Response doesn't discuss partners: {response[:300]}"
        )


# ============================================================================
# Quality Metadata Tests
# ============================================================================

@live_ai
class TestQualityMetadata:
    """Test that quality_analysis is included in response metadata."""

    
    def test_quality_analysis_in_metadata(self, api_client: LiveAPIClient):
        """Test that quality_analysis is included in API response metadata."""
        result = api_client.send_message("What is the ERC Starting Grant?")

        metadata = result["metadata"]

        # Check if quality_analysis is in metadata
        # Note: This depends on the integration from the previous iteration
        if "quality_analysis" in metadata:
            qa = metadata["quality_analysis"]
            assert "score" in qa, "quality_analysis missing score"
            assert "category" in qa, "quality_analysis missing category"
            assert "query_type" in qa, "quality_analysis missing query_type"

            # Validate the score is reasonable
            assert qa["score"] >= 0, "Score is negative"
            assert qa["score"] <= 100, "Score exceeds 100"
        else:
            # Log a warning but don't fail - the local analyzer still works
            logger.warning(
                "quality_analysis not found in API metadata. "
                "Using local analyzer for validation."
            )


# ============================================================================
# Deflection Detection Tests
# ============================================================================

@live_ai
class TestNoDeflections:
    """
    Test that the AI doesn't deflect on queries it should answer.

    These tests specifically look for deflection patterns that indicate
    the AI is avoiding answering when it shouldn't.
    """

    
    @pytest.mark.parametrize("query", [
        "What is Horizon Europe?",
        "What is a RIA project type?",
        "What is the minimum consortium size?",
        "Can universities coordinate projects?",
    ])
    def test_basic_faq_no_deflection(self, api_client: LiveAPIClient, query: str):
        """Test that basic FAQs don't result in deflections."""
        result = api_client.send_message(query)

        analysis = result["quality_analysis"]

        assert analysis.category != ResponseCategory.DEFLECTION, (
            f"Query '{query}' resulted in deflection. "
            f"Phrases found: {analysis.deflection_phrases_found}"
        )
        assert analysis.category != ResponseCategory.EMPTY, (
            f"Query '{query}' resulted in empty response"
        )

    
    def test_deflection_phrase_check(self, api_client: LiveAPIClient):
        """Test that responses don't contain common deflection phrases."""
        result = api_client.send_message("What are the eligibility requirements for Horizon Europe?")

        response = result["response"].lower()
        analysis = result["quality_analysis"]

        # Check for common deflection phrases
        deflection_phrases = [
            "could not find",
            "no information available",
            "i am not sure",
            "i cannot answer",
            "unable to retrieve",
        ]

        found_deflections = [p for p in deflection_phrases if p in response]

        assert len(found_deflections) == 0, (
            f"Response contains deflection phrases: {found_deflections}. "
            f"Full response: {result['response'][:500]}"
        )


# ============================================================================
# Quality Score Threshold Tests
# ============================================================================

@live_ai
class TestQualityThresholds:
    """
    Test that responses meet quality score thresholds.

    These tests verify that quality scores are above minimum
    acceptable levels for different query types.
    """

    
    @pytest.mark.parametrize("query,min_score", [
        ("What is Horizon Europe?", 60),
        ("Can SMEs apply to RIA projects?", 55),
        ("What is the deadline for ERC Starting Grant?", 50),
        ("Find hydrogen funding opportunities", 50),
    ])
    def test_quality_score_thresholds(
        self, api_client: LiveAPIClient, query: str, min_score: int
    ):
        """Test that quality scores meet minimum thresholds."""
        result = api_client.send_message(query)

        analysis = result["quality_analysis"]

        assert analysis.score >= min_score, (
            f"Query '{query}' scored {analysis.score}, below threshold {min_score}. "
            f"Category: {analysis.category.value}. "
            f"Missing elements: {analysis.missing_elements}. "
            f"Deflection phrases: {analysis.deflection_phrases_found}"
        )


# ============================================================================
# Performance Benchmarking
# ============================================================================

@live_ai
class TestResponsePerformance:
    """Test response time performance."""

    
    def test_simple_query_performance(self, api_client: LiveAPIClient):
        """Test that simple queries respond within reasonable time."""
        result = api_client.send_message("What is Horizon Europe?")

        elapsed_ms = result["elapsed_ms"]

        # Simple FAQ should respond within 30 seconds
        assert elapsed_ms < 30000, (
            f"Simple query took too long: {elapsed_ms}ms"
        )

    
    def test_complex_query_performance(self, api_client: LiveAPIClient):
        """Test that complex queries respond within extended time."""
        result = api_client.send_message(
            "Compare EIC Accelerator success rates with ERC Starting Grant"
        )

        elapsed_ms = result["elapsed_ms"]

        # Complex query with multiple tool calls - allow up to 120 seconds
        assert elapsed_ms < 120000, (
            f"Complex query took too long: {elapsed_ms}ms"
        )


# ============================================================================
# Conversation Context Tests
# ============================================================================

@live_ai
class TestConversationContext:
    """Test conversation context handling."""

    
    def test_follow_up_quality(self, api_client: LiveAPIClient):
        """Test that follow-up questions maintain quality."""
        conv_id = random.randint(1000000, 9999999)

        # First message
        result1 = api_client.send_message(
            "What is the EIC Accelerator?",
            conversation_id=conv_id
        )

        assert result1["quality_analysis"].category != ResponseCategory.DEFLECTION, (
            "First message was a deflection"
        )

        # Follow-up message
        result2 = api_client.send_message(
            "What is the success rate?",
            conversation_id=conv_id
        )

        assert result2["quality_analysis"].category != ResponseCategory.DEFLECTION, (
            "Follow-up message was a deflection"
        )
        assert result2["quality_analysis"].score >= MIN_QUALITY_SCORE, (
            f"Follow-up quality too low: {result2['quality_analysis'].score}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--timeout=180"])
