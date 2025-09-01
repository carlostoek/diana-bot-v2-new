import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.core.events import EventBus, GameEvent, UserEvent, NarrativeEvent, AdminEvent, SystemEvent
from src.core.interfaces import IEventHandler


class TestEventBusIntegration:
    """Integration tests for the EventBus system."""

    @pytest.fixture
    async def event_bus(self):
        """Create a test event bus instance."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        yield bus
        await bus.cleanup()

    @pytest.mark.asyncio
    async def test_game_event_publish_and_subscribe(self, event_bus):
        """Test publishing and subscribing to game events."""
        # Create a mock handler
        handler = AsyncMock()
        
        # Subscribe to game events
        await event_bus.subscribe("game.login", handler)
        
        # Create and publish a game event
        event = GameEvent(
            user_id=12345,
            action="login",
            points_earned=10,
            context={"source": "telegram"}
        )
        
        # Publish the event
        await event_bus.publish(event)
        
        # Verify the handler was called with the event
        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert isinstance(called_event, GameEvent)
        assert called_event.user_id == 12345
        assert called_event.action == "login"
        assert called_event.points_earned == 10
        assert called_event.context == {"source": "telegram"}

    @pytest.mark.asyncio
    async def test_user_event_publish_and_subscribe(self, event_bus):
        """Test publishing and subscribing to user events."""
        # Create a mock handler
        handler = AsyncMock()
        
        # Subscribe to user events
        await event_bus.subscribe("user.registered", handler)
        
        # Create and publish a user event
        event = UserEvent(
            user_id=54321,
            event_type="registered",
            user_data={"username": "testuser", "source": "telegram"}
        )
        
        # Publish the event
        await event_bus.publish(event)
        
        # Verify the handler was called with the event
        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert isinstance(called_event, UserEvent)
        assert called_event.user_id == 54321
        assert called_event.event_type == "registered"
        assert called_event.user_data == {"username": "testuser", "source": "telegram"}

    @pytest.mark.asyncio
    async def test_narrative_event_publish_and_subscribe(self, event_bus):
        """Test publishing and subscribing to narrative events."""
        # Create a mock handler
        handler = AsyncMock()
        
        # Subscribe to narrative events
        await event_bus.subscribe("narrative.decision_made", handler)
        
        # Create and publish a narrative event
        event = NarrativeEvent(
            user_id=98765,
            chapter_id="chapter_01_intro",
            decision_made="help_stranger",
            character_impact={"alice": 5, "bob": -2},
            choice_time_seconds=30.5
        )
        
        # Publish the event
        await event_bus.publish(event)
        
        # Verify the handler was called with the event
        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert isinstance(called_event, NarrativeEvent)
        assert called_event.user_id == 98765
        assert called_event.chapter_id == "chapter_01_intro"
        assert called_event.decision_made == "help_stranger"
        assert called_event.character_impact == {"alice": 5, "bob": -2}
        assert called_event.choice_time_seconds == 30.5

    @pytest.mark.asyncio
    async def test_admin_event_publish_and_subscribe(self, event_bus):
        """Test publishing and subscribing to admin events."""
        # Create a mock handler
        handler = AsyncMock()
        
        # Subscribe to admin events
        await event_bus.subscribe("admin.points_adjusted", handler)
        
        # Create and publish an admin event
        event = AdminEvent(
            admin_id=11111,
            action_type="points_adjusted",
            target_user=22222,
            details={"reason": "Bug fix", "points_adjustment": 100}
        )
        
        # Publish the event
        await event_bus.publish(event)
        
        # Verify the handler was called with the event
        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert isinstance(called_event, AdminEvent)
        assert called_event.admin_id == 11111
        assert called_event.action_type == "points_adjusted"
        assert called_event.target_user == 22222
        assert called_event.details == {"reason": "Bug fix", "points_adjustment": 100}

    @pytest.mark.asyncio
    async def test_system_event_publish_and_subscribe(self, event_bus):
        """Test publishing and subscribing to system events."""
        # Create a mock handler
        handler = AsyncMock()
        
        # Subscribe to system events
        await event_bus.subscribe("system.service_started", handler)
        
        # Create and publish a system event
        event = SystemEvent(
            component="gamification_service",
            event_type="service_started",
            system_data={"version": "2.0.0", "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        # Publish the event
        await event_bus.publish(event)
        
        # Verify the handler was called with the event
        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert isinstance(called_event, SystemEvent)
        assert called_event.component == "gamification_service"
        assert called_event.event_type == "service_started"
        assert "version" in called_event.system_data
        assert "timestamp" in called_event.system_data

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, event_bus):
        """Test wildcard subscription functionality."""
        # Create a mock handler
        handler = AsyncMock()
        
        # Subscribe to all game events using wildcard
        await event_bus.subscribe("game.*", handler)
        
        # Create and publish multiple game events
        event1 = GameEvent(
            user_id=11111,
            action="login",
            points_earned=10
        )
        
        event2 = GameEvent(
            user_id=22222,
            action="daily_login",
            points_earned=20
        )
        
        # Publish both events
        await event_bus.publish(event1)
        await event_bus.publish(event2)
        
        # Verify the handler was called twice
        assert handler.call_count == 2
        
        # Verify both events were received
        called_events = [call[0][0] for call in handler.call_args_list]
        assert isinstance(called_events[0], GameEvent)
        assert isinstance(called_events[1], GameEvent)
        assert called_events[0].user_id == 11111
        assert called_events[1].user_id == 22222

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event(self, event_bus):
        """Test multiple handlers receiving the same event."""
        # Create two mock handlers
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        
        # Subscribe both handlers to the same event type
        await event_bus.subscribe("game.login", handler1)
        await event_bus.subscribe("game.login", handler2)
        
        # Create and publish a game event
        event = GameEvent(
            user_id=12345,
            action="login",
            points_earned=10
        )
        
        # Publish the event
        await event_bus.publish(event)
        
        # Verify both handlers were called
        handler1.assert_called_once()
        handler2.assert_called_once()
        
        # Verify both handlers received the same event
        called_event1 = handler1.call_args[0][0]
        called_event2 = handler2.call_args[0][0]
        assert called_event1.user_id == called_event2.user_id
        assert called_event1.action == called_event2.action

    @pytest.mark.asyncio
    async def test_unsubscribe_functionality(self, event_bus):
        """Test unsubscribing from events."""
        # Create a mock handler
        handler = AsyncMock()
        
        # Subscribe to an event
        await event_bus.subscribe("game.login", handler)
        
        # Create and publish an event (handler should be called)
        event1 = GameEvent(user_id=11111, action="login", points_earned=10)
        await event_bus.publish(event1)
        assert handler.call_count == 1
        
        # Unsubscribe the handler
        await event_bus.unsubscribe("game.login", handler)
        
        # Create and publish another event (handler should NOT be called)
        event2 = GameEvent(user_id=22222, action="login", points_earned=20)
        await event_bus.publish(event2)
        
        # Verify the handler was not called again
        assert handler.call_count == 1  # Still 1, not 2

    @pytest.mark.asyncio
    async def test_event_persistence_and_replay(self, event_bus):
        """Test event persistence and replay functionality."""
        # Create and publish several events
        events = [
            GameEvent(user_id=11111, action="login", points_earned=10),
            UserEvent(user_id=22222, event_type="registered", user_data={"source": "telegram"}),
            GameEvent(user_id=33333, action="daily_login", points_earned=20)
        ]
        
        for event in events:
            await event_bus.publish(event)
        
        # Retrieve persisted events
        persisted_events = await event_bus.get_published_events()
        
        # Verify all events were persisted
        assert len(persisted_events) == 3
        
        # Verify event types and order
        assert isinstance(persisted_events[0], GameEvent)
        assert isinstance(persisted_events[1], UserEvent)
        assert isinstance(persisted_events[2], GameEvent)
        
        # Test replay functionality with a new handler
        replay_handler = AsyncMock()
        await event_bus.replay_events(target_handlers=[replay_handler])
        
        # Verify the replay handler was called for each event
        assert replay_handler.call_count == 3
        
        # Verify the events received during replay
        called_events = [call[0][0] for call in replay_handler.call_args_list]
        assert called_events[0].user_id == 11111
        assert called_events[1].user_id == 22222
        assert called_events[2].user_id == 33333

    @pytest.mark.asyncio
    async def test_health_check(self, event_bus):
        """Test the health check functionality."""
        # Get health status
        health = await event_bus.health_check()
        
        # Verify health check fields
        assert "status" in health
        assert "redis_connected" in health
        assert "subscribers_count" in health
        assert "events_published" in health
        assert "circuit_breaker_state" in health
        
        # Verify expected values
        assert health["status"] == "healthy"
        assert health["redis_connected"] == True  # We're in test mode
        assert health["circuit_breaker_state"] == "closed"

    @pytest.mark.asyncio
    async def test_statistics(self, event_bus):
        """Test the statistics functionality."""
        # Get initial statistics
        stats = await event_bus.get_statistics()
        
        # Verify statistics fields
        assert "total_events_published" in stats
        assert "total_subscribers" in stats
        assert "events_by_type" in stats
        assert "avg_publish_time_ms" in stats
        assert "avg_handler_time_ms" in stats
        assert "failed_publishes" in stats
        assert "failed_handlers" in stats
        assert "circuit_breaker_state" in stats
        assert "circuit_breaker_failures" in stats
        assert "active_pubsub_tasks" in stats
        assert "stored_events_count" in stats
        
        # Publish an event and check if statistics update
        initial_published = stats["total_events_published"]
        
        event = GameEvent(user_id=12345, action="login", points_earned=10)
        await event_bus.publish(event)
        
        # Get updated statistics
        updated_stats = await event_bus.get_statistics()
        assert updated_stats["total_events_published"] == initial_published + 1
        assert updated_stats["stored_events_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__])