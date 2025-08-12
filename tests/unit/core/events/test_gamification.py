"""
Tests for gamification events.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.core.events.base import EventCategory
from src.core.events.gamification import (
    AchievementUnlockedEvent,
    DailyBonusClaimedEvent,
    LeaderboardChangedEvent,
    PointsAwardedEvent,
    PointsDeductedEvent,
    StreakUpdatedEvent,
)
from src.core.interfaces import EventPriority, EventValidationError


class TestPointsAwardedEvent:
    """Test PointsAwardedEvent functionality."""

    def test_points_awarded_creation(self):
        """Test creating a PointsAwardedEvent."""
        event = PointsAwardedEvent(
            user_id=123,
            points_amount=100,
            action_type="story_completion",
            multiplier=1.5,
            bonus_points=25,
            source_event_id="story-456",
        )

        assert event.user_id == 123
        assert event.points_amount == 100
        assert event.action_type == "story_completion"
        assert event.multiplier == 1.5
        assert event.bonus_points == 25
        assert event.total_points_awarded == 175  # (100 * 1.5) + 25
        assert event.source_event_id == "story-456"
        assert event.category == EventCategory.GAMIFICATION
        assert event.priority == EventPriority.NORMAL

    def test_points_awarded_serialization(self):
        """Test serialization of PointsAwardedEvent."""
        event = PointsAwardedEvent(
            user_id=123, points_amount=100, action_type="story_completion"
        )

        data = event.to_dict()
        restored = PointsAwardedEvent.from_dict(data)

        assert restored.user_id == event.user_id
        assert restored.points_amount == event.points_amount
        assert restored.action_type == event.action_type
        assert restored.total_points_awarded == event.total_points_awarded

    def test_points_awarded_validation(self):
        """Test validation for PointsAwardedEvent."""
        # Valid event should pass
        event = PointsAwardedEvent(
            user_id=123, points_amount=100, action_type="story_completion"
        )
        assert event.validate()

        # Invalid points amount should fail
        with pytest.raises(
            EventValidationError, match="Points amount must be a positive integer"
        ):
            PointsAwardedEvent(
                user_id=123, points_amount=-10, action_type="story_completion"
            )

        # Invalid multiplier should fail
        with pytest.raises(
            EventValidationError, match="Multiplier must be a positive number"
        ):
            PointsAwardedEvent(
                user_id=123,
                points_amount=100,
                action_type="story_completion",
                multiplier=-0.5,
            )

        # Empty action type should fail
        with pytest.raises(
            EventValidationError, match="Action type must be a non-empty string"
        ):
            PointsAwardedEvent(user_id=123, points_amount=100, action_type="")


class TestPointsDeductedEvent:
    """Test PointsDeductedEvent functionality."""

    def test_points_deducted_creation(self):
        """Test creating a PointsDeductedEvent."""
        event = PointsDeductedEvent(
            user_id=123, points_amount=50, deduction_reason="penalty", admin_user_id=456
        )

        assert event.user_id == 123
        assert event.points_amount == 50
        assert event.deduction_reason == "penalty"
        assert event.payload["admin_user_id"] == 456
        assert event.category == EventCategory.GAMIFICATION
        assert event.priority == EventPriority.HIGH  # Deductions are high priority


class TestAchievementUnlockedEvent:
    """Test AchievementUnlockedEvent functionality."""

    def test_achievement_unlocked_creation(self):
        """Test creating an AchievementUnlockedEvent."""
        event = AchievementUnlockedEvent(
            user_id=123,
            achievement_id="first_story",
            achievement_name="First Story Completed",
            achievement_category="narrative",
            achievement_tier="bronze",
            points_reward=500,
            badge_url="https://example.com/badge.png",
        )

        assert event.user_id == 123
        assert event.achievement_id == "first_story"
        assert event.achievement_name == "First Story Completed"
        assert event.achievement_category == "narrative"
        assert event.achievement_tier == "bronze"
        assert event.points_reward == 500
        assert event.badge_url == "https://example.com/badge.png"
        assert event.category == EventCategory.GAMIFICATION
        assert event.priority == EventPriority.HIGH

    def test_achievement_validation(self):
        """Test validation for AchievementUnlockedEvent."""
        # Valid event should pass
        event = AchievementUnlockedEvent(
            user_id=123,
            achievement_id="test_achievement",
            achievement_name="Test Achievement",
            achievement_category="test",
            achievement_tier="bronze",
        )
        assert event.validate()

        # Invalid tier should fail
        with pytest.raises(
            EventValidationError, match="Achievement tier must be one of"
        ):
            AchievementUnlockedEvent(
                user_id=123,
                achievement_id="test_achievement",
                achievement_name="Test Achievement",
                achievement_category="test",
                achievement_tier="invalid_tier",
            )

        # Empty achievement ID should fail
        with pytest.raises(
            EventValidationError, match="Achievement ID must be a non-empty string"
        ):
            AchievementUnlockedEvent(
                user_id=123,
                achievement_id="",
                achievement_name="Test Achievement",
                achievement_category="test",
                achievement_tier="bronze",
            )


class TestStreakUpdatedEvent:
    """Test StreakUpdatedEvent functionality."""

    def test_streak_updated_creation(self):
        """Test creating a StreakUpdatedEvent."""
        event = StreakUpdatedEvent(
            user_id=123,
            streak_type="daily_login",
            previous_count=4,
            new_count=5,
            streak_milestone=5,
            bonus_multiplier=1.2,
        )

        assert event.user_id == 123
        assert event.streak_type == "daily_login"
        assert event.previous_count == 4
        assert event.new_count == 5
        assert event.is_continued
        assert not event.is_broken
        assert event.streak_milestone == 5
        assert event.bonus_multiplier == 1.2
        assert event.category == EventCategory.GAMIFICATION
        assert event.priority == EventPriority.HIGH  # Milestone reached

    def test_streak_broken(self):
        """Test streak broken scenario."""
        event = StreakUpdatedEvent(
            user_id=123,
            streak_type="daily_login",
            previous_count=5,
            new_count=0,
            is_broken=True,
        )

        assert event.is_broken
        assert not event.is_continued
        assert event.priority == EventPriority.HIGH  # Broken streaks are high priority

    def test_streak_validation(self):
        """Test validation for StreakUpdatedEvent."""
        # Valid event should pass
        event = StreakUpdatedEvent(
            user_id=123, streak_type="daily_login", previous_count=0, new_count=1
        )
        assert event.validate()

        # Negative counts should fail
        with pytest.raises(
            EventValidationError, match="Previous count must be a non-negative integer"
        ):
            StreakUpdatedEvent(
                user_id=123, streak_type="daily_login", previous_count=-1, new_count=1
            )


class TestLeaderboardChangedEvent:
    """Test LeaderboardChangedEvent functionality."""

    def test_leaderboard_changed_creation(self):
        """Test creating a LeaderboardChangedEvent."""
        event = LeaderboardChangedEvent(
            user_id=123,
            leaderboard_type="global",
            previous_rank=15,
            new_rank=10,
            previous_score=1000,
            new_score=1250,
            is_new_personal_best=True,
        )

        assert event.user_id == 123
        assert event.leaderboard_type == "global"
        assert event.previous_rank == 15
        assert event.new_rank == 10
        assert event.rank_change_delta == 5  # Moved up 5 places
        assert event.moved_up
        assert event.is_new_personal_best
        assert event.category == EventCategory.GAMIFICATION
        assert event.priority == EventPriority.HIGH  # Personal best

    def test_leaderboard_first_time(self):
        """Test first time on leaderboard."""
        event = LeaderboardChangedEvent(
            user_id=123,
            leaderboard_type="weekly",
            previous_rank=None,
            new_rank=25,
            previous_score=None,
            new_score=500,
        )

        assert event.previous_rank is None
        assert event.new_rank == 25
        assert event.rank_change_delta is None

    def test_leaderboard_validation(self):
        """Test validation for LeaderboardChangedEvent."""
        # Valid event should pass
        event = LeaderboardChangedEvent(
            user_id=123,
            leaderboard_type="global",
            previous_rank=10,
            new_rank=8,
            previous_score=1000,
            new_score=1200,
        )
        assert event.validate()

        # Invalid new rank should fail
        with pytest.raises(
            EventValidationError, match="New rank must be a positive integer"
        ):
            LeaderboardChangedEvent(
                user_id=123,
                leaderboard_type="global",
                previous_rank=10,
                new_rank=0,
                previous_score=1000,
                new_score=1200,
            )


class TestDailyBonusClaimedEvent:
    """Test DailyBonusClaimedEvent functionality."""

    def test_daily_bonus_claimed_creation(self):
        """Test creating a DailyBonusClaimedEvent."""
        next_bonus_time = datetime.utcnow()

        event = DailyBonusClaimedEvent(
            user_id=123,
            bonus_day=5,
            points_awarded=150,
            bonus_type="streak_bonus",
            consecutive_days=5,
            next_bonus_available_at=next_bonus_time,
        )

        assert event.user_id == 123
        assert event.bonus_day == 5
        assert event.points_awarded == 150
        assert event.consecutive_days == 5
        assert event.payload["bonus_type"] == "streak_bonus"
        assert event.payload["next_bonus_available_at"] == next_bonus_time.isoformat()
        assert event.category == EventCategory.GAMIFICATION
        assert event.priority == EventPriority.NORMAL


class TestGamificationEventsIntegration:
    """Test integration scenarios with gamification events."""

    def test_points_to_achievement_flow(self):
        """Test flow from points awarded to achievement unlocked."""
        # Award points
        points_event = PointsAwardedEvent(
            user_id=123, points_amount=1000, action_type="story_completion"
        )

        # Achievement unlocked as result
        achievement_event = AchievementUnlockedEvent(
            user_id=123,
            achievement_id="thousand_points",
            achievement_name="Thousand Points",
            achievement_category="progression",
            achievement_tier="silver",
            points_reward=500,
            correlation_id=points_event.correlation_id,
        )

        assert points_event.user_id == achievement_event.user_id
        assert achievement_event.points_reward == 500

    def test_streak_milestone_achievement(self):
        """Test streak milestone triggering achievement."""
        # Streak milestone
        streak_event = StreakUpdatedEvent(
            user_id=123,
            streak_type="daily_login",
            previous_count=6,
            new_count=7,
            streak_milestone=7,
        )

        # Achievement for milestone
        achievement_event = AchievementUnlockedEvent(
            user_id=123,
            achievement_id="seven_day_streak",
            achievement_name="Seven Day Streak",
            achievement_category="engagement",
            achievement_tier="gold",
            correlation_id=streak_event.correlation_id,
        )

        assert streak_event.streak_milestone == 7
        assert achievement_event.achievement_tier == "gold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
