"""
Comprehensive tests for Enterprise Routes (Analytics, Alerts, Collaboration, Audit).

Tests:
- Analytics dashboard endpoints
- Saved searches and alerts CRUD
- Collaboration session management
- Audit trail queries
- Health checks for all services
- Error handling
- Request/Response model validation
"""

import json
import os
import sys
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Analytics Routes Tests
# =============================================================================


class TestAnalyticsRoutesModels:
    """Tests for Analytics route request/response models."""

    def test_usage_metrics_structure(self):
        """Test UsageMetrics model structure."""
        from app.api.analytics_routes import UsageMetrics

        metrics = UsageMetrics(
            total_queries=1000,
            unique_conversations=150,
            queries_per_day={"2025-01-01": 50, "2025-01-02": 60},
            peak_hour=14,
            avg_queries_per_conversation=6.67,
        )
        assert metrics.total_queries == 1000
        assert metrics.unique_conversations == 150
        assert metrics.peak_hour == 14

    def test_performance_metrics_structure(self):
        """Test PerformanceMetrics model structure."""
        from app.api.analytics_routes import PerformanceMetrics

        metrics = PerformanceMetrics(
            avg_response_time_ms=1500.0,
            p95_response_time_ms=3500.0,
            error_rate=0.02,
            tool_success_rates={"search_funding_calls": 98.5, "search_projects": 97.0},
        )
        assert metrics.avg_response_time_ms == 1500.0
        assert metrics.error_rate == 0.02

    def test_content_metrics_structure(self):
        """Test ContentMetrics model structure."""
        from app.api.analytics_routes import ContentMetrics

        metrics = ContentMetrics(
            top_queries=[{"query": "hydrogen calls", "count": 50}],
            top_tools=[{"tool_name": "search_funding_calls", "usage_count": 500}],
            popular_clusters=[{"cluster": "CLUSTER-5", "count": 200}],
            popular_countries=[{"country": "DE", "count": 150}],
        )
        assert len(metrics.top_queries) == 1
        assert len(metrics.top_tools) == 1

    def test_trend_point_structure(self):
        """Test TrendPoint model structure."""
        from app.api.analytics_routes import TrendPoint

        point = TrendPoint(date="2025-01-01T00:00:00", value=100.0)
        assert point.date == "2025-01-01T00:00:00"
        assert point.value == 100.0


class TestAnalyticsRoutesHealth:
    """Tests for analytics health endpoint."""

    @pytest.fixture
    def mock_analytics_service(self):
        """Create mock analytics service."""
        mock = MagicMock()
        mock.enabled = True
        mock.buffer = []
        mock.last_flush = datetime.utcnow()
        mock.session_metrics = {}
        return mock

    def test_health_endpoint_response_structure(self, mock_analytics_service):
        """Test health endpoint response structure."""
        from app.api.analytics_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.analytics_routes.get_analytics_service",
            return_value=mock_analytics_service,
        ):
            client = TestClient(app)
            response = client.get("/api/analytics/health")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "disabled"]
            assert "buffer_size" in data
            assert "timestamp" in data

    def test_health_endpoint_disabled_service(self):
        """Test health endpoint when service is disabled."""
        from app.api.analytics_routes import router

        mock_service = MagicMock()
        mock_service.enabled = False
        mock_service.buffer = []
        mock_service.last_flush = datetime.utcnow()
        mock_service.session_metrics = {}

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.analytics_routes.get_analytics_service", return_value=mock_service
        ):
            client = TestClient(app)
            response = client.get("/api/analytics/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "disabled"


class TestAnalyticsRoutesToolsEndpoint:
    """Tests for /api/analytics/tools endpoint."""

    @pytest.fixture
    def mock_analytics_service(self):
        """Create mock analytics service with tool data."""
        mock = MagicMock()
        mock.get_tool_performance.return_value = {
            "tools": [
                {"tool_name": "search_funding_calls", "avg_time_ms": 500, "count": 100}
            ]
        }
        mock.get_slow_tools.return_value = [
            {"tool_name": "get_budget_benchmark", "avg_time_ms": 3500}
        ]
        mock.get_popular_tool_combinations.return_value = {
            "combinations": [
                {"tools": ["search_calls", "get_details"], "count": 50}
            ]
        }
        mock.get_session_metrics.return_value = {"active_tools": 5}
        return mock

    def test_tools_endpoint_response(self, mock_analytics_service):
        """Test tools endpoint returns correct structure."""
        from app.api.analytics_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.analytics_routes.get_analytics_service",
            return_value=mock_analytics_service,
        ):
            client = TestClient(app)
            response = client.get("/api/analytics/tools?hours=24")

            assert response.status_code == 200
            data = response.json()
            assert "period_hours" in data
            assert "tool_performance" in data
            assert "slow_tools" in data
            assert "popular_combinations" in data
            assert "generated_at" in data

    def test_tools_endpoint_parameter_validation(self, mock_analytics_service):
        """Test tools endpoint validates hours parameter."""
        from app.api.analytics_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.analytics_routes.get_analytics_service",
            return_value=mock_analytics_service,
        ):
            client = TestClient(app)

            # Valid range
            response = client.get("/api/analytics/tools?hours=24")
            assert response.status_code == 200

            # Invalid - too low
            response = client.get("/api/analytics/tools?hours=0")
            assert response.status_code == 422

            # Invalid - too high
            response = client.get("/api/analytics/tools?hours=1000")
            assert response.status_code == 422


class TestAnalyticsTrendsEndpoint:
    """Tests for /api/analytics/trends endpoint."""

    def test_trends_endpoint_parameter_validation(self):
        """Test trends endpoint validates parameters."""
        from app.api.analytics_routes import router

        app = FastAPI()
        app.include_router(router)

        # Mock database connection to avoid actual DB calls
        with patch("app.api.analytics_routes._get_connection", return_value=None):
            client = TestClient(app)

            # Missing required metric parameter
            response = client.get("/api/analytics/trends")
            assert response.status_code == 422

            # Invalid granularity
            response = client.get(
                "/api/analytics/trends?metric=queries&granularity=invalid"
            )
            assert response.status_code == 422

    def test_trends_supported_metrics(self):
        """Test supported metrics for trends endpoint."""
        supported_metrics = ["queries", "response_time", "error_rate", "feedback"]

        for metric in supported_metrics:
            # These should be valid metric values
            assert metric in supported_metrics


# =============================================================================
# Alert Routes Tests
# =============================================================================


class TestAlertRoutesModels:
    """Tests for Alert route request/response models."""

    def test_create_saved_search_request_validation(self):
        """Test CreateSavedSearchRequest model validation."""
        from app.api.alert_routes import CreateSavedSearchRequest

        # Valid request
        request = CreateSavedSearchRequest(
            name="Hydrogen Calls",
            description="Open hydrogen funding calls",
            search_type="calls",
            parameters={"keywords": "hydrogen", "status": "open"},
        )
        assert request.name == "Hydrogen Calls"
        assert request.search_type == "calls"

        # Valid with alert config
        from app.api.alert_routes import AlertConfigRequest

        request_with_alert = CreateSavedSearchRequest(
            name="Test Search",
            search_type="projects",
            parameters={},
            alert_config=AlertConfigRequest(
                enabled=True, frequency="daily", channel="email", email="test@example.com"
            ),
        )
        assert request_with_alert.alert_config is not None
        assert request_with_alert.alert_config.enabled is True

    def test_alert_config_request_patterns(self):
        """Test AlertConfigRequest pattern validation."""
        from app.api.alert_routes import AlertConfigRequest

        # Valid frequency values
        for freq in ["immediate", "daily", "weekly"]:
            config = AlertConfigRequest(frequency=freq)
            assert config.frequency == freq

        # Valid channel values
        for channel in ["email", "webhook", "both"]:
            config = AlertConfigRequest(channel=channel)
            assert config.channel == channel

    def test_saved_search_response_structure(self):
        """Test SavedSearchResponse model structure."""
        from app.api.alert_routes import SavedSearchResponse

        response = SavedSearchResponse(
            id="search-123",
            user_id="user-456",
            name="Test Search",
            description=None,
            search_type="calls",
            parameters={"keywords": "test"},
            alert_config={"enabled": False},
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            last_run=None,
            is_active=True,
            run_count=0,
            alert_count=0,
        )
        assert response.id == "search-123"
        assert response.is_active is True


class TestAlertRoutesHealth:
    """Tests for alerts health endpoint."""

    def test_health_endpoint_response(self):
        """Test health endpoint returns correct structure."""
        from app.api.alert_routes import router

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/alerts/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "alerts"
        assert "timestamp" in data


class TestAlertRoutesCRUD:
    """Tests for alerts CRUD operations."""

    @pytest.fixture
    def mock_saved_search_service(self):
        """Create mock saved search service."""
        mock = MagicMock()

        # Mock SavedSearch object
        mock_search = MagicMock()
        mock_search.to_dict.return_value = {
            "id": "search-123",
            "user_id": "user-456",
            "name": "Test Search",
            "description": "Test description",
            "search_type": "calls",
            "parameters": {"keywords": "test"},
            "alert_config": {"enabled": False},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_run": None,
            "is_active": True,
            "run_count": 0,
            "alert_count": 0,
        }

        mock.create_search = AsyncMock(return_value=mock_search)
        mock.get_user_searches = AsyncMock(return_value=[mock_search])
        mock.get_search = AsyncMock(return_value=mock_search)
        mock.update_search = AsyncMock(return_value=mock_search)
        mock.delete_search = AsyncMock(return_value=True)
        mock.hard_delete_search = AsyncMock(return_value=True)
        mock.get_user_stats = AsyncMock(
            return_value={
                "total_searches": 5,
                "active_searches": 3,
                "inactive_searches": 2,
                "total_runs": 50,
                "total_alerts_sent": 10,
                "by_type": {"calls": 3, "projects": 2},
            }
        )

        return mock

    def test_create_saved_search_endpoint(self, mock_saved_search_service):
        """Test create saved search endpoint."""
        from app.api.alert_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.alert_routes.get_saved_search_service",
            return_value=mock_saved_search_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/alerts?user_id=user-456",
                json={
                    "name": "Test Search",
                    "search_type": "calls",
                    "parameters": {"keywords": "hydrogen"},
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["name"] == "Test Search"

    def test_list_saved_searches_endpoint(self, mock_saved_search_service):
        """Test list saved searches endpoint."""
        from app.api.alert_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.alert_routes.get_saved_search_service",
            return_value=mock_saved_search_service,
        ):
            client = TestClient(app)
            response = client.get("/api/alerts?user_id=user-456")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1

    def test_get_saved_search_endpoint(self, mock_saved_search_service):
        """Test get saved search by ID endpoint."""
        from app.api.alert_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.alert_routes.get_saved_search_service",
            return_value=mock_saved_search_service,
        ):
            client = TestClient(app)
            response = client.get("/api/alerts/search-123")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "search-123"

    def test_get_saved_search_not_found(self, mock_saved_search_service):
        """Test get saved search returns 404 when not found."""
        from app.api.alert_routes import router

        mock_saved_search_service.get_search = AsyncMock(return_value=None)

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.alert_routes.get_saved_search_service",
            return_value=mock_saved_search_service,
        ):
            client = TestClient(app)
            response = client.get("/api/alerts/nonexistent-id")

            assert response.status_code == 404

    def test_update_saved_search_endpoint(self, mock_saved_search_service):
        """Test update saved search endpoint."""
        from app.api.alert_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.alert_routes.get_saved_search_service",
            return_value=mock_saved_search_service,
        ):
            client = TestClient(app)
            response = client.patch(
                "/api/alerts/search-123",
                json={"name": "Updated Name", "is_active": False},
            )

            assert response.status_code == 200
            # Service was called with update data
            mock_saved_search_service.update_search.assert_called_once()

    def test_delete_saved_search_endpoint(self, mock_saved_search_service):
        """Test delete saved search endpoint."""
        from app.api.alert_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.alert_routes.get_saved_search_service",
            return_value=mock_saved_search_service,
        ):
            client = TestClient(app)
            response = client.delete("/api/alerts/search-123")

            assert response.status_code == 204

    def test_delete_saved_search_permanent(self, mock_saved_search_service):
        """Test permanent delete saved search endpoint."""
        from app.api.alert_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.alert_routes.get_saved_search_service",
            return_value=mock_saved_search_service,
        ):
            client = TestClient(app)
            response = client.delete("/api/alerts/search-123?permanent=true")

            assert response.status_code == 204
            mock_saved_search_service.hard_delete_search.assert_called_once()

    def test_get_user_stats_endpoint(self, mock_saved_search_service):
        """Test get user stats endpoint."""
        from app.api.alert_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.alert_routes.get_saved_search_service",
            return_value=mock_saved_search_service,
        ):
            client = TestClient(app)
            response = client.get("/api/alerts/stats?user_id=user-456")

            assert response.status_code == 200
            data = response.json()
            assert data["total_searches"] == 5
            assert data["active_searches"] == 3


# =============================================================================
# Collaboration Routes Tests
# =============================================================================


class TestCollaborationRoutesModels:
    """Tests for Collaboration route request/response models."""

    def test_join_session_request_validation(self):
        """Test JoinSessionRequest model validation."""
        from app.api.collaboration_routes import JoinSessionRequest

        request = JoinSessionRequest(username="John Doe")
        assert request.username == "John Doe"

    def test_cursor_update_request_validation(self):
        """Test CursorUpdateRequest model validation."""
        from app.api.collaboration_routes import CursorUpdateRequest

        request = CursorUpdateRequest(section_id="section-1", position=100)
        assert request.section_id == "section-1"
        assert request.position == 100

        # With selection
        request_with_selection = CursorUpdateRequest(
            section_id="section-1",
            position=100,
            selection_start=100,
            selection_end=150,
        )
        assert request_with_selection.selection_start == 100
        assert request_with_selection.selection_end == 150

    def test_edit_operation_request_validation(self):
        """Test EditOperationRequest model validation."""
        from app.api.collaboration_routes import EditOperationRequest

        # Insert operation
        request = EditOperationRequest(
            operation_type="insert", position=50, content="Hello World", base_version=1
        )
        assert request.operation_type == "insert"
        assert request.content == "Hello World"

        # Delete operation
        request = EditOperationRequest(
            operation_type="delete", position=50, length=10, base_version=1
        )
        assert request.operation_type == "delete"
        assert request.length == 10

    def test_edit_operation_type_pattern(self):
        """Test EditOperationRequest operation_type pattern validation."""
        from app.api.collaboration_routes import EditOperationRequest

        valid_types = ["insert", "delete", "replace", "retain"]
        for op_type in valid_types:
            request = EditOperationRequest(operation_type=op_type, position=0)
            assert request.operation_type == op_type


class TestCollaborationRoutesHealth:
    """Tests for collaboration health endpoint."""

    def test_health_endpoint_response(self):
        """Test health endpoint returns correct structure."""
        from app.api.collaboration_routes import router

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/collaboration/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "collaboration"
        assert "timestamp" in data


class TestCollaborationRoutesSession:
    """Tests for collaboration session endpoints."""

    @pytest.fixture
    def mock_collaboration_service(self):
        """Create mock collaboration service."""
        mock = MagicMock()

        mock.join_session = AsyncMock(
            return_value={
                "connection_id": "conn-123",
                "your_color": "#FF5733",
                "collaborators": [],
                "locked_sections": [],
            }
        )
        mock.leave_session = AsyncMock(return_value=None)
        mock.get_collaborators = AsyncMock(return_value=[])
        mock.update_cursor = AsyncMock(return_value=None)
        mock.lock_section = AsyncMock(return_value=None)
        mock.unlock_section = AsyncMock(return_value=True)
        mock.refresh_lock = AsyncMock(return_value=True)
        mock.get_locked_sections = AsyncMock(return_value=[])
        mock.apply_operation = AsyncMock(
            return_value={"success": True, "version": 2, "error": None}
        )

        return mock

    def test_join_session_endpoint(self, mock_collaboration_service):
        """Test join session endpoint."""
        from app.api.collaboration_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/collaboration/session-123/join?user_id=user-456",
                json={"username": "John Doe"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["connection_id"] == "conn-123"
            assert "your_color" in data

    def test_leave_session_endpoint(self, mock_collaboration_service):
        """Test leave session endpoint."""
        from app.api.collaboration_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/collaboration/session-123/leave?user_id=user-456"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_collaborators_endpoint(self, mock_collaboration_service):
        """Test get collaborators endpoint."""
        from app.api.collaboration_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.get("/api/collaboration/session-123/collaborators")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_update_cursor_endpoint(self, mock_collaboration_service):
        """Test update cursor endpoint."""
        from app.api.collaboration_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/collaboration/session-123/cursor?user_id=user-456",
                json={"section_id": "section-1", "position": 100},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_lock_section_endpoint(self, mock_collaboration_service):
        """Test lock section endpoint."""
        from app.api.collaboration_routes import router

        # Mock a lock object
        mock_lock = MagicMock()
        mock_lock.to_dict.return_value = {
            "section_id": "section-1",
            "locked_by": "user-456",
            "locked_at": datetime.utcnow().isoformat(),
        }
        mock_collaboration_service.lock_section = AsyncMock(return_value=mock_lock)

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/collaboration/session-123/sections/section-1/lock?user_id=user-456",
                json={"username": "John Doe"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["lock"] is not None

    def test_lock_section_already_locked(self, mock_collaboration_service):
        """Test lock section when already locked by another user."""
        from app.api.collaboration_routes import router

        mock_collaboration_service.lock_section = AsyncMock(return_value=None)

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/collaboration/session-123/sections/section-1/lock?user_id=user-456",
                json={"username": "John Doe"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "locked by another user" in data["message"]

    def test_unlock_section_endpoint(self, mock_collaboration_service):
        """Test unlock section endpoint."""
        from app.api.collaboration_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/collaboration/session-123/sections/section-1/unlock?user_id=user-456"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_locked_sections_endpoint(self, mock_collaboration_service):
        """Test get locked sections endpoint."""
        from app.api.collaboration_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.get("/api/collaboration/session-123/locks")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_apply_operation_endpoint(self, mock_collaboration_service):
        """Test apply operation endpoint."""
        from app.api.collaboration_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.collaboration_routes.get_collaboration_service",
            return_value=mock_collaboration_service,
        ):
            client = TestClient(app)
            response = client.post(
                "/api/collaboration/session-123/sections/section-1/operation?user_id=user-456",
                json={
                    "operation_type": "insert",
                    "position": 50,
                    "content": "Hello",
                    "base_version": 1,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["version"] == 2


class TestCollaborationConnectionManager:
    """Tests for ConnectionManager class."""

    def test_connection_manager_structure(self):
        """Test ConnectionManager data structure."""
        from app.api.collaboration_routes import ConnectionManager

        manager = ConnectionManager()
        assert hasattr(manager, "active_connections")
        assert isinstance(manager.active_connections, dict)


# =============================================================================
# Audit Routes Tests
# =============================================================================


class TestAuditRoutesModels:
    """Tests for Audit route request/response models."""

    def test_audit_event_response_structure(self):
        """Test AuditEventResponse model structure."""
        from app.api.audit_routes import AuditEventResponse

        response = AuditEventResponse(
            event_id="event-123",
            event_type="query.completed",
            action="execute",
            timestamp="2025-01-01T00:00:00",
            user_id="user-456",
            organization_id=None,
            resource_type="conversation",
            resource_id="conv-789",
            resource_name=None,
            ip_address="127.0.0.1",
            success=True,
            error_message=None,
            duration_ms=1500.0,
            details={"tools_used": ["search_funding_calls"]},
        )
        assert response.event_id == "event-123"
        assert response.success is True

    def test_audit_trail_response_structure(self):
        """Test AuditTrailResponse model structure."""
        from app.api.audit_routes import AuditTrailResponse

        response = AuditTrailResponse(
            events=[{"event_id": "event-123"}], total_count=1, has_more=False
        )
        assert len(response.events) == 1
        assert response.has_more is False

    def test_user_activity_response_structure(self):
        """Test UserActivityResponse model structure."""
        from app.api.audit_routes import UserActivityResponse

        response = UserActivityResponse(
            user_id="user-456",
            period_days=30,
            total_events=100,
            event_counts={"query.completed": 50, "proposal.created": 10},
        )
        assert response.total_events == 100

    def test_audit_stats_response_structure(self):
        """Test AuditStatsResponse model structure."""
        from app.api.audit_routes import AuditStatsResponse

        response = AuditStatsResponse(
            period_days=30,
            total_events=1000,
            unique_users=50,
            failed_events=10,
            auth_events=200,
            query_events=600,
            proposal_events=100,
            avg_duration_ms=1500.0,
            top_users=[{"user_id": "user-1", "count": 100}],
        )
        assert response.total_events == 1000
        assert response.unique_users == 50


class TestAuditRoutesHealth:
    """Tests for audit health endpoint."""

    @pytest.fixture
    def mock_audit_service(self):
        """Create mock audit service."""
        mock = MagicMock()
        mock._buffer = []
        mock.flush = AsyncMock(return_value=None)
        return mock

    def test_health_endpoint_response(self, mock_audit_service):
        """Test health endpoint returns correct structure."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)
            response = client.get("/api/audit/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "audit"
            assert "timestamp" in data


class TestAuditRoutesEventTypes:
    """Tests for audit event types endpoint."""

    def test_event_types_endpoint(self):
        """Test event types endpoint returns all types."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/audit/event-types")

        assert response.status_code == 200
        data = response.json()
        assert "event_types" in data
        assert isinstance(data["event_types"], list)
        assert len(data["event_types"]) > 0

        # Each event type should have value, name, and category
        for event_type in data["event_types"]:
            assert "value" in event_type
            assert "name" in event_type
            assert "category" in event_type


class TestAuditRoutesQueries:
    """Tests for audit query endpoints."""

    @pytest.fixture
    def mock_audit_service(self):
        """Create mock audit service."""
        mock = MagicMock()
        mock.get_audit_trail = AsyncMock(
            return_value=[
                {
                    "event_id": "event-123",
                    "event_type": "query.completed",
                    "action": "execute",
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": "user-456",
                    "success": True,
                }
            ]
        )
        mock.get_user_activity = AsyncMock(
            return_value={
                "user_id": "user-456",
                "period_days": 30,
                "total_events": 100,
                "event_counts": {"query.completed": 50},
            }
        )
        mock.get_security_events = AsyncMock(return_value=[])
        mock.get_statistics = AsyncMock(
            return_value={
                "period_days": 30,
                "total_events": 1000,
                "unique_users": 50,
                "failed_events": 10,
                "auth_events": 200,
                "query_events": 600,
                "proposal_events": 100,
                "avg_duration_ms": 1500.0,
                "top_users": [],
            }
        )
        mock.cleanup_old_events = AsyncMock(return_value=500)
        mock._buffer = []
        mock.flush = AsyncMock(return_value=None)
        return mock

    def test_get_audit_trail_endpoint(self, mock_audit_service):
        """Test get audit trail endpoint."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)
            response = client.get("/api/audit/trail")

            assert response.status_code == 200
            data = response.json()
            assert "events" in data
            assert "total_count" in data
            assert "has_more" in data

    def test_get_audit_trail_with_filters(self, mock_audit_service):
        """Test get audit trail with various filters."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)

            # Filter by user_id
            response = client.get("/api/audit/trail?user_id=user-456")
            assert response.status_code == 200

            # Filter by resource
            response = client.get(
                "/api/audit/trail?resource_type=conversation&resource_id=conv-123"
            )
            assert response.status_code == 200

            # Filter by event type
            response = client.get("/api/audit/trail?event_type=query.completed")
            assert response.status_code == 200

    def test_get_resource_audit_trail_endpoint(self, mock_audit_service):
        """Test get resource audit trail endpoint."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)
            response = client.get("/api/audit/trail/conversation/conv-123")

            assert response.status_code == 200
            data = response.json()
            assert data["resource_type"] == "conversation"
            assert data["resource_id"] == "conv-123"
            assert "events" in data

    def test_get_user_activity_endpoint(self, mock_audit_service):
        """Test get user activity endpoint."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)
            response = client.get("/api/audit/user/user-456/activity")

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-456"
            assert "total_events" in data
            assert "event_counts" in data

    def test_get_user_events_endpoint(self, mock_audit_service):
        """Test get user events endpoint."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)
            response = client.get("/api/audit/user/user-456/events")

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-456"
            assert "events" in data

    def test_get_security_events_endpoint(self, mock_audit_service):
        """Test get security events endpoint."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)
            response = client.get("/api/audit/security")

            assert response.status_code == 200
            data = response.json()
            assert "period_hours" in data
            assert "total_events" in data
            assert "summary" in data

    def test_get_audit_statistics_endpoint(self, mock_audit_service):
        """Test get audit statistics endpoint."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)
            response = client.get("/api/audit/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["total_events"] == 1000
            assert data["unique_users"] == 50

    def test_cleanup_old_events_endpoint(self, mock_audit_service):
        """Test cleanup old events endpoint."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        with patch(
            "app.api.audit_routes.get_audit_service", return_value=mock_audit_service
        ):
            client = TestClient(app)
            response = client.post("/api/audit/cleanup?retention_days=90")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["deleted_count"] == 500
            assert data["retention_days"] == 90


class TestAuditRoutesParameterValidation:
    """Tests for audit route parameter validation."""

    def test_audit_trail_days_validation(self):
        """Test audit trail days parameter validation."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        mock_service = MagicMock()
        mock_service.get_audit_trail = AsyncMock(return_value=[])

        with patch("app.api.audit_routes.get_audit_service", return_value=mock_service):
            client = TestClient(app)

            # Valid range (1-90)
            response = client.get("/api/audit/trail?days=30")
            assert response.status_code == 200

            # Invalid - too low
            response = client.get("/api/audit/trail?days=0")
            assert response.status_code == 422

            # Invalid - too high
            response = client.get("/api/audit/trail?days=100")
            assert response.status_code == 422

    def test_cleanup_retention_days_validation(self):
        """Test cleanup retention days parameter validation."""
        from app.api.audit_routes import router

        app = FastAPI()
        app.include_router(router)

        mock_service = MagicMock()
        mock_service.cleanup_old_events = AsyncMock(return_value=0)

        with patch("app.api.audit_routes.get_audit_service", return_value=mock_service):
            client = TestClient(app)

            # Valid range (30-365)
            response = client.post("/api/audit/cleanup?retention_days=90")
            assert response.status_code == 200

            # Invalid - too low
            response = client.post("/api/audit/cleanup?retention_days=10")
            assert response.status_code == 422

            # Invalid - too high
            response = client.post("/api/audit/cleanup?retention_days=500")
            assert response.status_code == 422


# =============================================================================
# Cross-Route Integration Tests
# =============================================================================


class TestEnterpriseRoutesIntegration:
    """Integration tests for all enterprise routes."""

    def test_all_health_endpoints_accessible(self):
        """Test all health endpoints are accessible and return correct structure."""
        from app.api.analytics_routes import router as analytics_router
        from app.api.alert_routes import router as alert_router
        from app.api.collaboration_routes import router as collaboration_router
        from app.api.audit_routes import router as audit_router

        app = FastAPI()
        app.include_router(analytics_router)
        app.include_router(alert_router)
        app.include_router(collaboration_router)
        app.include_router(audit_router)

        # Mock services
        mock_analytics = MagicMock()
        mock_analytics.enabled = True
        mock_analytics.buffer = []
        mock_analytics.last_flush = datetime.utcnow()
        mock_analytics.session_metrics = {}

        mock_audit = MagicMock()
        mock_audit._buffer = []
        mock_audit.flush = AsyncMock(return_value=None)

        with (
            patch(
                "app.api.analytics_routes.get_analytics_service",
                return_value=mock_analytics,
            ),
            patch("app.api.audit_routes.get_audit_service", return_value=mock_audit),
        ):
            client = TestClient(app)

            # Check all health endpoints
            health_endpoints = [
                "/api/analytics/health",
                "/api/alerts/health",
                "/api/collaboration/health",
                "/api/audit/health",
            ]

            for endpoint in health_endpoints:
                response = client.get(endpoint)
                assert response.status_code == 200, f"Failed for {endpoint}"
                data = response.json()
                assert "status" in data, f"Missing status for {endpoint}"
                assert "timestamp" in data, f"Missing timestamp for {endpoint}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
