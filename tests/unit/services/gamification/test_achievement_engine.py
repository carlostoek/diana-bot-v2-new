"""
Unit tests for the Achievement Engine.

Tests achievement criteria evaluation, unlocking logic,
progress tracking, and recommendation systems.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.models.gamification import (
    AchievementCategory,
    AchievementDefinition,
    AchievementTier,
    UserAchievement,
    UserGamification,
)
from src.services.gamification.engines.achievement_engine import AchievementEngine


@pytest.fixture
def achievement_config():
    """Test configuration for achievement engine."""
    return {
        "achievement_milestones": {
            "total_points": [1000, 5000, 10000],
            "stories_completed": [1, 5, 10],
            "daily_streaks": [7, 30, 100],
            "decisions_made": [50, 200, 500],
        }
    }


@pytest.fixture
def achievement_engine(achievement_config):
    """Create an achievement engine instance for testing."""
    return AchievementEngine(achievement_config)


@pytest.fixture
def sample_achievements():
    """Create sample achievement definitions for testing."""
    return [
        AchievementDefinition(
            id="first_story",
            name="Story Explorer",
            description="Complete your first story",
            category=AchievementCategory.NARRATIVE,
            tier=AchievementTier.BRONZE,
            points_reward=500,
            unlock_criteria={"stories_completed": 1},
            is_secret=False,
            is_repeatable=False,
            is_active=True,
            display_order=1,
        ),
        AchievementDefinition(
            id="point_collector",
            name="Point Collector",
            description="Accumulate 1,000 points",
            category=AchievementCategory.MILESTONE,
            tier=AchievementTier.BRONZE,
            points_reward=100,
            unlock_criteria={"total_points": 1000},
            is_secret=False,
            is_repeatable=False,
            is_active=True,
            display_order=2,
        ),
        AchievementDefinition(
            id="decision_maker",
            name="Decision Maker",
            description="Make 50 story decisions",
            category=AchievementCategory.NARRATIVE,
            tier=AchievementTier.SILVER,
            points_reward=300,
            unlock_criteria={"decisions_made": 50},
            is_secret=False,
            is_repeatable=False,
            is_active=True,
            display_order=3,
        ),
        AchievementDefinition(
            id="multi_criteria",
            name="Advanced Player",
            description="Complete 5 stories and make 100 decisions",
            category=AchievementCategory.MILESTONE,
            tier=AchievementTier.GOLD,
            points_reward=1000,
            unlock_criteria={"stories_completed": 5, "decisions_made": 100},
            is_secret=False,
            is_repeatable=False,
            is_active=True,
            display_order=4,
        ),
        AchievementDefinition(
            id="secret_achievement",
            name="Hidden Master",
            description="Secret achievement",
            category=AchievementCategory.SPECIAL,
            tier=AchievementTier.PLATINUM,
            points_reward=2000,
            unlock_criteria={"total_points": 50000},
            is_secret=True,
            is_repeatable=False,
            is_active=True,
            display_order=5,
        ),
    ]


class TestAchievementEvaluation:
    """Test achievement criteria evaluation logic."""

    def test_single_criteria_achievement_unlock(
        self, achievement_engine, sample_achievements
    ):
        """Test unlocking achievement with single criteria."""
        user_stats = {
            "stories_completed": 1,
            "total_points": 500,
            "decisions_made": 10,
        }

        user_achievements = []  # No previous achievements
        trigger_context = {"action_type": "story_complete"}

        unlockable = achievement_engine.evaluate_achievements(
            user_stats, sample_achievements, user_achievements, trigger_context
        )

        # Should unlock "first_story" achievement
        assert len(unlockable) == 1
        achievement_def, unlock_context = unlockable[0]
        assert achievement_def.id == "first_story"
        assert unlock_context["trigger_action"] == "story_complete"

    def test_multiple_criteria_achievement_unlock(
        self, achievement_engine, sample_achievements
    ):
        """Test unlocking achievement with multiple criteria."""
        user_stats = {
            "stories_completed": 5,
            "total_points": 2000,
            "decisions_made": 100,
        }

        user_achievements = []
        trigger_context = {"action_type": "decision_made"}

        unlockable = achievement_engine.evaluate_achievements(
            user_stats, sample_achievements, user_achievements, trigger_context
        )

        # Should unlock multiple achievements
        unlocked_ids = [achievement_def.id for achievement_def, _ in unlockable]
        assert "first_story" in unlocked_ids
        assert "point_collector" in unlocked_ids
        assert "decision_maker" in unlocked_ids
        assert "multi_criteria" in unlocked_ids

    def test_insufficient_criteria_no_unlock(
        self, achievement_engine, sample_achievements
    ):
        """Test that insufficient criteria don't unlock achievements."""
        user_stats = {
            "stories_completed": 0,
            "total_points": 500,
            "decisions_made": 10,
        }

        user_achievements = []
        trigger_context = {"action_type": "points_awarded"}

        unlockable = achievement_engine.evaluate_achievements(
            user_stats, sample_achievements, user_achievements, trigger_context
        )

        # Should not unlock any achievements
        assert len(unlockable) == 0

    def test_already_completed_not_unlocked(
        self, achievement_engine, sample_achievements
    ):
        """Test that already completed achievements are not unlocked again."""
        user_stats = {
            "stories_completed": 1,
            "total_points": 1000,
            "decisions_made": 50,
        }

        # User already has some achievements
        user_achievements = [
            MagicMock(achievement_id="first_story", is_completed=True),
            MagicMock(achievement_id="point_collector", is_completed=True),
        ]

        trigger_context = {"action_type": "decision_made"}

        unlockable = achievement_engine.evaluate_achievements(
            user_stats, sample_achievements, user_achievements, trigger_context
        )

        # Should only unlock decision_maker (not already completed)
        assert len(unlockable) == 1
        achievement_def, _ = unlockable[0]
        assert achievement_def.id == "decision_maker"

    def test_inactive_achievements_ignored(
        self, achievement_engine, sample_achievements
    ):
        """Test that inactive achievements are ignored."""
        # Mark an achievement as inactive
        sample_achievements[0].is_active = False

        user_stats = {
            "stories_completed": 1,
            "total_points": 500,
            "decisions_made": 10,
        }

        user_achievements = []
        trigger_context = {"action_type": "story_complete"}

        unlockable = achievement_engine.evaluate_achievements(
            user_stats, sample_achievements, user_achievements, trigger_context
        )

        # Should not unlock the inactive achievement
        unlocked_ids = [achievement_def.id for achievement_def, _ in unlockable]
        assert "first_story" not in unlocked_ids

    def test_repeatable_achievement_can_unlock_again(
        self, achievement_engine, sample_achievements
    ):
        """Test that repeatable achievements can be unlocked multiple times."""
        # Make an achievement repeatable
        sample_achievements[0].is_repeatable = True

        user_stats = {
            "stories_completed": 1,
            "total_points": 500,
            "decisions_made": 10,
        }

        # User already completed this repeatable achievement
        user_achievements = [
            MagicMock(achievement_id="first_story", is_completed=True),
        ]

        trigger_context = {"action_type": "story_complete"}

        unlockable = achievement_engine.evaluate_achievements(
            user_stats, sample_achievements, user_achievements, trigger_context
        )

        # Should unlock the repeatable achievement again
        assert len(unlockable) == 1
        achievement_def, unlock_context = unlockable[0]
        assert achievement_def.id == "first_story"
        assert unlock_context["is_repeat_unlock"] is True


class TestUserAchievementCreation:
    """Test user achievement creation logic."""

    def test_create_user_achievement_data(
        self, achievement_engine, sample_achievements
    ):
        """Test creating user achievement data."""
        achievement_def = sample_achievements[0]  # first_story
        unlock_context = {
            "criteria_met": {"stories_completed": {"is_met": True}},
            "trigger_action": "story_complete",
        }

        user_achievement_data = achievement_engine.create_user_achievement(
            user_id=123,
            achievement_definition=achievement_def,
            unlock_context=unlock_context,
            source_event_id="event_123",
        )

        assert user_achievement_data["user_id"] == 123
        assert user_achievement_data["achievement_id"] == "first_story"
        assert user_achievement_data["is_completed"] is True
        assert user_achievement_data["points_awarded"] == 500
        assert user_achievement_data["unlock_event_id"] == "event_123"
        assert isinstance(user_achievement_data["unlocked_at"], datetime)


class TestAchievementStatistics:
    """Test achievement statistics calculation."""

    def test_calculate_achievement_statistics(
        self, achievement_engine, sample_achievements
    ):
        """Test calculating comprehensive achievement statistics."""
        # Create mock user achievements
        user_achievements = [
            MagicMock(
                achievement_id="first_story",
                is_completed=True,
                points_awarded=500,
                unlocked_at=datetime.now(timezone.utc),
            ),
            MagicMock(
                achievement_id="point_collector",
                is_completed=True,
                points_awarded=100,
                unlocked_at=datetime.now(timezone.utc),
            ),
            MagicMock(
                achievement_id="decision_maker",
                is_completed=False,
                points_awarded=0,
                unlocked_at=None,
            ),
        ]

        stats = achievement_engine.calculate_achievement_statistics(
            user_achievements, sample_achievements
        )

        assert stats["total_completed"] == 2
        assert stats["total_in_progress"] == 1
        assert stats["total_available"] == 5
        assert stats["completion_percentage"] == 40.0  # 2/5 * 100
        assert stats["total_points_earned"] == 600  # 500 + 100
        assert stats["tier_counts"]["bronze"] == 2
        assert stats["tier_counts"]["silver"] == 0

    def test_tier_counts_calculation(self, achievement_engine, sample_achievements):
        """Test tier counts calculation."""
        # Create achievements for different tiers
        user_achievements = [
            MagicMock(achievement_id="first_story", is_completed=True),  # Bronze
            MagicMock(achievement_id="point_collector", is_completed=True),  # Bronze
            MagicMock(achievement_id="decision_maker", is_completed=True),  # Silver
        ]

        stats = achievement_engine.calculate_achievement_statistics(
            user_achievements, sample_achievements
        )

        assert stats["tier_counts"]["bronze"] == 2
        assert stats["tier_counts"]["silver"] == 1
        assert stats["tier_counts"]["gold"] == 0
        assert stats["tier_counts"]["platinum"] == 0

    def test_category_counts_calculation(self, achievement_engine, sample_achievements):
        """Test category counts calculation."""
        user_achievements = [
            MagicMock(achievement_id="first_story", is_completed=True),  # Narrative
            MagicMock(achievement_id="point_collector", is_completed=True),  # Milestone
            MagicMock(achievement_id="decision_maker", is_completed=True),  # Narrative
        ]

        stats = achievement_engine.calculate_achievement_statistics(
            user_achievements, sample_achievements
        )

        assert stats["category_counts"]["narrative"] == 2
        assert stats["category_counts"]["milestone"] == 1
        assert stats["category_counts"]["social"] == 0


class TestAchievementRecommendations:
    """Test achievement recommendation system."""

    def test_get_achievement_recommendations(
        self, achievement_engine, sample_achievements
    ):
        """Test getting achievement recommendations."""
        user_stats = {
            "stories_completed": 0,
            "total_points": 800,  # Close to 1000
            "decisions_made": 40,  # Close to 50
        }

        user_achievements = []  # No completed achievements

        recommendations = achievement_engine.get_achievement_recommendations(
            user_stats, sample_achievements, user_achievements, limit=3
        )

        # Should recommend achievements close to completion
        assert len(recommendations) <= 3

        # Check that recommendations include progress info
        for rec in recommendations:
            assert "achievement_id" in rec
            assert "progress_percentage" in rec
            assert "next_milestone" in rec
            assert rec["progress_percentage"] > 0

    def test_recommendations_exclude_secret_achievements(
        self, achievement_engine, sample_achievements
    ):
        """Test that recommendations exclude secret achievements."""
        user_stats = {
            "total_points": 45000,  # Close to secret achievement
        }

        user_achievements = []

        recommendations = achievement_engine.get_achievement_recommendations(
            user_stats, sample_achievements, user_achievements
        )

        # Should not include secret achievement
        rec_ids = [rec["achievement_id"] for rec in recommendations]
        assert "secret_achievement" not in rec_ids

    def test_recommendations_exclude_completed(
        self, achievement_engine, sample_achievements
    ):
        """Test that recommendations exclude completed achievements."""
        user_stats = {
            "stories_completed": 1,
            "total_points": 1000,
            "decisions_made": 50,
        }

        # User has already completed first_story
        user_achievements = [MagicMock(achievement_id="first_story", is_completed=True)]

        recommendations = achievement_engine.get_achievement_recommendations(
            user_stats, sample_achievements, user_achievements
        )

        # Should not recommend completed achievement
        rec_ids = [rec["achievement_id"] for rec in recommendations]
        assert "first_story" not in rec_ids

    def test_recommendations_sorted_by_progress(
        self, achievement_engine, sample_achievements
    ):
        """Test that recommendations are sorted by progress percentage."""
        user_stats = {
            "stories_completed": 0,
            "total_points": 900,  # 90% progress to point_collector
            "decisions_made": 25,  # 50% progress to decision_maker
        }

        user_achievements = []

        recommendations = achievement_engine.get_achievement_recommendations(
            user_stats, sample_achievements, user_achievements
        )

        # Should be sorted by progress (highest first)
        if len(recommendations) >= 2:
            assert (
                recommendations[0]["progress_percentage"]
                >= recommendations[1]["progress_percentage"]
            )


class TestAchievementCriteriaValidation:
    """Test achievement criteria validation."""

    def test_valid_criteria_passes(self, achievement_engine):
        """Test that valid criteria pass validation."""
        valid_criteria = {
            "total_points": 1000,
            "stories_completed": 5,
            "daily_streak": 7,
        }

        # Should not raise any exception
        assert achievement_engine.validate_achievement_criteria(valid_criteria) is True

    def test_empty_criteria_fails(self, achievement_engine):
        """Test that empty criteria fail validation."""
        with pytest.raises(ValueError, match="Achievement criteria cannot be empty"):
            achievement_engine.validate_achievement_criteria({})

    def test_non_dict_criteria_fails(self, achievement_engine):
        """Test that non-dictionary criteria fail validation."""
        with pytest.raises(
            ValueError, match="Achievement criteria must be a dictionary"
        ):
            achievement_engine.validate_achievement_criteria("not a dict")

    def test_non_numeric_values_fail(self, achievement_engine):
        """Test that non-numeric criterion values fail validation."""
        invalid_criteria = {
            "total_points": "not a number",
        }

        with pytest.raises(ValueError, match="must have a numeric value"):
            achievement_engine.validate_achievement_criteria(invalid_criteria)

    def test_negative_values_fail(self, achievement_engine):
        """Test that negative criterion values fail validation."""
        invalid_criteria = {
            "total_points": -100,
        }

        with pytest.raises(ValueError, match="must have a positive value"):
            achievement_engine.validate_achievement_criteria(invalid_criteria)

    def test_zero_values_fail(self, achievement_engine):
        """Test that zero criterion values fail validation."""
        invalid_criteria = {
            "total_points": 0,
        }

        with pytest.raises(ValueError, match="must have a positive value"):
            achievement_engine.validate_achievement_criteria(invalid_criteria)


class TestDefaultAchievements:
    """Test default achievement definitions."""

    def test_get_default_achievements(self, achievement_engine):
        """Test getting default achievement definitions."""
        defaults = achievement_engine.get_default_achievements()

        assert len(defaults) > 0

        # Check that all required fields are present
        for achievement in defaults:
            assert "id" in achievement
            assert "name" in achievement
            assert "description" in achievement
            assert "category" in achievement
            assert "tier" in achievement
            assert "unlock_criteria" in achievement
            assert isinstance(achievement["unlock_criteria"], dict)

    def test_default_achievements_have_valid_criteria(self, achievement_engine):
        """Test that default achievements have valid criteria."""
        defaults = achievement_engine.get_default_achievements()

        for achievement in defaults:
            # Should not raise any exception
            achievement_engine.validate_achievement_criteria(
                achievement["unlock_criteria"]
            )

    def test_default_achievements_cover_different_categories(self, achievement_engine):
        """Test that default achievements cover different categories."""
        defaults = achievement_engine.get_default_achievements()

        categories = set(achievement["category"] for achievement in defaults)

        # Should include multiple categories
        assert AchievementCategory.NARRATIVE in categories
        assert AchievementCategory.MILESTONE in categories
        assert AchievementCategory.ENGAGEMENT in categories

    def test_default_achievements_have_different_tiers(self, achievement_engine):
        """Test that default achievements have different tiers."""
        defaults = achievement_engine.get_default_achievements()

        tiers = set(achievement["tier"] for achievement in defaults)

        # Should include multiple tiers
        assert AchievementTier.BRONZE in tiers
        assert AchievementTier.SILVER in tiers
        assert AchievementTier.GOLD in tiers
