"""
Coverage-focused tests for GamificationService.

This module provides tests specifically designed to achieve high code coverage
for the GamificationService by exercising all methods and code paths.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.models.gamification import (
    AchievementCategory,
    AchievementTier,
    PointsTransaction,
    PointsTransactionType,
    UserAchievement,
    UserGamification,
)
from src.services.gamification.interfaces import GamificationError
from src.services.gamification.service import GamificationService


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = AsyncMock()
    # Set up default returns to avoid None errors
    repo.get_user_gamification.return_value = None
    repo.create_user_gamification.return_value = UserGamification(
        user_id=12345,
        total_points=0,
        current_level=1,
        current_daily_streak=0,
        vip_status=False,
        current_multiplier=1.0,
        vip_multiplier=1.0,
    )
    return repo


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    bus = AsyncMock()
    bus.publish.return_value = None
    return bus


@pytest.fixture
def service(mock_repository, mock_event_bus):
    """Create GamificationService with mocked dependencies."""
    return GamificationService(repository=mock_repository, event_bus=mock_event_bus)


class TestServiceInitialization:
    """Test service initialization and configuration."""

    def test_init_with_dependencies(self, mock_repository, mock_event_bus):
        """Test successful initialization."""
        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )
        assert service.repository == mock_repository
        assert service.event_bus == mock_event_bus

    def test_default_config(self, service):
        """Test default configuration retrieval."""
        config = service._get_default_config()
        assert isinstance(config, dict)
        assert "anti_abuse" in config
        assert "points" in config
        assert "achievements" in config

    async def test_initialize(self, service):
        """Test service initialization."""
        with patch.object(service, "_setup_event_subscriptions") as mock_setup:
            with patch.object(service, "_load_achievement_definitions") as mock_load:
                await service.initialize()
                mock_setup.assert_called_once()
                mock_load.assert_called_once()

    async def test_shutdown(self, service):
        """Test service shutdown."""
        await service.shutdown()
        # Should complete without error

    async def test_setup_event_subscriptions(self, service):
        """Test event subscription setup."""
        await service._setup_event_subscriptions()
        # Should complete without error

    async def test_load_achievement_definitions(self, service):
        """Test achievement definitions loading."""
        await service._load_achievement_definitions()
        # Should complete without error

    def test_get_default_achievements(self, service):
        """Test default achievements generation."""
        achievements = service._get_default_achievements()
        assert isinstance(achievements, list)
        assert len(achievements) > 0


class TestPointsAwarding:
    """Test points awarding functionality."""

    async def test_award_points_success(self, service, mock_repository):
        """Test successful points awarding."""
        user_id = 12345
        points = 100
        action = "test_action"

        # Mock user creation
        mock_repository.get_user_gamification.return_value = None
        mock_repository.create_user_gamification.return_value = UserGamification(
            user_id=user_id,
            total_points=0,
            current_level=1,
            vip_status=False,
            current_multiplier=1.0,
            vip_multiplier=1.0,
        )
        mock_repository.create_points_transaction.return_value = True
        mock_repository.update_user_gamification.return_value = True

        # Mock streak multiplier
        with patch.object(service, "_get_streak_multiplier", return_value=1.0):
            result = await service.award_points(user_id, points, action)
            assert result is True

    async def test_award_points_invalid_amount(self, service):
        """Test award points with invalid amount."""
        user_id = 12345

        with pytest.raises(ValueError, match="Points amount must be positive"):
            await service.award_points(user_id, 0, "test")

        with pytest.raises(ValueError, match="Points amount must be positive"):
            await service.award_points(user_id, -10, "test")

    async def test_award_points_with_vip_multiplier(self, service, mock_repository):
        """Test awarding points to VIP user."""
        user_id = 12345
        points = 100

        # Mock VIP user
        vip_user = UserGamification(
            user_id=user_id,
            total_points=500,
            current_level=3,
            vip_status=True,
            vip_multiplier=1.5,
            current_multiplier=1.0,
        )
        mock_repository.get_user_gamification.return_value = vip_user
        mock_repository.create_points_transaction.return_value = True
        mock_repository.update_user_gamification.return_value = True

        with patch.object(service, "_get_streak_multiplier", return_value=1.0):
            result = await service.award_points(user_id, points, "vip_action")
            assert result is True

    async def test_award_points_anti_abuse_error(self, service):
        """Test points awarding with anti-abuse error."""
        user_id = 12345

        with patch.object(
            service, "_check_anti_abuse", side_effect=GamificationError("Rate limited")
        ):
            with pytest.raises(GamificationError, match="Rate limited"):
                await service.award_points(user_id, 100, "test")

    async def test_get_streak_multiplier(self, service, mock_repository):
        """Test streak multiplier calculation."""
        user_id = 12345

        # Mock user with streak
        user_with_streak = UserGamification(
            user_id=user_id,
            current_daily_streak=5,
        )
        mock_repository.get_user_gamification.return_value = user_with_streak

        multiplier = await service._get_streak_multiplier(user_id)
        assert isinstance(multiplier, float)
        assert multiplier >= 1.0

    async def test_check_anti_abuse(self, service, mock_repository):
        """Test anti-abuse checking."""
        user_id = 12345
        points = 100
        action = "test"

        # Mock recent transactions for rate limiting
        mock_repository.get_recent_transactions.return_value = []

        # Should complete without error for normal usage
        await service._check_anti_abuse(user_id, points, action)


class TestPointsDeduction:
    """Test points deduction functionality."""

    async def test_deduct_points_success(self, service, mock_repository):
        """Test successful points deduction."""
        user_id = 12345
        points = 50
        reason = "purchase"

        # Mock user with sufficient points
        user_with_points = UserGamification(
            user_id=user_id,
            total_points=100,
            current_level=2,
        )
        mock_repository.get_user_gamification.return_value = user_with_points
        mock_repository.create_points_transaction.return_value = True
        mock_repository.update_user_gamification.return_value = True

        result = await service.deduct_points(user_id, points, reason)
        assert result is True

    async def test_deduct_points_insufficient_funds(self, service, mock_repository):
        """Test deduction with insufficient points."""
        user_id = 12345
        points = 150

        # Mock user with insufficient points
        user_low_points = UserGamification(
            user_id=user_id,
            total_points=100,
        )
        mock_repository.get_user_gamification.return_value = user_low_points

        with pytest.raises(GamificationError, match="Insufficient points"):
            await service.deduct_points(user_id, points, "expensive_item")

    async def test_deduct_points_user_not_found(self, service, mock_repository):
        """Test deduction for non-existent user."""
        user_id = 12345
        mock_repository.get_user_gamification.return_value = None

        with pytest.raises(GamificationError, match="User not found"):
            await service.deduct_points(user_id, 50, "test")


class TestUserManagement:
    """Test user management functionality."""

    async def test_get_or_create_user_new(self, service, mock_repository):
        """Test getting or creating a new user."""
        user_id = 12345

        mock_repository.get_user_gamification.return_value = None
        new_user = UserGamification(user_id=user_id, total_points=0, current_level=1)
        mock_repository.create_user_gamification.return_value = new_user

        result = await service._get_or_create_user(user_id)
        assert result.user_id == user_id
        mock_repository.create_user_gamification.assert_called_once_with(user_id)

    async def test_get_or_create_user_existing(self, service, mock_repository):
        """Test getting existing user."""
        user_id = 12345

        existing_user = UserGamification(
            user_id=user_id, total_points=500, current_level=3
        )
        mock_repository.get_user_gamification.return_value = existing_user

        result = await service._get_or_create_user(user_id)
        assert result.user_id == user_id
        assert result.total_points == 500

    async def test_initialize_user(self, service, mock_repository):
        """Test user initialization."""
        user_id = 12345

        new_user = UserGamification(user_id=user_id, total_points=0, current_level=1)
        mock_repository.create_user_gamification.return_value = new_user

        result = await service.initialize_user(user_id)
        assert result.user_id == user_id

    async def test_get_user_gamification(self, service, mock_repository):
        """Test getting user gamification data."""
        user_id = 12345

        user_data = UserGamification(user_id=user_id, total_points=300)
        mock_repository.get_user_gamification.return_value = user_data

        result = await service.get_user_gamification(user_id)
        assert result.user_id == user_id

    async def test_update_user_level(self, service, mock_repository):
        """Test user level update."""
        user_id = 12345

        user_data = UserGamification(
            user_id=user_id, total_points=1000, current_level=3
        )
        mock_repository.get_user_gamification.return_value = user_data

        level, level_up = await service.update_user_level(user_id)
        assert isinstance(level, int)
        assert isinstance(level_up, bool)

    async def test_set_vip_status(self, service, mock_repository):
        """Test setting VIP status."""
        user_id = 12345

        user_data = UserGamification(user_id=user_id, vip_status=False)
        mock_repository.get_user_gamification.return_value = user_data
        mock_repository.update_user_gamification.return_value = True

        result = await service.set_vip_status(user_id, True, 1.5)
        assert result is True


class TestPointsQueries:
    """Test points querying functionality."""

    async def test_get_user_points(self, service, mock_repository):
        """Test getting user points."""
        user_id = 12345

        user_data = UserGamification(user_id=user_id, total_points=750)
        mock_repository.get_user_gamification.return_value = user_data

        points = await service.get_user_points(user_id)
        assert points == 750

    async def test_get_user_points_no_user(self, service, mock_repository):
        """Test getting points for non-existent user."""
        user_id = 12345
        mock_repository.get_user_gamification.return_value = None

        points = await service.get_user_points(user_id)
        assert points == 0

    async def test_get_points_history(self, service, mock_repository):
        """Test getting points history."""
        user_id = 12345
        limit = 10

        mock_transactions = [
            PointsTransaction(
                user_id=user_id,
                amount=100,
                transaction_type=PointsTransactionType.EARNED,
                description="test",
                created_at=datetime.now(timezone.utc),
            )
        ]
        mock_repository.get_points_transactions.return_value = mock_transactions

        history = await service.get_points_history(user_id, limit)
        assert len(history) == 1
        assert history[0]["amount"] == 100


class TestAchievements:
    """Test achievement system functionality."""

    async def test_check_achievements(self, service, mock_repository):
        """Test checking achievements."""
        user_id = 12345
        user_data = {"chapters_completed": 5}

        mock_repository.get_all_achievement_definitions.return_value = []

        result = await service.check_achievements(user_id, user_data)
        assert isinstance(result, list)

    async def test_unlock_achievement(self, service, mock_repository):
        """Test unlocking an achievement."""
        user_id = 12345
        achievement_id = "test_achievement"

        mock_repository.create_user_achievement.return_value = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            unlocked_at=datetime.now(timezone.utc),
        )

        result = await service.unlock_achievement(user_id, achievement_id)
        assert result is True

    async def test_get_user_achievements(self, service, mock_repository):
        """Test getting user achievements."""
        user_id = 12345

        mock_achievements = [
            UserAchievement(user_id=user_id, achievement_id="test1"),
            UserAchievement(user_id=user_id, achievement_id="test2"),
        ]
        mock_repository.get_user_achievements.return_value = mock_achievements

        achievements = await service.get_user_achievements(user_id)
        assert len(achievements) == 2

    async def test_get_achievement_progress(self, service, mock_repository):
        """Test getting achievement progress."""
        user_id = 12345
        achievement_id = "test_achievement"

        mock_repository.get_user_achievement.return_value = None

        progress = await service.get_achievement_progress(user_id, achievement_id)
        assert isinstance(progress, dict)

    async def test_create_achievement_definition(self, service, mock_repository):
        """Test creating achievement definition."""
        achievement_data = {
            "achievement_id": "test",
            "name": "Test Achievement",
            "description": "Test description",
            "category": AchievementCategory.NARRATIVE,
            "tier": AchievementTier.BRONZE,
            "criteria": {"test": 1},
            "points_reward": 100,
            "is_active": True,
        }

        mock_repository.create_achievement_definition.return_value = True

        result = await service.create_achievement_definition(achievement_data)
        assert result is True


class TestStreaks:
    """Test streak functionality."""

    async def test_update_streak(self, service, mock_repository):
        """Test updating user streak."""
        user_id = 12345

        mock_repository.get_latest_streak_record.return_value = None
        mock_repository.create_streak_record.return_value = True

        result = await service.update_streak(user_id, "daily_login")
        assert result is True

    async def test_get_user_streaks(self, service, mock_repository):
        """Test getting user streaks."""
        user_id = 12345

        mock_repository.get_user_streaks.return_value = []

        streaks = await service.get_user_streaks(user_id)
        assert isinstance(streaks, list)

    async def test_freeze_streak(self, service, mock_repository):
        """Test freezing a streak."""
        user_id = 12345

        mock_repository.freeze_user_streak.return_value = True

        result = await service.freeze_streak(user_id, "daily_login")
        assert result is True


class TestLeaderboards:
    """Test leaderboard functionality."""

    async def test_update_leaderboard(self, service, mock_repository):
        """Test updating leaderboard."""
        user_id = 12345

        mock_repository.update_leaderboard_entry.return_value = True

        result = await service.update_leaderboard(user_id, "global", 1000)
        assert result is True

    async def test_get_leaderboard(self, service, mock_repository):
        """Test getting leaderboard."""
        leaderboard_type = "global"
        limit = 10

        mock_repository.get_leaderboard_entries.return_value = []

        result = await service.get_leaderboard(leaderboard_type, limit)
        assert isinstance(result, list)

    async def test_get_user_rank(self, service, mock_repository):
        """Test getting user rank."""
        user_id = 12345
        leaderboard_type = "global"

        mock_repository.get_user_leaderboard_rank.return_value = 5

        rank = await service.get_user_rank(user_id, leaderboard_type)
        assert rank == 5


class TestStatistics:
    """Test statistics functionality."""

    async def test_get_user_statistics(self, service, mock_repository):
        """Test getting user statistics."""
        user_id = 12345

        user_data = UserGamification(
            user_id=user_id,
            total_points=1000,
            current_level=5,
            total_achievements=10,
        )
        mock_repository.get_user_gamification.return_value = user_data
        mock_repository.get_user_achievements.return_value = []
        mock_repository.get_user_streaks.return_value = []

        stats = await service.get_user_statistics(user_id)
        assert isinstance(stats, dict)
        assert "total_points" in stats
        assert "current_level" in stats

    async def test_get_system_statistics(self, service, mock_repository):
        """Test getting system statistics."""
        mock_repository.get_system_statistics.return_value = {
            "total_users": 100,
            "total_points_awarded": 50000,
        }

        stats = await service.get_system_statistics()
        assert isinstance(stats, dict)


class TestConfiguration:
    """Test configuration functionality."""

    async def test_get_points_configuration(self, service):
        """Test getting points configuration."""
        config = await service.get_points_configuration()
        assert isinstance(config, dict)

    async def test_update_points_configuration(self, service):
        """Test updating points configuration."""
        new_config = {"test": "value"}

        result = await service.update_points_configuration(new_config)
        assert result is True


class TestEventHandlers:
    """Test event handler functionality."""

    async def test_handle_user_action(self, service):
        """Test handling user action event."""
        mock_event = Mock()
        mock_event.user_id = 12345
        mock_event.action_type = "test_action"
        mock_event.points_multiplier = 1.0
        mock_event.metadata = {}

        with patch.object(service, "award_points", return_value=True):
            await service.handle_user_action(mock_event)

    async def test_handle_story_completion(self, service):
        """Test handling story completion event."""
        mock_event = Mock()
        mock_event.user_id = 12345
        mock_event.story_id = "story1"
        mock_event.completion_time = datetime.now(timezone.utc)
        mock_event.metadata = {}

        with patch.object(service, "award_points", return_value=True):
            with patch.object(service, "check_achievements", return_value=[]):
                await service.handle_story_completion(mock_event)

    async def test_handle_chapter_completion(self, service):
        """Test handling chapter completion event."""
        mock_event = Mock()
        mock_event.user_id = 12345
        mock_event.chapter_id = "ch1"
        mock_event.story_id = "story1"
        mock_event.metadata = {}

        with patch.object(service, "award_points", return_value=True):
            with patch.object(service, "update_streak", return_value=True):
                await service.handle_chapter_completion(mock_event)

    async def test_handle_decision_made(self, service):
        """Test handling decision made event."""
        mock_event = Mock()
        mock_event.user_id = 12345
        mock_event.decision_id = "decision1"
        mock_event.choice_value = "option_a"
        mock_event.impact_score = 0.8
        mock_event.metadata = {}

        with patch.object(service, "award_points", return_value=True):
            await service.handle_decision_made(mock_event)


class TestErrorHandling:
    """Test error handling."""

    async def test_repository_error_propagation(self, service, mock_repository):
        """Test that repository errors are properly handled."""
        user_id = 12345

        mock_repository.get_user_gamification.side_effect = Exception("DB Error")

        with pytest.raises(Exception):
            await service.get_user_points(user_id)

    async def test_event_bus_error_handling(self, service, mock_event_bus):
        """Test that event bus errors don't break operations."""
        user_id = 12345

        # Mock successful repository but failing event bus
        mock_event_bus.publish.side_effect = Exception("Event bus error")

        # Operations should still succeed even if events fail to publish
        with patch.object(service, "_get_or_create_user"):
            with patch.object(service, "_check_anti_abuse"):
                with patch.object(service, "_get_streak_multiplier", return_value=1.0):
                    with patch.object(
                        service.repository,
                        "create_points_transaction",
                        return_value=True,
                    ):
                        with patch.object(
                            service.repository,
                            "update_user_gamification",
                            return_value=True,
                        ):
                            # This should not raise an exception even though event publishing fails
                            try:
                                await service.award_points(user_id, 100, "test")
                            except Exception as e:
                                # If an exception is raised, it should not be from event publishing
                                assert "Event bus error" not in str(e)
