import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.modules.user.service import UserService
from src.modules.user.models import User

@pytest.fixture
def mock_user_repository():
    return Mock()

@pytest.fixture
def mock_event_bus():
    return AsyncMock()

@pytest.fixture
def user_service(mock_user_repository, mock_event_bus):
    return UserService(user_repository=mock_user_repository, event_bus=mock_event_bus)

def test_update_user_profile(user_service, mock_user_repository):
    # Arrange
    user_id = 123
    update_data = {"first_name": "Jane"}
    mock_user_repository.update_user.return_value = User(id=user_id, first_name="Jane")

    # Act
    updated_user = user_service.update_user_profile(user_id, update_data)

    # Assert
    mock_user_repository.update_user.assert_called_once_with(user_id, update_data)
    assert updated_user is not None
    assert updated_user.first_name == "Jane"

def test_is_admin(user_service, mock_user_repository):
    # Arrange
    user_id = 123
    mock_user_repository.get_user_by_id.return_value = User(id=user_id, is_admin=True, first_name="Admin", role="admin")

    # Act
    is_admin = user_service.is_admin(user_id)

    # Assert
    assert is_admin is True

def test_has_role(user_service, mock_user_repository):
    # Arrange
    user_id = 123
    mock_user_repository.get_user_by_id.return_value = User(id=user_id, role="premium", first_name="User", is_admin=False)

    # Act
    has_role = user_service.has_role(user_id, "premium")

    # Assert
    assert has_role is True

@patch('src.modules.user.service.create_access_token')
def test_get_user_token(mock_create_token, user_service, mock_user_repository):
    # Arrange
    user_id = 123
    mock_user_repository.get_user_by_id.return_value = User(id=user_id, role="free", first_name="User", is_admin=False)
    mock_create_token.return_value = "fake_token"

    # Act
    token = user_service.get_user_token(user_id)

    # Assert
    assert token == "fake_token"
    mock_create_token.assert_called_once_with(data={"sub": str(user_id), "role": "free"})

def test_is_rate_limited(user_service):
    # Arrange
    user_id = 123
    user_service.rate_limit_max_requests = 2
    user_service.rate_limit_time_window = 10

    # Act & Assert
    assert user_service.is_rate_limited(user_id) is False # First request
    assert user_service.is_rate_limited(user_id) is False # Second request
    assert user_service.is_rate_limited(user_id) is True  # Third request, rate limited

@pytest.mark.asyncio
async def test_find_or_create_user_publishes_event_for_new_user(user_service, mock_user_repository, mock_event_bus):
    # Arrange
    user_id = 123
    user_data = {"id": user_id, "first_name": "New", "last_name": "User", "username": "newbie", "role": "free", "is_admin": False}
    mock_user_repository.get_user_by_id.return_value = None
    mock_user_repository.create_user.return_value = User(**user_data)

    # Act
    await user_service.find_or_create_user(user_id, "New", "User", "newbie")

    # Assert
    mock_event_bus.publish.assert_called_once()
    published_event = mock_event_bus.publish.call_args[0][0]
    assert published_event.type == "user.registered"
    assert published_event.data["user_id"] == user_id
