"""
TDD Tests for Event Bus Core Interfaces

These tests define the exact behavior expected from the IEvent and IEventBus interfaces
following the architecture outlined in docs/planning/04-technical-architecture.md.

These tests should initially FAIL (RED phase) until the interfaces are implemented.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock

import pytest

from core.events import EventBus, IEvent, IEventBus


class TestIEventInterface:
    """
    Comprehensive tests for the IEvent interface behavior.

    Tests cover:
    - Event creation with required fields
    - Event serialization to/from dict and JSON
    - Event validation (required fields, data types)
    - Event equality and hash operations
    - Event metadata handling
    """

    def test_event_creation_with_required_fields(self):
        """Test that IEvent can be created with all required fields."""
        event_id = str(uuid.uuid4())
        event_type = "test.event"
        timestamp = datetime.now(timezone.utc)
        data = {"key": "value", "number": 42}

        event = IEvent(id=event_id, type=event_type, timestamp=timestamp, data=data)

        assert event.id == event_id
        assert event.type == event_type
        assert event.timestamp == timestamp
        assert event.data == data

    def test_event_creation_fails_without_required_fields(self):
        """Test that IEvent creation fails when required fields are missing."""
        with pytest.raises((TypeError, ValueError)):
            IEvent()

        with pytest.raises((TypeError, ValueError)):
            IEvent(id="test-id")

        with pytest.raises((TypeError, ValueError)):
            IEvent(id="test-id", type="test.event")

        with pytest.raises((TypeError, ValueError)):
            IEvent(
                id="test-id", type="test.event", timestamp=datetime.now(timezone.utc)
            )

    def test_event_auto_generates_id_and_timestamp_if_not_provided(self):
        """Test that IEvent auto-generates ID and timestamp if not explicitly provided."""
        event = IEvent(type="test.event", data={"test": True})

        assert event.id is not None
        assert isinstance(event.id, str)
        assert len(event.id) > 0
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo is not None  # Should be timezone-aware

    def test_event_validates_data_types(self):
        """Test that IEvent validates field data types."""
        # ID must be string
        with pytest.raises((TypeError, ValueError)):
            IEvent(id=123, type="test.event", data={})

        # Type must be string
        with pytest.raises((TypeError, ValueError)):
            IEvent(id="test-id", type=123, data={})

        # Timestamp must be datetime
        with pytest.raises((TypeError, ValueError)):
            IEvent(id="test-id", type="test.event", timestamp="not-datetime", data={})

        # Data must be serializable dict
        with pytest.raises((TypeError, ValueError)):
            IEvent(id="test-id", type="test.event", data="not-dict")

    def test_event_metadata_fields(self):
        """Test that IEvent supports optional metadata fields."""
        correlation_id = str(uuid.uuid4())
        source = "gamification.service"

        event = IEvent(
            type="test.event",
            data={"test": True},
            correlation_id=correlation_id,
            source=source,
        )

        assert event.correlation_id == correlation_id
        assert event.source == source

    def test_event_serialization_to_dict(self):
        """Test that IEvent can be serialized to dictionary."""
        event_id = str(uuid.uuid4())
        event_type = "user.action"
        timestamp = datetime.now(timezone.utc)
        data = {"user_id": 12345, "action": "login", "points": 10}
        correlation_id = str(uuid.uuid4())
        source = "auth.service"

        event = IEvent(
            id=event_id,
            type=event_type,
            timestamp=timestamp,
            data=data,
            correlation_id=correlation_id,
            source=source,
        )

        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert event_dict["id"] == event_id
        assert event_dict["type"] == event_type
        assert event_dict["timestamp"] == timestamp.isoformat()
        assert event_dict["data"] == data
        assert event_dict["correlation_id"] == correlation_id
        assert event_dict["source"] == source

    def test_event_serialization_to_json(self):
        """Test that IEvent can be serialized to JSON string."""
        event = IEvent(
            type="test.event", data={"nested": {"key": "value"}, "array": [1, 2, 3]}
        )

        json_str = event.to_json()

        assert isinstance(json_str, str)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["type"] == "test.event"
        assert parsed["data"]["nested"]["key"] == "value"
        assert parsed["data"]["array"] == [1, 2, 3]

    def test_event_deserialization_from_dict(self):
        """Test that IEvent can be created from dictionary."""
        event_dict = {
            "id": str(uuid.uuid4()),
            "type": "test.event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"key": "value"},
            "correlation_id": str(uuid.uuid4()),
            "source": "test.service",
        }

        event = IEvent.from_dict(event_dict)

        assert event.id == event_dict["id"]
        assert event.type == event_dict["type"]
        assert event.data == event_dict["data"]
        assert event.correlation_id == event_dict["correlation_id"]
        assert event.source == event_dict["source"]
        assert isinstance(event.timestamp, datetime)

    def test_event_deserialization_from_json(self):
        """Test that IEvent can be created from JSON string."""
        event_data = {
            "id": str(uuid.uuid4()),
            "type": "test.event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"key": "value", "number": 42},
        }

        json_str = json.dumps(event_data)
        event = IEvent.from_json(json_str)

        assert event.id == event_data["id"]
        assert event.type == event_data["type"]
        assert event.data == event_data["data"]
        assert isinstance(event.timestamp, datetime)

    def test_event_equality(self):
        """Test that IEvent equality works correctly."""
        event_id = str(uuid.uuid4())
        event_type = "test.event"
        timestamp = datetime.now(timezone.utc)
        data = {"key": "value"}

        event1 = IEvent(id=event_id, type=event_type, timestamp=timestamp, data=data)
        event2 = IEvent(id=event_id, type=event_type, timestamp=timestamp, data=data)
        event3 = IEvent(type=event_type, data=data)  # Different ID

        assert event1 == event2
        assert event1 != event3
        assert event1 != "not-an-event"

    def test_event_hash(self):
        """Test that IEvent can be used as dictionary key."""
        event1 = IEvent(id="test-1", type="test.event", data={})
        event2 = IEvent(id="test-1", type="test.event", data={})
        event3 = IEvent(id="test-2", type="test.event", data={})

        event_dict = {event1: "value1", event3: "value3"}

        assert event_dict[event2] == "value1"  # Same as event1
        assert len(event_dict) == 2

    def test_event_validation_rejects_invalid_data(self):
        """Test that IEvent validates data contains only serializable types."""

        # Should reject non-serializable objects
        class NonSerializable:
            pass

        with pytest.raises((TypeError, ValueError)):
            IEvent(type="test.event", data={"invalid": NonSerializable()})

        # Should reject functions
        with pytest.raises((TypeError, ValueError)):
            IEvent(type="test.event", data={"invalid": lambda x: x})

    def test_event_type_validation(self):
        """Test that IEvent validates event type format."""
        # Valid event types
        valid_types = [
            "user.action",
            "game.points_earned",
            "narrative.decision_made",
            "admin.user_banned",
            "system.error",
        ]

        for event_type in valid_types:
            event = IEvent(type=event_type, data={})
            assert event.type == event_type

        # Invalid event types should be rejected
        invalid_types = [
            "",  # Empty
            "invalid",  # No namespace
            ".invalid",  # Starts with dot
            "invalid.",  # Ends with dot
            "invalid..type",  # Double dots
            "invalid type",  # Contains space
            "invalid-type!",  # Special characters
        ]

        for invalid_type in invalid_types:
            with pytest.raises((TypeError, ValueError)):
                IEvent(type=invalid_type, data={})

    def test_event_data_size_limits(self):
        """Test that IEvent enforces reasonable data size limits."""
        # Should accept reasonable sized data
        reasonable_data = {"key": "value" * 100}  # ~500 bytes
        event = IEvent(type="test.event", data=reasonable_data)
        assert event.data == reasonable_data

        # Should reject excessively large data (> 1MB)
        large_data = {"large": "x" * (1024 * 1024 + 1)}  # > 1MB
        with pytest.raises((ValueError, MemoryError)):
            IEvent(type="test.event", data=large_data)

    def test_event_timestamp_timezone_handling(self):
        """Test that IEvent properly handles timezone-aware timestamps."""
        # Should accept timezone-aware datetime
        tz_aware = datetime.now(timezone.utc)
        event1 = IEvent(type="test.event", data={}, timestamp=tz_aware)
        assert event1.timestamp.tzinfo is not None

        # Should convert naive datetime to UTC
        naive = datetime.now()
        event2 = IEvent(type="test.event", data={}, timestamp=naive)
        assert event2.timestamp.tzinfo is not None

    def test_event_string_representation(self):
        """Test that IEvent has useful string representation for debugging."""
        event = IEvent(id="test-123", type="test.event", data={"key": "value"})

        str_repr = str(event)
        assert "test-123" in str_repr
        assert "test.event" in str_repr

        repr_str = repr(event)
        assert "IEvent" in repr_str
        assert "test-123" in repr_str


class TestIEventBusInterface:
    """
    Comprehensive tests for the IEventBus interface behavior.

    Tests cover:
    - publish() method behavior with different event types
    - subscribe() method for event type registration
    - unsubscribe() method for cleanup
    - Event filtering and routing logic
    - Async handler execution and error handling
    - Event persistence and replay capabilities
    - Performance requirements (publish <10ms, subscribe <1ms)
    """

    @pytest.fixture
    def event_bus(self):
        """Create IEventBus instance for testing."""
        return EventBus(test_mode=True)

    @pytest.fixture
    def sample_event(self):
        """Create sample event for testing."""
        return IEvent(
            type="test.event", data={"user_id": 12345, "action": "test_action"}
        )

    @pytest.mark.asyncio
    async def test_event_bus_publish_basic(self, event_bus, sample_event):
        """Test basic event publishing functionality."""
        # Should not raise exception
        await event_bus.publish(sample_event)

    @pytest.mark.asyncio
    async def test_event_bus_publish_validates_event(self, event_bus):
        """Test that publish validates event parameter."""
        # Should reject non-IEvent objects
        with pytest.raises((TypeError, ValueError)):
            await event_bus.publish("not-an-event")

        with pytest.raises((TypeError, ValueError)):
            await event_bus.publish({"type": "fake.event"})

        with pytest.raises((TypeError, ValueError)):
            await event_bus.publish(None)

    @pytest.mark.asyncio
    async def test_event_bus_subscribe_basic(self, event_bus):
        """Test basic event subscription functionality."""
        handler = AsyncMock()

        # Should not raise exception
        await event_bus.subscribe("test.event", handler)

    @pytest.mark.asyncio
    async def test_event_bus_subscribe_validates_parameters(self, event_bus):
        """Test that subscribe validates its parameters."""
        handler = AsyncMock()

        # Should reject invalid event types
        with pytest.raises((TypeError, ValueError)):
            await event_bus.subscribe("", handler)

        with pytest.raises((TypeError, ValueError)):
            await event_bus.subscribe(None, handler)

        # Should reject invalid handlers
        with pytest.raises((TypeError, ValueError)):
            await event_bus.subscribe("test.event", "not-a-handler")

        with pytest.raises((TypeError, ValueError)):
            await event_bus.subscribe("test.event", None)

    @pytest.mark.asyncio
    async def test_event_bus_unsubscribe_basic(self, event_bus):
        """Test basic event unsubscription functionality."""
        handler = AsyncMock()

        await event_bus.subscribe("test.event", handler)

        # Should not raise exception
        await event_bus.unsubscribe("test.event", handler)

    @pytest.mark.asyncio
    async def test_event_bus_unsubscribe_nonexistent(self, event_bus):
        """Test unsubscribing from non-existent subscription."""
        handler = AsyncMock()

        # Should handle gracefully (no exception)
        await event_bus.unsubscribe("nonexistent.event", handler)

    @pytest.mark.asyncio
    async def test_event_bus_publish_to_subscribers(self, event_bus, sample_event):
        """Test that published events are delivered to subscribers."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        await event_bus.subscribe("test.event", handler1)
        await event_bus.subscribe("test.event", handler2)

        await event_bus.publish(sample_event)

        # Both handlers should be called
        handler1.assert_called_once_with(sample_event)
        handler2.assert_called_once_with(sample_event)

    @pytest.mark.asyncio
    async def test_event_bus_event_type_filtering(self, event_bus):
        """Test that events are only delivered to matching subscribers."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        await event_bus.subscribe("game.event", handler1)
        await event_bus.subscribe("narrative.event", handler2)

        game_event = IEvent(type="game.event", data={"points": 10})
        narrative_event = IEvent(type="narrative.event", data={"chapter": 1})

        await event_bus.publish(game_event)
        await event_bus.publish(narrative_event)

        # Each handler should only receive its subscribed event type
        handler1.assert_called_once_with(game_event)
        handler2.assert_called_once_with(narrative_event)

    @pytest.mark.asyncio
    async def test_event_bus_wildcard_subscriptions(self, event_bus):
        """Test that wildcard subscriptions work correctly."""
        handler = AsyncMock()

        # Subscribe to all game events
        await event_bus.subscribe("game.*", handler)

        game_event1 = IEvent(type="game.points_earned", data={})
        game_event2 = IEvent(type="game.achievement_unlocked", data={})
        other_event = IEvent(type="user.login", data={})

        await event_bus.publish(game_event1)
        await event_bus.publish(game_event2)
        await event_bus.publish(other_event)

        # Should receive game events but not other events
        assert handler.call_count == 2
        handler.assert_any_call(game_event1)
        handler.assert_any_call(game_event2)

    @pytest.mark.asyncio
    async def test_event_bus_handler_error_handling(self, event_bus, sample_event):
        """Test that handler exceptions don't break the event bus."""
        failing_handler = AsyncMock(side_effect=Exception("Handler error"))
        working_handler = AsyncMock()

        await event_bus.subscribe("test.event", failing_handler)
        await event_bus.subscribe("test.event", working_handler)

        # Should not raise exception despite handler failure
        await event_bus.publish(sample_event)

        # Working handler should still be called
        working_handler.assert_called_once_with(sample_event)

    @pytest.mark.asyncio
    async def test_event_bus_handler_timeout_handling(self, event_bus, sample_event):
        """Test that slow handlers don't block event processing."""
        import asyncio

        slow_handler = AsyncMock()
        slow_handler.side_effect = lambda e: asyncio.sleep(10)  # 10 second delay
        fast_handler = AsyncMock()

        await event_bus.subscribe("test.event", slow_handler)
        await event_bus.subscribe("test.event", fast_handler)

        # Should complete quickly despite slow handler
        start_time = asyncio.get_event_loop().time()
        await event_bus.publish(sample_event)
        end_time = asyncio.get_event_loop().time()

        # Should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0

        # Fast handler should be called
        fast_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_bus_concurrent_publishing(self, event_bus):
        """Test that event bus handles concurrent publishing correctly."""
        import asyncio

        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler)

        # Publish multiple events concurrently
        events = [IEvent(type="test.event", data={"id": i}) for i in range(10)]

        await asyncio.gather(*[event_bus.publish(event) for event in events])

        # All events should be processed
        assert handler.call_count == 10

    @pytest.mark.asyncio
    async def test_event_bus_subscription_management(self, event_bus):
        """Test subscription and unsubscription lifecycle."""
        handler = AsyncMock()
        event = IEvent(type="test.event", data={})

        # Initially no subscribers
        await event_bus.publish(event)
        handler.assert_not_called()

        # After subscription, handler should be called
        await event_bus.subscribe("test.event", handler)
        await event_bus.publish(event)
        assert handler.call_count == 1

        # After unsubscription, handler should not be called
        await event_bus.unsubscribe("test.event", handler)
        await event_bus.publish(event)
        assert handler.call_count == 1  # Still 1, not 2

    @pytest.mark.asyncio
    async def test_event_bus_multiple_subscriptions_same_handler(self, event_bus):
        """Test that same handler can subscribe to multiple event types."""
        handler = AsyncMock()

        await event_bus.subscribe("game.event", handler)
        await event_bus.subscribe("narrative.event", handler)

        game_event = IEvent(type="game.event", data={})
        narrative_event = IEvent(type="narrative.event", data={})

        await event_bus.publish(game_event)
        await event_bus.publish(narrative_event)

        assert handler.call_count == 2

    @pytest.mark.asyncio
    async def test_event_bus_event_persistence(self, event_bus, sample_event):
        """Test that events can be persisted for replay/audit."""
        await event_bus.publish(sample_event)

        # Should be able to retrieve published events
        events = await event_bus.get_published_events(limit=10)

        assert len(events) >= 1
        assert any(e.id == sample_event.id for e in events)

    @pytest.mark.asyncio
    async def test_event_bus_event_replay(self, event_bus):
        """Test that events can be replayed from persistence."""
        handler = AsyncMock()

        # Publish event before subscription
        event = IEvent(type="test.event", data={"replay": True})
        await event_bus.publish(event)

        # Subscribe and replay events
        await event_bus.subscribe("test.event", handler)
        await event_bus.replay_events(event_types=["test.event"], since=None)

        # Handler should receive replayed event
        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_event_bus_publish_performance(self, event_bus, sample_event):
        """Test that publishing meets performance requirements (<10ms)."""
        import asyncio

        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler)

        # Measure publish time
        start_time = asyncio.get_event_loop().time()
        await event_bus.publish(sample_event)
        end_time = asyncio.get_event_loop().time()

        publish_time = (end_time - start_time) * 1000  # Convert to ms

        # Should complete within 10ms requirement
        assert publish_time < 10.0, f"Publish took {publish_time}ms, should be <10ms"

    @pytest.mark.asyncio
    async def test_event_bus_subscribe_performance(self, event_bus):
        """Test that subscription meets performance requirements (<1ms)."""
        import asyncio

        handler = AsyncMock()

        # Measure subscribe time
        start_time = asyncio.get_event_loop().time()
        await event_bus.subscribe("test.event", handler)
        end_time = asyncio.get_event_loop().time()

        subscribe_time = (end_time - start_time) * 1000  # Convert to ms

        # Should complete within 1ms requirement
        assert (
            subscribe_time < 1.0
        ), f"Subscribe took {subscribe_time}ms, should be <1ms"

    @pytest.mark.asyncio
    async def test_event_bus_memory_management(self, event_bus):
        """Test that event bus doesn't leak memory with many subscriptions."""
        import gc

        handlers = [AsyncMock() for _ in range(1000)]

        # Subscribe many handlers
        for i, handler in enumerate(handlers):
            await event_bus.subscribe(f"test.event.{i}", handler)

        # Unsubscribe all handlers
        for i, handler in enumerate(handlers):
            await event_bus.unsubscribe(f"test.event.{i}", handler)

        # Force garbage collection
        gc.collect()

        # Memory usage should be reasonable (implementation detail)
        # This test mainly ensures unsubscribe properly cleans up

    @pytest.mark.asyncio
    async def test_event_bus_event_ordering(self, event_bus):
        """Test that events are processed in order when published sequentially."""
        received_events = []

        async def order_tracking_handler(event):
            received_events.append(event.data["order"])

        await event_bus.subscribe("test.event", order_tracking_handler)

        # Publish events in order
        for i in range(10):
            event = IEvent(type="test.event", data={"order": i})
            await event_bus.publish(event)

        # Events should be processed in order
        assert received_events == list(range(10))

    @pytest.mark.asyncio
    async def test_event_bus_health_check(self, event_bus):
        """Test that event bus provides health check functionality."""
        health = await event_bus.health_check()

        assert isinstance(health, dict)
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "subscribers_count" in health
        assert "events_published" in health

    @pytest.mark.asyncio
    async def test_event_bus_statistics(self, event_bus, sample_event):
        """Test that event bus provides operational statistics."""
        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler)
        await event_bus.publish(sample_event)

        stats = await event_bus.get_statistics()

        assert isinstance(stats, dict)
        assert "total_events_published" in stats
        assert "total_subscribers" in stats
        assert "events_by_type" in stats
        assert stats["total_events_published"] >= 1
        assert stats["total_subscribers"] >= 1
