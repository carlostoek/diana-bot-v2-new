"""
Performance Integration Tests

This module benchmarks the performance characteristics of the integrated system,
specifically focusing on the integration between EventBus, UserService, and
GamificationService under various load conditions.
"""

import asyncio
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio

from core.events import EventBus
from core.interfaces import IEvent
from modules.user.events import OnboardingStartedEvent, UserCreatedEvent
from services.gamification.interfaces import ActionType
from services.gamification.service import GamificationService


class PerformanceStats:
    """Helper class for collecting and analyzing performance statistics."""

    def __init__(self):
        self.operation_times = {}
        self.event_processing_times = {}

    def record_operation_time(self, operation_name, duration_ms):
        """Record the duration of an operation."""
        if operation_name not in self.operation_times:
            self.operation_times[operation_name] = []

        self.operation_times[operation_name].append(duration_ms)

    def record_event_processing_time(self, event_type, duration_ms):
        """Record the processing time for an event."""
        if event_type not in self.event_processing_times:
            self.event_processing_times[event_type] = []

        self.event_processing_times[event_type].append(duration_ms)

    def get_operation_stats(self, operation_name):
        """Get statistics for a specific operation."""
        if (
            operation_name not in self.operation_times
            or not self.operation_times[operation_name]
        ):
            return None

        times = self.operation_times[operation_name]
        return {
            "count": len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "avg_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)],
            "p99_ms": (
                sorted(times)[int(len(times) * 0.99)]
                if len(times) >= 100
                else max(times)
            ),
        }

    def get_event_processing_stats(self, event_type):
        """Get statistics for a specific event type."""
        if (
            event_type not in self.event_processing_times
            or not self.event_processing_times[event_type]
        ):
            return None

        times = self.event_processing_times[event_type]
        return {
            "count": len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "avg_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)],
            "p99_ms": (
                sorted(times)[int(len(times) * 0.99)]
                if len(times) >= 100
                else max(times)
            ),
        }

    def get_summary(self):
        """Get a summary of all performance statistics."""
        summary = {"operations": {}, "events": {}}

        for op_name in self.operation_times:
            summary["operations"][op_name] = self.get_operation_stats(op_name)

        for event_type in self.event_processing_times:
            summary["events"][event_type] = self.get_event_processing_stats(event_type)

        return summary


class EventMonitor:
    """Helper class for monitoring events and their processing times."""

    def __init__(self, stats: PerformanceStats):
        self.stats = stats
        self.event_start_times = {}
        self.events_received = []

    async def __call__(self, event: IEvent):
        """Event handler that records processing times."""
        event_id = event.id
        event_type = event.type

        # Record event receipt
        self.events_received.append(
            {
                "id": event_id,
                "type": event_type,
                "timestamp": datetime.now(timezone.utc),
            }
        )

        # Calculate processing time if we have a start time
        if event_id in self.event_start_times:
            start_time = self.event_start_times[event_id]
            duration_ms = (time.time() - start_time) * 1000

            self.stats.record_event_processing_time(event_type, duration_ms)

            # Clean up start time
            del self.event_start_times[event_id]

    def record_event_start(self, event_id):
        """Record the start time of an event."""
        self.event_start_times[event_id] = time.time()


class InstrumentedGamificationService(GamificationService):
    """Instrumented version of GamificationService for performance testing."""

    def __init__(self, event_bus, stats: PerformanceStats, event_monitor: EventMonitor):
        super().__init__(event_bus=event_bus)
        self.stats = stats
        self.event_monitor = event_monitor

    async def process_user_action(self, user_id, action_type, context):
        """Instrumented version of process_user_action that records performance metrics."""
        start_time = time.time()

        # Execute original method
        result = await super().process_user_action(user_id, action_type, context)

        # Record performance metrics
        duration_ms = (time.time() - start_time) * 1000
        self.stats.record_operation_time(
            f"process_user_action_{action_type.value}", duration_ms
        )

        return result


class MockUserService:
    """Mock UserService with instrumentation for performance testing."""

    def __init__(self, event_bus, stats: PerformanceStats, event_monitor: EventMonitor):
        self.event_bus = event_bus
        self.stats = stats
        self.event_monitor = event_monitor
        self.users = {}

    async def create_user(self, user_id, first_name, username=None):
        """Create a user with performance metrics."""
        start_time = time.time()

        # Store user
        self.users[user_id] = {
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "created_at": datetime.now(timezone.utc),
        }

        # Create event
        event = UserCreatedEvent(
            user_id=user_id,
            first_name=first_name,
            username=username,
            language_code="en",
        )

        # Record event start for latency measurement
        self.event_monitor.record_event_start(event.id)

        # Publish event
        await self.event_bus.publish(event)

        # Record performance metrics
        duration_ms = (time.time() - start_time) * 1000
        self.stats.record_operation_time("create_user", duration_ms)

        return user_id

    async def start_onboarding(self, user_id):
        """Start onboarding with performance metrics."""
        start_time = time.time()

        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")

        # Create event
        event = OnboardingStartedEvent(
            user_id=user_id,
            first_name=self.users[user_id]["first_name"],
            language_code="en",
            adaptive_context={"source": "performance_test"},
        )

        # Record event start for latency measurement
        self.event_monitor.record_event_start(event.id)

        # Publish event
        await self.event_bus.publish(event)

        # Record performance metrics
        duration_ms = (time.time() - start_time) * 1000
        self.stats.record_operation_time("start_onboarding", duration_ms)


@pytest.mark.skip(reason="Performance tests might be too slow for regular testing")
class TestPerformanceIntegration:
    """Performance tests for integrated services."""

    @pytest_asyncio.fixture
    async def performance_stats(self):
        """Create performance stats collector."""
        return PerformanceStats()

    @pytest_asyncio.fixture
    async def event_monitor(self, performance_stats):
        """Create event monitor."""
        return EventMonitor(performance_stats)

    @pytest_asyncio.fixture
    async def event_bus(self, event_monitor):
        """Create instrumented Event Bus."""
        bus = EventBus(test_mode=True)
        await bus.initialize()

        # Subscribe the event monitor to all events
        await bus.subscribe("*", event_monitor)

        yield bus

        # Clean up
        await bus.unsubscribe("*", event_monitor)
        await bus.cleanup()

    @pytest_asyncio.fixture
    async def gamification_service(self, event_bus, performance_stats, event_monitor):
        """Create instrumented GamificationService."""
        service = InstrumentedGamificationService(
            event_bus=event_bus, stats=performance_stats, event_monitor=event_monitor
        )
        await service.initialize()
        yield service
        await service.cleanup()

    @pytest_asyncio.fixture
    async def user_service(self, event_bus, performance_stats, event_monitor):
        """Create instrumented UserService."""
        service = MockUserService(
            event_bus=event_bus, stats=performance_stats, event_monitor=event_monitor
        )
        return service

    @pytest.mark.asyncio
    async def test_single_user_performance(
        self, event_bus, gamification_service, user_service, performance_stats
    ):
        """Test performance for single user operations."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        await user_service.create_user(
            user_id=user_id, first_name="PerformanceUser", username="perf_test"
        )

        # Allow events to process
        await asyncio.sleep(0.1)

        # Perform a series of user actions
        action_types = [
            ActionType.LOGIN,
            ActionType.MESSAGE_SENT,
            ActionType.TRIVIA_COMPLETED,
            ActionType.STORY_CHAPTER_COMPLETED,
            ActionType.DAILY_LOGIN,
        ]

        for action_type in action_types:
            await gamification_service.process_user_action(
                user_id=user_id,
                action_type=action_type,
                context={"test": "performance"},
            )

            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.05)

        # Allow all events to process
        await asyncio.sleep(0.2)

        # Get performance summary
        summary = performance_stats.get_summary()

        # Output results
        for op_name, stats in summary["operations"].items():
            print(
                f"Operation {op_name}: avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms"
            )

        for event_type, stats in summary["events"].items():
            print(
                f"Event {event_type}: avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms"
            )

        # Check that metrics were collected
        assert len(summary["operations"]) > 0, "No operation metrics collected"
        assert len(summary["events"]) > 0, "No event metrics collected"

        # Check performance requirements
        for op_name, stats in summary["operations"].items():
            assert (
                stats["p95_ms"] < 2000
            ), f"Operation {op_name} exceeds 2000ms at p95: {stats['p95_ms']:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_users_performance(
        self, event_bus, gamification_service, user_service, performance_stats
    ):
        """Test performance with concurrent users."""
        # Create multiple users
        user_count = 10  # Adjust based on test environment capacity
        users = []

        for i in range(user_count):
            user_id = int(uuid.uuid4().int % 100000000)
            await user_service.create_user(
                user_id=user_id,
                first_name=f"ConcurrentUser{i}",
                username=f"concurrent_test_{i}",
            )
            users.append(user_id)

        # Allow user creation events to process
        await asyncio.sleep(0.2)

        # Create a mix of actions for each user
        tasks = []
        for user_id in users:
            # Each user performs multiple actions
            for action_type in [
                ActionType.LOGIN,
                ActionType.MESSAGE_SENT,
                ActionType.TRIVIA_COMPLETED,
            ]:
                tasks.append(
                    gamification_service.process_user_action(
                        user_id=user_id,
                        action_type=action_type,
                        context={"test": "concurrent_performance"},
                    )
                )

        # Execute all actions concurrently
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000

        # Allow events to process
        await asyncio.sleep(0.5)

        # Get performance summary
        summary = performance_stats.get_summary()

        # Output results
        print(
            f"Concurrent operations total time: {total_time:.2f}ms for {len(tasks)} operations"
        )
        print(f"Average time per operation: {total_time/len(tasks):.2f}ms")

        for op_name, stats in summary["operations"].items():
            print(
                f"Operation {op_name}: avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms"
            )

        for event_type, stats in summary["events"].items():
            print(
                f"Event {event_type}: avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms"
            )

        # Verify performance under load
        # Calculate operations per second
        ops_per_second = len(tasks) / (total_time / 1000)
        print(f"Operations per second: {ops_per_second:.2f}")

        # System should handle at least 10 operations per second
        assert (
            ops_per_second >= 10
        ), f"Performance too low: {ops_per_second:.2f} ops/sec"

    @pytest.mark.asyncio
    async def test_event_propagation_latency(
        self, event_bus, gamification_service, user_service, performance_stats
    ):
        """Test end-to-end latency for event propagation."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        await user_service.create_user(
            user_id=user_id, first_name="LatencyUser", username="latency_test"
        )

        # Allow events to process
        await asyncio.sleep(0.1)

        # Monitor full roundtrip - user action to points awarded event
        # Create a special handler for game.points_awarded events
        latency_measurements = []

        async def measure_roundtrip(event):
            if event.type == "game.points_awarded":
                end_time = time.time()
                if hasattr(event, "start_time"):
                    latency = (end_time - event.start_time) * 1000
                    latency_measurements.append(latency)

        # Subscribe to points awarded events
        await event_bus.subscribe("game.points_awarded", measure_roundtrip)

        try:
            # Perform a series of actions and measure roundtrip time
            action_types = [
                ActionType.LOGIN,
                ActionType.MESSAGE_SENT,
                ActionType.TRIVIA_COMPLETED,
                ActionType.STORY_CHAPTER_COMPLETED,
                ActionType.DAILY_LOGIN,
            ]

            for action_type in action_types:
                # Record start time
                start_time = time.time()

                # Track start time for the event that will be published
                result = await gamification_service.process_user_action(
                    user_id=user_id,
                    action_type=action_type,
                    context={"test": "latency", "start_time": start_time},
                )

                # Allow event processing
                await asyncio.sleep(0.1)

            # Allow final events to process
            await asyncio.sleep(0.2)

            # Calculate latency statistics
            if latency_measurements:
                avg_latency = statistics.mean(latency_measurements)
                p95_latency = sorted(latency_measurements)[
                    int(len(latency_measurements) * 0.95)
                ]
                max_latency = max(latency_measurements)

                print(
                    f"Event propagation latency: avg={avg_latency:.2f}ms, p95={p95_latency:.2f}ms, max={max_latency:.2f}ms"
                )

                # Check against requirements (<2000ms for 95% of operations)
                assert p95_latency < 2000, f"Latency too high: p95={p95_latency:.2f}ms"

        finally:
            # Clean up subscription
            await event_bus.unsubscribe("game.points_awarded", measure_roundtrip)

    @pytest.mark.asyncio
    async def test_event_bus_throughput(self, event_bus, performance_stats):
        """Test Event Bus throughput under load."""
        # Create a simple event handler that just counts events
        event_count = 0

        async def count_handler(event):
            nonlocal event_count
            event_count += 1

        # Subscribe handler to all events
        await event_bus.subscribe("test.*", count_handler)

        try:
            # Create a batch of events to publish
            batch_size = 100
            events = []

            from core.events import GameEvent

            for i in range(batch_size):
                event = GameEvent(
                    user_id=1000 + i,
                    action="test_action",
                    points_earned=10,
                    context={"batch_id": i},
                )
                event._type = f"test.event_{i % 10}"  # Create 10 different event types
                events.append(event)

            # Measure throughput
            start_time = time.time()

            # Publish all events
            tasks = []
            for event in events:
                tasks.append(event_bus.publish(event))

            await asyncio.gather(*tasks)

            # Calculate throughput
            duration = time.time() - start_time
            throughput = batch_size / duration

            # Allow events to be processed
            await asyncio.sleep(0.5)

            print(f"Event Bus throughput: {throughput:.2f} events/second")
            print(f"Events published: {batch_size}, events received: {event_count}")

            # Check that most events were received
            assert (
                event_count >= batch_size * 0.9
            ), f"Too many events lost: received {event_count}/{batch_size}"

            # Check throughput requirement - at least 100 events/second
            assert (
                throughput >= 100
            ), f"Throughput too low: {throughput:.2f} events/second"

        finally:
            # Clean up subscription
            await event_bus.unsubscribe("test.*", count_handler)
