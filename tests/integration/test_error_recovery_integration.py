"""
Error Recovery Integration Tests

This module tests how the system handles and recovers from various error conditions
across service boundaries, ensuring that failures in one component don't compromise
the entire system. These tests validate the resilience aspects of the Event Bus,
UserService, and GamificationService integration.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio

from src.core.events import EventBus
from src.core.interfaces import IEvent
from services.gamification.interfaces import ActionType
from services.gamification.service import GamificationService, GamificationServiceError


class FaultyEventHandler:
    """Helper class that simulates faulty event handlers."""

    def __init__(self, failure_mode="exception", failure_count=3):
        self.failure_mode = failure_mode  # "exception", "hang", or "corrupt"
        self.calls = 0
        self.failure_count = failure_count
        self.events_received = []

    async def __call__(self, event: IEvent) -> None:
        """Event handler implementation that fails in specified ways."""
        self.calls += 1
        self.events_received.append(event)

        # Only fail for the specified number of calls
        if self.calls <= self.failure_count:
            if self.failure_mode == "exception":
                raise Exception(f"Simulated handler failure for event {event.id}")
            elif self.failure_mode == "hang":
                # Simulate a hanging handler
                await asyncio.sleep(2.0)
            elif self.failure_mode == "corrupt":
                # Corrupt the event data (not always possible due to immutability)
                try:
                    # Attempt to corrupt the event data
                    event.data["corrupted"] = True
                except (AttributeError, TypeError):
                    # If we can't modify the event, we'll raise an exception instead
                    raise Exception("Attempted to corrupt event data")


class ServiceDisruptor:
    """Helper class to disrupt services during tests."""

    def __init__(self, event_bus: EventBus, gamification_service: GamificationService):
        self.event_bus = event_bus
        self.gamification_service = gamification_service

    async def disrupt_event_bus(self, duration=0.5):
        """Temporarily disrupt the Event Bus (simulate network issues)."""
        # Save original state
        original_connected = self.event_bus._is_connected

        # Disrupt connection
        self.event_bus._is_connected = False

        # Wait for specified duration
        await asyncio.sleep(duration)

        # Restore connection
        self.event_bus._is_connected = original_connected

    async def disrupt_gamification_service(self, duration=0.5):
        """Temporarily disrupt the Gamification Service."""
        # Save original state
        original_initialized = self.gamification_service._initialized

        # Disrupt service
        self.gamification_service._initialized = False

        # Wait for specified duration
        await asyncio.sleep(duration)

        # Restore service
        self.gamification_service._initialized = original_initialized


class TestErrorRecoveryIntegration:
    """Test error recovery and resilience across service boundaries."""

    @pytest_asyncio.fixture
    async def event_bus(self):
        """Create Event Bus instance for testing."""
        bus = EventBus(test_mode=True)
        await bus.initialize()
        yield bus
        await bus.cleanup()

    @pytest_asyncio.fixture
    async def gamification_service(self, event_bus):
        """Create GamificationService with Event Bus."""
        service = GamificationService(event_bus=event_bus)
        await service.initialize()
        yield service
        await service.cleanup()

    @pytest_asyncio.fixture
    async def disruptor(self, event_bus, gamification_service):
        """Create service disruptor."""
        return ServiceDisruptor(event_bus, gamification_service)

    @pytest.mark.asyncio
    async def test_event_handler_exceptions(self, event_bus, gamification_service):
        """Test that exceptions in event handlers don't crash the system."""
        # Set up a handler that will throw exceptions
        faulty_handler = FaultyEventHandler(failure_mode="exception", failure_count=3)

        # Subscribe the faulty handler to game events
        event_type = "game.test_event"
        await event_bus.subscribe(event_type, faulty_handler)

        try:
            # Create and publish test events
            from core.events import GameEvent

            for i in range(5):
                event = GameEvent(
                    user_id=1000,
                    action="test_action",
                    points_earned=10,
                    context={"test_id": i},
                )
                event._type = event_type  # Force the event type

                # This should not raise exceptions to the caller
                await event_bus.publish(event)

                # Small delay to allow processing
                await asyncio.sleep(0.05)

            # Verify that the handler was called for all events despite exceptions
            assert faulty_handler.calls == 5, "Handler was not called for all events"
            assert (
                len(faulty_handler.events_received) == 5
            ), "Not all events were received"

            # Verify that Event Bus is still operational
            health = await event_bus.health_check()
            assert health["status"] in [
                "healthy",
                "degraded",
            ], f"Event Bus unhealthy: {health['status']}"

        finally:
            # Clean up subscription
            await event_bus.unsubscribe(event_type, faulty_handler)

    @pytest.mark.asyncio
    async def test_hanging_event_handlers(self, event_bus, gamification_service):
        """Test that slow/hanging event handlers don't block the system."""
        # Set up a handler that will hang
        hanging_handler = FaultyEventHandler(failure_mode="hang", failure_count=2)

        # Subscribe the hanging handler
        event_type = "game.slow_event"
        await event_bus.subscribe(event_type, hanging_handler)

        try:
            # Start timing
            start_time = asyncio.get_event_loop().time()

            # Create and publish test events
            from core.events import GameEvent

            # This will publish 3 events, 2 of which will trigger 2-second hangs
            # But the entire operation should not take 4+ seconds due to concurrency
            for i in range(3):
                event = GameEvent(
                    user_id=1001,
                    action="slow_action",
                    points_earned=10,
                    context={"test_id": i},
                )
                event._type = event_type
                await event_bus.publish(event)

            # Wait for all events to be processed
            # But with a shorter timeout than the total hang time would be
            await asyncio.sleep(1.0)

            # Measure time taken
            elapsed = asyncio.get_event_loop().time() - start_time

            # System should still be responsive
            health = await event_bus.health_check()
            assert health["status"] in [
                "healthy",
                "degraded",
            ], "Event Bus should remain healthy"

            # Validate that the system didn't wait for all handlers to complete
            # before continuing (should be processing concurrently)
            assert (
                elapsed < 4.0
            ), f"System was blocked by hanging handlers (elapsed: {elapsed}s)"

        finally:
            # Clean up subscription
            await event_bus.unsubscribe(event_type, hanging_handler)

    @pytest.mark.asyncio
    async def test_service_disruption_recovery(
        self, event_bus, gamification_service, disruptor
    ):
        """Test that the system recovers after temporary service disruptions."""
        user_id = int(uuid.uuid4().int % 100000000)

        # First, verify services are working normally
        result1 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.LOGIN,
            context={"test": "pre-disruption"},
        )
        assert result1.success is True, "Service not working before disruption"

        # Disrupt the Event Bus
        await disruptor.disrupt_event_bus(duration=0.5)

        # Attempt operations during disruption
        try:
            await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.LOGIN,
                context={"test": "during-disruption"},
            )
            # The operation may succeed or fail depending on timing
        except Exception:
            # Exception is acceptable during disruption
            pass

        # Wait for recovery
        await asyncio.sleep(0.6)

        # Verify system recovers
        try:
            result2 = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.LOGIN,
                context={"test": "post-disruption"},
            )
            assert (
                result2.success is True
            ), "Service did not recover after Event Bus disruption"

            # Check EventBus health
            health = await event_bus.health_check()
            assert health["status"] in [
                "healthy",
                "degraded",
            ], "Event Bus failed to recover"

        except Exception as e:
            pytest.fail(f"System failed to recover after disruption: {e}")

    @pytest.mark.asyncio
    async def test_service_restart_recovery(self, event_bus, gamification_service):
        """Test that the system recovers after service restarts."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create initial state
        result1 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.LOGIN,
            context={"test": "pre-restart"},
        )
        assert result1.success is True

        # Simulate service restart by calling cleanup and initialize again
        await gamification_service.cleanup()
        await asyncio.sleep(0.1)
        await gamification_service.initialize()
        await asyncio.sleep(0.1)

        # Verify service recovered after restart
        result2 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.LOGIN,
            context={"test": "post-restart"},
        )
        assert result2.success is True, "Service did not recover after restart"

        # Check user data persisted
        stats = await gamification_service.get_user_stats(user_id)
        assert (
            stats.total_points >= result1.points_awarded
        ), "User data not preserved after restart"

    @pytest.mark.asyncio
    async def test_event_publishing_errors(self, event_bus, gamification_service):
        """Test that failed event publishing is handled gracefully."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Force the Event Bus into a disconnected state
        original_connected = event_bus._is_connected
        event_bus._is_connected = False

        try:
            # Attempt to publish events via GamificationService
            # This should fail gracefully without crashing the service
            try:
                result = await gamification_service.process_user_action(
                    user_id=user_id,
                    action_type=ActionType.LOGIN,
                    context={"test": "disconnected"},
                )
                # Operation may fail due to disconnected Event Bus
            except Exception:
                # Exception is expected here
                pass

            # Restore connection
            event_bus._is_connected = original_connected
            await asyncio.sleep(0.1)

            # Service should still function after failure
            result = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.LOGIN,
                context={"test": "reconnected"},
            )
            assert (
                result.success is True
            ), "Service did not recover after publishing failure"

        finally:
            # Ensure we restore the connection state
            event_bus._is_connected = original_connected

    @pytest.mark.asyncio
    async def test_partial_system_failure(
        self, event_bus, gamification_service, disruptor
    ):
        """Test that the system continues partial operation during component failures."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Initial successful operation
        result1 = await gamification_service.process_user_action(
            user_id=user_id, action_type=ActionType.LOGIN, context={"test": "initial"}
        )
        assert result1.success is True

        # Disrupt Gamification Service
        await disruptor.disrupt_gamification_service(duration=0.5)

        # Event Bus should still function even if Gamification Service is down
        # Test by publishing an event directly
        from core.events import GameEvent

        direct_event = GameEvent(
            user_id=user_id,
            action="test_action",
            points_earned=10,
            context={"direct": True},
        )

        # This should succeed even with GamificationService disrupted
        try:
            await event_bus.publish(direct_event)
            event_bus_operational = True
        except Exception:
            event_bus_operational = False

        assert (
            event_bus_operational
        ), "Event Bus failed during GamificationService disruption"

        # Wait for recovery
        await asyncio.sleep(0.6)

        # System should recover fully
        result2 = await gamification_service.process_user_action(
            user_id=user_id, action_type=ActionType.LOGIN, context={"test": "recovered"}
        )
        assert (
            result2.success is True
        ), "System did not recover fully after partial failure"

    @pytest.mark.asyncio
    async def test_data_integrity_during_failures(
        self, event_bus, gamification_service, disruptor
    ):
        """Test that data integrity is maintained during service disruptions."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create initial state and track points
        result1 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.LOGIN,
            context={"test": "integrity-initial"},
        )
        assert result1.success is True

        initial_stats = await gamification_service.get_user_stats(user_id)
        initial_points = initial_stats.total_points

        # Perform a sequence of operations with disruptions in between

        # Operation 1
        result2 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"test": "integrity-1", "score": 100},
        )
        points_from_op1 = result2.points_awarded

        # Disrupt Event Bus
        await disruptor.disrupt_event_bus(duration=0.3)

        # Operation 2 (may fail due to disruption)
        try:
            result3 = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"test": "integrity-2"},
            )
            points_from_op2 = result3.points_awarded if result3.success else 0
        except Exception:
            points_from_op2 = 0

        # Disrupt Gamification Service
        await disruptor.disrupt_gamification_service(duration=0.3)

        # Operation 3 (may fail due to disruption)
        try:
            result4 = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.DAILY_LOGIN,
                context={"test": "integrity-3"},
            )
            points_from_op3 = result4.points_awarded if result4.success else 0
        except Exception:
            points_from_op3 = 0

        # Wait for recovery
        await asyncio.sleep(0.5)

        # Operation 4 (should succeed after recovery)
        result5 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.STORY_CHAPTER_COMPLETED,
            context={"test": "integrity-4", "chapter": "test"},
        )
        assert result5.success is True
        points_from_op4 = result5.points_awarded

        # Get final state
        final_stats = await gamification_service.get_user_stats(user_id)
        final_points = final_stats.total_points

        # Calculate expected points (only from successful operations)
        expected_points = (
            initial_points
            + points_from_op1
            + points_from_op2
            + points_from_op3
            + points_from_op4
        )

        # Verify data integrity with reasonable margin for any rounding differences
        assert (
            abs(final_points - expected_points) <= 1
        ), f"Points integrity error: expected {expected_points}, got {final_points}"

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, event_bus, gamification_service):
        """Test that circuit breaker patterns recover properly."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Configure a stricter circuit breaker for testing
        event_bus.configure_circuit_breaker(
            failure_threshold=2,  # Open circuit after 2 failures
            recovery_timeout=0.5,  # Half second timeout for recovery
        )

        # Force the circuit breaker into open state
        event_bus._circuit_breaker_failures = 3
        event_bus._circuit_breaker_state = "open"
        event_bus._circuit_breaker_last_failure = asyncio.get_event_loop().time()

        # First attempt should fail due to open circuit
        with pytest.raises(Exception):
            await event_bus.publish(
                IEvent.from_dict(
                    {
                        "id": "test-1",
                        "type": "test.circuit_breaker",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {"test": True},
                    }
                )
            )

        # Wait for circuit breaker timeout
        await asyncio.sleep(0.6)  # Just over the recovery timeout

        # Circuit should be in half-open state now
        assert (
            event_bus._circuit_breaker_state == "half-open"
        ), "Circuit breaker did not transition to half-open"

        # Next attempt should succeed and close the circuit
        try:
            await event_bus.publish(
                IEvent.from_dict(
                    {
                        "id": "test-2",
                        "type": "test.circuit_breaker",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {"test": True},
                    }
                )
            )
        except Exception as e:
            pytest.fail(f"Circuit breaker did not allow retry in half-open state: {e}")

        # Circuit should be closed now
        assert (
            event_bus._circuit_breaker_state == "closed"
        ), "Circuit breaker did not reset to closed"

        # System should function normally
        health = await event_bus.health_check()
        assert (
            health["status"] == "healthy"
        ), "System unhealthy after circuit breaker recovery"
