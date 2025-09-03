import pytest
from unittest.mock import AsyncMock
from src.services.notification_service import NotificationService
from src.services.onboarding_service import OnboardingService


@pytest.fixture
def mock_bot():
    return AsyncMock()


@pytest.mark.asyncio
async def test_onboarding_service(mock_bot):
    """
    Test that OnboardingService calls bot.send_message correctly.
    """
    service = OnboardingService(mock_bot)
    await service.send_welcome_message(user_id=123)

    mock_bot.send_message.assert_called_once()
    assert mock_bot.send_message.call_args.kwargs["chat_id"] == 123
    assert "Welcome to Diana Bot!" in mock_bot.send_message.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_notification_service(mock_bot):
    """
    Test that NotificationService calls bot.send_message correctly.
    """
    service = NotificationService(mock_bot)
    await service.send_achievement_unlocked_notification(
        user_id=123,
        achievement_name="Test Achievement",
        reward_points=100
    )

    mock_bot.send_message.assert_called_once()
    assert mock_bot.send_message.call_args.kwargs["chat_id"] == 123
    assert "Achievement Unlocked!" in mock_bot.send_message.call_args.kwargs["text"]
    assert "Test Achievement" in mock_bot.send_message.call_args.kwargs["text"]
