"""
Tests for main application entry point.
"""

import pytest
from unittest.mock import patch
from src.main import main


from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_main_function_runs_without_error():
    """
    Test that the main function runs without raising an exception.
    We patch the Redis client's ping method and the event publisher to avoid network calls.
    """
    with patch("redis.asyncio.Redis.ping", new_callable=AsyncMock, return_value=True) as mock_ping, \
         patch("src.infrastructure.event_bus.EventPublisher.publish", new_callable=AsyncMock) as mock_publish:

        await main()

        mock_ping.assert_called_once()
        mock_publish.assert_called_once()
        # The main assertion is that no exception was raised
        assert True
