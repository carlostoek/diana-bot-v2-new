import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from src.modules.user.service import UserService
from src.modules.user.repository import UserRepository
from src.modules.user.models import User
from src.modules.user.events import UserCreatedEvent, UserRegisteredEvent


class TestUserServiceIntegration:
    """Integration tests for the UserService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        return AsyncMock()

    @pytest.fixture
    def user_repository(self, mock_db_session):
        """Create a user repository with a mock database session."""
        return UserRepository(mock_db_session)

    @pytest.fixture
    def user_service(self, user_repository, mock_event_bus):
        """Create a user service with mock dependencies."""
        return UserService(user_repository, mock_event_bus)

    def test_get_user_by_id_found(self, user_service, user_repository):
        """Test getting a user by ID when the user exists."""
        # Setup
        user_id = 12345
        expected_user = User(id=user_id, first_name="John", last_name="Doe", username="johndoe")
        user_repository.get_user_by_id = MagicMock(return_value=expected_user)

        # Execute
        result = user_service.get_user_by_id(user_id)

        # Verify
        assert result == expected_user
        user_repository.get_user_by_id.assert_called_once_with(user_id)

    def test_get_user_by_id_not_found(self, user_service, user_repository):
        """Test getting a user by ID when the user doesn't exist."""
        # Setup
        user_id = 99999
        user_repository.get_user_by_id = MagicMock(return_value=None)

        # Execute
        result = user_service.get_user_by_id(user_id)

        # Verify
        assert result is None
        user_repository.get_user_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_find_or_create_user_existing_user(self, user_service, user_repository):
        """Test finding or creating a user when the user already exists."""
        # Setup
        user_id = 12345
        first_name = "John"
        last_name = "Doe"
        username = "johndoe"
        
        existing_user = User(id=user_id, first_name=first_name, last_name=last_name, username=username)
        user_repository.get_user_by_id = MagicMock(return_value=existing_user)

        # Execute
        result = await user_service.find_or_create_user(user_id, first_name, last_name, username)

        # Verify
        assert result == existing_user
        user_repository.get_user_by_id.assert_called_once_with(user_id)
        user_repository.create_user.assert_not_called()
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_or_create_user_new_user(self, user_service, user_repository, mock_event_bus):
        """Test finding or creating a user when the user doesn't exist."""
        # Setup
        user_id = 12345
        first_name = "John"
        last_name = "Doe"
        username = "johndoe"
        
        user_data = {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username
        }
        
        new_user = User(**user_data)
        user_repository.get_user_by_id = MagicMock(return_value=None)
        user_repository.create_user = MagicMock(return_value=new_user)

        # Execute
        result = await user_service.find_or_create_user(user_id, first_name, last_name, username)

        # Verify
        assert result == new_user
        user_repository.get_user_by_id.assert_called_once_with(user_id)
        user_repository.create_user.assert_called_once_with(user_data)
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserRegisteredEvent)
        assert published_event.user_id == user_id
        assert published_event.first_name == first_name
        assert published_event.last_name == last_name
        assert published_event.username == username

    def test_update_user_profile_success(self, user_service, user_repository):
        """Test updating a user's profile successfully."""
        # Setup
        user_id = 12345
        update_data = {"first_name": "Jane", "username": "janedoe"}
        updated_user = User(id=user_id, first_name="Jane", last_name="Doe", username="janedoe")
        user_repository.update_user = MagicMock(return_value=updated_user)

        # Execute
        result = user_service.update_user_profile(user_id, update_data)

        # Verify
        assert result == updated_user
        user_repository.update_user.assert_called_once_with(user_id, update_data)

    def test_update_user_profile_not_found(self, user_service, user_repository):
        """Test updating a user's profile when the user doesn't exist."""
        # Setup
        user_id = 99999
        update_data = {"first_name": "Jane"}
        user_repository.update_user = MagicMock(return_value=None)

        # Execute
        result = user_service.update_user_profile(user_id, update_data)

        # Verify
        assert result is None
        user_repository.update_user.assert_called_once_with(user_id, update_data)

    def test_is_admin_true(self, user_service, user_repository):
        """Test checking if a user is an admin when they are."""
        # Setup
        user_id = 12345
        admin_user = User(id=user_id, first_name="Admin", is_admin=True)
        user_repository.get_user_by_id = MagicMock(return_value=admin_user)

        # Execute
        result = user_service.is_admin(user_id)

        # Verify
        assert result is True
        user_repository.get_user_by_id.assert_called_once_with(user_id)

    def test_is_admin_false(self, user_service, user_repository):
        """Test checking if a user is an admin when they aren't."""
        # Setup
        user_id = 12345
        regular_user = User(id=user_id, first_name="User", is_admin=False)
        user_repository.get_user_by_id = MagicMock(return_value=regular_user)

        # Execute
        result = user_service.is_admin(user_id)

        # Verify
        assert result is False
        user_repository.get_user_by_id.assert_called_once_with(user_id)

    def test_is_admin_user_not_found(self, user_service, user_repository):
        """Test checking if a user is an admin when the user doesn't exist."""
        # Setup
        user_id = 99999
        user_repository.get_user_by_id = MagicMock(return_value=None)

        # Execute
        result = user_service.is_admin(user_id)

        # Verify
        assert result is False
        user_repository.get_user_by_id.assert_called_once_with(user_id)

    def test_has_role_true(self, user_service, user_repository):
        """Test checking if a user has a specific role when they do."""
        # Setup
        user_id = 12345
        role = "vip"
        user_with_role = User(id=user_id, first_name="User", role=role)
        user_repository.get_user_by_id = MagicMock(return_value=user_with_role)

        # Execute
        result = user_service.has_role(user_id, role)

        # Verify
        assert result is True
        user_repository.get_user_by_id.assert_called_once_with(user_id)

    def test_has_role_false(self, user_service, user_repository):
        """Test checking if a user has a specific role when they don't."""
        # Setup
        user_id = 12345
        user_role = "free"
        requested_role = "vip"
        user_with_role = User(id=user_id, first_name="User", role=user_role)
        user_repository.get_user_by_id = MagicMock(return_value=user_with_role)

        # Execute
        result = user_service.has_role(user_id, requested_role)

        # Verify
        assert result is False
        user_repository.get_user_by_id.assert_called_once_with(user_id)

    def test_get_user_token_success(self, user_service, user_repository):
        """Test getting a user token successfully."""
        # Setup
        user_id = 12345
        user = User(id=user_id, first_name="User", role="free")
        user_repository.get_user_by_id = MagicMock(return_value=user)
        
        # Mock the create_access_token function
        with patch('src.modules.user.service.create_access_token') as mock_create_token:
            mock_create_token.return_value = "mocked_jwt_token"

            # Execute
            result = user_service.get_user_token(user_id)

            # Verify
            assert result == "mocked_jwt_token"
            user_repository.get_user_by_id.assert_called_once_with(user_id)
            mock_create_token.assert_called_once_with(data={"sub": str(user_id), "role": "free"})

    def test_get_user_token_user_not_found(self, user_service, user_repository):
        """Test getting a user token when the user doesn't exist."""
        # Setup
        user_id = 99999
        user_repository.get_user_by_id = MagicMock(return_value=None)

        # Execute
        result = user_service.get_user_token(user_id)

        # Verify
        assert result is None
        user_repository.get_user_by_id.assert_called_once_with(user_id)

    def test_is_rate_limited_under_limit(self, user_service):
        """Test rate limiting when under the limit."""
        # Setup
        user_id = 12345
        user_service.rate_limit_max_requests = 5
        user_service.rate_limit_time_window = 60

        # Execute
        result = user_service.is_rate_limited(user_id)

        # Verify
        assert result is False

    def test_is_rate_limited_over_limit(self, user_service):
        """Test rate limiting when over the limit."""
        # Setup
        user_id = 12345
        user_service.rate_limit_max_requests = 2
        user_service.rate_limit_time_window = 60
        
        # Add requests to exceed the limit
        user_service._rate_limit_requests[user_id] = [1000, 1010]  # Two recent requests

        # Execute
        result = user_service.is_rate_limited(user_id)

        # Verify
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])