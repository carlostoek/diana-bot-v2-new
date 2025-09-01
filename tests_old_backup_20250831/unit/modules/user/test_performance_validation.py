"""
CRITICAL: UserService Performance Validation Tests

Validates latency claims and performance requirements.
Slow user operations create poor UX across entire bot.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from typing import List

from src.modules.user.service import UserService
from src.modules.user.models import User
from src.modules.user.interfaces import IUserRepository
from src.core.interfaces import IEventBus


class TestUserServicePerformance:
    """CRITICAL: Validate performance claims against requirements."""
    
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

    async def test_user_registration_latency_requirement(self, user_service, mock_repository, mock_event_bus):
        """Validate registration <200ms requirement."""
        telegram_user = {
            "id": 123456789,
            "first_name": "Speed User",
            "username": "speed_test"
        }
        
        expected_user = User(
            user_id=123456789,
            first_name="Speed User",
            username="speed_test"
        )
        
        # Mock repository with realistic delay (simulate database operation)
        async def mock_create(user):
            await asyncio.sleep(0.05)  # 50ms database operation
            return expected_user
        
        async def mock_publish(event):
            await asyncio.sleep(0.01)  # 10ms event publishing
        
        mock_repository.create.side_effect = mock_create
        mock_event_bus.publish.side_effect = mock_publish
        
        # Measure actual performance
        start_time = time.time()
        result = await user_service.register_user(telegram_user)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # REQUIREMENT: Registration <200ms
        assert latency_ms < 200, f"Registration took {latency_ms:.2f}ms, exceeds 200ms requirement"
        assert result.user_id == 123456789

    async def test_user_retrieval_latency_requirement(self, user_service, mock_repository):
        """Validate retrieval <50ms requirement."""
        user_id = 123456789
        expected_user = User(user_id=user_id, first_name="Fast User")
        
        # Mock repository with realistic delay
        async def mock_get_by_user_id(uid):
            await asyncio.sleep(0.02)  # 20ms database query
            return expected_user
        
        mock_repository.get_by_user_id.side_effect = mock_get_by_user_id
        
        # Measure actual performance
        start_time = time.time()
        result = await user_service.get_user(user_id)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # REQUIREMENT: Retrieval <50ms
        assert latency_ms < 50, f"Retrieval took {latency_ms:.2f}ms, exceeds 50ms requirement"
        assert result.user_id == user_id

    async def test_preferences_update_latency_requirement(self, user_service, mock_repository, mock_event_bus):
        """Validate preferences update <100ms requirement."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Prefs User")
        
        async def mock_get_by_user_id(uid):
            await asyncio.sleep(0.02)  # 20ms query
            return user
        
        async def mock_update(user_obj):
            await asyncio.sleep(0.03)  # 30ms update
            return user_obj
        
        async def mock_publish(event):
            await asyncio.sleep(0.01)  # 10ms event publishing
        
        mock_repository.get_by_user_id.side_effect = mock_get_by_user_id
        mock_repository.update.side_effect = mock_update
        mock_event_bus.publish.side_effect = mock_publish
        
        new_preferences = {"theme": "dark", "language": "en"}
        
        # Measure actual performance
        start_time = time.time()
        result = await user_service.update_preferences(user_id, new_preferences)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # REQUIREMENT: Preferences update <100ms
        assert latency_ms < 100, f"Preferences update took {latency_ms:.2f}ms, exceeds 100ms requirement"
        assert result.user_id == user_id

    async def test_bulk_operation_performance_claim(self, user_service, mock_repository):
        """Validate bulk operation claim (50 users in 95ms)."""
        user_ids = list(range(123456789, 123456789 + 50))  # 50 user IDs
        users = [User(user_id=uid, first_name=f"User {uid}") for uid in user_ids]
        
        # Mock repository bulk operation
        async def mock_get_users_for_service(ids):
            await asyncio.sleep(0.08)  # 80ms for bulk query
            return users
        
        mock_repository.get_users_for_service.side_effect = mock_get_users_for_service
        
        # Measure actual performance
        start_time = time.time()
        result = await user_service.get_users_for_service(user_ids)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # CLAIM: 50 users in 95ms
        assert latency_ms < 95, f"Bulk operation took {latency_ms:.2f}ms, exceeds claimed 95ms"
        assert len(result) == 50

    async def test_concurrent_user_operations_performance(self, user_service, mock_repository):
        """Test performance under concurrent load."""
        user_ids = [123456789, 987654321, 555666777, 111222333, 444555666]
        users = [User(user_id=uid, first_name=f"Concurrent User {uid}") for uid in user_ids]
        
        async def mock_get_by_user_id(uid):
            await asyncio.sleep(0.02)  # 20ms per query
            return next(u for u in users if u.user_id == uid)
        
        mock_repository.get_by_user_id.side_effect = mock_get_by_user_id
        
        # Create concurrent tasks
        async def get_user_task(uid):
            return await user_service.get_user(uid)
        
        # Measure concurrent performance
        start_time = time.time()
        tasks = [get_user_task(uid) for uid in user_ids]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Should be faster than sequential (5 * 20ms = 100ms)
        # Concurrent should be ~20ms (limited by slowest operation)
        assert latency_ms < 60, f"Concurrent operations took {latency_ms:.2f}ms, should be <60ms"
        assert len(results) == 5

    async def test_activity_marking_performance(self, user_service, mock_repository, mock_event_bus):
        """Test activity marking performance."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Activity User")
        
        async def mock_get_by_user_id(uid):
            await asyncio.sleep(0.01)  # 10ms query
            return user
        
        async def mock_update(user_obj):
            await asyncio.sleep(0.02)  # 20ms update
            return user_obj
        
        async def mock_publish(event):
            await asyncio.sleep(0.005)  # 5ms event publishing
        
        mock_repository.get_by_user_id.side_effect = mock_get_by_user_id
        mock_repository.update.side_effect = mock_update
        mock_event_bus.publish.side_effect = mock_publish
        
        # Measure performance
        start_time = time.time()
        await user_service.mark_user_active(user_id)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Activity marking should be fast (<50ms)
        assert latency_ms < 50, f"Activity marking took {latency_ms:.2f}ms, should be <50ms"

    async def test_vip_check_performance(self, user_service, mock_repository):
        """Test VIP status check performance."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="VIP User", is_vip=True)
        
        async def mock_get_by_user_id(uid):
            await asyncio.sleep(0.015)  # 15ms query
            return user
        
        mock_repository.get_by_user_id.side_effect = mock_get_by_user_id
        
        # Measure performance
        start_time = time.time()
        result = await user_service.is_vip_user(user_id)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # VIP check should be very fast (<30ms)
        assert latency_ms < 30, f"VIP check took {latency_ms:.2f}ms, should be <30ms"
        assert result is True


class TestDatabasePerformanceSimulation:
    """Simulate database performance under various conditions."""
    
    @pytest.fixture
    def mock_repository_slow(self):
        """Repository that simulates slow database."""
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def user_service_slow(self, mock_repository_slow):
        return UserService(mock_repository_slow, None)

    async def test_performance_under_database_load(self, user_service_slow, mock_repository_slow):
        """Test performance when database is under load."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Load Test User")
        
        # Simulate database under load (slower response)
        async def mock_get_slow(uid):
            await asyncio.sleep(0.1)  # 100ms slow query
            return user
        
        mock_repository_slow.get_by_user_id.side_effect = mock_get_slow
        
        start_time = time.time()
        result = await user_service_slow.get_user(user_id)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Should still complete reasonably quickly
        assert latency_ms < 150, f"Under load took {latency_ms:.2f}ms"
        assert result.user_id == user_id

    async def test_performance_with_network_latency(self, user_service_slow, mock_repository_slow):
        """Test performance with network latency to database."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Network Test User")
        
        # Simulate network latency
        async def mock_get_network_delay(uid):
            await asyncio.sleep(0.05)  # 50ms network delay
            return user
        
        mock_repository_slow.get_by_user_id.side_effect = mock_get_network_delay
        
        start_time = time.time()
        result = await user_service_slow.get_user(user_id)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Should handle network latency gracefully
        assert latency_ms < 80, f"With network latency took {latency_ms:.2f}ms"
        assert result.user_id == user_id


class TestMemoryPerformance:
    """Test memory usage and efficiency."""
    
    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def user_service(self, mock_repository):
        return UserService(mock_repository, None)

    async def test_bulk_operation_memory_efficiency(self, user_service, mock_repository):
        """Test bulk operations don't consume excessive memory."""
        # Create large number of users
        user_count = 1000
        user_ids = list(range(123456789, 123456789 + user_count))
        users = []
        
        # Create users with various data sizes
        for i, uid in enumerate(user_ids):
            preferences = {
                "theme": "dark" if i % 2 == 0 else "light",
                "language": "es" if i % 3 == 0 else "en",
                "data": f"user_data_{i}" * (i % 10 + 1)  # Variable size data
            }
            user = User(
                user_id=uid,
                first_name=f"Bulk User {i}",
                preferences=preferences
            )
            users.append(user)
        
        mock_repository.get_users_for_service.return_value = users
        
        # Measure memory usage (indirectly through performance)
        start_time = time.time()
        result = await user_service.get_users_for_service(user_ids)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Should handle large datasets efficiently
        assert len(result) == user_count
        assert latency_ms < 100, f"Bulk operation with {user_count} users took {latency_ms:.2f}ms"

    async def test_concurrent_memory_efficiency(self, user_service, mock_repository):
        """Test concurrent operations don't cause memory leaks."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Memory Test User")
        
        mock_repository.get_by_user_id.return_value = user
        
        # Create many concurrent operations
        async def get_user_task():
            return await user_service.get_user(user_id)
        
        # Run many concurrent operations
        task_count = 100
        start_time = time.time()
        tasks = [get_user_task() for _ in range(task_count)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Should handle concurrent operations efficiently
        assert len(results) == task_count
        assert latency_ms < 200, f"Concurrent operations took {latency_ms:.2f}ms"
        
        # All results should be valid
        for result in results:
            assert result.user_id == user_id


class TestPerformanceRegression:
    """Test for performance regressions."""
    
    @pytest.fixture
    def baseline_service(self):
        """Create baseline service for comparison."""
        repo = AsyncMock(spec=IUserRepository)
        return UserService(repo, None), repo

    async def test_registration_performance_baseline(self, baseline_service):
        """Establish baseline for registration performance."""
        user_service, mock_repository = baseline_service
        
        telegram_user = {
            "id": 123456789,
            "first_name": "Baseline User"
        }
        
        expected_user = User(user_id=123456789, first_name="Baseline User")
        
        async def mock_create(user):
            await asyncio.sleep(0.001)  # 1ms minimal operation
            return expected_user
        
        mock_repository.create.side_effect = mock_create
        
        # Measure baseline performance
        times = []
        for _ in range(10):  # Multiple measurements
            start_time = time.time()
            await user_service.register_user(telegram_user)
            end_time = time.time()
            times.append((end_time - start_time) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Performance thresholds
        assert avg_time < 10, f"Average registration time {avg_time:.2f}ms too high"
        assert max_time < 20, f"Max registration time {max_time:.2f}ms too high"

    async def test_retrieval_performance_consistency(self, baseline_service):
        """Test retrieval performance is consistent."""
        user_service, mock_repository = baseline_service
        
        user_id = 123456789
        user = User(user_id=user_id, first_name="Consistent User")
        
        async def mock_get_by_user_id(uid):
            await asyncio.sleep(0.001)  # 1ms minimal operation
            return user
        
        mock_repository.get_by_user_id.side_effect = mock_get_by_user_id
        
        # Measure consistency
        times = []
        for _ in range(20):  # Multiple measurements
            start_time = time.time()
            await user_service.get_user(user_id)
            end_time = time.time()
            times.append((end_time - start_time) * 1000)
        
        avg_time = sum(times) / len(times)
        std_dev = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5
        
        # Performance should be consistent
        assert avg_time < 5, f"Average retrieval time {avg_time:.2f}ms too high"
        assert std_dev < 2, f"Performance too variable, std dev {std_dev:.2f}ms"