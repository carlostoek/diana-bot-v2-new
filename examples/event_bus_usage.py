#!/usr/bin/env python3
"""
Diana Bot V2 - Event Bus Usage Examples

This file demonstrates how to use the Event Bus system for inter-service
communication following the established patterns and best practices.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from src.core import (
    AchievementUnlockedEvent,
    BaseEventHandler,
    EventBusConfig,
    EventType,
    IEvent,
    PointsAwardedEvent,
    RedisEventBus,
    StoryChapterStartedEvent,
    UserRegisteredEvent,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GamificationHandler(BaseEventHandler):
    """Example handler for gamification-related events."""

    def __init__(self):
        super().__init__("gamification", "points_manager")
        self.add_supported_event_type(EventType.STORY_CHAPTER_STARTED)
        self.add_supported_event_type(EventType.USER_REGISTERED)

    async def _process_event(self, event: IEvent) -> bool:
        """Process gamification events."""
        logger.info(f"Gamification handler processing: {event.event_type}")

        if event.event_type == EventType.STORY_CHAPTER_STARTED:
            # Award points for starting a chapter
            points_event = PointsAwardedEvent(
                user_id=event.payload["user_id"],
                points_amount=25,
                action_type="chapter_started",
                correlation_id=event.correlation_id,
            )
            logger.info(f"Awarding 25 points to user {event.payload['user_id']}")
            return True

        elif event.event_type == EventType.USER_REGISTERED:
            # Give welcome bonus
            points_event = PointsAwardedEvent(
                user_id=event.payload["user_id"],
                points_amount=100,
                action_type="welcome_bonus",
                correlation_id=event.correlation_id,
            )
            logger.info(
                f"Welcome bonus of 100 points for user {event.payload['user_id']}"
            )
            return True

        return False


class NarrativeHandler(BaseEventHandler):
    """Example handler for narrative-related events."""

    def __init__(self):
        super().__init__("narrative", "story_manager")
        self.add_supported_event_type(EventType.POINTS_AWARDED)

    async def _process_event(self, event: IEvent) -> bool:
        """Process narrative events."""
        logger.info(f"Narrative handler processing: {event.event_type}")

        if event.event_type == EventType.POINTS_AWARDED:
            # Check if user reached milestone for story unlock
            if event.payload["points_amount"] >= 100:
                logger.info(
                    f"User {event.payload['user_id']} may have unlocked new story content"
                )
                # Here you could check user's total points and unlock new chapters
            return True

        return False


class AnalyticsHandler(BaseEventHandler):
    """Example handler for analytics tracking."""

    def __init__(self):
        super().__init__("analytics", "event_tracker")
        # Subscribe to all event types for analytics
        self.add_supported_event_type(EventType.POINTS_AWARDED)
        self.add_supported_event_type(EventType.ACHIEVEMENT_UNLOCKED)
        self.add_supported_event_type(EventType.STORY_CHAPTER_STARTED)
        self.add_supported_event_type(EventType.USER_REGISTERED)

    async def _process_event(self, event: IEvent) -> bool:
        """Track all events for analytics."""
        logger.info(
            f"Analytics tracking: {event.event_type} for user {event.payload.get('user_id', 'N/A')}"
        )

        # In a real implementation, you would:
        # - Send to analytics service (Mixpanel, Google Analytics, etc.)
        # - Update metrics in database
        # - Trigger business intelligence workflows

        return True


async def demonstrate_event_publishing(event_bus: RedisEventBus):
    """Demonstrate publishing various events."""
    logger.info("=== Demonstrating Event Publishing ===")

    # 1. User Registration Event
    user_reg_event = UserRegisteredEvent(
        user_id=12345,
        username="test_user",
        first_name="Test",
        language_code="en",
        is_premium=False,
    )
    await event_bus.publish(user_reg_event)
    logger.info("Published user registration event")

    # 2. Story Chapter Started Event
    chapter_event = StoryChapterStartedEvent(
        user_id=12345,
        chapter_id="chapter_001",
        chapter_title="The Beginning",
        story_arc="main_story",
        correlation_id="story-session-123",
    )
    await event_bus.publish(chapter_event)
    logger.info("Published story chapter started event")

    # 3. Achievement Unlocked Event
    achievement_event = AchievementUnlockedEvent(
        user_id=12345,
        achievement_id="first_chapter",
        achievement_name="Story Beginner",
        achievement_category="narrative",
        points_reward=150,
    )
    await event_bus.publish(achievement_event)
    logger.info("Published achievement unlocked event")

    # 4. Manual Points Award
    points_event = PointsAwardedEvent(
        user_id=12345,
        points_amount=200,
        action_type="manual_bonus",
        multiplier=2.0,
        source_service="admin",
    )
    await event_bus.publish(points_event)
    logger.info("Published points awarded event")


async def demonstrate_event_handling(event_bus: RedisEventBus):
    """Demonstrate event handling with multiple handlers."""
    logger.info("=== Setting Up Event Handlers ===")

    # Create handlers
    gamification_handler = GamificationHandler()
    narrative_handler = NarrativeHandler()
    analytics_handler = AnalyticsHandler()

    # Subscribe to events
    subscriptions = []

    # Gamification subscriptions
    sub1 = await event_bus.subscribe(
        EventType.STORY_CHAPTER_STARTED, gamification_handler
    )
    sub2 = await event_bus.subscribe(EventType.USER_REGISTERED, gamification_handler)
    subscriptions.extend([sub1, sub2])

    # Narrative subscriptions
    sub3 = await event_bus.subscribe(EventType.POINTS_AWARDED, narrative_handler)
    subscriptions.append(sub3)

    # Analytics subscriptions (subscribes to multiple event types)
    sub4 = await event_bus.subscribe(EventType.POINTS_AWARDED, analytics_handler)
    sub5 = await event_bus.subscribe(EventType.ACHIEVEMENT_UNLOCKED, analytics_handler)
    sub6 = await event_bus.subscribe(EventType.STORY_CHAPTER_STARTED, analytics_handler)
    sub7 = await event_bus.subscribe(EventType.USER_REGISTERED, analytics_handler)
    subscriptions.extend([sub4, sub5, sub6, sub7])

    logger.info(f"Created {len(subscriptions)} subscriptions")

    # Wait a moment for subscriptions to be active
    await asyncio.sleep(0.5)

    return subscriptions


async def demonstrate_metrics_and_health(event_bus: RedisEventBus):
    """Demonstrate metrics and health monitoring."""
    logger.info("=== Event Bus Metrics and Health ===")

    # Get metrics
    metrics = await event_bus.get_metrics()
    logger.info(f"Event Bus Metrics: {metrics}")

    # Get subscription health
    health = await event_bus.get_subscription_health()
    logger.info(f"Active subscriptions: {len(health)}")

    for sub_id, sub_health in health.items():
        logger.info(
            f"Subscription {sub_id}: "
            f"Type={sub_health['event_type']}, "
            f"Service={sub_health['service_name']}, "
            f"Success={sub_health['success_count']}, "
            f"Errors={sub_health['error_count']}"
        )


async def main():
    """Main demonstration function."""
    logger.info("Starting Diana Bot V2 Event Bus Demo")

    # Configure Event Bus
    config = EventBusConfig(
        redis_url="redis://localhost:6379/0",
        max_retry_attempts=3,
        retry_delay_seconds=1.0,
        event_ttl_seconds=3600,
        health_check_interval_seconds=10,
        metrics_enabled=True,
        event_store_enabled=False,  # Disable for demo
    )

    # Initialize Event Bus
    event_bus = RedisEventBus(config)

    try:
        # Initialize connection
        await event_bus.initialize()
        logger.info("Event Bus initialized successfully")

        # Set up event handlers
        subscriptions = await demonstrate_event_handling(event_bus)

        # Publish events
        await demonstrate_event_publishing(event_bus)

        # Wait for event processing
        logger.info("Waiting for event processing...")
        await asyncio.sleep(2.0)

        # Show metrics and health
        await demonstrate_metrics_and_health(event_bus)

        # Cleanup subscriptions
        logger.info("Cleaning up subscriptions...")
        for sub_id in subscriptions:
            await event_bus.unsubscribe(sub_id)

        logger.info("Demo completed successfully!")

    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        raise

    finally:
        # Shutdown Event Bus
        await event_bus.shutdown()
        logger.info("Event Bus shutdown complete")


if __name__ == "__main__":
    # Run the demonstration
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        exit(1)
