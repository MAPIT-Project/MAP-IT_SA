"""
Tests for the ToolAnalyticsService.

Tests:
- ToolUsageEvent dataclass
- Service initialization
- Event tracking
- Session metrics
- Buffer management
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.analytics.tool_analytics_service import (
    ToolAnalyticsService,
    ToolUsageEvent,
    get_analytics_service
)


class TestToolUsageEventDataclass:
    """Tests for the ToolUsageEvent dataclass."""

    def test_required_fields(self):
        """Test event with required fields."""
        event = ToolUsageEvent(
            tool_name="search_funding_calls",
            parameters={"keywords": "hydrogen"},
            execution_time_ms=150,
            success=True
        )

        assert event.tool_name == "search_funding_calls"
        assert event.parameters == {"keywords": "hydrogen"}
        assert event.execution_time_ms == 150
        assert event.success is True

    def test_optional_fields_default(self):
        """Test optional fields default to None or False."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            parameters={},
            execution_time_ms=100,
            success=True
        )

        assert event.error_message is None
        assert event.result_count is None
        assert event.result_quality_score is None
        assert event.conversation_id is None
        assert event.query_hash is None
        assert event.speculative is False

    def test_all_fields(self):
        """Test event with all fields."""
        event = ToolUsageEvent(
            tool_name="search_projects",
            parameters={"query": "AI research"},
            execution_time_ms=500,
            success=True,
            error_message=None,
            result_count=25,
            result_quality_score=0.85,
            conversation_id="conv-123",
            query_hash="abc123",
            speculative=True
        )

        assert event.result_count == 25
        assert event.result_quality_score == 0.85
        assert event.conversation_id == "conv-123"
        assert event.query_hash == "abc123"
        assert event.speculative is True

    def test_failed_event(self):
        """Test failed event with error message."""
        event = ToolUsageEvent(
            tool_name="search_funding_calls",
            parameters={"keywords": "test"},
            execution_time_ms=50,
            success=False,
            error_message="Database connection timeout"
        )

        assert event.success is False
        assert "timeout" in event.error_message

    def test_timestamp_auto_generated(self):
        """Test timestamp is auto-generated."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            parameters={},
            execution_time_ms=100,
            success=True
        )

        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)


class TestToolAnalyticsServiceInitialization:
    """Tests for service initialization."""

    def test_service_singleton(self):
        """Test singleton pattern."""
        # Reset singleton
        ToolAnalyticsService._instance = None

        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service1 = ToolAnalyticsService()
            service2 = ToolAnalyticsService()

            assert service1 is service2

    def test_service_initialization_without_db(self):
        """Test service initializes without database."""
        ToolAnalyticsService._instance = None

        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()

            assert service._initialized is True
            assert service.enabled is False

    def test_buffer_initialized(self):
        """Test buffer is initialized."""
        ToolAnalyticsService._instance = None

        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()

            assert hasattr(service, 'buffer')
            assert isinstance(service.buffer, list)
            assert len(service.buffer) == 0

    def test_session_metrics_initialized(self):
        """Test session metrics are initialized."""
        ToolAnalyticsService._instance = None

        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()

            assert hasattr(service, 'session_metrics')


class TestToolUsageTracking:
    """Tests for tool usage tracking."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()
            service.enabled = True  # Enable for testing
            service.buffer = []
            return service

    @pytest.mark.asyncio
    async def test_track_tool_usage_updates_session_metrics(self, mock_service):
        """Test tracking updates session metrics."""
        event = ToolUsageEvent(
            tool_name="search_funding_calls",
            parameters={"keywords": "hydrogen"},
            execution_time_ms=100,
            success=True
        )

        # Mock _flush_buffer to avoid DB call
        mock_service._flush_buffer = AsyncMock()

        await mock_service.track_tool_usage(event)

        metrics = mock_service.session_metrics["search_funding_calls"]
        assert metrics['calls'] == 1
        assert metrics['successes'] == 1

    @pytest.mark.asyncio
    async def test_track_failed_event(self, mock_service):
        """Test tracking failed event."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            parameters={},
            execution_time_ms=50,
            success=False,
            error_message="Error occurred"
        )

        mock_service._flush_buffer = AsyncMock()

        await mock_service.track_tool_usage(event)

        metrics = mock_service.session_metrics["test_tool"]
        assert metrics['calls'] == 1
        assert metrics['successes'] == 0

    @pytest.mark.asyncio
    async def test_track_speculative_event(self, mock_service):
        """Test tracking speculative event."""
        event = ToolUsageEvent(
            tool_name="search_projects",
            parameters={"query": "AI"},
            execution_time_ms=200,
            success=True,
            speculative=True
        )

        mock_service._flush_buffer = AsyncMock()

        await mock_service.track_tool_usage(event)

        metrics = mock_service.session_metrics["search_projects"]
        assert metrics['speculative_hits'] == 1


class TestSessionMetrics:
    """Tests for session metrics."""

    @pytest.fixture
    def service_with_metrics(self):
        """Create service with pre-populated metrics."""
        ToolAnalyticsService._instance = None
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()
            service.enabled = True

            # Populate metrics
            service.session_metrics["search_funding_calls"] = {
                'calls': 10,
                'successes': 9,
                'total_time_ms': 1000,
                'speculative_hits': 3
            }
            service.session_metrics["search_projects"] = {
                'calls': 5,
                'successes': 5,
                'total_time_ms': 750,
                'speculative_hits': 1
            }

            return service

    def test_get_session_metrics(self, service_with_metrics):
        """Test getting session metrics."""
        metrics = service_with_metrics.get_session_metrics()

        assert "search_funding_calls" in metrics
        assert "search_projects" in metrics

    def test_session_metrics_calculations(self, service_with_metrics):
        """Test session metrics calculations."""
        metrics = service_with_metrics.get_session_metrics()

        funding_metrics = metrics["search_funding_calls"]
        assert funding_metrics['total_calls'] == 10
        assert funding_metrics['successful_calls'] == 9
        assert funding_metrics['success_rate'] == 90.0
        assert funding_metrics['avg_time_ms'] == 100.0  # 1000/10
        assert funding_metrics['speculative_hits'] == 3


class TestBufferManagement:
    """Tests for buffer management."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()
            service.enabled = True
            service.buffer = []
            service.buffer_size = 5  # Small buffer for testing
            return service

    @pytest.mark.asyncio
    async def test_buffer_fills_before_flush(self, mock_service):
        """Test buffer fills before flush."""
        mock_service._flush_buffer = AsyncMock()

        for i in range(3):
            event = ToolUsageEvent(
                tool_name=f"tool_{i}",
                parameters={},
                execution_time_ms=i * 100,
                success=True
            )
            await mock_service.track_tool_usage(event)

        # Buffer should have events (not flushed yet)
        assert len(mock_service.buffer) == 3

    @pytest.mark.asyncio
    async def test_buffer_flushes_when_full(self, mock_service):
        """Test buffer flushes when full."""
        flush_called = False

        async def mock_flush():
            nonlocal flush_called
            flush_called = True
            mock_service.buffer.clear()

        mock_service._flush_buffer = mock_flush

        for i in range(6):  # More than buffer_size
            event = ToolUsageEvent(
                tool_name=f"tool_{i}",
                parameters={},
                execution_time_ms=100,
                success=True
            )
            await mock_service.track_tool_usage(event)

        assert flush_called


class TestQueryHashing:
    """Tests for query hashing."""

    def test_hash_query(self):
        """Test query hashing produces consistent results."""
        query = "Find hydrogen funding calls"

        hash1 = ToolAnalyticsService.hash_query(query)
        hash2 = ToolAnalyticsService.hash_query(query)

        assert hash1 == hash2
        assert len(hash1) == 16  # Should be 16 chars

    def test_different_queries_different_hashes(self):
        """Test different queries produce different hashes."""
        hash1 = ToolAnalyticsService.hash_query("Query one")
        hash2 = ToolAnalyticsService.hash_query("Query two")

        assert hash1 != hash2


class TestGetAnalyticsService:
    """Tests for get_analytics_service function."""

    def test_returns_instance(self):
        """Test function returns instance."""
        import app.services.analytics.tool_analytics_service as module
        module._analytics_service = None
        ToolAnalyticsService._instance = None

        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = get_analytics_service()

            assert service is not None
            assert isinstance(service, ToolAnalyticsService)

    def test_returns_same_instance(self):
        """Test function returns same instance."""
        import app.services.analytics.tool_analytics_service as module
        module._analytics_service = None
        ToolAnalyticsService._instance = None

        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service1 = get_analytics_service()
            service2 = get_analytics_service()

            assert service1 is service2


class TestToolPerformanceQueries:
    """Tests for tool performance queries (with mocked DB)."""

    @pytest.fixture
    def service_with_mock_db(self):
        """Create service with mocked database."""
        ToolAnalyticsService._instance = None
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}, clear=False):
            with patch.object(ToolAnalyticsService, '_init_pool'):
                service = ToolAnalyticsService()
                service.enabled = True
                return service

    def test_get_tool_performance_disabled(self):
        """Test get_tool_performance when disabled."""
        ToolAnalyticsService._instance = None
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()
            service.enabled = False

            result = service.get_tool_performance()

            assert "error" in result

    def test_get_slow_tools_disabled(self):
        """Test get_slow_tools when disabled."""
        ToolAnalyticsService._instance = None
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()
            service.enabled = False

            result = service.get_slow_tools()

            assert result == []


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            service = ToolAnalyticsService()
            service.enabled = True
            service.buffer = []
            return service

    @pytest.mark.asyncio
    async def test_track_with_empty_parameters(self, mock_service):
        """Test tracking with empty parameters."""
        mock_service._flush_buffer = AsyncMock()

        event = ToolUsageEvent(
            tool_name="test_tool",
            parameters={},
            execution_time_ms=100,
            success=True
        )

        await mock_service.track_tool_usage(event)
        assert len(mock_service.buffer) == 1

    @pytest.mark.asyncio
    async def test_track_with_large_parameters(self, mock_service):
        """Test tracking with large parameters."""
        mock_service._flush_buffer = AsyncMock()

        large_params = {"data": "x" * 10000}
        event = ToolUsageEvent(
            tool_name="test_tool",
            parameters=large_params,
            execution_time_ms=100,
            success=True
        )

        await mock_service.track_tool_usage(event)
        assert len(mock_service.buffer) == 1

    @pytest.mark.asyncio
    async def test_track_with_zero_execution_time(self, mock_service):
        """Test tracking with zero execution time."""
        mock_service._flush_buffer = AsyncMock()

        event = ToolUsageEvent(
            tool_name="test_tool",
            parameters={},
            execution_time_ms=0,
            success=True
        )

        await mock_service.track_tool_usage(event)
        assert mock_service.session_metrics["test_tool"]['total_time_ms'] == 0

    @pytest.mark.asyncio
    async def test_tracking_disabled(self, mock_service):
        """Test tracking when disabled."""
        mock_service.enabled = False

        event = ToolUsageEvent(
            tool_name="test_tool",
            parameters={},
            execution_time_ms=100,
            success=True
        )

        await mock_service.track_tool_usage(event)

        # Should not add to buffer when disabled
        assert len(mock_service.buffer) == 0


# Helper for async mocking
class AsyncMock(Mock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
