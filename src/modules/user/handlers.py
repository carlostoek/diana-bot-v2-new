import logging
from src.core.interfaces import IEvent

logger = logging.getLogger(__name__)

async def user_registered_handler(event: IEvent):
    """
    Handles the user.registered event to kick off the onboarding process.
    """
    logger.info(f"New user registered: {event.data['user_id']}. Kicking off onboarding flow.")
    # In a real implementation, this would trigger a sequence of messages
    # to the user via the Telegram adapter.
    # For example:
    # telegram_service.send_welcome_message(event.data['user_id'])
