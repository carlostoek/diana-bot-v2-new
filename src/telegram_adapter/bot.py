import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from src.telegram_adapter.handlers import start
from src.core.container import Container

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
    # In a real app, you might raise an exception or handle this differently
    # For now, we exit if the token is not found.
    exit(1)

async def start_bot(container: Container):
    """
    Initializes and starts the bot.
    """
    # Initialize Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(
        user_service=container.user_service()
    )

    # Register the command handlers
    dp.include_router(start.router)

    logger.info("Starting bot polling...")
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    # This part is for standalone testing.
    # The main application will call start_bot from src/main.py
    container = Container()
    container.wire(modules=["src.telegram_adapter.handlers.start"])
    try:
        asyncio.run(start_bot(container))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
