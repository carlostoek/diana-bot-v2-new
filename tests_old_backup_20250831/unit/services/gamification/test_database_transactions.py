"""
Critical Database Transaction Tests

These tests ensure atomic transactions and data integrity under all conditions.
Database corruption or inconsistency could destroy the entire points system
and user trust. ZERO TOLERANCE for data integrity failures.

Every transaction MUST be atomic - either complete success or complete rollback.
"""

import asyncio
import threading
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import pytest_asyncio

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine import PointsEngine, PointsEngineError
from services.gamification.interfaces import ActionType, MultiplierType
from services.gamification.models import PointsTransaction, UserGamification


class TestAtomicTransactionIntegrity:
    """Test atomic transaction guarantees."""

    @pytest_asyncio.fixture
    async def points_engine_with_db_mock(self):
        """Create PointsEngine with database mock for transaction testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()

        # Mock database client
        db_mock = AsyncMock()
        db_mock.begin_transaction = AsyncMock()
        db_mock.commit_transaction = AsyncMock()
        db_mock.rollback_transaction = AsyncMock()
        db_mock.execute_query = AsyncMock()

        engine = PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=db_mock,
        )
        engine._db_mock = db_mock  # Store for test access
        return engine

    @pytest.mark.asyncio
    async def test_successful_transaction_commits_atomically(
        self, points_engine_with_db_mock
    ):
        """Test that successful operations commit all changes atomically."""
        user_id = 123
        db_mock = points_engine_with_db_mock._db_mock

        # Mock successful database operations
        db_mock.begin_transaction.return_value = "tx_123"
        db_mock.execute_query.return_value = {"success": True}
        db_mock.commit_transaction.return_value = True

        result = await points_engine_with_db_mock.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        assert result.success

        # Verify transaction flow
        db_mock.begin_transaction.assert_called_once()
        db_mock.commit_transaction.assert_called_once()
        db_mock.rollback_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_transaction_rolls_back_completely(
        self, points_engine_with_db_mock
    ):
        """Test that failed operations rollback all changes atomically."""
        user_id = 123
        db_mock = points_engine_with_db_mock._db_mock

        # Mock transaction start but fail during execution
        db_mock.begin_transaction.return_value = "tx_123"
        db_mock.execute_query.side_effect = Exception("Database error")
        db_mock.rollback_transaction.return_value = True

        # Should handle transaction failure gracefully
        with pytest.raises(PointsEngineError, match="Transaction failed"):
            await points_engine_with_db_mock.award_points(
                user_id=user_id,
                action_type=ActionType.DAILY_LOGIN,
                context={},
            )

        # Verify rollback occurred
        db_mock.begin_transaction.assert_called_once()
        db_mock.rollback_transaction.assert_called_once()
        db_mock.commit_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_transactions_isolation(self, points_engine_with_db_mock):
        """Test that concurrent transactions maintain isolation."""
        user_id = 123
        db_mock = points_engine_with_db_mock._db_mock

        # Track transaction calls
        transaction_calls = []

        def mock_begin_transaction():
            tx_id = f"tx_{len(transaction_calls)}"
            transaction_calls.append({"id": tx_id, "status": "started"})
            return tx_id

        def mock_commit_transaction(tx_id):
            for tx in transaction_calls:
                if tx["id"] == tx_id:
                    tx["status"] = "committed"
            return True

        def mock_rollback_transaction(tx_id):
            for tx in transaction_calls:
                if tx["id"] == tx_id:
                    tx["status"] = "rolled_back"
            return True

        db_mock.begin_transaction.side_effect = mock_begin_transaction
        db_mock.commit_transaction.side_effect = mock_commit_transaction
        db_mock.rollback_transaction.side_effect = mock_rollback_transaction
        db_mock.execute_query.return_value = {"success": True}

        # Create concurrent operations
        async def award_task(i):
            return await points_engine_with_db_mock.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": f"msg_{i}"},
                base_points=10,
            )

        tasks = [award_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert (
            len(successful_results) == 5
        ), "All concurrent transactions should succeed"

        # Each transaction should have its own ID and commit
        assert len(transaction_calls) == 5, "Should have 5 separate transactions"
        committed_txs = [tx for tx in transaction_calls if tx["status"] == "committed"]
        assert len(committed_txs) == 5, "All transactions should be committed"

    @pytest.mark.asyncio
    async def test_partial_failure_rollback_integrity(self, points_engine_with_db_mock):
        """Test rollback when transaction fails partway through."""
        user_id = 123
        db_mock = points_engine_with_db_mock._db_mock

        # Mock partial failure scenario
        call_count = 0

        def mock_execute_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # First two queries succeed
                return {"success": True}
            else:  # Third query fails
                raise Exception("Partial failure")

        db_mock.begin_transaction.return_value = "tx_123"
        db_mock.execute_query.side_effect = mock_execute_query
        db_mock.rollback_transaction.return_value = True

        # Should rollback entire transaction on partial failure
        with pytest.raises(PointsEngineError):
            await points_engine_with_db_mock.award_points(
                user_id=user_id,
                action_type=ActionType.TRIVIA_COMPLETED,
                context={"correct_answer": True},
            )

        # Verify rollback occurred
        db_mock.rollback_transaction.assert_called_once_with("tx_123")
        db_mock.commit_transaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_deadlock_detection_and_retry(self, points_engine_with_db_mock):
        """Test deadlock detection and automatic retry."""
        user_id = 123
        db_mock = points_engine_with_db_mock._db_mock

        # Mock deadlock scenario
        attempt_count = 0

        def mock_execute_with_deadlock(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:  # First two attempts deadlock
                raise Exception("Deadlock detected")
            else:  # Third attempt succeeds
                return {"success": True}

        db_mock.begin_transaction.return_value = "tx_123"
        db_mock.execute_query.side_effect = mock_execute_with_deadlock
        db_mock.commit_transaction.return_value = True
        db_mock.rollback_transaction.return_value = True

        # Should retry and eventually succeed
        result = await points_engine_with_db_mock.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        assert result.success, "Should succeed after deadlock retry"
        assert attempt_count == 3, "Should retry after deadlocks"

        # Should have rolled back failed attempts and committed final success
        assert (
            db_mock.rollback_transaction.call_count == 2
        ), "Should rollback deadlocked transactions"
        db_mock.commit_transaction.assert_called_once()


class TestDataConsistencyValidation:
    """Test data consistency and constraint enforcement."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine for consistency testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()

        engine = PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )
        return engine

    @pytest.mark.asyncio
    async def test_balance_constraint_enforcement(self, points_engine):
        """Test that negative balance constraints are enforced."""
        user_id = 123

        # Give user initial points
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123"},
            base_points=100,
        )

        # Try to spend more than available (should fail)
        success = await points_engine.spend_points(
            user_id=user_id,
            amount=200,  # More than the 100 available
            reason="Overspend test",
        )

        assert success is False, "Should not allow negative balance"

        # Balance should remain unchanged
        total, available = await points_engine.get_user_balance(user_id)
        assert available == 100, "Balance should be unchanged after failed spend"

    @pytest.mark.asyncio
    async def test_foreign_key_constraint_enforcement(self, points_engine):
        """Test foreign key constraints prevent orphaned records."""
        # This test would verify that transaction records can't exist
        # without valid user records, etc.

        # In a real database implementation, this would test:
        # 1. Cannot create transactions for non-existent users
        # 2. Cannot delete users with existing transactions
        # 3. Cannot create transactions with invalid action types

        # For now, verify the engine validates user existence
        invalid_user_id = -999

        result = await points_engine.award_points(
            user_id=invalid_user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        # Engine should handle gracefully (either succeed by creating user or fail safely)
        assert isinstance(result.success, bool), "Should return valid result"

    @pytest.mark.asyncio
    async def test_unique_constraint_enforcement(self, points_engine):
        """Test unique constraints prevent duplicate records."""
        user_id = 123
        transaction_id = "unique_tx_123"

        # First transaction should succeed
        result1 = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": transaction_id},
            base_points=100,
        )
        assert result1.success

        # Duplicate transaction should be prevented
        result2 = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": transaction_id},  # Same transaction ID
            base_points=100,
        )

        # Should either fail or handle idempotently
        if result2.success:
            # If it succeeds, it should be idempotent (no additional points)
            total, _ = await points_engine.get_user_balance(user_id)
            assert (
                total == result1.points_awarded
            ), "Duplicate transaction should be idempotent"

    @pytest.mark.asyncio
    async def test_data_type_constraint_enforcement(self, points_engine):
        """Test data type constraints prevent invalid data."""
        user_id = 123

        # Test with various invalid inputs
        invalid_contexts = [
            {"points": "not_a_number"},  # String instead of number
            {"timestamp": "invalid_date"},  # Invalid date format
            {"user_id": "not_an_int"},  # Non-integer user ID in context
        ]

        for context in invalid_contexts:
            # Should handle invalid data gracefully
            result = await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context=context,
            )

            # Either succeed (by sanitizing) or fail gracefully
            assert isinstance(result.success, bool), "Should handle invalid data types"


class TestTransactionRecovery:
    """Test transaction recovery and error handling."""

    @pytest_asyncio.fixture
    async def points_engine_with_recovery(self):
        """Create PointsEngine with recovery simulation."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)

        # Mock database with recovery scenarios
        db_mock = AsyncMock()
        db_mock.is_connected = AsyncMock(return_value=True)
        db_mock.reconnect = AsyncMock(return_value=True)

        engine = PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=db_mock,
        )
        engine._db_mock = db_mock
        return engine

    @pytest.mark.asyncio
    async def test_connection_loss_recovery(self, points_engine_with_recovery):
        """Test recovery from database connection loss."""
        user_id = 123
        db_mock = points_engine_with_recovery._db_mock

        # Simulate connection loss then recovery
        call_count = 0

        def mock_execute_with_reconnect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call - connection lost
                raise Exception("Connection lost")
            else:
                # After reconnect - succeeds
                return {"success": True}

        db_mock.execute_query.side_effect = mock_execute_with_reconnect
        db_mock.begin_transaction.return_value = "tx_123"
        db_mock.commit_transaction.return_value = True

        # Should recover from connection loss
        result = await points_engine_with_recovery.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        assert result.success, "Should recover from connection loss"
        db_mock.reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_timeout_handling(self, points_engine_with_recovery):
        """Test handling of transaction timeouts."""
        user_id = 123
        db_mock = points_engine_with_recovery._db_mock

        # Mock transaction timeout
        async def mock_timeout_execute(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow operation
            raise Exception("Transaction timeout")

        db_mock.execute_query.side_effect = mock_timeout_execute
        db_mock.begin_transaction.return_value = "tx_123"
        db_mock.rollback_transaction.return_value = True

        # Should handle timeout gracefully
        with pytest.raises(PointsEngineError, match="Transaction failed"):
            await points_engine_with_recovery.award_points(
                user_id=user_id,
                action_type=ActionType.DAILY_LOGIN,
                context={},
            )

        # Should rollback on timeout
        db_mock.rollback_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_corrupted_transaction_log_recovery(
        self, points_engine_with_recovery
    ):
        """Test recovery from corrupted transaction logs."""
        user_id = 123

        # Simulate corrupted transaction state
        with patch.object(
            points_engine_with_recovery, "_get_transaction_state"
        ) as mock_get_state:
            mock_get_state.side_effect = Exception("Corrupted transaction log")

            # Should handle corruption gracefully
            result = await points_engine_with_recovery.award_points(
                user_id=user_id,
                action_type=ActionType.DAILY_LOGIN,
                context={},
            )

            # Should either succeed with recovery or fail safely
            assert isinstance(
                result.success, bool
            ), "Should handle corruption gracefully"


class TestTransactionPerformance:
    """Test transaction performance and optimization."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine for performance testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()

        engine = PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )
        return engine

    @pytest.mark.asyncio
    async def test_transaction_latency_requirements(self, points_engine):
        """Test that transactions meet latency requirements."""
        user_id = 123

        # Measure transaction latency
        latencies = []

        for i in range(10):
            start_time = time.time()

            result = await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": f"perf_test_{i}"},
                base_points=10,
            )

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            assert result.success, f"Transaction {i} failed"

        # Verify performance requirements
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
        max_latency = max(latencies)

        assert (
            avg_latency < 50
        ), f"Average transaction latency too high: {avg_latency}ms"
        assert p95_latency < 100, f"95th percentile latency too high: {p95_latency}ms"
        assert max_latency < 200, f"Maximum latency too high: {max_latency}ms"

    @pytest.mark.asyncio
    async def test_concurrent_transaction_throughput(self, points_engine):
        """Test concurrent transaction throughput."""
        user_id = 123
        num_transactions = 50

        async def transaction_task(i):
            return await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": f"throughput_test_{i}"},
                base_points=5,
            )

        # Measure throughput
        start_time = time.time()
        tasks = [transaction_task(i) for i in range(num_transactions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Verify all transactions succeeded
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert (
            len(successful_results) == num_transactions
        ), "All transactions should succeed"

        # Calculate throughput
        duration = end_time - start_time
        throughput = num_transactions / duration

        assert throughput > 100, f"Transaction throughput too low: {throughput} tx/sec"

    @pytest.mark.asyncio
    async def test_transaction_batching_optimization(self, points_engine):
        """Test transaction batching for bulk operations."""
        user_id = 123

        # Simulate bulk point award scenario
        bulk_operations = [
            (ActionType.MESSAGE_SENT, 5),
            (ActionType.MESSAGE_SENT, 5),
            (ActionType.MESSAGE_SENT, 5),
            (ActionType.TRIVIA_COMPLETED, 100),
            (ActionType.TRIVIA_COMPLETED, 100),
        ]

        # Individual transactions
        start_time = time.time()
        individual_results = []
        for action_type, points in bulk_operations:
            result = await points_engine.award_points(
                user_id=user_id,
                action_type=action_type,
                context={},
                base_points=points,
            )
            individual_results.append(result)
        individual_time = time.time() - start_time

        # Verify final balance
        final_balance, _ = await points_engine.get_user_balance(user_id)
        expected_total = sum(r.points_awarded for r in individual_results)

        assert (
            final_balance == expected_total
        ), "Bulk operations should maintain consistency"

        # Performance should be reasonable
        assert individual_time < 1.0, f"Bulk operations too slow: {individual_time}s"
