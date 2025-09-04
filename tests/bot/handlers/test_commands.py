import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import InlineKeyboardMarkup
from src.bot.handlers.commands import start_handler, balance_handler
from src.domain.models import User, Wallet, UserProfile, UserMood, UserArchetype


@pytest.mark.asyncio
async def test_start_handler():
    """
    Test that the start_handler function provides a personalized experience.
    """
    # Create mock objects
    mock_message = AsyncMock()
    mock_user = User(id=1, first_name="Testy")
    mock_profile = UserProfile(
        user_id=1,
        mood=UserMood.CURIOUS,
        archetype=UserArchetype.EXPLORER,
    )
    mock_uow = MagicMock()
    mock_uow.user_profiles.get = AsyncMock(return_value=mock_profile)
    mock_gamification_service = AsyncMock()
    mock_context_service = AsyncMock()
    mock_personalization_service = AsyncMock()
    mock_personalization_service.generate_adaptive_message.return_value = (
        "Personalized Message"
    )

    # Call the handler
    await start_handler(
        mock_message,
        mock_user,
        mock_uow,
        mock_gamification_service,
        mock_context_service,
        mock_personalization_service,
    )

    # Assert that the context and personalization services were called
    mock_context_service.detect_user_mood.assert_called_once_with(mock_profile)
    mock_context_service.classify_user_archetype.assert_called_once_with(mock_profile)
    mock_personalization_service.generate_adaptive_message.assert_called_once_with(
        mock_profile
    )

    # Assert that the reply method was called with a personalized message and a keyboard
    mock_message.reply.assert_called_once()
    args, kwargs = mock_message.reply.call_args
    assert args[0] == "Personalized Message"
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)


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
