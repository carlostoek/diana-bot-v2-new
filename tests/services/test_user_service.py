import pytest
from unittest.mock import AsyncMock
from aiogram import types as tg_types
from src.services.user_service import UserService
from src.domain.models import User


@pytest.fixture
def mock_user_repo():
    return AsyncMock()

@pytest.fixture
def mock_event_publisher():
    return AsyncMock()

@pytest.fixture
def user_service(mock_user_repo, mock_event_publisher):
    return UserService(mock_user_repo, mock_event_publisher)


@pytest.mark.asyncio
async def test_get_or_create_user_creates_new_user(
    user_service: UserService,
    mock_user_repo: AsyncMock,
    mock_event_publisher: AsyncMock,
):
    """
    Test that a new user is created when they don't exist.
    """
    mock_user_repo.get.return_value = None
    telegram_user = tg_types.User(id=1, is_bot=False, first_name="Test")

    user, is_new = await user_service.get_or_create_user(telegram_user)

    assert is_new is True
    assert user.id == 1
    assert user.first_name == "Test"
    mock_user_repo.get.assert_called_once_with(1)
    mock_user_repo.add.assert_called_once()
    mock_event_publisher.publish.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_user_returns_existing_user(
    user_service: UserService,
    mock_user_repo: AsyncMock,
    mock_event_publisher: AsyncMock,
):
    """
    Test that an existing user is returned without creating a new one.
    """
    existing_user = User(id=2, first_name="Existing")
    mock_user_repo.get.return_value = existing_user
    telegram_user = tg_types.User(id=2, is_bot=False, first_name="Existing")

    user, is_new = await user_service.get_or_create_user(telegram_user)

    assert is_new is False
    assert user.id == 2
    mock_user_repo.get.assert_called_once_with(2)
    mock_user_repo.add.assert_not_called()
    mock_event_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_user_updates_user_info(
    user_service: UserService,
    mock_user_repo: AsyncMock,
):
    """
    Test that user's profile info is updated if it has changed.
    """
    existing_user = User(id=3, first_name="Old Name", username="old_username")
    mock_user_repo.get.return_value = existing_user
    telegram_user = tg_types.User(id=3, is_bot=False, first_name="New Name", username="new_username")

    user, is_new = await user_service.get_or_create_user(telegram_user)

    assert is_new is False
    assert user.id == 3
    assert user.first_name == "New Name"
    assert user.username == "new_username"
    mock_user_repo.add.assert_called_once_with(existing_user)
