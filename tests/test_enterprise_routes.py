"""
Integration Tests for Enterprise Route Modules.

Tests all 4 enterprise route modules:
- analytics_routes.py - Analytics dashboard
- alert_routes.py - Saved searches and alerts
- collaboration_routes.py - Real-time collaboration
- audit_routes.py - Audit logging

These tests use FastAPI's TestClient for HTTP testing
and mock external dependencies where needed.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_analytics_service():
    """Mock the analytics service."""
    with patch("app.api.analytics_routes.get_analytics_service") as mock:
        service = MagicMock()
        service.enabled = True
        service.buffer = []
        service.last_flush = datetime.utcnow()
        service.session_metrics = {}
        service.get_tool_performance.return_value = {"tools": []}
        service.get_slow_tools.return_value = []
        service.get_popular_tool_combinations.return_value = {"combinations": []}
        service.get_session_metrics.return_value = {}
        mock.return_value = service
        yield service


@pytest.fixture
def mock_saved_search_service():
    """Mock the saved search service."""
    with patch("app.api.alert_routes.get_saved_search_service") as mock:
        service = AsyncMock()

        # Create a mock SavedSearch object
        mock_search = MagicMock()
        mock_search.to_dict.return_value = {
            "id": "test-search-id",
            "user_id": "test-user",
            "name": "Test Search",
            "description": "Test description",
            "search_type": "calls",
            "parameters": {"keywords": "hydrogen"},
            "alert_config": {"enabled": False},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_run": None,
            "is_active": True,
            "run_count": 0,
            "alert_count": 0,
        }

        service.create_search.return_value = mock_search
        service.get_user_searches.return_value = [mock_search]
        service.get_search.return_value = mock_search
        service.update_search.return_value = mock_search
        service.delete_search.return_value = True
        service.hard_delete_search.return_value = True
        service.get_user_stats.return_value = {
            "total_searches": 5,
            "active_searches": 3,
            "inactive_searches": 2,
            "total_runs": 10,
            "total_alerts_sent": 2,
            "by_type": {"calls": 3, "projects": 2},
        }

        # Mock run_search result
        mock_result = MagicMock()
        mock_result.search_id = "test-search-id"
        mock_result.result_count = 5
        mock_result.new_count = 2
        mock_result.execution_time_ms = 150.0
        mock_result.executed_at = datetime.utcnow()
        mock_result.results = [{"id": "1"}]
        mock_result.new_results = [{"id": "1"}]
        service.run_search.return_value = mock_result

        service.process_alerts.return_value = {"processed": 5, "alerts_sent": 2}

        mock.return_value = service
        yield service


@pytest.fixture
def mock_collaboration_service():
    """Mock the collaboration service."""
    with patch("app.api.collaboration_routes.get_collaboration_service") as mock:
        service = AsyncMock()

        service.join_session.return_value = {
            "connection_id": "conn-123",
            "your_color": "#FF5733",
            "collaborators": [],
            "locked_sections": [],
        }
        service.leave_session.return_value = None
        service.get_collaborators.return_value = []
        service.update_cursor.return_value = None

        # Mock lock
        mock_lock = MagicMock()
        mock_lock.to_dict.return_value = {
            "section_id": "section-1",
            "user_id": "test-user",
            "username": "Test User",
            "acquired_at": datetime.utcnow().isoformat(),
        }
        service.lock_section.return_value = mock_lock
        service.unlock_section.return_value = True
        service.refresh_lock.return_value = True
        service.get_locked_sections.return_value = []

        service.apply_operation.return_value = {
            "success": True,
            "version": 1,
        }

        mock.return_value = service
        yield service


@pytest.fixture
def mock_audit_service():
    """Mock the audit service."""
    with patch("app.api.audit_routes.get_audit_service") as mock:
        service = AsyncMock()
        service._buffer = []

        service.get_audit_trail.return_value = [
            {
                "event_id": "evt-123",
                "event_type": "query.search",
                "action": "search_calls",
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": "test-user",
                "success": True,
                "details": {},
            }
        ]
        service.get_user_activity.return_value = {
            "user_id": "test-user",
            "period_days": 30,
            "total_events": 100,
            "event_counts": {"query.search": 50, "auth.login": 20},
        }
        service.get_security_events.return_value = []
        service.get_statistics.return_value = {
            "period_days": 30,
            "total_events": 1000,
            "unique_users": 50,
            "failed_events": 10,
            "auth_events": 200,
            "query_events": 600,
            "proposal_events": 200,
            "avg_duration_ms": 250.0,
            "top_users": [],
        }
        service.cleanup_old_events.return_value = 100
        service.flush.return_value = None

        mock.return_value = service
        yield service


# =============================================================================
# Analytics Routes Tests
# =============================================================================


class TestAnalyticsRoutes:
    """Tests for /api/analytics/* endpoints."""

    def test_analytics_health(self, client, mock_analytics_service):
        """Test analytics health endpoint returns healthy status."""
        response = client.get("/api/analytics/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "disabled"]
        assert "timestamp" in data

    def test_analytics_tools(self, client, mock_analytics_service):
        """Test tool analytics endpoint."""
        response = client.get("/api/analytics/tools?hours=24")

        assert response.status_code == 200
        data = response.json()
        assert "period_hours" in data
        assert data["period_hours"] == 24
        assert "tool_performance" in data
        assert "generated_at" in data

    def test_analytics_tools_custom_hours(self, client, mock_analytics_service):
        """Test tool analytics with custom hours parameter."""
        response = client.get("/api/analytics/tools?hours=168")

        assert response.status_code == 200
        data = response.json()
        assert data["period_hours"] == 168


# =============================================================================
# Alert Routes Tests
# =============================================================================


class TestAlertRoutes:
    """Tests for /api/alerts/* endpoints."""

    def test_alerts_health(self, client):
        """Test alerts health endpoint."""
        response = client.get("/api/alerts/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "alerts"

    def test_create_saved_search(self, client, mock_saved_search_service):
        """Test creating a saved search."""
        response = client.post(
            "/api/alerts?user_id=test-user",
            json={
                "name": "Hydrogen Calls",
                "description": "Find hydrogen funding calls",
                "search_type": "calls",
                "parameters": {"keywords": "hydrogen"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Search"
        assert data["user_id"] == "test-user"
        assert data["search_type"] == "calls"

    def test_list_saved_searches(self, client, mock_saved_search_service):
        """Test listing saved searches."""
        response = client.get("/api/alerts?user_id=test-user")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_list_saved_searches_with_filters(self, client, mock_saved_search_service):
        """Test listing saved searches with filters."""
        response = client.get("/api/alerts?user_id=test-user&search_type=calls&active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_user_stats(self, client, mock_saved_search_service):
        """Test getting user statistics."""
        response = client.get("/api/alerts/stats?user_id=test-user")

        assert response.status_code == 200
        data = response.json()
        assert data["total_searches"] == 5
        assert data["active_searches"] == 3
        assert "by_type" in data

    def test_get_saved_search(self, client, mock_saved_search_service):
        """Test getting a specific saved search."""
        response = client.get("/api/alerts/test-search-id")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-search-id"

    def test_get_saved_search_not_found(self, client, mock_saved_search_service):
        """Test getting a non-existent saved search."""
        mock_saved_search_service.get_search.return_value = None

        response = client.get("/api/alerts/nonexistent-id")

        assert response.status_code == 404
        # Error response uses "message" key from custom error handler
        data = response.json()
        assert "not found" in data.get("message", data.get("detail", "")).lower()

    def test_update_saved_search(self, client, mock_saved_search_service):
        """Test updating a saved search."""
        response = client.patch(
            "/api/alerts/test-search-id",
            json={
                "name": "Updated Name",
                "is_active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-search-id"

    def test_delete_saved_search(self, client, mock_saved_search_service):
        """Test deleting a saved search (soft delete)."""
        response = client.delete("/api/alerts/test-search-id")

        assert response.status_code == 204

    def test_delete_saved_search_permanent(self, client, mock_saved_search_service):
        """Test permanently deleting a saved search."""
        response = client.delete("/api/alerts/test-search-id?permanent=true")

        assert response.status_code == 204

    def test_run_saved_search(self, client, mock_saved_search_service):
        """Test running a saved search."""
        response = client.post("/api/alerts/test-search-id/run")

        assert response.status_code == 200
        data = response.json()
        assert data["search_id"] == "test-search-id"
        assert data["result_count"] == 5
        assert data["new_count"] == 2

    def test_process_alerts(self, client, mock_saved_search_service):
        """Test manually triggering alert processing."""
        response = client.post("/api/alerts/process-alerts")

        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 5


# =============================================================================
# Collaboration Routes Tests
# =============================================================================


class TestCollaborationRoutes:
    """Tests for /api/collaboration/* endpoints."""

    def test_collaboration_health(self, client):
        """Test collaboration health endpoint."""
        response = client.get("/api/collaboration/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "collaboration"

    def test_join_session(self, client, mock_collaboration_service):
        """Test joining a collaboration session."""
        response = client.post(
            "/api/collaboration/session-123/join?user_id=test-user",
            json={"username": "Test User"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["connection_id"] == "conn-123"
        assert data["your_color"] == "#FF5733"

    def test_leave_session(self, client, mock_collaboration_service):
        """Test leaving a collaboration session."""
        response = client.post("/api/collaboration/session-123/leave?user_id=test-user")

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_get_collaborators(self, client, mock_collaboration_service):
        """Test getting collaborators in a session."""
        response = client.get("/api/collaboration/session-123/collaborators")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_update_cursor(self, client, mock_collaboration_service):
        """Test updating cursor position."""
        response = client.post(
            "/api/collaboration/session-123/cursor?user_id=test-user",
            json={
                "section_id": "section-1",
                "position": 100,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_lock_section(self, client, mock_collaboration_service):
        """Test locking a section."""
        response = client.post(
            "/api/collaboration/session-123/sections/section-1/lock?user_id=test-user",
            json={"username": "Test User"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["lock"] is not None

    def test_lock_section_already_locked(self, client, mock_collaboration_service):
        """Test locking a section that's already locked."""
        mock_collaboration_service.lock_section.return_value = None

        response = client.post(
            "/api/collaboration/session-123/sections/section-1/lock?user_id=test-user",
            json={"username": "Test User"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "locked by another" in data["message"].lower()

    def test_unlock_section(self, client, mock_collaboration_service):
        """Test unlocking a section."""
        response = client.post(
            "/api/collaboration/session-123/sections/section-1/unlock?user_id=test-user"
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_refresh_lock(self, client, mock_collaboration_service):
        """Test refreshing a section lock."""
        response = client.post(
            "/api/collaboration/session-123/sections/section-1/refresh-lock?user_id=test-user"
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_get_locked_sections(self, client, mock_collaboration_service):
        """Test getting all locked sections."""
        response = client.get("/api/collaboration/session-123/locks")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_apply_operation(self, client, mock_collaboration_service):
        """Test applying an edit operation."""
        response = client.post(
            "/api/collaboration/session-123/sections/section-1/operation?user_id=test-user",
            json={
                "operation_type": "insert",
                "position": 0,
                "content": "Hello",
                "base_version": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["version"] == 1


# =============================================================================
# Audit Routes Tests
# =============================================================================


class TestAuditRoutes:
    """Tests for /api/audit/* endpoints."""

    def test_audit_health(self, client, mock_audit_service):
        """Test audit health endpoint."""
        response = client.get("/api/audit/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "audit"

    def test_get_audit_trail(self, client, mock_audit_service):
        """Test getting audit trail."""
        response = client.get("/api/audit/trail")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total_count" in data
        assert "has_more" in data

    def test_get_audit_trail_with_filters(self, client, mock_audit_service):
        """Test getting audit trail with filters."""
        response = client.get(
            "/api/audit/trail?user_id=test-user&event_type=query.search&days=7"
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_get_resource_audit_trail(self, client, mock_audit_service):
        """Test getting audit trail for a specific resource."""
        response = client.get("/api/audit/trail/conversation/conv-123")

        assert response.status_code == 200
        data = response.json()
        assert data["resource_type"] == "conversation"
        assert data["resource_id"] == "conv-123"

    def test_get_user_activity(self, client, mock_audit_service):
        """Test getting user activity summary."""
        response = client.get("/api/audit/user/test-user/activity?days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user"
        assert data["total_events"] == 100
        assert "event_counts" in data

    def test_get_user_events(self, client, mock_audit_service):
        """Test getting user events."""
        response = client.get("/api/audit/user/test-user/events?days=7")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user"
        assert "events" in data

    def test_get_security_events(self, client, mock_audit_service):
        """Test getting security events."""
        response = client.get("/api/audit/security?hours=24")

        assert response.status_code == 200
        data = response.json()
        assert data["period_hours"] == 24
        assert "summary" in data
        assert "events" in data

    def test_get_audit_statistics(self, client, mock_audit_service):
        """Test getting audit statistics."""
        response = client.get("/api/audit/stats?days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 30
        assert data["total_events"] == 1000
        assert data["unique_users"] == 50

    def test_get_event_types(self, client):
        """Test getting available event types."""
        response = client.get("/api/audit/event-types")

        assert response.status_code == 200
        data = response.json()
        assert "event_types" in data
        assert isinstance(data["event_types"], list)
        assert len(data["event_types"]) > 0

    def test_cleanup_old_events(self, client, mock_audit_service):
        """Test cleaning up old audit events."""
        response = client.post("/api/audit/cleanup?retention_days=90")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 100
        assert data["retention_days"] == 90


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in enterprise routes."""

    def test_invalid_search_type(self, client, mock_saved_search_service):
        """Test validation for invalid search type."""
        response = client.post(
            "/api/alerts?user_id=test-user",
            json={
                "name": "Invalid Search",
                "search_type": "invalid_type",
                "parameters": {},
            },
        )

        assert response.status_code == 422  # Validation error

    def test_invalid_alert_frequency(self, client, mock_saved_search_service):
        """Test validation for invalid alert frequency."""
        response = client.post(
            "/api/alerts?user_id=test-user",
            json={
                "name": "Test Search",
                "search_type": "calls",
                "parameters": {},
                "alert_config": {
                    "enabled": True,
                    "frequency": "invalid",
                    "channel": "email",
                },
            },
        )

        assert response.status_code == 422

    def test_invalid_operation_type(self, client, mock_collaboration_service):
        """Test validation for invalid operation type."""
        response = client.post(
            "/api/collaboration/session-123/sections/section-1/operation?user_id=test-user",
            json={
                "operation_type": "invalid",
                "position": 0,
            },
        )

        assert response.status_code == 422

    def test_missing_required_user_id(self, client):
        """Test that missing user_id returns validation error."""
        response = client.post(
            "/api/alerts",  # Missing user_id query param
            json={
                "name": "Test Search",
                "search_type": "calls",
                "parameters": {},
            },
        )

        assert response.status_code == 422


# =============================================================================
# Integration with Main App
# =============================================================================


class TestRouteRegistration:
    """Tests to verify routes are properly registered."""

    def test_analytics_routes_registered(self, client):
        """Test that analytics routes are registered."""
        response = client.get("/api/analytics/health")
        assert response.status_code == 200

    def test_alerts_routes_registered(self, client):
        """Test that alerts routes are registered."""
        response = client.get("/api/alerts/health")
        assert response.status_code == 200

    def test_collaboration_routes_registered(self, client):
        """Test that collaboration routes are registered."""
        response = client.get("/api/collaboration/health")
        assert response.status_code == 200

    def test_audit_routes_registered(self, client):
        """Test that audit routes are registered."""
        # Note: audit doesn't have a separate health endpoint in same pattern
        # We test by checking event-types endpoint which doesn't need mocking
        response = client.get("/api/audit/event-types")
        assert response.status_code == 200
