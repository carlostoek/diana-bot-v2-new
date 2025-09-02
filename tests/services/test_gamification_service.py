import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from src.services.gamification_service import GamificationService
from src.domain.models import User, Wallet, Achievement


@pytest.fixture
def mock_user_repo():
    return AsyncMock()

@pytest.fixture
def mock_wallet_repo():
    return AsyncMock()

@pytest.fixture
def mock_transaction_repo():
    return AsyncMock()

@pytest.fixture
def mock_achievement_repo():
    return AsyncMock()

@pytest.fixture
def mock_user_achievement_repo():
    return AsyncMock()

@pytest.fixture
def mock_event_publisher():
    return AsyncMock()

@pytest.fixture
def gamification_service(
    mock_user_repo,
    mock_wallet_repo,
    mock_transaction_repo,
    mock_achievement_repo,
    mock_user_achievement_repo,
    mock_event_publisher,
):
    return GamificationService(
        mock_user_repo,
        mock_wallet_repo,
        mock_transaction_repo,
        mock_achievement_repo,
        mock_user_achievement_repo,
        mock_event_publisher,
    )


@pytest.mark.asyncio
async def test_add_points(gamification_service, mock_wallet_repo, mock_transaction_repo):
    mock_wallet_repo.get_by_user_id.return_value = Wallet(user_id=1, balance=100)

    await gamification_service.add_points(user_id=1, amount=50, description="Test")

    mock_wallet_repo.add.assert_called_once()
    mock_transaction_repo.add.assert_called_once()
    assert mock_wallet_repo.add.call_args[0][0].balance == 150


@pytest.mark.asyncio
async def test_update_daily_streak_new_user(gamification_service, mock_user_repo):
    user = User(id=1, last_active_at=None, current_streak=0)

    await gamification_service.update_daily_streak(user)

    assert user.current_streak == 1
    assert user.max_streak == 1
    mock_user_repo.add.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_update_daily_streak_continued(gamification_service, mock_user_repo):
    yesterday = datetime.utcnow() - timedelta(days=1)
    user = User(id=1, last_active_at=yesterday, current_streak=5, max_streak=5)

    await gamification_service.update_daily_streak(user)

    assert user.current_streak == 6
    assert user.max_streak == 6
    mock_user_repo.add.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_unlock_achievement(gamification_service, mock_achievement_repo, mock_user_achievement_repo, mock_event_publisher):
    mock_achievement_repo.get_by_name.return_value = Achievement(id=1, name="Test", reward_points=50)
    mock_user_achievement_repo.find_by_user_and_achievement.return_value = None
    mock_wallet = Wallet(user_id=1, balance=0)
    gamification_service._wallet_repo.get_by_user_id.return_value = mock_wallet

    result = await gamification_service.unlock_achievement(user_id=1, achievement_name="Test")

    assert result is True
    mock_user_achievement_repo.add.assert_called_once()
    mock_event_publisher.publish.assert_called_once()
    # Check that points were added
    assert mock_wallet.balance == 50
