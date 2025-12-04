# Task 15: Progress Tracking & Achievements

> **Priority:** P2 (User Experience)
> **Estimated Effort:** 4-6 hours
> **Dependencies:** Task 09 (Score Integration), Task 10 (Gap Analysis)
> **Status:** Not Started

---

## Problem Statement

Writing a proposal is a long journey. Users need motivation and visibility into their progress. Currently there's no gamification, no milestones, and no sense of accomplishment.

### Current State
- No progress visualization
- No milestones or achievements
- No motivation mechanics
- Users don't know "how far along" they are

### Target State
- Visual progress tracker for entire proposal
- Achievement system with badges
- Streak tracking for consistent work
- Score improvement history
- Comparison to successful proposals

---

## Implementation Plan

### Step 1: Progress Tracking Service

**File:** `app/services/proposal_writing/progress_tracking_service.py`

```python
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

from app.services.database import get_db_connection

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
    last_activity: datetime


@dataclass
class Streak:
    """User writing streak."""
    current_streak: int
    longest_streak: int
    last_activity_date: date
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
            icon="✍️",
            points=10,
            criteria={"min_words": 100}
        ),
        Achievement(
            id="page_turner",
            name="Page Turner",
            description="Write 1,000 words in a single section",
            category=AchievementCategory.WRITING,
            rarity=AchievementRarity.UNCOMMON,
            icon="📄",
            points=25,
            criteria={"min_words": 1000}
        ),
        Achievement(
            id="prolific_writer",
            name="Prolific Writer",
            description="Write 10,000 total words across all sections",
            category=AchievementCategory.WRITING,
            rarity=AchievementRarity.RARE,
            icon="📚",
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
            icon="📊",
            points=20,
            criteria={"min_score": 3.0}
        ),
        Achievement(
            id="competitive_section",
            name="Competitive Edge",
            description="Get a section to score 4.0+",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.UNCOMMON,
            icon="⭐",
            points=50,
            criteria={"min_score": 4.0}
        ),
        Achievement(
            id="excellence_achieved",
            name="Excellence Achieved",
            description="Get a section to score 4.5+",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.RARE,
            icon="🏆",
            points=100,
            criteria={"min_score": 4.5}
        ),
        Achievement(
            id="perfect_score",
            name="Perfect Score",
            description="Achieve a 5.0 score on any section",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.LEGENDARY,
            icon="💎",
            points=500,
            criteria={"min_score": 5.0}
        ),
        Achievement(
            id="score_improver",
            name="Rising Star",
            description="Improve a section score by 1.0 points",
            category=AchievementCategory.QUALITY,
            rarity=AchievementRarity.UNCOMMON,
            icon="📈",
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
            icon="🔥",
            points=15,
            criteria={"streak_days": 3}
        ),
        Achievement(
            id="streak_7",
            name="Dedicated Writer",
            description="Work on your proposal 7 days in a row",
            category=AchievementCategory.CONSISTENCY,
            rarity=AchievementRarity.UNCOMMON,
            icon="🔥🔥",
            points=50,
            criteria={"streak_days": 7}
        ),
        Achievement(
            id="streak_14",
            name="Unstoppable",
            description="Work on your proposal 14 days in a row",
            category=AchievementCategory.CONSISTENCY,
            rarity=AchievementRarity.RARE,
            icon="🔥🔥🔥",
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
            icon="✅",
            points=20,
            criteria={"sections_completed": 1}
        ),
        Achievement(
            id="halfway_there",
            name="Halfway There",
            description="Complete 50% of your proposal",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.UNCOMMON,
            icon="🎯",
            points=75,
            criteria={"completion_percentage": 50}
        ),
        Achievement(
            id="proposal_complete",
            name="Proposal Complete",
            description="Complete all sections of your proposal",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.EPIC,
            icon="🎉",
            points=200,
            criteria={"completion_percentage": 100}
        ),
        Achievement(
            id="all_above_threshold",
            name="All Systems Go",
            description="Get all sections above the funding threshold",
            category=AchievementCategory.MILESTONE,
            rarity=AchievementRarity.EPIC,
            icon="🚀",
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
            icon="🔧",
            points=40,
            criteria={"gaps_resolved": 10}
        ),
        Achievement(
            id="suggestion_adopter",
            name="Open to Feedback",
            description="Accept 25 AI suggestions",
            category=AchievementCategory.MASTERY,
            rarity=AchievementRarity.UNCOMMON,
            icon="💡",
            points=35,
            criteria={"suggestions_accepted": 25}
        ),
        Achievement(
            id="rewrite_master",
            name="Rewrite Master",
            description="Apply 10 AI-generated rewrites",
            category=AchievementCategory.MASTERY,
            rarity=AchievementRarity.RARE,
            icon="✨",
            points=75,
            criteria={"rewrites_applied": 10}
        ),
    ]

    def __init__(self):
        self._achievement_map = {a.id: a for a in self.ACHIEVEMENTS}

    async def get_progress(self, proposal_id: str) -> ProgressSnapshot:
        """Get current progress snapshot for a proposal."""
        async with get_db_connection() as conn:
            # Get section stats
            section_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_sections,
                    COUNT(*) FILTER (WHERE ss.predicted_score >= 3.0) as completed_sections,
                    AVG(ss.predicted_score) as avg_score,
                    MAX(ss.predicted_score) as max_score,
                    MIN(ss.predicted_score) as min_score
                FROM proposal_sections ps
                LEFT JOIN section_scores ss ON ps.id = ss.section_id
                WHERE ps.proposal_id = $1
            """, proposal_id)

            # Get gap stats
            gap_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_gaps,
                    COUNT(*) FILTER (WHERE resolved) as resolved_gaps
                FROM gap_tracking gt
                JOIN proposal_sections ps ON gt.section_id = ps.id
                WHERE ps.proposal_id = $1
            """, proposal_id)

            # Get suggestion stats
            suggestion_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE action = 'accepted') as accepted
                FROM suggestion_analytics sa
                JOIN proposal_sections ps ON sa.section_id = ps.id
                WHERE ps.proposal_id = $1
            """, proposal_id)

            # Get rewrite stats
            rewrite_stats = await conn.fetchrow("""
                SELECT COUNT(*) as applied
                FROM rewrite_sessions rs
                WHERE rs.section_id IN (
                    SELECT id FROM proposal_sections WHERE proposal_id = $1
                )
                AND rs.applied_option_id IS NOT NULL
            """, proposal_id)

            # Get time spent (from activity log)
            time_spent = await conn.fetchval("""
                SELECT COALESCE(SUM(duration_seconds) / 60, 0)
                FROM activity_log
                WHERE proposal_id = $1
            """, proposal_id)

            # Get last activity
            last_activity = await conn.fetchval("""
                SELECT MAX(created_at)
                FROM activity_log
                WHERE proposal_id = $1
            """, proposal_id)

            total = section_stats['total_sections'] or 0
            completed = section_stats['completed_sections'] or 0
            completion = (completed / total * 100) if total > 0 else 0

            return ProgressSnapshot(
                proposal_id=proposal_id,
                completion_percentage=completion,
                sections_completed=completed,
                total_sections=total,
                average_score=float(section_stats['avg_score']) if section_stats['avg_score'] else None,
                highest_score=float(section_stats['max_score']) if section_stats['max_score'] else None,
                lowest_score=float(section_stats['min_score']) if section_stats['min_score'] else None,
                gaps_resolved=gap_stats['resolved_gaps'] or 0,
                total_gaps=gap_stats['total_gaps'] or 0,
                suggestions_accepted=suggestion_stats['accepted'] or 0,
                rewrites_applied=rewrite_stats['applied'] or 0,
                time_spent_minutes=time_spent or 0,
                last_activity=last_activity or datetime.now()
            )

    async def get_streak(self, user_id: str) -> Streak:
        """Get user's current writing streak."""
        async with get_db_connection() as conn:
            # Get activity dates
            dates = await conn.fetch("""
                SELECT DISTINCT DATE(created_at) as activity_date
                FROM activity_log
                WHERE user_id = $1
                ORDER BY activity_date DESC
                LIMIT 30
            """, user_id)

            if not dates:
                return Streak(
                    current_streak=0,
                    longest_streak=0,
                    last_activity_date=date.today(),
                    is_active=False
                )

            activity_dates = [d['activity_date'] for d in dates]
            today = date.today()
            yesterday = today - timedelta(days=1)

            # Check if streak is active (today or yesterday)
            is_active = activity_dates[0] >= yesterday

            # Calculate current streak
            current_streak = 0
            expected_date = today if activity_dates[0] == today else yesterday

            for d in activity_dates:
                if d == expected_date:
                    current_streak += 1
                    expected_date -= timedelta(days=1)
                else:
                    break

            # Get longest streak from database
            longest = await conn.fetchval("""
                SELECT COALESCE(MAX(streak_length), 0)
                FROM user_streaks
                WHERE user_id = $1
            """, user_id) or current_streak

            return Streak(
                current_streak=current_streak if is_active else 0,
                longest_streak=max(longest, current_streak),
                last_activity_date=activity_dates[0],
                is_active=is_active
            )

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
        async with get_db_connection() as conn:
            await conn.execute("""
                INSERT INTO user_achievements (user_id, achievement_id, context, earned_at)
                VALUES ($1, $2, $3, NOW())
            """, user_id, achievement.id, context)

        return UserAchievement(
            achievement_id=achievement.id,
            achievement=achievement,
            earned_at=datetime.now(),
            context=context
        )

    async def _get_user_achievements(self, user_id: str) -> List[UserAchievement]:
        """Get all achievements for a user."""
        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT achievement_id, context, earned_at
                FROM user_achievements
                WHERE user_id = $1
                ORDER BY earned_at DESC
            """, user_id)

            return [
                UserAchievement(
                    achievement_id=row['achievement_id'],
                    achievement=self._achievement_map.get(row['achievement_id']),
                    earned_at=row['earned_at'],
                    context=row['context'] or {}
                )
                for row in rows
                if row['achievement_id'] in self._achievement_map
            ]

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get achievement leaderboard."""
        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT
                    u.id as user_id,
                    u.name as user_name,
                    COUNT(ua.id) as achievement_count,
                    SUM(
                        CASE
                            WHEN ua.achievement_id IN ('perfect_score', 'proposal_complete', 'all_above_threshold')
                            THEN 1 ELSE 0
                        END
                    ) as epic_achievements
                FROM users u
                JOIN user_achievements ua ON u.id = ua.user_id
                GROUP BY u.id, u.name
                ORDER BY achievement_count DESC, epic_achievements DESC
                LIMIT $1
            """, limit)

            return [
                {
                    "user_id": row['user_id'],
                    "user_name": row['user_name'],
                    "achievement_count": row['achievement_count'],
                    "epic_achievements": row['epic_achievements']
                }
                for row in rows
            ]
```

### Step 2: Database Schema

**File:** `migration/015_progress_tracking.sql`

```sql
-- Progress tracking and achievements schema

-- Activity log for tracking time spent
CREATE TABLE IF NOT EXISTS activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    proposal_id UUID REFERENCES proposals(id),
    section_id UUID REFERENCES proposal_sections(id),

    activity_type VARCHAR(50) NOT NULL,  -- edit, evaluate, rewrite, etc.
    duration_seconds INT DEFAULT 0,
    metadata JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

-- User achievements
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    achievement_id VARCHAR(50) NOT NULL,
    context JSONB,
    earned_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, achievement_id)
);

-- User streaks
CREATE TABLE IF NOT EXISTS user_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    streak_length INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_activity_log_user ON activity_log(user_id);
CREATE INDEX idx_activity_log_proposal ON activity_log(proposal_id);
CREATE INDEX idx_activity_log_created ON activity_log(created_at);
CREATE INDEX idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX idx_user_streaks_user ON user_streaks(user_id);

-- View for user progress summary
CREATE OR REPLACE VIEW v_user_progress AS
SELECT
    u.id as user_id,
    COUNT(DISTINCT p.id) as proposals_count,
    COUNT(DISTINCT ua.achievement_id) as achievements_count,
    COALESCE(SUM(al.duration_seconds) / 3600, 0) as total_hours,
    MAX(al.created_at) as last_activity
FROM users u
LEFT JOIN proposals p ON u.id = p.user_id
LEFT JOIN user_achievements ua ON u.id = ua.user_id
LEFT JOIN activity_log al ON u.id = al.user_id
GROUP BY u.id;

-- Function to log activity
CREATE OR REPLACE FUNCTION log_activity(
    p_user_id UUID,
    p_proposal_id UUID,
    p_section_id UUID,
    p_activity_type VARCHAR,
    p_duration_seconds INT,
    p_metadata JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    activity_id UUID;
BEGIN
    INSERT INTO activity_log (user_id, proposal_id, section_id, activity_type, duration_seconds, metadata)
    VALUES (p_user_id, p_proposal_id, p_section_id, p_activity_type, p_duration_seconds, p_metadata)
    RETURNING id INTO activity_id;

    RETURN activity_id;
END;
$$ LANGUAGE plpgsql;
```

### Step 3: API Endpoints

**File:** `app/api/progress_routes.py`

```python
"""
API routes for progress tracking and achievements.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import date

from app.services.proposal_writing.progress_tracking_service import (
    ProgressTrackingService
)

router = APIRouter(prefix="/api/proposal/progress", tags=["progress"])


class ProgressResponse(BaseModel):
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


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_activity_date: str
    is_active: bool


class AchievementResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    rarity: str
    icon: str
    points: int
    earned_at: Optional[str]


class CheckAchievementsRequest(BaseModel):
    user_id: str
    proposal_id: str
    word_count: Optional[int] = 0
    total_words: Optional[int] = 0
    score: Optional[float] = None
    score_improvement: Optional[float] = 0


@router.get("/proposal/{proposal_id}", response_model=ProgressResponse)
async def get_proposal_progress(proposal_id: str):
    """Get progress snapshot for a proposal."""
    service = ProgressTrackingService()

    progress = await service.get_progress(proposal_id)

    return ProgressResponse(
        completion_percentage=progress.completion_percentage,
        sections_completed=progress.sections_completed,
        total_sections=progress.total_sections,
        average_score=progress.average_score,
        highest_score=progress.highest_score,
        lowest_score=progress.lowest_score,
        gaps_resolved=progress.gaps_resolved,
        total_gaps=progress.total_gaps,
        suggestions_accepted=progress.suggestions_accepted,
        rewrites_applied=progress.rewrites_applied,
        time_spent_minutes=progress.time_spent_minutes
    )


@router.get("/user/{user_id}/streak", response_model=StreakResponse)
async def get_user_streak(user_id: str):
    """Get user's current writing streak."""
    service = ProgressTrackingService()

    streak = await service.get_streak(user_id)

    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=str(streak.last_activity_date),
        is_active=streak.is_active
    )


@router.get("/user/{user_id}/achievements", response_model=List[AchievementResponse])
async def get_user_achievements(user_id: str):
    """Get all achievements for a user."""
    service = ProgressTrackingService()

    achievements = await service._get_user_achievements(user_id)

    return [
        AchievementResponse(
            id=a.achievement_id,
            name=a.achievement.name,
            description=a.achievement.description,
            category=a.achievement.category.value,
            rarity=a.achievement.rarity.value,
            icon=a.achievement.icon,
            points=a.achievement.points,
            earned_at=a.earned_at.isoformat() if a.earned_at else None
        )
        for a in achievements
    ]


@router.get("/achievements/all", response_model=List[AchievementResponse])
async def get_all_achievements(user_id: Optional[str] = None):
    """Get all available achievements, optionally marked with user's earned status."""
    service = ProgressTrackingService()

    earned_ids = set()
    if user_id:
        earned = await service._get_user_achievements(user_id)
        earned_ids = {a.achievement_id for a in earned}

    return [
        AchievementResponse(
            id=a.id,
            name=a.name,
            description=a.description,
            category=a.category.value,
            rarity=a.rarity.value,
            icon=a.icon,
            points=a.points,
            earned_at=None  # Not included in "all" view
        )
        for a in service.ACHIEVEMENTS
    ]


@router.post("/check-achievements")
async def check_achievements(request: CheckAchievementsRequest):
    """Check and award any newly earned achievements."""
    service = ProgressTrackingService()

    context = {
        "word_count": request.word_count,
        "total_words": request.total_words,
        "score": request.score,
        "score_improvement": request.score_improvement
    }

    new_achievements = await service.check_achievements(
        user_id=request.user_id,
        proposal_id=request.proposal_id,
        context=context
    )

    return {
        "new_achievements": [
            {
                "id": a.achievement_id,
                "name": a.achievement.name,
                "description": a.achievement.description,
                "icon": a.achievement.icon,
                "points": a.achievement.points,
                "rarity": a.achievement.rarity.value
            }
            for a in new_achievements
        ]
    }


@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Get achievement leaderboard."""
    service = ProgressTrackingService()

    return await service.get_leaderboard(limit)


@router.post("/activity")
async def log_activity(
    user_id: str,
    proposal_id: str,
    activity_type: str,
    duration_seconds: int,
    section_id: Optional[str] = None
):
    """Log user activity for streak and time tracking."""
    from app.services.database import get_db_connection

    async with get_db_connection() as conn:
        await conn.execute("""
            SELECT log_activity($1, $2, $3, $4, $5, NULL)
        """, user_id, proposal_id, section_id, activity_type, duration_seconds)

    return {"status": "logged"}
```

### Step 4: React UI Components

**File:** `frontend/components/ProgressTracker.tsx`

```typescript
import React, { useState, useEffect } from 'react';

interface Progress {
  completion_percentage: number;
  sections_completed: number;
  total_sections: number;
  average_score: number | null;
  gaps_resolved: number;
  total_gaps: number;
  time_spent_minutes: number;
}

interface Streak {
  current_streak: number;
  longest_streak: number;
  is_active: boolean;
}

interface Achievement {
  id: string;
  name: string;
  description: string;
  category: string;
  rarity: string;
  icon: string;
  points: number;
  earned_at?: string;
}

const RARITY_COLORS: Record<string, string> = {
  common: '#9ca3af',
  uncommon: '#22c55e',
  rare: '#3b82f6',
  epic: '#a855f7',
  legendary: '#f59e0b',
};

export const ProgressTracker: React.FC<{
  proposalId: string;
  userId: string;
}> = ({ proposalId, userId }) => {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [streak, setStreak] = useState<Streak | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [newAchievement, setNewAchievement] = useState<Achievement | null>(null);

  useEffect(() => {
    fetchProgress();
    fetchStreak();
    fetchAchievements();
  }, [proposalId, userId]);

  const fetchProgress = async () => {
    const res = await fetch(`/api/proposal/progress/proposal/${proposalId}`);
    setProgress(await res.json());
  };

  const fetchStreak = async () => {
    const res = await fetch(`/api/proposal/progress/user/${userId}/streak`);
    setStreak(await res.json());
  };

  const fetchAchievements = async () => {
    const res = await fetch(`/api/proposal/progress/user/${userId}/achievements`);
    setAchievements(await res.json());
  };

  // Show new achievement notification
  useEffect(() => {
    if (newAchievement) {
      const timer = setTimeout(() => setNewAchievement(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [newAchievement]);

  if (!progress) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      {/* New Achievement Notification */}
      {newAchievement && (
        <div className="fixed top-4 right-4 bg-gradient-to-r from-yellow-400 to-orange-500 text-white p-4 rounded-lg shadow-2xl animate-bounce z-50">
          <div className="flex items-center gap-3">
            <span className="text-4xl">{newAchievement.icon}</span>
            <div>
              <div className="font-bold">Achievement Unlocked!</div>
              <div className="text-lg">{newAchievement.name}</div>
              <div className="text-sm opacity-90">{newAchievement.description}</div>
            </div>
          </div>
        </div>
      )}

      {/* Progress Overview */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-xl font-bold mb-4">Proposal Progress</h2>

        {/* Completion Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Overall Completion</span>
            <span>{progress.completion_percentage.toFixed(0)}%</span>
          </div>
          <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
              style={{ width: `${progress.completion_percentage}%` }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-600">
              {progress.sections_completed}/{progress.total_sections}
            </div>
            <div className="text-sm text-gray-600">Sections Complete</div>
          </div>

          <div className="bg-green-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-600">
              {progress.average_score?.toFixed(1) || '—'}
            </div>
            <div className="text-sm text-gray-600">Average Score</div>
          </div>

          <div className="bg-purple-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-purple-600">
              {progress.gaps_resolved}/{progress.total_gaps}
            </div>
            <div className="text-sm text-gray-600">Gaps Resolved</div>
          </div>

          <div className="bg-orange-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-orange-600">
              {Math.floor(progress.time_spent_minutes / 60)}h {progress.time_spent_minutes % 60}m
            </div>
            <div className="text-sm text-gray-600">Time Invested</div>
          </div>
        </div>
      </div>

      {/* Streak */}
      {streak && (
        <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm opacity-80">Current Streak</div>
              <div className="text-4xl font-bold flex items-center gap-2">
                {streak.current_streak} {streak.is_active && '🔥'}
                <span className="text-lg font-normal">days</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm opacity-80">Best Streak</div>
              <div className="text-2xl font-bold">{streak.longest_streak} days</div>
            </div>
          </div>
          {!streak.is_active && (
            <div className="mt-2 text-sm bg-white bg-opacity-20 rounded px-2 py-1 inline-block">
              Write today to continue your streak!
            </div>
          )}
        </div>
      )}

      {/* Recent Achievements */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-bold mb-4">Achievements ({achievements.length})</h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {achievements.slice(0, 8).map(achievement => (
            <div
              key={achievement.id}
              className="border rounded-lg p-3 text-center hover:shadow-md transition-shadow"
              style={{ borderColor: RARITY_COLORS[achievement.rarity] }}
            >
              <div className="text-3xl mb-1">{achievement.icon}</div>
              <div className="font-medium text-sm">{achievement.name}</div>
              <div
                className="text-xs px-2 py-0.5 rounded mt-1 inline-block text-white"
                style={{ backgroundColor: RARITY_COLORS[achievement.rarity] }}
              >
                {achievement.rarity}
              </div>
            </div>
          ))}
        </div>

        {achievements.length > 8 && (
          <button className="mt-4 text-blue-600 hover:underline text-sm">
            View all {achievements.length} achievements →
          </button>
        )}
      </div>
    </div>
  );
};

// Mini progress bar for sidebar
export const MiniProgressBar: React.FC<{
  completion: number;
  score: number | null;
}> = ({ completion, score }) => (
  <div className="space-y-2">
    <div className="flex justify-between text-xs text-gray-500">
      <span>{completion.toFixed(0)}% complete</span>
      <span>{score?.toFixed(1) || '—'}/5</span>
    </div>
    <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
      <div
        className="h-full bg-blue-500 transition-all duration-300"
        style={{ width: `${completion}%` }}
      />
    </div>
  </div>
);
```

---

## Testing Plan

```python
# tests/test_progress_tracking.py

import pytest
from app.services.proposal_writing.progress_tracking_service import (
    ProgressTrackingService, AchievementRarity, Streak
)


class TestProgressTracking:

    @pytest.fixture
    def service(self):
        return ProgressTrackingService()

    def test_achievement_criteria_check_score(self, service):
        """Test score-based achievement criteria."""
        from app.services.proposal_writing.progress_tracking_service import (
            Achievement, AchievementCategory, ProgressSnapshot
        )

        # Create mock progress
        progress = ProgressSnapshot(
            proposal_id="test",
            completion_percentage=50,
            sections_completed=2,
            total_sections=4,
            average_score=3.5,
            highest_score=4.2,
            lowest_score=2.8,
            gaps_resolved=5,
            total_gaps=10,
            suggestions_accepted=15,
            rewrites_applied=3,
            time_spent_minutes=120,
            last_activity=None
        )

        streak = Streak(
            current_streak=5,
            longest_streak=5,
            last_activity_date=None,
            is_active=True
        )

        # Find the competitive_section achievement
        achievement = next(
            a for a in service.ACHIEVEMENTS
            if a.id == "competitive_section"
        )

        # Should pass with score 4.2
        context = {"score": 4.2}
        assert service._check_criteria(achievement, context, progress, streak)

        # Should fail with score 3.5
        context = {"score": 3.5}
        assert not service._check_criteria(achievement, context, progress, streak)

    def test_streak_calculation(self, service):
        """Test streak calculations."""
        # This would need database mocking
        pass

    def test_all_achievements_have_required_fields(self, service):
        """Test that all achievements are properly defined."""
        for achievement in service.ACHIEVEMENTS:
            assert achievement.id
            assert achievement.name
            assert achievement.description
            assert achievement.category
            assert achievement.rarity
            assert achievement.icon
            assert achievement.points > 0
            assert achievement.criteria
```

---

## Verification Checklist

- [ ] Progress calculation is accurate
- [ ] Streak tracking works across days
- [ ] Achievements are awarded correctly
- [ ] No duplicate achievements awarded
- [ ] New achievement notification displays
- [ ] Progress bar updates in real-time
- [ ] Time tracking accumulates correctly
- [ ] Leaderboard sorts correctly
- [ ] Activity logging works

---

## Gamification Best Practices

1. **Clear Goals**: Each achievement has specific, understandable criteria
2. **Progressive Difficulty**: Common → Legendary progression
3. **Immediate Feedback**: New achievements show instantly
4. **Social Proof**: Leaderboard for motivation
5. **Meaningful Progress**: Tied to actual proposal quality
6. **Non-Punitive**: Missing a day doesn't penalize heavily
