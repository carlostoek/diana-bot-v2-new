"""
Main application file for the Diana Bot.
"""

import asyncio
import logging
from src.containers import ApplicationContainer
from src.bot.main import start_bot


from src.bot.middleware.auth import AuthMiddleware
from src.bot.middleware.uow import UoWMiddleware



from src.bot.events import event_listener


from src.domain.models import Achievement


async def setup_database(container: ApplicationContainer):
    """A helper function to setup initial database data."""
    session_factory = container.infrastructure.session_factory()
    async with session_factory() as session:
        achievement_repo = container.infrastructure.achievement_repository(session=session)
        first_steps = await achievement_repo.get_by_name("First Steps")
        if not first_steps:
            new_achievement = Achievement(
                name="First Steps",
                description="Start the bot for the first time.",
                reward_points=10,
            )
            await achievement_repo.add(new_achievement)
            await session.commit()
            logging.info("Created 'First Steps' achievement.")


async def main() -> None:
    """
    Main application entry point.
    Initializes the container and starts the application.
    """
    logging.basicConfig(level=logging.INFO)
    
    container = ApplicationContainer()
    container.wire(modules=[__name__, "src.bot.handlers"])

    await setup_database(container)

    # Setup middleware
    uow_provider = container.infrastructure.uow
    user_service = container.services.user_service()
    gamification_service = container.services.gamification_service()
    
    uow_middleware = UoWMiddleware(uow_provider)
    auth_middleware = AuthMiddleware(user_service, gamification_service)

    bot = container.bot.bot()
    dispatcher = container.bot.dispatcher()
    # The order is important: UoW middleware must come before Auth middleware
    dispatcher.update.outer_middleware.register(uow_middleware)
    dispatcher.update.outer_middleware.register(auth_middleware)

    # Get services
    gamification_service = container.services.gamification_service()
    redis_client = container.infrastructure.redis_client()
    service_provider = container.services

    # Pass long-lived services to the dispatcher context
    dispatcher["gamification_service"] = gamification_service

    # Start the bot and the event listener concurrently
    await asyncio.gather(
        start_bot(bot, dispatcher),
        event_listener(redis_client, service_provider),


if __name__ == "__main__":
    asyncio.run(main())
