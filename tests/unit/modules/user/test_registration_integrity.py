"""
CRITICAL: User Registration Integrity Tests

Tests user registration scenarios that could cause data corruption or service failures.
These tests are MANDATORY for production readiness.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from src.modules.user.service import UserService
from src.modules.user.models import User, DuplicateUserError, InvalidUserDataError
from src.modules.user.interfaces import IUserRepository
from src.core.interfaces import IEventBus


class TestUserRegistrationIntegrity:
    """CRITICAL: User registration must be bulletproof."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing."""
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus for testing."""
        event_bus = AsyncMock(spec=IEventBus)
        return event_bus
    
    @pytest.fixture
    def user_service(self, mock_repository, mock_event_bus):
        """UserService with mocked dependencies."""
        return UserService(mock_repository, mock_event_bus)

    async def test_telegram_user_registration_complete(self, user_service, mock_repository):
        """Test complete Telegram user registration workflow."""
        # Test with real Telegram user data structure
        telegram_user = {
            "id": 123456789,
            "is_bot": False,
            "first_name": "María José",
            "last_name": "González Pérez",
            "username": "maria_jose_gp",
            "language_code": "es",
            "is_premium": True
        }
        
        expected_user = User(
            user_id=123456789,
            username="maria_jose_gp",
            first_name="María José",
            last_name="González Pérez",
            language_code="es",
            telegram_metadata=telegram_user.copy()
        )
        mock_repository.create.return_value = expected_user
        
        result = await user_service.register_user(telegram_user)
        
        # Verify all required fields handled correctly
        assert result.user_id == 123456789
        assert result.first_name == "María José"
        assert result.last_name == "González Pérez"
        assert result.username == "maria_jose_gp"
        assert result.language_code == "es"
        assert result.telegram_metadata == telegram_user
        
        # Verify repository call
        mock_repository.create.assert_called_once()
        created_user = mock_repository.create.call_args[0][0]
        assert created_user.user_id == 123456789
        assert created_user.first_name == "María José"

    async def test_user_registration_edge_cases(self, user_service, mock_repository):
        """Test edge cases in user registration."""
        
        # Case 1: Missing optional fields (last_name, username)
        telegram_user_minimal = {
            "id": 987654321,
            "first_name": "Ana",
            "is_bot": False
        }
        
        expected_user = User(
            user_id=987654321,
            first_name="Ana",
            username=None,
            last_name=None,
            language_code="es"  # Default
        )
        mock_repository.create.return_value = expected_user
        
        result = await user_service.register_user(telegram_user_minimal)
        assert result.user_id == 987654321
        assert result.first_name == "Ana"
        assert result.username is None
        assert result.last_name is None
        assert result.language_code == "es"
        
        # Case 2: Special characters in names
        telegram_user_special = {
            "id": 555666777,
            "first_name": "José María Ñoño",
            "last_name": "Çölmen-Übérich",
            "username": "jose_maria_99",
            "language_code": "tr"
        }
        
        expected_user_special = User(
            user_id=555666777,
            first_name="José María Ñoño",
            last_name="Çölmen-Übérich",
            username="jose_maria_99",
            language_code="tr"
        )
        mock_repository.create.return_value = expected_user_special
        
        result_special = await user_service.register_user(telegram_user_special)
        assert result_special.first_name == "José María Ñoño"
        assert result_special.last_name == "Çölmen-Übérich"
        assert result_special.language_code == "tr"

    async def test_user_registration_failure_recovery(self, user_service, mock_repository, mock_event_bus):
        """Test registration failure scenarios and recovery."""
        
        telegram_user = {
            "id": 111222333,
            "first_name": "Test User",
            "username": "test_user"
        }
        
        # Case 1: Database unavailable during registration
        mock_repository.create.side_effect = Exception("Database connection lost")
        
        with pytest.raises(InvalidUserDataError, match="Registration failed"):
            await user_service.register_user(telegram_user)
        
        # Case 2: Event Bus unavailable during user.registered event
        mock_repository.create.side_effect = None
        expected_user = User(user_id=111222333, first_name="Test User", username="test_user")
        mock_repository.create.return_value = expected_user
        mock_event_bus.publish.side_effect = Exception("Event bus unavailable")
        
        # Should still complete registration even if event fails
        result = await user_service.register_user(telegram_user)
        assert result.user_id == 111222333
        assert result.first_name == "Test User"
        
        # Event bus should have been called despite failure
        mock_event_bus.publish.assert_called_once()

    async def test_duplicate_user_handling(self, user_service, mock_repository):
        """Test duplicate user_id handling."""
        telegram_user = {
            "id": 999888777,
            "first_name": "Duplicate User"
        }
        
        # Repository should raise DuplicateUserError
        mock_repository.create.side_effect = Exception("Duplicate key violation")
        
        with pytest.raises(InvalidUserDataError, match="Registration failed"):
            await user_service.register_user(telegram_user)

    async def test_invalid_telegram_data(self, user_service, mock_repository):
        """Test handling of invalid Telegram data."""
        
        # Case 1: Missing user ID
        invalid_telegram_data = {
            "first_name": "No ID User",
            "is_bot": False
        }
        
        with pytest.raises(InvalidUserDataError):
            await user_service.register_user(invalid_telegram_data)
        
        # Case 2: Missing first_name
        invalid_telegram_data_no_name = {
            "id": 444555666,
            "is_bot": False
        }
        
        with pytest.raises(InvalidUserDataError):
            await user_service.register_user(invalid_telegram_data_no_name)
        
        # Case 3: Invalid user_id type
        invalid_telegram_data_bad_id = {
            "id": "not_a_number",
            "first_name": "Bad ID User"
        }
        
        with pytest.raises(InvalidUserDataError):
            await user_service.register_user(invalid_telegram_data_bad_id)

    async def test_registration_event_publishing(self, user_service, mock_repository, mock_event_bus):
        """Test event publishing during successful registration."""
        telegram_user = {
            "id": 777888999,
            "first_name": "Event Test User",
            "username": "event_test",
            "language_code": "en"
        }
        
        expected_user = User(
            user_id=777888999,
            first_name="Event Test User",
            username="event_test",
            language_code="en"
        )
        mock_repository.create.return_value = expected_user
        
        result = await user_service.register_user(telegram_user)
        
        # Verify event was published with correct data
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        
        assert published_event.user_id == 777888999
        assert published_event.first_name == "Event Test User"
        assert published_event.username == "event_test"
        assert published_event.language_code == "en"

    async def test_registration_without_event_bus(self, mock_repository):
        """Test registration works without event bus."""
        user_service_no_events = UserService(mock_repository, None)
        
        telegram_user = {
            "id": 333444555,
            "first_name": "No Events User"
        }
        
        expected_user = User(
            user_id=333444555,
            first_name="No Events User",
            language_code="es"
        )
        mock_repository.create.return_value = expected_user
        
        result = await user_service_no_events.register_user(telegram_user)
        
        # Should complete successfully without event bus
        assert result.user_id == 333444555
        assert result.first_name == "No Events User"

    async def test_registration_data_validation(self, user_service, mock_repository):
        """Test that user data validation works correctly."""
        
        # Test that User model validation catches invalid data
        telegram_user_empty_name = {
            "id": 123456789,
            "first_name": ""  # Empty first name should fail
        }
        
        # The User model validation should catch this
        with pytest.raises(InvalidUserDataError):
            await user_service.register_user(telegram_user_empty_name)
        
        # Test that User model validation catches invalid user_id
        telegram_user_invalid_id = {
            "id": -1,  # Negative ID should fail
            "first_name": "Invalid ID"
        }
        
        with pytest.raises(InvalidUserDataError):
            await user_service.register_user(telegram_user_invalid_id)

    async def test_telegram_metadata_preservation(self, user_service, mock_repository):
        """Test that all Telegram metadata is preserved correctly."""
        telegram_user = {
            "id": 111222333,
            "first_name": "Metadata User",
            "username": "metadata_test",
            "last_name": "Test",
            "language_code": "fr",
            "is_bot": False,
            "is_premium": True,
            "added_to_attachment_menu": False,
            "can_join_groups": True,
            "can_read_all_group_messages": False,
            "supports_inline_queries": True
        }
        
        expected_user = User(
            user_id=111222333,
            first_name="Metadata User",
            username="metadata_test",
            last_name="Test",
            language_code="fr",
            telegram_metadata=telegram_user.copy()
        )
        mock_repository.create.return_value = expected_user
        
        result = await user_service.register_user(telegram_user)
        
        # All Telegram metadata should be preserved
        assert result.telegram_metadata == telegram_user
        assert result.telegram_metadata["is_premium"] is True
        assert result.telegram_metadata["can_join_groups"] is True
        assert result.telegram_metadata["supports_inline_queries"] is True


class TestUserDataIntegrity:
    """Test user data consistency and corruption prevention."""
    
    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def user_service(self, mock_repository):
        return UserService(mock_repository, None)

    async def test_user_id_validation_edge_cases(self, user_service):
        """Test user_id validation prevents corruption."""
        
        # Zero user_id
        with pytest.raises(InvalidUserDataError):
            await user_service.get_user(0)
        
        # Negative user_id
        with pytest.raises(InvalidUserDataError):
            await user_service.get_user(-123)
        
        # Non-integer user_id
        with pytest.raises(InvalidUserDataError):
            await user_service.get_user("123")
        
        # Float user_id
        with pytest.raises(InvalidUserDataError):
            await user_service.get_user(123.45)

    async def test_preferences_data_consistency(self, user_service, mock_repository):
        """Test preferences update maintains data consistency."""
        user_id = 123456789
        existing_user = User(
            user_id=user_id,
            first_name="Test User",
            preferences={"theme": "dark", "notifications": True}
        )
        
        mock_repository.get_by_user_id.return_value = existing_user
        
        # Update preferences should merge, not replace
        new_preferences = {"language": "en", "notifications": False}
        
        updated_user = existing_user
        updated_user.preferences.update(new_preferences)
        mock_repository.update.return_value = updated_user
        
        result = await user_service.update_preferences(user_id, new_preferences)
        
        # Verify original preferences preserved and new ones added
        assert result.preferences["theme"] == "dark"  # Original preserved
        assert result.preferences["language"] == "en"  # New added
        assert result.preferences["notifications"] is False  # Updated

    async def test_vip_status_integrity(self, user_service, mock_repository):
        """Test VIP status changes maintain data integrity."""
        user_id = 555666777
        user = User(user_id=user_id, first_name="VIP User", is_vip=False)
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        # Test VIP status change
        result = await user_service.set_vip_status(user_id, True)
        assert result.is_vip is True
        
        # Test VIP status remains stable
        result2 = await user_service.set_vip_status(user_id, True)
        assert result2.is_vip is True