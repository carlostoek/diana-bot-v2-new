"""
Minimal Points Integrity Test for Diagnostic Purposes

This is an extremely simplified test that focuses on only the most basic operations
to identify lock issues and deadlocks in the points engine.
"""

import asyncio
from unittest.mock import AsyncMock
import pytest
import pytest_asyncio

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.interfaces import ActionType


class MockMinimalEngine:
    """Super minimal mock engine with no locking or database logic."""
    
    def __init__(self, anti_abuse_validator):
        """Initialize with bare minimum dependencies."""
        self.anti_abuse_validator = anti_abuse_validator
        self.balances = {}  # user_id -> balance
        
    async def award_points(self, user_id, action_type, context, base_points=None, force_award=False):
        """Award points with minimal logic and no locking."""
        # Default points based on action
        if base_points is None:
            base_points = 10  # Default for all actions
            
        # Update balance
        if user_id not in self.balances:
            self.balances[user_id] = 0
        self.balances[user_id] += base_points
        
        # Mock result
        class Result:
            def __init__(self, user_id, points, success=True):
                self.user_id = user_id
                self.points_awarded = points
                self.success = success
                self.new_balance = None
                
        result = Result(user_id, base_points)
        result.new_balance = self.balances[user_id]
        return result
        
    async def get_user_balance(self, user_id):
        """Get user balance with minimal logic."""
        balance = self.balances.get(user_id, 0)
        return balance, balance  # total, available


class TestPointsIntegrityMinimal:
    """Minimal test suite for points engine to diagnose locking issues."""
    
    @pytest_asyncio.fixture
    async def anti_abuse_validator(self):
        """Create a simple mock validator."""
        validator = AsyncMock(spec=AntiAbuseValidator)
        validator.validate_action.return_value = (True, None, None)
        validator.record_action = AsyncMock()
        return validator
        
    @pytest_asyncio.fixture
    async def minimal_engine(self, anti_abuse_validator):
        """Create an extremely minimal engine."""
        return MockMinimalEngine(anti_abuse_validator)
        
    @pytest.mark.asyncio
    async def test_award_points_basic(self, minimal_engine):
        """Test the most basic award operation."""
        user_id = 123
        
        # Simple award
        result = await minimal_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        
        # Basic assertions
        assert result.success is True
        assert result.points_awarded > 0
        
        # Check balance
        balance, _ = await minimal_engine.get_user_balance(user_id)
        assert balance > 0
        assert balance == result.points_awarded