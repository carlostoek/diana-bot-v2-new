"""
Test suite for User Service following TDD methodology.

This module contains comprehensive tests for the IUserService interface,
covering all Telegram user management functionality including CRUD operations,
EventBus integration, and edge cases.

TDD Phase: RED - Tests written first, implementation comes later.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, call
from typing import Optional, List

# Import core interfaces
from src.core.interfaces import IEvent, IEventBus

# These imports will fail initially - that's expected in RED phase
# from src.modules.user.interfaces import IUserService, IUserRepository
# from src.modules.user.models import TelegramUser, UserCreateRequest, UserUpdateRequest
# from src.modules.user.events import UserCreatedEvent, UserUpdatedEvent, UserDeletedEvent
# from src.modules.user.service import UserService
# from src.modules.user.exceptions import (
#     UserNotFoundError,
#     DuplicateUserError,
#     InvalidUserDataError
# )


class TestTelegramUserModel:
    """Test cases for TelegramUser domain model."""
    
    def test_telegram_user_creation_with_required_fields(self):
        """Test creating TelegramUser with minimum required fields."""
        # Arrange
        telegram_id = 12345678
        first_name = "Diana"
        
        # Act & Assert
        # This will fail in RED phase - expected
        with pytest.raises(ImportError):
            # TelegramUser should have these required fields
            # user = TelegramUser(
            #     telegram_id=telegram_id,
            #     first_name=first_name,
            #     username=None,
            #     last_name=None,
            #     language_code="en",
            #     created_at=datetime.now(timezone.utc),
            #     updated_at=datetime.now(timezone.utc),
            #     is_active=True
            # )
            # assert user.telegram_id == telegram_id
            # assert user.first_name == first_name
            # assert user.username is None
            # assert user.last_name is None
            # assert user.language_code == "en"
            # assert user.is_active is True
            # assert isinstance(user.created_at, datetime)
            # assert isinstance(user.updated_at, datetime)
            pass
    
    def test_telegram_user_creation_with_all_fields(self):
        """Test creating TelegramUser with all optional fields."""
        # Arrange
        telegram_id = 12345678
        username = "diana_bot"
        first_name = "Diana"
        last_name = "Bot"
        language_code = "es"
        now = datetime.now(timezone.utc)
        
        # Act & Assert
        with pytest.raises(ImportError):
            # user = TelegramUser(
            #     telegram_id=telegram_id,
            #     username=username,
            #     first_name=first_name,
            #     last_name=last_name,
            #     language_code=language_code,
            #     created_at=now,
            #     updated_at=now,
            #     is_active=True
            # )
            # assert user.telegram_id == telegram_id
            # assert user.username == username
            # assert user.first_name == first_name
            # assert user.last_name == last_name
            # assert user.language_code == language_code
            # assert user.is_active is True
            pass
    
    def test_telegram_user_validation_invalid_telegram_id(self):
        """Test TelegramUser validation with invalid telegram_id."""
        with pytest.raises(ImportError):
            # Should raise InvalidUserDataError for negative or zero telegram_id
            # TelegramUser(
            #     telegram_id=0,  # Invalid
            #     first_name="Diana"
            # )
            pass
    
    def test_telegram_user_validation_empty_first_name(self):
        """Test TelegramUser validation with empty first_name."""
        with pytest.raises(ImportError):
            # Should raise InvalidUserDataError for empty first_name
            # TelegramUser(
            #     telegram_id=12345678,
            #     first_name=""  # Invalid
            # )
            pass


class TestUserCreateRequest:
    """Test cases for UserCreateRequest DTO."""
    
    def test_user_create_request_from_telegram_update(self):
        """Test creating UserCreateRequest from Telegram update data."""
        # Arrange
        telegram_data = {
            "id": 12345678,
            "username": "diana_bot",
            "first_name": "Diana",
            "last_name": "Bot",
            "language_code": "es"
        }
        
        # Act & Assert
        with pytest.raises(ImportError):
            # request = UserCreateRequest.from_telegram_data(telegram_data)
            # assert request.telegram_id == telegram_data["id"]
            # assert request.username == telegram_data["username"]
            # assert request.first_name == telegram_data["first_name"]
            # assert request.last_name == telegram_data["last_name"]
            # assert request.language_code == telegram_data["language_code"]
            pass
    
    def test_user_create_request_minimal_data(self):
        """Test UserCreateRequest with minimal Telegram data."""
        # Arrange
        telegram_data = {
            "id": 12345678,
            "first_name": "Diana"
        }
        
        # Act & Assert
        with pytest.raises(ImportError):
            # request = UserCreateRequest.from_telegram_data(telegram_data)
            # assert request.telegram_id == telegram_data["id"]
            # assert request.username is None
            # assert request.first_name == telegram_data["first_name"]
            # assert request.last_name is None
            # assert request.language_code == "en"  # Default
            pass


class TestUserUpdateRequest:
    """Test cases for UserUpdateRequest DTO."""
    
    def test_user_update_request_partial_update(self):
        """Test UserUpdateRequest with partial field updates."""
        # Arrange
        updates = {
            "username": "new_username",
            "language_code": "fr"
        }
        
        # Act & Assert
        with pytest.raises(ImportError):
            # request = UserUpdateRequest(**updates)
            # assert request.username == "new_username"
            # assert request.language_code == "fr"
            # assert request.first_name is None
            # assert request.last_name is None
            pass


class TestUserService:
    """Test cases for UserService implementation."""
    
    @pytest.fixture
    def mock_user_repository(self) -> AsyncMock:
        """Create a mock user repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_event_bus(self) -> AsyncMock:
        """Create a mock event bus."""
        return AsyncMock()
    
    @pytest.fixture
    def user_service(self, mock_user_repository: AsyncMock, mock_event_bus: AsyncMock):
        """Create UserService with mocked dependencies."""
        # This will fail in RED phase - expected
        with pytest.raises(ImportError):
            # return UserService(
            #     user_repository=mock_user_repository,
            #     event_bus=mock_event_bus
            # )
            pass
        return None
    
    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        user_service,
        mock_user_repository: AsyncMock,
        mock_event_bus: AsyncMock
    ):
        """Test successful user creation with event publishing."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        create_request = UserCreateRequest(
            telegram_id=12345678,
            username="diana_bot",
            first_name="Diana",
            last_name="Bot",
            language_code="es"
        )
        
        expected_user = TelegramUser(
            telegram_id=12345678,
            username="diana_bot",
            first_name="Diana",
            last_name="Bot",
            language_code="es",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        mock_user_repository.get_by_telegram_id.return_value = None
        mock_user_repository.create.return_value = expected_user
        
        # Act
        result = await user_service.create_user(create_request)
        
        # Assert
        assert result == expected_user
        mock_user_repository.get_by_telegram_id.assert_called_once_with(12345678)
        mock_user_repository.create.assert_called_once()
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserCreatedEvent)
        assert published_event.user_id == expected_user.telegram_id
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_error(
        self,
        user_service,
        mock_user_repository: AsyncMock,
        mock_event_bus: AsyncMock
    ):
        """Test user creation fails when user already exists."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        create_request = UserCreateRequest(
            telegram_id=12345678,
            first_name="Diana"
        )
        
        existing_user = TelegramUser(
            telegram_id=12345678,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        mock_user_repository.get_by_telegram_id.return_value = existing_user
        
        # Act & Assert
        with pytest.raises(DuplicateUserError) as exc_info:
            await user_service.create_user(create_request)
        
        assert "User with telegram_id 12345678 already exists" in str(exc_info.value)
        mock_user_repository.create.assert_not_called()
        mock_event_bus.publish.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_success(
        self,
        user_service,
        mock_user_repository: AsyncMock
    ):
        """Test successful user retrieval by telegram_id."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 12345678
        expected_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        mock_user_repository.get_by_telegram_id.return_value = expected_user
        
        # Act
        result = await user_service.get_user_by_telegram_id(telegram_id)
        
        # Assert
        assert result == expected_user
        mock_user_repository.get_by_telegram_id.assert_called_once_with(telegram_id)
    
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_found(
        self,
        user_service,
        mock_user_repository: AsyncMock
    ):
        """Test user retrieval fails when user doesn't exist."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 99999999
        mock_user_repository.get_by_telegram_id.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundError) as exc_info:
            await user_service.get_user_by_telegram_id(telegram_id)
        
        assert f"User with telegram_id {telegram_id} not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_success(
        self,
        user_service,
        mock_user_repository: AsyncMock
    ):
        """Test successful user retrieval by username."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        username = "diana_bot"
        expected_user = TelegramUser(
            telegram_id=12345678,
            username=username,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        mock_user_repository.get_by_username.return_value = expected_user
        
        # Act
        result = await user_service.get_user_by_username(username)
        
        # Assert
        assert result == expected_user
        mock_user_repository.get_by_username.assert_called_once_with(username)
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(
        self,
        user_service,
        mock_user_repository: AsyncMock
    ):
        """Test user retrieval by username returns None when not found."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        username = "nonexistent_user"
        mock_user_repository.get_by_username.return_value = None
        
        # Act
        result = await user_service.get_user_by_username(username)
        
        # Assert
        assert result is None
        mock_user_repository.get_by_username.assert_called_once_with(username)
    
    @pytest.mark.asyncio
    async def test_update_user_success(
        self,
        user_service,
        mock_user_repository: AsyncMock,
        mock_event_bus: AsyncMock
    ):
        """Test successful user update with event publishing."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 12345678
        update_request = UserUpdateRequest(
            username="new_username",
            language_code="fr"
        )
        
        existing_user = TelegramUser(
            telegram_id=telegram_id,
            username="old_username",
            first_name="Diana",
            language_code="es",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        updated_user = TelegramUser(
            telegram_id=telegram_id,
            username="new_username",
            first_name="Diana",
            language_code="fr",
            created_at=existing_user.created_at,
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        mock_user_repository.get_by_telegram_id.return_value = existing_user
        mock_user_repository.update.return_value = updated_user
        
        # Act
        result = await user_service.update_user(telegram_id, update_request)
        
        # Assert
        assert result == updated_user
        mock_user_repository.get_by_telegram_id.assert_called_once_with(telegram_id)
        mock_user_repository.update.assert_called_once()
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserUpdatedEvent)
        assert published_event.user_id == telegram_id
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self,
        user_service,
        mock_user_repository: AsyncMock,
        mock_event_bus: AsyncMock
    ):
        """Test user update fails when user doesn't exist."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 99999999
        update_request = UserUpdateRequest(username="new_username")
        
        mock_user_repository.get_by_telegram_id.return_value = None
        
        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await user_service.update_user(telegram_id, update_request)
        
        mock_user_repository.update.assert_not_called()
        mock_event_bus.publish.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self,
        user_service,
        mock_user_repository: AsyncMock,
        mock_event_bus: AsyncMock
    ):
        """Test successful user deactivation with event publishing."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 12345678
        existing_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        deactivated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Diana",
            created_at=existing_user.created_at,
            updated_at=datetime.now(timezone.utc),
            is_active=False
        )
        
        mock_user_repository.get_by_telegram_id.return_value = existing_user
        mock_user_repository.update.return_value = deactivated_user
        
        # Act
        result = await user_service.deactivate_user(telegram_id)
        
        # Assert
        assert result == deactivated_user
        assert result.is_active is False
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserDeletedEvent)
        assert published_event.user_id == telegram_id
    
    @pytest.mark.asyncio
    async def test_get_active_users_success(
        self,
        user_service,
        mock_user_repository: AsyncMock
    ):
        """Test retrieving list of active users."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        expected_users = [
            TelegramUser(
                telegram_id=12345678,
                first_name="Diana",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True
            ),
            TelegramUser(
                telegram_id=87654321,
                first_name="Bot",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True
            )
        ]
        
        mock_user_repository.get_active_users.return_value = expected_users
        
        # Act
        result = await user_service.get_active_users()
        
        # Assert
        assert result == expected_users
        assert len(result) == 2
        assert all(user.is_active for user in result)
        mock_user_repository.get_active_users.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_users_by_language_success(
        self,
        user_service,
        mock_user_repository: AsyncMock
    ):
        """Test retrieving users filtered by language code."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        language_code = "es"
        expected_users = [
            TelegramUser(
                telegram_id=12345678,
                first_name="Diana",
                language_code="es",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True
            )
        ]
        
        mock_user_repository.get_by_language_code.return_value = expected_users
        
        # Act
        result = await user_service.get_users_by_language(language_code)
        
        # Assert
        assert result == expected_users
        assert all(user.language_code == language_code for user in result)
        mock_user_repository.get_by_language_code.assert_called_once_with(language_code)


class TestUserServiceErrorHandling:
    """Test cases for UserService error handling scenarios."""
    
    @pytest.fixture
    def mock_user_repository(self) -> AsyncMock:
        """Create a mock user repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_event_bus(self) -> AsyncMock:
        """Create a mock event bus."""
        return AsyncMock()
    
    @pytest.fixture
    def user_service(self, mock_user_repository: AsyncMock, mock_event_bus: AsyncMock):
        """Create UserService with mocked dependencies."""
        # This will fail in RED phase - expected
        with pytest.raises(ImportError):
            # return UserService(
            #     user_repository=mock_user_repository,
            #     event_bus=mock_event_bus
            # )
            pass
        return None
    
    @pytest.mark.asyncio
    async def test_create_user_repository_error(
        self,
        user_service,
        mock_user_repository: AsyncMock,
        mock_event_bus: AsyncMock
    ):
        """Test user creation handles repository errors gracefully."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        create_request = UserCreateRequest(
            telegram_id=12345678,
            first_name="Diana"
        )
        
        mock_user_repository.get_by_telegram_id.return_value = None
        mock_user_repository.create.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await user_service.create_user(create_request)
        
        # Verify no event was published on error
        mock_event_bus.publish.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_user_event_bus_error(
        self,
        user_service,
        mock_user_repository: AsyncMock,
        mock_event_bus: AsyncMock
    ):
        """Test user creation handles event bus errors gracefully."""
        if user_service is None:
            pytest.skip("UserService not implemented yet - RED phase")
        
        # Arrange
        create_request = UserCreateRequest(
            telegram_id=12345678,
            first_name="Diana"
        )
        
        expected_user = TelegramUser(
            telegram_id=12345678,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        mock_user_repository.get_by_telegram_id.return_value = None
        mock_user_repository.create.return_value = expected_user
        mock_event_bus.publish.side_effect = Exception("Event bus error")
        
        # Act & Assert
        # Should still return the user even if event publishing fails
        result = await user_service.create_user(create_request)
        
        assert result == expected_user
        mock_event_bus.publish.assert_called_once()