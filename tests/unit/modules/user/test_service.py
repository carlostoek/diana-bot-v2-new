"""Tests for UserService - Minimal Implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.modules.user.service import UserService, create_user_service
from src.modules.user.models import User, UserStats, UserNotFoundError, DuplicateUserError, InvalidUserDataError
from src.modules.user.events import UserRegisteredEvent, UserPreferencesUpdatedEvent, UserActivityEvent


class TestUserService:
    """Test UserService functionality."""

    @pytest.fixture
    def mock_repository(self):
        """Mock user repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository, mock_event_bus):
        """Create service with mocked dependencies."""
        return UserService(mock_repository, mock_event_bus)

    @pytest.fixture
    def sample_user(self):
        """Sample user for tests."""
        return User(
            user_id=123456789,
            username="diana_bot",
            first_name="Diana",
            last_name="Bot",
            language_code="es"
        )

    @pytest.fixture
    def telegram_data(self):
        """Sample Telegram user data."""
        return {
            "id": 123456789,
            "is_bot": False,
            "first_name": "Diana",
            "last_name": "Bot",
            "username": "diana_bot",
            "language_code": "es"
        }

    @pytest.mark.asyncio
    async def test_register_user_success(self, service, mock_repository, mock_event_bus, telegram_data):
        """Test successful user registration."""
        created_user = User(
            user_id=telegram_data["id"],
            first_name=telegram_data["first_name"],
            username=telegram_data["username"],
            telegram_metadata=telegram_data.copy()
        )
        mock_repository.create.return_value = created_user

        result = await service.register_user(telegram_data)

        assert result == created_user
        mock_repository.create.assert_called_once()
        mock_event_bus.publish.assert_called_once()

        # Verify event was published
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserRegisteredEvent)
        assert published_event.user_id == telegram_data["id"]
        assert published_event.first_name == telegram_data["first_name"]

    @pytest.mark.asyncio
    async def test_register_user_minimal_data(self, service, mock_repository, mock_event_bus):
        """Test registering user with minimal data."""
        telegram_data = {
            "id": 123456789,
            "first_name": "Diana"
        }
        
        created_user = User(
            user_id=telegram_data["id"],
            first_name=telegram_data["first_name"],
            language_code="es"
        )
        mock_repository.create.return_value = created_user

        result = await service.register_user(telegram_data)

        assert result.user_id == 123456789
        assert result.first_name == "Diana"
        assert result.language_code == "es"

    @pytest.mark.asyncio
    async def test_register_user_repository_error(self, service, mock_repository, telegram_data):
        """Test user registration with repository error."""
        mock_repository.create.side_effect = Exception("Database error")

        with pytest.raises(InvalidUserDataError, match="Registration failed"):
            await service.register_user(telegram_data)

    @pytest.mark.asyncio
    async def test_register_user_no_event_bus(self, mock_repository, telegram_data):
        """Test user registration without event bus."""
        service = UserService(mock_repository, None)
        
        created_user = User(
            user_id=telegram_data["id"],
            first_name=telegram_data["first_name"]
        )
        mock_repository.create.return_value = created_user

        result = await service.register_user(telegram_data)

        assert result == created_user
        # Should not fail even without event bus

    @pytest.mark.asyncio
    async def test_get_user_success(self, service, mock_repository, sample_user):
        """Test successful user retrieval."""
        mock_repository.get_by_user_id.return_value = sample_user

        result = await service.get_user(123456789)

        assert result == sample_user
        mock_repository.get_by_user_id.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, service, mock_repository):
        """Test getting non-existent user."""
        mock_repository.get_by_user_id.return_value = None

        with pytest.raises(UserNotFoundError, match="not found"):
            await service.get_user(999999)

    @pytest.mark.asyncio
    async def test_get_user_invalid_id(self, service):
        """Test getting user with invalid ID."""
        with pytest.raises(InvalidUserDataError, match="positive integer"):
            await service.get_user(0)

        with pytest.raises(InvalidUserDataError, match="positive integer"):
            await service.get_user(-1)

    @pytest.mark.asyncio
    async def test_update_preferences_success(self, service, mock_repository, mock_event_bus, sample_user):
        """Test successful preferences update."""
        mock_repository.get_by_user_id.return_value = sample_user
        mock_repository.update.return_value = sample_user
        
        preferences = {"theme": "dark", "notifications": True}

        result = await service.update_preferences(123456789, preferences)

        assert result == sample_user
        assert sample_user.preferences == preferences
        mock_repository.update.assert_called_once_with(sample_user)
        mock_event_bus.publish.assert_called_once()

        # Verify event was published
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserPreferencesUpdatedEvent)

    @pytest.mark.asyncio
    async def test_mark_user_active_success(self, service, mock_repository, mock_event_bus, sample_user):
        """Test marking user as active."""
        mock_repository.get_by_user_id.return_value = sample_user
        original_timestamp = sample_user.last_active

        await service.mark_user_active(123456789)

        assert sample_user.last_active > original_timestamp
        mock_repository.update.assert_called_once_with(sample_user)
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_user_active_not_found(self, service, mock_repository):
        """Test marking non-existent user as active."""
        mock_repository.get_by_user_id.return_value = None

        # Should not raise exception, just log warning
        await service.mark_user_active(999999)

        mock_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, service, mock_repository, sample_user):
        """Test getting user statistics."""
        sample_user.is_vip = True
        sample_user.preferences = {"interaction_history": [1, 2, 3]}
        mock_repository.get_by_user_id.return_value = sample_user

        result = await service.get_user_stats(123456789)

        assert isinstance(result, UserStats)
        assert result.total_interactions == 3
        assert result.registration_date == sample_user.created_at
        assert result.vip_since == sample_user.created_at

    @pytest.mark.asyncio
    async def test_get_users_for_service_success(self, service, mock_repository):
        """Test getting users for service integration."""
        users = [
            User(user_id=123, first_name="User1"),
            User(user_id=456, first_name="User2")
        ]
        mock_repository.get_users_for_service.return_value = users

        result = await service.get_users_for_service([123, 456])

        assert result == users
        mock_repository.get_users_for_service.assert_called_once_with([123, 456])

    @pytest.mark.asyncio
    async def test_get_users_for_service_empty_list(self, service, mock_repository):
        """Test getting users with empty list."""
        result = await service.get_users_for_service([])

        assert result == []
        mock_repository.get_users_for_service.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_users_for_service_invalid_ids(self, service, mock_repository):
        """Test getting users with invalid IDs."""
        mock_repository.get_users_for_service.return_value = []

        result = await service.get_users_for_service([123, 0, -1, 456])

        # Should filter out invalid IDs
        mock_repository.get_users_for_service.assert_called_once_with([123, 456])

    @pytest.mark.asyncio
    async def test_is_vip_user_true(self, service, mock_repository, sample_user):
        """Test checking VIP user (true)."""
        sample_user.is_vip = True
        mock_repository.get_by_user_id.return_value = sample_user

        result = await service.is_vip_user(123456789)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_vip_user_false(self, service, mock_repository, sample_user):
        """Test checking VIP user (false)."""
        sample_user.is_vip = False
        mock_repository.get_by_user_id.return_value = sample_user

        result = await service.is_vip_user(123456789)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_vip_user_not_found(self, service, mock_repository):
        """Test checking VIP status for non-existent user."""
        mock_repository.get_by_user_id.return_value = None

        result = await service.is_vip_user(999999)

        assert result is False

    @pytest.mark.asyncio
    async def test_set_vip_status_success(self, service, mock_repository, mock_event_bus, sample_user):
        """Test setting VIP status."""
        sample_user.is_vip = False
        mock_repository.get_by_user_id.return_value = sample_user
        mock_repository.update.return_value = sample_user

        result = await service.set_vip_status(123456789, True)

        assert result.is_vip is True
        mock_repository.update.assert_called_once_with(sample_user)
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_vip_status_no_change(self, service, mock_repository, mock_event_bus, sample_user):
        """Test setting VIP status to same value."""
        sample_user.is_vip = True
        mock_repository.get_by_user_id.return_value = sample_user
        mock_repository.update.return_value = sample_user

        await service.set_vip_status(123456789, True)

        mock_repository.update.assert_called_once_with(sample_user)
        # Should not publish event if status didn't change
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_count_success(self, service, mock_repository):
        """Test getting user count."""
        mock_repository.count_users.return_value = 42

        result = await service.get_user_count()

        assert result == 42

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, service, mock_repository):
        """Test healthy service health check."""
        mock_repository.health_check.return_value = {
            "status": "healthy",
            "users_count": 100
        }

        result = await service.health_check()

        assert result["status"] == "healthy"
        assert result["service"] == "UserService"
        assert result["repository"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_repository(self, service, mock_repository):
        """Test health check with unhealthy repository."""
        mock_repository.health_check.return_value = {
            "status": "unhealthy",
            "error": "Database connection failed"
        }

        result = await service.health_check()

        assert result["status"] == "unhealthy"
        assert "Repository unhealthy" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_repository_error(self, service, mock_repository):
        """Test health check with repository error."""
        mock_repository.health_check.side_effect = Exception("Connection failed")

        result = await service.health_check()

        assert result["status"] == "unhealthy"
        assert "Health check failed" in result["error"]

    @pytest.mark.asyncio
    async def test_get_user_language_success(self, service, mock_repository, sample_user):
        """Test getting user language."""
        sample_user.language_code = "en"
        mock_repository.get_by_user_id.return_value = sample_user

        result = await service.get_user_language(123456789)

        assert result == "en"

    @pytest.mark.asyncio
    async def test_get_user_language_default(self, service, mock_repository):
        """Test getting language for non-existent user."""
        mock_repository.get_by_user_id.return_value = None

        result = await service.get_user_language(999999)

        assert result == "es"  # Default Spanish

    @pytest.mark.asyncio
    async def test_bulk_mark_users_active_success(self, service, mock_repository, sample_user):
        """Test bulk marking users as active."""
        mock_repository.get_by_user_id.return_value = sample_user

        result = await service.bulk_mark_users_active([123, 456])

        assert result == 2  # Both users processed successfully
        assert mock_repository.get_by_user_id.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_mark_users_active_partial_failure(self, service, mock_repository, sample_user):
        """Test bulk marking users with some failures."""
        mock_repository.get_by_user_id.side_effect = [sample_user, None]

        result = await service.bulk_mark_users_active([123, 456])

        assert result == 1  # Only one user processed successfully


class TestCreateUserService:
    """Test factory function for UserService."""

    @pytest.mark.asyncio
    async def test_create_user_service_success(self):
        """Test successful service creation."""
        mock_repository = AsyncMock()
        mock_event_bus = AsyncMock()

        service = await create_user_service(mock_repository, mock_event_bus)

        assert isinstance(service, UserService)
        assert service._repository == mock_repository
        assert service._event_bus == mock_event_bus

    @pytest.mark.asyncio
    async def test_create_user_service_no_event_bus(self):
        """Test service creation without event bus."""
        mock_repository = AsyncMock()

        service = await create_user_service(mock_repository)

        assert isinstance(service, UserService)
        assert service._repository == mock_repository
        assert service._event_bus is None


class TestUserServiceEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def service_no_event_bus(self, mock_repository):
        """Service without event bus for testing."""
        return UserService(mock_repository, None)

    @pytest.fixture
    def mock_repository(self):
        """Mock repository for edge case tests."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_register_user_missing_id(self, service_no_event_bus):
        """Test registering user with missing ID."""
        telegram_data = {"first_name": "Diana"}

        with pytest.raises(InvalidUserDataError):
            await service_no_event_bus.register_user(telegram_data)

    @pytest.mark.asyncio
    async def test_register_user_missing_first_name(self, service_no_event_bus):
        """Test registering user with missing first name."""
        telegram_data = {"id": 123456789}

        with pytest.raises(InvalidUserDataError):
            await service_no_event_bus.register_user(telegram_data)

    @pytest.mark.asyncio
    async def test_get_vip_users_empty_result(self, service_no_event_bus, mock_repository):
        """Test getting VIP users with no results."""
        mock_repository.get_users_for_service.return_value = []

        result = await service_no_event_bus.get_vip_users()

        assert result == []

    @pytest.mark.asyncio
    async def test_search_users_by_name_short_term(self, service_no_event_bus):
        """Test searching users with short search term."""
        result = await service_no_event_bus.search_users_by_name("a")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_users_by_name_empty_term(self, service_no_event_bus):
        """Test searching users with empty search term."""
        result = await service_no_event_bus.search_users_by_name("")

        assert result == []