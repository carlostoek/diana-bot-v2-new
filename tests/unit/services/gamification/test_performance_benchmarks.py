"""
Critical Performance Benchmark Tests

These tests validate that the GamificationService meets strict performance requirements.
Performance failures could lead to:
- User experience degradation (engagement lost)
- System overload under load (service crashes)
- Revenue loss from slow VIP features

Performance Requirements:
- Points Award: <100ms (target ~20ms)
- Achievement Check: <50ms (target ~15ms)
- Leaderboard Generation: <3s (target ~500ms)
- Throughput: 1000+ operations/second
"""

import asyncio
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from core.events import EventBus
from services.gamification.engines.achievement_engine import AchievementEngine
from services.gamification.engines.leaderboard_engine import LeaderboardEngine
from services.gamification.engines.points_engine import PointsEngine
from services.gamification.interfaces import ActionType, LeaderboardType


class TestPointsEnginePerformance:
    """Test Points Engine performance against requirements."""

    @pytest_asyncio.fixture
    async def optimized_points_engine(self):
        """Create optimized PointsEngine for performance testing."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        # Fast mock database with minimal latency
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.rollback_transaction = AsyncMock()

        def fast_query_mock(query, params=None):
            # Simulate fast database response
            if "SELECT" in query:
                return {"balance": 100}
            elif "INSERT" in query:
                return {"transaction_id": "tx_fast"}
            elif "UPDATE" in query:
                return {"rows_affected": 1}
            return {"balance": 150}

        db_client.execute_query = AsyncMock(side_effect=fast_query_mock)

        return PointsEngine(database_client=db_client, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_single_points_award_latency(self, optimized_points_engine):
        """Test single points award meets <100ms requirement (target ~20ms)."""
        user_id = 123

        # Warm up
        await optimized_points_engine.award_points(
            user_id=user_id, action_type=ActionType.DAILY_LOGIN, context={}, points=50
        )

        # Measure actual performance
        latencies = []
        for i in range(50):  # Multiple samples for accuracy
            start_time = time.perf_counter()

            result = await optimized_points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": i},
                points=10,
            )

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            assert result.success, f"Operation {i} failed"

        # Performance analysis
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        max_latency = max(latencies)

        # Requirements validation
        assert (
            avg_latency < 20
        ), f"Average latency {avg_latency:.1f}ms exceeds target 20ms"
        assert (
            p95_latency < 100
        ), f"P95 latency {p95_latency:.1f}ms exceeds requirement 100ms"
        assert max_latency < 200, f"Max latency {max_latency:.1f}ms too high"

        print(
            f"Points Award Performance: avg={avg_latency:.1f}ms, p95={p95_latency:.1f}ms, max={max_latency:.1f}ms"
        )

    @pytest.mark.asyncio
    async def test_points_throughput_requirement(self, optimized_points_engine):
        """Test system meets 1000+ operations/second throughput requirement."""
        num_operations = 1000
        user_base = 100  # Distribute across users

        # Prepare operations
        tasks = []
        for i in range(num_operations):
            user_id = 1000 + (i % user_base)
            task = optimized_points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"throughput_test": True, "op": i},
                points=5,
            )
            tasks.append(task)

        # Measure throughput
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()

        duration = end_time - start_time
        actual_throughput = num_operations / duration

        # Validate results
        successful_ops = sum(1 for r in results if hasattr(r, "success") and r.success)
        success_rate = successful_ops / num_operations

        # Requirements
        assert success_rate >= 0.99, f"Success rate {success_rate:.2%} too low"
        assert (
            actual_throughput >= 1000
        ), f"Throughput {actual_throughput:.0f} ops/sec below requirement"

        print(
            f"Throughput: {actual_throughput:.0f} ops/sec, Success rate: {success_rate:.2%}"
        )

    @pytest.mark.asyncio
    async def test_concurrent_user_performance(self, optimized_points_engine):
        """Test performance doesn't degrade under concurrent user load."""
        num_users = 500
        ops_per_user = 5

        # Create concurrent user operations
        tasks = []
        for user_id in range(2000, 2000 + num_users):
            for op in range(ops_per_user):
                task = optimized_points_engine.award_points(
                    user_id=user_id,
                    action_type=ActionType.COMMUNITY_PARTICIPATION,
                    context={"user_op": op},
                    points=15,
                )
                tasks.append(task)

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()

        total_operations = num_users * ops_per_user
        duration = end_time - start_time
        throughput = total_operations / duration

        successful_ops = sum(1 for r in results if hasattr(r, "success") and r.success)

        # Performance under concurrent load
        assert (
            throughput >= 500
        ), f"Concurrent throughput {throughput:.0f} ops/sec too low"
        assert (
            successful_ops == total_operations
        ), f"Lost operations under concurrent load"
        assert duration < 10, f"Concurrent operations took too long: {duration:.1f}s"


class TestAchievementEnginePerformance:
    """Test Achievement Engine performance requirements."""

    @pytest_asyncio.fixture
    async def achievement_engine(self):
        """Create AchievementEngine for performance testing."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        # Mock fast achievement database
        db_client = Mock()

        def fast_achievement_query(query, params=None):
            # Simulate achievement checks
            if "user_achievements" in query:
                return {
                    "achievements": [
                        {"id": "daily_login_3", "unlocked_at": "2024-08-21"}
                    ]
                }
            elif "user_stats" in query:
                return {"total_points": 500, "days_active": 5, "messages_sent": 50}
            elif "achievement_rules" in query:
                return {
                    "rules": [
                        {
                            "id": "points_100",
                            "condition": "total_points >= 100",
                            "unlocked": True,
                        },
                        {
                            "id": "messages_10",
                            "condition": "messages_sent >= 10",
                            "unlocked": True,
                        },
                    ]
                }
            return {"result": "success"}

        db_client.execute_query = AsyncMock(side_effect=fast_achievement_query)

        return AchievementEngine(database_client=db_client, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_achievement_check_latency(self, achievement_engine):
        """Test achievement check meets <50ms requirement (target ~15ms)."""
        user_id = 456

        # Warm up
        await achievement_engine.check_achievements(
            user_id, ActionType.DAILY_LOGIN, {"points_awarded": 50}
        )

        # Performance measurement
        latencies = []
        for i in range(30):
            start_time = time.perf_counter()

            result = await achievement_engine.check_achievements(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"points_awarded": 10, "iteration": i},
            )

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

        # Performance analysis
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]
        max_latency = max(latencies)

        # Requirements
        assert (
            avg_latency < 15
        ), f"Average achievement check {avg_latency:.1f}ms exceeds target 15ms"
        assert (
            p95_latency < 50
        ), f"P95 achievement check {p95_latency:.1f}ms exceeds requirement 50ms"

        print(
            f"Achievement Check Performance: avg={avg_latency:.1f}ms, p95={p95_latency:.1f}ms"
        )

    @pytest.mark.asyncio
    async def test_bulk_achievement_processing(self, achievement_engine):
        """Test bulk achievement processing efficiency."""
        user_ids = list(range(3000, 3100))  # 100 users

        start_time = time.perf_counter()

        # Process achievements for multiple users
        tasks = []
        for user_id in user_ids:
            task = achievement_engine.check_achievements(
                user_id=user_id,
                action_type=ActionType.TRIVIA_COMPLETED,
                context={"correct": True, "points_awarded": 25},
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()

        duration = end_time - start_time
        users_per_second = len(user_ids) / duration

        # Bulk processing efficiency
        assert (
            users_per_second >= 50
        ), f"Bulk achievement processing too slow: {users_per_second:.1f} users/sec"
        assert duration < 5, f"Bulk processing took too long: {duration:.1f}s"


class TestLeaderboardEnginePerformance:
    """Test Leaderboard Engine performance requirements."""

    @pytest_asyncio.fixture
    async def leaderboard_engine(self):
        """Create LeaderboardEngine for performance testing."""
        event_bus = Mock(spec=EventBus)

        # Mock leaderboard database with realistic data volume
        db_client = Mock()

        def leaderboard_query_mock(query, params=None):
            # Simulate realistic leaderboard queries
            if "weekly_points" in query:
                # Generate mock weekly leaderboard data
                return {
                    "leaderboard": [
                        {"user_id": i, "username": f"user_{i}", "points": 1000 - i}
                        for i in range(1, 101)  # Top 100
                    ]
                }
            elif "total_points" in query:
                return {
                    "leaderboard": [
                        {
                            "user_id": i,
                            "username": f"user_{i}",
                            "total_points": 5000 - i * 10,
                        }
                        for i in range(1, 101)
                    ]
                }
            elif "user_rank" in query:
                user_id = params.get("user_id", 1)
                return {"rank": user_id, "total_users": 10000}
            return {"result": "success"}

        db_client.execute_query = AsyncMock(side_effect=leaderboard_query_mock)

        return LeaderboardEngine(database_client=db_client, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_leaderboard_generation_latency(self, leaderboard_engine):
        """Test leaderboard generation meets <3s requirement (target ~500ms)."""

        # Test different leaderboard types
        leaderboard_types = [
            LeaderboardType.WEEKLY_POINTS,
            LeaderboardType.TOTAL_POINTS,
            LeaderboardType.CURRENT_STREAK,
            LeaderboardType.ACHIEVEMENTS_COUNT,
        ]

        for leaderboard_type in leaderboard_types:
            start_time = time.perf_counter()

            result = await leaderboard_engine.get_leaderboard(
                leaderboard_type=leaderboard_type, limit=100, offset=0
            )

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            # Requirements per leaderboard type
            assert (
                latency_ms < 500
            ), f"{leaderboard_type.value} generation {latency_ms:.1f}ms exceeds target 500ms"
            assert (
                latency_ms < 3000
            ), f"{leaderboard_type.value} generation {latency_ms:.1f}ms exceeds requirement 3s"

            print(f"{leaderboard_type.value} generation: {latency_ms:.1f}ms")

    @pytest.mark.asyncio
    async def test_concurrent_leaderboard_requests(self, leaderboard_engine):
        """Test leaderboard performance under concurrent requests."""
        num_requests = 20

        # Create concurrent leaderboard requests
        tasks = []
        for i in range(num_requests):
            task = leaderboard_engine.get_leaderboard(
                leaderboard_type=LeaderboardType.WEEKLY_POINTS,
                limit=50,
                offset=i * 50,  # Different offsets
            )
            tasks.append(task)

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()

        duration = end_time - start_time
        requests_per_second = num_requests / duration

        # Concurrent performance
        successful_requests = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_requests == num_requests, "Some leaderboard requests failed"
        assert (
            requests_per_second >= 10
        ), f"Concurrent leaderboard throughput too low: {requests_per_second:.1f} req/sec"

    @pytest.mark.asyncio
    async def test_user_rank_lookup_performance(self, leaderboard_engine):
        """Test individual user rank lookup performance."""
        user_ids = list(range(4000, 4100))  # 100 users

        start_time = time.perf_counter()

        # Concurrent rank lookups
        tasks = []
        for user_id in user_ids:
            task = leaderboard_engine.get_user_rank(
                user_id=user_id, leaderboard_type=LeaderboardType.TOTAL_POINTS
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()

        duration = end_time - start_time
        lookups_per_second = len(user_ids) / duration

        # Rank lookup performance
        successful_lookups = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_lookups == len(user_ids), "Some rank lookups failed"
        assert (
            lookups_per_second >= 100
        ), f"Rank lookup throughput too low: {lookups_per_second:.1f} lookups/sec"


class TestIntegratedSystemPerformance:
    """Test full system performance under realistic load."""

    @pytest_asyncio.fixture
    async def full_gamification_system(self):
        """Create complete gamification system for integration testing."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        # Shared fast database mock
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.execute_query = AsyncMock(return_value={"result": "success"})

        points_engine = PointsEngine(database_client=db_client, event_bus=event_bus)
        achievement_engine = AchievementEngine(
            database_client=db_client, event_bus=event_bus
        )
        leaderboard_engine = LeaderboardEngine(
            database_client=db_client, event_bus=event_bus
        )

        return {
            "points": points_engine,
            "achievements": achievement_engine,
            "leaderboards": leaderboard_engine,
        }

    @pytest.mark.asyncio
    async def test_end_to_end_user_action_performance(self, full_gamification_system):
        """Test complete user action processing performance."""
        user_id = 5000
        engines = full_gamification_system

        # Simulate complete user action: award points + check achievements + update leaderboard
        start_time = time.perf_counter()

        # Award points
        points_result = await engines["points"].award_points(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"correct": True},
            points=75,
        )

        # Check achievements
        achievement_result = await engines["achievements"].check_achievements(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"points_awarded": 75},
        )

        # Update leaderboard position (simulated)
        rank_result = await engines["leaderboards"].get_user_rank(
            user_id=user_id, leaderboard_type=LeaderboardType.TOTAL_POINTS
        )

        end_time = time.perf_counter()
        total_latency_ms = (end_time - start_time) * 1000

        # End-to-end performance requirement
        assert (
            total_latency_ms < 200
        ), f"End-to-end processing {total_latency_ms:.1f}ms exceeds 200ms target"

        print(f"End-to-end user action: {total_latency_ms:.1f}ms")

    @pytest.mark.asyncio
    async def test_system_performance_under_realistic_load(
        self, full_gamification_system
    ):
        """Test system performance under realistic user load."""
        engines = full_gamification_system

        # Simulate realistic user activity patterns
        user_base = 200
        actions_per_user = 3

        total_operations = user_base * actions_per_user

        start_time = time.perf_counter()

        # Create realistic mixed workload
        tasks = []
        for user_id in range(6000, 6000 + user_base):
            # Points award
            task1 = engines["points"].award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={},
                points=10,
            )
            tasks.append(task1)

            # Achievement check
            task2 = engines["achievements"].check_achievements(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"points_awarded": 10},
            )
            tasks.append(task2)

            # Periodic leaderboard lookup (every 10th user)
            if user_id % 10 == 0:
                task3 = engines["leaderboards"].get_user_rank(
                    user_id=user_id, leaderboard_type=LeaderboardType.WEEKLY_POINTS
                )
                tasks.append(task3)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()

        duration = end_time - start_time
        operations_per_second = len(tasks) / duration

        # System performance under realistic load
        successful_ops = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = successful_ops / len(tasks)

        assert (
            success_rate >= 0.99
        ), f"System success rate {success_rate:.2%} too low under load"
        assert (
            operations_per_second >= 200
        ), f"System throughput {operations_per_second:.0f} ops/sec too low"
        assert duration < 15, f"Realistic load test took too long: {duration:.1f}s"

        print(
            f"Realistic Load Test: {operations_per_second:.0f} ops/sec, {success_rate:.2%} success rate"
        )
