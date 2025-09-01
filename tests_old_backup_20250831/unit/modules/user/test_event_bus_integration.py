"""
CRITICAL: Event Bus Integration Tests

Tests Event Bus communication reliability and failure handling.
Ensures service coordination doesn't break when events fail.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.modules.user.service import UserService
from src.modules.user.models import User
from src.modules.user.interfaces import IUserRepository
from src.modules.user.events import UserRegisteredEvent, UserPreferencesUpdatedEvent, UserActivityEvent
from src.core.interfaces import IEventBus


class TestEventBusIntegration:
    """CRITICAL: Event Bus communication must be reliable."""
    
    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def mock_event_bus(self):
        event_bus = AsyncMock(spec=IEventBus)
        return event_bus
    
    @pytest.fixture
    def user_service(self, mock_repository, mock_event_bus):
        return UserService(mock_repository, mock_event_bus)

    async def test_user_registration_event_publishing(self, user_service, mock_repository, mock_event_bus):
        """Test UserRegisteredEvent is published correctly."""
        telegram_user = {
            "id": 123456789,
            "first_name": "Event User",
            "username": "event_user",
            "language_code": "es"
        }
        
        expected_user = User(
            user_id=123456789,
            first_name="Event User",
            username="event_user",
            language_code="es"
        )
        mock_repository.create.return_value = expected_user
        
        await user_service.register_user(telegram_user)
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        
        assert isinstance(published_event, UserRegisteredEvent)
        assert published_event.user_id == 123456789
        assert published_event.first_name == "Event User"
        assert published_event.username == "event_user"
        assert published_event.language_code == "es"

    async def test_preferences_update_event_publishing(self, user_service, mock_repository, mock_event_bus):
        """Test UserPreferencesUpdatedEvent is published correctly."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Prefs User")
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        new_preferences = {
            "theme": "dark",
            "notifications": True,
            "language": "en"
        }
        
        await user_service.update_preferences(user_id, new_preferences)
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        
        assert isinstance(published_event, UserPreferencesUpdatedEvent)
        assert published_event.user_id == user_id
        assert published_event.preferences == new_preferences

    async def test_user_activity_event_publishing(self, user_service, mock_repository, mock_event_bus):
        """Test UserActivityEvent is published correctly."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Activity User")
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        await user_service.mark_user_active(user_id)
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        
        assert isinstance(published_event, UserActivityEvent)
        assert published_event.user_id == user_id
        assert published_event.activity_type == "user_active"
        assert "timestamp" in published_event.activity_data

    async def test_vip_status_change_event_publishing(self, user_service, mock_repository, mock_event_bus):
        """Test VIP status change publishes activity event."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="VIP User", is_vip=False)
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        await user_service.set_vip_status(user_id, True)
        
        # Verify VIP status change event was published
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        
        assert isinstance(published_event, UserActivityEvent)
        assert published_event.user_id == user_id
        assert published_event.activity_type == "vip_status_changed"
        assert published_event.activity_data["old_status"] is False
        assert published_event.activity_data["new_status"] is True

    async def test_no_event_for_unchanged_vip_status(self, user_service, mock_repository, mock_event_bus):
        """Test no event is published when VIP status doesn't change."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="VIP User", is_vip=True)
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        # Set VIP status to same value
        await user_service.set_vip_status(user_id, True)
        
        # No event should be published since status didn't change
        mock_event_bus.publish.assert_not_called()


class TestEventBusFailureHandling:
    """Test UserService behavior when Event Bus fails."""
    
    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def failing_event_bus(self):
        event_bus = AsyncMock(spec=IEventBus)
        event_bus.publish.side_effect = Exception("Event Bus unavailable")
        return event_bus
    
    @pytest.fixture
    def user_service_with_failing_bus(self, mock_repository, failing_event_bus):
        return UserService(mock_repository, failing_event_bus)

    async def test_registration_continues_despite_event_failure(
        self, user_service_with_failing_bus, mock_repository, failing_event_bus
    ):
        """Test registration completes even if event publishing fails."""
        telegram_user = {
            "id": 123456789,
            "first_name": "Resilient User",
            "username": "resilient_user"
        }
        
        expected_user = User(
            user_id=123456789,
            first_name="Resilient User",
            username="resilient_user"
        )
        mock_repository.create.return_value = expected_user
        
        # Registration should complete successfully despite event failure
        result = await user_service_with_failing_bus.register_user(telegram_user)
        
        assert result.user_id == 123456789
        assert result.first_name == "Resilient User"
        
        # Verify repository operation completed
        mock_repository.create.assert_called_once()
        
        # Verify event publishing was attempted
        failing_event_bus.publish.assert_called_once()

    async def test_preferences_update_continues_despite_event_failure(
        self, user_service_with_failing_bus, mock_repository, failing_event_bus
    ):
        """Test preferences update completes even if event publishing fails."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Resilient User")
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        new_preferences = {"theme": "dark", "language": "en"}
        
        # Update should complete successfully despite event failure
        result = await user_service_with_failing_bus.update_preferences(user_id, new_preferences)
        
        assert result.user_id == user_id
        
        # Verify database operation completed
        mock_repository.update.assert_called_once()
        
        # Verify event publishing was attempted
        failing_event_bus.publish.assert_called_once()

    async def test_activity_marking_continues_despite_event_failure(
        self, user_service_with_failing_bus, mock_repository, failing_event_bus
    ):
        """Test activity marking completes even if event publishing fails."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Resilient User")
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        # Activity marking should complete successfully despite event failure
        await user_service_with_failing_bus.mark_user_active(user_id)
        
        # Verify database operation completed
        mock_repository.update.assert_called_once()
        
        # Verify event publishing was attempted
        failing_event_bus.publish.assert_called_once()

    async def test_vip_status_change_continues_despite_event_failure(
        self, user_service_with_failing_bus, mock_repository, failing_event_bus
    ):
        """Test VIP status change completes even if event publishing fails."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Resilient User", is_vip=False)
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        # VIP status change should complete successfully despite event failure
        result = await user_service_with_failing_bus.set_vip_status(user_id, True)
        
        assert result.is_vip is True
        
        # Verify database operation completed
        mock_repository.update.assert_called_once()
        
        # Verify event publishing was attempted
        failing_event_bus.publish.assert_called_once()


class TestEventBuslessOperation:
    """Test UserService works correctly without Event Bus."""
    
    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def user_service_no_events(self, mock_repository):
        return UserService(mock_repository, None)  # No event bus

    async def test_registration_without_event_bus(self, user_service_no_events, mock_repository):
        """Test registration works without Event Bus."""
        telegram_user = {
            "id": 123456789,
            "first_name": "No Events User"
        }
        
        expected_user = User(
            user_id=123456789,
            first_name="No Events User",
            language_code="es"
        )
        mock_repository.create.return_value = expected_user
        
        result = await user_service_no_events.register_user(telegram_user)
        
        assert result.user_id == 123456789
        assert result.first_name == "No Events User"
        mock_repository.create.assert_called_once()

    async def test_preferences_update_without_event_bus(self, user_service_no_events, mock_repository):
        """Test preferences update works without Event Bus."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="No Events User")
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        new_preferences = {"theme": "dark"}
        result = await user_service_no_events.update_preferences(user_id, new_preferences)
        
        assert result.user_id == user_id
        mock_repository.update.assert_called_once()

    async def test_activity_marking_without_event_bus(self, user_service_no_events, mock_repository):
        """Test activity marking works without Event Bus."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="No Events User")
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        await user_service_no_events.mark_user_active(user_id)
        
        mock_repository.update.assert_called_once()

    async def test_vip_status_without_event_bus(self, user_service_no_events, mock_repository):
        """Test VIP status change works without Event Bus."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="No Events User", is_vip=False)
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        result = await user_service_no_events.set_vip_status(user_id, True)
        
        assert result.is_vip is True
        mock_repository.update.assert_called_once()


class TestEventDataIntegrity:
    """Test event data integrity and serialization."""
    
    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def event_capture_bus(self):
        """Event bus that captures events for inspection."""
        event_bus = AsyncMock(spec=IEventBus)
        event_bus.published_events = []
        
        async def capture_publish(event):
            event_bus.published_events.append(event)
        
        event_bus.publish.side_effect = capture_publish
        return event_bus
    
    @pytest.fixture
    def user_service_with_capture(self, mock_repository, event_capture_bus):
        return UserService(mock_repository, event_capture_bus), event_capture_bus

    async def test_event_serialization_compatibility(self, user_service_with_capture, mock_repository):
        """Test events can be properly serialized for transport."""
        user_service, event_bus = user_service_with_capture
        
        telegram_user = {
            "id": 123456789,
            "first_name": "Serialization User",
            "username": "serial_user",
            "language_code": "es"
        }
        
        expected_user = User(
            user_id=123456789,
            first_name="Serialization User",
            username="serial_user",
            language_code="es"
        )
        mock_repository.create.return_value = expected_user
        
        await user_service.register_user(telegram_user)
        
        # Get the published event
        assert len(event_bus.published_events) == 1
        event = event_bus.published_events[0]
        
        # Test event can be converted to dict (for serialization)
        event_dict = {
            "user_id": event.user_id,
            "first_name": event.first_name,
            "username": event.username,
            "language_code": event.language_code,
            "event_type": "user_registered",
            "timestamp": event.timestamp.isoformat()
        }
        
        # Verify all required data is present
        assert event_dict["user_id"] == 123456789
        assert event_dict["first_name"] == "Serialization User"
        assert event_dict["username"] == "serial_user"
        assert event_dict["language_code"] == "es"

    async def test_complex_event_data_integrity(self, user_service_with_capture, mock_repository):
        """Test complex event data maintains integrity."""
        user_service, event_bus = user_service_with_capture
        
        user_id = 123456789
        user = User(user_id=user_id, first_name="Complex User")
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        # Complex preferences with nested structures
        complex_preferences = {
            "ui_settings": {
                "theme": "dark",
                "language": "es",
                "notifications": {
                    "push": True,
                    "types": ["achievements", "stories"]
                }
            },
            "game_data": {
                "level": 15,
                "points": 2500,
                "achievements": [1, 3, 5, 7, 11]
            }
        }
        
        await user_service.update_preferences(user_id, complex_preferences)
        
        # Get the published event
        assert len(event_bus.published_events) == 1
        event = event_bus.published_events[0]
        
        # Verify complex data is preserved
        assert event.preferences == complex_preferences
        assert event.preferences["ui_settings"]["theme"] == "dark"
        assert event.preferences["game_data"]["achievements"] == [1, 3, 5, 7, 11]