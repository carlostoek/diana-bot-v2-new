"""Performance tests for UserService - Validate <200ms targets."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock

from src.modules.user.service import UserService
from src.modules.user.models import User


class PerformanceTracker:
    """Helper to track operation performance."""
    
    def __init__(self):
        self.measurements = []
    
    async def measure_operation(self, operation, *args, **kwargs):
        """Measure operation performance."""
        start_time = time.time()
        result = await operation(*args, **kwargs)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        self.measurements.append({
            'operation': operation.__name__,
            'duration_ms': duration_ms,
            'success': True
        })
        return result, duration_ms
    
    def get_average_duration(self, operation_name=None):
        """Get average duration for operations."""
        measurements = self.measurements
        if operation_name:
            measurements = [m for m in measurements if m['operation'] == operation_name]
        
        if not measurements:
            return 0
        
        return sum(m['duration_ms'] for m in measurements) / len(measurements)


class MockRepository:
    """High-performance mock repository."""
    
    def __init__(self, simulated_latency_ms=0):
        self.users = {}
        self.latency = simulated_latency_ms / 1000.0  # Convert to seconds
    
    async def _simulate_latency(self):
        """Simulate database latency."""
        if self.latency > 0:
            import asyncio
            await asyncio.sleep(self.latency)
    
    async def create(self, user):
        await self._simulate_latency()
        self.users[user.user_id] = user
        return user
    
    async def get_by_user_id(self, user_id):
        await self._simulate_latency()
        return self.users.get(user_id)
    
    async def update(self, user):
        await self._simulate_latency()
        self.users[user.user_id] = user
        return user
    
    async def get_users_for_service(self, user_ids):
        await self._simulate_latency()
        return [self.users[uid] for uid in user_ids if uid in self.users]
    
    async def count_users(self):
        await self._simulate_latency()
        return len(self.users)


@pytest.mark.asyncio
async def test_user_registration_performance():
    """Test user registration meets <200ms target."""
    repository = MockRepository(simulated_latency_ms=30)  # Realistic DB latency
    service = UserService(repository, None)
    tracker = PerformanceTracker()
    
    # Test single registration
    telegram_data = {"id": 123, "first_name": "Diana"}
    user, duration = await tracker.measure_operation(
        service.register_user, telegram_data
    )
    
    assert duration < 200, f"Registration took {duration}ms, expected <200ms"
    assert user.user_id == 123


@pytest.mark.asyncio
async def test_user_retrieval_performance():
    """Test user retrieval meets <50ms target."""
    repository = MockRepository(simulated_latency_ms=20)
    service = UserService(repository, None)
    tracker = PerformanceTracker()
    
    # Pre-populate user
    user = User(user_id=123, first_name="Diana")
    await repository.create(user)
    
    # Test retrieval
    retrieved_user, duration = await tracker.measure_operation(
        service.get_user, 123
    )
    
    assert duration < 50, f"Retrieval took {duration}ms, expected <50ms"
    assert retrieved_user.user_id == 123


@pytest.mark.asyncio
async def test_preferences_update_performance():
    """Test preferences update meets <100ms target."""
    repository = MockRepository(simulated_latency_ms=25)
    service = UserService(repository, None)
    tracker = PerformanceTracker()
    
    # Pre-populate user
    await service.register_user({"id": 123, "first_name": "Diana"})
    
    # Test preferences update
    preferences = {"theme": "dark", "notifications": True}
    updated_user, duration = await tracker.measure_operation(
        service.update_preferences, 123, preferences
    )
    
    assert duration < 100, f"Preferences update took {duration}ms, expected <100ms"
    assert updated_user.preferences == preferences


@pytest.mark.asyncio
async def test_bulk_operations_performance():
    """Test bulk operations performance."""
    repository = MockRepository(simulated_latency_ms=20)
    service = UserService(repository, None)
    tracker = PerformanceTracker()
    
    # Pre-populate users
    user_ids = []
    for i in range(50):  # 50 users
        user_id = 1000 + i
        await service.register_user({"id": user_id, "first_name": f"User{i}"})
        user_ids.append(user_id)
    
    # Test bulk retrieval
    users, duration = await tracker.measure_operation(
        service.get_users_for_service, user_ids
    )
    
    assert duration < 200, f"Bulk retrieval took {duration}ms, expected <200ms"
    assert len(users) == 50


@pytest.mark.asyncio
async def test_concurrent_operations_performance():
    """Test concurrent operations don't degrade performance significantly."""
    import asyncio
    
    repository = MockRepository(simulated_latency_ms=15)
    service = UserService(repository, None)
    
    # Test concurrent registrations
    tasks = []
    start_time = time.time()
    
    for i in range(10):
        task = service.register_user({
            "id": 2000 + i,
            "first_name": f"ConcurrentUser{i}"
        })
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    total_duration = (end_time - start_time) * 1000
    avg_per_operation = total_duration / 10
    
    assert avg_per_operation < 200, f"Avg concurrent operation took {avg_per_operation}ms"
    assert len(results) == 10
    assert all(user.user_id >= 2000 for user in results)


@pytest.mark.asyncio
async def test_database_query_performance():
    """Test database query operations meet targets."""
    repository = MockRepository(simulated_latency_ms=30)
    service = UserService(repository, None)
    tracker = PerformanceTracker()
    
    # Pre-populate some users
    for i in range(10):
        await service.register_user({"id": 3000 + i, "first_name": f"QueryUser{i}"})
    
    # Test user count query
    count, duration = await tracker.measure_operation(service.get_user_count)
    assert duration < 50, f"Count query took {duration}ms, expected <50ms"
    assert count == 10
    
    # Test VIP status check
    is_vip, duration = await tracker.measure_operation(service.is_vip_user, 3000)
    assert duration < 50, f"VIP check took {duration}ms, expected <50ms"


@pytest.mark.asyncio
async def test_activity_tracking_performance():
    """Test activity tracking performance."""
    repository = MockRepository(simulated_latency_ms=25)
    service = UserService(repository, None)
    tracker = PerformanceTracker()
    
    # Pre-populate user
    await service.register_user({"id": 4000, "first_name": "ActiveUser"})
    
    # Test activity tracking
    _, duration = await tracker.measure_operation(service.mark_user_active, 4000)
    assert duration < 100, f"Activity tracking took {duration}ms, expected <100ms"


@pytest.mark.asyncio  
async def test_service_performance_under_load():
    """Test service performance under realistic load."""
    repository = MockRepository(simulated_latency_ms=20)
    service = UserService(repository, None)
    
    # Simulate realistic mixed workload
    start_time = time.time()
    
    # Register 20 users
    registration_tasks = []
    for i in range(20):
        task = service.register_user({
            "id": 5000 + i,
            "first_name": f"LoadUser{i}"
        })
        registration_tasks.append(task)
    
    await asyncio.gather(*registration_tasks)
    
    # Mixed operations
    operations = []
    
    # 10 user retrievals
    for i in range(10):
        operations.append(service.get_user(5000 + i))
    
    # 5 preference updates
    for i in range(5):
        operations.append(service.update_preferences(
            5000 + i, 
            {"last_action": f"test_{i}"}
        ))
    
    # 3 VIP status checks
    for i in range(3):
        operations.append(service.is_vip_user(5000 + i))
    
    # Execute all operations concurrently
    results = await asyncio.gather(*operations)
    end_time = time.time()
    
    total_duration = (end_time - start_time) * 1000
    
    # Should handle realistic load efficiently
    assert total_duration < 2000, f"Load test took {total_duration}ms, expected <2000ms"
    assert len(results) == 18  # 10 + 5 + 3


if __name__ == "__main__":
    pytest.main([__file__])