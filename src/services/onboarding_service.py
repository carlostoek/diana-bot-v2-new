from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
import logging

logger = logging.getLogger(__name__)


class OnboardingService:
    """
    Service for handling user onboarding flows.
    """

    def __init__(self, bot: Bot):
        self._bot = bot

    async def send_welcome_message(self, user_id: int):
        """
        Sends a welcome message to a newly registered user.
        """
        text = (
            "🎉 Welcome to Diana Bot! 🎉\n\n"
            "We're so excited to have you on board. "
            "Get ready to explore a new world of interactive storytelling."
        )
        try:
            await self._bot.send_message(chat_id=user_id, text=text)
            logger.info(f"Sent welcome message to user {user_id}")
        except TelegramAPIError as e:
            logger.error(
                f"Failed to send welcome message to user {user_id}: {e}",
                exc_info=True,
            )
