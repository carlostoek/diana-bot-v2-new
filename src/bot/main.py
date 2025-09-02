import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from src.containers import ApplicationContainer

logger = logging.getLogger(__name__)


from aiogram.filters import CommandStart
from .handlers import commands, errors

def register_handlers(dp: Dispatcher):
    """
    Registers all handlers for the bot.
    """
    # Register command handlers
    dp.message.register(commands.start_handler, CommandStart())

    # Register error handlers
    dp.errors.register(errors.error_handler)


async def start_bot(bot: Bot, dp: Dispatcher):
    """
    Initializes and starts the Telegram bot.
    """
    register_handlers(dp)

    logger.info("Starting bot...")
    # Start polling
    await dp.start_polling(bot)
