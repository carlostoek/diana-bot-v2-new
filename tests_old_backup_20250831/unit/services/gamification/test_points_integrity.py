"""
Critical Points Integrity Tests

These tests ensure mathematical correctness and prevent points corruption.
Any failure here indicates potential system-breaking bugs that could
destroy user trust and break the entire gamification economy.

ZERO TOLERANCE for failures in this test suite.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine import PointsEngine
from services.gamification.interfaces import ActionType, MultiplierType
from services.gamification.models import PointsTransaction, UserGamification


class TestPointsMathematicalIntegrity:
    """Test mathematical correctness of points calculations."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create clean PointsEngine for mathematical testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()

        engine = PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )
        return engine

    @pytest.mark.asyncio
    async def test_balance_equals_transaction_sum_single_user(self, points_engine):
        """CRITICAL: Balance must always equal sum of all transactions."""
        user_id = 123
        expected_total = 0

        # Perform various point operations
        operations = [
            (ActionType.DAILY_LOGIN, 50),
            (ActionType.TRIVIA_COMPLETED, 100),
            (ActionType.MESSAGE_SENT, 5),
            (ActionType.VIP_PURCHASE, 1000),
            (ActionType.ADMIN_ADJUSTMENT, -200),  # Penalty
        ]

        for action_type, base_points in operations:
            if base_points < 0:
                result = await points_engine.award_points(
                    user_id=user_id,
                    action_type=action_type,
                    context={"admin_id": 1, "reason": "Test penalty"},
                    base_points=base_points,
                    force_award=True,
                )
            else:
                result = await points_engine.award_points(
                    user_id=user_id,
                    action_type=action_type,
                    context={},
                    base_points=base_points,
                )

            assert result.success, f"Failed to award points for {action_type}"
            expected_total += result.points_awarded

        # Verify mathematical integrity
        total_balance, available_balance = await points_engine.get_user_balance(user_id)
        assert total_balance == expected_total, (
            f"Balance integrity violated: balance={total_balance}, "
            f"expected={expected_total}"
        )

        # Additional verification: sum transaction history
        history = await points_engine.get_transaction_history(user_id, limit=1000)
        history_sum = sum(tx["points_awarded"] for tx in history)
        assert (
            history_sum == expected_total
        ), f"Transaction history sum mismatch: {history_sum} != {expected_total}"

    @pytest.mark.asyncio
    async def test_concurrent_points_award_no_race_condition(self, points_engine):
        """CRITICAL: Concurrent point awards must not create race conditions."""
        user_id = 123
        num_operations = 50
        points_per_operation = 10

        # Create concurrent award operations
        async def award_points_task(i):
            return await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": f"msg_{i}"},
                base_points=points_per_operation,
            )

        # Execute all operations concurrently
        tasks = [award_points_task(i) for i in range(num_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == num_operations, (
            f"Not all concurrent operations succeeded: "
            f"{len(successful_results)}/{num_operations}"
        )

        # Verify final balance is mathematically correct
        total_balance, _ = await points_engine.get_user_balance(user_id)
        expected_total = sum(r.points_awarded for r in successful_results)

        assert total_balance == expected_total, (
            f"Race condition detected: balance={total_balance}, "
            f"expected={expected_total}"
        )

    @pytest.mark.asyncio
    async def test_multiplier_calculation_precision(self, points_engine):
        """Test multiplier calculations maintain mathematical precision."""
        user_id = 123
        base_points = 100

        # Set up complex multiplier scenario
        user_data = await points_engine._get_or_create_user_data(user_id)
        user_data.vip_multiplier = 1.5
        user_data.current_streak = 10
        user_data.level = 5

        result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"event_multiplier": 2.0},
            base_points=base_points,
        )

        # Calculate expected result manually
        expected_multipliers = {
            MultiplierType.VIP_BONUS: 1.5,
            MultiplierType.STREAK_BONUS: 1.2,  # 10-day streak
            MultiplierType.LEVEL_BONUS: 1.2,  # Level 5
            MultiplierType.EVENT_BONUS: 2.0,
        }

        expected_total = base_points
        for multiplier in expected_multipliers.values():
            expected_total = int(expected_total * multiplier)

        assert result.points_awarded == expected_total, (
            f"Multiplier calculation error: got {result.points_awarded}, "
            f"expected {expected_total}"
        )
        assert result.base_points == base_points

    @pytest.mark.asyncio
    async def test_points_spend_balance_consistency(self, points_engine):
        """Test that spending points maintains balance consistency."""
        user_id = 123

        # Award initial points
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123"},
            base_points=1000,
        )

        initial_total, initial_available = await points_engine.get_user_balance(user_id)
        assert initial_total == 1000
        assert initial_available == 1000

        # Spend some points
        spend_amount = 300
        success = await points_engine.spend_points(
            user_id=user_id,
            amount=spend_amount,
            reason="Test purchase",
        )
        assert success is True

        # Verify balance consistency
        final_total, final_available = await points_engine.get_user_balance(user_id)
        assert (
            final_total == initial_total
        ), "Total points should not change when spending"
        assert final_available == initial_available - spend_amount, (
            f"Available points calculation error: {final_available} != "
            f"{initial_available - spend_amount}"
        )

    @pytest.mark.asyncio
    async def test_negative_adjustment_mathematical_correctness(self, points_engine):
        """Test negative adjustments (penalties) maintain mathematical integrity."""
        user_id = 123

        # Give user initial points
        initial_result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123"},
            base_points=1000,
        )
        assert initial_result.success

        # Apply negative adjustment
        penalty_amount = -250
        penalty_result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={"admin_id": 1, "reason": "Violation penalty"},
            base_points=penalty_amount,
            force_award=True,
        )

        assert penalty_result.success
        assert penalty_result.points_awarded == penalty_amount

        # Verify mathematical correctness
        final_balance, _ = await points_engine.get_user_balance(user_id)
        expected_balance = initial_result.points_awarded + penalty_amount
        assert (
            final_balance == expected_balance
        ), f"Negative adjustment calculation error: {final_balance} != {expected_balance}"

    @pytest.mark.asyncio
    async def test_balance_integrity_verification_detects_corruption(
        self, points_engine
    ):
        """Test balance integrity verification catches corruption."""
        user_id = 123

        # Create valid transactions
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        # Verify integrity is clean initially
        is_valid = await points_engine.verify_balance_integrity(user_id)
        assert is_valid is True

        # Simulate corruption by manually modifying user data
        user_data = await points_engine._get_or_create_user_data(user_id)
        original_balance = user_data.total_points
        user_data.total_points = 999999  # Corrupt the balance

        # Integrity check should detect corruption
        is_valid = await points_engine.verify_balance_integrity(user_id)
        assert (
            is_valid is False
        ), "Balance integrity verification failed to detect corruption"

        # Restore original balance
        user_data.total_points = original_balance

    @pytest.mark.asyncio
    async def test_zero_points_operations_mathematical_safety(self, points_engine):
        """Test that zero-point operations don't break mathematical integrity."""
        user_id = 123

        # Award some initial points
        initial_result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        initial_balance = initial_result.new_balance

        # Attempt zero-point operations
        zero_result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.ACHIEVEMENT_UNLOCKED,
            context={"achievement_id": "zero_point_test"},
            base_points=0,
        )

        # Zero point operations should fail gracefully
        assert zero_result.success is False

        # Balance should remain unchanged
        current_balance, _ = await points_engine.get_user_balance(user_id)
        assert (
            current_balance == initial_balance
        ), "Zero-point operation modified balance unexpectedly"

    @pytest.mark.asyncio
    async def test_extreme_multiplier_values_precision(self, points_engine):
        """Test mathematical precision with extreme multiplier values."""
        user_id = 123
        base_points = 1

        # Test extreme multiplier combinations
        user_data = await points_engine._get_or_create_user_data(user_id)
        user_data.vip_multiplier = 2.5
        user_data.current_streak = 30  # Max streak bonus (1.5x)
        user_data.level = 10

        result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"event_multiplier": 3.0},
            base_points=base_points,
        )

        # Ensure result is reasonable and precise
        assert result.success
        assert result.points_awarded > base_points
        assert result.points_awarded < 1000  # Sanity check for reasonable upper bound

        # Verify mathematical consistency
        total_balance, _ = await points_engine.get_user_balance(user_id)
        assert total_balance == result.points_awarded


class TestAntiAbuseIntegration:
    """Test anti-abuse integration with points integrity."""

    @pytest_asyncio.fixture
    async def points_engine_with_anti_abuse(self):
        """Create PointsEngine with realistic anti-abuse validation."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)

        # Track request counts for rate limiting simulation
        request_counts = {}

        async def mock_validate_action(user_id, action_type, context):
            # Simulate rate limiting
            key = f"{user_id}:{action_type.value}"
            count = request_counts.get(key, 0) + 1
            request_counts[key] = count

            if count > 10:  # Rate limit at 10 requests
                from services.gamification.interfaces import AntiAbuseViolation

                return (
                    False,
                    AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
                    "Rate limit exceeded",
                )

            return True, None, None

        anti_abuse_validator.validate_action.side_effect = mock_validate_action
        anti_abuse_validator.record_action = AsyncMock()

        engine = PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )
        engine._request_counts = request_counts  # Store for test access
        return engine

    @pytest.mark.asyncio
    async def test_anti_abuse_prevents_points_inflation(
        self, points_engine_with_anti_abuse
    ):
        """Test that anti-abuse prevents points inflation through gaming."""
        user_id = 123

        # Rapid-fire identical requests (should be rate limited)
        successful_awards = 0
        total_points_awarded = 0

        for i in range(15):  # Exceed rate limit
            result = await points_engine_with_anti_abuse.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message": f"spam_{i}"},
            )

            if result.success:
                successful_awards += 1
                total_points_awarded += result.points_awarded

        # Should have been rate limited
        assert (
            successful_awards <= 10
        ), f"Rate limiting failed: {successful_awards} > 10"

        # Verify balance matches successful awards only
        total_balance, _ = await points_engine_with_anti_abuse.get_user_balance(user_id)
        assert (
            total_balance == total_points_awarded
        ), f"Anti-abuse didn't prevent points inflation: {total_balance} vs {total_points_awarded}"

    @pytest.mark.asyncio
    async def test_force_award_bypasses_anti_abuse_safely(
        self, points_engine_with_anti_abuse
    ):
        """Test that force_award bypasses anti-abuse but maintains integrity."""
        user_id = 123

        # Trigger rate limiting first
        for i in range(12):
            await points_engine_with_anti_abuse.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message": f"spam_{i}"},
            )

        # Now force award should still work
        force_result = await points_engine_with_anti_abuse.award_points(
            user_id=user_id,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={"admin_id": 1, "reason": "Manual adjustment"},
            base_points=500,
            force_award=True,
        )

        assert force_result.success, "Force award should bypass anti-abuse"
        assert force_result.points_awarded == 500

        # Verify balance integrity maintained
        total_balance, _ = await points_engine_with_anti_abuse.get_user_balance(user_id)
        history = await points_engine_with_anti_abuse.get_transaction_history(
            user_id, limit=100
        )
        history_sum = sum(tx["points_awarded"] for tx in history)

        assert total_balance == history_sum, "Force award broke balance integrity"


class TestConcurrentOperationsSafety:
    """Test thread safety and concurrent operation handling."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine for concurrency testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()

        engine = PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )
        return engine

    @pytest.mark.asyncio
    async def test_massive_concurrent_operations_integrity(self, points_engine):
        """Test integrity under massive concurrent load."""
        user_id = 123
        num_tasks = 100
        points_per_task = 10

        # Create many concurrent operations
        async def award_task(task_id):
            return await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"task_id": task_id},
                base_points=points_per_task,
            )

        # Execute all tasks concurrently
        start_time = time.time()
        tasks = [award_task(i) for i in range(num_tasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Verify all operations succeeded
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert (
            len(successful_results) == num_tasks
        ), f"Concurrent operations failed: {len(successful_results)}/{num_tasks}"

        # Verify mathematical integrity
        total_balance, _ = await points_engine.get_user_balance(user_id)
        expected_total = sum(r.points_awarded for r in successful_results)
        assert (
            total_balance == expected_total
        ), f"Concurrent operation integrity violation: {total_balance} != {expected_total}"

        # Performance check: should complete in reasonable time
        duration = end_time - start_time
        assert duration < 5.0, f"Concurrent operations too slow: {duration}s"

    @pytest.mark.asyncio
    async def test_mixed_operations_concurrency(self, points_engine):
        """Test concurrent mix of awards, spends, and queries."""
        user_id = 123

        # Give initial points
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "initial"},
            base_points=2000,
        )

        # Mixed concurrent operations
        async def award_task():
            return await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={},
                base_points=10,
            )

        async def spend_task():
            return await points_engine.spend_points(
                user_id=user_id,
                amount=50,
                reason="Test spend",
            )

        async def query_task():
            return await points_engine.get_user_balance(user_id)

        # Create mixed operation tasks
        tasks = []
        for i in range(20):
            if i % 3 == 0:
                tasks.append(award_task())
            elif i % 3 == 1:
                tasks.append(spend_task())
            else:
                tasks.append(query_task())

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent operations failed: {exceptions}"

        # Final integrity check
        is_valid = await points_engine.verify_balance_integrity(user_id)
        assert is_valid, "Mixed concurrent operations broke integrity"
