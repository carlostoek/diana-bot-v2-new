"""
Unit tests for the complete Gamification Service Implementation.

Tests the main service orchestrator with all engines integrated,
event handling, and comprehensive business logic.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.event_bus import RedisEventBus
from src.models.gamification import (
    AchievementCategory,
    AchievementDefinition,
    AchievementTier,
    LeaderboardType,
    PointsTransactionType,
    StreakType,
    UserAchievement,
    UserGamification,
)
from src.services.gamification.interfaces import (
    AntiAbuseError,
    GamificationError,
    InsufficientPointsError,
    UserNotFoundError,
)
from src.services.gamification.service_impl import GamificationServiceImpl


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    event_bus = MagicMock(spec=RedisEventBus)
    event_bus.subscribe = AsyncMock()
    event_bus.unsubscribe = AsyncMock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = MagicMock()
    repo.initialize = AsyncMock()
    repo.shutdown = AsyncMock()
    repo.get_user_gamification = AsyncMock()
    repo.create_user_gamification = AsyncMock()
    repo.update_user_gamification = AsyncMock()
    repo.create_points_transaction = AsyncMock()
    repo.get_points_transactions = AsyncMock()
    repo.get_achievement_definitions = AsyncMock()
    repo.create_achievement_definition = AsyncMock()
    repo.get_user_achievements = AsyncMock()
    repo.create_user_achievement = AsyncMock()
    repo.get_user_streaks = AsyncMock()
    repo.update_streak_record = AsyncMock()
    repo.get_leaderboard_entries = AsyncMock()
    repo.update_leaderboard_entry = AsyncMock()
    repo.get_system_statistics = AsyncMock()
    repo.get_achievement_completion_count = AsyncMock()
    return repo


@pytest.fixture
def mock_user_gamification():
    """Create a mock user gamification object."""
    user_gam = MagicMock(spec=UserGamification)
    user_gam.user_id = 123
    user_gam.total_points = 1000
    user_gam.current_level = 5
    user_gam.experience_points = 1500
    user_gam.vip_status = False
    user_gam.vip_multiplier = 1.0
    user_gam.total_achievements = 3
    user_gam.current_daily_streak = 5
    user_gam.longest_daily_streak = 10
    return user_gam


@pytest.fixture
def gamification_service(mock_event_bus, mock_repository):
    """Create a gamification service instance for testing."""
    return GamificationServiceImpl(event_bus=mock_event_bus, repository=mock_repository)


class TestServiceInitialization:
    """Test service initialization and lifecycle."""

    @pytest.mark.asyncio
    async def test_service_initialization(
        self, gamification_service, mock_repository, mock_event_bus
    ):
        """Test service initialization process."""
        # Mock repository methods
        mock_repository.get_achievement_definitions.return_value = []

        await gamification_service.initialize()

        # Verify initialization steps
        mock_repository.initialize.assert_called_once()
        mock_event_bus.subscribe.assert_called()  # Should be called for event subscriptions
        assert gamification_service._is_initialized is True

    @pytest.mark.asyncio
    async def test_service_shutdown(
        self, gamification_service, mock_repository, mock_event_bus
    ):
        """Test service shutdown process."""
        # Initialize first
        gamification_service._is_initialized = True
        gamification_service._subscription_ids = ["sub1", "sub2"]

        await gamification_service.shutdown()

        # Verify shutdown steps
        assert mock_event_bus.unsubscribe.call_count == 2
        mock_repository.shutdown.assert_called_once()
        assert gamification_service._is_initialized is False

    @pytest.mark.asyncio
    async def test_double_initialization_ignored(
        self, gamification_service, mock_repository
    ):
        """Test that double initialization is ignored."""
        gamification_service._is_initialized = True

        await gamification_service.initialize()

        # Repository initialize should not be called
        mock_repository.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialization_failure(self, gamification_service, mock_repository):
        """Test handling of initialization failures."""
        mock_repository.initialize.side_effect = Exception("Database connection failed")

        with pytest.raises(GamificationError, match="Service initialization failed"):
            await gamification_service.initialize()


class TestPointsSystem:
    """Test points system functionality."""

    @pytest.mark.asyncio
    async def test_award_points_success(
        self,
        gamification_service,
        mock_repository,
        mock_event_bus,
        mock_user_gamification,
    ):
        """Test successful points award."""
        # Setup mocks
        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.get_user_streaks.return_value = []
        mock_repository.create_points_transaction.return_value = MagicMock()
        mock_repository.update_user_gamification.return_value = mock_user_gamification
        mock_repository.get_achievement_definitions.return_value = []
        mock_repository.get_user_achievements.return_value = []
        mock_repository.get_achievement_completion_count.return_value = 3

        result = await gamification_service.award_points(
            user_id=123, points_amount=100, action_type="test_action"
        )

        assert result is True
        mock_repository.create_points_transaction.assert_called_once()
        mock_repository.update_user_gamification.assert_called_once()
        mock_event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_award_points_with_multipliers(
        self,
        gamification_service,
        mock_repository,
        mock_event_bus,
        mock_user_gamification,
    ):
        """Test points award with multipliers and bonuses."""
        # Setup VIP user
        mock_user_gamification.vip_status = True
        mock_user_gamification.vip_multiplier = 1.5

        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.get_user_streaks.return_value = []
        mock_repository.create_points_transaction.return_value = MagicMock()
        mock_repository.update_user_gamification.return_value = mock_user_gamification
        mock_repository.get_achievement_definitions.return_value = []
        mock_repository.get_user_achievements.return_value = []
        mock_repository.get_achievement_completion_count.return_value = 3

        result = await gamification_service.award_points(
            user_id=123,
            points_amount=100,
            action_type="test_action",
            multiplier=1.2,
            bonus_points=50,
        )

        assert result is True

        # Verify transaction was created with calculated points
        call_args = mock_repository.create_points_transaction.call_args[0][0]
        assert (
            call_args["amount"] > 100
        )  # Should be more due to multipliers and bonuses

    @pytest.mark.asyncio
    async def test_award_points_anti_abuse_failure(
        self, gamification_service, mock_repository
    ):
        """Test points award failure due to anti-abuse."""
        mock_repository.get_user_gamification.return_value = mock_user_gamification

        # Mock anti-abuse validation to raise error
        with patch.object(
            gamification_service.points_engine, "validate_points_transaction"
        ) as mock_validate:
            mock_validate.side_effect = AntiAbuseError("Rate limit exceeded")

            with pytest.raises(AntiAbuseError):
                await gamification_service.award_points(
                    user_id=123, points_amount=100, action_type="test_action"
                )

    @pytest.mark.asyncio
    async def test_deduct_points_success(
        self,
        gamification_service,
        mock_repository,
        mock_event_bus,
        mock_user_gamification,
    ):
        """Test successful points deduction."""
        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.create_points_transaction.return_value = MagicMock()
        mock_repository.update_user_gamification.return_value = mock_user_gamification

        result = await gamification_service.deduct_points(
            user_id=123, points_amount=100, deduction_reason="Test penalty"
        )

        assert result is True
        mock_repository.create_points_transaction.assert_called_once()
        mock_repository.update_user_gamification.assert_called_once()
        mock_event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_deduct_points_insufficient_balance(
        self, gamification_service, mock_repository, mock_user_gamification
    ):
        """Test points deduction with insufficient balance."""
        mock_user_gamification.total_points = 50  # Less than deduction amount
        mock_repository.get_user_gamification.return_value = mock_user_gamification

        with pytest.raises(InsufficientPointsError):
            await gamification_service.deduct_points(
                user_id=123, points_amount=100, deduction_reason="Test penalty"
            )

    @pytest.mark.asyncio
    async def test_deduct_points_user_not_found(
        self, gamification_service, mock_repository
    ):
        """Test points deduction when user is not found."""
        mock_repository.get_user_gamification.return_value = None

        with pytest.raises(UserNotFoundError):
            await gamification_service.deduct_points(
                user_id=999, points_amount=100, deduction_reason="Test penalty"
            )

    @pytest.mark.asyncio
    async def test_get_user_points(
        self, gamification_service, mock_repository, mock_user_gamification
    ):
        """Test getting user points."""
        mock_repository.get_user_gamification.return_value = mock_user_gamification

        points = await gamification_service.get_user_points(123)

        assert points == 1000

    @pytest.mark.asyncio
    async def test_get_user_points_no_user(self, gamification_service, mock_repository):
        """Test getting points for non-existent user."""
        mock_repository.get_user_gamification.return_value = None

        points = await gamification_service.get_user_points(999)

        assert points == 0

    @pytest.mark.asyncio
    async def test_get_points_history(self, gamification_service, mock_repository):
        """Test getting points transaction history."""
        mock_transactions = [
            MagicMock(
                id=1,
                amount=100,
                transaction_type=PointsTransactionType.EARNED,
                action_type="test_action",
                description="Test transaction",
                points_before=500,
                points_after=600,
                multiplier_applied=1.0,
                bonus_applied=0,
                created_at=datetime.now(timezone.utc),
                transaction_metadata={},
            )
        ]
        mock_repository.get_points_transactions.return_value = mock_transactions

        history = await gamification_service.get_points_history(123, limit=10)

        assert len(history) == 1
        assert history[0]["amount"] == 100
        assert history[0]["transaction_type"] == "earned"


class TestAchievementSystem:
    """Test achievement system functionality."""

    @pytest.mark.asyncio
    async def test_check_achievements_unlock(
        self, gamification_service, mock_repository, mock_event_bus
    ):
        """Test checking and unlocking achievements."""
        # Setup achievement definitions
        achievement_def = MagicMock(spec=AchievementDefinition)
        achievement_def.id = "test_achievement"
        achievement_def.name = "Test Achievement"
        achievement_def.category = AchievementCategory.MILESTONE
        achievement_def.tier = AchievementTier.BRONZE
        achievement_def.points_reward = 100
        achievement_def.unlock_criteria = {"total_points": 1000}

        mock_repository.get_user_achievements.return_value = []
        mock_repository.get_achievement_definitions.return_value = [achievement_def]
        mock_repository.get_achievement_completion_count.return_value = 0
        mock_repository.create_user_achievement.return_value = MagicMock()
        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.update_user_gamification.return_value = mock_user_gamification
        mock_repository.create_points_transaction.return_value = MagicMock()
        mock_repository.get_user_streaks.return_value = []

        # Mock achievement engine evaluation
        with patch.object(
            gamification_service.achievement_engine, "evaluate_achievements"
        ) as mock_evaluate:
            mock_evaluate.return_value = [(achievement_def, {"criteria_met": {}})]

            with patch.object(
                gamification_service.achievement_engine, "create_user_achievement"
            ) as mock_create:
                mock_create.return_value = {
                    "user_id": 123,
                    "achievement_id": "test_achievement",
                    "is_completed": True,
                    "points_awarded": 100,
                }

                unlocked = await gamification_service.check_achievements(
                    user_id=123,
                    trigger_context={
                        "action_type": "points_awarded",
                        "total_points": 1000,
                    },
                )

                assert len(unlocked) == 1
                mock_repository.create_user_achievement.assert_called_once()
                mock_event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_unlock_achievement_manual(
        self, gamification_service, mock_repository, mock_event_bus
    ):
        """Test manually unlocking an achievement."""
        # Setup achievement definition
        achievement_def = MagicMock(spec=AchievementDefinition)
        achievement_def.id = "test_achievement"
        achievement_def.name = "Test Achievement"
        achievement_def.points_reward = 100

        mock_repository.get_achievement_definitions.return_value = [achievement_def]
        mock_repository.create_user_achievement.return_value = MagicMock()
        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.update_user_gamification.return_value = mock_user_gamification
        mock_repository.create_points_transaction.return_value = MagicMock()
        mock_repository.get_user_streaks.return_value = []

        with patch.object(
            gamification_service.achievement_engine, "create_user_achievement"
        ) as mock_create:
            mock_create.return_value = {
                "user_id": 123,
                "achievement_id": "test_achievement",
                "is_completed": True,
                "points_awarded": 100,
            }

            result = await gamification_service.unlock_achievement(
                user_id=123, achievement_id="test_achievement"
            )

            assert result is not None
            mock_repository.create_user_achievement.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlock_achievement_not_found(
        self, gamification_service, mock_repository
    ):
        """Test unlocking non-existent achievement."""
        mock_repository.get_achievement_definitions.return_value = []

        with pytest.raises(GamificationError, match="Achievement .* not found"):
            await gamification_service.unlock_achievement(
                user_id=123, achievement_id="nonexistent"
            )

    @pytest.mark.asyncio
    async def test_get_user_achievements(self, gamification_service, mock_repository):
        """Test getting user achievements."""
        mock_achievements = [MagicMock()]
        mock_repository.get_user_achievements.return_value = mock_achievements

        achievements = await gamification_service.get_user_achievements(123)

        assert achievements == mock_achievements
        mock_repository.get_user_achievements.assert_called_once_with(123, False)

    @pytest.mark.asyncio
    async def test_get_achievement_progress(
        self, gamification_service, mock_repository
    ):
        """Test getting achievement progress."""
        mock_achievement = MagicMock()
        mock_achievement.achievement_id = "test_achievement"
        mock_repository.get_user_achievements.return_value = [mock_achievement]

        progress = await gamification_service.get_achievement_progress(
            123, "test_achievement"
        )

        assert progress == mock_achievement

    @pytest.mark.asyncio
    async def test_create_achievement_definition(
        self, gamification_service, mock_repository
    ):
        """Test creating achievement definition."""
        achievement_data = {
            "id": "new_achievement",
            "name": "New Achievement",
            "unlock_criteria": {"total_points": 1000},
        }

        mock_achievement = MagicMock()
        mock_repository.create_achievement_definition.return_value = mock_achievement

        with patch.object(
            gamification_service.achievement_engine, "validate_achievement_criteria"
        ) as mock_validate:
            result = await gamification_service.create_achievement_definition(
                achievement_data
            )

            assert result == mock_achievement
            mock_validate.assert_called_once_with({"total_points": 1000})
            mock_repository.create_achievement_definition.assert_called_once_with(
                achievement_data
            )


class TestStreakSystem:
    """Test streak system functionality."""

    @pytest.mark.asyncio
    async def test_update_streak_success(
        self, gamification_service, mock_repository, mock_event_bus
    ):
        """Test successful streak update."""
        mock_existing_streak = MagicMock()
        mock_repository.get_user_streaks.return_value = [mock_existing_streak]
        mock_repository.update_streak_record.return_value = MagicMock(
            current_count=6, longest_count=10, current_multiplier=1.1
        )
        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.update_user_gamification.return_value = mock_user_gamification

        with patch.object(
            gamification_service.streak_engine, "update_streak"
        ) as mock_update:
            mock_update.return_value = ({"current_count": 6}, True)  # milestone reached

            result = await gamification_service.update_streak(
                user_id=123, streak_type=StreakType.DAILY_LOGIN
            )

            assert result["current_count"] == 6
            assert result["is_milestone"] is True
            mock_repository.update_streak_record.assert_called_once()
            mock_event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_freeze_streak_success(self, gamification_service, mock_repository):
        """Test successful streak freeze."""
        mock_user_gamification.vip_status = True
        mock_streak = MagicMock()

        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.get_user_streaks.return_value = [mock_streak]
        mock_repository.update_streak_record.return_value = MagicMock()

        with patch.object(
            gamification_service.streak_engine, "can_use_streak_freeze"
        ) as mock_can_freeze:
            mock_can_freeze.return_value = (True, "Freeze available")

            with patch.object(
                gamification_service.streak_engine, "apply_streak_freeze"
            ) as mock_apply:
                mock_apply.return_value = {"freeze_count": 1}

                result = await gamification_service.freeze_streak(
                    123, StreakType.DAILY_LOGIN
                )

                assert result is True
                mock_repository.update_streak_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_freeze_streak_not_allowed(
        self, gamification_service, mock_repository
    ):
        """Test streak freeze when not allowed."""
        mock_user_gamification.vip_status = False
        mock_streak = MagicMock()

        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.get_user_streaks.return_value = [mock_streak]

        with patch.object(
            gamification_service.streak_engine, "can_use_streak_freeze"
        ) as mock_can_freeze:
            mock_can_freeze.return_value = (False, "Not VIP")

            with pytest.raises(
                GamificationError, match="Cannot freeze streak: Not VIP"
            ):
                await gamification_service.freeze_streak(123, StreakType.DAILY_LOGIN)

    @pytest.mark.asyncio
    async def test_get_user_streaks(self, gamification_service, mock_repository):
        """Test getting user streaks."""
        mock_streaks = [
            MagicMock(
                streak_type=StreakType.DAILY_LOGIN,
                current_count=5,
                longest_count=10,
                last_activity_date=datetime.now(timezone.utc),
                current_multiplier=1.1,
                milestones_reached=[],
                is_active=True,
            )
        ]
        mock_repository.get_user_streaks.return_value = mock_streaks

        streaks = await gamification_service.get_user_streaks(123)

        assert len(streaks) == 1
        assert streaks[0]["streak_type"] == "daily_login"
        assert streaks[0]["current_count"] == 5


class TestLeaderboardSystem:
    """Test leaderboard system functionality."""

    @pytest.mark.asyncio
    async def test_update_leaderboard(
        self, gamification_service, mock_repository, mock_event_bus
    ):
        """Test leaderboard update."""
        now = datetime.now(timezone.utc)
        mock_entry = MagicMock()
        mock_entry.is_personal_best = True

        mock_repository.get_leaderboard_entries.return_value = []
        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.update_leaderboard_entry.return_value = mock_entry

        with patch.object(
            gamification_service.leaderboard_engine, "calculate_user_ranking"
        ) as mock_calc:
            mock_calc.return_value = (5, {"rank_change": -2, "total_participants": 100})

            with patch.object(
                gamification_service.leaderboard_engine, "create_leaderboard_entry_data"
            ) as mock_create:
                mock_create.return_value = {"rank": 5, "score": 1500}

                result = await gamification_service.update_leaderboard(
                    user_id=123,
                    leaderboard_type=LeaderboardType.GLOBAL,
                    score=1500,
                    period_start=now,
                    period_end=now,
                )

                assert result["rank"] == 5
                assert result["is_personal_best"] is True
                mock_event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, gamification_service, mock_repository):
        """Test getting leaderboard data."""
        now = datetime.now(timezone.utc)
        mock_entries = [MagicMock()]
        mock_repository.get_leaderboard_entries.return_value = mock_entries

        with patch.object(
            gamification_service.leaderboard_engine, "get_leaderboard_data"
        ) as mock_get:
            mock_get.return_value = {"entries": [], "total_participants": 0}

            result = await gamification_service.get_leaderboard(
                LeaderboardType.GLOBAL, now, now
            )

            assert "entries" in result
            mock_repository.get_leaderboard_entries.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_rank(self, gamification_service, mock_repository):
        """Test getting user rank."""
        now = datetime.now(timezone.utc)
        mock_entry = MagicMock()
        mock_entry.user_id = 123
        mock_entry.rank = 5

        mock_repository.get_leaderboard_entries.return_value = [mock_entry]

        rank = await gamification_service.get_user_rank(
            123, LeaderboardType.GLOBAL, now, now
        )

        assert rank == 5


class TestUserManagement:
    """Test user management functionality."""

    @pytest.mark.asyncio
    async def test_initialize_user(self, gamification_service, mock_repository):
        """Test initializing a new user."""
        mock_repository.create_user_gamification.return_value = mock_user_gamification

        result = await gamification_service.initialize_user(123)

        assert result == mock_user_gamification
        mock_repository.create_user_gamification.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_update_user_level(
        self, gamification_service, mock_repository, mock_event_bus
    ):
        """Test updating user level."""
        mock_user_gamification.experience_points = 1500
        mock_user_gamification.current_level = 5

        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.update_user_gamification.return_value = mock_user_gamification
        mock_repository.get_achievement_definitions.return_value = []
        mock_repository.get_user_achievements.return_value = []
        mock_repository.get_achievement_completion_count.return_value = 3

        with patch.object(
            gamification_service.points_engine, "calculate_level_from_experience"
        ) as mock_calc:
            mock_calc.return_value = 6  # Level up!

            new_level, level_increased = await gamification_service.update_user_level(
                123
            )

            assert new_level == 6
            assert level_increased is True
            mock_repository.update_user_gamification.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_vip_status(
        self, gamification_service, mock_repository, mock_user_gamification
    ):
        """Test setting VIP status."""
        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.update_user_gamification.return_value = mock_user_gamification

        result = await gamification_service.set_vip_status(123, True, 1.5)

        assert result is True
        assert mock_user_gamification.vip_status is True
        assert mock_user_gamification.vip_multiplier == 1.5
        mock_repository.update_user_gamification.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_statistics(
        self, gamification_service, mock_repository, mock_user_gamification
    ):
        """Test getting user statistics."""
        mock_repository.get_user_gamification.return_value = mock_user_gamification
        mock_repository.get_achievement_completion_count.return_value = 5

        stats = await gamification_service.get_user_statistics(123)

        assert stats["total_points"] == 1000
        assert stats["current_level"] == 5
        assert stats["total_achievements"] == 5
        assert stats["vip_status"] is False

    @pytest.mark.asyncio
    async def test_get_user_statistics_no_user(
        self, gamification_service, mock_repository
    ):
        """Test getting statistics for non-existent user."""
        mock_repository.get_user_gamification.return_value = None

        stats = await gamification_service.get_user_statistics(999)

        assert stats["total_points"] == 0
        assert stats["current_level"] == 1


class TestConfiguration:
    """Test configuration management."""

    @pytest.mark.asyncio
    async def test_get_points_configuration(self, gamification_service):
        """Test getting points configuration."""
        config = await gamification_service.get_points_configuration()

        assert "daily_login" in config
        assert "story_complete" in config

    @pytest.mark.asyncio
    async def test_update_points_configuration(self, gamification_service):
        """Test updating points configuration."""
        new_config = {"new_action": 75}

        result = await gamification_service.update_points_configuration(new_config)

        assert result is True
        config = await gamification_service.get_points_configuration()
        assert config["new_action"] == 75


class TestHelperMethods:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(
        self, gamification_service, mock_repository, mock_user_gamification
    ):
        """Test getting existing user."""
        mock_repository.get_user_gamification.return_value = mock_user_gamification

        result = await gamification_service._get_or_create_user(123)

        assert result == mock_user_gamification
        mock_repository.create_user_gamification.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_user_new(
        self, gamification_service, mock_repository, mock_user_gamification
    ):
        """Test creating new user when not existing."""
        mock_repository.get_user_gamification.return_value = None
        mock_repository.create_user_gamification.return_value = mock_user_gamification

        result = await gamification_service._get_or_create_user(123)

        assert result == mock_user_gamification
        mock_repository.create_user_gamification.assert_called_once_with(123)
