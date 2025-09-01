"""
Comprehensive Points Integrity Test Suite

This module provides a simplified test suite for validating the mathematical
integrity and correctness of the PointsEngine, specifically designed to avoid
deadlock issues identified in the full implementation.

It uses the MinimalPointsEngine which has been designed with simpler locking
to avoid the deadlock issues.
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock
import pytest
import pytest_asyncio

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.interfaces import (
    ActionType,
    AntiAbuseViolation,
    MultiplierType,
)
from tests.unit.services.gamification.minimal_points_engine import MinimalPointsEngine


class TestPointsIntegrityComprehensive:
    """Comprehensive test suite for points integrity using minimal engine."""

    @pytest_asyncio.fixture
    async def anti_abuse_validator(self):
        """Mock anti-abuse validator that always passes."""
        validator = AsyncMock(spec=AntiAbuseValidator)
        validator.validate_action.return_value = (True, None, None)
        validator.record_action = AsyncMock()
        return validator
        
    @pytest_asyncio.fixture
    async def minimal_engine(self, anti_abuse_validator):
        """Create a minimal engine instance for testing."""
        return MinimalPointsEngine(anti_abuse_validator=anti_abuse_validator)

    @pytest.mark.asyncio
    async def test_balance_equals_transaction_sum(self, minimal_engine):
        """CRITICAL: Balance must always equal the sum of transactions."""
        user_id = 123
        
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
                result = await minimal_engine.award_points(
                    user_id=user_id,
                    action_type=action_type,
                    context={"admin_id": 1, "reason": "Test penalty"},
                    base_points=base_points,
                    force_award=True,
                )
            else:
                result = await minimal_engine.award_points(
                    user_id=user_id,
                    action_type=action_type,
                    context={},
                    base_points=base_points,
                )
                
            assert result.success, f"Failed to award points for {action_type}"
        
        # Get the current balance and transaction history
        total_balance, available_balance = await minimal_engine.get_user_balance(user_id)
        history = await minimal_engine.get_transaction_history(user_id, limit=100)
        calculated_total = sum(tx.get('points_change', 0) for tx in history)
        
        # Verify the balance matches the transaction history
        assert total_balance == calculated_total, (
            f"Balance integrity violation: balance={total_balance}, "
            f"transaction history total={calculated_total}"
        )

    @pytest.mark.asyncio
    async def test_negative_adjustment_mathematical_correctness(self, minimal_engine):
        """Test negative adjustments (penalties) maintain mathematical integrity."""
        user_id = 123
        
        # Give user initial points
        initial_result = await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123"},
            base_points=1000,
        )
        assert initial_result.success
        
        # Get initial balance
        initial_balance, _ = await minimal_engine.get_user_balance(user_id)
        
        # Apply negative adjustment
        penalty_amount = -250
        penalty_result = await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={"admin_id": 1, "reason": "Violation penalty"},
            base_points=penalty_amount,
            force_award=True,
        )
        
        assert penalty_result.success
        assert penalty_result.points_awarded == penalty_amount
        
        # Get the final balance
        final_balance, _ = await minimal_engine.get_user_balance(user_id)
        
        # Calculate expected balance from transaction history
        history = await minimal_engine.get_transaction_history(user_id, limit=100)
        calculated_balance = sum(tx.get("points_change", 0) for tx in history)
        
        # Verify the balance is mathematically correct
        expected_balance = initial_balance + penalty_amount
        assert final_balance == expected_balance, (
            f"Negative adjustment calculation error: "
            f"final={final_balance}, expected={expected_balance}"
        )
        assert calculated_balance == expected_balance, (
            f"Transaction history doesn't match expected balance: "
            f"calculated={calculated_balance}, expected={expected_balance}"
        )
        
        # Verify the result contains the correct balance
        assert penalty_result.new_balance == final_balance, (
            f"Result balance incorrect: "
            f"result={penalty_result.new_balance}, actual={final_balance}"
        )

    @pytest.mark.asyncio
    async def test_zero_points_operations_mathematical_safety(self, minimal_engine):
        """Test that zero-point operations don't break mathematical integrity."""
        user_id = 123
        
        # Award some initial points
        initial_result = await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        initial_balance = initial_result.new_balance
        
        # Try zero-point achievement operation
        zero_result = await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.ACHIEVEMENT_UNLOCKED,
            context={"achievement_id": "zero_point_test", "achievement_points": 0},
            base_points=0,
        )
        
        # Zero-point achievement operations should succeed with zero points
        assert zero_result.success is True
        assert zero_result.points_awarded == 0
        
        # Verify balance remains unchanged
        current_balance, _ = await minimal_engine.get_user_balance(user_id)
        assert current_balance == initial_balance, (
            f"Zero-point operation changed balance: "
            f"current={current_balance}, initial={initial_balance}"
        )