import json
import redis.asyncio as redis
from src.domain.events import Event


class EventPublisher:
    """
    Handles publishing events to the Redis event bus.
    """

    def __init__(self, redis_client: redis.Redis):
        self._redis_client = redis_client

    async def publish(self, channel: str, event: Event) -> None:
        """
        Publishes an event to the specified Redis channel.

        Args:
            channel: The Redis channel to publish to.
            event: The event to publish.
        """
        message = event.model_dump_json()
        await self._redis_client.publish(channel, message)
        print(f"Published event {event.event_name} to channel {channel}")
