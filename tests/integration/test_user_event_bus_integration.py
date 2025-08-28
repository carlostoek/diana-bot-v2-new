"""Quick Event Bus integration validation for UserService."""

import pytest
from unittest.mock import AsyncMock

from src.modules.user.service import UserService
from src.modules.user.models import User
from src.modules.user.events import UserRegisteredEvent, UserActivityEvent


class MockEventBus:
    """Simple mock event bus for testing."""
    
    def __init__(self):
        self.events = []
    
    async def publish(self, event):
        """Mock publish - just store events."""
        self.events.append(event)
    
    def get_events(self, event_type=None):
        """Get stored events."""
        if event_type:
            return [e for e in self.events if e.event_type == event_type]
        return self.events


class MockRepository:
    """Simple mock repository for testing."""
    
    def __init__(self):
        self.users = {}
    
    async def create(self, user):
        self.users[user.user_id] = user
        return user
    
    async def get_by_user_id(self, user_id):
        return self.users.get(user_id)
    
    async def update(self, user):
        self.users[user.user_id] = user
        return user


@pytest.mark.asyncio
async def test_user_registration_event_integration():
    """Test user registration publishes correct event."""
    event_bus = MockEventBus()
    repository = MockRepository()
    service = UserService(repository, event_bus)
    
    # Register user
    telegram_data = {
        "id": 123456789,
        "first_name": "Diana",
        "username": "diana_bot"
    }
    
    user = await service.register_user(telegram_data)
    
    # Verify user was created
    assert user.user_id == 123456789
    assert user.first_name == "Diana"
    
    # Verify event was published
    events = event_bus.get_events("user.registered")
    assert len(events) == 1
    
    event = events[0]
    assert isinstance(event, UserRegisteredEvent)
    assert event.user_id == 123456789
    assert event.first_name == "Diana"


@pytest.mark.asyncio
async def test_user_activity_event_integration():
    """Test user activity tracking publishes correct event."""
    event_bus = MockEventBus()
    repository = MockRepository()
    service = UserService(repository, event_bus)
    
    # Create user first
    user = User(user_id=123, first_name="Diana")
    await repository.create(user)
    
    # Mark user active
    await service.mark_user_active(123)
    
    # Verify activity event was published
    events = event_bus.get_events("user.activity")
    assert len(events) == 1
    
    event = events[0]
    assert isinstance(event, UserActivityEvent)
    assert event.user_id == 123
    assert event.activity_type == "user_active"


@pytest.mark.asyncio
async def test_service_without_event_bus():
    """Test service works without event bus."""
    repository = MockRepository()
    service = UserService(repository, None)  # No event bus
    
    # Should still work
    telegram_data = {"id": 123, "first_name": "Diana"}
    user = await service.register_user(telegram_data)
    
    assert user.user_id == 123
    assert user.first_name == "Diana"


if __name__ == "__main__":
    pytest.main([__file__])