"""
Tests for main application entry point.
"""

import pytest
import asyncio
from unittest.mock import patch
from src.main import main


from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_main_function_runs_without_error(monkeypatch):
    """
    Test that the main function runs without raising an exception.
    We patch network calls and external dependencies.
    """
    # Patch the bot token to be a valid format
    monkeypatch.setattr("src.config.settings.TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

    # Patch the bot's start_polling and the event_listener to prevent them from running
    with patch("src.main.start_bot", new_callable=AsyncMock) as mock_start_bot, \
         patch("src.main.event_listener", new_callable=AsyncMock) as mock_event_listener:

        # Make the mocks block forever so we can test cancellation
        async def endless_wait(*args, **kwargs):
            await asyncio.Event().wait()

        mock_start_bot.side_effect = endless_wait
        mock_event_listener.side_effect = endless_wait

        # We need to run main() in a way that it can be cancelled
        main_task = asyncio.create_task(main())
        await asyncio.sleep(0.1)  # allow the task to start
        main_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await main_task

        # Check that our main components were called
        mock_start_bot.assert_called_once()
        mock_event_listener.assert_called_once()
        # The main assertion is that the setup ran without other exceptions
        assert True
