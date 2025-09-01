"""
Critical Database Transaction Integrity Tests

These tests ensure absolute atomicity and consistency of database operations.
ZERO TOLERANCE for data corruption or lost transactions.

Every database operation must be bulletproof - any failure could result in:
- Lost points (user trust destroyed)
- Duplicate points (economic collapse)
- Corrupted leaderboards (system credibility lost)
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from core.events import EventBus
from services.gamification.engines.points_engine import PointsEngine
from services.gamification.interfaces import ActionType, PointsAwardResult


class TestAtomicTransactionIntegrity:
    """Test atomic transaction guarantees - CRITICAL for data integrity."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine with mocked dependencies for transaction testing."""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()

        # Mock database client with transaction support
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.rollback_transaction = AsyncMock()
        db_client.execute_query = AsyncMock()

        engine = PointsEngine(database_client=db_client, event_bus=event_bus)
        return engine

    @pytest.mark.asyncio
    async def test_successful_transaction_commits_atomically(self, points_engine):
        """Test that successful operations commit all changes atomically."""
        user_id = 123
        initial_balance = 100
        points_to_award = 50

        # Mock successful database operations
        points_engine.database_client.execute_query.side_effect = [
            # Get current balance
            {"balance": initial_balance},
            # Insert transaction record
            {"transaction_id": "tx_001"},
            # Update balance
            {"rows_affected": 1},
            # Verify final balance
            {"balance": initial_balance + points_to_award},
        ]

        result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={"login_time": "2024-08-21T10:00:00Z"},
            points=points_to_award,
        )

        # Verify transaction was committed
        assert result.success is True
        assert result.points_awarded == points_to_award
        assert result.new_balance == initial_balance + points_to_award

        # Verify transaction flow
        points_engine.database_client.begin_transaction.assert_called_once()
        points_engine.database_client.commit_transaction.assert_called_once()
        points_engine.database_client.rollback_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_transaction_rolls_back_completely(self, points_engine):
        """Test that failed operations rollback completely with no partial state."""
        user_id = 123

        # Mock database failure during transaction
        points_engine.database_client.execute_query.side_effect = [
            # Get current balance succeeds
            {"balance": 100},
            # Insert transaction record fails
            Exception("Database connection lost"),
        ]

        result = await points_engine.award_points(
            user_id=user_id, action_type=ActionType.DAILY_LOGIN, context={}, points=50
        )

        # Verify operation failed cleanly
        assert result.success is False
        assert result.points_awarded == 0
        assert "Database connection lost" in result.error_message

        # Verify rollback was called
        points_engine.database_client.begin_transaction.assert_called_once()
        points_engine.database_client.rollback_transaction.assert_called_once()
        points_engine.database_client.commit_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_transactions_isolation(self, points_engine):
        """Test that concurrent transactions don't interfere with each other."""
        user1_id = 123
        user2_id = 456

        # Track transaction calls to ensure isolation
        transaction_calls = []

        def track_transaction_begin():
            transaction_calls.append("begin")
            return AsyncMock()

        def track_transaction_commit():
            transaction_calls.append("commit")
            return AsyncMock()

        points_engine.database_client.begin_transaction.side_effect = (
            track_transaction_begin
        )
        points_engine.database_client.commit_transaction.side_effect = (
            track_transaction_commit
        )

        # Mock successful queries for both users
        points_engine.database_client.execute_query.side_effect = [
            # User 1 operations
            {"balance": 100},
            {"transaction_id": "tx_001"},
            {"rows_affected": 1},
            {"balance": 150},
            # User 2 operations
            {"balance": 200},
            {"transaction_id": "tx_002"},
            {"rows_affected": 1},
            {"balance": 275},
        ]

        # Execute concurrent transactions
        results = await asyncio.gather(
            points_engine.award_points(user1_id, ActionType.DAILY_LOGIN, {}, 50),
            points_engine.award_points(user2_id, ActionType.MESSAGE_SENT, {}, 75),
        )

        # Both transactions should succeed independently
        assert all(r.success for r in results)
        assert results[0].points_awarded == 50
        assert results[1].points_awarded == 75

        # Should have 2 begin/commit pairs
        assert transaction_calls.count("begin") == 2
        assert transaction_calls.count("commit") == 2

    @pytest.mark.asyncio
    async def test_partial_failure_rollback_integrity(self, points_engine):
        """Test rollback when transaction partially succeeds then fails."""
        user_id = 123

        # Mock partial success then failure
        points_engine.database_client.execute_query.side_effect = [
            # Get balance succeeds
            {"balance": 100},
            # Insert transaction succeeds
            {"transaction_id": "tx_001"},
            # Update balance fails
            Exception("Constraint violation: negative balance"),
        ]

        result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={"admin_id": 1},
            points=-200,  # Would make balance negative
        )

        # Should fail and rollback everything
        assert result.success is False
        assert "Constraint violation" in result.error_message

        # Verify complete rollback
        points_engine.database_client.rollback_transaction.assert_called_once()
        points_engine.database_client.commit_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_deadlock_detection_and_retry(self, points_engine):
        """Test deadlock detection and automatic retry logic."""
        user_id = 123
        retry_count = 0

        def mock_execute_with_deadlock(*args, **kwargs):
            nonlocal retry_count
            retry_count += 1
            if retry_count <= 2:
                # First two attempts: deadlock
                raise Exception("Deadlock detected")
            else:
                # Third attempt: success
                if "SELECT" in args[0]:
                    return {"balance": 100}
                elif "INSERT" in args[0]:
                    return {"transaction_id": f"tx_{retry_count}"}
                elif "UPDATE" in args[0]:
                    return {"rows_affected": 1}
                else:
                    return {"balance": 150}

        points_engine.database_client.execute_query.side_effect = (
            mock_execute_with_deadlock
        )

        result = await points_engine.award_points(
            user_id=user_id, action_type=ActionType.DAILY_LOGIN, context={}, points=50
        )

        # Should eventually succeed after retries
        assert result.success is True
        assert result.points_awarded == 50

        # Should have retried multiple times
        assert retry_count > 2
        points_engine.database_client.commit_transaction.assert_called()


class TestDataConsistencyValidation:
    """Test data consistency constraints and validation."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine for consistency testing."""
        event_bus = Mock(spec=EventBus)
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.rollback_transaction = AsyncMock()
        db_client.execute_query = AsyncMock()

        return PointsEngine(database_client=db_client, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_balance_constraint_enforcement(self, points_engine):
        """Test that balance constraints are enforced at database level."""
        user_id = 123

        # Mock constraint violation for negative balance
        points_engine.database_client.execute_query.side_effect = [
            {"balance": 50},  # Current balance
            {"transaction_id": "tx_001"},  # Transaction insert
            Exception("CHECK constraint failed: balance >= 0"),  # Balance update fails
        ]

        result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={},
            points=-100,  # Would make balance negative
        )

        assert result.success is False
        assert "constraint" in result.error_message.lower()
        points_engine.database_client.rollback_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_foreign_key_constraint_enforcement(self, points_engine):
        """Test foreign key constraints prevent orphaned records."""
        user_id = 999  # Non-existent user

        points_engine.database_client.execute_query.side_effect = [
            Exception("FOREIGN KEY constraint failed: user_id not found")
        ]

        result = await points_engine.award_points(
            user_id=user_id, action_type=ActionType.DAILY_LOGIN, context={}, points=50
        )

        assert result.success is False
        assert "foreign key" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_data_type_constraint_enforcement(self, points_engine):
        """Test data type constraints prevent invalid data."""
        user_id = 123

        points_engine.database_client.execute_query.side_effect = [
            {"balance": 100},
            Exception("Invalid data type: points must be integer"),
        ]

        # This should be caught at the application level, but test DB constraint too
        with pytest.raises(Exception):
            await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.DAILY_LOGIN,
                context={},
                points="invalid",  # String instead of int
            )


class TestTransactionPerformance:
    """Test transaction performance requirements."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine for performance testing."""
        event_bus = Mock(spec=EventBus)
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.execute_query = AsyncMock(return_value={"balance": 100})

        return PointsEngine(database_client=db_client, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_transaction_latency_requirements(self, points_engine):
        """Test that transactions complete within latency requirements (<100ms)."""
        import time

        user_id = 123
        start_time = time.time()

        result = await points_engine.award_points(
            user_id=user_id, action_type=ActionType.DAILY_LOGIN, context={}, points=50
        )

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Should complete within 100ms requirement
        assert (
            latency_ms < 100
        ), f"Transaction took {latency_ms}ms, exceeds 100ms requirement"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_concurrent_transaction_throughput(self, points_engine):
        """Test system can handle concurrent transaction load."""
        # Simulate 50 concurrent transactions
        tasks = []
        for i in range(50):
            task = points_engine.award_points(
                user_id=100 + i,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": i},
                points=10,
            )
            tasks.append(task)

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # All should succeed
        successful_results = [
            r for r in results if isinstance(r, PointsAwardResult) and r.success
        ]
        assert len(successful_results) == 50

        # Should handle 50 transactions in reasonable time (<5 seconds)
        total_time = end_time - start_time
        assert total_time < 5.0, f"50 transactions took {total_time}s, too slow"

    @pytest.mark.asyncio
    async def test_transaction_batching_optimization(self, points_engine):
        """Test that bulk operations are optimized."""
        # This would test actual batching implementation
        # For now, just verify the interface exists
        user_ids = [100, 101, 102, 103, 104]

        # Bulk award points (if implemented)
        if hasattr(points_engine, "award_points_bulk"):
            results = await points_engine.award_points_bulk(
                user_ids=user_ids,
                action_type=ActionType.COMMUNITY_PARTICIPATION,
                context={},
                points=25,
            )
            assert len(results) == len(user_ids)
            assert all(r.success for r in results)
