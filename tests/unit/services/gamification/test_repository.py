"""
Tests for GamificationRepository.

This module tests the data access layer for the gamification system.
"""

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from src.models.gamification import (
    AchievementCategory,
    AchievementTier,
    LeaderboardType,
    PointsTransactionType,
    StreakType,
)
from src.services.gamification.interfaces import GamificationError
from src.services.gamification.repository import GamificationRepository


@pytest.fixture
async def repository():
    """Create a repository instance for testing."""
    # In a real test environment, this would use a test database
    repo = GamificationRepository("sqlite+aiosqlite:///:memory:")
    await repo.initialize()
    return repo


class TestUserGamificationCRUD:
    """Test user gamification CRUD operations."""

    async def test_create_user_gamification(self, repository):
        """Test creating a new user gamification record."""
        user_id = 123

        user_gam = await repository.create_user_gamification(user_id)

        assert user_gam.user_id == user_id
        assert user_gam.total_points == 0
        assert user_gam.current_level == 1
        assert user_gam.vip_status is False

    async def test_get_user_gamification_exists(self, repository):
        """Test retrieving existing user gamification record."""
        user_id = 456

        # Create user first
        created_user = await repository.create_user_gamification(user_id)

        # Retrieve user
        retrieved_user = await repository.get_user_gamification(user_id)

        assert retrieved_user is not None
        assert retrieved_user.user_id == user_id
        assert retrieved_user.user_id == created_user.user_id

    async def test_get_user_gamification_not_exists(self, repository):
        """Test retrieving non-existent user gamification record."""
        user_id = 999

        user_gam = await repository.get_user_gamification(user_id)

        assert user_gam is None

    async def test_update_user_gamification(self, repository):
        """Test updating user gamification record."""
        user_id = 789

        # Create user
        user_gam = await repository.create_user_gamification(user_id)

        # Update fields
        user_gam.total_points = 500
        user_gam.current_level = 3
        user_gam.vip_status = True

        # Save update
        updated_user = await repository.update_user_gamification(user_gam)

        assert updated_user.total_points == 500
        assert updated_user.current_level == 3
        assert updated_user.vip_status is True


class TestPointsTransactions:
    """Test points transaction operations."""

    async def test_create_points_transaction(self, repository):
        """Test creating a points transaction."""
        user_id = 111

        # Create user first
        await repository.create_user_gamification(user_id)

        transaction_data = {
            "user_id": user_id,
            "transaction_type": PointsTransactionType.EARNED,
            "amount": 100,
            "points_before": 0,
            "points_after": 100,
            "action_type": "test_action",
            "description": "Test transaction",
            "source_service": "gamification",
            "multiplier_applied": 1.0,
            "bonus_applied": 0,
            "transaction_metadata": {"test": True},
        }

        transaction = await repository.create_points_transaction(transaction_data)

        assert transaction.user_id == user_id
        assert transaction.amount == 100
        assert transaction.action_type == "test_action"
        assert transaction.transaction_metadata["test"] is True

    async def test_get_points_transactions(self, repository):
        """Test retrieving points transactions."""
        user_id = 222

        # Create user
        await repository.create_user_gamification(user_id)

        # Create multiple transactions
        for i in range(5):
            transaction_data = {
                "user_id": user_id,
                "transaction_type": PointsTransactionType.EARNED,
                "amount": 50 * (i + 1),
                "points_before": 50 * i,
                "points_after": 50 * (i + 1),
                "action_type": f"action_{i}",
                "description": f"Transaction {i}",
                "source_service": "gamification",
            }
            await repository.create_points_transaction(transaction_data)

        # Retrieve transactions
        transactions = await repository.get_points_transactions(user_id, 10, 0, None)

        assert len(transactions) == 5
        # Should be ordered by creation time (most recent first)
        assert transactions[0].amount == 250  # Last transaction created

    async def test_get_points_transactions_filtered(self, repository):
        """Test retrieving filtered points transactions."""
        user_id = 333

        # Create user
        await repository.create_user_gamification(user_id)

        # Create different types of transactions
        earned_data = {
            "user_id": user_id,
            "transaction_type": PointsTransactionType.EARNED,
            "amount": 100,
            "points_before": 0,
            "points_after": 100,
            "action_type": "earned",
            "source_service": "gamification",
        }
        await repository.create_points_transaction(earned_data)

        spent_data = {
            "user_id": user_id,
            "transaction_type": PointsTransactionType.SPENT,
            "amount": -50,
            "points_before": 100,
            "points_after": 50,
            "action_type": "spent",
            "source_service": "gamification",
        }
        await repository.create_points_transaction(spent_data)

        # Get only earned transactions
        earned_transactions = await repository.get_points_transactions(
            user_id, 10, 0, PointsTransactionType.EARNED
        )

        assert len(earned_transactions) == 1
        assert earned_transactions[0].transaction_type == PointsTransactionType.EARNED


class TestAchievements:
    """Test achievement operations."""

    async def test_create_achievement_definition(self, repository):
        """Test creating an achievement definition."""
        achievement_data = {
            "id": "test_achievement",
            "name": "Test Achievement",
            "description": "A test achievement",
            "category": AchievementCategory.MILESTONE,
            "tier": AchievementTier.BRONZE,
            "points_reward": 100,
            "unlock_criteria": {"total_points": 1000},
            "is_secret": False,
            "is_repeatable": False,
            "is_active": True,
        }

        achievement = await repository.create_achievement_definition(achievement_data)

        assert achievement.id == "test_achievement"
        assert achievement.name == "Test Achievement"
        assert achievement.category == AchievementCategory.MILESTONE
        assert achievement.tier == AchievementTier.BRONZE
        assert achievement.points_reward == 100

    async def test_get_achievement_definitions(self, repository):
        """Test retrieving achievement definitions."""
        # Create multiple achievements
        for i in range(3):
            achievement_data = {
                "id": f"achievement_{i}",
                "name": f"Achievement {i}",
                "description": f"Achievement {i} description",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.SILVER,
                "unlock_criteria": {"stories_completed": i + 1},
                "is_active": i < 2,  # Make one inactive
            }
            await repository.create_achievement_definition(achievement_data)

        # Get all active achievements
        active_achievements = await repository.get_achievement_definitions(
            active_only=True
        )
        assert len(active_achievements) == 2

        # Get all achievements
        all_achievements = await repository.get_achievement_definitions(
            active_only=False
        )
        assert len(all_achievements) == 3

    async def test_create_user_achievement(self, repository):
        """Test creating a user achievement."""
        user_id = 444
        achievement_id = "user_test_achievement"

        # Create user and achievement definition
        await repository.create_user_gamification(user_id)
        await repository.create_achievement_definition(
            {
                "id": achievement_id,
                "name": "User Test Achievement",
                "description": "Test",
                "category": AchievementCategory.SPECIAL,
                "tier": AchievementTier.GOLD,
                "unlock_criteria": {},
            }
        )

        achievement_data = {
            "user_id": user_id,
            "achievement_id": achievement_id,
            "progress_current": 1,
            "progress_required": 1,
            "is_completed": True,
            "unlocked_at": datetime.now(timezone.utc),
            "points_awarded": 250,
        }

        user_achievement = await repository.create_user_achievement(achievement_data)

        assert user_achievement.user_id == user_id
        assert user_achievement.achievement_id == achievement_id
        assert user_achievement.is_completed is True
        assert user_achievement.points_awarded == 250

    async def test_get_user_achievements(self, repository):
        """Test retrieving user achievements."""
        user_id = 555

        # Create user
        await repository.create_user_gamification(user_id)

        # Create achievement definitions
        for i in range(3):
            await repository.create_achievement_definition(
                {
                    "id": f"user_achievement_{i}",
                    "name": f"User Achievement {i}",
                    "description": "Test",
                    "category": AchievementCategory.ENGAGEMENT,
                    "tier": AchievementTier.BRONZE,
                    "unlock_criteria": {},
                }
            )

        # Create user achievements (some completed, some not)
        for i in range(3):
            achievement_data = {
                "user_id": user_id,
                "achievement_id": f"user_achievement_{i}",
                "progress_current": i + 1,
                "progress_required": 3,
                "is_completed": i == 2,  # Only last one completed
                "points_awarded": 100 if i == 2 else 0,
            }
            await repository.create_user_achievement(achievement_data)

        # Get all user achievements
        all_achievements = await repository.get_user_achievements(
            user_id, completed_only=False
        )
        assert len(all_achievements) == 3

        # Get only completed achievements
        completed_achievements = await repository.get_user_achievements(
            user_id, completed_only=True
        )
        assert len(completed_achievements) == 1
        assert completed_achievements[0].is_completed is True

    async def test_update_user_achievement(self, repository):
        """Test updating user achievement progress."""
        user_id = 666
        achievement_id = "update_test_achievement"

        # Create user and achievement
        await repository.create_user_gamification(user_id)
        await repository.create_achievement_definition(
            {
                "id": achievement_id,
                "name": "Update Test",
                "description": "Test",
                "category": AchievementCategory.MILESTONE,
                "tier": AchievementTier.SILVER,
                "unlock_criteria": {},
            }
        )

        # Create user achievement
        user_achievement = await repository.create_user_achievement(
            {
                "user_id": user_id,
                "achievement_id": achievement_id,
                "progress_current": 2,
                "progress_required": 5,
                "is_completed": False,
            }
        )

        # Update progress
        user_achievement.progress_current = 5
        user_achievement.is_completed = True
        user_achievement.unlocked_at = datetime.now(timezone.utc)
        user_achievement.points_awarded = 200

        updated_achievement = await repository.update_user_achievement(user_achievement)

        assert updated_achievement.progress_current == 5
        assert updated_achievement.is_completed is True
        assert updated_achievement.points_awarded == 200


class TestStreaks:
    """Test streak operations."""

    async def test_update_streak_record_new(self, repository):
        """Test creating a new streak record."""
        user_id = 777

        # Create user
        await repository.create_user_gamification(user_id)

        streak_data = {
            "user_id": user_id,
            "streak_type": StreakType.DAILY_LOGIN,
            "current_count": 1,
            "longest_count": 1,
            "last_activity_date": datetime.now(timezone.utc),
            "current_multiplier": 1.0,
            "is_active": True,
        }

        streak_record = await repository.update_streak_record(streak_data)

        assert streak_record.user_id == user_id
        assert streak_record.streak_type == StreakType.DAILY_LOGIN
        assert streak_record.current_count == 1

    async def test_update_streak_record_existing(self, repository):
        """Test updating an existing streak record."""
        user_id = 888

        # Create user
        await repository.create_user_gamification(user_id)

        # Create initial streak
        initial_data = {
            "user_id": user_id,
            "streak_type": StreakType.DAILY_LOGIN,
            "current_count": 5,
            "longest_count": 10,
            "is_active": True,
        }
        await repository.update_streak_record(initial_data)

        # Update streak
        update_data = {
            "user_id": user_id,
            "streak_type": StreakType.DAILY_LOGIN,
            "current_count": 6,
            "longest_count": 10,
            "current_multiplier": 1.1,
        }

        updated_streak = await repository.update_streak_record(update_data)

        assert updated_streak.current_count == 6
        assert updated_streak.current_multiplier == 1.1

    async def test_get_user_streaks(self, repository):
        """Test retrieving user streaks."""
        user_id = 999

        # Create user
        await repository.create_user_gamification(user_id)

        # Create multiple streak types
        streak_types = [StreakType.DAILY_LOGIN, StreakType.STORY_PROGRESS]

        for streak_type in streak_types:
            streak_data = {
                "user_id": user_id,
                "streak_type": streak_type,
                "current_count": 3,
                "longest_count": 7,
                "is_active": True,
            }
            await repository.update_streak_record(streak_data)

        streaks = await repository.get_user_streaks(user_id)

        assert len(streaks) == 2
        streak_types_retrieved = {s.streak_type for s in streaks}
        assert streak_types_retrieved == set(streak_types)


class TestLeaderboards:
    """Test leaderboard operations."""

    async def test_update_leaderboard_entry_new(self, repository):
        """Test creating a new leaderboard entry."""
        user_id = 1001
        period_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_end = period_start.replace(hour=23, minute=59, second=59)

        # Create user
        await repository.create_user_gamification(user_id)

        entry_data = {
            "user_id": user_id,
            "leaderboard_type": LeaderboardType.GLOBAL,
            "period_start": period_start,
            "period_end": period_end,
            "rank": 1,
            "score": 1500,
            "is_personal_best": True,
        }

        entry = await repository.update_leaderboard_entry(entry_data)

        assert entry.user_id == user_id
        assert entry.leaderboard_type == LeaderboardType.GLOBAL
        assert entry.rank == 1
        assert entry.score == 1500
        assert entry.is_personal_best is True

    async def test_update_leaderboard_entry_existing(self, repository):
        """Test updating an existing leaderboard entry."""
        user_id = 1002
        period_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_end = period_start.replace(hour=23, minute=59, second=59)

        # Create user
        await repository.create_user_gamification(user_id)

        # Create initial entry
        initial_data = {
            "user_id": user_id,
            "leaderboard_type": LeaderboardType.WEEKLY,
            "period_start": period_start,
            "period_end": period_end,
            "rank": 5,
            "score": 1000,
        }
        await repository.update_leaderboard_entry(initial_data)

        # Update entry
        update_data = {
            "user_id": user_id,
            "leaderboard_type": LeaderboardType.WEEKLY,
            "period_start": period_start,
            "period_end": period_end,
            "rank": 3,
            "score": 1200,
            "rank_change": 2,  # Moved up 2 positions
        }

        updated_entry = await repository.update_leaderboard_entry(update_data)

        assert updated_entry.previous_rank == 5
        assert updated_entry.rank == 3
        assert updated_entry.score == 1200
        assert updated_entry.rank_change == 2

    async def test_get_leaderboard_entries(self, repository):
        """Test retrieving leaderboard entries."""
        period_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        period_end = period_start.replace(hour=23, minute=59, second=59)

        # Create multiple users and entries
        for i in range(5):
            user_id = 2000 + i
            await repository.create_user_gamification(user_id)

            entry_data = {
                "user_id": user_id,
                "leaderboard_type": LeaderboardType.MONTHLY,
                "period_start": period_start,
                "period_end": period_end,
                "rank": i + 1,
                "score": 1000 - (i * 100),  # Descending scores
            }
            await repository.update_leaderboard_entry(entry_data)

        # Retrieve leaderboard
        entries = await repository.get_leaderboard_entries(
            LeaderboardType.MONTHLY, period_start, period_end, 10
        )

        assert len(entries) == 5
        # Should be ordered by rank
        assert entries[0].rank == 1
        assert entries[0].score == 1000
        assert entries[4].rank == 5
        assert entries[4].score == 600


class TestAnalytics:
    """Test analytics and aggregation operations."""

    async def test_get_user_points_total(self, repository):
        """Test calculating user points total."""
        user_id = 3001

        # Create user
        await repository.create_user_gamification(user_id)

        # Create multiple transactions
        transactions = [
            {"amount": 100, "transaction_type": PointsTransactionType.EARNED},
            {"amount": 50, "transaction_type": PointsTransactionType.EARNED},
            {"amount": -25, "transaction_type": PointsTransactionType.SPENT},
        ]

        for i, tx in enumerate(transactions):
            transaction_data = {
                "user_id": user_id,
                "transaction_type": tx["transaction_type"],
                "amount": tx["amount"],
                "points_before": 0,
                "points_after": 0,
                "action_type": f"action_{i}",
                "source_service": "gamification",
            }
            await repository.create_points_transaction(transaction_data)

        total_points = await repository.get_user_points_total(user_id)

        assert total_points == 125  # 100 + 50 - 25

    async def test_get_achievement_completion_count(self, repository):
        """Test counting completed achievements."""
        user_id = 3002

        # Create user
        await repository.create_user_gamification(user_id)

        # Create achievement definitions
        for i in range(4):
            await repository.create_achievement_definition(
                {
                    "id": f"count_achievement_{i}",
                    "name": f"Count Achievement {i}",
                    "description": "Test",
                    "category": AchievementCategory.MILESTONE,
                    "tier": AchievementTier.BRONZE,
                    "unlock_criteria": {},
                }
            )

        # Create user achievements (2 completed, 2 not)
        for i in range(4):
            achievement_data = {
                "user_id": user_id,
                "achievement_id": f"count_achievement_{i}",
                "is_completed": i < 2,  # First 2 are completed
            }
            await repository.create_user_achievement(achievement_data)

        completion_count = await repository.get_achievement_completion_count(user_id)

        assert completion_count == 2

    async def test_get_system_statistics(self, repository):
        """Test getting system-wide statistics."""
        # Create some test data
        for i in range(3):
            user_id = 4000 + i
            await repository.create_user_gamification(user_id)

            # Add points transaction
            await repository.create_points_transaction(
                {
                    "user_id": user_id,
                    "transaction_type": PointsTransactionType.EARNED,
                    "amount": 100 * (i + 1),
                    "points_before": 0,
                    "points_after": 100 * (i + 1),
                    "action_type": "test",
                    "source_service": "gamification",
                }
            )

        stats = await repository.get_system_statistics()

        assert "total_users" in stats
        assert "total_points_awarded" in stats
        assert "total_achievements_unlocked" in stats
        assert stats["total_users"] >= 3
        assert stats["total_points_awarded"] >= 600  # 100 + 200 + 300


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/unit/services/gamification/test_repository.py -v
    pytest.main([__file__, "-v"])
