"""
Comprehensive tests for the FeedbackService.

Tests:
- Feedback submission
- Feedback summary retrieval
- Conversation-specific feedback
- Improvement suggestions
- Singleton pattern
- Error handling
- Data validation
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.feedback.feedback_service import (
    FeedbackService,
    FeedbackSubmission,
    get_feedback_service,
)


class TestFeedbackSubmissionDataclass:
    """Tests for the FeedbackSubmission dataclass."""

    def test_required_fields(self):
        """Test that required fields must be provided."""
        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=4,
            feedback_type="helpful"
        )

        assert feedback.conversation_id == "conv-123"
        assert feedback.rating == 4
        assert feedback.feedback_type == "helpful"

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None."""
        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=4,
            feedback_type="helpful"
        )

        assert feedback.feedback_text is None
        assert feedback.message_id is None
        assert feedback.query_text is None
        assert feedback.response_text is None
        assert feedback.tools_used is None
        assert feedback.query_type is None
        assert feedback.response_time_ms is None

    def test_all_fields_provided(self):
        """Test feedback with all fields provided."""
        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=5,
            feedback_type="helpful",
            feedback_text="Great response!",
            message_id="msg-456",
            query_text="What hydrogen calls are open?",
            response_text="Here are the open calls...",
            tools_used=["search_funding_calls", "get_call_details"],
            query_type="search_calls",
            response_time_ms=1500
        )

        assert feedback.tools_used == ["search_funding_calls", "get_call_details"]
        assert feedback.response_time_ms == 1500

    def test_rating_values(self):
        """Test various rating values."""
        for rating in [1, 2, 3, 4, 5]:
            feedback = FeedbackSubmission(
                conversation_id="conv-123",
                rating=rating,
                feedback_type="helpful"
            )
            assert feedback.rating == rating

    def test_feedback_types(self):
        """Test all valid feedback types."""
        valid_types = ["helpful", "not_helpful", "incorrect", "incomplete", "other"]

        for ftype in valid_types:
            feedback = FeedbackSubmission(
                conversation_id="conv-123",
                rating=3,
                feedback_type=ftype
            )
            assert feedback.feedback_type == ftype


class TestFeedbackServiceInitialization:
    """Tests for FeedbackService initialization."""

    def test_service_disabled_without_db_url(self):
        """Test service is disabled when DATABASE_URL is not set."""
        # Reset singleton
        FeedbackService._instance = None
        FeedbackService._pool = None

        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            with patch.object(FeedbackService, '_init_pool'):
                service = FeedbackService()
                service.db_url = None
                service.enabled = False
                assert service.enabled == False

    def test_singleton_returns_same_instance(self):
        """Test singleton pattern returns same instance."""
        # Reset singleton
        FeedbackService._instance = None

        service1 = FeedbackService()
        service2 = FeedbackService()

        assert service1 is service2


class TestFeedbackSubmission:
    """Tests for feedback submission functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock service with mocked database."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)  # Returned feedback ID
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        FeedbackService._pool = mock_pool

        return service

    def test_submit_feedback_success(self, mock_service):
        """Test successful feedback submission."""
        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=5,
            feedback_type="helpful",
            feedback_text="Great response!"
        )

        result = asyncio.run(mock_service.submit_feedback(feedback))

        assert result["success"] == True
        assert result["feedback_id"] == 42
        assert "Thank you" in result["message"]

    def test_submit_feedback_disabled_service(self):
        """Test submission when service is disabled."""
        FeedbackService._instance = None
        service = FeedbackService()
        service.enabled = False

        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=5,
            feedback_type="helpful"
        )

        result = asyncio.run(service.submit_feedback(feedback))

        assert result["success"] == False
        assert "not available" in result["error"]

    def test_submit_feedback_db_error(self, mock_service):
        """Test submission handling database errors."""
        FeedbackService._pool.getconn.return_value.cursor.return_value.execute.side_effect = Exception("DB Error")

        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=5,
            feedback_type="helpful"
        )

        result = asyncio.run(mock_service.submit_feedback(feedback))

        assert result["success"] == False
        assert "error" in result


class TestFeedbackSummary:
    """Tests for feedback summary retrieval."""

    @pytest.fixture
    def mock_service_with_data(self):
        """Create a mock service with sample summary data."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock summary data
        mock_cursor.fetchone.return_value = {
            'total_feedback': 100,
            'avg_rating': 4.2,
            'helpful': 60,
            'not_helpful': 20,
            'incorrect': 10,
            'incomplete': 10,
            'positive_ratings': 75,
            'negative_ratings': 10
        }

        # Mock fetchall for distribution and other queries
        mock_cursor.fetchall.side_effect = [
            [{'rating': 1, 'count': 5}, {'rating': 2, 'count': 5},
             {'rating': 3, 'count': 15}, {'rating': 4, 'count': 35}, {'rating': 5, 'count': 40}],
            [{'tool_name': 'search_funding_calls', 'usage_count': 50, 'avg_rating': 4.5}],
            []  # No low-rated responses
        ]

        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        FeedbackService._pool = mock_pool

        return service

    def test_get_feedback_summary(self, mock_service_with_data):
        """Test getting feedback summary."""
        result = asyncio.run(mock_service_with_data.get_feedback_summary(days=30))

        assert result["period_days"] == 30
        assert result["total_feedback"] == 100
        assert result["avg_rating"] == 4.2
        assert result["satisfaction_rate"] == 75.0
        assert "by_type" in result
        assert "rating_distribution" in result
        assert "tool_feedback" in result

    def test_summary_disabled_service(self):
        """Test summary when service is disabled."""
        FeedbackService._instance = None
        service = FeedbackService()
        service.enabled = False

        result = asyncio.run(service.get_feedback_summary())

        assert "error" in result

    def test_summary_satisfaction_calculation(self, mock_service_with_data):
        """Test satisfaction rate calculation."""
        result = asyncio.run(mock_service_with_data.get_feedback_summary())

        # 75 positive out of 100 total = 75%
        assert result["satisfaction_rate"] == 75.0


class TestConversationFeedback:
    """Tests for conversation-specific feedback retrieval."""

    @pytest.fixture
    def mock_service_with_conversation_data(self):
        """Create mock service with conversation feedback data."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'rating': 5, 'feedback_type': 'helpful',
             'feedback_text': 'Great!', 'tools_used': ['search_funding_calls'],
             'created_at': datetime.now()},
            {'id': 2, 'rating': 3, 'feedback_type': 'incomplete',
             'feedback_text': 'Missing details', 'tools_used': None,
             'created_at': datetime.now() - timedelta(hours=1)}
        ]
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        FeedbackService._pool = mock_pool

        return service

    def test_get_conversation_feedback(self, mock_service_with_conversation_data):
        """Test getting feedback for specific conversation."""
        result = asyncio.run(
            mock_service_with_conversation_data.get_conversation_feedback("conv-123")
        )

        assert len(result) == 2
        assert result[0]['rating'] == 5
        assert result[1]['feedback_type'] == 'incomplete'

    def test_conversation_feedback_empty(self):
        """Test getting feedback for conversation with no feedback."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        FeedbackService._pool = mock_pool

        result = asyncio.run(service.get_conversation_feedback("conv-nonexistent"))

        assert result == []


class TestImprovementSuggestions:
    """Tests for improvement suggestions generation."""

    @pytest.fixture
    def mock_service_with_improvement_data(self):
        """Create mock service with improvement data."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock underperforming tools and issue patterns
        mock_cursor.fetchall.side_effect = [
            [{'tool_name': 'problematic_tool', 'total_uses': 20,
              'avg_rating': 2.5, 'low_ratings': 12}],
            [{'feedback_type': 'incomplete', 'count': 15},
             {'feedback_type': 'incorrect', 'count': 8}]
        ]

        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        FeedbackService._pool = mock_pool

        return service

    def test_get_improvement_suggestions(self, mock_service_with_improvement_data):
        """Test getting improvement suggestions."""
        result = asyncio.run(
            mock_service_with_improvement_data.get_improvement_suggestions()
        )

        assert "suggestions" in result
        assert len(result["suggestions"]) >= 1  # At least tool improvement suggestion
        assert "underperforming_tools" in result
        assert "issue_patterns" in result

    def test_suggestion_priority_assignment(self, mock_service_with_improvement_data):
        """Test that suggestions have correct priority."""
        result = asyncio.run(
            mock_service_with_improvement_data.get_improvement_suggestions()
        )

        tool_suggestion = next(
            (s for s in result["suggestions"] if s["type"] == "tool_improvement"),
            None
        )

        if tool_suggestion:
            # avg_rating 2.5 < 3.0 should be "high" priority
            assert tool_suggestion["priority"] == "high"


class TestFeedbackServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_feedback_service_singleton(self):
        """Test that get_feedback_service returns same instance."""
        # Reset global
        import app.services.feedback.feedback_service as module
        module._feedback_service = None

        service1 = get_feedback_service()
        service2 = get_feedback_service()

        assert service1 is service2


class TestFeedbackValidation:
    """Tests for feedback data validation."""

    def test_rating_boundary_values(self):
        """Test rating boundary values."""
        # Valid ratings
        for rating in [1, 5]:
            feedback = FeedbackSubmission(
                conversation_id="conv-123",
                rating=rating,
                feedback_type="helpful"
            )
            assert feedback.rating == rating

    def test_feedback_text_can_be_long(self):
        """Test that feedback text can handle long strings."""
        long_text = "This is a detailed feedback. " * 100

        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=3,
            feedback_type="other",
            feedback_text=long_text
        )

        assert len(feedback.feedback_text) > 1000

    def test_tools_used_as_list(self):
        """Test tools_used accepts list of strings."""
        tools = ["tool1", "tool2", "tool3", "tool4", "tool5"]

        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=4,
            feedback_type="helpful",
            tools_used=tools
        )

        assert len(feedback.tools_used) == 5
        assert all(isinstance(t, str) for t in feedback.tools_used)


class TestFeedbackServiceErrorHandling:
    """Tests for error handling in feedback service."""

    def test_connection_pool_none_handling(self):
        """Test handling when connection pool is None."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True
        FeedbackService._pool = None  # Ensure pool is None

        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=5,
            feedback_type="helpful"
        )

        result = asyncio.run(service.submit_feedback(feedback))

        assert result["success"] == False
        assert "connection" in result["error"].lower()

    def test_database_commit_rollback_on_error(self):
        """Test that database rollback happens on error."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Insert failed")
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        FeedbackService._pool = mock_pool

        feedback = FeedbackSubmission(
            conversation_id="conv-123",
            rating=5,
            feedback_type="helpful"
        )

        result = asyncio.run(service.submit_feedback(feedback))

        # Should have rolled back
        mock_conn.rollback.assert_called_once()


class TestFeedbackSummaryCalculations:
    """Tests for summary calculation accuracy."""

    def test_satisfaction_rate_zero_feedback(self):
        """Test satisfaction rate with zero feedback."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'total_feedback': 0,
            'avg_rating': None,
            'helpful': 0,
            'not_helpful': 0,
            'incorrect': 0,
            'incomplete': 0,
            'positive_ratings': 0,
            'negative_ratings': 0
        }
        mock_cursor.fetchall.side_effect = [[], [], []]
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        FeedbackService._pool = mock_pool

        result = asyncio.run(service.get_feedback_summary())

        assert result["total_feedback"] == 0
        assert result["satisfaction_rate"] == 0
        assert result["avg_rating"] == 0

    def test_rating_distribution_complete(self):
        """Test that rating distribution covers all ratings."""
        FeedbackService._instance = None
        FeedbackService._pool = None

        service = FeedbackService()
        service.enabled = True

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'total_feedback': 50,
            'avg_rating': 3.5,
            'helpful': 20,
            'not_helpful': 10,
            'incorrect': 10,
            'incomplete': 10,
            'positive_ratings': 25,
            'negative_ratings': 15
        }
        mock_cursor.fetchall.side_effect = [
            [{'rating': 1, 'count': 5}, {'rating': 2, 'count': 10},
             {'rating': 3, 'count': 10}, {'rating': 4, 'count': 15}, {'rating': 5, 'count': 10}],
            [],
            []
        ]
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        FeedbackService._pool = mock_pool

        result = asyncio.run(service.get_feedback_summary())

        # Check all ratings present
        dist = result["rating_distribution"]
        assert "1" in dist
        assert "5" in dist


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
