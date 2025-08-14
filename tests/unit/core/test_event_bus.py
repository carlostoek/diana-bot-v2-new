"""
TDD Tests for Event Bus Implementation

These tests define the exact behavior expected from the EventBus implementation,
focusing on Redis pub/sub integration, async operations, and production requirements.

These tests should initially FAIL (RED phase) until the EventBus is implemented.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from diana_bot.core.events import EventBus, IEvent
from diana_bot.core.exceptions import EventBusError, PublishError, SubscribeError


class TestEventBusImplementation:
    """
    Tests for the concrete EventBus implementation with Redis backend.

    Tests cover:
    - Redis connection management and failover
    - Pub/sub pattern implementation
    - Event serialization/deserialization
    - Error handling and resilience
    - Performance characteristics
    - Production monitoring and metrics
    """

    @pytest.fixture
    async def redis_mock(self):
        """Mock Redis client for testing."""
        redis_mock = AsyncMock()
        redis_mock.ping.return_value = True
        redis_mock.publish.return_value = 1  # Number of subscribers
        redis_mock.subscribe.return_value = AsyncMock()
        redis_mock.unsubscribe.return_value = None
        redis_mock.close.return_value = None
        return redis_mock

    @pytest.fixture
    async def event_bus(self, redis_mock):
        """Create EventBus instance with mocked Redis."""
        with patch("diana_bot.core.events.redis.Redis", return_value=redis_mock):
            bus = EventBus(redis_url="redis://localhost:6379/0")
            await bus.initialize()
            yield bus
            await bus.cleanup()

    @pytest.fixture
    def sample_event(self):
        """Create sample event for testing."""
        return IEvent(
            type="game.points_earned",
            data={"user_id": 12345, "points": 100, "action": "daily_login"},
        )

    @pytest.mark.asyncio
    async def test_event_bus_initialization(self, redis_mock):
        """Test EventBus initializes correctly with Redis connection."""
        with patch("diana_bot.core.events.redis.Redis", return_value=redis_mock):
            bus = EventBus(redis_url="redis://localhost:6379/0")
            await bus.initialize()

            # Should connect to Redis
            redis_mock.ping.assert_called_once()

            await bus.cleanup()

    @pytest.mark.asyncio
    async def test_event_bus_initialization_failure(self):
        """Test EventBus handles Redis connection failures gracefully."""
        failing_redis = AsyncMock()
        failing_redis.ping.side_effect = ConnectionError("Redis unavailable")

        with patch("diana_bot.core.events.redis.Redis", return_value=failing_redis):
            bus = EventBus(redis_url="redis://localhost:6379/0")

            with pytest.raises(EventBusError):
                await bus.initialize()

    @pytest.mark.asyncio
    async def test_event_bus_publish_success(self, event_bus, redis_mock, sample_event):
        """Test successful event publishing to Redis."""
        await event_bus.publish(sample_event)

        # Should publish to Redis with correct channel and data
        redis_mock.publish.assert_called_once()
        call_args = redis_mock.publish.call_args

        channel = call_args[0][0]
        message = call_args[0][1]

        assert channel == f"events.{sample_event.type}"

        # Message should be serialized event
        parsed_message = json.loads(message)
        assert parsed_message["id"] == sample_event.id
        assert parsed_message["type"] == sample_event.type
        assert parsed_message["data"] == sample_event.data

    @pytest.mark.asyncio
    async def test_event_bus_publish_redis_failure(
        self, event_bus, redis_mock, sample_event
    ):
        """Test publish handles Redis failures correctly."""
        redis_mock.publish.side_effect = ConnectionError("Redis connection lost")

        with pytest.raises(PublishError):
            await event_bus.publish(sample_event)

    @pytest.mark.asyncio
    async def test_event_bus_publish_serialization_failure(
        self, event_bus, sample_event
    ):
        """Test publish handles serialization failures."""
        # Create event with non-serializable data
        bad_event = IEvent(
            type="test.event", data={"function": lambda x: x}  # Non-serializable
        )

        with pytest.raises(PublishError):
            await event_bus.publish(bad_event)

    @pytest.mark.asyncio
    async def test_event_bus_subscribe_success(self, event_bus, redis_mock):
        """Test successful subscription to event type."""
        handler = AsyncMock()

        # Mock Redis pubsub
        pubsub_mock = AsyncMock()
        redis_mock.pubsub.return_value = pubsub_mock

        await event_bus.subscribe("game.points_earned", handler)

        # Should create pubsub subscription
        pubsub_mock.subscribe.assert_called_with("events.game.points_earned")

    @pytest.mark.asyncio
    async def test_event_bus_subscribe_wildcard(self, event_bus, redis_mock):
        """Test wildcard subscription support."""
        handler = AsyncMock()

        pubsub_mock = AsyncMock()
        redis_mock.pubsub.return_value = pubsub_mock

        await event_bus.subscribe("game.*", handler)

        # Should subscribe to pattern
        pubsub_mock.psubscribe.assert_called_with("events.game.*")

    @pytest.mark.asyncio
    async def test_event_bus_subscribe_redis_failure(self, event_bus, redis_mock):
        """Test subscribe handles Redis failures correctly."""
        handler = AsyncMock()

        pubsub_mock = AsyncMock()
        pubsub_mock.subscribe.side_effect = ConnectionError("Redis connection lost")
        redis_mock.pubsub.return_value = pubsub_mock

        with pytest.raises(SubscribeError):
            await event_bus.subscribe("test.event", handler)

    @pytest.mark.asyncio
    async def test_event_bus_unsubscribe_success(self, event_bus, redis_mock):
        """Test successful unsubscription."""
        handler = AsyncMock()

        pubsub_mock = AsyncMock()
        redis_mock.pubsub.return_value = pubsub_mock

        await event_bus.subscribe("test.event", handler)
        await event_bus.unsubscribe("test.event", handler)

        # Should unsubscribe from channel
        pubsub_mock.unsubscribe.assert_called_with("events.test.event")

    @pytest.mark.asyncio
    async def test_event_bus_message_processing(self, event_bus, redis_mock):
        """Test that received Redis messages are properly processed."""
        handler = AsyncMock()

        # Setup pubsub mock
        pubsub_mock = AsyncMock()
        redis_mock.pubsub.return_value = pubsub_mock

        # Mock received message
        event_data = {
            "id": str(uuid.uuid4()),
            "type": "game.points_earned",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"user_id": 123, "points": 50},
        }

        message = {
            "type": "message",
            "channel": "events.game.points_earned",
            "data": json.dumps(event_data).encode(),
        }

        # Setup async iteration for pubsub
        async def mock_listen():
            yield message

        pubsub_mock.listen.return_value = mock_listen()

        await event_bus.subscribe("game.points_earned", handler)

        # Allow message processing
        await asyncio.sleep(0.1)

        # Handler should be called with reconstructed event
        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert called_event.id == event_data["id"]
        assert called_event.type == event_data["type"]
        assert called_event.data == event_data["data"]

    @pytest.mark.asyncio
    async def test_event_bus_handler_isolation(self, event_bus, redis_mock):
        """Test that handler exceptions don't affect other handlers."""
        working_handler = AsyncMock()
        failing_handler = AsyncMock(side_effect=Exception("Handler error"))

        pubsub_mock = AsyncMock()
        redis_mock.pubsub.return_value = pubsub_mock

        await event_bus.subscribe("test.event", working_handler)
        await event_bus.subscribe("test.event", failing_handler)

        # Mock message
        event_data = {
            "id": str(uuid.uuid4()),
            "type": "test.event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"test": True},
        }

        message = {
            "type": "message",
            "channel": "events.test.event",
            "data": json.dumps(event_data).encode(),
        }

        async def mock_listen():
            yield message

        pubsub_mock.listen.return_value = mock_listen()

        # Should not raise exception
        await asyncio.sleep(0.1)

        # Working handler should still be called
        working_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_bus_connection_recovery(self, redis_mock):
        """Test EventBus recovers from Redis connection losses."""
        with patch("diana_bot.core.events.redis.Redis", return_value=redis_mock):
            bus = EventBus(redis_url="redis://localhost:6379/0", reconnect_retries=3)

            # Initial connection succeeds
            await bus.initialize()

            # Connection fails
            redis_mock.ping.side_effect = ConnectionError("Connection lost")

            # Should attempt reconnection
            health = await bus.health_check()
            assert health["status"] == "degraded"

            # Connection recovers
            redis_mock.ping.side_effect = None
            redis_mock.ping.return_value = True

            await asyncio.sleep(0.1)  # Allow reconnection

            health = await bus.health_check()
            assert health["status"] == "healthy"

            await bus.cleanup()

    @pytest.mark.asyncio
    async def test_event_bus_event_persistence(
        self, event_bus, redis_mock, sample_event
    ):
        """Test that events are persisted for audit/replay."""
        # Mock Redis list operations for persistence
        redis_mock.lpush.return_value = 1
        redis_mock.lrange.return_value = [json.dumps(sample_event.to_dict()).encode()]

        await event_bus.publish(sample_event)

        # Should persist event
        redis_mock.lpush.assert_called_once()
        call_args = redis_mock.lpush.call_args
        assert call_args[0][0] == "events.history"

        # Should be able to retrieve events
        events = await event_bus.get_published_events(limit=10)
        assert len(events) == 1
        assert events[0].id == sample_event.id

    @pytest.mark.asyncio
    async def test_event_bus_event_replay(self, event_bus, redis_mock):
        """Test event replay functionality."""
        handler = AsyncMock()

        # Mock historical events
        historical_events = [
            {
                "id": str(uuid.uuid4()),
                "type": "game.points_earned",
                "timestamp": (
                    datetime.now(timezone.utc) - timedelta(minutes=5)
                ).isoformat(),
                "data": {"user_id": 123, "points": 10},
            },
            {
                "id": str(uuid.uuid4()),
                "type": "game.points_earned",
                "timestamp": (
                    datetime.now(timezone.utc) - timedelta(minutes=3)
                ).isoformat(),
                "data": {"user_id": 123, "points": 20},
            },
        ]

        redis_mock.lrange.return_value = [
            json.dumps(event).encode() for event in historical_events
        ]

        await event_bus.subscribe("game.points_earned", handler)

        # Replay events from last 10 minutes
        since = datetime.now(timezone.utc) - timedelta(minutes=10)
        await event_bus.replay_events(event_types=["game.points_earned"], since=since)

        # Handler should receive both replayed events
        assert handler.call_count == 2

    @pytest.mark.asyncio
    async def test_event_bus_batch_operations(self, event_bus, redis_mock):
        """Test batch publishing for efficiency."""
        events = [IEvent(type="batch.event", data={"index": i}) for i in range(10)]

        # Mock Redis pipeline
        pipeline_mock = AsyncMock()
        redis_mock.pipeline.return_value = pipeline_mock

        await event_bus.publish_batch(events)

        # Should use Redis pipeline for efficiency
        redis_mock.pipeline.assert_called_once()
        assert pipeline_mock.publish.call_count == 10
        pipeline_mock.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_bus_rate_limiting(self, event_bus, redis_mock, sample_event):
        """Test that event bus implements rate limiting."""
        # Configure rate limiting
        event_bus.configure_rate_limit(max_events=5, time_window=1.0)

        # Should allow events within limit
        for i in range(5):
            await event_bus.publish(sample_event)

        # Should reject events over limit
        with pytest.raises(PublishError):
            await event_bus.publish(sample_event)

    @pytest.mark.asyncio
    async def test_event_bus_dead_letter_queue(self, event_bus, redis_mock):
        """Test that failed events go to dead letter queue."""
        failing_handler = AsyncMock(side_effect=Exception("Processing failed"))

        pubsub_mock = AsyncMock()
        redis_mock.pubsub.return_value = pubsub_mock

        await event_bus.subscribe("test.event", failing_handler)

        event_data = {
            "id": str(uuid.uuid4()),
            "type": "test.event",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"test": True},
        }

        message = {
            "type": "message",
            "channel": "events.test.event",
            "data": json.dumps(event_data).encode(),
        }

        async def mock_listen():
            yield message

        pubsub_mock.listen.return_value = mock_listen()

        await asyncio.sleep(0.1)

        # Failed event should be added to dead letter queue
        redis_mock.lpush.assert_called_with(
            "events.dead_letter", json.dumps(event_data)
        )

    @pytest.mark.asyncio
    async def test_event_bus_metrics_collection(
        self, event_bus, redis_mock, sample_event
    ):
        """Test that event bus collects operational metrics."""
        handler = AsyncMock()
        await event_bus.subscribe("game.points_earned", handler)
        await event_bus.publish(sample_event)

        stats = await event_bus.get_statistics()

        assert stats["total_events_published"] >= 1
        assert stats["total_subscribers"] >= 1
        assert "game.points_earned" in stats["events_by_type"]
        assert stats["events_by_type"]["game.points_earned"] >= 1
        assert "avg_publish_time_ms" in stats
        assert "avg_handler_time_ms" in stats

    @pytest.mark.asyncio
    async def test_event_bus_health_monitoring(self, event_bus, redis_mock):
        """Test event bus health check functionality."""
        redis_mock.ping.return_value = True

        health = await event_bus.health_check()

        assert health["status"] == "healthy"
        assert health["redis_connected"] is True
        assert "subscribers_count" in health
        assert "events_published" in health
        assert "memory_usage" in health
        assert "last_publish_time" in health

    @pytest.mark.asyncio
    async def test_event_bus_circuit_breaker(self, event_bus, redis_mock):
        """Test circuit breaker pattern for Redis failures."""
        # Configure circuit breaker
        event_bus.configure_circuit_breaker(failure_threshold=3, recovery_timeout=5.0)

        sample_event = IEvent(type="test.event", data={})

        # Simulate Redis failures
        redis_mock.publish.side_effect = ConnectionError("Redis down")

        # Should fail and open circuit after threshold
        for i in range(3):
            with pytest.raises(PublishError):
                await event_bus.publish(sample_event)

        # Circuit should be open - immediate failures
        with pytest.raises(PublishError):
            await event_bus.publish(sample_event)

        # Should not call Redis when circuit is open
        assert redis_mock.publish.call_count == 3

    @pytest.mark.asyncio
    async def test_event_bus_graceful_shutdown(self, event_bus, redis_mock):
        """Test graceful shutdown procedures."""
        handler = AsyncMock()
        await event_bus.subscribe("test.event", handler)

        # Start shutdown
        await event_bus.shutdown(timeout=5.0)

        # Should close Redis connections
        redis_mock.close.assert_called_once()

        # Should reject new operations after shutdown
        with pytest.raises(EventBusError):
            await event_bus.publish(IEvent(type="test.event", data={}))

    @pytest.mark.asyncio
    async def test_event_bus_performance_publish(self, event_bus, redis_mock):
        """Test publish performance meets <10ms requirement."""
        sample_event = IEvent(type="perf.test", data={"test": True})

        # Measure publish performance
        times = []
        for _ in range(10):
            start = asyncio.get_event_loop().time()
            await event_bus.publish(sample_event)
            end = asyncio.get_event_loop().time()
            times.append((end - start) * 1000)  # Convert to ms

        avg_time = sum(times) / len(times)
        p95_time = sorted(times)[int(0.95 * len(times))]

        assert avg_time < 10.0, f"Average publish time {avg_time}ms > 10ms"
        assert p95_time < 10.0, f"95th percentile publish time {p95_time}ms > 10ms"

    @pytest.mark.asyncio
    async def test_event_bus_performance_subscribe(self, event_bus, redis_mock):
        """Test subscribe performance meets <1ms requirement."""
        handler = AsyncMock()

        # Measure subscribe performance
        times = []
        for i in range(10):
            start = asyncio.get_event_loop().time()
            await event_bus.subscribe(f"perf.test.{i}", handler)
            end = asyncio.get_event_loop().time()
            times.append((end - start) * 1000)  # Convert to ms

        avg_time = sum(times) / len(times)
        p95_time = sorted(times)[int(0.95 * len(times))]

        assert avg_time < 1.0, f"Average subscribe time {avg_time}ms > 1ms"
        assert p95_time < 1.0, f"95th percentile subscribe time {p95_time}ms > 1ms"

    @pytest.mark.asyncio
    async def test_event_bus_concurrent_load(self, event_bus, redis_mock):
        """Test event bus handles concurrent load correctly."""
        handlers = [AsyncMock() for _ in range(10)]

        # Subscribe multiple handlers
        for i, handler in enumerate(handlers):
            await event_bus.subscribe(f"load.test.{i}", handler)

        # Publish events concurrently
        events = [
            IEvent(type=f"load.test.{i % 10}", data={"index": i}) for i in range(100)
        ]

        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(*[event_bus.publish(event) for event in events])
        end_time = asyncio.get_event_loop().time()

        # Should handle load efficiently
        total_time = end_time - start_time
        throughput = len(events) / total_time

        assert throughput > 100, f"Throughput {throughput} events/sec too low"
        assert redis_mock.publish.call_count == 100

    @pytest.mark.asyncio
    async def test_event_bus_memory_efficiency(self, event_bus, redis_mock):
        """Test that event bus manages memory efficiently."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create many subscriptions and events
        handlers = [AsyncMock() for _ in range(1000)]
        for i, handler in enumerate(handlers):
            await event_bus.subscribe(f"memory.test.{i}", handler)

        # Publish many events
        for i in range(1000):
            event = IEvent(type=f"memory.test.{i % 100}", data={"data": "x" * 100})
            await event_bus.publish(event)

        # Clean up subscriptions
        for i, handler in enumerate(handlers):
            await event_bus.unsubscribe(f"memory.test.{i}", handler)

        # Force garbage collection
        gc.collect()

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (< 50MB for this test)
        assert (
            memory_growth < 50 * 1024 * 1024
        ), f"Memory growth {memory_growth} bytes too high"


class TestEventBusIntegrationReadiness:
    """
    Tests that verify EventBus is ready for Redis integration.
    These tests use mocks but verify the integration contracts.
    """

    @pytest.mark.asyncio
    async def test_redis_connection_string_parsing(self):
        """Test that EventBus correctly parses Redis connection strings."""
        test_urls = [
            "redis://localhost:6379/0",
            "redis://user:pass@redis.example.com:6379/1",
            "rediss://secure-redis.example.com:6380/0",  # SSL
            "redis://localhost:6379?socket_timeout=5&socket_connect_timeout=5",
        ]

        for url in test_urls:
            with patch("diana_bot.core.events.redis.Redis") as mock_redis:
                mock_client = AsyncMock()
                mock_client.ping.return_value = True
                mock_redis.return_value = mock_client

                bus = EventBus(redis_url=url)
                await bus.initialize()

                # Should create Redis client with correct parameters
                mock_redis.assert_called_once()

                await bus.cleanup()

    @pytest.mark.asyncio
    async def test_redis_cluster_support(self):
        """Test that EventBus supports Redis cluster configuration."""
        cluster_nodes = [
            {"host": "redis-node-1", "port": 6379},
            {"host": "redis-node-2", "port": 6379},
            {"host": "redis-node-3", "port": 6379},
        ]

        with patch("diana_bot.core.events.redis.RedisCluster") as mock_cluster:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_cluster.return_value = mock_client

            bus = EventBus(cluster_nodes=cluster_nodes)
            await bus.initialize()

            # Should create Redis cluster client
            mock_cluster.assert_called_once()

            await bus.cleanup()

    @pytest.mark.asyncio
    async def test_redis_sentinel_support(self):
        """Test that EventBus supports Redis Sentinel for high availability."""
        sentinel_config = {
            "sentinels": [("sentinel-1", 26379), ("sentinel-2", 26379)],
            "service_name": "diana-redis",
            "password": "redis-password",
        }

        with patch("diana_bot.core.events.redis.Sentinel") as mock_sentinel:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_sentinel.return_value.master_for.return_value = mock_client

            bus = EventBus(sentinel_config=sentinel_config)
            await bus.initialize()

            # Should create Sentinel client
            mock_sentinel.assert_called_once()

            await bus.cleanup()

    @pytest.mark.asyncio
    async def test_event_compression_support(self):
        """Test that EventBus supports event compression for large payloads."""
        large_data = {"large_field": "x" * 10000}  # 10KB of data
        large_event = IEvent(type="large.event", data=large_data)

        with patch("diana_bot.core.events.redis.Redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            bus = EventBus(redis_url="redis://localhost:6379", enable_compression=True)
            await bus.initialize()

            await bus.publish(large_event)

            # Should publish compressed data
            mock_client.publish.assert_called_once()
            call_args = mock_client.publish.call_args
            published_data = call_args[0][1]

            # Compressed data should be smaller than original
            original_size = len(json.dumps(large_event.to_dict()))
            compressed_size = len(published_data)

            assert compressed_size < original_size

            await bus.cleanup()

    @pytest.mark.asyncio
    async def test_event_encryption_support(self):
        """Test that EventBus supports event encryption for sensitive data."""
        sensitive_event = IEvent(
            type="user.payment",
            data={"user_id": 123, "amount": 99.99, "card_last_four": "1234"},
        )

        with patch("diana_bot.core.events.redis.Redis") as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client

            bus = EventBus(
                redis_url="redis://localhost:6379",
                encryption_key="test-encryption-key-32-chars!!",
            )
            await bus.initialize()

            await bus.publish(sensitive_event)

            # Should publish encrypted data
            mock_client.publish.assert_called_once()
            call_args = mock_client.publish.call_args
            published_data = call_args[0][1]

            # Encrypted data should not contain plaintext sensitive info
            assert "1234" not in published_data
            assert "99.99" not in published_data

            await bus.cleanup()
