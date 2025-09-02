from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications to users.
    """

    def __init__(self, bot: Bot):
        self._bot = bot

    async def send_achievement_unlocked_notification(
        self,
        user_id: int,
        achievement_name: str,
        reward_points: int,
    ):
        """
        Notifies a user that they have unlocked an achievement.
        """
        text = (
            f"🏆 Achievement Unlocked! 🏆\n\n"
            f"You've unlocked: **{achievement_name}**\n"
            f"You've earned {reward_points} Besitos! 💋"
        )
        try:
            # Using MarkdownV2 parse mode for bold text
            await self._bot.send_message(chat_id=user_id, text=text, parse_mode="MarkdownV2")
            logger.info(f"Sent achievement notification to user {user_id} for '{achievement_name}'")
        except TelegramAPIError as e:
            logger.error(
                f"Failed to send achievement notification to user {user_id}: {e}",
                exc_info=True,
            )
