import pytest
from unittest.mock import AsyncMock
from aiogram.types import Update, Message, Chat, User
from src.bot.handlers.errors import error_handler


from datetime import datetime

from unittest.mock import patch

@pytest.mark.asyncio
async def test_error_handler():
    """
    Test that the error_handler function replies to the user.
    """
    message = Message(
        message_id=1,
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="Test"),
        date=datetime.now()
    )
    mock_update = Update(update_id=1, message=message)
    mock_event = AsyncMock()
    mock_event.update = mock_update
    mock_event.exception = Exception("Test error")

    with patch.object(Message, "reply", new_callable=AsyncMock) as mock_reply:
        await error_handler(mock_event)
        mock_reply.assert_called_once_with(
            "Sorry, something went wrong on our end. We've been notified."
        )
