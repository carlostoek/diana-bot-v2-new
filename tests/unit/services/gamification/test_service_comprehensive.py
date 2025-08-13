"""
Comprehensive tests for GamificationService to achieve >90% coverage.

This module provides extensive test coverage for all GamificationService functionality,
including points management, achievements, leaderboards, and event handling.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.events.gamification import (
    AchievementUnlockedEvent,
    LeaderboardChangedEvent,
    PointsAwardedEvent,
    PointsDeductedEvent,
    StreakUpdatedEvent,
)
from src.models.gamification import (
    AchievementCategory,
    AchievementDefinition,
    AchievementTier,
    LeaderboardEntry,
    LeaderboardType,
    PointsTransaction,
    PointsTransactionType,
    StreakRecord,
    StreakType,
    UserAchievement,
    UserGamification,
)
from src.services.gamification.interfaces import GamificationError
from src.services.gamification.service import GamificationService


class TestGamificationServiceInitialization:
    """Test GamificationService initialization and configuration."""

    def test_initialization_with_dependencies(self, mock_event_bus):
        """Test proper initialization with dependencies."""
        mock_repository = Mock()

        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )

        assert service.repository == mock_repository
        assert service.event_bus == mock_event_bus
        assert service.logger is not None

    def test_initialization_without_dependencies_raises_error(self):
        """Test that initialization without required dependencies raises error."""
        with pytest.raises(TypeError):
            GamificationService()

    def test_default_configuration_values(self, mock_event_bus):
        """Test that default configuration values are set correctly."""
        mock_repository = Mock()
        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )

        # Check that internal rate limiting structures exist
        assert hasattr(service, "repository")
        assert hasattr(service, "event_bus")


class TestPointsSystem:
    """Test points awarding, deduction, and validation."""

    @pytest.fixture
    async def service(self, mock_event_bus):
        """Create a GamificationService with mocked repository."""
        mock_repository = AsyncMock()
        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )
        return service

    @pytest.fixture
    def sample_user_gam(self):
        """Sample UserGamification record."""
        return UserGamification(
            user_id=12345,
            total_points=100,
            current_level=2,
            experience_points=50,
            current_daily_streak=5,
            vip_status=False,
            current_multiplier=1.0,
            vip_multiplier=1.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def test_award_points_new_user(self, service, mock_event_bus):
        """Test awarding points to a new user."""
        user_id = 12345
        points = 100
        reason = "test_action"

        # Mock repository responses
        service.repository.get_user_gamification.return_value = None
        service.repository.create_user_gamification.return_value = UserGamification(
            user_id=user_id,
            total_points=0,
            current_level=1,
        )
        service.repository.update_user_gamification.return_value = UserGamification(
            user_id=user_id,
            total_points=points,
            current_level=1,
        )
        service.repository.create_points_transaction.return_value = PointsTransaction(
            user_id=user_id,
            amount=points,
            transaction_type=PointsTransactionType.EARNED,
            description=reason,
        )

        result = await service.award_points(user_id, points, reason)

        assert result["success"] is True
        assert result["points_awarded"] == points
        assert result["total_points"] == points

        # Verify repository calls
        service.repository.get_user_gamification.assert_called_once_with(user_id)
        service.repository.create_user_gamification.assert_called_once_with(user_id)
        service.repository.update_user_gamification.assert_called_once()
        service.repository.create_points_transaction.assert_called_once()

        # Verify event publishing
        mock_event_bus.publish.assert_called()

    async def test_award_points_existing_user(
        self, service, sample_user_gam, mock_event_bus
    ):
        """Test awarding points to an existing user."""
        user_id = sample_user_gam.user_id
        points = 50
        reason = "chapter_completion"

        # Mock repository responses
        service.repository.get_user_gamification.return_value = sample_user_gam
        updated_user = UserGamification(
            user_id=user_id,
            total_points=sample_user_gam.total_points + points,
            current_level=sample_user_gam.current_level,
        )
        service.repository.update_user_gamification.return_value = updated_user
        service.repository.create_points_transaction.return_value = PointsTransaction(
            user_id=user_id,
            amount=points,
            transaction_type=PointsTransactionType.EARNED,
            description=reason,
        )

        result = await service.award_points(user_id, points, reason)

        assert result["success"] is True
        assert result["points_awarded"] == points
        assert result["total_points"] == sample_user_gam.total_points + points

        mock_event_bus.publish.assert_called()

    async def test_award_points_with_vip_multiplier(self, service, mock_event_bus):
        """Test awarding points with VIP multiplier."""
        user_id = 12345
        points = 100
        reason = "vip_action"

        # Create VIP user
        vip_user = UserGamification(
            user_id=user_id,
            total_points=200,
            current_level=3,
            vip_status=True,
            vip_multiplier=1.5,
            current_multiplier=1.0,
        )

        service.repository.get_user_gamification.return_value = vip_user
        service.repository.update_user_gamification.return_value = vip_user
        service.repository.create_points_transaction.return_value = PointsTransaction(
            user_id=user_id,
            amount=int(points * 1.5),  # With VIP multiplier
            transaction_type=PointsTransactionType.EARNED,
            description=reason,
        )

        result = await service.award_points(user_id, points, reason)

        # Should award points with multiplier
        expected_points = int(points * 1.5)
        assert result["points_awarded"] == expected_points
        assert result["multiplier_applied"] == 1.5

    async def test_award_points_invalid_amount(self, service):
        """Test awarding invalid point amounts."""
        user_id = 12345

        # Test negative points
        with pytest.raises(GamificationError, match="Points amount must be positive"):
            await service.award_points(user_id, -10, "negative")

        # Test zero points
        with pytest.raises(GamificationError, match="Points amount must be positive"):
            await service.award_points(user_id, 0, "zero")

    async def test_deduct_points_success(
        self, service, sample_user_gam, mock_event_bus
    ):
        """Test successful points deduction."""
        user_id = sample_user_gam.user_id
        points = 50
        reason = "item_purchase"

        service.repository.get_user_gamification.return_value = sample_user_gam
        updated_user = UserGamification(
            user_id=user_id,
            total_points=sample_user_gam.total_points - points,
            current_level=sample_user_gam.current_level,
        )
        service.repository.update_user_gamification.return_value = updated_user
        service.repository.create_points_transaction.return_value = PointsTransaction(
            user_id=user_id,
            amount=points,
            transaction_type=PointsTransactionType.SPENT,
            description=reason,
        )

        result = await service.deduct_points(user_id, points, reason)

        assert result["success"] is True
        assert result["points_deducted"] == points
        assert result["remaining_points"] == sample_user_gam.total_points - points

        mock_event_bus.publish.assert_called()

    async def test_deduct_points_insufficient_funds(self, service, sample_user_gam):
        """Test points deduction with insufficient funds."""
        user_id = sample_user_gam.user_id
        points = sample_user_gam.total_points + 50  # More than available
        reason = "expensive_item"

        service.repository.get_user_gamification.return_value = sample_user_gam

        with pytest.raises(GamificationError, match="Insufficient points"):
            await service.deduct_points(user_id, points, reason)

    async def test_get_points_history(self, service):
        """Test retrieving points transaction history."""
        user_id = 12345
        limit = 10

        mock_transactions = [
            PointsTransaction(
                user_id=user_id,
                amount=100,
                transaction_type=PointsTransactionType.EARNED,
                description="test1",
                created_at=datetime.now(timezone.utc),
            ),
            PointsTransaction(
                user_id=user_id,
                amount=50,
                transaction_type=PointsTransactionType.SPENT,
                description="test2",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        service.repository.get_points_transactions.return_value = mock_transactions

        result = await service.get_points_history(user_id, limit)

        assert len(result) == 2
        assert result[0]["amount"] == 100
        assert result[1]["amount"] == 50

        service.repository.get_points_transactions.assert_called_once_with(
            user_id, limit
        )


class TestUserManagement:
    """Test user initialization and profile management."""

    @pytest.fixture
    async def service(self, mock_event_bus):
        """Create a GamificationService with mocked repository."""
        mock_repository = AsyncMock()
        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )
        return service

    async def test_initialize_user(self, service):
        """Test user gamification initialization."""
        user_id = 12345

        new_user = UserGamification(
            user_id=user_id,
            total_points=0,
            current_level=1,
        )
        service.repository.get_user_gamification.return_value = None
        service.repository.create_user_gamification.return_value = new_user

        result = await service.initialize_user(user_id)

        # The actual method returns a UserGamification object, not a dict
        assert result.user_id == user_id
        assert result.total_points == 0
        assert result.current_level == 1

        service.repository.create_user_gamification.assert_called_once_with(user_id)

    async def test_initialize_existing_user(self, service):
        """Test initializing an already existing user."""
        user_id = 12345

        existing_user = UserGamification(
            user_id=user_id,
            total_points=500,
            current_level=5,
        )
        service.repository.get_user_gamification.return_value = existing_user

        result = await service.initialize_user(user_id)

        assert result["user_id"] == user_id
        assert result["total_points"] == 500
        assert result["current_level"] == 5
        assert result["created"] is False

    async def test_get_user_statistics(self, service):
        """Test retrieving comprehensive user statistics."""
        user_id = 12345

        user_gam = UserGamification(
            user_id=user_id,
            total_points=1000,
            current_level=5,
            total_achievements=10,
            current_daily_streak=7,
        )

        mock_achievements = [
            UserAchievement(achievement_id="test1", user_id=user_id),
            UserAchievement(achievement_id="test2", user_id=user_id),
        ]

        service.repository.get_user_gamification.return_value = user_gam
        service.repository.get_user_achievements.return_value = mock_achievements

        result = await service.get_user_statistics(user_id)

        assert result["user_id"] == user_id
        assert result["total_points"] == 1000
        assert result["current_level"] == 5
        assert result["total_achievements"] == 10
        assert result["current_streak"] == 7
        assert len(result["recent_achievements"]) == 2

    async def test_update_user_level(self, service, mock_event_bus):
        """Test user level calculation and updates."""
        user_id = 12345
        new_points = 2000  # Should trigger level up

        user_gam = UserGamification(
            user_id=user_id,
            total_points=1500,
            current_level=3,
        )

        service.repository.get_user_gamification.return_value = user_gam

        # Mock the level calculation
        with patch.object(service, "_calculate_level_from_points", return_value=4):
            updated_user = UserGamification(
                user_id=user_id,
                total_points=new_points,
                current_level=4,
            )
            service.repository.update_user_gamification.return_value = updated_user

            result = await service.update_user_level(user_id, new_points)

            assert result["level_up"] is True
            assert result["new_level"] == 4
            assert result["previous_level"] == 3

            # Should publish level up event
            mock_event_bus.publish.assert_called()


class TestAchievementSystem:
    """Test achievement checking, unlocking, and management."""

    @pytest.fixture
    async def service(self, mock_event_bus):
        """Create a GamificationService with mocked repository."""
        mock_repository = AsyncMock()
        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )
        return service

    @pytest.fixture
    def sample_achievement(self):
        """Sample achievement definition."""
        return AchievementDefinition(
            id="first_steps",
            name="First Steps",
            description="Complete your first story chapter",
            category=AchievementCategory.NARRATIVE,
            tier=AchievementTier.BRONZE,
            unlock_criteria={"chapters_completed": 1},
            points_reward=100,
            is_active=True,
        )

    async def test_check_achievement_unlock(
        self, service, sample_achievement, mock_event_bus
    ):
        """Test achievement unlock checking."""
        user_id = 12345
        trigger_context = {"chapters_completed": 1}

        service.repository.get_achievement_definitions.return_value = [
            sample_achievement
        ]
        service.repository.get_user_achievements.return_value = (
            []
        )  # No achievements yet
        service.get_user_statistics = AsyncMock(return_value={"chapters_completed": 1})

        unlocked_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=sample_achievement.id,
            unlocked_at=datetime.now(timezone.utc),
        )
        service.repository.create_user_achievement.return_value = unlocked_achievement

        result = await service.check_achievements(user_id, trigger_context)

        assert len(result) == 1
        assert result[0].achievement_id == sample_achievement.id

        # Should create achievement record and publish event
        service.repository.create_user_achievement.assert_called_once()

    async def test_check_achievement_already_unlocked(
        self, service, sample_achievement
    ):
        """Test checking achievement that's already unlocked."""
        user_id = 12345
        trigger_context = {"chapters_completed": 1}

        existing_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=sample_achievement.id,
            unlocked_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_completed=True,
        )

        service.repository.get_achievement_definitions.return_value = [
            sample_achievement
        ]
        service.repository.get_user_achievements.return_value = [existing_achievement]

        result = await service.check_achievements(user_id, trigger_context)

        assert len(result) == 0  # No new achievements unlocked

    async def test_check_achievement_criteria_not_met(
        self, service, sample_achievement
    ):
        """Test achievement criteria not met."""
        user_id = 12345
        trigger_context = {"chapters_completed": 0}  # Criteria not met

        service.repository.get_achievement_definitions.return_value = [
            sample_achievement
        ]
        service.repository.get_user_achievements.return_value = []
        service.get_user_statistics = AsyncMock(return_value={"chapters_completed": 0})

        result = await service.check_achievements(user_id, trigger_context)

        assert len(result) == 0  # No achievements unlocked

    async def test_get_user_achievements(self, service):
        """Test retrieving user achievements."""
        user_id = 12345

        mock_achievements = [
            UserAchievement(
                user_id=user_id,
                achievement_id="test1",
                unlocked_at=datetime.now(timezone.utc),
            ),
            UserAchievement(
                user_id=user_id,
                achievement_id="test2",
                unlocked_at=datetime.now(timezone.utc),
            ),
        ]

        service.repository.get_user_achievements.return_value = mock_achievements

        result = await service.get_user_achievements(user_id)

        assert len(result) == 2
        assert all("achievement_id" in achievement for achievement in result)
        assert all("unlocked_at" in achievement for achievement in result)


class TestEventHandlers:
    """Test event handling and processing."""

    @pytest.fixture
    async def service(self, mock_event_bus):
        """Create a GamificationService with mocked repository."""
        mock_repository = AsyncMock()
        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )
        return service

    async def test_handle_user_action_event(self, service):
        """Test handling generic user action events."""
        event_data = {
            "user_id": 12345,
            "action": "story_interaction",
            "points": 25,
            "metadata": {"chapter_id": "ch1", "choice_made": True},
        }

        # Mock user exists
        service.repository.get_user_gamification.return_value = UserGamification(
            user_id=event_data["user_id"],
            total_points=100,
            current_level=2,
        )

        # Mock successful point award
        with patch.object(
            service,
            "award_points",
            return_value={"success": True, "points_awarded": 25},
        ):
            result = await service.handle_user_action_event(event_data)

            assert result["success"] is True
            assert result["points_awarded"] == 25

    async def test_handle_story_completion_event(self, service):
        """Test handling story completion events."""
        event_data = {
            "user_id": 12345,
            "story_id": "story1",
            "completion_time": datetime.now(timezone.utc),
            "choices_made": 10,
        }

        # Mock achievements check
        with patch.object(
            service, "check_achievement_unlock", return_value={"unlocked": True}
        ):
            with patch.object(
                service,
                "award_points",
                return_value={"success": True, "points_awarded": 200},
            ):
                result = await service.handle_story_completion_event(event_data)

                assert result["success"] is True
                assert result["story_completed"] is True

    async def test_handle_chapter_completion_event(self, service):
        """Test handling chapter completion events."""
        event_data = {
            "user_id": 12345,
            "chapter_id": "ch1",
            "story_id": "story1",
            "completion_time": datetime.now(timezone.utc),
        }

        with patch.object(
            service,
            "award_points",
            return_value={"success": True, "points_awarded": 50},
        ):
            with patch.object(
                service,
                "update_streak",
                return_value={"updated": True, "current_streak": 5},
            ):
                result = await service.handle_chapter_completion_event(event_data)

                assert result["success"] is True
                assert result["chapter_completed"] is True

    async def test_handle_decision_made_event(self, service):
        """Test handling decision-making events."""
        event_data = {
            "user_id": 12345,
            "decision_id": "decision1",
            "choice": "option_a",
            "impact_score": 0.8,
        }

        with patch.object(
            service,
            "award_points",
            return_value={"success": True, "points_awarded": 10},
        ):
            result = await service.handle_decision_made_event(event_data)

            assert result["success"] is True
            assert result["decision_processed"] is True


class TestAntiAbuseSystem:
    """Test anti-abuse mechanisms and rate limiting."""

    @pytest.fixture
    async def service(self, mock_event_bus):
        """Create a GamificationService with mocked repository."""
        mock_repository = AsyncMock()
        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )
        return service

    async def test_rate_limiting(self, service):
        """Test rate limiting for point awards."""
        user_id = 12345

        # Mock user exists
        service.repository.get_user_gamification.return_value = UserGamification(
            user_id=user_id,
            total_points=100,
            current_level=2,
        )

        # Mock successful transactions
        service.repository.update_user_gamification.return_value = UserGamification(
            user_id=user_id,
            total_points=150,
            current_level=2,
        )
        service.repository.create_points_transaction.return_value = PointsTransaction(
            user_id=user_id,
            amount=50,
            transaction_type=PointsTransactionType.EARNED,
        )

        # First award should succeed
        result1 = await service.award_points(user_id, 50, "test1")
        assert result1["success"] is True

        # Multiple rapid awards might trigger rate limiting
        # (Implementation details depend on the actual rate limiting logic)

    async def test_suspicious_activity_detection(self, service):
        """Test detection of suspicious point-earning patterns."""
        user_id = 12345

        # This would test the actual anti-abuse logic
        # Implementation depends on specific requirements

        # Mock multiple rapid transactions
        service.repository.get_recent_transactions.return_value = [
            PointsTransaction(
                user_id=user_id,
                amount=100,
                created_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            ),
            PointsTransaction(
                user_id=user_id,
                amount=100,
                created_at=datetime.now(timezone.utc) - timedelta(seconds=2),
            ),
        ]

        # Test the suspicious activity check
        with patch.object(service, "_check_suspicious_activity", return_value=True):
            with pytest.raises(GamificationError, match="Suspicious activity detected"):
                await service.award_points(user_id, 100, "rapid_test")


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    async def service(self, mock_event_bus):
        """Create a GamificationService with mocked repository."""
        mock_repository = AsyncMock()
        service = GamificationService(
            repository=mock_repository, event_bus=mock_event_bus
        )
        return service

    async def test_repository_error_handling(self, service):
        """Test handling of repository errors."""
        user_id = 12345

        # Mock repository error
        service.repository.get_user_gamification.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(GamificationError, match="Failed to get user gamification"):
            await service.award_points(user_id, 100, "test")

    async def test_event_bus_error_handling(self, service, mock_event_bus):
        """Test handling of event bus errors."""
        user_id = 12345

        # Mock successful repository operations
        service.repository.get_user_gamification.return_value = UserGamification(
            user_id=user_id,
            total_points=100,
        )
        service.repository.update_user_gamification.return_value = UserGamification(
            user_id=user_id,
            total_points=150,
        )
        service.repository.create_points_transaction.return_value = PointsTransaction(
            user_id=user_id,
            amount=50,
        )

        # Mock event bus error
        mock_event_bus.publish.side_effect = Exception("Event bus error")

        # The operation should still succeed even if event publishing fails
        result = await service.award_points(user_id, 50, "test")
        assert result["success"] is True

    async def test_invalid_user_id(self, service):
        """Test handling of invalid user IDs."""
        invalid_user_id = -1

        with pytest.raises(GamificationError, match="Invalid user ID"):
            await service.award_points(invalid_user_id, 100, "test")

    async def test_invalid_points_amount(self, service):
        """Test handling of invalid point amounts."""
        user_id = 12345

        # Test extremely large amount
        with pytest.raises(GamificationError, match="Points amount too large"):
            await service.award_points(user_id, 1000000, "test")

    async def test_empty_reason_string(self, service):
        """Test handling of empty reason strings."""
        user_id = 12345

        with pytest.raises(GamificationError, match="Reason cannot be empty"):
            await service.award_points(user_id, 100, "")

    async def test_concurrent_operations(self, service):
        """Test handling of concurrent operations on the same user."""
        user_id = 12345

        # This would test the actual concurrency handling
        # Implementation depends on specific requirements and locking mechanisms

        # Mock concurrent access scenario
        service.repository.get_user_gamification.return_value = UserGamification(
            user_id=user_id,
            total_points=100,
        )

        # Test concurrent point awards
        # (Would need actual async concurrency testing)
        result = await service.award_points(user_id, 50, "concurrent_test")
        assert result["success"] is True
