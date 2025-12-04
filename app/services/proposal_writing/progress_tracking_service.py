"""
Progress Tracking Service

Tracks user progress through proposal writing, awards achievements,
and provides motivation through gamification elements.
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum

logger = logging.getLogger(__name__)


class AchievementCategory(str, Enum):
    """Categories of achievements."""
    WRITING = "writing"           # Content creation
    QUALITY = "quality"           # Score improvements
    CONSISTENCY = "consistency"   # Streaks and habits
    MILESTONE = "milestone"       # Major progress points
    MASTERY = "mastery"           # Expert-level accomplishments


class AchievementRarity(str, Enum):
    """Rarity levels for achievements."""
    COMMON = "common"         # Easy to get
    UNCOMMON = "uncommon"     # Moderate effort
    RARE = "rare"             # Significant accomplishment
    EPIC = "epic"             # Major milestone
    LEGENDARY = "legendary"   # Exceptional achievement


@dataclass
class Achievement:
    """Definition of an achievement."""
    id: str
    name: str
    description: str
    category: AchievementCategory
    rarity: AchievementRarity
    icon: str
    points: int
    criteria: Dict[str, Any]


@dataclass
class UserAchievement:
    """A user's earned achievement."""
    achievement_id: str
    achievement: Achievement
    earned_at: datetime
    context: Dict[str, Any]  # e.g., which proposal, what score


@dataclass
class ProgressSnapshot:
    """Snapshot of proposal progress."""
    proposal_id: str
    completion_percentage: float
    sections_completed: int
    total_sections: int
    average_score: Optional[float]
    highest_score: Optional[float]
    lowest_score: Optional[float]
    gaps_resolved: int
    total_gaps: int
    suggestions_accepted: int
    rewrites_applied: int
    time_spent_minutes: int
    last_activity: Optional[datetime]


@dataclass
class Streak:
    """User writing streak."""
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[date]
    is_active: bool


class ProgressTrackingService:
    """
    Service for tracking proposal writing progress and awarding achievements.

    Provides gamification elements to motivate users through the
    proposal writing process.
    """

    # Achievement definitions
    ACHIEVEMENTS = [
        # Writing achievements
        Achievement(
            id="first_draft",
            name="First Words",
            description="Write your first 100 words",
            category=AchievementCategory.WRITING,
            rarity=AchievementRarity.COMMON,
            icon="W",
            points=10,
            criteria={"min_words": 100}
        ),
        Achievement(
            id="page_turner",
            name="Page Turner",
            description="Write 1,000 words in a single section",
            category=AchievementCategory.WRITING,
            rarity=AchievementRarity.UNCOMMON,
            icon="P",
            points=25,
            criteria={"min_words": 1000}
        ),
        Achievement(
            id="prolific_writer",
            name="Prolific Writer",
            description="Write 10,000 total words across all sections",
            category=AchievementCategory.WRITING,
            rarity=AchievementRarity.RARE,
            icon="B",
            points=100,
            criteria={"total_words": 10000}
        ),

        # Quality achievements
        Achievement(
            id="threshold_reached",
            name="Over the Bar",
            description="Get a section to score 3.0 (funding threshold)",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.COMMON,
            icon="C",
            points=20,
            criteria={"min_score": 3.0}
        ),
        Achievement(
            id="competitive_section",
            name="Competitive Edge",
            description="Get a section to score 4.0+",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.UNCOMMON,
            icon="S",
            points=50,
            criteria={"min_score": 4.0}
        ),
        Achievement(
            id="excellence_achieved",
            name="Excellence Achieved",
            description="Get a section to score 4.5+",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.RARE,
            icon="T",
            points=100,
            criteria={"min_score": 4.5}
        ),
        Achievement(
            id="perfect_score",
            name="Perfect Score",
            description="Achieve a 5.0 score on any section",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.LEGENDARY,
            icon="D",
            points=500,
            criteria={"min_score": 5.0}
        ),
        Achievement(
            id="score_improver",
            name="Rising Star",
            description="Improve a section score by 1.0 points",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.UNCOMMON,
            icon="U",
            points=30,
            criteria={"improvement": 1.0}
        ),

        # Consistency achievements
        Achievement(
            id="streak_3",
            name="Getting Started",
            description="Work on your proposal 3 days in a row",
            category=AchievementCategory.CONSISTENCY,
            rarity=AchievementRarity.COMMON,
            icon="F",
            points=15,
            criteria={"streak_days": 3}
        ),
        Achievement(
            id="streak_7",
            name="Dedicated Writer",
            description="Work on your proposal 7 days in a row",
            category=AchievementCategory.CONSISTENCY,
            rarity=AchievementRarity.UNCOMMON,
            icon="FF",
            points=50,
            criteria={"streak_days": 7}
        ),
        Achievement(
            id="streak_14",
            name="Unstoppable",
            description="Work on your proposal 14 days in a row",
            category=AchievementCategory.CONSISTENCY,
            rarity=AchievementRarity.RARE,
            icon="FFF",
            points=150,
            criteria={"streak_days": 14}
        ),

        # Milestone achievements
        Achievement(
            id="section_complete",
            name="Section Complete",
            description="Complete your first section",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.COMMON,
            icon="V",
            points=20,
            criteria={"sections_completed": 1}
        ),
        Achievement(
            id="halfway_there",
            name="Halfway There",
            description="Complete 50% of your proposal",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.UNCOMMON,
            icon="G",
            points=75,
            criteria={"completion_percentage": 50}
        ),
        Achievement(
            id="proposal_complete",
            name="Proposal Complete",
            description="Complete all sections of your proposal",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.EPIC,
            icon="Y",
            points=200,
            criteria={"completion_percentage": 100}
        ),
        Achievement(
            id="all_above_threshold",
            name="All Systems Go",
            description="Get all sections above the funding threshold",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.EPIC,
            icon="R",
            points=250,
            criteria={"all_sections_min_score": 3.0}
        ),

        # Mastery achievements
        Achievement(
            id="gap_closer",
            name="Gap Closer",
            description="Resolve 10 identified gaps",
            category=AchievementCategory.MASTERY,
            rarity=AchievementRarity.UNCOMMON,
            icon="X",
            points=40,
            criteria={"gaps_resolved": 10}
        ),
        Achievement(
            id="suggestion_adopter",
            name="Open to Feedback",
            description="Accept 25 AI suggestions",
            category=AchievementCategory.MASTERY,
            rarity=AchievementRarity.UNCOMMON,
            icon="L",
            points=35,
            criteria={"suggestions_accepted": 25}
        ),
        Achievement(
            id="rewrite_master",
            name="Rewrite Master",
            description="Apply 10 AI-generated rewrites",
            category=AchievementCategory.MASTERY,
            rarity=AchievementRarity.RARE,
            icon="M",
            points=75,
            criteria={"rewrites_applied": 10}
        ),
    ]

    def __init__(self):
        self._achievement_map = {a.id: a for a in self.ACHIEVEMENTS}
        self._user_achievements_cache: Dict[str, List[UserAchievement]] = {}
        self._user_streaks_cache: Dict[str, Streak] = {}
        self._progress_cache: Dict[str, ProgressSnapshot] = {}

    async def get_progress(self, proposal_id: str) -> ProgressSnapshot:
        """Get current progress snapshot for a proposal."""
        # Check cache first
        if proposal_id in self._progress_cache:
            return self._progress_cache[proposal_id]

        # Return a default progress snapshot
        # In a real implementation, this would query the database
        progress = ProgressSnapshot(
            proposal_id=proposal_id,
            completion_percentage=0.0,
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
            last_activity=datetime.now()
        )

        self._progress_cache[proposal_id] = progress
        return progress

    async def update_progress(
        self,
        proposal_id: str,
        sections_completed: Optional[int] = None,
        total_sections: Optional[int] = None,
        average_score: Optional[float] = None,
        highest_score: Optional[float] = None,
        lowest_score: Optional[float] = None,
        gaps_resolved: Optional[int] = None,
        total_gaps: Optional[int] = None,
        suggestions_accepted: Optional[int] = None,
        rewrites_applied: Optional[int] = None,
        time_spent_minutes: Optional[int] = None
    ) -> ProgressSnapshot:
        """Update progress for a proposal."""
        current = await self.get_progress(proposal_id)

        # Update provided fields
        if sections_completed is not None:
            current.sections_completed = sections_completed
        if total_sections is not None:
            current.total_sections = total_sections
        if average_score is not None:
            current.average_score = average_score
        if highest_score is not None:
            current.highest_score = highest_score
        if lowest_score is not None:
            current.lowest_score = lowest_score
        if gaps_resolved is not None:
            current.gaps_resolved = gaps_resolved
        if total_gaps is not None:
            current.total_gaps = total_gaps
        if suggestions_accepted is not None:
            current.suggestions_accepted = suggestions_accepted
        if rewrites_applied is not None:
            current.rewrites_applied = rewrites_applied
        if time_spent_minutes is not None:
            current.time_spent_minutes = time_spent_minutes

        # Recalculate completion percentage
        if current.total_sections > 0:
            current.completion_percentage = (current.sections_completed / current.total_sections) * 100

        current.last_activity = datetime.now()
        self._progress_cache[proposal_id] = current

        return current

    async def get_streak(self, user_id: str) -> Streak:
        """Get user's current writing streak."""
        # Check cache first
        if user_id in self._user_streaks_cache:
            return self._user_streaks_cache[user_id]

        # Return default streak
        streak = Streak(
            current_streak=0,
            longest_streak=0,
            last_activity_date=date.today(),
            is_active=False
        )

        self._user_streaks_cache[user_id] = streak
        return streak

    async def record_activity(self, user_id: str) -> Streak:
        """Record user activity and update streak."""
        current_streak = await self.get_streak(user_id)
        today = date.today()
        yesterday = today - timedelta(days=1)

        if current_streak.last_activity_date == today:
            # Already recorded today
            return current_streak

        if current_streak.last_activity_date == yesterday:
            # Continue streak
            current_streak.current_streak += 1
        elif current_streak.last_activity_date and current_streak.last_activity_date < yesterday:
            # Streak broken, start new one
            current_streak.current_streak = 1
        else:
            # First activity
            current_streak.current_streak = 1

        current_streak.last_activity_date = today
        current_streak.is_active = True

        # Update longest streak if needed
        if current_streak.current_streak > current_streak.longest_streak:
            current_streak.longest_streak = current_streak.current_streak

        self._user_streaks_cache[user_id] = current_streak
        return current_streak

    async def check_achievements(
        self,
        user_id: str,
        proposal_id: str,
        context: Dict[str, Any]
    ) -> List[UserAchievement]:
        """
        Check if any new achievements have been earned.

        Args:
            user_id: The user ID
            proposal_id: The proposal ID
            context: Current context (scores, word counts, etc.)

        Returns:
            List of newly earned achievements
        """
        earned = []

        # Get user's existing achievements
        existing = await self._get_user_achievements(user_id)
        existing_ids = {a.achievement_id for a in existing}

        # Get progress data
        progress = await self.get_progress(proposal_id)
        streak = await self.get_streak(user_id)

        # Check each achievement
        for achievement in self.ACHIEVEMENTS:
            if achievement.id in existing_ids:
                continue

            if self._check_criteria(achievement, context, progress, streak):
                # Award achievement
                user_achievement = await self._award_achievement(
                    user_id=user_id,
                    achievement=achievement,
                    context=context
                )
                earned.append(user_achievement)

        return earned

    def _check_criteria(
        self,
        achievement: Achievement,
        context: Dict[str, Any],
        progress: ProgressSnapshot,
        streak: Streak
    ) -> bool:
        """Check if achievement criteria are met."""
        criteria = achievement.criteria

        # Writing criteria
        if "min_words" in criteria:
            if context.get("word_count", 0) < criteria["min_words"]:
                return False

        if "total_words" in criteria:
            if context.get("total_words", 0) < criteria["total_words"]:
                return False

        # Quality criteria
        if "min_score" in criteria:
            if context.get("score", 0) < criteria["min_score"]:
                return False

        if "improvement" in criteria:
            if context.get("score_improvement", 0) < criteria["improvement"]:
                return False

        # Consistency criteria
        if "streak_days" in criteria:
            if streak.current_streak < criteria["streak_days"]:
                return False

        # Milestone criteria
        if "sections_completed" in criteria:
            if progress.sections_completed < criteria["sections_completed"]:
                return False

        if "completion_percentage" in criteria:
            if progress.completion_percentage < criteria["completion_percentage"]:
                return False

        if "all_sections_min_score" in criteria:
            if progress.lowest_score is None or progress.lowest_score < criteria["all_sections_min_score"]:
                return False

        # Mastery criteria
        if "gaps_resolved" in criteria:
            if progress.gaps_resolved < criteria["gaps_resolved"]:
                return False

        if "suggestions_accepted" in criteria:
            if progress.suggestions_accepted < criteria["suggestions_accepted"]:
                return False

        if "rewrites_applied" in criteria:
            if progress.rewrites_applied < criteria["rewrites_applied"]:
                return False

        return True

    async def _award_achievement(
        self,
        user_id: str,
        achievement: Achievement,
        context: Dict[str, Any]
    ) -> UserAchievement:
        """Award an achievement to a user."""
        user_achievement = UserAchievement(
            achievement_id=achievement.id,
            achievement=achievement,
            earned_at=datetime.now(),
            context=context
        )

        # Add to cache
        if user_id not in self._user_achievements_cache:
            self._user_achievements_cache[user_id] = []
        self._user_achievements_cache[user_id].append(user_achievement)

        logger.info(f"User {user_id} earned achievement: {achievement.name}")

        return user_achievement

    async def _get_user_achievements(self, user_id: str) -> List[UserAchievement]:
        """Get all achievements for a user."""
        if user_id in self._user_achievements_cache:
            return self._user_achievements_cache[user_id]

        # Return empty list (in real implementation, would query database)
        self._user_achievements_cache[user_id] = []
        return []

    async def get_all_achievements(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all achievements, optionally with user's earned status."""
        earned_ids = set()
        if user_id:
            earned = await self._get_user_achievements(user_id)
            earned_ids = {a.achievement_id for a in earned}

        return [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "category": a.category.value,
                "rarity": a.rarity.value,
                "icon": a.icon,
                "points": a.points,
                "earned": a.id in earned_ids
            }
            for a in self.ACHIEVEMENTS
        ]

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get achievement leaderboard."""
        # In a real implementation, this would query the database
        # For now, return empty leaderboard
        return []

    def get_total_points(self, achievements: List[UserAchievement]) -> int:
        """Calculate total points from achievements."""
        return sum(a.achievement.points for a in achievements)
