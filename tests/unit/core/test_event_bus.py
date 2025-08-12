"""
Comprehensive unit tests for Diana Bot V2 Event Bus system.

These tests validate the core Event Bus functionality including:
- Event publishing and subscription
- Error handling and retry logic
- Subscription management
- Event serialization/deserialization
- Performance tracking and metrics
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio

from src.core.event_bus import BaseEventHandler, RedisEventBus, Subscription
# Import from the new event system
from src.core import (
    AchievementUnlockedEvent,
    PointsAwardedEvent,
    UserRegisteredEvent,
)

# Try to import legacy components for backward compatibility
try:
    from src.core import BaseEvent, EventFactory, EventType
except ImportError:
    # Use new event system base
    from src.core import BaseEventWithValidation as BaseEvent
    BaseEvent = BaseEvent
    EventFactory = None
    EventType = None
from src.core.interfaces import (
    EventBusConfig,
    EventHandlingError,
    EventPriority,
    EventPublishError,
    EventSubscriptionError,
    EventValidationError,
    IEvent,
    IEventHandler,
)


# Test Fixtures
@pytest.fixture
def event_bus_config():
    """Create test configuration for EventBus."""
    return EventBusConfig(
        redis_url="redis://localhost:6379/15",  # Use test database
        max_retry_attempts=2,
        retry_delay_seconds=0.1,
        event_ttl_seconds=3600,
        max_concurrent_handlers=10,
        health_check_interval_seconds=1,
        metrics_enabled=True,
        event_store_enabled=False,
    )


@pytest.fixture
async def mock_redis():
    """Create mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.publish = AsyncMock(return_value=1)  # 1 subscriber
    redis_mock.close = AsyncMock()

    # Mock pubsub
    pubsub_mock = AsyncMock()
    pubsub_mock.subscribe = AsyncMock()
    pubsub_mock.unsubscribe = AsyncMock()
    pubsub_mock.close = AsyncMock()
    pubsub_mock.listen = AsyncMock()

    redis_mock.pubsub = Mock(return_value=pubsub_mock)

    return redis_mock


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return PointsAwardedEvent(
        user_id=12345,
        points_amount=100,
        action_type="story_completion",
        multiplier=1.5,
        source_service="narrative",
        correlation_id="test-correlation-123",
    )


@pytest.fixture
def sample_handler():
    """Create a sample event handler for testing."""

    class TestHandler(BaseEventHandler):
        def __init__(self):
            super().__init__("test_service", "test_handler_1")
            self.add_supported_event_type(EventType.POINTS_AWARDED)
            self.processed_events = []
            self.should_fail = False
            self.should_retry = True

        async def _process_event(self, event: IEvent) -> bool:
            if self.should_fail:
                raise Exception("Handler configured to fail")

            self.processed_events.append(event)
            return True

        async def on_error(self, event: IEvent, error: Exception) -> bool:
            return self.should_retry

    return TestHandler()


class TestBaseEvent:
    """Test the BaseEvent implementation."""

    def test_base_event_creation(self):
        """Test creating a BaseEvent instance."""
        event = BaseEvent(
            _event_id="test-123",
            _event_type="test.event",
            _timestamp=datetime.utcnow(),
            _source_service="test_service",
            _correlation_id="corr-123",
            _priority=EventPriority.HIGH,
            _payload={"key": "value"},
        )

        assert event.event_id == "test-123"
        assert event.event_type == "test.event"
        assert event.source_service == "test_service"
        assert event.correlation_id == "corr-123"
        assert event.priority == EventPriority.HIGH
        assert event.payload == {"key": "value"}

    def test_base_event_validation(self):
        """Test event validation."""
        # Valid event should pass
        event = BaseEvent(
            _event_id="test-123",
            _event_type="test.event",
            _timestamp=datetime.utcnow(),
            _source_service="test_service",
        )
        assert event.validate() is True

        # Invalid event should raise
        with pytest.raises(EventValidationError):
            BaseEvent(
                _event_id="",  # Empty ID should fail
                _event_type="test.event",
                _timestamp=datetime.utcnow(),
                _source_service="test_service",
            )

    def test_event_serialization(self):
        """Test event to_dict and from_dict."""
        original_event = BaseEvent(
            _event_id="test-123",
            _event_type="test.event",
            _timestamp=datetime(2024, 1, 1, 12, 0, 0),
            _source_service="test_service",
            _correlation_id="corr-123",
            _priority=EventPriority.HIGH,
            _payload={"key": "value", "number": 42},
        )

        # Serialize
        event_dict = original_event.to_dict()

        # Deserialize
        restored_event = BaseEvent.from_dict(event_dict)

        # Verify
        assert restored_event.event_id == original_event.event_id
        assert restored_event.event_type == original_event.event_type
        assert restored_event.timestamp == original_event.timestamp
        assert restored_event.source_service == original_event.source_service
        assert restored_event.correlation_id == original_event.correlation_id
        assert restored_event.priority == original_event.priority
        assert restored_event.payload == original_event.payload


class TestSpecificEvents:
    """Test domain-specific event implementations."""

    def test_points_awarded_event(self):
        """Test PointsAwardedEvent creation and properties."""
        event = PointsAwardedEvent(
            user_id=12345,
            points_amount=100,
            action_type="story_completion",
            multiplier=1.5,
        )

        assert event.event_type == EventType.POINTS_AWARDED
        assert event.user_id == 12345
        assert event.points_amount == 100
        assert event.action_type == "story_completion"
        assert event.multiplier == 1.5
        assert event.priority == EventPriority.NORMAL
        assert event.source_service == "gamification"

    def test_achievement_unlocked_event(self):
        """Test AchievementUnlockedEvent creation."""
        event = AchievementUnlockedEvent(
            user_id=12345,
            achievement_id="first_story",
            achievement_name="First Story Completed",
            achievement_category="narrative",
            points_reward=500,
        )

        assert event.event_type == EventType.ACHIEVEMENT_UNLOCKED
        assert event.user_id == 12345
        assert event.achievement_id == "first_story"
        assert event.achievement_name == "First Story Completed"
        assert event.priority == EventPriority.HIGH

    def test_user_registered_event(self):
        """Test UserRegisteredEvent creation."""
        event = UserRegisteredEvent(
            user_id=67890,
            username="testuser",
            first_name="Test",
            language_code="en",
            is_premium=True,
        )

        assert event.event_type == EventType.USER_REGISTERED
        assert event.payload["user_id"] == 67890
        assert event.payload["username"] == "testuser"
        assert event.payload["is_premium"] is True
        assert event.priority == EventPriority.HIGH
        assert event.source_service == "telegram_adapter"


class TestEventFactory:
    """Test the EventFactory functionality."""

    def test_event_factory_creation(self):
        """Test creating events through the factory."""
        event = EventFactory.create_event(
            EventType.POINTS_AWARDED,
            user_id=12345,
            points_amount=100,
            action_type="test_action",
        )

        assert isinstance(event, PointsAwardedEvent)
        assert event.user_id == 12345
        assert event.points_amount == 100

    def test_event_factory_unsupported_type(self):
        """Test factory with unsupported event type."""
        with pytest.raises(ValueError):
            EventFactory.create_event("unsupported.event.type")

    def test_event_factory_from_dict(self):
        """Test factory deserialization."""
        event_dict = {
            "event_id": "test-123",
            "event_type": EventType.POINTS_AWARDED,
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "test",
            "priority": EventPriority.NORMAL.value,
            "payload": {
                "user_id": 12345,
                "points_amount": 100,
                "action_type": "test",
                "multiplier": 1.0,
                "total_points_after": None,
            },
        }

        event = EventFactory.from_dict(event_dict)
        assert isinstance(event, PointsAwardedEvent)
        assert event.user_id == 12345

    def test_event_factory_supported_types(self):
        """Test getting supported event types."""
        supported_types = EventFactory.get_supported_event_types()
        assert EventType.POINTS_AWARDED in supported_types
        assert EventType.ACHIEVEMENT_UNLOCKED in supported_types
        assert EventType.USER_REGISTERED in supported_types


class TestBaseEventHandler:
    """Test the BaseEventHandler implementation."""

    @pytest.fixture
    def test_handler(self):
        """Create a test handler."""

        class TestHandler(BaseEventHandler):
            def __init__(self):
                super().__init__("test_service", "test_handler")
                self.add_supported_event_type(EventType.POINTS_AWARDED)
                self.processed_events = []
                self.should_succeed = True

            async def _process_event(self, event: IEvent) -> bool:
                if not self.should_succeed:
                    raise Exception("Test failure")
                self.processed_events.append(event)
                return True

        return TestHandler()

    def test_handler_properties(self, test_handler):
        """Test handler basic properties."""
        assert test_handler.handler_id == "test_handler"
        assert test_handler.service_name == "test_service"
        assert EventType.POINTS_AWARDED in test_handler.supported_event_types

    @pytest.mark.asyncio
    async def test_handler_can_handle(self, test_handler, sample_event):
        """Test handler can_handle method."""
        # Should handle supported event types
        assert await test_handler.can_handle(sample_event) is True

        # Should not handle unsupported event types
        unsupported_event = BaseEvent(
            _event_id="test",
            _event_type="unsupported.event",
            _timestamp=datetime.utcnow(),
            _source_service="test",
        )
        assert await test_handler.can_handle(unsupported_event) is False

    @pytest.mark.asyncio
    async def test_handler_successful_processing(self, test_handler, sample_event):
        """Test successful event processing."""
        result = await test_handler.handle(sample_event)

        assert result is True
        assert len(test_handler.processed_events) == 1
        assert test_handler.processed_events[0] == sample_event

        # Check metrics
        metrics = test_handler.get_performance_metrics()
        assert metrics["processing_count"] == 1
        assert metrics["error_count"] == 0
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_handler_error_handling(self, test_handler, sample_event):
        """Test error handling in event processing."""
        test_handler.should_succeed = False

        with pytest.raises(Exception):
            await test_handler.handle(sample_event)

        # Check metrics
        metrics = test_handler.get_performance_metrics()
        assert metrics["processing_count"] == 0
        assert metrics["error_count"] == 1


class TestRedisEventBus:
    """Test the RedisEventBus implementation."""

    @pytest_asyncio.fixture
    async def event_bus(self, event_bus_config):
        """Create and initialize event bus for testing."""
        bus = RedisEventBus(event_bus_config)

        with patch("redis.asyncio.from_url") as mock_redis_factory:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.publish = AsyncMock(return_value=1)
            mock_redis.close = AsyncMock()

            pubsub_mock = AsyncMock()
            pubsub_mock.subscribe = AsyncMock()
            pubsub_mock.unsubscribe = AsyncMock()
            pubsub_mock.close = AsyncMock()

            # Create a proper async iterator for listen()
            async def async_iter():
                return
                yield  # Never reached, but makes this an async generator

            pubsub_mock.listen = Mock(return_value=async_iter())

            mock_redis.pubsub = Mock(return_value=pubsub_mock)
            mock_redis_factory.return_value = mock_redis

            bus._redis = mock_redis
            bus._pubsub = pubsub_mock

            await bus.initialize()
            yield bus
            await bus.shutdown()

    @pytest.mark.asyncio
    async def test_event_bus_initialization(self, event_bus_config):
        """Test EventBus initialization and shutdown."""
        bus = RedisEventBus(event_bus_config)

        with patch("redis.asyncio.from_url") as mock_redis_factory:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.pubsub = Mock(return_value=AsyncMock())
            mock_redis_factory.return_value = mock_redis

            await bus.initialize()
            assert bus._is_initialized is True

            await bus.shutdown()
            assert bus._is_initialized is False

    @pytest.mark.asyncio
    async def test_event_publishing(self, event_bus, sample_event):
        """Test publishing events to the bus."""
        result = await event_bus.publish(sample_event)

        assert result is True

        # Verify Redis publish was called
        event_bus._redis.publish.assert_called_once()
        call_args = event_bus._redis.publish.call_args
        channel = call_args[0][0]
        message = call_args[0][1]

        assert channel == f"diana:events:{sample_event.event_type}"

        # Verify message format
        message_data = json.loads(message)
        assert message_data["event"]["event_id"] == sample_event.event_id
        assert message_data["event"]["event_type"] == sample_event.event_type

    @pytest.mark.asyncio
    async def test_event_subscription(self, event_bus, sample_handler):
        """Test subscribing to events."""
        subscription_id = await event_bus.subscribe(
            EventType.POINTS_AWARDED, sample_handler
        )

        assert subscription_id is not None
        assert len(subscription_id) > 0

        # Verify subscription is recorded
        subscriptions = await event_bus.get_active_subscriptions()
        assert EventType.POINTS_AWARDED in subscriptions
        assert subscription_id in subscriptions[EventType.POINTS_AWARDED]

        # Verify Redis subscribe was called
        event_bus._pubsub.subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_unsubscription(self, event_bus, sample_handler):
        """Test unsubscribing from events."""
        # First subscribe
        subscription_id = await event_bus.subscribe(
            EventType.POINTS_AWARDED, sample_handler
        )

        # Then unsubscribe
        result = await event_bus.unsubscribe(subscription_id)
        assert result is True

        # Verify subscription is removed
        subscriptions = await event_bus.get_active_subscriptions()
        assert EventType.POINTS_AWARDED not in subscriptions

        # Verify Redis unsubscribe was called
        event_bus._pubsub.unsubscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscription_health(self, event_bus, sample_handler):
        """Test subscription health monitoring."""
        subscription_id = await event_bus.subscribe(
            EventType.POINTS_AWARDED,
            sample_handler,
            service_name=sample_handler.service_name,
        )

        health = await event_bus.get_subscription_health()

        assert subscription_id in health
        sub_health = health[subscription_id]
        assert sub_health["event_type"] == EventType.POINTS_AWARDED
        assert sub_health["service_name"] == sample_handler.service_name
        assert sub_health["handler_id"] == sample_handler.handler_id
        assert sub_health["is_active"] is True

    @pytest.mark.asyncio
    async def test_event_bus_metrics(self, event_bus, sample_event):
        """Test EventBus metrics tracking."""
        # Publish an event to generate metrics
        await event_bus.publish(sample_event)

        metrics = await event_bus.get_metrics()

        assert metrics["events_published"] == 1
        assert metrics["is_healthy"] is True
        assert "last_activity" in metrics
        assert "active_subscriptions" in metrics

    @pytest.mark.asyncio
    async def test_publish_failure_handling(self, event_bus, sample_event):
        """Test handling of publish failures."""
        # Mock Redis to raise an exception
        event_bus._redis.publish.side_effect = Exception("Redis connection failed")

        with pytest.raises(EventPublishError):
            await event_bus.publish(sample_event)

    @pytest.mark.asyncio
    async def test_subscription_failure_handling(self, event_bus, sample_handler):
        """Test handling of subscription failures."""
        # Mock pubsub to raise an exception
        event_bus._pubsub.subscribe.side_effect = Exception("Subscription failed")

        with pytest.raises(EventSubscriptionError):
            await event_bus.subscribe(EventType.POINTS_AWARDED, sample_handler)

    # Event Processing Tests
    @pytest.fixture
    def mock_message(self, sample_event):
        """Create a mock Redis message."""
        message_data = {
            "event": sample_event.to_dict(),
            "target_services": None,
            "published_at": datetime.utcnow().isoformat(),
            "message_id": str(uuid.uuid4()),
        }

        return {
            "type": "message",
            "channel": f"diana:events:{sample_event.event_type}",
            "data": json.dumps(message_data),
        }

    @pytest.mark.asyncio
    async def test_message_processing(self, event_bus, sample_handler, mock_message):
        """Test processing of Redis messages."""
        # Subscribe to events
        await event_bus.subscribe(EventType.POINTS_AWARDED, sample_handler)

        # Process the message
        await event_bus._process_message(mock_message)

        # Wait a bit for processing to complete
        await asyncio.sleep(0.1)

        # Verify handler was called
        assert len(sample_handler.processed_events) == 1

    @pytest.mark.asyncio
    async def test_retry_logic(self, event_bus, sample_event):
        """Test retry logic for failed event processing."""

        # Create a handler that fails initially
        class FailingHandler(BaseEventHandler):
            def __init__(self):
                super().__init__("test", "failing_handler")
                self.add_supported_event_type(EventType.POINTS_AWARDED)
                self.call_count = 0
                self.max_failures = 2

            async def _process_event(self, event: IEvent) -> bool:
                self.call_count += 1
                if self.call_count <= self.max_failures:
                    raise Exception("Simulated failure")
                return True

        failing_handler = FailingHandler()
        subscription = Subscription(
            subscription_id="test-sub",
            event_type=EventType.POINTS_AWARDED,
            handler=failing_handler,
            service_name="test",
            created_at=datetime.utcnow(),
        )

        # Test retry logic
        result = await event_bus._handle_event_with_retry(sample_event, subscription)

        # Should succeed after retries
        assert result.success is True
        assert result.retry_count == 2
        assert failing_handler.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, event_bus, sample_event):
        """Test retry exhaustion for persistently failing handlers."""

        # Create a handler that always fails
        class AlwaysFailingHandler(BaseEventHandler):
            def __init__(self):
                super().__init__("test", "always_failing_handler")
                self.add_supported_event_type(EventType.POINTS_AWARDED)
                self.call_count = 0

            async def _process_event(self, event: IEvent) -> bool:
                self.call_count += 1
                raise Exception("Always fails")

        failing_handler = AlwaysFailingHandler()
        subscription = Subscription(
            subscription_id="test-sub",
            event_type=EventType.POINTS_AWARDED,
            handler=failing_handler,
            service_name="test",
            created_at=datetime.utcnow(),
        )

        # Test retry exhaustion
        result = await event_bus._handle_event_with_retry(sample_event, subscription)

        # Should fail after exhausting retries
        assert result.success is False
        assert result.retry_count > event_bus.config.max_retry_attempts
        assert failing_handler.call_count == event_bus.config.max_retry_attempts + 1


class TestEventBusIntegration:
    """Integration tests for complete Event Bus workflows."""

    @pytest.mark.asyncio
    async def test_complete_event_workflow(self, event_bus_config):
        """Test a complete event publishing and handling workflow."""
        bus = RedisEventBus(event_bus_config)

        with patch("redis.asyncio.from_url") as mock_redis_factory:
            # Setup mocks
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.publish = AsyncMock(return_value=1)
            mock_redis.close = AsyncMock()

            pubsub_mock = AsyncMock()
            pubsub_mock.subscribe = AsyncMock()
            pubsub_mock.close = AsyncMock()

            # Mock the listen method to yield our test message
            event = PointsAwardedEvent(
                user_id=12345, points_amount=100, action_type="test"
            )

            message_data = {
                "event": event.to_dict(),
                "target_services": None,
                "published_at": datetime.utcnow().isoformat(),
                "message_id": str(uuid.uuid4()),
            }

            test_message = {
                "type": "message",
                "channel": f"diana:events:{event.event_type}",
                "data": json.dumps(message_data),
            }

            async def mock_listen():
                yield test_message
                # Simulate shutdown
                await asyncio.sleep(0.1)

            pubsub_mock.listen = mock_listen
            mock_redis.pubsub = Mock(return_value=pubsub_mock)
            mock_redis_factory.return_value = mock_redis

            try:
                # Initialize
                await bus.initialize()

                # Create and subscribe handler
                class IntegrationTestHandler(BaseEventHandler):
                    def __init__(self):
                        super().__init__("integration_test", "handler_1")
                        self.add_supported_event_type(EventType.POINTS_AWARDED)
                        self.events_received = []

                    async def _process_event(self, event: IEvent) -> bool:
                        self.events_received.append(event)
                        return True

                handler = IntegrationTestHandler()
                subscription_id = await bus.subscribe(EventType.POINTS_AWARDED, handler)

                # Publish event
                await bus.publish(event)

                # Start message processing briefly
                processing_task = asyncio.create_task(bus._message_processing_loop())
                await asyncio.sleep(0.2)  # Let it process messages
                processing_task.cancel()

                try:
                    await processing_task
                except asyncio.CancelledError:
                    pass

                # Verify results
                assert mock_redis.publish.called
                assert len(handler.events_received) >= 1
                # Check that our event was processed (there might be duplicate processing in mocks)
                event_ids = [e.event_id for e in handler.events_received]
                assert event.event_id in event_ids

                # Check metrics
                metrics = await bus.get_metrics()
                assert metrics["events_published"] == 1

                # Cleanup
                await bus.unsubscribe(subscription_id)

            finally:
                await bus.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
