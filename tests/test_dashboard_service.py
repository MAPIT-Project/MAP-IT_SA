"""
Tests for DashboardService (Task 16)

Tests dashboard aggregation, readiness checks, and next actions.
"""

from datetime import datetime, timedelta

import pytest

from app.services.proposal_writing.dashboard_service import (
    ActionPriority,
    DashboardService,
    NextAction,
    ReadinessCheck,
    SectionStatus,
    SectionSummary,
)


class TestSectionStatus:
    """Tests for SectionStatus enum."""

    def test_status_values(self):
        """Test all status values."""
        assert SectionStatus.NOT_STARTED.value == "not_started"
        assert SectionStatus.DRAFT.value == "draft"
        assert SectionStatus.NEEDS_WORK.value == "needs_work"
        assert SectionStatus.ACCEPTABLE.value == "acceptable"
        assert SectionStatus.GOOD.value == "good"
        assert SectionStatus.EXCELLENT.value == "excellent"

    def test_status_count(self):
        """Test that we have all 6 statuses."""
        assert len(SectionStatus) == 6


class TestActionPriority:
    """Tests for ActionPriority enum."""

    def test_priority_values(self):
        """Test all priority values."""
        assert ActionPriority.CRITICAL.value == "critical"
        assert ActionPriority.HIGH.value == "high"
        assert ActionPriority.MEDIUM.value == "medium"
        assert ActionPriority.LOW.value == "low"

    def test_priority_count(self):
        """Test that we have all 4 priorities."""
        assert len(ActionPriority) == 4


class TestSectionSummary:
    """Tests for SectionSummary dataclass."""

    def test_create_section_summary(self):
        """Test creating a section summary."""
        summary = SectionSummary(
            id="section-1",
            title="Excellence: Objectives",
            section_type="excellence_objectives",
            status=SectionStatus.GOOD,
            word_count=1500,
            score=3.8,
            confidence=0.85,
            gap_count=2,
            suggestion_count=5,
            last_edited=datetime.now(),
        )

        assert summary.id == "section-1"
        assert summary.title == "Excellence: Objectives"
        assert summary.status == SectionStatus.GOOD
        assert summary.score == 3.8


class TestNextAction:
    """Tests for NextAction dataclass."""

    def test_create_next_action(self):
        """Test creating a next action."""
        action = NextAction(
            id="action-1",
            title="Improve Section",
            description="Score needs improvement",
            priority=ActionPriority.HIGH,
            section_id="section-1",
            section_title="Excellence",
            action_type="improve",
            estimated_minutes=30,
            impact="+0.5 points",
        )

        assert action.id == "action-1"
        assert action.priority == ActionPriority.HIGH
        assert action.estimated_minutes == 30


class TestReadinessCheck:
    """Tests for ReadinessCheck dataclass."""

    def test_create_readiness_check(self):
        """Test creating a readiness check."""
        check = ReadinessCheck(
            id="check-1",
            category="Content",
            title="All sections have content",
            description="Every section must have content",
            passed=True,
            details=None,
            blocking=True,
        )

        assert check.id == "check-1"
        assert check.passed is True
        assert check.blocking is True


class TestDashboardService:
    """Tests for DashboardService."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        return DashboardService()

    def test_init(self, service):
        """Test service initialization."""
        assert service.progress_service is not None
        assert service.THRESHOLD_SCORE == 3.0
        assert service.GOOD_SCORE == 3.5
        assert service.EXCELLENT_SCORE == 4.0

    # --- Add Section Tests ---

    def test_add_section_not_started(self, service):
        """Test adding a section with no content."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-1",
            title="Excellence",
            section_type="excellence_objectives",
            content="",
        )

        assert summary.status == SectionStatus.NOT_STARTED
        assert summary.word_count == 0

    def test_add_section_draft(self, service):
        """Test adding a section with content but no score."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-2",
            title="Excellence",
            section_type="excellence_objectives",
            content="This is a draft section with enough content " * 20,
        )

        assert summary.status == SectionStatus.DRAFT
        assert summary.word_count > 50
        assert summary.score is None

    def test_add_section_with_score(self, service):
        """Test adding a section with content and score."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-3",
            title="Excellence",
            section_type="excellence_objectives",
            content="Content " * 100,
            score=3.8,
        )

        assert summary.status == SectionStatus.GOOD
        assert summary.score == 3.8

    def test_add_section_needs_work(self, service):
        """Test section status when score below threshold."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-4",
            title="Excellence",
            section_type="excellence_objectives",
            content="Content " * 100,
            score=2.5,
        )

        assert summary.status == SectionStatus.NEEDS_WORK

    def test_add_section_excellent(self, service):
        """Test section status when score is excellent."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-5",
            title="Excellence",
            section_type="excellence_objectives",
            content="Content " * 100,
            score=4.5,
        )

        assert summary.status == SectionStatus.EXCELLENT

    def test_add_section_acceptable(self, service):
        """Test section status when score is acceptable (3.0-3.5)."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-acceptable",
            title="Excellence",
            section_type="excellence_objectives",
            content="Content " * 100,
            score=3.2,  # Between THRESHOLD_SCORE (3.0) and GOOD_SCORE (3.5)
        )

        assert summary.status == SectionStatus.ACCEPTABLE

    def test_add_section_boundary_at_3_0(self, service):
        """Test section status exactly at 3.0 threshold."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-3.0",
            title="Excellence",
            section_type="excellence_objectives",
            content="Content " * 100,
            score=3.0,  # Exactly at THRESHOLD_SCORE
        )

        assert summary.status == SectionStatus.ACCEPTABLE

    def test_add_section_boundary_at_3_5(self, service):
        """Test section status exactly at 3.5 threshold."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-3.5",
            title="Excellence",
            section_type="excellence_objectives",
            content="Content " * 100,
            score=3.5,  # Exactly at GOOD_SCORE
        )

        assert summary.status == SectionStatus.GOOD

    def test_add_section_boundary_at_4_0(self, service):
        """Test section status exactly at 4.0 threshold."""
        summary = service.add_section(
            proposal_id="test-proposal",
            section_id="section-4.0",
            title="Excellence",
            section_type="excellence_objectives",
            content="Content " * 100,
            score=4.0,  # Exactly at EXCELLENT_SCORE
        )

        assert summary.status == SectionStatus.EXCELLENT

    # --- Update Section Score Tests ---

    def test_update_section_score(self, service):
        """Test updating a section's score."""
        proposal_id = "test-update"

        # Add section
        service.add_section(
            proposal_id=proposal_id,
            section_id="section-1",
            title="Test",
            section_type="test",
            content="Content " * 100,
            score=2.5,
        )

        # Update score
        updated = service.update_section_score(
            proposal_id=proposal_id, section_id="section-1", score=3.8
        )

        assert updated is not None
        assert updated.score == 3.8
        assert updated.status == SectionStatus.GOOD

    def test_update_section_score_not_found(self, service):
        """Test updating a non-existent section."""
        result = service.update_section_score(proposal_id="fake", section_id="fake", score=4.0)

        assert result is None

    def test_update_section_score_with_confidence(self, service):
        """Test updating score with confidence value."""
        proposal_id = "test-confidence"

        service.add_section(
            proposal_id=proposal_id,
            section_id="section-1",
            title="Test",
            section_type="test",
            content="Content " * 100,
            score=2.5,
        )

        updated = service.update_section_score(
            proposal_id=proposal_id, section_id="section-1", score=3.8, confidence=0.92
        )

        assert updated is not None
        assert updated.score == 3.8
        assert updated.confidence == 0.92

    def test_update_section_score_to_needs_work(self, service):
        """Test update that changes status to NEEDS_WORK."""
        proposal_id = "test-needs-work"

        service.add_section(
            proposal_id=proposal_id,
            section_id="section-1",
            title="Test",
            section_type="test",
            content="Content " * 100,
            score=4.0,  # Start as EXCELLENT
        )

        updated = service.update_section_score(
            proposal_id=proposal_id,
            section_id="section-1",
            score=2.5,  # Below threshold
        )

        assert updated.status == SectionStatus.NEEDS_WORK

    def test_update_section_score_to_acceptable(self, service):
        """Test update that changes status to ACCEPTABLE."""
        proposal_id = "test-acceptable"

        service.add_section(
            proposal_id=proposal_id,
            section_id="section-1",
            title="Test",
            section_type="test",
            content="Content " * 100,
            score=4.5,  # Start as EXCELLENT
        )

        updated = service.update_section_score(
            proposal_id=proposal_id,
            section_id="section-1",
            score=3.2,  # Between 3.0 and 3.5
        )

        assert updated.status == SectionStatus.ACCEPTABLE

    def test_update_section_score_to_good(self, service):
        """Test update that changes status to GOOD."""
        proposal_id = "test-good"

        service.add_section(
            proposal_id=proposal_id,
            section_id="section-1",
            title="Test",
            section_type="test",
            content="Content " * 100,
            score=2.5,  # Start as NEEDS_WORK
        )

        updated = service.update_section_score(
            proposal_id=proposal_id,
            section_id="section-1",
            score=3.7,  # Between 3.5 and 4.0
        )

        assert updated.status == SectionStatus.GOOD

    def test_update_section_score_to_excellent(self, service):
        """Test update that changes status to EXCELLENT."""
        proposal_id = "test-excellent"

        service.add_section(
            proposal_id=proposal_id,
            section_id="section-1",
            title="Test",
            section_type="test",
            content="Content " * 100,
            score=2.5,  # Start as NEEDS_WORK
        )

        updated = service.update_section_score(
            proposal_id=proposal_id,
            section_id="section-1",
            score=4.5,  # Above 4.0
        )

        assert updated.status == SectionStatus.EXCELLENT

    def test_update_section_score_short_content_stays_not_started(self, service):
        """Test that short content sections stay NOT_STARTED even with score update."""
        proposal_id = "test-short"

        # Add section with short content
        service.add_section(
            proposal_id=proposal_id,
            section_id="section-1",
            title="Test",
            section_type="test",
            content="Short",  # Less than 50 words
            score=None,
        )

        # Update with a score
        updated = service.update_section_score(
            proposal_id=proposal_id, section_id="section-1", score=4.0
        )

        # Status should stay NOT_STARTED due to short content
        assert updated.status == SectionStatus.NOT_STARTED

    # --- Set Proposal Info Tests ---

    def test_set_proposal_info(self, service):
        """Test setting proposal info."""
        deadline = datetime.now() + timedelta(days=30)

        service.set_proposal_info(
            proposal_id="test-proposal",
            title="My Proposal",
            call_id="CALL-123",
            call_title="Test Call",
            deadline=deadline,
        )

        assert service._proposal_cache["test-proposal"]["title"] == "My Proposal"
        assert service._proposal_cache["test-proposal"]["deadline"] == deadline

    # --- Count By Status Tests ---

    def test_count_by_status_empty(self, service):
        """Test counting with no sections."""
        counts = service._count_by_status([])

        for status in SectionStatus:
            assert counts[status.value] == 0

    def test_count_by_status_multiple(self, service):
        """Test counting with multiple sections."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.DRAFT, 100, None, None, 0, 0, None),
            SectionSummary("2", "S2", "t", SectionStatus.DRAFT, 100, None, None, 0, 0, None),
            SectionSummary("3", "S3", "t", SectionStatus.GOOD, 100, 3.8, None, 0, 0, None),
            SectionSummary("4", "S4", "t", SectionStatus.EXCELLENT, 100, 4.5, None, 0, 0, None),
        ]

        counts = service._count_by_status(sections)

        assert counts["draft"] == 2
        assert counts["good"] == 1
        assert counts["excellent"] == 1
        assert counts["not_started"] == 0

    # --- Generate Next Actions Tests ---

    def test_generate_next_actions_not_started(self, service):
        """Test generating actions for not started sections."""
        sections = [
            SectionSummary(
                "1", "Section 1", "t", SectionStatus.NOT_STARTED, 0, None, None, 0, 0, None
            ),
        ]

        actions = service._generate_next_actions("proposal-1", sections)

        assert len(actions) > 0
        assert actions[0].priority == ActionPriority.CRITICAL
        assert actions[0].action_type == "write"

    def test_generate_next_actions_draft(self, service):
        """Test generating actions for draft sections."""
        sections = [
            SectionSummary("1", "Section 1", "t", SectionStatus.DRAFT, 500, None, None, 0, 0, None),
        ]

        actions = service._generate_next_actions("proposal-1", sections)

        assert len(actions) > 0
        assert actions[0].action_type == "review"

    def test_generate_next_actions_needs_work(self, service):
        """Test generating actions for sections below threshold."""
        sections = [
            SectionSummary(
                "1", "Section 1", "t", SectionStatus.NEEDS_WORK, 500, 2.5, None, 0, 0, None
            ),
        ]

        actions = service._generate_next_actions("proposal-1", sections)

        assert len(actions) > 0
        assert actions[0].priority == ActionPriority.CRITICAL
        assert actions[0].action_type == "improve"

    def test_generate_next_actions_with_gaps(self, service):
        """Test generating actions for sections with gaps."""
        sections = [
            SectionSummary("1", "Section 1", "t", SectionStatus.GOOD, 500, 3.8, None, 3, 0, None),
        ]

        actions = service._generate_next_actions("proposal-1", sections)

        # Should have an action to close gaps
        gap_action = next((a for a in actions if "gap" in a.title.lower()), None)
        assert gap_action is not None
        assert gap_action.action_type == "fix"

    def test_generate_next_actions_sorted_by_priority(self, service):
        """Test that actions are sorted by priority."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.GOOD, 500, 3.8, None, 0, 0, None),
            SectionSummary("2", "S2", "t", SectionStatus.NOT_STARTED, 0, None, None, 0, 0, None),
            SectionSummary("3", "S3", "t", SectionStatus.DRAFT, 500, None, None, 0, 0, None),
        ]

        actions = service._generate_next_actions("proposal-1", sections)

        # Critical should come before high
        if len(actions) >= 2:
            priorities = [a.priority for a in actions]
            critical_idx = (
                priorities.index(ActionPriority.CRITICAL)
                if ActionPriority.CRITICAL in priorities
                else float("inf")
            )
            high_idx = (
                priorities.index(ActionPriority.HIGH)
                if ActionPriority.HIGH in priorities
                else float("inf")
            )

            if critical_idx != float("inf") and high_idx != float("inf"):
                assert critical_idx < high_idx

    def test_generate_next_actions_limit(self, service):
        """Test that actions are limited to 10."""
        sections = [
            SectionSummary(
                f"{i}", f"S{i}", "t", SectionStatus.NOT_STARTED, 0, None, None, 5, 0, None
            )
            for i in range(15)
        ]

        actions = service._generate_next_actions("proposal-1", sections)

        assert len(actions) <= 10

    def test_generate_next_actions_empty_sections(self, service):
        """Test generating actions with no sections."""
        actions = service._generate_next_actions("proposal-1", [])
        assert actions == []

    def test_generate_next_actions_all_excellent(self, service):
        """Test generating actions when all sections are excellent."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.EXCELLENT, 1000, 4.5, None, 0, 0, None),
            SectionSummary("2", "S2", "t", SectionStatus.EXCELLENT, 1000, 4.8, None, 0, 0, None),
        ]

        actions = service._generate_next_actions("proposal-1", sections)

        # Should have no actions when everything is excellent and no gaps
        assert len(actions) == 0

    def test_generate_next_actions_gap_priority_based_on_score(self, service):
        """Test that gap actions priority depends on section score."""
        sections = [
            SectionSummary("1", "High Score", "t", SectionStatus.GOOD, 500, 3.8, None, 3, 0, None),
            SectionSummary(
                "2", "Low Score", "t", SectionStatus.NEEDS_WORK, 500, 2.5, None, 3, 0, None
            ),
        ]

        actions = service._generate_next_actions("proposal-1", sections)

        # Find gap actions
        gap_actions = [a for a in actions if "gap" in a.title.lower()]

        # Low score section gaps should be HIGH priority
        low_score_gap = next((a for a in gap_actions if "Low Score" in a.title), None)
        assert low_score_gap.priority == ActionPriority.HIGH

        # High score section gaps should be MEDIUM priority
        high_score_gap = next((a for a in gap_actions if "High Score" in a.title), None)
        assert high_score_gap.priority == ActionPriority.MEDIUM

    # --- Readiness Check Tests ---

    def test_readiness_check_all_content(self, service):
        """Test readiness check for all content."""
        # All sections have content
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.GOOD, 500, 3.8, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        content_check = next((c for c in checks if c.id == "all_content"), None)
        assert content_check is not None
        assert content_check.passed is True

    def test_readiness_check_missing_content(self, service):
        """Test readiness check when content is missing."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.NOT_STARTED, 0, None, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        content_check = next((c for c in checks if c.id == "all_content"), None)
        assert content_check is not None
        assert content_check.passed is False
        assert content_check.blocking is True

    def test_readiness_check_all_evaluated(self, service):
        """Test readiness check for all evaluated."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.GOOD, 500, 3.8, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        eval_check = next((c for c in checks if c.id == "all_evaluated"), None)
        assert eval_check is not None
        assert eval_check.passed is True

    def test_readiness_check_not_evaluated(self, service):
        """Test readiness check when sections not evaluated."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.DRAFT, 500, None, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        eval_check = next((c for c in checks if c.id == "all_evaluated"), None)
        assert eval_check is not None
        assert eval_check.passed is False

    def test_readiness_check_above_threshold(self, service):
        """Test readiness check for all above threshold."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.GOOD, 500, 3.8, None, 0, 0, None),
            SectionSummary("2", "S2", "t", SectionStatus.EXCELLENT, 500, 4.5, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        threshold_check = next((c for c in checks if c.id == "above_threshold"), None)
        assert threshold_check is not None
        assert threshold_check.passed is True

    def test_readiness_check_below_threshold(self, service):
        """Test readiness check when section below threshold."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.NEEDS_WORK, 500, 2.5, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        threshold_check = next((c for c in checks if c.id == "above_threshold"), None)
        assert threshold_check is not None
        assert threshold_check.passed is False
        assert threshold_check.blocking is True

    def test_readiness_check_competitive_score(self, service):
        """Test readiness check for competitive average score."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.GOOD, 500, 4.0, None, 0, 0, None),
            SectionSummary("2", "S2", "t", SectionStatus.EXCELLENT, 500, 4.5, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        competitive_check = next((c for c in checks if c.id == "competitive_score"), None)
        assert competitive_check is not None
        assert competitive_check.passed is True  # Average is 4.25 >= 3.5

    def test_readiness_check_word_count_within_limits(self, service):
        """Test readiness check for word count within limits."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.GOOD, 8000, 4.0, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        word_check = next((c for c in checks if c.id == "word_count"), None)
        assert word_check is not None
        assert word_check.passed is True  # 8000 is within 5000-15000

    def test_readiness_check_word_count_too_short(self, service):
        """Test readiness check for word count too short."""
        sections = [
            SectionSummary("1", "S1", "t", SectionStatus.GOOD, 1000, 4.0, None, 0, 0, None),
        ]

        checks = service._run_readiness_checks("proposal-1", sections)

        word_check = next((c for c in checks if c.id == "word_count"), None)
        assert word_check is not None
        assert word_check.passed is False  # 1000 < 5000

    # --- Calculate Readiness Score Tests ---

    def test_calculate_readiness_score_all_passed(self, service):
        """Test readiness score when all checks pass."""
        checks = [
            ReadinessCheck("1", "Cat", "Test1", "Desc", True, None, True),
            ReadinessCheck("2", "Cat", "Test2", "Desc", True, None, False),
        ]

        score = service._calculate_readiness_score(checks)

        assert score == 100.0

    def test_calculate_readiness_score_none_passed(self, service):
        """Test readiness score when no checks pass."""
        checks = [
            ReadinessCheck("1", "Cat", "Test1", "Desc", False, None, True),
            ReadinessCheck("2", "Cat", "Test2", "Desc", False, None, False),
        ]

        score = service._calculate_readiness_score(checks)

        assert score == 0.0

    def test_calculate_readiness_score_blocking_weight(self, service):
        """Test that blocking checks have more weight."""
        # Same number of passed/failed, but different weights
        checks = [
            ReadinessCheck("1", "Cat", "Blocking", "Desc", True, None, True),  # 2 weight, passed
            ReadinessCheck("2", "Cat", "NonBlock", "Desc", False, None, False),  # 1 weight, failed
        ]

        score = service._calculate_readiness_score(checks)

        # Weight: 2 + 1 = 3
        # Earned: 2 (from blocking passed)
        # Score: 2/3 = 66.67%
        assert abs(score - 66.67) < 1.0

    def test_calculate_readiness_score_empty(self, service):
        """Test readiness score with no checks."""
        score = service._calculate_readiness_score([])
        assert score == 0.0

    # --- Funding Probability Tests ---

    def test_estimate_funding_probability_none_score(self, service):
        """Test funding probability with no score."""
        result = service._estimate_funding_probability(None, 80)
        assert result is None

    def test_estimate_funding_probability_low_score(self, service):
        """Test funding probability with low score."""
        result = service._estimate_funding_probability(2.5, 100)
        assert result < 0.1

    def test_estimate_funding_probability_threshold_score(self, service):
        """Test funding probability at threshold."""
        result = service._estimate_funding_probability(3.0, 100)
        assert 0.1 < result < 0.3

    def test_estimate_funding_probability_good_score(self, service):
        """Test funding probability with good score."""
        result = service._estimate_funding_probability(4.0, 100)
        assert 0.4 < result < 0.6

    def test_estimate_funding_probability_excellent_score(self, service):
        """Test funding probability with excellent score."""
        result = service._estimate_funding_probability(4.5, 100)
        assert result > 0.6

    def test_estimate_funding_probability_readiness_factor(self, service):
        """Test that readiness affects funding probability."""
        high_readiness = service._estimate_funding_probability(4.0, 100)
        low_readiness = service._estimate_funding_probability(4.0, 50)

        assert high_readiness > low_readiness

    def test_estimate_funding_probability_capped(self, service):
        """Test that funding probability is capped at 95%."""
        result = service._estimate_funding_probability(5.0, 100)
        assert result <= 0.95

    # --- Get Dashboard Tests ---

    @pytest.mark.asyncio
    async def test_get_dashboard_basic(self, service):
        """Test getting dashboard data."""
        proposal_id = "test-dashboard"
        user_id = "test-user"

        # Set up proposal
        service.set_proposal_info(proposal_id=proposal_id, title="Test Proposal")

        # Add sections
        service.add_section(
            proposal_id=proposal_id,
            section_id="s1",
            title="Section 1",
            section_type="excellence",
            content="Content " * 100,
            score=3.8,
        )

        dashboard = await service.get_dashboard(proposal_id, user_id)

        assert dashboard.proposal_id == proposal_id
        assert dashboard.proposal_title == "Test Proposal"
        assert len(dashboard.sections) == 1
        assert len(dashboard.readiness_checks) > 0

    @pytest.mark.asyncio
    async def test_get_dashboard_calculates_completion(self, service):
        """Test that dashboard calculates completion."""
        proposal_id = "test-completion"
        user_id = "test-user"

        service.set_proposal_info(proposal_id=proposal_id, title="Test")

        # Set up progress
        await service.progress_service.update_progress(
            proposal_id=proposal_id, sections_completed=3, total_sections=6
        )

        dashboard = await service.get_dashboard(proposal_id, user_id)

        assert dashboard.completion_percentage == 50.0

    @pytest.mark.asyncio
    async def test_get_dashboard_submission_ready(self, service):
        """Test submission readiness in dashboard."""
        proposal_id = "test-ready"
        user_id = "test-user"

        service.set_proposal_info(proposal_id=proposal_id, title="Test")

        # Add sections that pass all blocking checks
        service.add_section(
            proposal_id=proposal_id,
            section_id="s1",
            title="Section 1",
            section_type="excellence",
            content="Content " * 2000,  # Enough words
            score=4.0,  # Above threshold
        )

        dashboard = await service.get_dashboard(proposal_id, user_id)

        # Should have some blocking checks that pass
        blocking_checks = [c for c in dashboard.readiness_checks if c.blocking]
        assert len(blocking_checks) > 0

    # --- Get Quick Summary Tests ---

    @pytest.mark.asyncio
    async def test_get_quick_summary(self, service):
        """Test getting quick summary."""
        proposal_id = "test-summary"

        service.set_proposal_info(proposal_id=proposal_id, title="Quick Test")

        service.add_section(
            proposal_id=proposal_id,
            section_id="s1",
            title="Section 1",
            section_type="excellence",
            content="Content " * 100,
            score=3.8,
        )

        summary = await service.get_quick_summary(proposal_id)

        assert summary["title"] == "Quick Test"
        assert summary["sections"]["total"] == 1
        assert summary["sections"]["evaluated"] == 1


class TestDashboardIntegration:
    """Integration tests for dashboard service."""

    @pytest.fixture
    def service(self):
        return DashboardService()

    @pytest.mark.asyncio
    async def test_full_dashboard_workflow(self, service):
        """Test complete dashboard workflow."""
        proposal_id = "integration-test"
        user_id = "user-1"

        # 1. Set up proposal
        deadline = datetime.now() + timedelta(days=30)
        service.set_proposal_info(
            proposal_id=proposal_id,
            title="Integration Test Proposal",
            call_id="CALL-123",
            call_title="Test Call 2024",
            deadline=deadline,
        )

        # 2. Add multiple sections
        service.add_section(
            proposal_id=proposal_id,
            section_id="excellence",
            title="Excellence",
            section_type="excellence_objectives",
            content="Excellent content " * 500,
            score=4.2,
        )

        service.add_section(
            proposal_id=proposal_id,
            section_id="impact",
            title="Impact",
            section_type="impact_pathways",
            content="Impact content " * 300,
            score=3.5,
        )

        service.add_section(
            proposal_id=proposal_id,
            section_id="implementation",
            title="Implementation",
            section_type="implementation",
            content="",  # Not started
            score=None,
        )

        # 3. Get dashboard
        dashboard = await service.get_dashboard(proposal_id, user_id)

        # 4. Verify dashboard data
        assert dashboard.proposal_title == "Integration Test Proposal"
        assert dashboard.call_title == "Test Call 2024"
        assert len(dashboard.sections) == 3

        # Check section statuses
        statuses = {s.id: s.status for s in dashboard.sections}
        assert statuses["excellence"] == SectionStatus.EXCELLENT
        assert statuses["impact"] == SectionStatus.GOOD
        assert statuses["implementation"] == SectionStatus.NOT_STARTED

        # Check next actions
        assert len(dashboard.next_actions) > 0

        # Should have action for not_started section
        not_started_action = next(
            (a for a in dashboard.next_actions if a.section_id == "implementation"), None
        )
        assert not_started_action is not None
        assert not_started_action.priority == ActionPriority.CRITICAL

        # Check readiness
        assert dashboard.submission_ready is False  # Has not started section

        # Check sections by status
        assert dashboard.sections_by_status["excellent"] == 1
        assert dashboard.sections_by_status["good"] == 1
        assert dashboard.sections_by_status["not_started"] == 1
