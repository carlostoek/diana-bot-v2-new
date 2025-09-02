import asyncio
import json
import logging
import redis.asyncio as redis
from src.services.onboarding_service import OnboardingService
from src.domain.events import UserRegistered

logger = logging.getLogger(__name__)


async def event_listener(
    redis_client: redis.Redis,
    onboarding_service: OnboardingService,
):
    """
    Listens for events on Redis pub/sub and triggers corresponding services.
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("user_events")
    logger.info("Event listener subscribed to 'user_events' channel.")

    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message is None:
                await asyncio.sleep(0.1)
                continue

            data = json.loads(message["data"])
            event_name = data.get("event_name")
            payload = data.get("payload", {})

            if event_name == UserRegistered.event_name:
                user_id = payload.get("user_id")
                if user_id:
                    logger.info(f"Processing UserRegistered event for user_id: {user_id}")
                    await onboarding_service.send_welcome_message(user_id)

        except json.JSONDecodeError:
            logger.warning("Could not decode event message: %s", message.get("data"))
        except Exception:
            logger.error("Error processing event", exc_info=True)
            # Avoid crashing the listener on a single bad event
            await asyncio.sleep(1)
