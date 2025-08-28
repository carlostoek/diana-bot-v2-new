"""
ULTRA MINIMAL DIAGNOSIS - DEADLOCK DETECTION
===========================================

Isolate the specific deadlock issue in the points engine.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine import PointsEngine
from services.gamification.interfaces import ActionType


class TestDeadlockDiagnosis:
    """Minimal tests to isolate deadlock issues."""

    @pytest_asyncio.fixture
    async def engine_with_failing_validator(self):
        """Create engine with failing anti-abuse validator to trigger _get_user_total_points."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        # Make validator fail to trigger the error path
        anti_abuse_validator.validate_action.return_value = (False, None, "Test failure")
        anti_abuse_validator.record_action = AsyncMock()
        
        return PointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )

    @pytest.mark.asyncio
    async def test_deadlock_in_error_path(self, engine_with_failing_validator):
        """Test if the error path creates a deadlock."""
        import asyncio
        
        # This should trigger the error path which calls _get_user_total_points
        # from within the locked context, potentially causing deadlock
        
        try:
            result = await asyncio.wait_for(
                engine_with_failing_validator.award_points(
                    user_id=1,
                    action_type=ActionType.DAILY_LOGIN,
                    context={}
                ),
                timeout=1.0  # Very short timeout
            )
            
            # If we get here, no deadlock occurred
            assert result.success is False, "Expected validation failure"
            print("✅ No deadlock detected - validation error path works")
            
        except asyncio.TimeoutError:
            pytest.fail("❌ DEADLOCK DETECTED: _get_user_total_points called from locked context")

    @pytest.mark.asyncio  
    async def test_simple_lock_acquisition(self):
        """Test basic lock acquisition without engine complexity."""
        import asyncio
        
        # Simple test of asyncio lock behavior
        lock = asyncio.Lock()
        
        async def simple_locked_operation():
            async with lock:
                await asyncio.sleep(0.001)  # Minimal delay
                return "success"
        
        try:
            result = await asyncio.wait_for(
                simple_locked_operation(),
                timeout=0.1
            )
            assert result == "success"
            print("✅ Basic asyncio locks work correctly")
        except asyncio.TimeoutError:
            pytest.fail("❌ Basic asyncio lock failed - environment issue")

    @pytest.mark.asyncio
    async def test_nested_lock_deadlock_simulation(self):
        """Simulate the nested lock issue in the points engine."""
        import asyncio
        
        lock = asyncio.Lock()
        
        async def get_data_without_lock():
            # This simulates _get_or_create_user_data when called from error path
            return {"user_id": 1, "points": 0}
        
        async def get_total_points():
            # This simulates _get_user_total_points (NO LOCK)
            data = await get_data_without_lock()
            return data["points"]
        
        async def award_points_with_error():
            async with lock:  # Main lock acquired
                # Simulate validation failure path
                total_points = await get_total_points()  # This should NOT cause deadlock
                return {"success": False, "balance": total_points}
        
        try:
            result = await asyncio.wait_for(
                award_points_with_error(),
                timeout=0.1
            )
            assert result["success"] is False
            print("✅ Nested operation simulation works - no deadlock")
        except asyncio.TimeoutError:
            pytest.fail("❌ Nested lock simulation deadlocked")