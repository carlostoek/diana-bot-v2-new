import pytest
from unittest.mock import AsyncMock, MagicMock

from src.telegram_adapter.handlers.start import handle_start
from src.telegram_adapter.keyboards.start_keyboard import get_start_keyboard
from src.modules.user.models import User

def test_get_start_keyboard():
    """
    Tests that the start keyboard factory creates the correct keyboard.
    """
    keyboard = get_start_keyboard()
    assert keyboard is not None
    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[0][0].text == "Check out the project!"
    assert keyboard.inline_keyboard[1][0].text == "Learn more"

@pytest.mark.asyncio
async def test_handle_start():
    """
    Tests the /start command handler.
    """
    # Arrange
    mock_user_service = AsyncMock()
    mock_user_service.find_or_create_user.return_value = User(
        id=123,
        first_name="Test",
        last_name="User",
        username="testuser",
        role="free",
        is_admin=False
    )

    mock_message = MagicMock()
    mock_message.from_user.id = 123
    mock_message.from_user.first_name = "Test"
    mock_message.from_user.last_name = "User"
    mock_message.from_user.username = "testuser"
    mock_message.reply = AsyncMock()

    # Act
    await handle_start(mock_message, user_service=mock_user_service)

    # Assert
    mock_user_service.find_or_create_user.assert_called_once_with(
        user_id=123,
        first_name="Test",
        last_name="User",
        username="testuser",
    )

    mock_message.reply.assert_called_once()
    # Check that the reply text is correct
    assert "Hello, Test!" in mock_message.reply.call_args[0][0]
    # Check that the keyboard was sent
    assert "reply_markup" in mock_message.reply.call_args[1]
