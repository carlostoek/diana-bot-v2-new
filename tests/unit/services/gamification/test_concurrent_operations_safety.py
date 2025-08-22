"""
Critical Concurrent Operations Safety Tests

These tests ensure the system maintains data integrity under high concurrent load.
Race conditions could lead to:
- Duplicate point awards (economic disaster)
- Lost transactions (user trust destroyed)
- Corrupted balances (system credibility lost)

ZERO TOLERANCE for race conditions or concurrency bugs.
"""

import asyncio
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from core.events import EventBus
from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine import PointsEngine
from services.gamification.interfaces import ActionType, PointsAwardResult


class TestConcurrentPointsOperations:
    """Test concurrent points operations maintain mathematical integrity."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine with thread-safe mocked dependencies."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        # Thread-safe mock database
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.rollback_transaction = AsyncMock()

        # Mock balance tracking with thread safety
        self.balance_store = {}
        self.transaction_store = []
        self.lock = threading.Lock()

        def mock_execute_query(query, params=None):
            user_id = params.get("user_id") if params else 123

            with self.lock:
                if "SELECT" in query and "balance" in query:
                    return {"balance": self.balance_store.get(user_id, 0)}
                elif "INSERT" in query and "transactions" in query:
                    tx_id = f"tx_{len(self.transaction_store)}"
                    self.transaction_store.append(
                        {
                            "id": tx_id,
                            "user_id": user_id,
                            "points": params.get("points", 0),
                        }
                    )
                    return {"transaction_id": tx_id}
                elif "UPDATE" in query and "balance" in query:
                    points = params.get("points", 0)
                    current = self.balance_store.get(user_id, 0)
                    self.balance_store[user_id] = current + points
                    return {"rows_affected": 1}
                else:
                    return {"balance": self.balance_store.get(user_id, 0)}

        db_client.execute_query = AsyncMock(side_effect=mock_execute_query)

        return PointsEngine(database_client=db_client, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_concurrent_points_award_no_race_condition(self, points_engine):
        """Test that concurrent point awards don't create race conditions."""
        user_id = 123
        num_operations = 20
        points_per_operation = 10

        # Reset balance
        self.balance_store[user_id] = 0

        # Create concurrent award operations
        tasks = []
        for i in range(num_operations):
            task = points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": i},
                points=points_per_operation,
            )
            tasks.append(task)

        # Execute all operations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should succeed
        successful_results = [
            r for r in results if isinstance(r, PointsAwardResult) and r.success
        ]
        assert (
            len(successful_results) == num_operations
        ), "Some operations failed unexpectedly"

        # Final balance should equal sum of all transactions
        expected_balance = num_operations * points_per_operation
        actual_balance = self.balance_store[user_id]
        assert (
            actual_balance == expected_balance
        ), f"Balance integrity violated: expected {expected_balance}, got {actual_balance}"

        # Transaction count should match operations
        user_transactions = [
            tx for tx in self.transaction_store if tx["user_id"] == user_id
        ]
        assert (
            len(user_transactions) == num_operations
        ), "Transaction count doesn't match operations"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations_integrity(self, points_engine):
        """Test concurrent mix of awards and deductions maintain integrity."""
        user_id = 456

        # Start with initial balance
        self.balance_store[user_id] = 1000

        # Mix of operations
        operations = [
            (ActionType.DAILY_LOGIN, 100),  # +100
            (ActionType.ADMIN_ADJUSTMENT, -50),  # -50
            (ActionType.MESSAGE_SENT, 25),  # +25
            (ActionType.ADMIN_ADJUSTMENT, -30),  # -30
            (ActionType.TRIVIA_COMPLETED, 75),  # +75
            (ActionType.ADMIN_ADJUSTMENT, -20),  # -20
        ]

        tasks = []
        for i, (action_type, points) in enumerate(operations):
            task = points_engine.award_points(
                user_id=user_id,
                action_type=action_type,
                context={"operation_id": i},
                points=points,
            )
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        successful_results = [
            r for r in results if isinstance(r, PointsAwardResult) and r.success
        ]
        assert len(successful_results) == len(operations)

        # Calculate expected balance
        expected_balance = 1000 + sum(points for _, points in operations)
        actual_balance = self.balance_store[user_id]
        assert (
            actual_balance == expected_balance
        ), f"Mixed operations integrity violated: expected {expected_balance}, got {actual_balance}"

    @pytest.mark.asyncio
    async def test_concurrent_users_isolation(self, points_engine):
        """Test that concurrent operations on different users don't interfere."""
        users = [100, 101, 102, 103, 104]
        points_per_user = 50

        # Initialize balances
        for user_id in users:
            self.balance_store[user_id] = 0

        # Create operations for all users
        tasks = []
        for user_id in users:
            for i in range(5):  # 5 operations per user
                task = points_engine.award_points(
                    user_id=user_id,
                    action_type=ActionType.MESSAGE_SENT,
                    context={"user": user_id, "op": i},
                    points=points_per_user,
                )
                tasks.append(task)

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        successful_results = [
            r for r in results if isinstance(r, PointsAwardResult) and r.success
        ]
        assert len(successful_results) == len(users) * 5

        # Each user should have correct balance
        for user_id in users:
            expected_balance = 5 * points_per_user
            actual_balance = self.balance_store[user_id]
            assert (
                actual_balance == expected_balance
            ), f"User {user_id} balance incorrect: expected {expected_balance}, got {actual_balance}"


class TestAntiAbuseUnderConcurrency:
    """Test anti-abuse system integrity under concurrent load."""

    @pytest_asyncio.fixture
    async def anti_abuse_validator(self):
        """Create AntiAbuseValidator for concurrency testing."""
        return AntiAbuseValidator()

    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_enforcement(self, anti_abuse_validator):
        """Test rate limiting works correctly under concurrent requests."""
        user_id = 789
        action_type = ActionType.MESSAGE_SENT

        # Create many concurrent validation requests
        tasks = []
        for i in range(150):  # Exceed MESSAGE_SENT limit (100/hour)
            context = {
                "message": f"concurrent_msg_{i}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            task = anti_abuse_validator.validate_action(
                user_id=user_id, action_type=action_type, context=context
            )
            tasks.append(task)

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count valid vs blocked requests
        valid_count = sum(
            1 for result in results if isinstance(result, tuple) and result[0]
        )
        blocked_count = sum(
            1 for result in results if isinstance(result, tuple) and not result[0]
        )

        # Should block some requests due to rate limiting
        assert blocked_count > 0, "Rate limiting failed under concurrent load"
        assert valid_count <= 100, "Too many requests allowed through rate limiting"

        # Total should be all requests
        assert valid_count + blocked_count == 150

    @pytest.mark.asyncio
    async def test_concurrent_pattern_detection_accuracy(self, anti_abuse_validator):
        """Test pattern detection accuracy under concurrent operations."""
        user_id = 890

        # Create suspicious patterns concurrently
        identical_context = {"trivia_question": "What is 2+2?", "answer": "4"}

        tasks = []
        for i in range(20):  # Create identical context pattern
            task = anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=ActionType.TRIVIA_COMPLETED,
                context=identical_context.copy(),
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should detect identical context pattern
        blocked_results = [r for r in results if isinstance(r, tuple) and not r[0]]
        assert len(blocked_results) > 0, "Pattern detection failed under concurrency"

    @pytest.mark.asyncio
    async def test_concurrent_penalty_escalation_consistency(
        self, anti_abuse_validator
    ):
        """Test penalty escalation works consistently under concurrent violations."""
        user_id = 999

        # Create rapid violations that should escalate penalties
        tasks = []
        for i in range(30):
            context = {"rapid_fire": True, "attempt": i}
            # Use rapid-fire actions to trigger violations
            task = anti_abuse_validator.validate_action(
                user_id=user_id, action_type=ActionType.MESSAGE_SENT, context=context
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should escalate to gaming behavior penalties
        violations = [r for r in results if isinstance(r, tuple) and not r[0]]
        assert len(violations) > 5, "Not enough violations detected"

        # Later violations should show escalated penalties
        gaming_violations = [
            r
            for r in violations
            if len(r) > 1 and r[1] and "gaming" in str(r[1]).lower()
        ]
        assert len(gaming_violations) > 0, "Penalty escalation failed under concurrency"


class TestEventBusIntegrationConcurrency:
    """Test Event Bus integration maintains consistency under concurrent load."""

    @pytest_asyncio.fixture
    async def points_engine_with_event_bus(self):
        """Create PointsEngine with real Event Bus integration."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        # Track published events
        self.published_events = []
        self.event_lock = threading.Lock()

        def track_event_publish(event):
            with self.event_lock:
                self.published_events.append(event)
            return AsyncMock()

        event_bus.publish.side_effect = track_event_publish

        # Mock database
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.execute_query = AsyncMock(return_value={"balance": 100})

        return PointsEngine(database_client=db_client, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_concurrent_event_publishing_consistency(
        self, points_engine_with_event_bus
    ):
        """Test that events are published consistently under concurrent operations."""
        user_ids = [200, 201, 202, 203, 204]

        # Create concurrent operations that should publish events
        tasks = []
        for user_id in user_ids:
            for i in range(5):
                task = points_engine_with_event_bus.award_points(
                    user_id=user_id,
                    action_type=ActionType.ACHIEVEMENT_UNLOCKED,
                    context={"achievement_id": f"ach_{i}"},
                    points=100,
                )
                tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should succeed
        successful_results = [
            r for r in results if isinstance(r, PointsAwardResult) and r.success
        ]
        assert len(successful_results) == len(user_ids) * 5

        # Should have published events for each operation
        assert (
            len(self.published_events) == len(user_ids) * 5
        ), "Event publishing count mismatch"

        # Events should contain correct data
        for event in self.published_events:
            assert hasattr(event, "user_id"), "Event missing user_id"
            assert hasattr(event, "points_awarded"), "Event missing points_awarded"
            assert event.points_awarded == 100, "Event has incorrect points value"

    @pytest.mark.asyncio
    async def test_event_ordering_under_concurrency(self, points_engine_with_event_bus):
        """Test that events maintain logical ordering under concurrent operations."""
        user_id = 300

        # Create sequential operations for same user
        tasks = []
        for i in range(10):
            task = points_engine_with_event_bus.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"sequence": i},
                points=10,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        assert all(isinstance(r, PointsAwardResult) and r.success for r in results)

        # Events for this user should be present
        user_events = [
            e
            for e in self.published_events
            if hasattr(e, "user_id") and e.user_id == user_id
        ]
        assert len(user_events) == 10, "Not all events published for user"


class TestHighConcurrencyStressTest:
    """Stress tests for high concurrency scenarios."""

    @pytest_asyncio.fixture
    async def stress_test_engine(self):
        """Create optimized PointsEngine for stress testing."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.execute_query = AsyncMock(
            return_value={"balance": 0, "transaction_id": "tx_stress"}
        )

        return PointsEngine(database_client=db_client, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_thousand_concurrent_operations(self, stress_test_engine):
        """Test system handles 1000+ concurrent operations without corruption."""
        num_operations = 1000
        num_users = 100

        # Create massive concurrent load
        tasks = []
        for i in range(num_operations):
            user_id = 1000 + (i % num_users)  # Distribute across users
            task = stress_test_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"stress_test": True, "operation": i},
                points=1,
            )
            tasks.append(task)

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Measure performance
        duration = end_time - start_time
        operations_per_second = num_operations / duration

        # All operations should succeed
        successful_count = sum(
            1 for r in results if isinstance(r, PointsAwardResult) and r.success
        )
        success_rate = successful_count / num_operations

        # Performance and reliability requirements
        assert success_rate >= 0.99, f"Success rate too low: {success_rate:.2%}"
        assert (
            operations_per_second >= 100
        ), f"Throughput too low: {operations_per_second:.1f} ops/sec"
        assert duration < 30, f"Operations took too long: {duration:.1f} seconds"

    @pytest.mark.asyncio
    async def test_memory_usage_under_concurrency(self, stress_test_engine):
        """Test that memory usage doesn't grow excessively under concurrent load."""
        import os

        import psutil

        # Measure initial memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create sustained concurrent load
        for batch in range(5):  # 5 batches of 200 operations
            tasks = []
            for i in range(200):
                user_id = 2000 + i
                task = stress_test_engine.award_points(
                    user_id=user_id,
                    action_type=ActionType.COMMUNITY_PARTICIPATION,
                    context={"batch": batch, "operation": i},
                    points=5,
                )
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (<100MB for this test)
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f} MB"
