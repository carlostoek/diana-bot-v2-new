"""
Tests for GamificationService.

This module contains comprehensive tests for the gamification service,
covering points system, achievements, leaderboards, and event handling.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# from src.core.event_bus import RedisEventBus  # Not needed for mocked tests
from src.core.events.core import UserActionEvent
from src.core.events.gamification import AchievementUnlockedEvent, PointsAwardedEvent
from src.core.events.narrative import (
    ChapterCompletedEvent,
    DecisionMadeEvent,
    StoryCompletionEvent,
)
from src.models.gamification import (
    AchievementCategory,
    AchievementDefinition,
    AchievementTier,
    LeaderboardType,
    PointsTransaction,
    PointsTransactionType,
    StreakType,
    UserAchievement,
    UserGamification,
)
from src.services.gamification.interfaces import (
    AntiAbuseError,
    IGamificationRepository,
    InsufficientPointsError,
    UserNotFoundError,
)
from src.services.gamification.service import GamificationService


class MockGamificationRepository(IGamificationRepository):
    """Mock repository for testing."""

    def __init__(self):
        self.users: Dict[int, UserGamification] = {}
        self.transactions: List[PointsTransaction] = []
        self.achievements: List[AchievementDefinition] = []
        self.user_achievements: List[UserAchievement] = []
        self.streaks: List[Any] = []
        self.leaderboard_entries: List[Any] = []

    async def initialize(self):
        pass

    async def get_user_gamification(self, user_id: int) -> Optional[UserGamification]:
        return self.users.get(user_id)

    async def create_user_gamification(self, user_id: int) -> UserGamification:
        user_gam = UserGamification(user_id=user_id)
        self.users[user_id] = user_gam
        return user_gam

    async def update_user_gamification(
        self, user_gamification: UserGamification
    ) -> UserGamification:
        self.users[user_gamification.user_id] = user_gamification
        return user_gamification

    async def create_points_transaction(self, transaction_data: Dict[str, Any]) -> Any:
        transaction = MagicMock()
        transaction.id = len(self.transactions) + 1
        for key, value in transaction_data.items():
            setattr(transaction, key, value)
        transaction.created_at = datetime.now(timezone.utc)
        self.transactions.append(transaction)
        return transaction

    async def get_points_transactions(
        self,
        user_id: int,
        limit: int,
        offset: int,
        transaction_type: Optional[PointsTransactionType],
    ) -> List[Any]:
        user_transactions = [t for t in self.transactions if t.user_id == user_id]
        if transaction_type:
            user_transactions = [
                t for t in user_transactions if t.transaction_type == transaction_type
            ]
        return user_transactions[offset : offset + limit]

    async def get_achievement_definitions(
        self, active_only: bool = True
    ) -> List[AchievementDefinition]:
        achievements = self.achievements
        if active_only:
            achievements = [a for a in achievements if a.is_active]
        return achievements

    async def create_achievement_definition(
        self, achievement_data: Dict[str, Any]
    ) -> AchievementDefinition:
        achievement = AchievementDefinition(
            id=achievement_data["id"],
            name=achievement_data["name"],
            description=achievement_data["description"],
            category=achievement_data["category"],
            tier=achievement_data["tier"],
            points_reward=achievement_data.get("points_reward", 0),
            unlock_criteria=achievement_data["unlock_criteria"],
            is_secret=achievement_data.get("is_secret", False),
            is_repeatable=achievement_data.get("is_repeatable", False),
            is_active=achievement_data.get("is_active", True),
        )
        self.achievements.append(achievement)
        return achievement

    async def get_user_achievements(
        self, user_id: int, completed_only: bool = False
    ) -> List[UserAchievement]:
        user_achievements = [
            ua for ua in self.user_achievements if ua.user_id == user_id
        ]
        if completed_only:
            user_achievements = [ua for ua in user_achievements if ua.is_completed]
        return user_achievements

    async def create_user_achievement(
        self, achievement_data: Dict[str, Any]
    ) -> UserAchievement:
        user_achievement = UserAchievement(
            user_id=achievement_data["user_id"],
            achievement_id=achievement_data["achievement_id"],
            progress_current=achievement_data.get("progress_current", 0),
            progress_required=achievement_data.get("progress_required", 1),
            is_completed=achievement_data.get("is_completed", False),
            unlocked_at=achievement_data.get("unlocked_at"),
            points_awarded=achievement_data.get("points_awarded", 0),
        )
        user_achievement.id = len(self.user_achievements) + 1
        self.user_achievements.append(user_achievement)
        return user_achievement

    async def update_user_achievement(
        self, user_achievement: UserAchievement
    ) -> UserAchievement:
        for i, ua in enumerate(self.user_achievements):
            if ua.id == user_achievement.id:
                self.user_achievements[i] = user_achievement
                break
        return user_achievement

    async def get_user_streaks(self, user_id: int) -> List[Any]:
        return [s for s in self.streaks if s.user_id == user_id]

    async def update_streak_record(self, streak_data: Dict[str, Any]) -> Any:
        streak = MagicMock()
        for key, value in streak_data.items():
            setattr(streak, key, value)
        self.streaks.append(streak)
        return streak

    async def update_leaderboard_entry(self, entry_data: Dict[str, Any]) -> Any:
        entry = MagicMock()
        for key, value in entry_data.items():
            setattr(entry, key, value)
        self.leaderboard_entries.append(entry)
        return entry

    async def get_leaderboard_entries(
        self,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
        limit: int,
    ) -> List[Any]:
        return self.leaderboard_entries[:limit]


@pytest.fixture
async def mock_event_bus():
    """Create a mock event bus."""
    event_bus = MagicMock()
    event_bus.subscribe = AsyncMock(return_value="subscription_id")
    event_bus.unsubscribe = AsyncMock(return_value=True)
    event_bus.publish = AsyncMock(return_value=True)
    return event_bus


@pytest.fixture
async def mock_repository():
    """Create a mock repository."""
    return MockGamificationRepository()


@pytest.fixture
async def gamification_service(mock_event_bus, mock_repository):
    """Create a gamification service with mocked dependencies."""
    service = GamificationService(
        event_bus=mock_event_bus,
        repository=mock_repository,
        config={
            "points": {
                "daily_login": 50,
                "story_complete": 500,
                "chapter_complete": 150,
                "decision_made": 200,
            },
            "anti_abuse": {
                "max_points_per_hour": 1000,
                "max_actions_per_minute": 10,
                "suspicious_threshold": 5000,
            },
            "streak_multipliers": {
                "1-7": 1.1,
                "8-14": 1.2,
                "15-30": 1.3,
                "31+": 1.5,
            },
            "level_progression": [0, 100, 300, 600, 1000],
        },
    )
    await service.initialize()
    return service


class TestGamificationServiceInitialization:
    """Test service initialization and shutdown."""

    async def test_initialize_service(self, mock_event_bus, mock_repository):
        """Test successful service initialization."""
        service = GamificationService(mock_event_bus, mock_repository)

        await service.initialize()

        assert service._is_initialized is True
        assert len(service._subscription_ids) > 0
        mock_event_bus.subscribe.assert_called()

    async def test_shutdown_service(self, gamification_service, mock_event_bus):
        """Test service shutdown."""
        await gamification_service.shutdown()

        assert gamification_service._is_initialized is False
        assert len(gamification_service._subscription_ids) == 0
        mock_event_bus.unsubscribe.assert_called()


class TestPointsSystem:
    """Test points system functionality."""

    async def test_award_points_new_user(self, gamification_service, mock_event_bus):
        """Test awarding points to a new user."""
        user_id = 123
        points_amount = 100
        action_type = "story_complete"

        result = await gamification_service.award_points(
            user_id=user_id,
            points_amount=points_amount,
            action_type=action_type,
        )

        assert result is True

        # Check user was created and points awarded
        user_gam = await gamification_service.repository.get_user_gamification(user_id)
        assert user_gam is not None
        assert user_gam.total_points == points_amount
        assert user_gam.experience_points == points_amount

        # Check transaction was created
        transactions = await gamification_service.repository.get_points_transactions(
            user_id, 10, 0, None
        )
        assert len(transactions) == 1
        assert transactions[0].amount == points_amount
        assert transactions[0].action_type == action_type

        # Check event was published
        mock_event_bus.publish.assert_called()

    async def test_award_points_existing_user(self, gamification_service):
        """Test awarding points to an existing user."""
        user_id = 456

        # Create user with initial points
        await gamification_service.award_points(user_id, 100, "initial")
        initial_points = await gamification_service.get_user_points(user_id)

        # Award more points
        additional_points = 50
        await gamification_service.award_points(user_id, additional_points, "bonus")

        final_points = await gamification_service.get_user_points(user_id)
        assert final_points == initial_points + additional_points

    async def test_award_points_with_multiplier(self, gamification_service):
        """Test awarding points with multiplier."""
        user_id = 789
        base_points = 100
        multiplier = 1.5
        bonus_points = 25

        await gamification_service.award_points(
            user_id=user_id,
            points_amount=base_points,
            action_type="test",
            multiplier=multiplier,
            bonus_points=bonus_points,
        )

        expected_points = int(base_points * multiplier) + bonus_points
        actual_points = await gamification_service.get_user_points(user_id)
        assert actual_points == expected_points

    async def test_award_points_vip_multiplier(self, gamification_service):
        """Test VIP multiplier is applied."""
        user_id = 101

        # Set user as VIP
        await gamification_service.set_vip_status(user_id, True, 2.0)

        # Award points
        base_points = 100
        await gamification_service.award_points(user_id, base_points, "test")

        # Should have VIP multiplier applied
        expected_points = int(base_points * 2.0)  # VIP multiplier
        actual_points = await gamification_service.get_user_points(user_id)
        assert actual_points == expected_points

    async def test_deduct_points_success(self, gamification_service):
        """Test successful points deduction."""
        user_id = 202

        # Give user initial points
        initial_points = 200
        await gamification_service.award_points(user_id, initial_points, "initial")

        # Deduct points
        deduction_amount = 50
        result = await gamification_service.deduct_points(
            user_id=user_id,
            points_amount=deduction_amount,
            deduction_reason="test_penalty",
        )

        assert result is True

        final_points = await gamification_service.get_user_points(user_id)
        assert final_points == initial_points - deduction_amount

    async def test_deduct_points_insufficient_funds(self, gamification_service):
        """Test deduction fails with insufficient points."""
        user_id = 303

        # Give user some points
        await gamification_service.award_points(user_id, 50, "initial")

        # Try to deduct more than available
        with pytest.raises(InsufficientPointsError):
            await gamification_service.deduct_points(
                user_id=user_id,
                points_amount=100,
                deduction_reason="test_penalty",
            )

    async def test_deduct_points_user_not_found(self, gamification_service):
        """Test deduction fails for non-existent user."""
        user_id = 404

        with pytest.raises(UserNotFoundError):
            await gamification_service.deduct_points(
                user_id=user_id,
                points_amount=50,
                deduction_reason="test_penalty",
            )

    async def test_anti_abuse_rate_limiting(self, gamification_service):
        """Test anti-abuse rate limiting."""
        user_id = 505

        # Rapidly award points to trigger rate limiting
        for i in range(15):  # Exceeds max_actions_per_minute (10)
            if i < 10:
                await gamification_service.award_points(user_id, 10, f"action_{i}")
            else:
                with pytest.raises(AntiAbuseError):
                    await gamification_service.award_points(user_id, 10, f"action_{i}")

    async def test_get_points_history(self, gamification_service):
        """Test retrieving points transaction history."""
        user_id = 606

        # Create multiple transactions
        await gamification_service.award_points(user_id, 100, "action1")
        await gamification_service.award_points(user_id, 50, "action2")

        history = await gamification_service.get_points_history(user_id, limit=10)

        assert len(history) == 2
        assert history[0]["amount"] == 50  # Most recent first
        assert history[1]["amount"] == 100
        assert all("action_type" in tx for tx in history)

    async def test_invalid_points_amount(self, gamification_service):
        """Test error handling for invalid points amounts."""
        user_id = 707

        with pytest.raises(ValueError):
            await gamification_service.award_points(user_id, 0, "invalid")

        with pytest.raises(ValueError):
            await gamification_service.award_points(user_id, -10, "invalid")


class TestAchievementSystem:
    """Test achievement system functionality."""

    async def test_create_achievement_definition(self, gamification_service):
        """Test creating achievement definitions."""
        achievement_data = {
            "id": "test_achievement",
            "name": "Test Achievement",
            "description": "A test achievement",
            "category": AchievementCategory.MILESTONE,
            "tier": AchievementTier.BRONZE,
            "points_reward": 100,
            "unlock_criteria": {"total_points": 1000},
        }

        achievement = await gamification_service.create_achievement_definition(
            achievement_data
        )

        assert achievement.id == "test_achievement"
        assert achievement.name == "Test Achievement"
        assert achievement.points_reward == 100

    async def test_unlock_achievement_manual(self, gamification_service):
        """Test manually unlocking an achievement."""
        user_id = 808
        achievement_id = "manual_test"

        # Create achievement definition first
        await gamification_service.repository.create_achievement_definition(
            {
                "id": achievement_id,
                "name": "Manual Test",
                "description": "Manually unlocked",
                "category": AchievementCategory.SPECIAL,
                "tier": AchievementTier.GOLD,
                "points_reward": 500,
                "unlock_criteria": {},
            }
        )

        user_achievement = await gamification_service.unlock_achievement(
            user_id=user_id,
            achievement_id=achievement_id,
        )

        assert user_achievement.user_id == user_id
        assert user_achievement.achievement_id == achievement_id
        assert user_achievement.is_completed is True

    async def test_get_user_achievements(self, gamification_service):
        """Test retrieving user achievements."""
        user_id = 909

        # Create and unlock an achievement
        achievement_id = "test_user_achievement"
        await gamification_service.repository.create_achievement_definition(
            {
                "id": achievement_id,
                "name": "Test User Achievement",
                "description": "Test",
                "category": AchievementCategory.ENGAGEMENT,
                "tier": AchievementTier.SILVER,
                "points_reward": 200,
                "unlock_criteria": {},
            }
        )

        await gamification_service.unlock_achievement(user_id, achievement_id)

        achievements = await gamification_service.get_user_achievements(user_id)
        assert len(achievements) == 1
        assert achievements[0].achievement_id == achievement_id

        completed_achievements = await gamification_service.get_user_achievements(
            user_id, completed_only=True
        )
        assert len(completed_achievements) == 1

    async def test_get_achievement_progress(self, gamification_service):
        """Test getting achievement progress."""
        user_id = 1010
        achievement_id = "progress_test"

        # Create achievement and user achievement
        await gamification_service.repository.create_achievement_definition(
            {
                "id": achievement_id,
                "name": "Progress Test",
                "description": "Test progress tracking",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.BRONZE,
                "points_reward": 100,
                "unlock_criteria": {"stories_completed": 5},
            }
        )

        await gamification_service.repository.create_user_achievement(
            {
                "user_id": user_id,
                "achievement_id": achievement_id,
                "progress_current": 3,
                "progress_required": 5,
                "is_completed": False,
            }
        )

        progress = await gamification_service.get_achievement_progress(
            user_id, achievement_id
        )
        assert progress is not None
        assert progress.progress_current == 3
        assert progress.progress_required == 5
        assert progress.is_completed is False


class TestUserManagement:
    """Test user management functionality."""

    async def test_initialize_user(self, gamification_service):
        """Test initializing a new user."""
        user_id = 1111

        user_gam = await gamification_service.initialize_user(user_id)

        assert user_gam.user_id == user_id
        assert user_gam.total_points == 0
        assert user_gam.current_level == 1
        assert user_gam.vip_status is False

    async def test_get_user_gamification(self, gamification_service):
        """Test retrieving user gamification data."""
        user_id = 1212

        # User doesn't exist yet
        user_gam = await gamification_service.get_user_gamification(user_id)
        assert user_gam is None

        # Initialize user
        await gamification_service.initialize_user(user_id)

        # Now should exist
        user_gam = await gamification_service.get_user_gamification(user_id)
        assert user_gam is not None
        assert user_gam.user_id == user_id

    async def test_update_user_level(self, gamification_service):
        """Test user level progression."""
        user_id = 1313

        # Initialize user
        await gamification_service.initialize_user(user_id)

        # Award experience points for level up
        await gamification_service.award_points(
            user_id, 300, "level_test"
        )  # Should reach level 3

        new_level, level_increased = await gamification_service.update_user_level(
            user_id
        )

        assert new_level == 3  # Based on config: [0, 100, 300, 600, 1000]
        assert level_increased is True

    async def test_set_vip_status(self, gamification_service):
        """Test setting VIP status."""
        user_id = 1414

        # Initialize user
        await gamification_service.initialize_user(user_id)

        # Set VIP status
        result = await gamification_service.set_vip_status(user_id, True, 2.0)
        assert result is True

        user_gam = await gamification_service.get_user_gamification(user_id)
        assert user_gam.vip_status is True
        assert user_gam.vip_multiplier == 2.0

        # Unset VIP status
        await gamification_service.set_vip_status(user_id, False)
        user_gam = await gamification_service.get_user_gamification(user_id)
        assert user_gam.vip_status is False
        assert user_gam.vip_multiplier == 1.0

    async def test_get_user_statistics(self, gamification_service):
        """Test retrieving user statistics."""
        user_id = 1515

        # Initialize user and add some data
        await gamification_service.initialize_user(user_id)
        await gamification_service.award_points(user_id, 500, "test")

        stats = await gamification_service.get_user_statistics(user_id)

        assert "total_points" in stats
        assert "current_level" in stats
        assert "experience_points" in stats
        assert stats["total_points"] == 500


class TestEventHandlers:
    """Test event handling functionality."""

    async def test_handle_user_action_event(self, gamification_service):
        """Test handling UserActionEvent."""
        user_id = 1616

        # Create a UserActionEvent
        event = UserActionEvent(
            user_id=user_id,
            action_type="daily_login",
            action_data={"timestamp": "2024-01-01T00:00:00Z"},
            source_service="telegram",
        )

        await gamification_service.handle_user_action(event)

        # Check points were awarded
        points = await gamification_service.get_user_points(user_id)
        assert points == 50  # daily_login points from config

    async def test_handle_story_completion_event(self, gamification_service):
        """Test handling StoryCompletionEvent."""
        user_id = 1717

        # Create a StoryCompletionEvent
        event = StoryCompletionEvent(
            user_id=user_id,
            story_id="test_story",
            story_title="Test Story",
            story_category="adventure",
            total_completion_time_seconds=3600,
            total_chapters_completed=10,
            total_decisions_made=25,
            ending_achieved="happy_ending",
            completion_percentage=100.0,
            overall_rating=5,
            source_service="narrative",
        )

        await gamification_service.handle_story_completion(event)

        # Check points were awarded (base + bonus for 100% completion + rating bonus)
        points = await gamification_service.get_user_points(user_id)
        expected_points = 500 + 200 + 100  # base + completion bonus + rating bonus
        assert points == expected_points

    async def test_handle_chapter_completion_event(self, gamification_service):
        """Test handling ChapterCompletedEvent."""
        user_id = 1818

        # Create a ChapterCompletedEvent
        event = ChapterCompletedEvent(
            user_id=user_id,
            story_id="test_story",
            chapter_id="chapter_1",
            chapter_title="Chapter 1",
            completion_time_seconds=600,
            decisions_made=3,
            character_interactions=5,
            source_service="narrative",
        )

        await gamification_service.handle_chapter_completion(event)

        # Check points were awarded
        points = await gamification_service.get_user_points(user_id)
        assert points == 150  # chapter_complete points from config

    async def test_handle_decision_made_event(self, gamification_service):
        """Test handling DecisionMadeEvent."""
        user_id = 1919

        # Create a DecisionMadeEvent
        event = DecisionMadeEvent(
            user_id=user_id,
            story_id="test_story",
            chapter_id="chapter_1",
            decision_point_id="decision_1",
            decision_id="choice_a",
            decision_text="Choose option A",
            decision_consequences={"relationship_change": {"character_1": 0.1}},
            source_service="narrative",
        )

        await gamification_service.handle_decision_made(event)

        # Check points were awarded
        points = await gamification_service.get_user_points(user_id)
        assert points == 200  # decision_made points from config


class TestStreakSystem:
    """Test streak system functionality."""

    async def test_update_streak(self, gamification_service):
        """Test updating user streaks."""
        user_id = 2020

        result = await gamification_service.update_streak(
            user_id, StreakType.DAILY_LOGIN
        )

        assert "streak_type" in result
        assert result["streak_type"] == StreakType.DAILY_LOGIN.value

    async def test_get_user_streaks(self, gamification_service):
        """Test retrieving user streaks."""
        user_id = 2121

        # Create a streak record
        await gamification_service.repository.update_streak_record(
            {
                "user_id": user_id,
                "streak_type": StreakType.DAILY_LOGIN,
                "current_count": 5,
                "longest_count": 10,
                "current_multiplier": 1.1,
                "is_active": True,
            }
        )

        streaks = await gamification_service.get_user_streaks(user_id)

        assert len(streaks) == 1
        assert streaks[0]["streak_type"] == StreakType.DAILY_LOGIN.value
        assert streaks[0]["current_count"] == 5

    async def test_freeze_streak(self, gamification_service):
        """Test streak freeze functionality."""
        user_id = 2222

        result = await gamification_service.freeze_streak(
            user_id, StreakType.DAILY_LOGIN
        )

        assert result is True


class TestLeaderboardSystem:
    """Test leaderboard system functionality."""

    async def test_update_leaderboard(self, gamification_service):
        """Test updating leaderboard entries."""
        user_id = 2323
        period_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_end = period_start + timedelta(days=7)

        result = await gamification_service.update_leaderboard(
            user_id=user_id,
            leaderboard_type=LeaderboardType.WEEKLY,
            score=1500,
            period_start=period_start,
            period_end=period_end,
        )

        assert "leaderboard_type" in result
        assert result["leaderboard_type"] == LeaderboardType.WEEKLY.value
        assert result["score"] == 1500

    async def test_get_leaderboard(self, gamification_service):
        """Test retrieving leaderboard."""
        period_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_end = period_start + timedelta(days=7)

        leaderboard = await gamification_service.get_leaderboard(
            leaderboard_type=LeaderboardType.WEEKLY,
            period_start=period_start,
            period_end=period_end,
            limit=10,
        )

        assert "leaderboard_type" in leaderboard
        assert "entries" in leaderboard
        assert leaderboard["leaderboard_type"] == LeaderboardType.WEEKLY.value

    async def test_get_user_rank(self, gamification_service):
        """Test getting user rank."""
        user_id = 2424
        period_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_end = period_start + timedelta(days=7)

        rank = await gamification_service.get_user_rank(
            user_id=user_id,
            leaderboard_type=LeaderboardType.WEEKLY,
            period_start=period_start,
            period_end=period_end,
        )

        # Should return None for non-existent entry
        assert rank is None


class TestConfiguration:
    """Test configuration management."""

    async def test_get_points_configuration(self, gamification_service):
        """Test retrieving points configuration."""
        config = await gamification_service.get_points_configuration()

        assert "daily_login" in config
        assert "story_complete" in config
        assert config["daily_login"] == 50

    async def test_update_points_configuration(self, gamification_service):
        """Test updating points configuration."""
        new_config = {"daily_login": 75, "new_action": 25}

        result = await gamification_service.update_points_configuration(new_config)
        assert result is True

        updated_config = await gamification_service.get_points_configuration()
        assert updated_config["daily_login"] == 75
        assert updated_config["new_action"] == 25

    async def test_get_system_statistics(self, gamification_service):
        """Test retrieving system statistics."""
        stats = await gamification_service.get_system_statistics()

        assert "total_users" in stats
        assert "total_points_awarded" in stats
        assert "total_achievements_unlocked" in stats
        assert all(isinstance(v, int) for v in stats.values())


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/unit/services/gamification/test_service.py -v
    pytest.main([__file__, "-v"])
