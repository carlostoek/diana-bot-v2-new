import unittest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import pytest
from src.modules.user.service import UserService
from src.modules.user.models import User
from src.core.events import UserEvent
import time

@pytest.fixture
def mock_user_repository():
    return MagicMock()

@pytest.fixture
def mock_event_bus():
    mock = MagicMock()
    mock.publish = AsyncMock()
    return mock

@pytest.fixture
def user_service(mock_user_repository, mock_event_bus):
    return UserService(mock_user_repository, mock_event_bus)

def test_get_user_by_id(user_service, mock_user_repository):
    # Arrange
    user_id = 1
    mock_user = User(id=user_id, first_name="Test", last_name="User", username="testuser", is_admin=False, role="user")
    mock_user_repository.get_user_by_id.return_value = mock_user

    # Act
    user = user_service.get_user_by_id(user_id)

    # Assert
    mock_user_repository.get_user_by_id.assert_called_once_with(user_id)
    assert user == mock_user

@pytest.mark.asyncio
async def test_find_or_create_user_existing_user(user_service, mock_user_repository):
    # Arrange
    user_id = 1
    mock_user = User(id=user_id, first_name="Test", last_name="User", username="testuser", is_admin=False, role="user")
    mock_user_repository.get_user_by_id.return_value = mock_user

    # Act
    user = await user_service.find_or_create_user(user_id, "Test", "User", "testuser")

    # Assert
    mock_user_repository.get_user_by_id.assert_called_once_with(user_id)
    mock_user_repository.create_user.assert_not_called()
    assert user == mock_user

@pytest.mark.asyncio
async def test_find_or_create_user_new_user(user_service, mock_user_repository, mock_event_bus):
    # Arrange
    user_id = 1
    user_data = {"id": user_id, "first_name": "New", "last_name": "User", "username": "newuser"}
    new_user = User(**user_data, is_admin=False, role="user")
    mock_user_repository.get_user_by_id.return_value = None
    mock_user_repository.create_user.return_value = new_user

    # Act
    user = await user_service.find_or_create_user(user_id, "New", "User", "newuser")

    # Assert
    mock_user_repository.get_user_by_id.assert_called_once_with(user_id)
    mock_user_repository.create_user.assert_called_once_with(user_data)
    mock_event_bus.publish.assert_awaited_once()
    assert user == new_user

def test_update_user_profile(user_service, mock_user_repository):
    # Arrange
    user_id = 1
    update_data = {"first_name": "Updated"}
    updated_user = User(id=user_id, first_name="Updated", last_name="User", username="testuser", is_admin=False, role="user")
    mock_user_repository.update_user.return_value = updated_user

    # Act
    user = user_service.update_user_profile(user_id, update_data)

    # Assert
    mock_user_repository.update_user.assert_called_once_with(user_id, update_data)
    assert user == updated_user

def test_is_admin_true(user_service, mock_user_repository):
    # Arrange
    user_id = 1
    admin_user = User(id=user_id, first_name="Admin", last_name="User", username="adminuser", is_admin=True, role="admin")
    mock_user_repository.get_user_by_id.return_value = admin_user

    # Act
    is_admin = user_service.is_admin(user_id)

    # Assert
    assert is_admin is True

def test_is_admin_false(user_service, mock_user_repository):
    # Arrange
    user_id = 1
    regular_user = User(id=user_id, first_name="Test", last_name="User", username="testuser", is_admin=False, role="user")
    mock_user_repository.get_user_by_id.return_value = regular_user

    # Act
    is_admin = user_service.is_admin(user_id)

    # Assert
    assert is_admin is False

def test_has_role_true(user_service, mock_user_repository):
    # Arrange
    user_id = 1
    user_with_role = User(id=user_id, first_name="Test", last_name="User", username="testuser", is_admin=False, role="editor")
    mock_user_repository.get_user_by_id.return_value = user_with_role

    # Act
    has_role = user_service.has_role(user_id, "editor")

    # Assert
    assert has_role is True

def test_has_role_false(user_service, mock_user_repository):
    # Arrange
    user_id = 1
    user_with_role = User(id=user_id, first_name="Test", last_name="User", username="testuser", is_admin=False, role="editor")
    mock_user_repository.get_user_by_id.return_value = user_with_role

    # Act
    has_role = user_service.has_role(user_id, "viewer")

    # Assert
    assert has_role is False

@patch('src.modules.user.service.create_access_token')
def test_get_user_token(mock_create_access_token, user_service, mock_user_repository):
    # Arrange
    user_id = 1
    user = User(id=user_id, first_name="Test", last_name="User", username="testuser", is_admin=False, role="user")
    mock_user_repository.get_user_by_id.return_value = user
    mock_create_access_token.return_value = "some_jwt_token"

    # Act
    token = user_service.get_user_token(user_id)

    # Assert
    mock_create_access_token.assert_called_once_with(data={"sub": str(user_id), "role": "user"})
    assert token == "some_jwt_token"

def test_rate_limiting(user_service):
    # Arrange
    user_id = 1
    user_service.rate_limit_max_requests = 5
    user_service.rate_limit_time_window = 1

    # Act & Assert
    for _ in range(5):
        assert user_service.is_rate_limited(user_id) is False

    assert user_service.is_rate_limited(user_id) is True

    # Wait for the time window to pass
    time.sleep(1)

    assert user_service.is_rate_limited(user_id) is False
