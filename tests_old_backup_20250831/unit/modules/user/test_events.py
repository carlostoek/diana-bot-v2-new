"""Tests for User events - Minimal Implementation."""

import pytest
from datetime import datetime, timezone
from src.modules.user.events import (
    UserRegisteredEvent, 
    UserPreferencesUpdatedEvent, 
    UserActivityEvent,
    BaseUserEvent
)


class TestBaseUserEvent:
    """Test BaseUserEvent functionality."""
    
    def test_base_event_creation(self):
        """Test creating base user event."""
        # Create a concrete subclass for testing
        class TestEvent(BaseUserEvent):
            @property
            def event_type(self) -> str:
                return "test.event"
        
        event = TestEvent(user_id=123)
        
        assert event.user_id == 123
        assert isinstance(event.event_id, str)
        assert isinstance(event.timestamp, datetime)
        assert event.aggregate_id == "123"
        assert event.event_type == "test.event"
    
    def test_base_event_with_custom_values(self):
        """Test base event with custom event_id and timestamp."""
        custom_timestamp = datetime.now(timezone.utc)
        custom_event_id = "custom-event-id"
        
        class TestEvent(BaseUserEvent):
            @property
            def event_type(self) -> str:
                return "test.event"
        
        event = TestEvent(
            user_id=123, 
            event_id=custom_event_id, 
            timestamp=custom_timestamp
        )
        
        assert event.event_id == custom_event_id
        assert event.timestamp == custom_timestamp
    
    def test_base_event_to_dict(self):
        """Test serializing base event to dictionary."""
        class TestEvent(BaseUserEvent):
            def __init__(self, user_id: int, extra_field: str = "test"):
                super().__init__(user_id)
                self.extra_field = extra_field
            
            @property
            def event_type(self) -> str:
                return "test.event"
        
        event = TestEvent(user_id=123, extra_field="test_value")
        result = event.to_dict()
        
        assert result["user_id"] == 123
        assert result["event_type"] == "test.event"
        assert result["aggregate_id"] == "123"
        assert result["extra_field"] == "test_value"
        assert "timestamp" in result
        assert "event_id" in result


class TestUserRegisteredEvent:
    """Test UserRegisteredEvent."""
    
    def test_user_registered_event_creation(self):
        """Test creating user registered event."""
        event = UserRegisteredEvent(
            user_id=123456789,
            first_name="Diana",
            username="diana_bot",
            language_code="es"
        )
        
        assert event.user_id == 123456789
        assert event.first_name == "Diana"
        assert event.username == "diana_bot"
        assert event.language_code == "es"
        assert event.event_type == "user.registered"
    
    def test_user_registered_event_minimal(self):
        """Test creating user registered event with minimal data."""
        event = UserRegisteredEvent(
            user_id=123456789,
            first_name="Diana"
        )
        
        assert event.user_id == 123456789
        assert event.first_name == "Diana"
        assert event.username is None
        assert event.language_code == "es"  # Default
        assert event.event_type == "user.registered"
    
    def test_user_registered_event_invalid_user_id(self):
        """Test user registered event with invalid user ID."""
        with pytest.raises(ValueError, match="user_id must be positive"):
            UserRegisteredEvent(user_id=0, first_name="Diana")
        
        with pytest.raises(ValueError, match="user_id must be positive"):
            UserRegisteredEvent(user_id=-1, first_name="Diana")
    
    def test_user_registered_event_empty_name(self):
        """Test user registered event with empty first name."""
        with pytest.raises(ValueError, match="first_name cannot be empty"):
            UserRegisteredEvent(user_id=123, first_name="")
        
        with pytest.raises(ValueError, match="first_name cannot be empty"):
            UserRegisteredEvent(user_id=123, first_name="   ")
    
    def test_user_registered_event_serialization(self):
        """Test serializing user registered event."""
        event = UserRegisteredEvent(
            user_id=123456789,
            first_name="Diana",
            username="diana_bot"
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "user.registered"
        assert result["user_id"] == 123456789
        assert result["first_name"] == "Diana"
        assert result["username"] == "diana_bot"


class TestUserPreferencesUpdatedEvent:
    """Test UserPreferencesUpdatedEvent."""
    
    def test_preferences_updated_event_creation(self):
        """Test creating preferences updated event."""
        preferences = {"theme": "dark", "notifications": True}
        
        event = UserPreferencesUpdatedEvent(
            user_id=123456789,
            preferences=preferences
        )
        
        assert event.user_id == 123456789
        assert event.preferences == preferences
        assert event.event_type == "user.preferences_updated"
    
    def test_preferences_updated_event_empty_preferences(self):
        """Test preferences updated event with empty preferences."""
        event = UserPreferencesUpdatedEvent(
            user_id=123456789,
            preferences={}
        )
        
        assert event.preferences == {}
        assert event.event_type == "user.preferences_updated"
    
    def test_preferences_updated_event_serialization(self):
        """Test serializing preferences updated event."""
        preferences = {"theme": "dark"}
        
        event = UserPreferencesUpdatedEvent(
            user_id=123456789,
            preferences=preferences
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "user.preferences_updated"
        assert result["user_id"] == 123456789
        assert result["preferences"] == preferences


class TestUserActivityEvent:
    """Test UserActivityEvent."""
    
    def test_activity_event_creation(self):
        """Test creating user activity event."""
        activity_data = {"action": "login", "timestamp": "2024-01-01T10:00:00Z"}
        
        event = UserActivityEvent(
            user_id=123456789,
            activity_type="user_login",
            activity_data=activity_data
        )
        
        assert event.user_id == 123456789
        assert event.activity_type == "user_login"
        assert event.activity_data == activity_data
        assert event.event_type == "user.activity"
    
    def test_activity_event_minimal(self):
        """Test creating activity event with minimal data."""
        event = UserActivityEvent(
            user_id=123456789,
            activity_type="user_active"
        )
        
        assert event.user_id == 123456789
        assert event.activity_type == "user_active"
        assert event.activity_data == {}
        assert event.event_type == "user.activity"
    
    def test_activity_event_serialization(self):
        """Test serializing activity event."""
        activity_data = {"action": "click", "button": "settings"}
        
        event = UserActivityEvent(
            user_id=123456789,
            activity_type="user_interaction",
            activity_data=activity_data
        )
        
        result = event.to_dict()
        
        assert result["event_type"] == "user.activity"
        assert result["user_id"] == 123456789
        assert result["activity_type"] == "user_interaction"
        assert result["activity_data"] == activity_data


class TestEventValidation:
    """Test event validation scenarios."""
    
    def test_event_timestamp_consistency(self):
        """Test that event timestamps are consistent."""
        before = datetime.now(timezone.utc)
        
        event = UserRegisteredEvent(user_id=123, first_name="Diana")
        
        after = datetime.now(timezone.utc)
        
        assert before <= event.timestamp <= after
    
    def test_event_id_uniqueness(self):
        """Test that event IDs are unique."""
        event1 = UserRegisteredEvent(user_id=123, first_name="Diana")
        event2 = UserRegisteredEvent(user_id=123, first_name="Diana")
        
        assert event1.event_id != event2.event_id
    
    def test_aggregate_id_consistency(self):
        """Test that aggregate ID is consistent with user ID."""
        user_id = 123456789
        event = UserRegisteredEvent(user_id=user_id, first_name="Diana")
        
        assert event.aggregate_id == str(user_id)
    
    def test_event_immutability_simulation(self):
        """Test that events maintain their data integrity."""
        original_preferences = {"theme": "dark"}
        
        event = UserPreferencesUpdatedEvent(
            user_id=123,
            preferences=original_preferences
        )
        
        # Modify original dict
        original_preferences["theme"] = "light"
        
        # Event should maintain its original data
        assert event.preferences["theme"] == "dark"