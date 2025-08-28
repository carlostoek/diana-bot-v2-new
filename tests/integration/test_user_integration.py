"""Integration tests for UserService with Event Bus."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from src.modules.user.service import UserService
from src.modules.user.repository import UserRepository
from src.modules.user.models import User
from src.modules.user.events import UserRegisteredEvent, UserActivityEvent
from src.core.event_bus import EventBus
from src.core.events import BaseEvent


class MockEventBus:
    """Mock event bus for integration testing."""
    
    def __init__(self):
        self.published_events = []
        self.subscribers = {}
    
    async def publish(self, event):
        """Mock publish method."""
        self.published_events.append(event)
    
    async def subscribe(self, event_type, handler):
        """Mock subscribe method."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def get_published_events(self, event_type=None):
        """Get published events, optionally filtered by type."""
        if event_type:
            return [e for e in self.published_events if e.event_type == event_type]
        return self.published_events.copy()


class MockRepository:
    """Mock repository for integration testing."""
    
    def __init__(self):
        self.users = {}
        self.user_count = 0
    
    async def create(self, user: User) -> User:
        """Mock create method."""
        if user.user_id in self.users:
            from src.modules.user.models import DuplicateUserError
            raise DuplicateUserError(f"User {user.user_id} already exists")
        
        self.users[user.user_id] = user
        self.user_count += 1
        return user
    
    async def get_by_user_id(self, user_id: int) -> User:
        """Mock get by user ID."""
        return self.users.get(user_id)
    
    async def update(self, user: User) -> User:
        """Mock update method."""
        if user.user_id not in self.users:
            from src.modules.user.models import UserNotFoundError
            raise UserNotFoundError(f"User {user.user_id} not found")
        
        self.users[user.user_id] = user
        return user
    
    async def get_users_for_service(self, user_ids):
        """Mock get users for service."""
        return [self.users[uid] for uid in user_ids if uid in self.users]
    
    async def count_users(self) -> int:
        """Mock count users."""
        return len(self.users)
    
    async def health_check(self):
        """Mock health check."""
        return {
            "status": "healthy",
            "users_count": len(self.users)
        }


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    return MockEventBus()


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    return MockRepository()


@pytest.fixture
def user_service(mock_repository, mock_event_bus):
    """Create UserService with mocked dependencies."""
    return UserService(mock_repository, mock_event_bus)


class TestUserServiceIntegration:
    """Integration tests for UserService."""
    
    @pytest.mark.asyncio
    async def test_user_registration_flow(self, user_service, mock_event_bus):
        """Test complete user registration flow with event publishing."""
        telegram_data = {
            "id": 123456789,
            "first_name": "Diana",
            "username": "diana_bot",
            "language_code": "es"
        }
        
        # Register user
        user = await user_service.register_user(telegram_data)
        
        # Verify user was created
        assert user.user_id == 123456789
        assert user.first_name == "Diana"
        assert user.username == "diana_bot"
        
        # Verify event was published
        events = mock_event_bus.get_published_events("user.registered")
        assert len(events) == 1
        
        event = events[0]
        assert isinstance(event, UserRegisteredEvent)
        assert event.user_id == 123456789
        assert event.first_name == "Diana"
    
    @pytest.mark.asyncio
    async def test_user_activity_tracking_flow(self, user_service, mock_event_bus, mock_repository):
        """Test user activity tracking with event publishing."""
        # First register a user
        user = User(user_id=123, first_name="Diana")
        await mock_repository.create(user)
        
        # Mark user as active
        await user_service.mark_user_active(123)
        
        # Verify activity event was published
        events = mock_event_bus.get_published_events("user.activity")
        assert len(events) == 1
        
        event = events[0]
        assert isinstance(event, UserActivityEvent)
        assert event.user_id == 123
        assert event.activity_type == "user_active"
    
    @pytest.mark.asyncio
    async def test_preferences_update_flow(self, user_service, mock_event_bus, mock_repository):
        """Test preferences update with event publishing."""
        # Register user
        user = User(user_id=123, first_name="Diana")
        await mock_repository.create(user)
        
        # Update preferences
        preferences = {"theme": "dark", "notifications": True}
        updated_user = await user_service.update_preferences(123, preferences)
        
        # Verify preferences were updated
        assert updated_user.preferences == preferences
        
        # Verify event was published
        events = mock_event_bus.get_published_events("user.preferences_updated")
        assert len(events) == 1
        
        event = events[0]
        assert event.user_id == 123
        assert event.preferences == preferences
    
    @pytest.mark.asyncio
    async def test_vip_status_change_flow(self, user_service, mock_event_bus, mock_repository):
        """Test VIP status change with event publishing."""
        # Register user
        user = User(user_id=123, first_name="Diana", is_vip=False)
        await mock_repository.create(user)
        
        # Set VIP status
        updated_user = await user_service.set_vip_status(123, True)
        
        # Verify VIP status was updated
        assert updated_user.is_vip is True
        
        # Verify activity event was published
        events = mock_event_bus.get_published_events("user.activity")
        assert len(events) == 1
        
        event = events[0]
        assert event.activity_type == "vip_status_changed"
        assert event.activity_data["old_status"] is False
        assert event.activity_data["new_status"] is True
    
    @pytest.mark.asyncio
    async def test_service_integration_flow(self, user_service, mock_repository):
        """Test service integration scenarios."""
        # Register multiple users
        users_data = [
            {"id": 123, "first_name": "User1"},
            {"id": 456, "first_name": "User2"}, 
            {"id": 789, "first_name": "User3"}
        ]
        
        for data in users_data:
            await user_service.register_user(data)
        
        # Test getting users for service
        users = await user_service.get_users_for_service([123, 456])
        assert len(users) == 2
        assert users[0].user_id in [123, 456]
        assert users[1].user_id in [123, 456]
        
        # Test user count
        count = await user_service.get_user_count()
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_bulk_operations_flow(self, user_service, mock_repository):
        """Test bulk operations."""
        # Register multiple users
        for i in range(1, 6):  # Users 1-5
            user = User(user_id=i, first_name=f"User{i}")
            await mock_repository.create(user)
        
        # Bulk mark users active
        result = await user_service.bulk_mark_users_active([1, 2, 3, 6])  # 6 doesn't exist
        assert result == 3  # Only 3 users were successfully updated
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, user_service, mock_event_bus):
        """Test error handling across the integration."""
        # Try to register user with missing data
        with pytest.raises(Exception):  # Should raise InvalidUserDataError
            await user_service.register_user({"first_name": "Diana"})  # Missing ID
        
        # Try to get non-existent user
        with pytest.raises(Exception):  # Should raise UserNotFoundError
            await user_service.get_user(999999)
        
        # Verify no events were published for failed operations
        events = mock_event_bus.get_published_events()
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, user_service):
        """Test health check across all components."""
        health = await user_service.health_check()
        
        assert health["status"] == "healthy"
        assert health["service"] == "UserService"
        assert health["repository"]["status"] == "healthy"
        assert "timestamp" in health


class TestEventBusIntegration:
    """Test integration with actual Event Bus patterns."""
    
    @pytest.mark.asyncio
    async def test_event_publishing_patterns(self, mock_repository):
        """Test event publishing follows expected patterns."""
        event_bus = MockEventBus()
        service = UserService(mock_repository, event_bus)
        
        # Register user
        telegram_data = {"id": 123, "first_name": "Diana"}
        await service.register_user(telegram_data)
        
        # Get published event
        events = event_bus.get_published_events("user.registered")
        assert len(events) == 1
        
        event = events[0]
        assert hasattr(event, 'event_id')
        assert hasattr(event, 'timestamp')
        assert hasattr(event, 'aggregate_id')
        assert event.aggregate_id == "123"
    
    @pytest.mark.asyncio
    async def test_event_serialization_integration(self, mock_repository):
        """Test event serialization works with service integration."""
        event_bus = MockEventBus()
        service = UserService(mock_repository, event_bus)
        
        # Register user
        await service.register_user({"id": 123, "first_name": "Diana"})
        
        # Get event and serialize it
        event = event_bus.get_published_events("user.registered")[0]
        serialized = event.to_dict()
        
        # Verify serialization includes all required fields
        assert "event_id" in serialized
        assert "event_type" in serialized
        assert "timestamp" in serialized
        assert "user_id" in serialized
        assert "first_name" in serialized
        assert serialized["event_type"] == "user.registered"
    
    @pytest.mark.asyncio
    async def test_service_without_event_bus(self, mock_repository):
        """Test service functionality without event bus."""
        service = UserService(mock_repository, None)
        
        # Should work without event bus
        user = await service.register_user({"id": 123, "first_name": "Diana"})
        assert user.user_id == 123
        
        # Should not fail on activity tracking
        await service.mark_user_active(123)
        
        # Should not fail on preferences update
        await service.update_preferences(123, {"theme": "dark"})


class TestPerformanceIntegration:
    """Test performance characteristics of the integration."""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_registration(self, mock_repository):
        """Test concurrent user registrations."""
        event_bus = MockEventBus()
        service = UserService(mock_repository, event_bus)
        
        # Create concurrent registration tasks
        tasks = []
        for i in range(10):
            task = service.register_user({
                "id": i + 1,
                "first_name": f"User{i+1}"
            })
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        assert len(results) == 10
        assert all(isinstance(r, User) for r in results)
        
        # Verify events were published
        events = event_bus.get_published_events("user.registered")
        assert len(events) == 10
    
    @pytest.mark.asyncio
    async def test_bulk_service_operations(self, mock_repository):
        """Test bulk service operations performance."""
        event_bus = MockEventBus()
        service = UserService(mock_repository, event_bus)
        
        # Register many users
        for i in range(100):
            user = User(user_id=i + 1, first_name=f"User{i+1}")
            await mock_repository.create(user)
        
        # Test bulk retrieval
        user_ids = list(range(1, 51))  # First 50 users
        users = await service.get_users_for_service(user_ids)
        assert len(users) == 50
        
        # Test bulk activity marking
        result = await service.bulk_mark_users_active(user_ids)
        assert result == 50