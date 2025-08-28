"""
Tests for Ultra-Minimal Points Engine

These tests focus on the core mathematical integrity of points operations
without the complexity of locks, transactions, or database operations.
"""

import asyncio
from unittest.mock import AsyncMock
import pytest
import pytest_asyncio

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.interfaces import ActionType
from tests.unit.services.gamification.ultra_minimal_engine import UltraMinimalEngine


class TestUltraMinimalEngine:
    """Test suite for the ultra-minimal points engine."""
    
    @pytest_asyncio.fixture
    async def engine(self):
        """Create an ultra-minimal engine for testing."""
        return UltraMinimalEngine()
    
    @pytest.mark.asyncio
    async def test_basic_award(self, engine):
        """Test that basic point awards work correctly."""
        user_id = 123
        
        # Award points
        result = await engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        
        # Check result
        assert result.success is True
        assert result.points_awarded > 0
        
        # Check balance
        total, available = await engine.get_user_balance(user_id)
        assert total > 0
        assert available > 0
        assert total == result.points_awarded
    
    @pytest.mark.asyncio
    async def test_balance_equals_transaction_sum(self, engine):
        """CRITICAL: Balance must always equal the sum of transactions."""
        user_id = 123
        
        # Perform various operations
        operations = [
            (ActionType.DAILY_LOGIN, 50),
            (ActionType.TRIVIA_COMPLETED, 100),
            (ActionType.MESSAGE_SENT, 5),
            (ActionType.VIP_PURCHASE, 1000),
            (ActionType.ADMIN_ADJUSTMENT, -200),  # Penalty
        ]
        
        for action_type, base_points in operations:
            await engine.award_points(
                user_id=user_id,
                action_type=action_type,
                context={},
                base_points=base_points,
            )
        
        # Get balance and transaction history
        total_balance, _ = await engine.get_user_balance(user_id)
        history = await engine.get_transaction_history(user_id)
        calculated_total = sum(tx.get("points_change", 0) for tx in history)
        
        # Ensure we don't go negative in calculation
        if calculated_total < 0:
            calculated_total = 0
            
        # Verify balance equals transaction sum
        assert total_balance == calculated_total, (
            f"Balance integrity violation: balance={total_balance}, "
            f"transaction history total={calculated_total}"
        )
    
    @pytest.mark.asyncio
    async def test_negative_adjustment_mathematical_correctness(self, engine):
        """Test negative adjustments maintain mathematical integrity."""
        user_id = 123
        
        # Give initial points
        await engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={},
            base_points=1000,
        )
        
        # Get initial balance
        initial_balance, _ = await engine.get_user_balance(user_id)
        
        # Apply negative adjustment
        penalty_amount = -200
        await engine.award_points(
            user_id=user_id,
            action_type=ActionType.ADMIN_ADJUSTMENT,
            context={"reason": "Penalty"},
            base_points=penalty_amount,
        )
        
        # Get final balance
        final_balance, _ = await engine.get_user_balance(user_id)
        
        # Calculate expected result
        expected_balance = max(0, initial_balance + penalty_amount)
        
        # Verify balance is correct
        assert final_balance == expected_balance, (
            f"Negative adjustment calculation error: "
            f"final={final_balance}, expected={expected_balance}"
        )
    
    @pytest.mark.asyncio
    async def test_spend_points(self, engine):
        """Test spending points from available balance."""
        user_id = 123
        
        # Give initial points
        await engine.award_points(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={},
            base_points=1000,
        )
        
        # Spend some points
        success = await engine.spend_points(
            user_id=user_id,
            amount=300,
            reason="Test purchase",
        )
        
        # Verify success
        assert success is True
        
        # Check updated balance
        total, available = await engine.get_user_balance(user_id)
        assert total == 1000  # Total shouldn't change
        assert available == 700  # Available should decrease
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, engine):
        """Test that concurrent operations maintain integrity."""
        user_ids = [101, 102, 103]
        operations_per_user = 5
        
        # Create tasks for concurrent execution
        tasks = []
        for user_id in user_ids:
            for i in range(operations_per_user):
                tasks.append(
                    engine.award_points(
                        user_id=user_id,
                        action_type=ActionType.MESSAGE_SENT,
                        context={"message_id": f"msg_{i}"},
                        base_points=10,
                    )
                )
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all operations succeeded
        assert all(result.success for result in results)
        
        # Verify balance integrity for each user
        for user_id in user_ids:
            # Check balance equals transaction sum
            total, _ = await engine.get_user_balance(user_id)
            history = await engine.get_transaction_history(user_id)
            calculated_total = sum(tx["points_change"] for tx in history)
            
            assert total == calculated_total, (
                f"Balance integrity violation for user {user_id}: "
                f"balance={total}, calculated={calculated_total}"
            )
            
            # Check expected amount (5 operations * 10 points)
            expected = operations_per_user * 10
            assert total == expected, (
                f"Unexpected balance for user {user_id}: "
                f"got {total}, expected {expected}"
            )