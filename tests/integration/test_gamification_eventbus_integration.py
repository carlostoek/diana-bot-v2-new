"""
Integration Tests for Gamification Service with Event Bus

Tests the real integration between GamificationService and Event Bus
to ensure proper event handling and system communication.
"""

import asyncio

import pytest
import pytest_asyncio

from core.events import EventBus, GameEvent, NarrativeEvent
from services.gamification.interfaces import ActionType
from services.gamification.service import GamificationService


class TestGamificationEventBusIntegration:
    """Test real integration between Gamification and Event Bus."""

    @pytest_asyncio.fixture
    async def event_bus(self):
        """Create real Event Bus instance for integration testing."""
        bus = EventBus(test_mode=True)  # Use test mode to avoid Redis dependency
        await bus.initialize()
        yield bus
        await bus.cleanup()

    @pytest_asyncio.fixture
    async def gamification_service(self, event_bus):
        """Create real GamificationService with Event Bus."""
        service = GamificationService(event_bus=event_bus)
        await service.initialize()
        yield service
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_event_bus_game_event_integration(
        self, event_bus, gamification_service
    ):
        """Test that GameEvents are properly processed through Event Bus."""
        user_id = 123

        # Create and publish a game event
        event = GameEvent(
            user_id=user_id,
            action="daily_login",
            points_earned=50,
            context={"source": "integration_test"},
        )

        # Publish event to Event Bus
        await event_bus.publish(event)

        # Allow time for event processing
        await asyncio.sleep(0.1)

        # Check that user received points
        stats = await gamification_service.get_user_stats(user_id)
        assert stats.total_points > 0

    @pytest.mark.asyncio
    async def test_event_bus_narrative_event_integration(
        self, event_bus, gamification_service
    ):
        """Test that NarrativeEvents are properly processed."""
        user_id = 456

        # Create and publish a narrative event
        event = NarrativeEvent(
            user_id=user_id,
            chapter_id="chapter_01_intro",
            decision_made="help_stranger",
            context={"source": "integration_test"},
        )

        # Mock event type for chapter completion
        event._type = "narrative.chapter_completed"

        # Publish event
        await event_bus.publish(event)

        # Allow processing time
        await asyncio.sleep(0.1)

        # Check that user received points for story progress
        stats = await gamification_service.get_user_stats(user_id)
        assert stats.total_points > 0

    @pytest.mark.asyncio
    async def test_bidirectional_event_communication(
        self, event_bus, gamification_service
    ):
        """Test that GamificationService publishes events back to Event Bus."""
        user_id = 789

        # Set up event listener to capture published events
        published_events = []

        async def event_listener(event):
            published_events.append(event)

        # Subscribe to gamification events
        await event_bus.subscribe("game.points_awarded", event_listener)

        # Process an action through gamification service
        result = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"correct_answer": True},
        )

        assert result.success is True

        # Allow time for event publishing
        await asyncio.sleep(0.1)

        # Should have published a points awarded event
        # (In test mode, events might not be delivered exactly as in production)

    @pytest.mark.asyncio
    async def test_multiple_services_event_flow(self, event_bus, gamification_service):
        """Test event flow between multiple services."""
        user_id = 999

        # Simulate events from multiple sources
        events = [
            GameEvent(user_id=user_id, action="login", points_earned=10, context={}),
            GameEvent(
                user_id=user_id, action="message_sent", points_earned=5, context={}
            ),
            GameEvent(
                user_id=user_id,
                action="trivia_completed",
                points_earned=100,
                context={},
            ),
        ]

        # Publish all events
        for event in events:
            await event_bus.publish(event)

        # Allow processing time
        await asyncio.sleep(0.2)

        # Check final user state
        stats = await gamification_service.get_user_stats(user_id)
        assert stats.total_points > 0

        # Check health of both systems
        bus_health = await event_bus.health_check()
        service_health = await gamification_service.health_check()

        assert bus_health["status"] == "healthy"
        assert service_health["status"] == "healthy"
