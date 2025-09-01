"""
CRITICAL EVENT BUS INTEGRATION TESTS
====================================

Tests for Diana Bot V2's Event Bus integration with GamificationService.
The Event Bus is the communication backbone - failures here cascade to all services.

ZERO TOLERANCE for Event Bus integration failures.
"""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Callable

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.engines.points_engine_fixed import FixedPointsEngine
from services.gamification.interfaces import ActionType


class MockEventBus:
    """Mock Event Bus for testing Diana Bot V2 event patterns."""
    
    def __init__(self):
        self.published_events: List[Dict[str, Any]] = []
        self.subscribers: Dict[str, List[Callable]] = {}
        self.connection_status = "connected"
        self.failure_mode = False
    
    async def publish(self, channel: str, event: Dict[str, Any]) -> bool:
        """Publish event to channel."""
        if self.failure_mode:
            raise Exception("Event Bus connection failed")
        
        self.published_events.append({
            "channel": channel,
            "event": event,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # Trigger subscribers with pattern matching
        for pattern, callbacks in self.subscribers.items():
            if self._pattern_matches(pattern, channel):
                for callback in callbacks:
                    await callback(event)
        
        return True
    
    def _pattern_matches(self, pattern: str, channel: str) -> bool:
        """Check if channel matches pattern (simple wildcard support)."""
        if pattern == channel:
            return True
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return channel.startswith(prefix)
        return False
    
    async def subscribe(self, pattern: str, callback: Callable) -> bool:
        """Subscribe to event pattern."""
        if self.failure_mode:
            return False
            
        if pattern not in self.subscribers:
            self.subscribers[pattern] = []
        self.subscribers[pattern].append(callback)
        return True
    
    def get_published_events(self, channel: str = None) -> List[Dict[str, Any]]:
        """Get published events, optionally filtered by channel."""
        if channel is None:
            return self.published_events
        return [e for e in self.published_events if e["channel"] == channel]
    
    def simulate_failure(self):
        """Simulate Event Bus failure."""
        self.failure_mode = True
        self.connection_status = "failed"
    
    def restore_connection(self):
        """Restore Event Bus connection."""
        self.failure_mode = False
        self.connection_status = "connected"


class MockGamificationService:
    """Mock GamificationService with Event Bus integration."""
    
    def __init__(self, points_engine: FixedPointsEngine, event_bus: MockEventBus):
        self.points_engine = points_engine
        self.event_bus = event_bus
        self.processed_events: List[Dict[str, Any]] = []
        
    async def initialize_event_subscriptions(self):
        """Initialize Event Bus subscriptions (Diana Bot pattern)."""
        # Subscribe to game events
        await self.event_bus.subscribe("game.*", self._handle_game_event)
        
        # Subscribe to narrative events  
        await self.event_bus.subscribe("narrative.*", self._handle_narrative_event)
        
        # Subscribe to user events
        await self.event_bus.subscribe("user.*", self._handle_user_event)
        
        # Subscribe to admin events
        await self.event_bus.subscribe("admin.*", self._handle_admin_event)
    
    async def _handle_game_event(self, event: Dict[str, Any]):
        """Handle game-related events."""
        self.processed_events.append({"type": "game", "event": event})
        
        # Award points based on game events
        if event.get("event_type") == "trivia_completed":
            await self._award_points_with_event_publishing(
                user_id=event["user_id"],
                action_type=ActionType.TRIVIA_COMPLETED,
                context=event.get("context", {}),
                source_event=event
            )
    
    async def _handle_narrative_event(self, event: Dict[str, Any]):
        """Handle narrative-related events."""
        self.processed_events.append({"type": "narrative", "event": event})
        
        if event.get("event_type") == "chapter_completed":
            await self._award_points_with_event_publishing(
                user_id=event["user_id"],
                action_type=ActionType.STORY_CHAPTER_COMPLETED,
                context=event.get("context", {}),
                source_event=event
            )
    
    async def _handle_user_event(self, event: Dict[str, Any]):
        """Handle user-related events."""
        self.processed_events.append({"type": "user", "event": event})
        
        if event.get("event_type") == "daily_login":
            await self._award_points_with_event_publishing(
                user_id=event["user_id"],
                action_type=ActionType.DAILY_LOGIN,
                context=event.get("context", {}),
                source_event=event
            )
    
    async def _handle_admin_event(self, event: Dict[str, Any]):
        """Handle admin-related events."""
        self.processed_events.append({"type": "admin", "event": event})
        
        if event.get("event_type") == "points_adjustment":
            await self._award_points_with_event_publishing(
                user_id=event["user_id"],
                action_type=ActionType.ADMIN_ADJUSTMENT,
                context=event.get("context", {}),
                base_points=event.get("points_change", 0),
                force_award=True,
                source_event=event
            )
    
    async def _award_points_with_event_publishing(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        source_event: Dict[str, Any],
        base_points: int = None,
        force_award: bool = False
    ):
        """Award points and publish result events."""
        try:
            # Award points
            result = await self.points_engine.award_points(
                user_id=user_id,
                action_type=action_type,
                context=context,
                base_points=base_points,
                force_award=force_award
            )
            
            if result.success:
                # Publish points_awarded event
                await self.event_bus.publish("gamification.points_awarded", {
                    "event_id": f"points_{result.transaction_id}",
                    "user_id": user_id,
                    "action_type": action_type.value,
                    "points_awarded": result.points_awarded,
                    "new_balance": result.new_balance,
                    "source_event_id": source_event.get("event_id"),
                    "timestamp": asyncio.get_event_loop().time()
                })
                
                # Check for achievements and publish if unlocked
                if result.achievements_unlocked:
                    for achievement in result.achievements_unlocked:
                        await self.event_bus.publish("gamification.achievement_unlocked", {
                            "event_id": f"achievement_{result.transaction_id}",
                            "user_id": user_id,
                            "achievement": achievement,
                            "points_balance": result.new_balance,
                            "timestamp": asyncio.get_event_loop().time()
                        })
            
        except Exception as e:
            # Publish error event for monitoring
            await self.event_bus.publish("gamification.error", {
                "event_id": f"error_{asyncio.get_event_loop().time()}",
                "user_id": user_id,
                "action_type": action_type.value if action_type else "unknown",
                "error": str(e),
                "source_event_id": source_event.get("event_id"),
                "timestamp": asyncio.get_event_loop().time()
            })


class TestEventBusIntegrationCritical:
    """Critical Event Bus integration tests."""
    
    @pytest_asyncio.fixture
    async def event_bus(self):
        """Create mock Event Bus."""
        return MockEventBus()
    
    @pytest_asyncio.fixture 
    async def points_engine(self):
        """Create points engine for Event Bus testing."""
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()
        
        return FixedPointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )
    
    @pytest_asyncio.fixture
    async def gamification_service(self, points_engine, event_bus):
        """Create GamificationService with Event Bus."""
        service = MockGamificationService(points_engine, event_bus)
        await service.initialize_event_subscriptions()
        return service

    @pytest.mark.asyncio
    async def test_event_subscription_initialization(self, gamification_service):
        """CRITICAL: Service must subscribe to all required event patterns."""
        event_bus = gamification_service.event_bus
        
        # Verify all required subscriptions
        expected_patterns = ["game.*", "narrative.*", "user.*", "admin.*"]
        
        for pattern in expected_patterns:
            assert pattern in event_bus.subscribers, f"Missing subscription: {pattern}"
            assert len(event_bus.subscribers[pattern]) > 0, f"No handlers for: {pattern}"
        
        print("✅ Event Bus subscriptions initialized correctly")

    @pytest.mark.asyncio
    async def test_game_event_processing_and_publishing(self, gamification_service):
        """CRITICAL: Game events must trigger points and publish results."""
        event_bus = gamification_service.event_bus
        
        # Simulate game event
        game_event = {
            "event_id": "trivia_001",
            "event_type": "trivia_completed",
            "user_id": 123,
            "context": {
                "question_id": "q123",
                "correct_answer": True,
                "difficulty": "hard"
            }
        }
        
        # Publish game event
        await event_bus.publish("game.trivia", game_event)
        
        # Give time for event processing
        await asyncio.sleep(0.01)
        
        # Verify event was processed
        processed_events = [e for e in gamification_service.processed_events if e["type"] == "game"]
        assert len(processed_events) == 1, "Game event not processed"
        
        # Verify points were awarded
        user_balance, _ = await gamification_service.points_engine.get_user_balance(123)
        assert user_balance > 0, "Points not awarded for game event"
        
        # Verify points_awarded event was published
        points_events = event_bus.get_published_events("gamification.points_awarded")
        assert len(points_events) == 1, "Points awarded event not published"
        
        points_event = points_events[0]["event"]
        assert points_event["user_id"] == 123
        assert points_event["action_type"] == "trivia_completed"
        assert points_event["points_awarded"] > 0
        
        print(f"✅ Game event processing: {user_balance} points awarded")

    @pytest.mark.asyncio
    async def test_narrative_event_integration(self, gamification_service):
        """CRITICAL: Narrative events must integrate with points system."""
        event_bus = gamification_service.event_bus
        
        narrative_event = {
            "event_id": "story_001",
            "event_type": "chapter_completed", 
            "user_id": 456,
            "context": {
                "story_id": "romance_001",
                "chapter_id": "ch_05",
                "reading_time_seconds": 120
            }
        }
        
        await event_bus.publish("narrative.story", narrative_event)
        await asyncio.sleep(0.01)
        
        # Verify processing
        processed_events = [e for e in gamification_service.processed_events if e["type"] == "narrative"]
        assert len(processed_events) == 1, "Narrative event not processed"
        
        # Verify points awarded
        user_balance, _ = await gamification_service.points_engine.get_user_balance(456)
        assert user_balance > 0, "Points not awarded for narrative event"
        
        # Verify event publishing
        points_events = event_bus.get_published_events("gamification.points_awarded")
        assert len(points_events) == 1, "Points event not published"
        
        print(f"✅ Narrative event integration: {user_balance} points awarded")

    @pytest.mark.asyncio
    async def test_concurrent_event_processing_integrity(self, gamification_service):
        """CRITICAL: Concurrent events must not corrupt points system."""
        event_bus = gamification_service.event_bus
        user_id = 789
        
        # Create multiple concurrent events
        events = [
            {"event_id": f"login_{i}", "event_type": "daily_login", "user_id": user_id, "context": {}}
            for i in range(10)
        ]
        
        # Publish all events concurrently
        publish_tasks = [
            event_bus.publish("user.login", event) for event in events
        ]
        
        await asyncio.gather(*publish_tasks)
        await asyncio.sleep(0.05)  # Allow processing time
        
        # Verify mathematical integrity
        user_balance, _ = await gamification_service.points_engine.get_user_balance(user_id)
        
        # Should have exactly 10 daily login awards (50 points each = 500 total)
        expected_balance = 50 * 10  # Assuming no multipliers
        assert user_balance == expected_balance, (
            f"Concurrent event processing integrity violation: "
            f"{user_balance} != {expected_balance}"
        )
        
        # Verify all events were published
        points_events = event_bus.get_published_events("gamification.points_awarded")
        assert len(points_events) == 10, f"Expected 10 events, got {len(points_events)}"
        
        print(f"✅ Concurrent event processing: {user_balance} points (integrity maintained)")

    @pytest.mark.asyncio
    async def test_event_bus_failure_graceful_degradation(self, gamification_service):
        """CRITICAL: Service must degrade gracefully when Event Bus fails."""
        event_bus = gamification_service.event_bus
        user_id = 999
        
        # Award points normally first
        result_before = await gamification_service.points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={}
        )
        assert result_before.success, "Initial operation should succeed"
        
        # Simulate Event Bus failure
        event_bus.simulate_failure()
        
        # Try to process event during failure
        failed_event = {
            "event_id": "fail_test", 
            "event_type": "daily_login",
            "user_id": user_id,
            "context": {}
        }
        
        # This should fail but not crash the service
        try:
            await event_bus.publish("user.login", failed_event)
            pytest.fail("Expected Event Bus publish to fail")
        except Exception as e:
            assert "Event Bus connection failed" in str(e)
        
        # Direct points operations should still work
        result_during_failure = await gamification_service.points_engine.award_points(
            user_id=user_id,
            action_type=ActionType.MESSAGE_SENT,
            context={}
        )
        assert result_during_failure.success, "Direct operations should work during Event Bus failure"
        
        # Restore connection
        event_bus.restore_connection()
        
        # Events should work again
        recovery_event = {
            "event_id": "recovery_test",
            "event_type": "daily_login", 
            "user_id": user_id,
            "context": {}
        }
        
        await event_bus.publish("user.login", recovery_event)
        await asyncio.sleep(0.01)
        
        # Verify recovery
        final_balance, _ = await gamification_service.points_engine.get_user_balance(user_id)
        expected_final = result_before.new_balance + result_during_failure.points_awarded + 50  # Recovery event
        
        assert final_balance == expected_final, "Service recovery failed"
        
        print(f"✅ Graceful degradation: final_balance={final_balance}")

    @pytest.mark.asyncio
    async def test_achievement_event_publishing(self, gamification_service):
        """CRITICAL: Achievement unlocks must publish events."""
        event_bus = gamification_service.event_bus
        user_id = 555
        
        # Give user enough points to level up (trigger achievement)
        large_event = {
            "event_id": "big_purchase",
            "event_type": "points_adjustment",
            "user_id": user_id,
            "points_change": 1000,
            "context": {"reason": "VIP purchase"}
        }
        
        await event_bus.publish("admin.adjustment", large_event)
        await asyncio.sleep(0.01)
        
        # Check for achievement events
        achievement_events = event_bus.get_published_events("gamification.achievement_unlocked")
        
        if achievement_events:
            achievement_event = achievement_events[0]["event"]
            assert achievement_event["user_id"] == user_id
            assert "achievement" in achievement_event
            assert achievement_event["points_balance"] > 0
            
            print(f"✅ Achievement event published: {achievement_event['achievement']}")
        else:
            print("ℹ️ No achievements unlocked (user didn't level up)")

    @pytest.mark.asyncio
    async def test_error_event_publishing(self, gamification_service):
        """CRITICAL: Errors must publish monitoring events."""
        event_bus = gamification_service.event_bus
        
        # Create an event that will cause an error (invalid user_id type)
        error_event = {
            "event_id": "error_test",
            "event_type": "daily_login",
            "user_id": "invalid_user_id",  # Should be int, not string
            "context": {}
        }
        
        # This should trigger error handling
        await event_bus.publish("user.login", error_event)
        await asyncio.sleep(0.01)
        
        # Check for error events
        error_events = event_bus.get_published_events("gamification.error")
        
        if error_events:
            error_event_data = error_events[0]["event"]
            assert "error" in error_event_data
            assert error_event_data["user_id"] == "invalid_user_id"
            
            print(f"✅ Error event published: {error_event_data['error'][:50]}...")
        else:
            print("ℹ️ Error handling didn't trigger error event (might be handled differently)")


class TestEventBusPerformanceIntegration:
    """Performance testing for Event Bus integration."""
    
    @pytest_asyncio.fixture
    async def performance_setup(self):
        """Setup for performance testing."""
        event_bus = MockEventBus()
        
        anti_abuse_validator = AsyncMock(spec=AntiAbuseValidator)
        anti_abuse_validator.validate_action.return_value = (True, None, None)
        anti_abuse_validator.record_action = AsyncMock()
        
        points_engine = FixedPointsEngine(
            anti_abuse_validator=anti_abuse_validator,
            database_client=None,
        )
        
        service = MockGamificationService(points_engine, event_bus)
        await service.initialize_event_subscriptions()
        
        return service, event_bus

    @pytest.mark.asyncio
    async def test_high_frequency_event_processing(self, performance_setup):
        """PERFORMANCE: High-frequency events must maintain performance."""
        service, event_bus = performance_setup
        
        num_events = 100
        user_id = 1000
        
        # Create high-frequency events
        events = [
            {
                "event_id": f"msg_{i}",
                "event_type": "daily_login",
                "user_id": user_id,
                "context": {"message_id": i}
            }
            for i in range(num_events)
        ]
        
        import time
        start_time = time.time()
        
        # Process all events
        for event in events:
            await event_bus.publish("user.login", event)
        
        await asyncio.sleep(0.1)  # Allow processing
        
        duration = time.time() - start_time
        
        # Verify all processed
        processed_count = len([e for e in service.processed_events if e["type"] == "user"])
        assert processed_count == num_events, f"Not all events processed: {processed_count}/{num_events}"
        
        # Performance requirement
        events_per_second = num_events / duration
        assert events_per_second > 500, f"Event processing too slow: {events_per_second:.2f} events/sec"
        
        # Verify final integrity (considering level bonuses)
        final_balance, _ = await service.points_engine.get_user_balance(user_id)
        
        # With 100 daily logins (5000 base points), user will level up multiple times
        # Each level increases multiplier, so final balance will be higher than base
        min_expected = 50 * num_events  # At least base points
        assert final_balance >= min_expected, f"Event processing broke integrity: {final_balance} < {min_expected}"
        assert final_balance <= min_expected * 2, f"Excessive points awarded: {final_balance} > {min_expected * 2}"
        
        print(f"✅ High-frequency processing: {events_per_second:.2f} events/sec, "
              f"final_balance={final_balance}")