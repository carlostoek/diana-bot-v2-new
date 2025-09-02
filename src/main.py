"""
Main application file for the Diana Bot.
"""

import asyncio
import logging
from src.containers import ApplicationContainer
from src.bot.main import start_bot


from src.bot.middleware.auth import AuthMiddleware


from src.bot.events import event_listener


async def main() -> None:
    """
    Main application entry point.
    Initializes the container and starts the application.
    """
    logging.basicConfig(level=logging.INFO)

    container = ApplicationContainer()
    container.wire(modules=[__name__, "src.bot.handlers"])

    # Setup middleware
    user_service = container.services.user_service()
    auth_middleware = AuthMiddleware(user_service)

    bot = container.bot.bot()
    dispatcher = container.bot.dispatcher()
    dispatcher.update.outer_middleware.register(auth_middleware)

    # Get services for the event listener
    redis_client = container.infrastructure.redis_client()
    onboarding_service = container.services.onboarding_service()

    # Start the bot and the event listener concurrently
    await asyncio.gather(
        start_bot(bot, dispatcher),
        event_listener(redis_client, onboarding_service),
    )


if __name__ == "__main__":
    asyncio.run(main())
