"""
FIXED POINTS ENGINE VALIDATION TESTS
=====================================

Tests to validate the fixed points engine eliminates deadlocks and maintains
mathematical integrity while meeting performance requirements.
"""

import asyncio
import time
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine_fixed import FixedPointsEngine
from services.gamification.interfaces import ActionType, MultiplierType


class TestFixedPointsEngineIntegrity:
    """Test the fixed engine eliminates deadlocks and maintains integrity."""

    @pytest_asyncio.fixture
    async def fixed_engine(self):
        """Create fixed points engine."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()
        
        return FixedPointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )

    @pytest.mark.asyncio
    async def test_single_operation_performance(self, fixed_engine):
        """CRITICAL: Single operation must be fast and reliable."""
        start_time = time.time()
        
        result = await fixed_engine.award_points(
            user_id=1,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        
        duration = time.time() - start_time
        
        # PERFORMANCE REQUIREMENTS
        assert result.success, f"Operation failed: {result.error_message}"
        assert duration < 0.1, f"Too slow: {duration}s > 0.1s requirement"
        assert result.points_awarded == 50, "Incorrect calculation"
        
        print(f"✅ Single operation: {duration*1000:.2f}ms (target: <100ms)")

    @pytest.mark.asyncio
    async def test_concurrent_operations_no_deadlock(self, fixed_engine):
        """CRITICAL: Concurrent operations must not deadlock."""
        user_id = 1
        num_operations = 10
        points_per_operation = 10
        
        async def award_task(i):
            return await fixed_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": i},
                base_points=points_per_operation,
            )
        
        start_time = time.time()
        
        # Execute concurrently with timeout
        try:
            tasks = [award_task(i) for i in range(num_operations)]
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=2.0  # Should complete much faster
            )
        except asyncio.TimeoutError:
            pytest.fail("❌ DEADLOCK DETECTED: Concurrent operations timed out")
        
        duration = time.time() - start_time
        
        # All should succeed
        assert all(r.success for r in results), "Some operations failed"
        
        # Mathematical integrity
        total_balance, _ = await fixed_engine.get_user_balance(user_id)
        expected_total = sum(r.points_awarded for r in results)
        
        assert total_balance == expected_total, (
            f"Race condition: balance={total_balance}, expected={expected_total}"
        )
        
        # Performance check
        avg_time = duration / num_operations
        assert avg_time < 0.05, f"Average operation too slow: {avg_time*1000:.2f}ms"
        
        print(f"✅ Concurrent operations: {duration*1000:.2f}ms total, "
              f"{avg_time*1000:.2f}ms average")

    @pytest.mark.asyncio
    async def test_mathematical_integrity_comprehensive(self, fixed_engine):
        """CRITICAL: Mathematical integrity under all operations."""
        user_id = 1
        
        operations = [
            (ActionType.DAILY_LOGIN, 50),
            (ActionType.TRIVIA_COMPLETED, 100),
            (ActionType.MESSAGE_SENT, 5),
            (ActionType.VIP_PURCHASE, 1000),
        ]
        
        expected_total = 0
        
        for action_type, base_points in operations:
            result = await fixed_engine.award_points(
                user_id=user_id,
                action_type=action_type,
                context={},
                base_points=base_points,
            )
            
            assert result.success, f"Operation failed: {action_type}"
            expected_total += result.points_awarded
        
        # Verify balance integrity
        total_balance, _ = await fixed_engine.get_user_balance(user_id)
        assert total_balance == expected_total, (
            f"Balance integrity violation: {total_balance} != {expected_total}"
        )
        
        # Verify through transaction history
        history = await fixed_engine.get_transaction_history(user_id, limit=100)
        history_total = sum(tx["points_change"] for tx in history)
        
        assert history_total == expected_total, (
            f"Transaction history mismatch: {history_total} != {expected_total}"
        )
        
        # Verify integrity check passes
        integrity_valid = await fixed_engine.verify_balance_integrity(user_id)
        assert integrity_valid, "Balance integrity verification failed"
        
        print(f"✅ Mathematical integrity: balance={total_balance}, "
              f"transactions={history_total}")

    @pytest.mark.asyncio
    async def test_massive_concurrent_load(self, fixed_engine):
        """PERFORMANCE: Test under massive concurrent load."""
        user_id = 1
        num_operations = 50  # Reduced for faster testing
        points_per_operation = 5
        
        async def award_task(i):
            return await fixed_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"task_id": i},
                base_points=points_per_operation,
            )
        
        start_time = time.time()
        
        try:
            tasks = [award_task(i) for i in range(num_operations)]
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=3.0  # Generous timeout
            )
        except asyncio.TimeoutError:
            pytest.fail("❌ MASSIVE LOAD DEADLOCK: Operations timed out")
        
        duration = time.time() - start_time
        
        # All operations should succeed
        successful_results = [r for r in results if r.success]
        assert len(successful_results) == num_operations, (
            f"Operations failed: {len(successful_results)}/{num_operations}"
        )
        
        # Mathematical integrity under load
        total_balance, _ = await fixed_engine.get_user_balance(user_id)
        expected_total = sum(r.points_awarded for r in successful_results)
        
        assert total_balance == expected_total, (
            f"Load test integrity failure: {total_balance} != {expected_total}"
        )
        
        # Performance metrics
        avg_latency = duration / num_operations
        throughput = num_operations / duration
        
        print(f"✅ Load test: {num_operations} ops in {duration*1000:.2f}ms")
        print(f"   Average latency: {avg_latency*1000:.2f}ms")
        print(f"   Throughput: {throughput:.2f} operations/second")