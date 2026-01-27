"""
Tests for ProgressTrackingService (Task 15)

Tests progress tracking, achievements, and streaks.
"""

from datetime import date, datetime, timedelta

import pytest

from app.services.proposal_writing.progress_tracking_service import (
    Achievement,
    AchievementCategory,
    AchievementRarity,
    ProgressSnapshot,
    ProgressTrackingService,
    Streak,
    UserAchievement,
)


class TestAchievementCategory:
    """Tests for AchievementCategory enum."""

    def test_category_values(self):
        """Test all category values."""
        assert AchievementCategory.WRITING.value == "writing"
        assert AchievementCategory.QUALITY.value == "quality"
        assert AchievementCategory.CONSISTENCY.value == "consistency"
        assert AchievementCategory.MILESTONE.value == "milestone"
        assert AchievementCategory.MASTERY.value == "mastery"

    def test_category_count(self):
        """Test that we have all 5 categories."""
        assert len(AchievementCategory) == 5


class TestAchievementRarity:
    """Tests for AchievementRarity enum."""

    def test_rarity_values(self):
        """Test all rarity values."""
        assert AchievementRarity.COMMON.value == "common"
        assert AchievementRarity.UNCOMMON.value == "uncommon"
        assert AchievementRarity.RARE.value == "rare"
        assert AchievementRarity.EPIC.value == "epic"
        assert AchievementRarity.LEGENDARY.value == "legendary"

    def test_rarity_count(self):
        """Test that we have all 5 rarity levels."""
        assert len(AchievementRarity) == 5


class TestAchievement:
    """Tests for Achievement dataclass."""

    def test_create_achievement(self):
        """Test creating an achievement."""
        achievement = Achievement(
            id="test_achievement",
            name="Test Achievement",
            description="A test achievement",
            category=AchievementCategory.WRITING,
            rarity=AchievementRarity.COMMON,
            icon="T",
            points=10,
            criteria={"min_words": 100},
        )

        assert achievement.id == "test_achievement"
        assert achievement.name == "Test Achievement"
        assert achievement.category == AchievementCategory.WRITING
        assert achievement.rarity == AchievementRarity.COMMON
        assert achievement.points == 10
        assert achievement.criteria["min_words"] == 100


class TestProgressSnapshot:
    """Tests for ProgressSnapshot dataclass."""

    def test_create_progress_snapshot(self):
        """Test creating a progress snapshot."""
        snapshot = ProgressSnapshot(
            proposal_id="test-proposal",
            completion_percentage=50.0,
            sections_completed=3,
            total_sections=6,
            average_score=3.5,
            highest_score=4.2,
            lowest_score=2.8,
            gaps_resolved=5,
            total_gaps=10,
            suggestions_accepted=15,
            rewrites_applied=3,
            time_spent_minutes=120,
            last_activity=datetime.now(),
        )

        assert snapshot.proposal_id == "test-proposal"
        assert snapshot.completion_percentage == 50.0
        assert snapshot.sections_completed == 3
        assert snapshot.total_sections == 6
        assert snapshot.average_score == 3.5


class TestStreak:
    """Tests for Streak dataclass."""

    def test_create_streak(self):
        """Test creating a streak."""
        streak = Streak(
            current_streak=5, longest_streak=10, last_activity_date=date.today(), is_active=True
        )

        assert streak.current_streak == 5
        assert streak.longest_streak == 10
        assert streak.is_active is True

    def test_streak_with_none_date(self):
        """Test streak with None date."""
        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        assert streak.last_activity_date is None


class TestProgressTrackingService:
    """Tests for ProgressTrackingService."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        return ProgressTrackingService()

    def test_init(self, service):
        """Test service initialization."""
        assert len(service.ACHIEVEMENTS) > 0
        assert len(service._achievement_map) == len(service.ACHIEVEMENTS)

    def test_achievements_have_required_fields(self, service):
        """Test that all achievements have required fields."""
        for achievement in service.ACHIEVEMENTS:
            assert achievement.id, "Achievement missing id"
            assert achievement.name, "Achievement missing name"
            assert achievement.description, "Achievement missing description"
            assert achievement.category, "Achievement missing category"
            assert achievement.rarity, "Achievement missing rarity"
            assert achievement.icon, "Achievement missing icon"
            assert achievement.points > 0, "Achievement should have positive points"
            assert achievement.criteria, "Achievement missing criteria"

    def test_achievements_unique_ids(self, service):
        """Test that all achievement IDs are unique."""
        ids = [a.id for a in service.ACHIEVEMENTS]
        assert len(ids) == len(set(ids)), "Duplicate achievement IDs found"

    def test_achievement_categories_coverage(self, service):
        """Test that all categories are represented."""
        categories_used = {a.category for a in service.ACHIEVEMENTS}
        for category in AchievementCategory:
            assert category in categories_used, f"No achievements for category {category}"

    def test_achievement_rarities_coverage(self, service):
        """Test that multiple rarity levels are used."""
        rarities_used = {a.rarity for a in service.ACHIEVEMENTS}
        # Should have at least 3 different rarities
        assert len(rarities_used) >= 3

    # --- Progress Tests ---

    @pytest.mark.asyncio
    async def test_get_progress_default(self, service):
        """Test getting progress for a new proposal."""
        progress = await service.get_progress("new-proposal")

        assert progress.proposal_id == "new-proposal"
        assert progress.completion_percentage == 0.0
        assert progress.sections_completed == 0

    @pytest.mark.asyncio
    async def test_update_progress(self, service):
        """Test updating progress."""
        proposal_id = "test-proposal"

        # Initial update
        await service.update_progress(
            proposal_id=proposal_id, sections_completed=2, total_sections=4
        )

        progress = await service.get_progress(proposal_id)
        assert progress.sections_completed == 2
        assert progress.total_sections == 4
        assert progress.completion_percentage == 50.0

    @pytest.mark.asyncio
    async def test_update_progress_partial(self, service):
        """Test updating only some fields."""
        proposal_id = "test-proposal-2"

        # Set initial values
        await service.update_progress(
            proposal_id=proposal_id, sections_completed=1, total_sections=5, average_score=3.0
        )

        # Update only average_score
        await service.update_progress(proposal_id=proposal_id, average_score=3.5)

        progress = await service.get_progress(proposal_id)
        assert progress.sections_completed == 1  # Unchanged
        assert progress.average_score == 3.5  # Updated

    # --- Streak Tests ---

    @pytest.mark.asyncio
    async def test_get_streak_default(self, service):
        """Test getting streak for new user."""
        streak = await service.get_streak("new-user")

        assert streak.current_streak == 0
        assert streak.is_active is False
        assert streak.last_activity_date is None  # No activity yet

    @pytest.mark.asyncio
    async def test_record_activity_starts_streak(self, service):
        """Test that recording activity starts a streak."""
        user_id = "test-user-1"

        streak = await service.record_activity(user_id)

        assert streak.current_streak == 1
        assert streak.is_active is True
        assert streak.last_activity_date == date.today()

    @pytest.mark.asyncio
    async def test_record_activity_same_day(self, service):
        """Test recording activity multiple times same day."""
        user_id = "test-user-2"

        await service.record_activity(user_id)
        streak = await service.record_activity(user_id)

        # Should still be 1, not increment
        assert streak.current_streak == 1

    @pytest.mark.asyncio
    async def test_record_activity_continues_streak(self, service):
        """Test continuing a streak from yesterday."""
        user_id = "test-user-3"

        # Manually set up yesterday's activity
        yesterday = date.today() - timedelta(days=1)
        service._user_streaks_cache[user_id] = Streak(
            current_streak=3, longest_streak=3, last_activity_date=yesterday, is_active=True
        )

        streak = await service.record_activity(user_id)

        assert streak.current_streak == 4
        assert streak.longest_streak == 4

    @pytest.mark.asyncio
    async def test_record_activity_breaks_streak(self, service):
        """Test that missing a day breaks the streak."""
        user_id = "test-user-4"

        # Set up activity from 2 days ago
        two_days_ago = date.today() - timedelta(days=2)
        service._user_streaks_cache[user_id] = Streak(
            current_streak=5, longest_streak=5, last_activity_date=two_days_ago, is_active=True
        )

        streak = await service.record_activity(user_id)

        # Streak should reset to 1
        assert streak.current_streak == 1
        # But longest streak should be preserved
        assert streak.longest_streak == 5

    @pytest.mark.asyncio
    async def test_record_activity_future_date_edge_case(self, service):
        """Test that a future date edge case resets streak."""
        user_id = "test-user-future"

        # Manually set a future date (edge case that shouldn't happen normally)
        future_date = date.today() + timedelta(days=1)
        service._user_streaks_cache[user_id] = Streak(
            current_streak=10, longest_streak=10, last_activity_date=future_date, is_active=True
        )

        streak = await service.record_activity(user_id)

        # Streak should reset to 1 (future date is treated as invalid)
        assert streak.current_streak == 1
        assert streak.last_activity_date == date.today()

    # --- Update Progress All Parameters Tests ---

    @pytest.mark.asyncio
    async def test_update_progress_highest_score(self, service):
        """Test updating highest_score field."""
        proposal_id = "test-highest"

        await service.update_progress(proposal_id=proposal_id, highest_score=4.5)

        progress = await service.get_progress(proposal_id)
        assert progress.highest_score == 4.5

    @pytest.mark.asyncio
    async def test_update_progress_lowest_score(self, service):
        """Test updating lowest_score field."""
        proposal_id = "test-lowest"

        await service.update_progress(proposal_id=proposal_id, lowest_score=2.8)

        progress = await service.get_progress(proposal_id)
        assert progress.lowest_score == 2.8

    @pytest.mark.asyncio
    async def test_update_progress_gaps_resolved(self, service):
        """Test updating gaps_resolved field."""
        proposal_id = "test-gaps"

        await service.update_progress(proposal_id=proposal_id, gaps_resolved=5, total_gaps=10)

        progress = await service.get_progress(proposal_id)
        assert progress.gaps_resolved == 5
        assert progress.total_gaps == 10

    @pytest.mark.asyncio
    async def test_update_progress_suggestions_accepted(self, service):
        """Test updating suggestions_accepted field."""
        proposal_id = "test-suggestions"

        await service.update_progress(proposal_id=proposal_id, suggestions_accepted=15)

        progress = await service.get_progress(proposal_id)
        assert progress.suggestions_accepted == 15

    @pytest.mark.asyncio
    async def test_update_progress_rewrites_applied(self, service):
        """Test updating rewrites_applied field."""
        proposal_id = "test-rewrites"

        await service.update_progress(proposal_id=proposal_id, rewrites_applied=8)

        progress = await service.get_progress(proposal_id)
        assert progress.rewrites_applied == 8

    @pytest.mark.asyncio
    async def test_update_progress_time_spent_minutes(self, service):
        """Test updating time_spent_minutes field."""
        proposal_id = "test-time"

        await service.update_progress(proposal_id=proposal_id, time_spent_minutes=120)

        progress = await service.get_progress(proposal_id)
        assert progress.time_spent_minutes == 120

    @pytest.mark.asyncio
    async def test_update_progress_all_fields(self, service):
        """Test updating all fields at once."""
        proposal_id = "test-all-fields"

        await service.update_progress(
            proposal_id=proposal_id,
            sections_completed=3,
            total_sections=6,
            average_score=3.7,
            highest_score=4.5,
            lowest_score=2.9,
            gaps_resolved=8,
            total_gaps=12,
            suggestions_accepted=20,
            rewrites_applied=5,
            time_spent_minutes=180,
        )

        progress = await service.get_progress(proposal_id)
        assert progress.sections_completed == 3
        assert progress.total_sections == 6
        assert progress.average_score == 3.7
        assert progress.highest_score == 4.5
        assert progress.lowest_score == 2.9
        assert progress.gaps_resolved == 8
        assert progress.total_gaps == 12
        assert progress.suggestions_accepted == 20
        assert progress.rewrites_applied == 5
        assert progress.time_spent_minutes == 180
        assert progress.completion_percentage == 50.0

    # --- Achievement Criteria Tests ---

    def test_check_criteria_min_words(self, service):
        """Test checking min_words criteria."""
        achievement = Achievement(
            id="test",
            name="Test",
            description="Test",
            category=AchievementCategory.WRITING,
            rarity=AchievementRarity.COMMON,
            icon="T",
            points=10,
            criteria={"min_words": 100},
        )

        progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        # Below threshold
        assert not service._check_criteria(achievement, {"word_count": 50}, progress, streak)

        # At threshold
        assert service._check_criteria(achievement, {"word_count": 100}, progress, streak)

        # Above threshold
        assert service._check_criteria(achievement, {"word_count": 200}, progress, streak)

    def test_check_criteria_min_score(self, service):
        """Test checking min_score criteria."""
        achievement = Achievement(
            id="score_test",
            name="Score Test",
            description="Test",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.UNCOMMON,
            icon="S",
            points=20,
            criteria={"min_score": 4.0},
        )

        progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        # Below threshold
        assert not service._check_criteria(achievement, {"score": 3.5}, progress, streak)

        # At threshold
        assert service._check_criteria(achievement, {"score": 4.0}, progress, streak)

    def test_check_criteria_streak_days(self, service):
        """Test checking streak_days criteria."""
        achievement = Achievement(
            id="streak_test",
            name="Streak Test",
            description="Test",
            category=AchievementCategory.CONSISTENCY,
            rarity=AchievementRarity.UNCOMMON,
            icon="F",
            points=30,
            criteria={"streak_days": 7},
        )

        progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        low_streak = Streak(
            current_streak=3, longest_streak=3, last_activity_date=date.today(), is_active=True
        )

        high_streak = Streak(
            current_streak=7, longest_streak=7, last_activity_date=date.today(), is_active=True
        )

        assert not service._check_criteria(achievement, {}, progress, low_streak)
        assert service._check_criteria(achievement, {}, progress, high_streak)

    def test_check_criteria_completion_percentage(self, service):
        """Test checking completion_percentage criteria."""
        achievement = Achievement(
            id="completion_test",
            name="Completion Test",
            description="Test",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.UNCOMMON,
            icon="C",
            points=40,
            criteria={"completion_percentage": 50},
        )

        low_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=30.0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        high_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=50.0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        assert not service._check_criteria(achievement, {}, low_progress, streak)
        assert service._check_criteria(achievement, {}, high_progress, streak)

    def test_check_criteria_improvement(self, service):
        """Test checking score_improvement criteria."""
        achievement = Achievement(
            id="improvement_test",
            name="Improvement Test",
            description="Test",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.UNCOMMON,
            icon="I",
            points=30,
            criteria={"improvement": 1.0},
        )

        progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        # Below threshold
        assert not service._check_criteria(
            achievement, {"score_improvement": 0.5}, progress, streak
        )

        # At threshold
        assert service._check_criteria(achievement, {"score_improvement": 1.0}, progress, streak)

    def test_check_criteria_all_sections_min_score(self, service):
        """Test checking all_sections_min_score criteria."""
        achievement = Achievement(
            id="all_sections_test",
            name="All Sections Test",
            description="Test",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.EPIC,
            icon="A",
            points=100,
            criteria={"all_sections_min_score": 3.0},
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        # Progress with lowest score below threshold
        low_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=100,
            sections_completed=5,
            total_sections=5,
            average_score=3.5,
            highest_score=4.0,
            lowest_score=2.5,  # Below 3.0
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        # Progress with all sections above threshold
        high_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=100,
            sections_completed=5,
            total_sections=5,
            average_score=3.8,
            highest_score=4.5,
            lowest_score=3.2,  # Above 3.0
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        assert not service._check_criteria(achievement, {}, low_progress, streak)
        assert service._check_criteria(achievement, {}, high_progress, streak)

    def test_check_criteria_all_sections_min_score_with_none(self, service):
        """Test all_sections_min_score when lowest_score is None."""
        achievement = Achievement(
            id="all_sections_test",
            name="All Sections Test",
            description="Test",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.EPIC,
            icon="A",
            points=100,
            criteria={"all_sections_min_score": 3.0},
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        # Progress with no lowest score (sections not evaluated)
        progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=50,
            sections_completed=2,
            total_sections=4,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        # Should fail when lowest_score is None
        assert not service._check_criteria(achievement, {}, progress, streak)

    def test_check_criteria_gaps_resolved(self, service):
        """Test checking gaps_resolved criteria."""
        achievement = Achievement(
            id="gaps_test",
            name="Gaps Test",
            description="Test",
            category=AchievementCategory.MASTERY,
            rarity=AchievementRarity.UNCOMMON,
            icon="G",
            points=25,
            criteria={"gaps_resolved": 10},
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        low_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=50,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=5,
            total_gaps=15,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        high_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=50,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=12,
            total_gaps=15,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        assert not service._check_criteria(achievement, {}, low_progress, streak)
        assert service._check_criteria(achievement, {}, high_progress, streak)

    def test_check_criteria_suggestions_accepted(self, service):
        """Test checking suggestions_accepted criteria."""
        achievement = Achievement(
            id="suggestions_test",
            name="Suggestions Test",
            description="Test",
            category=AchievementCategory.MASTERY,
            rarity=AchievementRarity.UNCOMMON,
            icon="S",
            points=25,
            criteria={"suggestions_accepted": 25},
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        low_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=10,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        high_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=30,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        assert not service._check_criteria(achievement, {}, low_progress, streak)
        assert service._check_criteria(achievement, {}, high_progress, streak)

    def test_check_criteria_rewrites_applied(self, service):
        """Test checking rewrites_applied criteria."""
        achievement = Achievement(
            id="rewrites_test",
            name="Rewrites Test",
            description="Test",
            category=AchievementCategory.MASTERY,
            rarity=AchievementRarity.RARE,
            icon="R",
            points=50,
            criteria={"rewrites_applied": 10},
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        low_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=5,
            time_spent_minutes=0,
            last_activity=None,
        )

        high_progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=15,
            time_spent_minutes=0,
            last_activity=None,
        )

        assert not service._check_criteria(achievement, {}, low_progress, streak)
        assert service._check_criteria(achievement, {}, high_progress, streak)

    def test_check_criteria_total_words(self, service):
        """Test checking total_words criteria."""
        achievement = Achievement(
            id="total_words_test",
            name="Total Words Test",
            description="Test",
            category=AchievementCategory.WRITING,
            rarity=AchievementRarity.RARE,
            icon="W",
            points=75,
            criteria={"total_words": 10000},
        )

        progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=0,
            sections_completed=0,
            total_sections=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            gaps_resolved=0,
            total_gaps=0,
            suggestions_accepted=0,
            rewrites_applied=0,
            time_spent_minutes=0,
            last_activity=None,
        )

        streak = Streak(
            current_streak=0, longest_streak=0, last_activity_date=None, is_active=False
        )

        # Below threshold
        assert not service._check_criteria(achievement, {"total_words": 5000}, progress, streak)

        # At threshold
        assert service._check_criteria(achievement, {"total_words": 10000}, progress, streak)

    # --- Award Achievement Tests ---

    @pytest.mark.asyncio
    async def test_award_achievement(self, service):
        """Test awarding an achievement."""
        user_id = "test-user"
        achievement = service.ACHIEVEMENTS[0]
        context = {"test": "data"}

        user_achievement = await service._award_achievement(
            user_id=user_id, achievement=achievement, context=context
        )

        assert user_achievement.achievement_id == achievement.id
        assert user_achievement.achievement == achievement
        assert user_achievement.context == context
        assert user_achievement.earned_at is not None

    @pytest.mark.asyncio
    async def test_get_user_achievements(self, service):
        """Test getting user achievements."""
        user_id = "test-user-achievements"

        # Should be empty initially
        achievements = await service._get_user_achievements(user_id)
        assert len(achievements) == 0

        # Award one
        await service._award_achievement(
            user_id=user_id, achievement=service.ACHIEVEMENTS[0], context={}
        )

        # Now should have one
        achievements = await service._get_user_achievements(user_id)
        assert len(achievements) == 1

    # --- Check Achievements Tests ---

    @pytest.mark.asyncio
    async def test_check_achievements_first_words(self, service):
        """Test earning 'First Words' achievement."""
        user_id = "test-checker"
        proposal_id = "test-proposal"

        # Set up progress
        await service.update_progress(
            proposal_id=proposal_id, sections_completed=0, total_sections=5
        )

        # Check with 100 words - should earn first_draft
        new_achievements = await service.check_achievements(
            user_id=user_id, proposal_id=proposal_id, context={"word_count": 100}
        )

        achievement_ids = [a.achievement_id for a in new_achievements]
        assert "first_draft" in achievement_ids

    @pytest.mark.asyncio
    async def test_check_achievements_no_duplicates(self, service):
        """Test that achievements aren't awarded twice."""
        user_id = "test-no-dupes"
        proposal_id = "test-proposal"

        await service.update_progress(
            proposal_id=proposal_id, sections_completed=0, total_sections=5
        )

        context = {"word_count": 100}

        # First check - should get achievement
        first_check = await service.check_achievements(
            user_id=user_id, proposal_id=proposal_id, context=context
        )
        first_count = len(first_check)

        # Second check - should not get same achievement again
        second_check = await service.check_achievements(
            user_id=user_id, proposal_id=proposal_id, context=context
        )

        # Should get fewer (or zero) new achievements
        assert len(second_check) < first_count or first_count == 0

    # --- Get All Achievements Tests ---

    @pytest.mark.asyncio
    async def test_get_all_achievements(self, service):
        """Test getting all achievements."""
        achievements = await service.get_all_achievements()

        assert len(achievements) == len(service.ACHIEVEMENTS)
        for ach in achievements:
            assert "id" in ach
            assert "name" in ach
            assert "description" in ach
            assert "category" in ach
            assert "rarity" in ach
            assert "points" in ach

    @pytest.mark.asyncio
    async def test_get_all_achievements_with_user(self, service):
        """Test getting all achievements with user earned status."""
        user_id = "test-user-all"

        # Award one achievement
        await service._award_achievement(
            user_id=user_id, achievement=service.ACHIEVEMENTS[0], context={}
        )

        achievements = await service.get_all_achievements(user_id)

        earned_count = sum(1 for a in achievements if a.get("earned"))
        assert earned_count == 1

    # --- Total Points Tests ---

    def test_get_total_points_empty(self, service):
        """Test total points with no achievements."""
        points = service.get_total_points([])
        assert points == 0

    def test_get_total_points_single(self, service):
        """Test total points with one achievement."""
        achievement = service.ACHIEVEMENTS[0]
        user_achievement = UserAchievement(
            achievement_id=achievement.id,
            achievement=achievement,
            earned_at=datetime.now(),
            context={},
        )

        points = service.get_total_points([user_achievement])
        assert points == achievement.points

    def test_get_total_points_multiple(self, service):
        """Test total points with multiple achievements."""
        user_achievements = []
        expected_total = 0

        for ach in service.ACHIEVEMENTS[:3]:
            user_achievements.append(
                UserAchievement(
                    achievement_id=ach.id, achievement=ach, earned_at=datetime.now(), context={}
                )
            )
            expected_total += ach.points

        points = service.get_total_points(user_achievements)
        assert points == expected_total


class TestSpecificAchievements:
    """Tests for specific achievement types."""

    @pytest.fixture
    def service(self):
        return ProgressTrackingService()

    def test_first_draft_achievement_exists(self, service):
        """Test that first_draft achievement exists."""
        achievement = service._achievement_map.get("first_draft")
        assert achievement is not None
        assert achievement.criteria["min_words"] == 100

    def test_threshold_reached_achievement(self, service):
        """Test threshold_reached achievement."""
        achievement = service._achievement_map.get("threshold_reached")
        assert achievement is not None
        assert achievement.criteria["min_score"] == 3.0

    def test_competitive_section_achievement(self, service):
        """Test competitive_section achievement."""
        achievement = service._achievement_map.get("competitive_section")
        assert achievement is not None
        assert achievement.criteria["min_score"] == 4.0

    def test_perfect_score_achievement(self, service):
        """Test perfect_score achievement is legendary."""
        achievement = service._achievement_map.get("perfect_score")
        assert achievement is not None
        assert achievement.rarity == AchievementRarity.LEGENDARY
        assert achievement.criteria["min_score"] == 5.0

    def test_streak_achievements(self, service):
        """Test streak achievements are progressive."""
        streak_3 = service._achievement_map.get("streak_3")
        streak_7 = service._achievement_map.get("streak_7")
        streak_14 = service._achievement_map.get("streak_14")

        assert streak_3.criteria["streak_days"] == 3
        assert streak_7.criteria["streak_days"] == 7
        assert streak_14.criteria["streak_days"] == 14

        # Points should increase
        assert streak_3.points < streak_7.points < streak_14.points

    def test_proposal_complete_achievement(self, service):
        """Test proposal_complete achievement."""
        achievement = service._achievement_map.get("proposal_complete")
        assert achievement is not None
        assert achievement.rarity == AchievementRarity.EPIC
        assert achievement.criteria["completion_percentage"] == 100
