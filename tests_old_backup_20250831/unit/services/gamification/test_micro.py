"""
Micro-test for diagnosing PointsEngine issues
"""

import asyncio
from unittest.mock import AsyncMock, Mock
import pytest

from services.gamification.interfaces import ActionType


class TestMicro:
    """Micro tests to diagnose fundamental issues."""
    
    @pytest.mark.asyncio
    async def test_simple_async_function(self):
        """Test that the test infrastructure works with simple async functions."""
        # Simple async function
        async def simple_func():
            return 42
            
        # This should work without any issues
        result = await simple_func()
        assert result == 42
    
    @pytest.mark.asyncio
    async def test_async_with_mock(self):
        """Test that async mocks work as expected."""
        # Create a mock
        mock = AsyncMock()
        mock.return_value = 42
        
        # Call the mock
        result = await mock()
        assert result == 42
        assert mock.called