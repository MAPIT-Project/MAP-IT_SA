# isort: skip_file
"""
Tests for the Fix Tracking System.

This module tests the fix_tracker.py module which implements Task 003
of MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD.md.

Tests:
- FixAttempt dataclass creation and serialization
- FailureTicket dataclass creation and properties
- FixTracker record_failure functionality
- FixTracker record_fix_attempt functionality
- FixTracker record_resolution functionality
- Fix history persistence
- Report generation
- Fix cycle workflow tests
"""

import pytest
from datetime import datetime

from tests.quality.fix_tracker import (
    FixAttempt,
    FailureTicket,
    FixTracker,
    FixStatus,
    FailureSeverity,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def tmp_history_path(tmp_path):
    """Create a temporary path for fix history."""
    return tmp_path / "fix_history.json"


@pytest.fixture
def tracker(tmp_history_path):
    """Create a FixTracker with temporary storage."""
    return FixTracker(history_path=tmp_history_path)


@pytest.fixture
def sample_failure_data():
    """Sample failure data for testing."""
    return {
        "scenario": "programme_discovery",
        "category": "NO_RESULTS",
        "severity": "CRITICAL",
        "description": "Response contains no-results pattern: 'I don't have'",
        "turn_number": 0,
        "evidence": {"pattern": "I don't have", "response_length": 45},
        "before_score": 65.0,
    }


# =============================================================================
# FixAttempt Tests
# =============================================================================


class TestFixAttempt:
    """Tests for FixAttempt dataclass."""

    def test_fix_attempt_creation(self):
        """Test FixAttempt creation with all fields."""
        attempt = FixAttempt(
            scenario="programme_discovery",
            failure_id="test_001",
            fix_description="Updated prompt to include more details",
            before_score=65.0,
            after_score=85.0,
            success=True,
            files_changed=["app/services/agents/tool_aware_agent.py"],
            attempt_number=1,
            notes="First attempt successful",
        )

        assert attempt.scenario == "programme_discovery"
        assert attempt.failure_id == "test_001"
        assert attempt.fix_description == "Updated prompt to include more details"
        assert attempt.before_score == 65.0
        assert attempt.after_score == 85.0
        assert attempt.success is True
        assert len(attempt.files_changed) == 1
        assert attempt.attempt_number == 1
        assert attempt.notes == "First attempt successful"
        assert isinstance(attempt.timestamp, datetime)

    def test_fix_attempt_to_dict(self):
        """Test FixAttempt serialization."""
        attempt = FixAttempt(
            scenario="test_scenario",
            failure_id="test_002",
            fix_description="Test fix",
            before_score=50.0,
            after_score=80.0,
            success=True,
            files_changed=["file1.py", "file2.py"],
            attempt_number=2,
        )

        data = attempt.to_dict()

        assert data["scenario"] == "test_scenario"
        assert data["failure_id"] == "test_002"
        assert data["before_score"] == 50.0
        assert data["after_score"] == 80.0
        assert data["success"] is True
        assert len(data["files_changed"]) == 2
        assert data["attempt_number"] == 2
        assert "timestamp" in data

    def test_fix_attempt_from_dict(self):
        """Test FixAttempt deserialization."""
        data = {
            "scenario": "test_scenario",
            "failure_id": "test_003",
            "fix_description": "Test fix description",
            "before_score": 60.0,
            "after_score": 90.0,
            "success": True,
            "files_changed": ["test.py"],
            "attempt_number": 1,
            "timestamp": "2026-01-22T10:00:00",
            "notes": "Test notes",
        }

        attempt = FixAttempt.from_dict(data)

        assert attempt.scenario == "test_scenario"
        assert attempt.failure_id == "test_003"
        assert attempt.fix_description == "Test fix description"
        assert attempt.before_score == 60.0
        assert attempt.after_score == 90.0
        assert attempt.success is True
        assert attempt.notes == "Test notes"

    def test_fix_attempt_defaults(self):
        """Test FixAttempt with default values."""
        attempt = FixAttempt(
            scenario="test",
            failure_id="test_id",
            fix_description="Test",
            before_score=50.0,
        )

        assert attempt.after_score == 0.0
        assert attempt.success is False
        assert attempt.files_changed == []
        assert attempt.attempt_number == 1
        assert attempt.notes == ""


# =============================================================================
# FailureTicket Tests
# =============================================================================


class TestFailureTicket:
    """Tests for FailureTicket dataclass."""

    def test_failure_ticket_creation(self):
        """Test FailureTicket creation."""
        ticket = FailureTicket(
            id="ticket_001",
            scenario="programme_discovery",
            category="NO_RESULTS",
            severity=FailureSeverity.CRITICAL,
            description="Test failure",
            turn_number=0,
            evidence={"test": "data"},
            before_score=65.0,
        )

        assert ticket.id == "ticket_001"
        assert ticket.scenario == "programme_discovery"
        assert ticket.category == "NO_RESULTS"
        assert ticket.severity == FailureSeverity.CRITICAL
        assert ticket.status == FixStatus.OPEN
        assert ticket.attempt_count == 0
        assert ticket.max_attempts == 5  # CRITICAL = 5 attempts
        assert ticket.can_attempt_fix is True

    def test_failure_ticket_max_attempts_by_severity(self):
        """Test max attempts vary by severity."""
        critical_ticket = FailureTicket(
            id="t1",
            scenario="test",
            category="TEST",
            severity=FailureSeverity.CRITICAL,
            description="Test",
            turn_number=0,
        )
        assert critical_ticket.max_attempts == 5

        high_ticket = FailureTicket(
            id="t2",
            scenario="test",
            category="TEST",
            severity=FailureSeverity.HIGH,
            description="Test",
            turn_number=0,
        )
        assert high_ticket.max_attempts == 3

        medium_ticket = FailureTicket(
            id="t3",
            scenario="test",
            category="TEST",
            severity=FailureSeverity.MEDIUM,
            description="Test",
            turn_number=0,
        )
        assert medium_ticket.max_attempts == 2

    def test_failure_ticket_to_dict(self):
        """Test FailureTicket serialization."""
        ticket = FailureTicket(
            id="ticket_002",
            scenario="test_scenario",
            category="INCORRECT_DATA",
            severity=FailureSeverity.HIGH,
            description="Incorrect budget amount",
            turn_number=1,
            evidence={"stated": 100, "expected": 95.5},
            before_score=70.0,
        )

        data = ticket.to_dict()

        assert data["id"] == "ticket_002"
        assert data["scenario"] == "test_scenario"
        assert data["category"] == "INCORRECT_DATA"
        assert data["severity"] == "HIGH"
        assert data["status"] == "OPEN"
        assert data["turn_number"] == 1
        assert data["attempt_count"] == 0
        assert data["max_attempts"] == 3

    def test_failure_ticket_from_dict(self):
        """Test FailureTicket deserialization."""
        data = {
            "id": "ticket_003",
            "scenario": "test_scenario",
            "category": "MISSING_DATA",
            "severity": "MEDIUM",
            "description": "Missing required fields",
            "turn_number": 2,
            "evidence": {},
            "status": "IN_PROGRESS",
            "fix_attempts": [
                {
                    "scenario": "test_scenario",
                    "failure_id": "ticket_003",
                    "fix_description": "Added fields",
                    "before_score": 60.0,
                    "after_score": 75.0,
                    "success": False,
                    "files_changed": [],
                    "attempt_number": 1,
                    "timestamp": "2026-01-22T10:00:00",
                    "notes": "",
                }
            ],
            "before_score": 60.0,
            "final_score": 75.0,
            "created_at": "2026-01-22T09:00:00",
            "resolved_at": None,
            "resolution_notes": "",
        }

        ticket = FailureTicket.from_dict(data)

        assert ticket.id == "ticket_003"
        assert ticket.severity == FailureSeverity.MEDIUM
        assert ticket.status == FixStatus.IN_PROGRESS
        assert ticket.attempt_count == 1
        assert len(ticket.fix_attempts) == 1
        assert ticket.can_attempt_fix is True  # MEDIUM allows 2 attempts

    def test_failure_ticket_can_attempt_fix(self):
        """Test can_attempt_fix property."""
        ticket = FailureTicket(
            id="ticket_004",
            scenario="test",
            category="TEST",
            severity=FailureSeverity.MEDIUM,  # Max 2 attempts
            description="Test",
            turn_number=0,
        )

        # Initially can attempt
        assert ticket.can_attempt_fix is True

        # Add 2 attempts (max for MEDIUM)
        ticket.fix_attempts.append(
            FixAttempt(
                scenario="test",
                failure_id="ticket_004",
                fix_description="Fix 1",
                before_score=50.0,
                attempt_number=1,
            )
        )
        assert ticket.can_attempt_fix is True  # 1 attempt, max 2

        ticket.fix_attempts.append(
            FixAttempt(
                scenario="test",
                failure_id="ticket_004",
                fix_description="Fix 2",
                before_score=60.0,
                attempt_number=2,
            )
        )
        assert ticket.can_attempt_fix is False  # 2 attempts = max

        # Resolved ticket cannot be fixed
        ticket_resolved = FailureTicket(
            id="ticket_005",
            scenario="test",
            category="TEST",
            severity=FailureSeverity.HIGH,
            description="Test",
            turn_number=0,
            status=FixStatus.RESOLVED,
        )
        assert ticket_resolved.can_attempt_fix is False


# =============================================================================
# FixTracker Tests
# =============================================================================


class TestFixTracker:
    """Tests for FixTracker class."""

    def test_tracker_initialization(self, tracker, tmp_history_path):
        """Test FixTracker initialization."""
        assert len(tracker) == 0
        assert tracker.history_path == tmp_history_path

    def test_record_failure(self, tracker, sample_failure_data):
        """Test recording a failure."""
        ticket_id = tracker.record_failure(**sample_failure_data)

        assert ticket_id is not None
        assert len(tracker) == 1

        ticket = tracker.get_ticket(ticket_id)
        assert ticket is not None
        assert ticket.scenario == "programme_discovery"
        assert ticket.category == "NO_RESULTS"
        assert ticket.severity == FailureSeverity.CRITICAL
        assert ticket.status == FixStatus.OPEN
        assert ticket.before_score == 65.0

    def test_record_failure_with_string_severity(self, tracker):
        """Test recording a failure with string severity."""
        ticket_id = tracker.record_failure(
            scenario="test",
            category="TEST",
            severity="HIGH",  # String instead of enum
            description="Test",
            turn_number=0,
        )

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.severity == FailureSeverity.HIGH

    def test_record_fix_attempt(self, tracker, sample_failure_data):
        """Test recording a fix attempt."""
        ticket_id = tracker.record_failure(**sample_failure_data)

        success = tracker.record_fix_attempt(
            ticket_id=ticket_id,
            fix_description="Updated prompts to return results",
            files_changed=["app/services/agents/tool_aware_agent.py"],
            notes="First attempt",
        )

        assert success is True

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.IN_PROGRESS
        assert ticket.attempt_count == 1
        assert len(ticket.fix_attempts) == 1
        assert ticket.fix_attempts[0].fix_description == "Updated prompts to return results"

    def test_record_fix_attempt_invalid_ticket(self, tracker):
        """Test recording a fix attempt for non-existent ticket."""
        success = tracker.record_fix_attempt(
            ticket_id="nonexistent_ticket",
            fix_description="Test fix",
        )
        assert success is False

    def test_record_resolution_success(self, tracker, sample_failure_data):
        """Test recording a successful resolution."""
        ticket_id = tracker.record_failure(**sample_failure_data)

        tracker.record_fix_attempt(
            ticket_id=ticket_id,
            fix_description="Fixed the issue",
        )

        success = tracker.record_resolution(
            ticket_id=ticket_id,
            after_score=85.0,  # Above 80 threshold
            notes="Successfully fixed",
        )

        assert success is True

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.RESOLVED
        assert ticket.final_score == 85.0
        assert ticket.resolved_at is not None
        assert ticket.fix_attempts[-1].success is True

    def test_record_resolution_failure(self, tracker, sample_failure_data):
        """Test recording a failed resolution (score below 80)."""
        ticket_id = tracker.record_failure(**sample_failure_data)

        tracker.record_fix_attempt(
            ticket_id=ticket_id,
            fix_description="Attempted fix",
        )

        tracker.record_resolution(
            ticket_id=ticket_id,
            after_score=75.0,  # Below 80 threshold
        )

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.IN_PROGRESS  # Still in progress
        assert ticket.final_score == 75.0
        assert ticket.fix_attempts[-1].success is False

    def test_record_resolution_escalation(self, tracker):
        """Test escalation when max attempts reached."""
        # Use MEDIUM severity (max 2 attempts)
        ticket_id = tracker.record_failure(
            scenario="test",
            category="POOR_QUALITY",
            severity=FailureSeverity.MEDIUM,
            description="Test",
            turn_number=0,
            before_score=50.0,
        )

        # First attempt fails
        tracker.record_fix_attempt(ticket_id=ticket_id, fix_description="Fix 1")
        tracker.record_resolution(ticket_id=ticket_id, after_score=70.0)

        # Second attempt fails (should escalate)
        tracker.record_fix_attempt(ticket_id=ticket_id, fix_description="Fix 2")
        tracker.record_resolution(ticket_id=ticket_id, after_score=75.0)

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.ESCALATED
        assert ticket.attempt_count == 2

    def test_defer_ticket(self, tracker, sample_failure_data):
        """Test deferring a ticket."""
        ticket_id = tracker.record_failure(**sample_failure_data)

        success = tracker.defer_ticket(ticket_id, reason="Low priority")

        assert success is True

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.DEFERRED
        assert ticket.resolution_notes == "Low priority"

    def test_get_open_failures(self, tracker):
        """Test getting open failures."""
        # Create tickets with different statuses
        ticket1 = tracker.record_failure(
            scenario="test1",
            category="NO_RESULTS",
            severity="CRITICAL",
            description="Test 1",
            turn_number=0,
        )

        ticket2 = tracker.record_failure(
            scenario="test2",
            category="INCORRECT_DATA",
            severity="HIGH",
            description="Test 2",
            turn_number=0,
        )
        tracker.record_fix_attempt(ticket2, "Fix")  # Makes it IN_PROGRESS

        ticket3 = tracker.record_failure(
            scenario="test3",
            category="MISSING_DATA",
            severity="MEDIUM",
            description="Test 3",
            turn_number=0,
        )
        tracker.record_fix_attempt(ticket3, "Fix")
        tracker.record_resolution(ticket3, 85.0)  # Resolves it

        open_failures = tracker.get_open_failures()

        assert len(open_failures) == 2
        assert any(t.id == ticket1 for t in open_failures)
        assert any(t.id == ticket2 for t in open_failures)

    def test_get_failures_by_scenario(self, tracker):
        """Test getting failures by scenario."""
        tracker.record_failure(
            scenario="Scenario A",
            category="NO_RESULTS",
            severity="CRITICAL",
            description="Test 1",
            turn_number=0,
        )
        tracker.record_failure(
            scenario="Scenario A",
            category="INCORRECT_DATA",
            severity="HIGH",
            description="Test 2",
            turn_number=1,
        )
        tracker.record_failure(
            scenario="Scenario B",
            category="MISSING_DATA",
            severity="MEDIUM",
            description="Test 3",
            turn_number=0,
        )

        scenario_a_failures = tracker.get_failures_by_scenario("Scenario A")
        scenario_b_failures = tracker.get_failures_by_scenario("Scenario B")

        assert len(scenario_a_failures) == 2
        assert len(scenario_b_failures) == 1

    def test_get_failures_by_severity(self, tracker):
        """Test getting failures by severity."""
        tracker.record_failure(
            scenario="test1",
            category="NO_RESULTS",
            severity=FailureSeverity.CRITICAL,
            description="Critical",
            turn_number=0,
        )
        tracker.record_failure(
            scenario="test2",
            category="INCORRECT_DATA",
            severity=FailureSeverity.CRITICAL,
            description="Critical 2",
            turn_number=0,
        )
        tracker.record_failure(
            scenario="test3",
            category="MISSING_DATA",
            severity=FailureSeverity.HIGH,
            description="High",
            turn_number=0,
        )

        critical = tracker.get_failures_by_severity(FailureSeverity.CRITICAL)
        high = tracker.get_failures_by_severity(FailureSeverity.HIGH)

        assert len(critical) == 2
        assert len(high) == 1

    def test_get_escalated_failures(self, tracker):
        """Test getting escalated failures."""
        # Create a ticket that gets escalated (MEDIUM severity, max 2 attempts)
        ticket_id = tracker.record_failure(
            scenario="test",
            category="POOR_QUALITY",
            severity=FailureSeverity.MEDIUM,
            description="Test",
            turn_number=0,
        )

        tracker.record_fix_attempt(ticket_id, "Fix 1")
        tracker.record_resolution(ticket_id, 70.0)
        tracker.record_fix_attempt(ticket_id, "Fix 2")
        tracker.record_resolution(ticket_id, 75.0)

        escalated = tracker.get_escalated_failures()

        assert len(escalated) == 1
        assert escalated[0].id == ticket_id

    def test_persistence(self, tmp_history_path):
        """Test that fix history persists correctly."""
        # Create tracker and add data
        tracker1 = FixTracker(history_path=tmp_history_path)
        ticket_id = tracker1.record_failure(
            scenario="test_persistence",
            category="NO_RESULTS",
            severity="HIGH",
            description="Persistence test",
            turn_number=0,
            before_score=50.0,
        )
        tracker1.record_fix_attempt(ticket_id, "Test fix")

        # Verify file was created
        assert tmp_history_path.exists()

        # Create new tracker and verify data loads
        tracker2 = FixTracker(history_path=tmp_history_path)

        assert len(tracker2) == 1
        ticket = tracker2.get_ticket(ticket_id)
        assert ticket is not None
        assert ticket.scenario == "test_persistence"
        assert ticket.attempt_count == 1

    def test_generate_fix_report(self, tracker):
        """Test fix report generation."""
        # Create various tickets
        ticket1 = tracker.record_failure(
            scenario="scenario1",
            category="NO_RESULTS",
            severity=FailureSeverity.CRITICAL,
            description="Test 1",
            turn_number=0,
            before_score=50.0,
        )
        tracker.record_fix_attempt(ticket1, "Fix 1")
        tracker.record_resolution(ticket1, 85.0)  # Resolved

        tracker.record_failure(
            scenario="scenario1",
            category="INCORRECT_DATA",
            severity=FailureSeverity.HIGH,
            description="Test 2",
            turn_number=1,
            before_score=60.0,
        )  # Open

        ticket3 = tracker.record_failure(
            scenario="scenario2",
            category="POOR_QUALITY",
            severity=FailureSeverity.MEDIUM,
            description="Test 3",
            turn_number=0,
            before_score=65.0,
        )
        tracker.record_fix_attempt(ticket3, "Fix 3a")
        tracker.record_resolution(ticket3, 70.0)
        tracker.record_fix_attempt(ticket3, "Fix 3b")
        tracker.record_resolution(ticket3, 75.0)  # Escalated

        report = tracker.generate_fix_report()

        # Check summary
        assert report["summary"]["total_tickets"] == 3
        assert report["summary"]["by_status"]["RESOLVED"] == 1
        assert report["summary"]["by_status"]["OPEN"] == 1
        assert report["summary"]["by_status"]["ESCALATED"] == 1
        assert report["summary"]["by_severity"]["CRITICAL"] == 1
        assert report["summary"]["by_severity"]["HIGH"] == 1
        assert report["summary"]["by_severity"]["MEDIUM"] == 1
        assert report["summary"]["total_fix_attempts"] == 3
        assert report["summary"]["successful_attempts"] == 1

        # Check scenarios
        assert "scenario1" in report["scenarios"]
        assert report["scenarios"]["scenario1"]["total_failures"] == 2
        assert report["scenarios"]["scenario1"]["resolved"] == 1
        assert report["scenarios"]["scenario1"]["open"] == 1

        # Check lists
        assert len(report["open_failures"]) == 1
        assert len(report["escalated_failures"]) == 1
        assert len(report["all_tickets"]) == 3

    def test_clear_history(self, tracker, sample_failure_data):
        """Test clearing fix history."""
        tracker.record_failure(**sample_failure_data)
        assert len(tracker) == 1

        tracker.clear_history()

        assert len(tracker) == 0
        assert tracker.history_path.exists()  # File still exists but empty

    def test_repr(self, tracker, sample_failure_data):
        """Test string representation."""
        repr_empty = repr(tracker)
        assert "0 tickets" in repr_empty
        assert "0 open" in repr_empty

        tracker.record_failure(**sample_failure_data)
        repr_with_ticket = repr(tracker)
        assert "1 tickets" in repr_with_ticket
        assert "1 open" in repr_with_ticket


class TestFixCycleWorkflow:
    """Tests for complete fix cycle workflow."""

    def test_complete_fix_cycle_success(self, tracker):
        """Test a complete fix cycle ending in success."""
        # 1. Record failure
        ticket_id = tracker.record_failure(
            scenario="programme_discovery",
            category="NO_RESULTS",
            severity=FailureSeverity.HIGH,
            description="Tool returned empty results",
            turn_number=0,
            evidence={"tool": "search_funding_calls", "result": []},
            before_score=45.0,
        )

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.OPEN

        # 2. First fix attempt (fails)
        tracker.record_fix_attempt(
            ticket_id=ticket_id,
            fix_description="Added fallback to API search",
            files_changed=["app/services/tools/call_search.py"],
            notes="First attempt - added API fallback",
        )
        tracker.record_resolution(ticket_id, after_score=70.0)

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.IN_PROGRESS
        assert ticket.attempt_count == 1
        assert ticket.fix_attempts[-1].success is False

        # 3. Second fix attempt (succeeds)
        tracker.record_fix_attempt(
            ticket_id=ticket_id,
            fix_description="Expanded search keywords and added retry logic",
            files_changed=[
                "app/services/tools/call_search.py",
                "app/services/agents/tool_aware_agent.py",
            ],
            notes="Second attempt - improved search",
        )
        tracker.record_resolution(ticket_id, after_score=88.0, notes="Fix verified")

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.RESOLVED
        assert ticket.final_score == 88.0
        assert ticket.attempt_count == 2
        assert ticket.fix_attempts[-1].success is True
        assert ticket.resolved_at is not None

    def test_complete_fix_cycle_escalation(self, tracker):
        """Test a complete fix cycle ending in escalation."""
        # MEDIUM severity = 2 max attempts
        ticket_id = tracker.record_failure(
            scenario="budget_comparison",
            category="POOR_QUALITY",
            severity=FailureSeverity.MEDIUM,
            description="Response lacks specific numbers",
            turn_number=2,
            before_score=55.0,
        )

        # First attempt fails
        tracker.record_fix_attempt(ticket_id, "Enhanced number formatting")
        tracker.record_resolution(ticket_id, 68.0)

        # Second attempt fails (should escalate)
        tracker.record_fix_attempt(ticket_id, "Added data enrichment")
        tracker.record_resolution(ticket_id, 72.0)

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.status == FixStatus.ESCALATED
        assert ticket.attempt_count == 2
        assert ticket.can_attempt_fix is False

        # Cannot add more attempts
        success = tracker.record_fix_attempt(ticket_id, "Third attempt")
        assert success is False

    def test_multiple_scenarios_tracking(self, tracker):
        """Test tracking failures across multiple scenarios."""
        scenarios = [
            ("programme_discovery", "NO_RESULTS", FailureSeverity.CRITICAL),
            ("programme_comparison", "INCORRECT_DATA", FailureSeverity.CRITICAL),
            ("budget_iteration", "MISSING_DATA", FailureSeverity.HIGH),
            ("eligibility_routing", "POOR_QUALITY", FailureSeverity.MEDIUM),
        ]

        ticket_ids = []
        for scenario, category, severity in scenarios:
            tid = tracker.record_failure(
                scenario=scenario,
                category=category,
                severity=severity,
                description=f"Test failure for {scenario}",
                turn_number=0,
            )
            ticket_ids.append(tid)

        assert len(tracker) == 4
        assert len(tracker.get_open_failures()) == 4

        # Resolve first two
        for tid in ticket_ids[:2]:
            tracker.record_fix_attempt(tid, "Fix applied")
            tracker.record_resolution(tid, 85.0)

        assert len(tracker.get_open_failures()) == 2

        # Generate report
        report = tracker.generate_fix_report()
        assert report["summary"]["total_tickets"] == 4
        assert report["summary"]["by_status"]["RESOLVED"] == 2
        assert report["summary"]["by_status"]["OPEN"] == 2


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_severity_string(self, tracker):
        """Test handling of invalid severity string."""
        ticket_id = tracker.record_failure(
            scenario="test",
            category="TEST",
            severity="INVALID_SEVERITY",  # Invalid
            description="Test",
            turn_number=0,
        )

        ticket = tracker.get_ticket(ticket_id)
        assert ticket.severity == FailureSeverity.HIGH  # Defaults to HIGH

    def test_empty_tracker_operations(self, tracker):
        """Test operations on empty tracker."""
        assert tracker.get_open_failures() == []
        assert tracker.get_escalated_failures() == []
        assert tracker.get_failures_by_scenario("nonexistent") == []
        assert tracker.get_ticket("nonexistent") is None

        report = tracker.generate_fix_report()
        assert report["summary"]["total_tickets"] == 0
        assert report["summary"]["fix_success_rate"] == 0.0

    def test_resolution_without_attempt(self, tracker, sample_failure_data):
        """Test recording resolution without any fix attempt."""
        ticket_id = tracker.record_failure(**sample_failure_data)

        success = tracker.record_resolution(ticket_id, 85.0)
        assert success is False  # No fix attempts recorded

    def test_corrupted_history_file(self, tmp_history_path):
        """Test handling of corrupted history file."""
        # Write invalid JSON
        tmp_history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_history_path, "w") as f:
            f.write("invalid json {{{")

        # Tracker should recover gracefully
        tracker = FixTracker(history_path=tmp_history_path)
        assert len(tracker) == 0

    def test_concurrent_ticket_ids(self, tracker):
        """Test that concurrent ticket IDs are unique."""
        ids = set()
        for i in range(10):
            tid = tracker.record_failure(
                scenario="test",
                category="TEST",
                severity="HIGH",
                description=f"Test {i}",
                turn_number=i,
            )
            ids.add(tid)

        # All IDs should be unique
        assert len(ids) == 10
