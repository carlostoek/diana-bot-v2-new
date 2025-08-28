"""
CRITICAL INTEGRITY DIAGNOSIS TESTS
==================================

Minimal test suite to diagnose critical issues in the points system.
These tests MUST pass before production deployment.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine import PointsEngine
from services.gamification.interfaces import ActionType


class TestCriticalIntegrityDiagnosis:
    """Minimal tests to diagnose critical system failures."""

    @pytest_asyncio.fixture
    async def minimal_engine(self):
        """Create minimal PointsEngine for diagnosis."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()
        
        return PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )

    @pytest.mark.asyncio
    async def test_single_operation_baseline(self, minimal_engine):
        """BASELINE: Single point operation must succeed quickly."""
        import time
        start_time = time.time()
        
        result = await minimal_engine.award_points(
            user_id=1,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        
        duration = time.time() - start_time
        
        # CRITICAL: Must succeed and be fast
        assert result.success, f"Basic operation failed: {result.error_message}"
        assert duration < 0.1, f"Operation too slow: {duration}s > 0.1s"
        assert result.points_awarded == 50, "Incorrect points calculation"

    @pytest.mark.asyncio
    async def test_mathematical_integrity_simple(self, minimal_engine):
        """CRITICAL: Balance must equal transaction sum."""
        user_id = 1
        
        # Single award
        result1 = await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        
        # Second award
        result2 = await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.MESSAGE_SENT,
            context={},
        )
        
        # Check balance
        total_balance, _ = await minimal_engine.get_user_balance(user_id)
        expected_total = result1.points_awarded + result2.points_awarded
        
        assert total_balance == expected_total, (
            f"Mathematical integrity VIOLATED: balance={total_balance}, "
            f"expected={expected_total}"
        )

    @pytest.mark.asyncio
    async def test_concurrent_operations_minimal(self, minimal_engine):
        """CRITICAL: Two concurrent operations must not create race condition."""
        user_id = 1
        
        # Create two concurrent operations
        task1 = minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.MESSAGE_SENT,
            context={"id": 1},
            base_points=10
        )
        
        task2 = minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.MESSAGE_SENT,
            context={"id": 2},
            base_points=10
        )
        
        # Execute concurrently with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(task1, task2),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            pytest.fail("Concurrent operations timed out - DEADLOCK detected")
        
        # Verify both succeeded
        assert all(r.success for r in results), "Concurrent operations failed"
        
        # Verify balance integrity
        total_balance, _ = await minimal_engine.get_user_balance(user_id)
        expected_balance = sum(r.points_awarded for r in results)
        
        assert total_balance == expected_balance, (
            f"Race condition detected: balance={total_balance}, "
            f"expected={expected_balance}"
        )

    @pytest.mark.asyncio
    async def test_negative_adjustment_safety(self, minimal_engine):
        """CRITICAL: Negative adjustments must not corrupt balance."""
        user_id = 1
        
        # Give initial points
        await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={},
            base_points=1000
        )
        
        # Apply penalty
        penalty_result = await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={"reason": "penalty"},
            base_points=-200,
            force_award=True
        )
        
        assert penalty_result.success, "Penalty application failed"
        assert penalty_result.points_awarded == -200, "Incorrect penalty calculation"
        
        # Verify final balance
        final_balance, _ = await minimal_engine.get_user_balance(user_id)
        assert final_balance == 800, f"Penalty calculation error: {final_balance} != 800"
        
        # Verify integrity
        integrity_valid = await minimal_engine.verify_balance_integrity(user_id)
        assert integrity_valid, "Balance integrity check failed after penalty"

    @pytest.mark.asyncio  
    async def test_performance_latency_requirement(self, minimal_engine):
        """CRITICAL: Performance must meet <100ms requirement."""
        user_id = 1
        import time
        
        # Multiple operations to test sustained performance
        durations = []
        
        for i in range(10):
            start_time = time.time()
            
            result = await minimal_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": i},
                base_points=5
            )
            
            duration = time.time() - start_time
            durations.append(duration)
            
            assert result.success, f"Operation {i} failed"
            assert duration < 0.1, f"Operation {i} too slow: {duration}s"
        
        # Check average performance
        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 0.02, f"Average latency too high: {avg_duration}s > 0.02s"