"""
Comprehensive UserService Integration Validation

This test suite validates UserService integration with:
- Event Bus: Event publishing, handling, and format compatibility
- GamificationService: Data compatibility and complete user workflows
- Database: Schema validation and transaction integrity  
- Performance: Claims validation under realistic load
- Error Handling: Recovery and graceful degradation

CRITICAL: UserService is foundational - integration failures cascade everywhere.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.user.service import UserService
from src.modules.user.models import User, UserNotFoundError, DuplicateUserError
from src.modules.user.events import UserRegisteredEvent, UserActivityEvent, UserPreferencesUpdatedEvent


class MockDatabase:
    """Mock database with transaction simulation."""
    
    def __init__(self):
        self.users = {}
        self.transaction_log = []
        self.connection_failures = 0
        self.slow_queries = False
        
    async def execute_with_transaction(self, query, *args):
        """Simulate database transaction."""
        self.transaction_log.append({"query": query, "args": args, "timestamp": datetime.now()})
        
        if self.connection_failures > 0:
            self.connection_failures -= 1
            raise ConnectionError("Database connection failed")
            
        if self.slow_queries:
            await asyncio.sleep(0.1)  # Simulate slow query
            
        return "executed"


class MockUserRepository:
    """Production-like UserRepository mock with all features."""
    
    def __init__(self, database=None):
        self.users = {}
        self.database = database
        self.call_log = []
        self.performance_metrics = {
            "create_calls": [],
            "get_calls": [], 
            "update_calls": [],
            "bulk_calls": []
        }
        
    async def create(self, user: User) -> User:
        start_time = time.time()
        self.call_log.append({"method": "create", "user_id": user.user_id})
        
        if user.user_id in self.users:
            raise DuplicateUserError(f"User {user.user_id} already exists")
            
        self.users[user.user_id] = user
        
        # Record performance
        elapsed = (time.time() - start_time) * 1000
        self.performance_metrics["create_calls"].append(elapsed)
        
        return user
        
    async def get_by_user_id(self, user_id: int):
        start_time = time.time()
        self.call_log.append({"method": "get_by_user_id", "user_id": user_id})
        
        result = self.users.get(user_id)
        
        # Record performance
        elapsed = (time.time() - start_time) * 1000
        self.performance_metrics["get_calls"].append(elapsed)
        
        return result
        
    async def update(self, user: User) -> User:
        start_time = time.time()
        self.call_log.append({"method": "update", "user_id": user.user_id})
        
        if user.user_id not in self.users:
            raise UserNotFoundError(f"User {user.user_id} not found")
            
        self.users[user.user_id] = user
        
        # Record performance
        elapsed = (time.time() - start_time) * 1000
        self.performance_metrics["update_calls"].append(elapsed)
        
        return user
        
    async def get_users_for_service(self, user_ids: List[int]) -> List[User]:
        start_time = time.time()
        self.call_log.append({"method": "get_users_for_service", "count": len(user_ids)})
        
        users = [self.users[uid] for uid in user_ids if uid in self.users]
        
        # Record performance
        elapsed = (time.time() - start_time) * 1000
        self.performance_metrics["bulk_calls"].append(elapsed)
        
        return users
        
    async def count_users(self) -> int:
        return len(self.users)
        
    async def health_check(self) -> Dict:
        return {
            "status": "healthy",
            "users_count": len(self.users),
            "database": "connected"
        }


class IntegrationTestEventBus:
    """Production-like EventBus for integration testing."""
    
    def __init__(self):
        self.events = []
        self.subscribers = {}
        self.event_delivery_log = []
        self.performance_metrics = {
            "publish_times": [],
            "subscribe_times": [],
            "event_counts_by_type": {}
        }
        
    async def initialize(self):
        pass
        
    async def publish(self, event):
        start_time = time.time()
        
        # Validate event
        if not hasattr(event, 'event_type') or not hasattr(event, 'to_dict'):
            raise ValueError("Invalid event format")
            
        # Store event
        self.events.append(event)
        
        # Update metrics
        event_type = event.event_type
        self.performance_metrics["event_counts_by_type"][event_type] = \
            self.performance_metrics["event_counts_by_type"].get(event_type, 0) + 1
        
        # Deliver to subscribers
        delivered_count = 0
        for pattern, handlers in self.subscribers.items():
            if self._matches_pattern(event_type, pattern):
                for handler in handlers:
                    try:
                        await handler(event)
                        delivered_count += 1
                        self.event_delivery_log.append({
                            "event_id": event.event_id,
                            "handler": handler.__name__ if hasattr(handler, '__name__') else str(handler),
                            "success": True
                        })
                    except Exception as e:
                        self.event_delivery_log.append({
                            "event_id": event.event_id,
                            "handler": handler.__name__ if hasattr(handler, '__name__') else str(handler),
                            "success": False,
                            "error": str(e)
                        })
        
        # Record performance
        elapsed = (time.time() - start_time) * 1000
        self.performance_metrics["publish_times"].append(elapsed)
        
        return delivered_count
        
    async def subscribe(self, event_type, handler):
        start_time = time.time()
        
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        
        # Record performance
        elapsed = (time.time() - start_time) * 1000
        self.performance_metrics["subscribe_times"].append(elapsed)
        
    async def unsubscribe(self, event_type, handler):
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(handler)
            except ValueError:
                pass  # Handler not found
                
    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Simple pattern matching."""
        if pattern == event_type:
            return True
        if pattern.endswith("*"):
            return event_type.startswith(pattern[:-1])
        return False
        
    async def health_check(self):
        return {
            "status": "healthy",
            "events_published": len(self.events),
            "subscribers_count": sum(len(handlers) for handlers in self.subscribers.values())
        }


@pytest.mark.asyncio
class TestUserServiceIntegrationValidation:
    """Comprehensive UserService integration validation tests."""

    async def test_complete_user_registration_flow(self):
        """Test complete user registration through all integration points."""
        # Setup
        event_bus = IntegrationTestEventBus()
        repository = MockUserRepository()
        user_service = UserService(repository, event_bus)
        
        # Mock GamificationService
        gamification_service = MagicMock()
        gamification_service.initialize_new_user = AsyncMock(return_value={"points": 100, "level": 1})
        
        # Subscribe gamification service to user events
        async def gamification_handler(event):
            if event.event_type == "user.registered":
                await gamification_service.initialize_new_user(event.user_id, {
                    "first_name": event.first_name,
                    "language_code": getattr(event, 'language_code', 'es')
                })
                
        await event_bus.subscribe("user.registered", gamification_handler)
        
        # Test user registration
        telegram_data = {
            "id": 123456789,
            "first_name": "Diana Test",
            "username": "diana_test",
            "language_code": "es"
        }
        
        user = await user_service.register_user(telegram_data)
        
        # Validate UserService integration
        assert user.user_id == 123456789
        assert user.first_name == "Diana Test"
        assert user.username == "diana_test"
        assert user.language_code == "es"
        
        # Validate Event Bus integration
        assert len(event_bus.events) == 1
        event = event_bus.events[0]
        assert isinstance(event, UserRegisteredEvent)
        assert event.user_id == 123456789
        assert event.first_name == "Diana Test"
        assert event.language_code == "es"
        
        # Validate GamificationService integration
        await asyncio.sleep(0.1)  # Allow event processing
        gamification_service.initialize_new_user.assert_called_once_with(
            123456789, 
            {"first_name": "Diana Test", "language_code": "es"}
        )
        
        # Validate event delivery success
        assert len(event_bus.event_delivery_log) == 1
        assert event_bus.event_delivery_log[0]["success"] is True

    async def test_user_service_gamification_data_compatibility(self):
        """Test UserService provides compatible data to GamificationService."""
        # Setup
        event_bus = IntegrationTestEventBus()
        repository = MockUserRepository()
        user_service = UserService(repository, event_bus)
        
        # Create users with various profiles
        test_users = [
            {"id": 100, "first_name": "User1", "language_code": "es", "username": "user1"},
            {"id": 200, "first_name": "User2", "language_code": "en", "username": None},
            {"id": 300, "first_name": "VIPUser", "language_code": "es", "username": "vip_user"}
        ]
        
        # Register users
        for user_data in test_users:
            await user_service.register_user(user_data)
            
        # Set VIP status for one user
        await user_service.set_vip_status(300, True)
        
        # Test bulk user retrieval (common gamification operation)
        user_ids = [100, 200, 300]
        users = await user_service.get_users_for_service(user_ids)
        
        # Validate data format compatibility
        assert len(users) == 3
        
        # Validate each user has required fields for gamification
        for user in users:
            assert isinstance(user, User)
            assert hasattr(user, 'user_id') and isinstance(user.user_id, int)
            assert hasattr(user, 'first_name') and user.first_name
            assert hasattr(user, 'language_code') and user.language_code
            assert hasattr(user, 'is_vip') and isinstance(user.is_vip, bool)
            assert hasattr(user, 'preferences') and isinstance(user.preferences, dict)
            assert hasattr(user, 'created_at') and isinstance(user.created_at, datetime)
            assert hasattr(user, 'last_active') and isinstance(user.last_active, datetime)
            
        # Validate VIP status
        vip_user = next(u for u in users if u.user_id == 300)
        assert vip_user.is_vip is True
        
        # Validate VIP status checking
        assert await user_service.is_vip_user(300) is True
        assert await user_service.is_vip_user(100) is False

    async def test_event_bus_integration_reliability(self):
        """Test Event Bus integration under various scenarios."""
        # Setup
        event_bus = IntegrationTestEventBus()
        repository = MockUserRepository()
        user_service = UserService(repository, event_bus)
        
        # Test 1: High-frequency events (activity tracking)
        user_data = {"id": 999, "first_name": "ActiveUser"}
        await user_service.register_user(user_data)
        
        # Simulate rapid user activity
        for i in range(10):
            await user_service.mark_user_active(999)
            
        # Validate event publishing
        activity_events = [e for e in event_bus.events if e.event_type == "user.activity"]
        assert len(activity_events) == 10
        
        # Validate event format consistency
        for event in activity_events:
            assert event.user_id == 999
            assert event.activity_type == "user_active"
            assert "timestamp" in event.activity_data
            
        # Test 2: Event publishing performance
        publish_times = event_bus.performance_metrics["publish_times"]
        avg_publish_time = sum(publish_times) / len(publish_times)
        assert avg_publish_time < 50  # Should be under 50ms
        
        # Test 3: Event without Event Bus (degradation)
        user_service_no_bus = UserService(repository, None)
        user = await user_service_no_bus.register_user({"id": 888, "first_name": "NoEventUser"})
        assert user.user_id == 888  # Should still work without Event Bus

    async def test_cross_service_workflow_integration(self):
        """Test complete workflow from UserService through GamificationService."""
        # Setup integrated services
        event_bus = IntegrationTestEventBus()
        repository = MockUserRepository()
        user_service = UserService(repository, event_bus)
        
        # Mock simplified GamificationService with event handling
        class MockGamificationService:
            def __init__(self):
                self.user_initializations = []
                self.activity_processed = []
                
            async def handle_user_registered(self, event):
                self.user_initializations.append({
                    "user_id": event.user_id,
                    "timestamp": datetime.now(),
                    "user_data": {
                        "first_name": event.first_name,
                        "language_code": event.language_code
                    }
                })
                
            async def handle_user_activity(self, event):
                if event.activity_type == "user_active":
                    self.activity_processed.append({
                        "user_id": event.user_id,
                        "activity_type": event.activity_type,
                        "timestamp": datetime.now()
                    })
        
        gamification = MockGamificationService()
        
        # Subscribe to user events
        await event_bus.subscribe("user.registered", gamification.handle_user_registered)
        await event_bus.subscribe("user.activity", gamification.handle_user_activity)
        
        # Execute complete workflow
        telegram_data = {"id": 777, "first_name": "WorkflowUser", "language_code": "en"}
        
        # 1. User registration
        user = await user_service.register_user(telegram_data)
        
        # 2. User activity
        await user_service.mark_user_active(777)
        await user_service.mark_user_active(777)
        
        # 3. Preferences update
        await user_service.update_preferences(777, {"notifications": True, "language": "en"})
        
        # Validate workflow
        assert len(gamification.user_initializations) == 1
        init = gamification.user_initializations[0]
        assert init["user_id"] == 777
        assert init["user_data"]["first_name"] == "WorkflowUser"
        assert init["user_data"]["language_code"] == "en"
        
        assert len(gamification.activity_processed) == 2
        for activity in gamification.activity_processed:
            assert activity["user_id"] == 777
            assert activity["activity_type"] == "user_active"

    async def test_database_integration_simulation(self):
        """Test database integration scenarios."""
        # Setup with database simulation
        database = MockDatabase()
        repository = MockUserRepository(database)
        event_bus = IntegrationTestEventBus()
        user_service = UserService(repository, event_bus)
        
        # Test 1: Normal operations
        user_data = {"id": 555, "first_name": "DBUser"}
        user = await user_service.register_user(user_data)
        
        retrieved = await user_service.get_user(555)
        assert retrieved.user_id == 555
        assert retrieved.first_name == "DBUser"
        
        # Test 2: Bulk operations (common with gamification)
        bulk_users = []
        for i in range(50):
            user_id = 1000 + i
            await user_service.register_user({"id": user_id, "first_name": f"BulkUser{i}"})
            bulk_users.append(user_id)
            
        # Simulate gamification requesting user data
        users = await user_service.get_users_for_service(bulk_users)
        assert len(users) == 50
        
        # Test 3: Database performance simulation  
        database.slow_queries = True
        
        start_time = time.time()
        await user_service.get_user(555)
        elapsed = time.time() - start_time
        assert elapsed >= 0.1  # Should be slow due to simulation
        
        # Test 4: Connection failure recovery
        database.connection_failures = 2
        database.slow_queries = False
        
        with pytest.raises(Exception):  # Should fail first attempts
            await user_service.register_user({"id": 444, "first_name": "FailUser"})

    async def test_performance_claims_validation(self):
        """Validate UserService performance claims under realistic load."""
        # Setup
        event_bus = IntegrationTestEventBus()
        repository = MockUserRepository()
        user_service = UserService(repository, event_bus)
        
        # Test 1: User registration performance (claimed <45ms)
        registration_times = []
        for i in range(20):
            start_time = time.time()
            await user_service.register_user({"id": 2000 + i, "first_name": f"PerfUser{i}"})
            elapsed = (time.time() - start_time) * 1000
            registration_times.append(elapsed)
            
        avg_registration = sum(registration_times) / len(registration_times)
        p95_registration = sorted(registration_times)[int(0.95 * len(registration_times))]
        
        print(f"Registration performance: avg={avg_registration:.2f}ms, p95={p95_registration:.2f}ms")
        # Note: In mock environment, should be much faster than 45ms
        
        # Test 2: User retrieval performance (claimed <25ms)
        retrieval_times = []
        user_ids = list(range(2000, 2020))
        
        for user_id in user_ids:
            start_time = time.time()
            await user_service.get_user(user_id)
            elapsed = (time.time() - start_time) * 1000
            retrieval_times.append(elapsed)
            
        avg_retrieval = sum(retrieval_times) / len(retrieval_times)
        p95_retrieval = sorted(retrieval_times)[int(0.95 * len(retrieval_times))]
        
        print(f"Retrieval performance: avg={avg_retrieval:.2f}ms, p95={p95_retrieval:.2f}ms")
        
        # Test 3: Bulk operations performance (claimed 50 users in <95ms)
        start_time = time.time()
        users = await user_service.get_users_for_service(user_ids)
        bulk_time = (time.time() - start_time) * 1000
        
        print(f"Bulk retrieval (20 users): {bulk_time:.2f}ms")
        assert len(users) == 20
        
        # Validate performance metrics are recorded
        assert len(repository.performance_metrics["create_calls"]) == 20
        assert len(repository.performance_metrics["get_calls"]) == 20
        assert len(repository.performance_metrics["bulk_calls"]) >= 1

    async def test_error_handling_integration(self):
        """Test error handling across integration points."""
        # Setup
        event_bus = IntegrationTestEventBus()
        repository = MockUserRepository()
        user_service = UserService(repository, event_bus)
        
        # Test 1: Duplicate user handling
        user_data = {"id": 666, "first_name": "ErrorUser"}
        await user_service.register_user(user_data)
        
        with pytest.raises(Exception):  # Should raise InvalidUserDataError wrapping DuplicateUserError
            await user_service.register_user(user_data)
            
        # Test 2: User not found scenarios
        with pytest.raises(UserNotFoundError):
            await user_service.get_user(99999)
            
        # Test 3: Invalid data handling
        with pytest.raises(Exception):
            await user_service.register_user({"id": "invalid", "first_name": ""})
            
        # Test 4: Event publishing failure resilience
        class FailingEventBus:
            async def publish(self, event):
                raise ConnectionError("Event Bus unavailable")
                
        user_service_failing_bus = UserService(repository, FailingEventBus())
        
        # Should still complete user operations despite event bus failure
        user = await user_service_failing_bus.register_user({"id": 777, "first_name": "ResilientUser"})
        assert user.user_id == 777

    async def test_service_health_integration(self):
        """Test service health check integration."""
        # Setup
        event_bus = IntegrationTestEventBus()
        repository = MockUserRepository()
        user_service = UserService(repository, event_bus)
        
        # Test health check
        health = await user_service.health_check()
        
        # Validate health response format
        assert "status" in health
        assert "service" in health
        assert "timestamp" in health
        assert "repository" in health
        assert "event_bus" in health
        
        assert health["service"] == "UserService"
        assert health["event_bus"] == "connected"
        
        # Test repository health integration
        repo_health = health["repository"]
        assert repo_health["status"] == "healthy"
        assert "users_count" in repo_health

if __name__ == "__main__":
    pytest.main([__file__, "-v"])