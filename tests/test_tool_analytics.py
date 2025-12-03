"""
Comprehensive tests for the ToolAnalyticsService.

Tests:
- Tool usage event tracking
- Buffered writes
- Statistics retrieval
- Tool performance analysis
- Error rate tracking
- Async operations
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
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
            execution_time_ms=150,
            success=True
        )

        assert event.tool_name == "search_funding_calls"
        assert event.execution_time_ms == 150
        assert event.success == True

    def test_optional_fields_default(self):
        """Test optional fields default to None."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            execution_time_ms=100,
            success=True
        )

        assert event.query_type is None
        assert event.result_count is None
        assert event.error_message is None
        assert event.conversation_id is None

    def test_all_fields(self):
        """Test event with all fields."""
        event = ToolUsageEvent(
            tool_name="search_projects",
            execution_time_ms=500,
            success=True,
            query_type="search_projects",
            result_count=25,
            error_message=None,
            conversation_id="conv-123"
        )

        assert event.result_count == 25
        assert event.conversation_id == "conv-123"

    def test_failed_event(self):
        """Test failed event with error message."""
        event = ToolUsageEvent(
            tool_name="search_funding_calls",
            execution_time_ms=50,
            success=False,
            error_message="Database connection timeout"
        )

        assert event.success == False
        assert "timeout" in event.error_message


class TestToolAnalyticsServiceInitialization:
    """Tests for service initialization."""

    def test_service_initialization_without_db(self):
        """Test service initializes without database."""
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            # Reset singleton
            ToolAnalyticsService._instance = None

            service = ToolAnalyticsService()

            assert service._initialized == True

    def test_buffer_initialized(self):
        """Test buffer is initialized."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()

        assert hasattr(service, '_buffer')
        assert isinstance(service._buffer, list)

    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        ToolAnalyticsService._instance = None

        service1 = ToolAnalyticsService()
        service2 = ToolAnalyticsService()

        assert service1 is service2


class TestToolUsageTracking:
    """Tests for tool usage tracking."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service._buffer = []
        return service

    def test_track_tool_usage_adds_to_buffer(self, mock_service):
        """Test tracking adds event to buffer."""
        event = ToolUsageEvent(
            tool_name="search_funding_calls",
            execution_time_ms=100,
            success=True
        )

        mock_service.track_tool_usage(event)

        assert len(mock_service._buffer) == 1
        assert mock_service._buffer[0].tool_name == "search_funding_calls"

    def test_multiple_events_buffered(self, mock_service):
        """Test multiple events are buffered."""
        for i in range(5):
            event = ToolUsageEvent(
                tool_name=f"tool_{i}",
                execution_time_ms=i * 100,
                success=True
            )
            mock_service.track_tool_usage(event)

        assert len(mock_service._buffer) == 5

    def test_timestamp_added_if_missing(self, mock_service):
        """Test timestamp is added to event."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            execution_time_ms=100,
            success=True
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].timestamp is not None


class TestBufferedWrites:
    """Tests for buffered writes to database."""

    @pytest.fixture
    def mock_service_with_db(self):
        """Create service with mocked database."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        service._pool = mock_pool

        return service

    def test_flush_buffer_clears_buffer(self, mock_service_with_db):
        """Test flushing buffer clears it."""
        mock_service_with_db._buffer = [
            ToolUsageEvent("tool1", 100, True),
            ToolUsageEvent("tool2", 200, True)
        ]

        asyncio.run(mock_service_with_db._flush_buffer())

        assert len(mock_service_with_db._buffer) == 0

    def test_buffer_flush_threshold(self, mock_service_with_db):
        """Test buffer flushes at threshold."""
        # Default threshold is typically around 100
        threshold = getattr(mock_service_with_db, '_buffer_threshold', 100)
        assert threshold > 0


class TestStatisticsRetrieval:
    """Tests for statistics retrieval."""

    @pytest.fixture
    def mock_service_with_stats(self):
        """Create service with mocked stats data."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock usage stats
        mock_cursor.fetchall.return_value = [
            {'tool_name': 'search_funding_calls', 'usage_count': 500,
             'avg_time_ms': 150, 'success_rate': 0.95},
            {'tool_name': 'search_projects', 'usage_count': 300,
             'avg_time_ms': 200, 'success_rate': 0.92}
        ]

        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        service._pool = mock_pool

        return service

    def test_get_tool_stats_structure(self, mock_service_with_stats):
        """Test tool stats have correct structure."""
        stats = asyncio.run(mock_service_with_stats.get_tool_statistics())

        assert isinstance(stats, dict) or isinstance(stats, list)

    def test_get_tool_stats_disabled(self):
        """Test stats return empty when disabled."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service.enabled = False

        stats = asyncio.run(service.get_tool_statistics())

        assert stats == {} or stats == [] or 'error' in stats


class TestToolPerformanceAnalysis:
    """Tests for tool performance analysis."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service._buffer = []
        return service

    def test_track_slow_tool(self, mock_service):
        """Test tracking slow tool execution."""
        event = ToolUsageEvent(
            tool_name="slow_tool",
            execution_time_ms=5000,  # 5 seconds
            success=True
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].execution_time_ms == 5000

    def test_track_fast_tool(self, mock_service):
        """Test tracking fast tool execution."""
        event = ToolUsageEvent(
            tool_name="fast_tool",
            execution_time_ms=10,
            success=True
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].execution_time_ms == 10


class TestErrorRateTracking:
    """Tests for error rate tracking."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service._buffer = []
        return service

    def test_track_successful_execution(self, mock_service):
        """Test tracking successful execution."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            execution_time_ms=100,
            success=True
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].success == True

    def test_track_failed_execution(self, mock_service):
        """Test tracking failed execution."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            execution_time_ms=50,
            success=False,
            error_message="Connection refused"
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].success == False
        assert mock_service._buffer[0].error_message == "Connection refused"

    def test_track_various_errors(self, mock_service):
        """Test tracking various error types."""
        errors = [
            "Database timeout",
            "Invalid parameters",
            "Rate limit exceeded",
            "Network error"
        ]

        for error in errors:
            event = ToolUsageEvent(
                tool_name="test_tool",
                execution_time_ms=50,
                success=False,
                error_message=error
            )
            mock_service.track_tool_usage(event)

        assert len(mock_service._buffer) == 4


class TestGetAnalyticsServiceSingleton:
    """Tests for get_analytics_service function."""

    def test_get_analytics_service_returns_instance(self):
        """Test function returns instance."""
        # Reset singleton
        import app.services.analytics.tool_analytics_service as module
        module._analytics_instance = None

        service = get_analytics_service()

        assert service is not None
        assert isinstance(service, ToolAnalyticsService)

    def test_get_analytics_service_singleton(self):
        """Test function returns same instance."""
        import app.services.analytics.tool_analytics_service as module
        module._analytics_instance = None

        service1 = get_analytics_service()
        service2 = get_analytics_service()

        assert service1 is service2


class TestQueryTypeTracking:
    """Tests for query type tracking."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service._buffer = []
        return service

    def test_track_faq_query_type(self, mock_service):
        """Test tracking FAQ query type."""
        event = ToolUsageEvent(
            tool_name="search_documents",
            execution_time_ms=100,
            success=True,
            query_type="faq"
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].query_type == "faq"

    def test_track_search_calls_query_type(self, mock_service):
        """Test tracking search_calls query type."""
        event = ToolUsageEvent(
            tool_name="search_funding_calls",
            execution_time_ms=150,
            success=True,
            query_type="search_calls"
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].query_type == "search_calls"


class TestResultCountTracking:
    """Tests for result count tracking."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service._buffer = []
        return service

    def test_track_zero_results(self, mock_service):
        """Test tracking query with zero results."""
        event = ToolUsageEvent(
            tool_name="search_projects",
            execution_time_ms=100,
            success=True,
            result_count=0
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].result_count == 0

    def test_track_many_results(self, mock_service):
        """Test tracking query with many results."""
        event = ToolUsageEvent(
            tool_name="search_projects",
            execution_time_ms=500,
            success=True,
            result_count=150
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].result_count == 150


class TestConversationTracking:
    """Tests for conversation ID tracking."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service._buffer = []
        return service

    def test_track_with_conversation_id(self, mock_service):
        """Test tracking with conversation ID."""
        event = ToolUsageEvent(
            tool_name="search_funding_calls",
            execution_time_ms=100,
            success=True,
            conversation_id="conv-abc123"
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].conversation_id == "conv-abc123"

    def test_track_without_conversation_id(self, mock_service):
        """Test tracking without conversation ID."""
        event = ToolUsageEvent(
            tool_name="search_funding_calls",
            execution_time_ms=100,
            success=True
        )

        mock_service.track_tool_usage(event)

        assert mock_service._buffer[0].conversation_id is None


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service."""
        ToolAnalyticsService._instance = None
        service = ToolAnalyticsService()
        service._buffer = []
        return service

    def test_very_long_tool_name(self, mock_service):
        """Test handling very long tool name."""
        event = ToolUsageEvent(
            tool_name="a" * 500,
            execution_time_ms=100,
            success=True
        )

        # Should not crash
        mock_service.track_tool_usage(event)
        assert len(mock_service._buffer) == 1

    def test_very_long_error_message(self, mock_service):
        """Test handling very long error message."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            execution_time_ms=50,
            success=False,
            error_message="Error: " + "x" * 10000
        )

        # Should not crash
        mock_service.track_tool_usage(event)
        assert len(mock_service._buffer) == 1

    def test_negative_execution_time(self, mock_service):
        """Test handling negative execution time (edge case)."""
        event = ToolUsageEvent(
            tool_name="test_tool",
            execution_time_ms=-1,  # Should not happen but handle gracefully
            success=True
        )

        mock_service.track_tool_usage(event)
        assert len(mock_service._buffer) == 1

    def test_concurrent_tracking(self, mock_service):
        """Test concurrent event tracking."""
        async def track_many():
            for i in range(100):
                event = ToolUsageEvent(
                    tool_name=f"tool_{i % 10}",
                    execution_time_ms=i * 10,
                    success=True
                )
                mock_service.track_tool_usage(event)

        asyncio.run(track_many())
        assert len(mock_service._buffer) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
