import pytest
from unittest.mock import AsyncMock
from src.bot.handlers.commands import start_handler
from src.bot.ui.keyboards import get_start_keyboard


@pytest.mark.asyncio
async def test_start_handler():
    """
    Test that the start_handler function replies with the correct text and keyboard.
    """
    # Create a mock message object
    mock_message = AsyncMock()

    # Call the handler
    await start_handler(mock_message)

    # Get the expected keyboard
    expected_keyboard = get_start_keyboard()

    # Assert that the reply method was called with the correct arguments
    mock_message.reply.assert_called_once_with(
        "Welcome to Diana Bot! How can I help you today?",
        reply_markup=expected_keyboard,
    )
