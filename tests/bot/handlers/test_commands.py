import pytest
from unittest.mock import AsyncMock
from src.bot.handlers.commands import start_handler, balance_handler
from src.bot.ui.keyboards import get_start_keyboard
from src.domain.models import User, Wallet


@pytest.mark.asyncio
async def test_start_handler():
    """
    Test that the start_handler function replies and calls the gamification service.
    """
    # Create mock objects
    mock_message = AsyncMock()
    mock_user = User(id=1, first_name="Testy")
    mock_gamification_service = AsyncMock()
    mock_uow = AsyncMock()

    # Call the handler
    await start_handler(mock_message, mock_user, mock_uow, mock_gamification_service)

    # Get the expected keyboard
    expected_keyboard = get_start_keyboard()

    # Assert that the gamification service was called
    mock_gamification_service.unlock_achievement.assert_called_once_with(
        mock_uow, mock_user.id, "First Steps"
    )

    # Assert that the reply method was called
    mock_message.reply.assert_called_once_with(
        f"Welcome back, {mock_user.first_name}! How can I help you today?",
        reply_markup=expected_keyboard,
    )


@pytest.mark.asyncio
async def test_balance_handler():
    """
    Test that the balance_handler function replies with the correct balance.
    """
    # Create mock objects
    mock_message = AsyncMock()
    mock_user = User(id=1, first_name="Testy")
    mock_gamification_service = AsyncMock()
    mock_uow = AsyncMock()
    mock_gamification_service.get_wallet_by_user_id.return_value = Wallet(balance=123)

    # Call the handler
    await balance_handler(mock_message, mock_user, mock_uow, mock_gamification_service)

    # Assert that the reply method was called
    mock_message.reply.assert_called_once_with(
        "Your current balance is: 123 Besitos 💋"
    )
