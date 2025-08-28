"""
Diagnostic test for PointsEngine problems
"""

import asyncio
from unittest.mock import AsyncMock
import pytest
import pytest_asyncio

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine import PointsEngine
from services.gamification.interfaces import ActionType


class TestDiagnostic:
    """Minimal diagnostic tests to identify issues with PointsEngine."""

    @pytest_asyncio.fixture
    async def simple_points_engine(self):
        """Create a simple PointsEngine with minimal configuration."""
        validator = AsyncMock(spec=AntiAbuseValidator)
        validator.validate_action.return_value = (True, None, None)
        validator.record_action = AsyncMock()
        
        engine = PointsEngine(
            anti_abuse_validator=validator,
            database_client=None,
            enable_balance_verification=False,  # Disable for faster execution
            enable_transaction_logging=False,   # Disable for faster execution
        )
        return engine

    @pytest.mark.asyncio
    async def test_basic_award(self, simple_points_engine):
        """Test most basic award operation."""
        user_id = 123
        
        # Make a simple award
        result = await simple_points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        
        # Check basic expectations
        assert result.success is True
        assert result.points_awarded > 0
        assert result.user_id == user_id
        assert result.action_type == ActionType.DAILY_LOGIN

    @pytest.mark.asyncio
    async def test_award_with_custom_points(self, simple_points_engine):
        """Test award with explicitly specified points."""
        user_id = 123
        base_points = 42
        
        # Award explicit points
        result = await simple_points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.MESSAGE_SENT,
            context={},
            base_points=base_points,
        )
        
        # Check points were awarded correctly
        assert result.success is True
        assert result.base_points == base_points
        
    @pytest.mark.asyncio
    async def test_get_balance(self, simple_points_engine):
        """Test that get_user_balance returns a valid result."""
        user_id = 123
        
        # Get balance for a new user
        total, available = await simple_points_engine.get_user_balance(user_id)
        
        # Should start with zero
        assert total == 0
        assert available == 0
        
        # Award points
        await simple_points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        
        # Check balance increased
        new_total, new_available = await simple_points_engine.get_user_balance(user_id)
        assert new_total > 0
        assert new_available > 0