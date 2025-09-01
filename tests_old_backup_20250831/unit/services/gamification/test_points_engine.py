"""
Unit Tests for PointsEngine

Tests the core points calculation and transaction engine with emphasis on:
- Atomic transaction integrity
- Anti-abuse integration
- Multiplier calculations
- Balance integrity verification
- Error handling and edge cases
- Performance requirements (<100ms latency)
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine import PointsEngine, PointsEngineError
from services.gamification.interfaces import (
    ActionType,
    AntiAbuseViolation,
    MultiplierType,
)
from services.gamification.models import PointsTransaction, UserGamification


class TestPointsEngineCore:
    """Test core PointsEngine functionality."""

    @pytest_asyncio.fixture
    async def anti_abuse_validator(self):
        """Mock anti-abuse validator."""
        validator = AsyncMock(spec=AntiAbuseValidator)
        validator.validate_action.return_value = (True, None, None)
        validator.record_action = AsyncMock()
        return validator

    @pytest_asyncio.fixture
    async def points_engine(self, anti_abuse_validator):
        """Create PointsEngine instance for testing."""
        engine = PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,  # Use in-memory for testing
        )
        return engine

    @pytest.mark.asyncio
    async def test_award_points_basic_success(self, points_engine):
        """Test basic successful points award."""
        user_id = 123
        action_type = ActionType.DAILY_LOGIN
        context = {"ip_address": "127.0.0.1"}

        result = await points_engine.award_points(
            user_id=user_id,
            action_type=action_type,
            context=context,
        )

        assert result.success is True
        assert result.user_id == user_id
        assert result.action_type == action_type
        assert result.points_awarded == 50  # Default for DAILY_LOGIN
        assert result.base_points == 50
        assert result.new_balance == 50
        assert result.transaction_id is not None

    @pytest.mark.asyncio
    async def test_award_points_with_multipliers(self, points_engine):
        """Test points award with multiplier calculations."""
        user_id = 123

        # First, give user some points to establish level
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123", "amount": 100},
        )

        # Set VIP multiplier
        user_data = await points_engine._get_or_create_user_data(user_id)
        user_data.vip_multiplier = 1.5
        user_data.current_streak = 10  # Should give streak bonus

        result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"correct_answer": True},
        )

        assert result.success is True
        assert result.points_awarded > result.base_points  # Should have multipliers
        assert MultiplierType.VIP_BONUS in result.multipliers_applied
        assert MultiplierType.STREAK_BONUS in result.multipliers_applied

    @pytest.mark.asyncio
    async def test_award_points_anti_abuse_rejection(
        self, points_engine, anti_abuse_validator
    ):
        """Test points award rejection by anti-abuse system."""
        anti_abuse_validator.validate_action.return_value = (
            False,
            AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
            "Too many requests",
        )

        result = await points_engine.award_points(
            user_id=123,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        assert result.success is False
        assert result.violation == AntiAbuseViolation.RATE_LIMIT_EXCEEDED
        assert result.error_message == "Too many requests"
        assert result.points_awarded == 0

    @pytest.mark.asyncio
    async def test_award_points_force_award_bypasses_anti_abuse(
        self, points_engine, anti_abuse_validator
    ):
        """Test force_award bypasses anti-abuse validation."""
        anti_abuse_validator.validate_action.return_value = (
            False,
            AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
            "Too many requests",
        )

        result = await points_engine.award_points(
            user_id=123,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={"admin_id": 1, "reason": "Test adjustment"},
            base_points=100,
            force_award=True,
        )

        assert result.success is True
        assert result.points_awarded == 100
        # Anti-abuse validation should not have been called
        anti_abuse_validator.validate_action.assert_not_called()

    @pytest.mark.asyncio
    async def test_award_points_custom_base_points(self, points_engine):
        """Test points award with custom base points override."""
        result = await points_engine.award_points(
            user_id=123,
            action_type=ActionType.ACHIEVEMENT_UNLOCKED,
            context={"achievement_id": "test"},
            base_points=500,
        )

        assert result.success is True
        assert result.base_points == 500
        assert result.points_awarded >= 500  # Might have multipliers

    @pytest.mark.asyncio
    async def test_get_user_balance_new_user(self, points_engine):
        """Test getting balance for new user."""
        total, available = await points_engine.get_user_balance(999)

        assert total == 0
        assert available == 0

    @pytest.mark.asyncio
    async def test_get_user_balance_existing_user(self, points_engine):
        """Test getting balance for user with points."""
        user_id = 123

        # Award some points
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        total, available = await points_engine.get_user_balance(user_id)

        assert total == 50  # DAILY_LOGIN base points
        assert available == 50

    @pytest.mark.asyncio
    async def test_spend_points_success(self, points_engine):
        """Test successful points spending."""
        user_id = 123

        # Give user some points first
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123", "amount": 100},
        )

        # Spend some points
        success = await points_engine.spend_points(
            user_id=user_id,
            amount=500,
            reason="Test purchase",
        )

        assert success is True

        # Check balance
        total, available = await points_engine.get_user_balance(user_id)
        assert total == 1000  # Total unchanged
        assert available == 500  # Available reduced

    @pytest.mark.asyncio
    async def test_spend_points_insufficient_balance(self, points_engine):
        """Test spending more points than available."""
        user_id = 123

        # Give user some points
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        # Try to spend more than available
        success = await points_engine.spend_points(
            user_id=user_id,
            amount=100,
            reason="Test purchase",
        )

        assert success is False

        # Balance should be unchanged
        total, available = await points_engine.get_user_balance(user_id)
        assert total == 50
        assert available == 50

    @pytest.mark.asyncio
    async def test_spend_points_invalid_amount(self, points_engine):
        """Test spending invalid amount."""
        with pytest.raises(ValueError, match="Spend amount must be positive"):
            await points_engine.spend_points(
                user_id=123,
                amount=-10,
                reason="Invalid",
            )

        with pytest.raises(ValueError, match="Spend amount must be positive"):
            await points_engine.spend_points(
                user_id=123,
                amount=0,
                reason="Invalid",
            )

    @pytest.mark.asyncio
    async def test_get_transaction_history(self, points_engine):
        """Test retrieving transaction history."""
        user_id = 123

        # Create several transactions
        for i in range(5):
            await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": f"msg_{i}"},
            )

        # Get transaction history
        history = await points_engine.get_transaction_history(user_id, limit=3)

        assert len(history) == 3  # Limited to 3
        assert all(tx["user_id"] == user_id for tx in history)

        # Should be sorted by timestamp (newest first)
        timestamps = [tx["timestamp"] for tx in history]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_get_transaction_history_with_filters(self, points_engine):
        """Test transaction history with filters."""
        user_id = 123

        # Create different types of transactions
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={},
        )

        # Filter by action type
        history = await points_engine.get_transaction_history(
            user_id=user_id,
            action_types=[ActionType.DAILY_LOGIN],
        )

        assert len(history) == 1
        assert history[0]["action_type"] == ActionType.DAILY_LOGIN.value

    @pytest.mark.asyncio
    async def test_calculate_multipliers_vip_user(self, points_engine):
        """Test multiplier calculation for VIP user."""
        user_id = 123

        # Set up user as VIP with streak
        user_data = await points_engine._get_or_create_user_data(user_id)
        user_data.vip_multiplier = 1.5
        user_data.current_streak = 10
        user_data.level = 5

        multipliers = await points_engine.calculate_multipliers(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"event_multiplier": 2.0},
        )

        assert MultiplierType.VIP_BONUS in multipliers
        assert multipliers[MultiplierType.VIP_BONUS] == 1.5

        assert MultiplierType.STREAK_BONUS in multipliers
        assert multipliers[MultiplierType.STREAK_BONUS] == 1.2  # 10-day streak

        assert MultiplierType.LEVEL_BONUS in multipliers
        assert multipliers[MultiplierType.LEVEL_BONUS] == 1.2  # Level 5 bonus

        assert MultiplierType.EVENT_BONUS in multipliers
        assert multipliers[MultiplierType.EVENT_BONUS] == 2.0

    @pytest.mark.asyncio
    async def test_verify_balance_integrity_success(self, points_engine):
        """Test balance integrity verification success."""
        user_id = 123

        # Create some transactions
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={},
        )

        # Verify integrity
        is_valid = await points_engine.verify_balance_integrity(user_id)
        assert is_valid is True


class TestPointsEngineEdgeCases:
    """Test edge cases and error conditions."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine for edge case testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)

        return PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )

    @pytest.mark.asyncio
    async def test_award_points_negative_adjustment(self, points_engine):
        """Test admin adjustment with negative points."""
        user_id = 123

        # Give user some points first
        await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123", "amount": 100},
        )

        # Apply negative adjustment
        result = await points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={"admin_id": 1, "reason": "Penalty", "adjustment_amount": -200},
            base_points=-200,
            force_award=True,
        )

        assert result.success is True
        assert result.points_awarded == -200
        assert result.new_balance == 800  # 1000 - 200

    @pytest.mark.asyncio
    async def test_award_points_zero_points(self, points_engine):
        """Test awarding zero points."""
        result = await points_engine.award_points(
            user_id=123,
            action_type=ActionType.ACHIEVEMENT_UNLOCKED,
            context={"achievement_points": 0},
            base_points=0,
        )

        assert result.success is False
        assert result.points_awarded == 0

    @pytest.mark.asyncio
    async def test_concurrent_points_operations(self, points_engine):
        """Test concurrent points operations for race condition safety."""
        user_id = 123

        # Create multiple concurrent operations
        tasks = []
        for i in range(10):
            task = points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": f"msg_{i}"},
            )
            tasks.append(task)

        # Wait for all operations to complete
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert all(result.success for result in results)

        # Final balance should be correct
        total, available = await points_engine.get_user_balance(user_id)
        expected_total = 10 * 5  # 10 messages * 5 points each
        assert total == expected_total
        assert available == expected_total

    @pytest.mark.asyncio
    async def test_performance_award_points_latency(self, points_engine):
        """Test that points award meets <100ms latency requirement."""
        import time

        user_id = 123

        # Measure latency for multiple operations
        latencies = []
        for i in range(10):
            start_time = time.time()

            result = await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": f"msg_{i}"},
            )

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            assert result.success is True

        # Check performance requirements
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(0.95 * len(latencies))]

        assert avg_latency < 100, f"Average latency {avg_latency}ms > 100ms"
        assert p95_latency < 100, f"95th percentile latency {p95_latency}ms > 100ms"

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, points_engine):
        """Test transaction rollback on errors."""
        user_id = 123

        # Mock database error during transaction
        original_persist = points_engine._persist_transaction
        points_engine._persist_transaction = AsyncMock(
            side_effect=Exception("DB Error")
        )

        initial_balance = (await points_engine.get_user_balance(user_id))[0]

        with pytest.raises(PointsEngineError):
            await points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.DAILY_LOGIN,
                context={},
            )

        # Balance should be unchanged after rollback
        final_balance = (await points_engine.get_user_balance(user_id))[0]
        assert final_balance == initial_balance

        # Restore original method
        points_engine._persist_transaction = original_persist


class TestPointsEngineMultipliers:
    """Test multiplier calculations in detail."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine for multiplier testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)

        return PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )

    @pytest.mark.asyncio
    async def test_streak_multiplier_calculation(self, points_engine):
        """Test streak multiplier calculation logic."""
        # Test different streak lengths
        assert points_engine._calculate_streak_multiplier(0) == 1.0
        assert points_engine._calculate_streak_multiplier(2) == 1.0
        assert points_engine._calculate_streak_multiplier(3) == 1.1
        assert points_engine._calculate_streak_multiplier(7) == 1.2
        assert points_engine._calculate_streak_multiplier(14) == 1.3
        assert points_engine._calculate_streak_multiplier(30) == 1.5
        assert points_engine._calculate_streak_multiplier(100) == 1.5

    @pytest.mark.asyncio
    async def test_apply_multipliers_calculation(self, points_engine):
        """Test multiplier application logic."""
        base_points = 100

        # Test single multiplier
        multipliers = {MultiplierType.VIP_BONUS: 1.5}
        result = points_engine._apply_multipliers(base_points, multipliers)
        assert result == 150

        # Test multiple multipliers
        multipliers = {
            MultiplierType.VIP_BONUS: 1.5,
            MultiplierType.STREAK_BONUS: 1.2,
            MultiplierType.EVENT_BONUS: 2.0,
        }
        result = points_engine._apply_multipliers(base_points, multipliers)
        assert result == int(100 * 1.5 * 1.2 * 2.0)  # 360

        # Test with zero points
        result = points_engine._apply_multipliers(0, multipliers)
        assert result == 0

        # Test with negative points (should not apply multipliers)
        result = points_engine._apply_multipliers(-100, multipliers)
        assert result == -100

    @pytest.mark.asyncio
    async def test_base_points_calculation_trivia(self, points_engine):
        """Test base points calculation for trivia events."""
        # Correct answer with difficulty
        context = {"correct_answer": True, "difficulty": "hard"}
        base_points = points_engine._calculate_base_points(
            ActionType.TRIVIA_COMPLETED, context
        )
        assert base_points == int(100 * 2.0)  # Hard difficulty 2x multiplier

        # Easy difficulty
        context = {"correct_answer": True, "difficulty": "easy"}
        base_points = points_engine._calculate_base_points(
            ActionType.TRIVIA_COMPLETED, context
        )
        assert base_points == 100  # Easy difficulty 1x multiplier

        # Wrong answer
        context = {"correct_answer": False}
        base_points = points_engine._calculate_base_points(
            ActionType.TRIVIA_COMPLETED, context
        )
        assert base_points == 100  # Base points regardless of correctness


class TestPointsEngineMetrics:
    """Test performance metrics and monitoring."""

    @pytest_asyncio.fixture
    async def points_engine(self):
        """Create PointsEngine for metrics testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)

        return PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )

    @pytest.mark.asyncio
    async def test_performance_metrics_tracking(self, points_engine):
        """Test that performance metrics are properly tracked."""
        # Reset metrics
        await points_engine.reset_metrics()

        initial_metrics = points_engine.get_performance_metrics()
        assert initial_metrics["total_operations"] == 0
        assert initial_metrics["successful_operations"] == 0

        # Perform successful operation
        result = await points_engine.award_points(
            user_id=123,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        assert result.success is True

        # Check metrics updated
        metrics = points_engine.get_performance_metrics()
        assert metrics["total_operations"] == 1
        assert metrics["successful_operations"] == 1
        assert metrics["failed_operations"] == 0
        assert metrics["total_points_awarded"] == 50
        assert metrics["avg_operation_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_metrics_failure_tracking(self, points_engine, anti_abuse_validator):
        """Test failure metrics tracking."""
        # Reset metrics
        await points_engine.reset_metrics()

        # Force a failure
        anti_abuse_validator.validate_action.return_value = (
            False,
            AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
            "Rate limited",
        )

        result = await points_engine.award_points(
            user_id=123,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        assert result.success is False

        # Check failure metrics
        metrics = points_engine.get_performance_metrics()
        assert metrics["total_operations"] == 1
        assert metrics["successful_operations"] == 0
        assert metrics["failed_operations"] == 1
        assert metrics["total_points_awarded"] == 0
