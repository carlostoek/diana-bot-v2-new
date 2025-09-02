"""
Main application file for the Diana Bot.
"""

import asyncio
import logging
from src.containers import ApplicationContainer
from src.bot.main import start_bot


async def main() -> None:
    """
    Main application entry point.
    Initializes the container and starts the application.
    """
    logging.basicConfig(level=logging.INFO)

    container = ApplicationContainer()
    container.wire(modules=[__name__, "src.bot.handlers"])

    bot = container.bot.bot()
    dispatcher = container.bot.dispatcher()

    await start_bot(bot, dispatcher)


if __name__ == "__main__":
    asyncio.run(main())
