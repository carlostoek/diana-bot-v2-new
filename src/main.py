"""
Main application file for the Diana Bot.
"""

import asyncio
from src.containers import ApplicationContainer


from src.domain.events import Event


async def main() -> None:
    """
    Main application entry point.
    Initializes the container and starts the application.
    """
    container = ApplicationContainer()
    container.wire(modules=[__name__])

    config = container.config()
    print(f"🚀 Application starting in {config.ENVIRONMENT} mode")

    # Example of accessing a dependency
    redis_client = await container.infrastructure.redis_client()
    pong = await redis_client.ping()
    print(f"Redis ping: {'PONG' if pong else 'FAIL'}")

    # Example of publishing an event
    event_publisher = container.infrastructure.event_publisher()
    sample_event = Event(event_name="user_registered", payload={"user_id": 123})
    await event_publisher.publish(channel="user_events", event=sample_event)

    # The main application loop will go here
    print("Application setup complete. Ready to run services.")


if __name__ == "__main__":
    asyncio.run(main())
