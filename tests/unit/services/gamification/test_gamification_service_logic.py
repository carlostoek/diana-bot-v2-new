import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

from src.services.gamification.service import GamificationService
from src.services.gamification.interfaces import ActionType
from src.services.gamification.models import UserGamification

@pytest.fixture
def mock_repository():
    # Using MagicMock for synchronous repository methods
    return MagicMock()

@pytest.fixture
def mock_event_bus():
    return AsyncMock()

@pytest.fixture
def gamification_service(mock_repository, mock_event_bus):
    # We can pass the mocked repository to the service
    service = GamificationService(
        repository=mock_repository,
        event_bus=mock_event_bus
    )
    return service

@pytest.mark.asyncio
async def test_award_points_for_new_user(gamification_service, mock_repository):
    # Arrange
    user_id = 123
    mock_repository.get_user_gamification_stats.return_value = None

    # Act
    result = await gamification_service.process_user_action(
        user_id, ActionType.DAILY_LOGIN, {}
    )

    # Assert
    assert result.success is True
    assert result.points_awarded == 50 # Default for DAILY_LOGIN
    mock_repository.create_or_update_user_gamification_stats.assert_called_once()
    saved_stats = mock_repository.create_or_update_user_gamification_stats.call_args[0][0]
    assert saved_stats.user_id == user_id
    assert saved_stats.total_points == 50

@pytest.mark.asyncio
async def test_streak_update_new_user(gamification_service, mock_repository):
    # Arrange
    user_id = 456
    mock_repository.get_user_gamification_stats.return_value = None

    # Act
    updated = await gamification_service.update_daily_streak(user_id)

    # Assert
    assert updated is True
    mock_repository.create_or_update_user_gamification_stats.assert_called_once()
    saved_stats = mock_repository.create_or_update_user_gamification_stats.call_args[0][0]
    assert saved_stats.current_streak == 1
    assert saved_stats.longest_streak == 1

@pytest.mark.asyncio
async def test_streak_update_continuing_streak(gamification_service, mock_repository):
    # Arrange
    user_id = 789
    last_date = datetime.now(timezone.utc) - timedelta(days=1)
    stats = UserGamification(user_id=user_id, current_streak=2, longest_streak=2, last_streak_date=last_date)
    mock_repository.get_user_gamification_stats.return_value = stats

    # Act
    updated = await gamification_service.update_daily_streak(user_id)

    # Assert
    assert updated is True
    mock_repository.create_or_update_user_gamification_stats.assert_called_once_with(stats)
    assert stats.current_streak == 3
    assert stats.longest_streak == 3

@pytest.mark.asyncio
async def test_streak_update_broken_streak(gamification_service, mock_repository):
    # Arrange
    user_id = 101
    last_date = datetime.now(timezone.utc) - timedelta(days=3)
    stats = UserGamification(user_id=user_id, current_streak=5, longest_streak=5, last_streak_date=last_date)
    mock_repository.get_user_gamification_stats.return_value = stats

    # Act
    updated = await gamification_service.update_daily_streak(user_id)

    # Assert
    assert updated is True
    assert stats.current_streak == 1 # Resets to 1
    assert stats.longest_streak == 5 # Longest streak remains

@pytest.mark.asyncio
async def test_streak_update_same_day(gamification_service, mock_repository):
    # Arrange
    user_id = 112
    last_date = datetime.now(timezone.utc)
    stats = UserGamification(user_id=user_id, current_streak=3, longest_streak=3, last_streak_date=last_date)
    mock_repository.get_user_gamification_stats.return_value = stats

    # Act
    updated = await gamification_service.update_daily_streak(user_id)

    # Assert
    assert updated is False # Should not update
    mock_repository.create_or_update_user_gamification_stats.assert_not_called()
    assert stats.current_streak == 3
