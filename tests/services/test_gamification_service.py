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
def uow():
    return AsyncMock()

@pytest.fixture
def gamification_service(mock_event_publisher):
    return GamificationService(mock_event_publisher)


@pytest.mark.asyncio
async def test_add_points(gamification_service: GamificationService, uow: AsyncMock):
    uow.wallets.get_by_user_id.return_value = Wallet(user_id=1, balance=100)

    await gamification_service.add_points(uow, user_id=1, amount=50, description="Test")

    uow.wallets.add.assert_called_once()
    uow.transactions.add.assert_called_once()
    assert uow.wallets.add.call_args[0][0].balance == 150


@pytest.mark.asyncio
async def test_update_daily_streak_new_user(gamification_service: GamificationService, uow: AsyncMock):
    user = User(id=1, last_active_at=None, current_streak=0)

    await gamification_service.update_daily_streak(uow, user)

    assert user.current_streak == 1
    assert user.max_streak == 1
    uow.users.add.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_update_daily_streak_continued(gamification_service: GamificationService, uow: AsyncMock):
    yesterday = datetime.utcnow() - timedelta(days=1)
    user = User(id=1, last_active_at=yesterday, current_streak=5, max_streak=5)

    await gamification_service.update_daily_streak(uow, user)

    assert user.current_streak == 6
    assert user.max_streak == 6
    uow.users.add.assert_called_once_with(user)


@pytest.mark.asyncio
async def test_unlock_achievement(gamification_service: GamificationService, uow: AsyncMock, mock_event_publisher: AsyncMock):
    uow.achievements.get_by_name.return_value = Achievement(id=1, name="Test", reward_points=50)
    uow.user_achievements.find_by_user_and_achievement.return_value = None
    mock_wallet = Wallet(user_id=1, balance=0)
    uow.wallets.get_by_user_id.return_value = mock_wallet

    result = await gamification_service.unlock_achievement(uow, user_id=1, achievement_name="Test")

    assert result is True
    uow.user_achievements.add.assert_called_once()
    mock_event_publisher.publish.assert_called_once()
    # Check that points were added
    assert mock_wallet.balance == 50


@pytest.mark.asyncio
async def test_spend_points_success(gamification_service: GamificationService, uow: AsyncMock):
    uow.wallets.get_by_user_id.return_value = Wallet(user_id=1, balance=100)

    await gamification_service.spend_points(uow, user_id=1, amount=50, description="Test")

    uow.wallets.add.assert_called_once()
    uow.transactions.add.assert_called_once()
    assert uow.wallets.add.call_args[0][0].balance == 50


@pytest.mark.asyncio
async def test_spend_points_insufficient_balance(gamification_service: GamificationService, uow: AsyncMock):
    uow.wallets.get_by_user_id.return_value = Wallet(user_id=1, balance=40)

    with pytest.raises(ValueError, match="Insufficient balance."):
        await gamification_service.spend_points(uow, user_id=1, amount=50, description="Test")


@pytest.mark.asyncio
async def test_update_daily_streak_broken(gamification_service: GamificationService, uow: AsyncMock):
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    user = User(id=1, last_active_at=two_days_ago, current_streak=5, max_streak=5)

    await gamification_service.update_daily_streak(uow, user)

    assert user.current_streak == 1
    assert user.max_streak == 5 # Max streak should remain
    uow.users.add.assert_called_once_with(user)
