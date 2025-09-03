import asyncio
import json
import logging
import redis.asyncio as redis
from src.services.onboarding_service import OnboardingService
from src.services.notification_service import NotificationService
from src.domain.events import UserRegistered, AchievementUnlocked

logger = logging.getLogger(__name__)


MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

async def _handle_event(event_name: str, payload: dict, container):
    """Helper function to dispatch events to services with retry logic."""
    onboarding_service = container.onboarding_service
    notification_service = container.notification_service

    for attempt in range(MAX_RETRIES):
        try:
            if event_name == "user_registered":
                user_id = payload.get("user_id")
                if user_id:
                    logger.info(f"Processing UserRegistered event for user_id: {user_id}")
                    await onboarding_service.send_welcome_message(user_id)
                    return  # Success

            elif event_name == "achievement_unlocked":
                user_id = payload.get("user_id")
                achievement_name = payload.get("achievement_name")
                reward_points = payload.get("reward_points")
                if user_id and achievement_name:
                    logger.info(f"Processing AchievementUnlocked event for user {user_id}")
                    await notification_service.send_achievement_unlocked_notification(
                        user_id=user_id,
                        achievement_name=achievement_name,
                        reward_points=reward_points,
                    )
                    return  # Success
            else:
                return # Unknown event, do not retry

        except Exception as e:
            logger.error(
                f"Attempt {attempt + 1}/{MAX_RETRIES} failed for event {event_name}: {e}",
                exc_info=True
            )
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error(f"Event {event_name} failed after {MAX_RETRIES} attempts.")


async def event_listener(redis_client: redis.Redis, service_provider):
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

            if event_name:
                # Fire and forget: run handler in a background task
                asyncio.create_task(_handle_event(event_name, payload, service_provider))

        except json.JSONDecodeError:
            logger.warning("Could not decode event message: %s", message.get("data"))
        except Exception:
            logger.error("Critical error in event listener loop", exc_info=True)
            await asyncio.sleep(1)
