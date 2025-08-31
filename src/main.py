import asyncio
from src.core.container import Container
from src.modules.user.handlers import user_registered_handler
from dependency_injector.wiring import inject, Provide
from src.modules.user.interfaces import IUserService
from src.telegram_adapter.bot import start_bot

@inject
def handle_new_user(user_service: IUserService = Provide[Container.user_service]):
    """
    Example function that uses an injected service.
    """
    print("Handling new user... (example usage of injected service)")
    # In a real scenario, you would call the service's methods.
    # For example: user_service.find_or_create_user(...)
    pass

async def main():
    """
    Main entry point for the application.
    Initializes the container and starts the bot.
    """
    # Initialize the dependency injection container
    container = Container()

    # Wire the container to the modules that need it.
    container.wire(
        modules=[
            __name__,
            "src.modules.user.handlers",
            "src.telegram_adapter.handlers.start",
        ]
    )
    print("Application container initialized and wired.")

    # Example of using an injected function
    handle_new_user()

    # Get the event bus and subscribe handlers
    event_bus = container.event_bus()
    await event_bus.initialize()
    await event_bus.subscribe("user.registered", user_registered_handler)
    print("Subscribed user_registered_handler to 'user.registered' event.")

    # Start the bot
    print("Starting bot...")
    await start_bot(container)
    print("Bot has stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Application stopped manually.")
