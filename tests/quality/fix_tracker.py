# isort: skip_file
"""
Fix Tracking System for Production Quality Validation.

This module provides a system for tracking failures and fix attempts during
quality validation, as specified in MAPIT_PRODUCTION_QUALITY_VALIDATION_PRD.md Task 003.

Classes:
- FixAttempt: Records a single fix attempt with before/after scores
- FixTracker: Main tracker class for recording and managing fix cycles

Persistence:
- Fix history is stored in tests/quality/results/fix_history.json
- Each scenario has its own history of failures and fix attempts

Usage:
    from tests.quality.fix_tracker import FixTracker

    tracker = FixTracker()

    # Record a failure
    tracker.record_failure(
        scenario="programme_discovery",
        failure=FailureRecord(...),
        turn_number=0
    )

    # Record a fix attempt
    tracker.record_fix_attempt(
        scenario="programme_discovery",
        fix_description="Updated prompt to include more details",
        files_changed=["app/services/agents/tool_aware_agent.py"]
    )

    # Record resolution after fix
    tracker.record_resolution(
        scenario="programme_discovery",
        after_score=85.5
    )

    # Get open failures
    open_failures = tracker.get_open_failures()

    # Generate report
    report = tracker.generate_fix_report()
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class FixStatus(str, Enum):
    """Status of a fix attempt."""

    OPEN = "OPEN"  # Failure identified, no fix attempted yet
    IN_PROGRESS = "IN_PROGRESS"  # Fix attempt in progress
    RESOLVED = "RESOLVED"  # Fix successful, failure resolved
    ESCALATED = "ESCALATED"  # Max attempts reached, escalated
    DEFERRED = "DEFERRED"  # Fix deferred to later


class FailureSeverity(str, Enum):
    """Severity levels for failures."""

    CRITICAL = "CRITICAL"  # Requires immediate fix (max 5 attempts)
    HIGH = "HIGH"  # Requires fix (max 3 attempts)
    MEDIUM = "MEDIUM"  # Requires improvement (max 2 attempts)


# Maximum fix attempts by severity (per PRD)
MAX_FIX_ATTEMPTS = {
    FailureSeverity.CRITICAL: 5,
    FailureSeverity.HIGH: 3,
    FailureSeverity.MEDIUM: 2,
}


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class FixAttempt:
    """Records a single fix attempt for a failure."""

    scenario: str
    failure_id: str
    fix_description: str
    before_score: float
    after_score: float = 0.0
    success: bool = False
    files_changed: list[str] = field(default_factory=list)
    attempt_number: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario": self.scenario,
            "failure_id": self.failure_id,
            "fix_description": self.fix_description,
            "before_score": self.before_score,
            "after_score": self.after_score,
            "success": self.success,
            "files_changed": self.files_changed,
            "attempt_number": self.attempt_number,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FixAttempt":
        """Create a FixAttempt from a dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        else:
            timestamp = datetime.now()

        return cls(
            scenario=data.get("scenario", ""),
            failure_id=data.get("failure_id", ""),
            fix_description=data.get("fix_description", ""),
            before_score=data.get("before_score", 0.0),
            after_score=data.get("after_score", 0.0),
            success=data.get("success", False),
            files_changed=data.get("files_changed", []),
            attempt_number=data.get("attempt_number", 1),
            timestamp=timestamp,
            notes=data.get("notes", ""),
        )


@dataclass
class FailureTicket:
    """A ticket tracking a failure through the fix cycle."""

    id: str
    scenario: str
    category: str
    severity: FailureSeverity
    description: str
    turn_number: int
    evidence: dict[str, Any] = field(default_factory=dict)
    status: FixStatus = FixStatus.OPEN
    fix_attempts: list[FixAttempt] = field(default_factory=list)
    before_score: float = 0.0
    final_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: datetime | None = None
    resolution_notes: str = ""

    @property
    def attempt_count(self) -> int:
        """Get the number of fix attempts made."""
        return len(self.fix_attempts)

    @property
    def max_attempts(self) -> int:
        """Get the maximum allowed fix attempts for this severity."""
        return MAX_FIX_ATTEMPTS.get(self.severity, 3)

    @property
    def can_attempt_fix(self) -> bool:
        """Check if another fix attempt is allowed."""
        return (
            self.status in (FixStatus.OPEN, FixStatus.IN_PROGRESS)
            and self.attempt_count < self.max_attempts
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "scenario": self.scenario,
            "category": self.category,
            "severity": self.severity.value,
            "description": self.description,
            "turn_number": self.turn_number,
            "evidence": self.evidence,
            "status": self.status.value,
            "fix_attempts": [fa.to_dict() for fa in self.fix_attempts],
            "before_score": self.before_score,
            "final_score": self.final_score,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FailureTicket":
        """Create a FailureTicket from a dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        resolved_at = data.get("resolved_at")
        if isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at)
        else:
            resolved_at = None

        severity_str = data.get("severity", "HIGH")
        try:
            severity = FailureSeverity(severity_str)
        except ValueError:
            severity = FailureSeverity.HIGH

        status_str = data.get("status", "OPEN")
        try:
            status = FixStatus(status_str)
        except ValueError:
            status = FixStatus.OPEN

        fix_attempts = [FixAttempt.from_dict(fa) for fa in data.get("fix_attempts", [])]

        return cls(
            id=data.get("id", ""),
            scenario=data.get("scenario", ""),
            category=data.get("category", ""),
            severity=severity,
            description=data.get("description", ""),
            turn_number=data.get("turn_number", 0),
            evidence=data.get("evidence", {}),
            status=status,
            fix_attempts=fix_attempts,
            before_score=data.get("before_score", 0.0),
            final_score=data.get("final_score", 0.0),
            created_at=created_at,
            resolved_at=resolved_at,
            resolution_notes=data.get("resolution_notes", ""),
        )


# =============================================================================
# FixTracker
# =============================================================================


class FixTracker:
    """
    Main tracker class for recording and managing fix cycles.

    Persists fix history to JSON file for continuity across sessions.
    """

    DEFAULT_HISTORY_PATH = Path("tests/quality/results/fix_history.json")

    def __init__(self, history_path: str | Path | None = None):
        """
        Initialize the fix tracker.

        Args:
            history_path: Path to the fix history JSON file
                         (default: tests/quality/results/fix_history.json)
        """
        self.history_path = Path(history_path) if history_path else self.DEFAULT_HISTORY_PATH
        self.tickets: dict[str, FailureTicket] = {}
        self._load_history()

    def _generate_ticket_id(self, scenario: str, turn_number: int, category: str) -> str:
        """Generate a unique ticket ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_scenario = scenario.lower().replace(" ", "_")[:20]
        return f"{safe_scenario}_t{turn_number}_{category[:10]}_{timestamp}"

    def _load_history(self) -> None:
        """Load fix history from JSON file."""
        if self.history_path.exists():
            try:
                with open(self.history_path) as f:
                    data = json.load(f)
                for ticket_id, ticket_data in data.get("tickets", {}).items():
                    self.tickets[ticket_id] = FailureTicket.from_dict(ticket_data)
                logger.info(f"Loaded {len(self.tickets)} tickets from {self.history_path}")
            except Exception as e:
                logger.warning(f"Failed to load fix history: {e}")
                self.tickets = {}
        else:
            self.tickets = {}

    def _save_history(self) -> None:
        """Save fix history to JSON file."""
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "tickets": {tid: ticket.to_dict() for tid, ticket in self.tickets.items()},
            "last_updated": datetime.now().isoformat(),
            "summary": {
                "total_tickets": len(self.tickets),
                "open": len([t for t in self.tickets.values() if t.status == FixStatus.OPEN]),
                "in_progress": len(
                    [t for t in self.tickets.values() if t.status == FixStatus.IN_PROGRESS]
                ),
                "resolved": len(
                    [t for t in self.tickets.values() if t.status == FixStatus.RESOLVED]
                ),
                "escalated": len(
                    [t for t in self.tickets.values() if t.status == FixStatus.ESCALATED]
                ),
                "deferred": len(
                    [t for t in self.tickets.values() if t.status == FixStatus.DEFERRED]
                ),
            },
        }

        with open(self.history_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self.tickets)} tickets to {self.history_path}")

    def record_failure(
        self,
        scenario: str,
        category: str,
        severity: str | FailureSeverity,
        description: str,
        turn_number: int,
        evidence: dict[str, Any] | None = None,
        before_score: float = 0.0,
    ) -> str:
        """
        Record a failure and create a ticket for tracking.

        Args:
            scenario: Name of the scenario where failure occurred
            category: Failure category (NO_RESULTS, INCORRECT_DATA, etc.)
            severity: Failure severity (CRITICAL, HIGH, MEDIUM)
            description: Description of the failure
            turn_number: Turn number where failure occurred
            evidence: Additional evidence about the failure
            before_score: Quality score before fix attempts

        Returns:
            The ticket ID for the recorded failure
        """
        if isinstance(severity, str):
            try:
                severity = FailureSeverity(severity)
            except ValueError:
                severity = FailureSeverity.HIGH

        ticket_id = self._generate_ticket_id(scenario, turn_number, category)

        ticket = FailureTicket(
            id=ticket_id,
            scenario=scenario,
            category=category,
            severity=severity,
            description=description,
            turn_number=turn_number,
            evidence=evidence or {},
            before_score=before_score,
        )

        self.tickets[ticket_id] = ticket
        self._save_history()

        logger.info(f"Recorded failure ticket: {ticket_id}")
        return ticket_id

    def record_fix_attempt(
        self,
        ticket_id: str,
        fix_description: str,
        files_changed: list[str] | None = None,
        notes: str = "",
    ) -> bool:
        """
        Record a fix attempt for a ticket.

        Args:
            ticket_id: ID of the ticket to update
            fix_description: Description of the fix applied
            files_changed: List of files modified in the fix
            notes: Additional notes about the fix attempt

        Returns:
            True if the attempt was recorded, False if ticket not found or max attempts reached
        """
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            logger.warning(f"Ticket not found: {ticket_id}")
            return False

        if not ticket.can_attempt_fix:
            logger.warning(f"Cannot attempt fix: {ticket_id} (max attempts reached or resolved)")
            return False

        attempt = FixAttempt(
            scenario=ticket.scenario,
            failure_id=ticket_id,
            fix_description=fix_description,
            before_score=ticket.final_score if ticket.fix_attempts else ticket.before_score,
            files_changed=files_changed or [],
            attempt_number=ticket.attempt_count + 1,
            notes=notes,
        )

        ticket.fix_attempts.append(attempt)
        ticket.status = FixStatus.IN_PROGRESS

        self._save_history()

        logger.info(f"Recorded fix attempt {attempt.attempt_number} for {ticket_id}")
        return True

    def record_resolution(
        self,
        ticket_id: str,
        after_score: float,
        notes: str = "",
    ) -> bool:
        """
        Record the resolution of a fix attempt.

        If the score meets the threshold (80), the ticket is marked resolved.
        If max attempts are reached, the ticket is escalated.

        Args:
            ticket_id: ID of the ticket to update
            after_score: Quality score after the fix
            notes: Resolution notes

        Returns:
            True if resolution was recorded successfully
        """
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            logger.warning(f"Ticket not found: {ticket_id}")
            return False

        if not ticket.fix_attempts:
            logger.warning(f"No fix attempts recorded for {ticket_id}")
            return False

        # Update the latest fix attempt
        latest_attempt = ticket.fix_attempts[-1]
        latest_attempt.after_score = after_score
        latest_attempt.success = after_score >= 80

        ticket.final_score = after_score

        if after_score >= 80:
            # Fix successful
            ticket.status = FixStatus.RESOLVED
            ticket.resolved_at = datetime.now()
            ticket.resolution_notes = notes
            logger.info(f"Ticket {ticket_id} resolved with score {after_score}")
        elif ticket.attempt_count >= ticket.max_attempts:
            # Max attempts reached, escalate
            ticket.status = FixStatus.ESCALATED
            ticket.resolution_notes = notes or "Max fix attempts reached"
            logger.warning(f"Ticket {ticket_id} escalated after {ticket.attempt_count} attempts")
        else:
            # More attempts allowed
            ticket.status = FixStatus.IN_PROGRESS
            remaining = ticket.max_attempts - ticket.attempt_count
            logger.info(f"Ticket {ticket_id} score {after_score}, {remaining} attempts remaining")

        self._save_history()
        return True

    def defer_ticket(self, ticket_id: str, reason: str = "") -> bool:
        """
        Defer a ticket to be addressed later.

        Args:
            ticket_id: ID of the ticket to defer
            reason: Reason for deferring

        Returns:
            True if ticket was deferred successfully
        """
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            logger.warning(f"Ticket not found: {ticket_id}")
            return False

        ticket.status = FixStatus.DEFERRED
        ticket.resolution_notes = reason
        self._save_history()

        logger.info(f"Deferred ticket {ticket_id}: {reason}")
        return True

    def get_open_failures(self) -> list[FailureTicket]:
        """
        Get all open failures that need attention.

        Returns:
            List of FailureTicket objects with OPEN or IN_PROGRESS status
        """
        return [
            ticket
            for ticket in self.tickets.values()
            if ticket.status in (FixStatus.OPEN, FixStatus.IN_PROGRESS)
        ]

    def get_failures_by_scenario(self, scenario: str) -> list[FailureTicket]:
        """
        Get all failures for a specific scenario.

        Args:
            scenario: Name of the scenario

        Returns:
            List of FailureTicket objects for the scenario
        """
        return [
            ticket
            for ticket in self.tickets.values()
            if ticket.scenario.lower() == scenario.lower()
        ]

    def get_failures_by_severity(self, severity: FailureSeverity) -> list[FailureTicket]:
        """
        Get all failures with a specific severity.

        Args:
            severity: The severity level to filter by

        Returns:
            List of FailureTicket objects with the given severity
        """
        return [ticket for ticket in self.tickets.values() if ticket.severity == severity]

    def get_escalated_failures(self) -> list[FailureTicket]:
        """
        Get all escalated failures.

        Returns:
            List of FailureTicket objects with ESCALATED status
        """
        return [ticket for ticket in self.tickets.values() if ticket.status == FixStatus.ESCALATED]

    def get_ticket(self, ticket_id: str) -> FailureTicket | None:
        """
        Get a specific ticket by ID.

        Args:
            ticket_id: The ticket ID to look up

        Returns:
            The FailureTicket if found, None otherwise
        """
        return self.tickets.get(ticket_id)

    def generate_fix_report(self) -> dict[str, Any]:
        """
        Generate a comprehensive report of all fixes.

        Returns:
            Dictionary with fix report data suitable for JSON serialization
        """
        all_tickets = list(self.tickets.values())

        # Count by status
        status_counts = {status.value: 0 for status in FixStatus}
        for ticket in all_tickets:
            status_counts[ticket.status.value] += 1

        # Count by severity
        severity_counts = {sev.value: 0 for sev in FailureSeverity}
        for ticket in all_tickets:
            severity_counts[ticket.severity.value] += 1

        # Count by category
        category_counts: dict[str, int] = {}
        for ticket in all_tickets:
            category_counts[ticket.category] = category_counts.get(ticket.category, 0) + 1

        # Calculate fix success rate
        resolved = [t for t in all_tickets if t.status == FixStatus.RESOLVED]
        total_fix_attempts = sum(t.attempt_count for t in all_tickets)
        successful_attempts = sum(1 for t in all_tickets for fa in t.fix_attempts if fa.success)

        # Score improvements
        score_improvements = [
            t.final_score - t.before_score
            for t in resolved
            if t.before_score > 0 and t.final_score > 0
        ]
        avg_improvement = (
            sum(score_improvements) / len(score_improvements) if score_improvements else 0.0
        )

        # Group by scenario
        scenarios: dict[str, dict[str, Any]] = {}
        for ticket in all_tickets:
            if ticket.scenario not in scenarios:
                scenarios[ticket.scenario] = {
                    "total_failures": 0,
                    "resolved": 0,
                    "escalated": 0,
                    "open": 0,
                    "tickets": [],
                }
            scenarios[ticket.scenario]["total_failures"] += 1
            scenarios[ticket.scenario]["tickets"].append(ticket.id)
            if ticket.status == FixStatus.RESOLVED:
                scenarios[ticket.scenario]["resolved"] += 1
            elif ticket.status == FixStatus.ESCALATED:
                scenarios[ticket.scenario]["escalated"] += 1
            elif ticket.status in (FixStatus.OPEN, FixStatus.IN_PROGRESS):
                scenarios[ticket.scenario]["open"] += 1

        report = {
            "summary": {
                "total_tickets": len(all_tickets),
                "by_status": status_counts,
                "by_severity": severity_counts,
                "by_category": category_counts,
                "total_fix_attempts": total_fix_attempts,
                "successful_attempts": successful_attempts,
                "fix_success_rate": (
                    (successful_attempts / total_fix_attempts * 100)
                    if total_fix_attempts > 0
                    else 0.0
                ),
                "average_score_improvement": round(avg_improvement, 2),
            },
            "scenarios": scenarios,
            "open_failures": [t.to_dict() for t in self.get_open_failures()],
            "escalated_failures": [t.to_dict() for t in self.get_escalated_failures()],
            "all_tickets": [t.to_dict() for t in all_tickets],
            "generated_at": datetime.now().isoformat(),
        }

        return report

    def clear_history(self) -> None:
        """Clear all fix history (use with caution)."""
        self.tickets = {}
        self._save_history()
        logger.info("Fix history cleared")

    def __len__(self) -> int:
        """Get the number of tickets."""
        return len(self.tickets)

    def __repr__(self) -> str:
        """String representation of the tracker."""
        open_count = len(self.get_open_failures())
        return f"FixTracker({len(self.tickets)} tickets, {open_count} open)"
