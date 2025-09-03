import logging
from aiogram import types
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


async def error_handler(event: types.ErrorEvent):
    """
    Catches exceptions and logs them.
    """
    logger.error(
        "Caught an exception: %s",
        event.exception,
        exc_info=True,
    )

    # Optionally, inform the user that an error occurred
    if isinstance(event.exception, TelegramAPIError):
        # More specific handling for API errors can be added here
        pass

    # For other types of errors, you might want to send a generic message
    # to the user. Be careful not to spam the user in case of frequent errors.
    # For example, check if the update has a message and a chat id.
    if event.update.message:
        try:
            await event.update.message.reply(
                "Sorry, something went wrong on our end. We've been notified."
            )
        except TelegramAPIError:
            logger.error("Could not send error message to user.")

    return True # Mark the exception as handled
