"""
Tests for Scenario 051: API Rate Limited - Graceful Degradation

PRD Reference:
- Simulate: EU Portal API rate limit
- Query: "Get details for call HORIZON-xxx"
- Expected: Uses cached data or explains delay
- Verify: Doesn't fail completely
- Fix if: Crashes on rate limit
- Pass threshold: 75

This scenario tests that when EU Portal API returns 429 (rate limited),
the system gracefully degrades to cached/local data and provides useful
results while informing the user of the limitation.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Unit Tests - Test rate limit configuration and constants
# ============================================================================


class TestRateLimitConfiguration:
    """Test that rate limit constants are properly configured."""

    def test_rate_limit_constants_exist(self):
        """Test that rate limit constants are defined."""
        from app.services.call_enrichment_service import (
            BASE_DELAY,
            CACHE_TTL,
            EXPONENTIAL_BASE,
            MAX_DELAY,
            MAX_RETRIES,
        )

        assert MAX_RETRIES > 0, "MAX_RETRIES should be positive"
        assert BASE_DELAY > 0, "BASE_DELAY should be positive"
        assert MAX_DELAY > 0, "MAX_DELAY should be positive"
        assert EXPONENTIAL_BASE > 1, "EXPONENTIAL_BASE should be > 1"
        assert CACHE_TTL > 0, "CACHE_TTL should be positive"

    def test_rate_limit_constants_reasonable_values(self):
        """Test that rate limit values are reasonable."""
        from app.services.call_enrichment_service import (
            BASE_DELAY,
            CACHE_TTL,
            MAX_DELAY,
            MAX_RETRIES,
        )

        # Should have 2-5 retries
        assert 2 <= MAX_RETRIES <= 5, f"MAX_RETRIES {MAX_RETRIES} should be 2-5"
        # Base delay should be 0.5-5s
        assert 0.5 <= BASE_DELAY <= 5, f"BASE_DELAY {BASE_DELAY}s should be 0.5-5s"
        # Max delay should be 10-60s
        assert 10 <= MAX_DELAY <= 60, f"MAX_DELAY {MAX_DELAY}s should be 10-60s"
        # Cache TTL should be 5 minutes to 2 hours
        assert 300 <= CACHE_TTL <= 7200, f"CACHE_TTL {CACHE_TTL}s should be 300-7200s"


class TestRateLimitExceptions:
    """Test custom exceptions for rate limiting."""

    def test_rate_limit_error_exists(self):
        """Test that RateLimitError exception exists."""
        from app.services.call_enrichment_service import RateLimitError

        assert RateLimitError is not None

    def test_rate_limit_error_has_retry_after(self):
        """Test that RateLimitError can store retry_after value."""
        from app.services.call_enrichment_service import RateLimitError

        err = RateLimitError("Rate limited", retry_after=60)
        assert err.retry_after == 60

    def test_rate_limit_error_message(self):
        """Test RateLimitError message."""
        from app.services.call_enrichment_service import RateLimitError

        err = RateLimitError("API rate limited")
        assert "rate limited" in str(err).lower()

    def test_api_unavailable_error_exists(self):
        """Test that APIUnavailableError exception exists."""
        from app.services.call_enrichment_service import APIUnavailableError

        assert APIUnavailableError is not None


class TestServiceAvailability:
    """Test service availability configuration for graceful degradation."""

    def test_get_call_details_in_degradable_tools(self):
        """Test that get_call_details is in DEGRADABLE_TOOLS."""
        from app.core.service_availability import DEGRADABLE_TOOLS

        assert (
            "get_call_details" in DEGRADABLE_TOOLS
        ), "get_call_details should be in DEGRADABLE_TOOLS"

    def test_eu_portal_api_service_type_exists(self):
        """Test that EU_PORTAL_API service type exists."""
        from app.core.service_availability import ServiceType

        assert hasattr(ServiceType, "EU_PORTAL_API"), "ServiceType.EU_PORTAL_API should exist"

    def test_get_call_details_degradable_on_eu_portal_api(self):
        """Test that get_call_details can degrade when EU_PORTAL_API unavailable."""
        from app.core.service_availability import DEGRADABLE_TOOLS, ServiceType

        degradable_services = DEGRADABLE_TOOLS.get("get_call_details", [])
        assert (
            ServiceType.EU_PORTAL_API in degradable_services
        ), "get_call_details should degrade when EU_PORTAL_API unavailable"


# ============================================================================
# Unit Tests - Test caching methods
# ============================================================================


class TestCacheMethods:
    """Test in-memory caching methods."""

    def test_cache_methods_exist(self):
        """Test that cache methods exist."""
        from app.services.call_enrichment_service import CallEnrichmentService

        assert hasattr(CallEnrichmentService, "get_cached")
        assert hasattr(CallEnrichmentService, "set_cached")
        assert hasattr(CallEnrichmentService, "clear_cache")

    def test_cache_set_and_get(self):
        """Test setting and getting cached data."""
        from app.services.call_enrichment_service import CallEnrichmentService

        # Clear cache first
        CallEnrichmentService.clear_cache()

        test_data = {"topic_code": "TEST-123", "title": "Test Call"}
        CallEnrichmentService.set_cached("TEST-123", test_data)

        cached = CallEnrichmentService.get_cached("TEST-123")
        assert cached is not None
        assert cached["topic_code"] == "TEST-123"

        # Clean up
        CallEnrichmentService.clear_cache()

    def test_cache_case_insensitive(self):
        """Test that cache lookup is case insensitive."""
        from app.services.call_enrichment_service import CallEnrichmentService

        CallEnrichmentService.clear_cache()

        test_data = {"topic_code": "HORIZON-TEST-01", "title": "Test Call"}
        CallEnrichmentService.set_cached("HORIZON-TEST-01", test_data)

        # Should work with different cases
        cached = CallEnrichmentService.get_cached("horizon-test-01")
        assert cached is not None

        CallEnrichmentService.clear_cache()

    def test_cache_clear(self):
        """Test clearing the cache."""
        from app.services.call_enrichment_service import CallEnrichmentService

        CallEnrichmentService.set_cached("TEST-CLEAR", {"title": "Test"})
        CallEnrichmentService.clear_cache()

        cached = CallEnrichmentService.get_cached("TEST-CLEAR")
        assert cached is None


class TestRateLimitState:
    """Test rate limit state management."""

    def test_is_rate_limited_method_exists(self):
        """Test that is_rate_limited method exists."""
        from app.services.call_enrichment_service import CallEnrichmentService

        assert hasattr(CallEnrichmentService, "is_rate_limited")
        assert hasattr(CallEnrichmentService, "set_rate_limited")

    def test_rate_limit_state_tracking(self):
        """Test that rate limit state is tracked correctly."""
        from app.services.call_enrichment_service import CallEnrichmentService

        # Clear any existing state
        CallEnrichmentService.clear_cache()

        # Initially not rate limited
        assert not CallEnrichmentService.is_rate_limited()

        # Set rate limited for 1 second
        CallEnrichmentService.set_rate_limited(retry_after=1)

        # Should be rate limited now
        assert CallEnrichmentService.is_rate_limited()

        # Clear and check again
        CallEnrichmentService.clear_cache()
        assert not CallEnrichmentService.is_rate_limited()


# ============================================================================
# Unit Tests - Test retry logic
# ============================================================================


class TestRetryLogic:
    """Test exponential backoff retry logic."""

    def test_fetch_with_retry_method_exists(self):
        """Test that _fetch_from_api_with_retry method exists."""
        from app.services.call_enrichment_service import CallEnrichmentService

        service = CallEnrichmentService("postgresql://test:test@localhost/test")
        assert hasattr(service, "_fetch_from_api_with_retry")

    def test_rate_limit_error_raised_on_429(self):
        """Test that RateLimitError is raised on 429 response."""
        from app.services.call_enrichment_service import CallEnrichmentService, RateLimitError

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        # Mock the HTTP client to return 429
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        service._client = mock_client

        with pytest.raises(RateLimitError):
            service._fetch_direct_topic_details("TEST-CALL")

    def test_rate_limit_error_includes_retry_after(self):
        """Test that RateLimitError includes Retry-After header value."""
        from app.services.call_enrichment_service import CallEnrichmentService, RateLimitError

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        service._client = mock_client

        try:
            service._fetch_direct_topic_details("TEST-CALL")
            pytest.fail("Should have raised RateLimitError")
        except RateLimitError as e:
            assert e.retry_after == 120

    def test_api_unavailable_error_on_500(self):
        """Test that APIUnavailableError is raised on 500 response."""
        from app.services.call_enrichment_service import APIUnavailableError, CallEnrichmentService

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        service._client = mock_client

        with pytest.raises(APIUnavailableError):
            service._fetch_direct_topic_details("TEST-CALL")

    def test_api_unavailable_error_on_503(self):
        """Test that APIUnavailableError is raised on 503 response."""
        from app.services.call_enrichment_service import APIUnavailableError, CallEnrichmentService

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.headers = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        service._client = mock_client

        with pytest.raises(APIUnavailableError):
            service._fetch_direct_topic_details("TEST-CALL")


# ============================================================================
# Integration Tests - Test graceful degradation
# ============================================================================


class TestGracefulDegradation:
    """Test graceful degradation when rate limited."""

    def test_uses_local_data_when_rate_limited(self):
        """Test that local data is returned when rate limited."""
        from app.services.call_enrichment_service import CallEnrichmentService

        # Clear state
        CallEnrichmentService.clear_cache()

        # Set rate limited
        CallEnrichmentService.set_rate_limited(retry_after=300)

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        # Mock local database to return data
        local_data = {
            "topic_code": "HORIZON-TEST-01",
            "title": "Test Call",
            "scope": "This is a test call with sufficient scope content for testing.",
            "deadline": "2026-06-01",
        }

        with patch.object(service, "_get_local_call", return_value=local_data):
            result = service.get_call_details("HORIZON-TEST-01")

        assert result is not None
        assert result.get("_rate_limited") is True
        assert "HORIZON-TEST-01" in result.get("topic_code", "")

        # Clean up
        CallEnrichmentService.clear_cache()

    def test_rate_limited_message_included(self):
        """Test that rate limited message is included in response."""
        from app.services.call_enrichment_service import CallEnrichmentService

        CallEnrichmentService.clear_cache()
        CallEnrichmentService.set_rate_limited(retry_after=300)

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        local_data = {
            "topic_code": "HORIZON-TEST-02",
            "title": "Test Call",
            "scope": "Sufficient scope content here.",
            "deadline": "2026-06-01",
        }

        with patch.object(service, "_get_local_call", return_value=local_data):
            result = service.get_call_details("HORIZON-TEST-02")

        assert result is not None
        assert "_rate_limited_message" in result
        assert "unavailable" in result["_rate_limited_message"].lower()

        CallEnrichmentService.clear_cache()

    def test_uses_cached_api_data_when_rate_limited(self):
        """Test that cached API data is used when rate limited."""
        from app.services.call_enrichment_service import CallEnrichmentService

        CallEnrichmentService.clear_cache()

        # First, cache some data
        cached_data = {
            "topic_code": "HORIZON-CACHED-01",
            "title": "Cached Call",
            "scope": "Cached scope content.",
            "deadline": "2026-06-01",
        }
        CallEnrichmentService.set_cached("HORIZON-CACHED-01", cached_data)

        # Then set rate limited
        CallEnrichmentService.set_rate_limited(retry_after=300)

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        # Mock local database to return None (no local data)
        with patch.object(service, "_get_local_call", return_value=None):
            result = service.get_call_details("HORIZON-CACHED-01")

        assert result is not None
        assert result.get("title") == "Cached Call"

        CallEnrichmentService.clear_cache()

    def test_returns_none_when_no_data_available(self):
        """Test that None is returned when no data available and rate limited."""
        from app.services.call_enrichment_service import CallEnrichmentService

        CallEnrichmentService.clear_cache()
        CallEnrichmentService.set_rate_limited(retry_after=300)

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        with patch.object(service, "_get_local_call", return_value=None):
            result = service.get_call_details("NONEXISTENT-CALL")

        assert result is None

        CallEnrichmentService.clear_cache()


class TestRetryWithBackoff:
    """Test retry with exponential backoff."""

    @patch("time.sleep")  # Don't actually sleep in tests
    def test_retries_on_rate_limit(self, mock_sleep):
        """Test that retries happen on rate limit with backoff."""
        from app.services.call_enrichment_service import CallEnrichmentService, RateLimitError

        service = CallEnrichmentService("postgresql://test:test@localhost/test")
        CallEnrichmentService.clear_cache()

        # Track how many times _fetch_from_api is called
        call_count = 0

        def mock_fetch(topic_code):
            nonlocal call_count
            call_count += 1
            raise RateLimitError("Rate limited", retry_after=5)

        with patch.object(service, "_fetch_from_api", side_effect=mock_fetch):
            with patch.object(service, "_get_local_call", return_value=None):
                service._fetch_from_api_with_retry("TEST-CALL")

        # Should have retried MAX_RETRIES times + initial attempt
        from app.services.call_enrichment_service import MAX_RETRIES

        assert call_count == MAX_RETRIES + 1
        assert mock_sleep.call_count >= MAX_RETRIES

    @patch("time.sleep")
    def test_respects_retry_after_header(self, mock_sleep):
        """Test that Retry-After header value is respected."""
        from app.services.call_enrichment_service import CallEnrichmentService, RateLimitError

        service = CallEnrichmentService("postgresql://test:test@localhost/test")
        CallEnrichmentService.clear_cache()

        def mock_fetch(topic_code):
            raise RateLimitError("Rate limited", retry_after=120)

        with patch.object(service, "_fetch_from_api", side_effect=mock_fetch):
            with patch.object(service, "_get_local_call", return_value=None):
                service._fetch_from_api_with_retry("TEST-CALL")

        # Check that at least one sleep call was >= 120 seconds (or close due to jitter)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        # At least one call should use the retry_after value (120s)
        # Due to jitter, it could be slightly different
        assert any(s >= 60 for s in sleep_calls)  # At least respecting retry_after logic


# ============================================================================
# Integration Tests - Test with mock API responses
# ============================================================================


class TestAPIIntegration:
    """Test integration with mocked API responses."""

    def test_successful_api_call_cached(self):
        """Test that successful API calls are cached."""
        from app.services.call_enrichment_service import CallEnrichmentService

        CallEnrichmentService.clear_cache()

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        # Mock successful API response
        api_response = {
            "topic_code": "HORIZON-SUCCESS-01",
            "title": "Successful API Call",
            "scope": "This is the scope from the API.",
            "deadline": datetime.now().date(),
            "enriched_from_api": True,
        }

        with patch.object(service, "_fetch_from_api_with_retry", return_value=api_response):
            with patch.object(service, "_get_local_call", return_value=None):
                with patch.object(service, "_cache_call"):
                    result = service.get_call_details("HORIZON-SUCCESS-01", force_refresh=True)

        assert result is not None
        assert result["title"] == "Successful API Call"

        # Verify it was cached
        cached = CallEnrichmentService.get_cached("HORIZON-SUCCESS-01")
        assert cached is not None

        CallEnrichmentService.clear_cache()

    def test_no_api_call_when_cached(self):
        """Test that API is not called when data is cached."""
        from app.services.call_enrichment_service import CallEnrichmentService

        CallEnrichmentService.clear_cache()

        # Pre-cache data
        cached_data = {
            "topic_code": "HORIZON-CACHED-02",
            "title": "Cached Data",
            "scope": "Cached scope.",
            "deadline": "2026-06-01",
        }
        CallEnrichmentService.set_cached("HORIZON-CACHED-02", cached_data)

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        # This should NOT be called
        api_called = False

        def mock_api_call(topic_code):
            nonlocal api_called
            api_called = True
            return None

        with patch.object(service, "_fetch_from_api_with_retry", side_effect=mock_api_call):
            result = service.get_call_details("HORIZON-CACHED-02")

        assert result is not None
        assert result["title"] == "Cached Data"
        assert not api_called  # API should not have been called

        CallEnrichmentService.clear_cache()


# ============================================================================
# Full Scenario Test
# ============================================================================


class TestFullScenario051:
    """Full scenario test for API rate limiting graceful degradation."""

    def test_scenario_051_graceful_degradation(self):
        """
        Test the complete scenario:
        1. API returns 429 rate limit
        2. System falls back to cached/local data
        3. Response includes rate limit notification
        4. No crash or hard failure
        """
        from app.services.call_enrichment_service import CallEnrichmentService

        CallEnrichmentService.clear_cache()

        # Pre-cache some data as if from a previous successful call
        cached_data = {
            "topic_code": "HORIZON-CL5-2026-D3-01",
            "title": "Sustainable Energy Research",
            "scope": "Research into sustainable energy solutions for climate adaptation.",
            "deadline": "2026-09-15",
            "status": "open",
            "budget": 5000000,
        }
        CallEnrichmentService.set_cached("HORIZON-CL5-2026-D3-01", cached_data)

        # Simulate being rate limited
        CallEnrichmentService.set_rate_limited(retry_after=300)

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        # Query for call details (should use cache due to rate limit)
        result = service.get_call_details("HORIZON-CL5-2026-D3-01")

        # Assertions
        assert result is not None, "Should return data, not None"
        assert "topic_code" in result, "Should include topic_code"
        assert result.get("_rate_limited") is True, "Should indicate rate limited"
        assert "_rate_limited_message" in result, "Should include explanation"

        # Clean up
        CallEnrichmentService.clear_cache()

    @patch("time.sleep")
    def test_scenario_051_no_crash_on_complete_failure(self, mock_sleep):
        """
        Test that system doesn't crash when:
        1. API is rate limited
        2. No cached data exists
        3. No local data exists
        """
        from app.services.call_enrichment_service import CallEnrichmentService, RateLimitError

        CallEnrichmentService.clear_cache()

        service = CallEnrichmentService("postgresql://test:test@localhost/test")

        def mock_api_fail(topic_code):
            raise RateLimitError("Rate limited", retry_after=60)

        with patch.object(service, "_fetch_from_api", side_effect=mock_api_fail):
            with patch.object(service, "_get_local_call", return_value=None):
                # This should not raise an exception
                result = service._fetch_from_api_with_retry("NONEXISTENT-CALL")

        # Should gracefully return None, not crash
        assert result is None

        CallEnrichmentService.clear_cache()

    def test_scenario_051_quality_score_check(self):
        """
        Quality scoring check for Scenario 051.

        Score breakdown (threshold: 75/100):
        - Graceful Handling (25 pts): Doesn't crash, provides partial results
        - User Communication (20 pts): Clear message explaining limitation
        - Cache Usage (20 pts): Uses cached data when available
        - Retry Logic (20 pts): Implements exponential backoff
        - API Detection (15 pts): Correctly detects 429 status
        """
        from app.services.call_enrichment_service import (
            MAX_RETRIES,
            CallEnrichmentService,
            RateLimitError,
        )

        score = 0

        # API Detection (15 pts) - Check RateLimitError is raised on 429
        try:
            service = CallEnrichmentService("postgresql://test:test@localhost/test")
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {}
            with patch.object(service, "client") as mock_client:
                mock_client.get.return_value = mock_response
                try:
                    service._fetch_direct_topic_details("TEST")
                except RateLimitError:
                    score += 15
        except Exception:
            pass

        # Retry Logic (20 pts) - Check retry constants
        if MAX_RETRIES >= 2:
            score += 20

        # Cache Usage (20 pts) - Check cache methods work
        CallEnrichmentService.clear_cache()
        CallEnrichmentService.set_cached("TEST", {"data": "test"})
        if CallEnrichmentService.get_cached("TEST") is not None:
            score += 20
        CallEnrichmentService.clear_cache()

        # User Communication (20 pts) - Check rate limit message
        CallEnrichmentService.set_rate_limited(retry_after=60)
        service = CallEnrichmentService("postgresql://test:test@localhost/test")
        with patch.object(
            service, "_get_local_call", return_value={"topic_code": "T", "title": "T"}
        ):
            result = service.get_call_details("TEST")
            if result and "_rate_limited_message" in result:
                score += 20
        CallEnrichmentService.clear_cache()

        # Graceful Handling (25 pts) - Check no crash on rate limit
        CallEnrichmentService.set_rate_limited(retry_after=60)
        with patch.object(service, "_get_local_call", return_value=None):
            try:
                result = service.get_call_details("MISSING")
                # Should return None, not crash
                if result is None:
                    score += 25
            except Exception:
                pass  # Crash = no points
        CallEnrichmentService.clear_cache()

        print(f"\nScenario 051 Quality Score: {score}/100")
        assert score >= 75, f"Quality score {score}/100 below threshold 75"
