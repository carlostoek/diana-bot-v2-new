"""
Shared test configuration and utilities for Diana Bot V2.

This module provides common fixtures, utilities, and helper functions
used across the test suite to ensure consistency and reduce duplication.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

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


class GamificationTestFactory:
    """Factory for creating properly initialized test objects."""

    @staticmethod
    def create_user_gamification(
        user_id: int = 12345,
        total_points: int = 0,
        experience_points: int = 0,
        current_level: int = 1,
        vip_status: bool = False,
        current_multiplier: float = 1.0,
        vip_multiplier: float = 1.0,
        current_daily_streak: int = 0,
        longest_daily_streak: int = 0,
        total_achievements: int = 0,
        **kwargs,
    ) -> UserGamification:
        """Create a UserGamification object with proper defaults."""
        return UserGamification(
            user_id=user_id,
            total_points=total_points,
            experience_points=experience_points,
            current_level=current_level,
            current_daily_streak=current_daily_streak,
            longest_daily_streak=longest_daily_streak,
            total_achievements=total_achievements,
            bronze_achievements=0,
            silver_achievements=0,
            gold_achievements=0,
            platinum_achievements=0,
            current_multiplier=current_multiplier,
            vip_status=vip_status,
            vip_multiplier=vip_multiplier,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            **kwargs,
        )

    @staticmethod
    def create_achievement_definition(
        achievement_id: str = "test_achievement",
        name: str = "Test Achievement",
        description: str = "A test achievement",
        category: AchievementCategory = AchievementCategory.MILESTONE,
        tier: AchievementTier = AchievementTier.BRONZE,
        points_reward: int = 100,
        unlock_criteria: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
        **kwargs,
    ) -> AchievementDefinition:
        """Create an AchievementDefinition object with proper defaults."""
        if unlock_criteria is None:
            unlock_criteria = {"points_required": 1000}

        return AchievementDefinition(
            id=achievement_id,
            name=name,
            description=description,
            category=category,
            tier=tier,
            points_reward=points_reward,
            unlock_criteria=unlock_criteria,
            is_secret=False,
            is_repeatable=False,
            display_order=0,
            is_active=is_active,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            **kwargs,
        )

    @staticmethod
    def create_points_transaction(
        user_id: int = 12345,
        transaction_type: PointsTransactionType = PointsTransactionType.EARNED,
        amount: int = 100,
        points_before: int = 0,
        points_after: int = 100,
        action_type: str = "test_action",
        description: str = "Test transaction",
        source_service: str = "gamification",
        **kwargs,
    ) -> PointsTransaction:
        """Create a PointsTransaction object with proper defaults."""
        return PointsTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            points_before=points_before,
            points_after=points_after,
            action_type=action_type,
            description=description,
            source_service=source_service,
            multiplier_applied=1.0,
            bonus_applied=0,
            is_suspicious=False,
            created_at=datetime.now(timezone.utc),
            **kwargs,
        )


@pytest.fixture
def gamification_factory():
    """Provide the gamification test factory."""
    return GamificationTestFactory


@pytest.fixture
def mock_repository():
    """Create a properly configured mock repository."""
    repository = AsyncMock()

    # Configure common mock behaviors
    repository.get_user_gamification.return_value = None
    repository.create_user_gamification.return_value = (
        GamificationTestFactory.create_user_gamification()
    )
    repository.update_user_gamification.return_value = True
    repository.create_points_transaction.return_value = True

    return repository


@pytest.fixture
def mock_event_bus():
    """Create a properly configured mock event bus."""
    event_bus = AsyncMock()
    event_bus.publish.return_value = True
    return event_bus


@pytest.fixture
def sample_user_gamification():
    """Provide a sample UserGamification object for testing."""
    return GamificationTestFactory.create_user_gamification(
        user_id=12345,
        total_points=500,
        experience_points=500,
        current_level=5,
        vip_status=False,
    )


@pytest.fixture
def sample_vip_user_gamification():
    """Provide a sample VIP UserGamification object for testing."""
    return GamificationTestFactory.create_user_gamification(
        user_id=67890,
        total_points=2000,
        experience_points=2000,
        current_level=10,
        vip_status=True,
        vip_multiplier=1.5,
    )
