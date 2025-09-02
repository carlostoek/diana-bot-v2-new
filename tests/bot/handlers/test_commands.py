import pytest
from unittest.mock import AsyncMock
from src.bot.handlers.commands import start_handler
from src.bot.ui.keyboards import get_start_keyboard


from src.domain.models import User


@pytest.mark.asyncio
async def test_start_handler():
    """
    Test that the start_handler function replies with the correct text and keyboard.
    """
    # Create mock objects
    mock_message = AsyncMock()
    mock_user = User(id=1, first_name="Testy")

    # Call the handler
    await start_handler(mock_message, mock_user)

    # Get the expected keyboard
    expected_keyboard = get_start_keyboard()

    # Assert that the reply method was called with the correct arguments
    mock_message.reply.assert_called_once_with(
        f"Welcome back, {mock_user.first_name}! How can I help you today?",
        reply_markup=expected_keyboard,
    )
