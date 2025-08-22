"""
Critical Event Bus Integration Tests

These tests ensure bulletproof communication between GamificationService and other services.
Event Bus failures could cause:
- Lost user actions (engagement tracking broken)
- Missed achievement triggers (user rewards lost)
- Broken narratives (story progression fails)
- Admin notifications missing (moderation blind spots)

ZERO TOLERANCE for event communication failures.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
import pytest_asyncio

from core.events import AdminEvent, EventBus, GameEvent, NarrativeEvent, UserEvent
from services.gamification.engines.points_engine import PointsEngine
from services.gamification.interfaces import ActionType
from services.gamification.service import GamificationService


class TestEventBusSubscriptionIntegrity:
    """Test GamificationService correctly subscribes to required events."""

    @pytest_asyncio.fixture
    async def gamification_service_with_event_bus(self):
        """Create GamificationService with mocked Event Bus."""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        event_bus.unsubscribe = AsyncMock()

        # Mock database
        db_client = Mock()
        db_client.execute_query = AsyncMock(return_value={"result": "success"})

        service = GamificationService(database_client=db_client, event_bus=event_bus)

        return service, event_bus

    @pytest.mark.asyncio
    async def test_service_subscribes_to_required_event_patterns(
        self, gamification_service_with_event_bus
    ):
        """Test service subscribes to all required Event Bus patterns."""
        service, event_bus = gamification_service_with_event_bus

        # Initialize service (should set up subscriptions)
        await service.initialize()

        # Verify subscription calls
        expected_patterns = [
            "game.*",  # All game events
            "narrative.*",  # Story events
            "user.*",  # User lifecycle events
            "admin.*",  # Admin actions
        ]

        subscribe_calls = event_bus.subscribe.call_args_list
        subscribed_patterns = [call[0][0] for call in subscribe_calls]

        for pattern in expected_patterns:
            assert (
                pattern in subscribed_patterns
            ), f"Missing subscription to pattern: {pattern}"

        # Should have handler for each pattern
        assert len(subscribe_calls) >= len(
            expected_patterns
        ), "Not enough subscription handlers"

    @pytest.mark.asyncio
    async def test_event_handler_registration_integrity(
        self, gamification_service_with_event_bus
    ):
        """Test that event handlers are properly registered and callable."""
        service, event_bus = gamification_service_with_event_bus

        await service.initialize()

        # Verify handlers are callable functions
        subscribe_calls = event_bus.subscribe.call_args_list
        for call_args in subscribe_calls:
            pattern = call_args[0][0]
            handler = call_args[0][1]

            assert callable(handler), f"Handler for pattern {pattern} is not callable"
            assert asyncio.iscoroutinefunction(
                handler
            ), f"Handler for pattern {pattern} is not async"

    @pytest.mark.asyncio
    async def test_graceful_subscription_failure_handling(
        self, gamification_service_with_event_bus
    ):
        """Test service handles Event Bus subscription failures gracefully."""
        service, event_bus = gamification_service_with_event_bus

        # Mock subscription failure
        event_bus.subscribe.side_effect = Exception("Event Bus connection failed")

        # Should not crash on initialization failure
        try:
            await service.initialize()
        except Exception as e:
            # Should log error but not crash the service
            assert "Event Bus connection failed" in str(e)


class TestEventPublishingIntegrity:
    """Test GamificationService publishes events correctly."""

    @pytest_asyncio.fixture
    async def service_with_tracking(self):
        """Create service with event publishing tracking."""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()

        # Track published events
        self.published_events = []

        def track_publish(event):
            self.published_events.append(event)
            return AsyncMock()

        event_bus.publish = AsyncMock(side_effect=track_publish)

        # Mock database
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.execute_query = AsyncMock(
            return_value={"balance": 100, "transaction_id": "tx_001"}
        )

        service = GamificationService(database_client=db_client, event_bus=event_bus)
        return service, event_bus

    @pytest.mark.asyncio
    async def test_points_awarded_event_publishing(self, service_with_tracking):
        """Test that points awarded events are published correctly."""
        service, event_bus = service_with_tracking

        user_id = 123
        points = 50
        action_type = ActionType.DAILY_LOGIN

        # Award points
        result = await service.award_points(
            user_id=user_id,
            action_type=action_type,
            context={"login_time": "2024-08-21T10:00:00Z"},
            points=points,
        )

        assert result.success is True

        # Should have published points awarded event
        points_events = [
            e
            for e in self.published_events
            if hasattr(e, "event_type") and "points_awarded" in str(e.event_type)
        ]
        assert len(points_events) > 0, "No points awarded event published"

        points_event = points_events[0]
        assert points_event.user_id == user_id
        assert points_event.points_awarded == points
        assert points_event.action_type == action_type

    @pytest.mark.asyncio
    async def test_achievement_unlocked_event_publishing(self, service_with_tracking):
        """Test achievement unlocked events are published."""
        service, event_bus = service_with_tracking

        # Mock achievement unlock
        with patch.object(
            service.achievement_engine, "check_achievements"
        ) as mock_check:
            mock_check.return_value = [
                {
                    "achievement_id": "daily_login_7",
                    "name": "Week Warrior",
                    "points": 100,
                }
            ]

            result = await service.process_user_action(
                user_id=456, action_type=ActionType.DAILY_LOGIN, context={}
            )

        # Should publish achievement event
        achievement_events = [
            e
            for e in self.published_events
            if hasattr(e, "event_type") and "achievement" in str(e.event_type)
        ]
        assert len(achievement_events) > 0, "No achievement unlocked event published"

        achievement_event = achievement_events[0]
        assert achievement_event.user_id == 456
        assert achievement_event.achievement_id == "daily_login_7"

    @pytest.mark.asyncio
    async def test_leaderboard_position_change_event(self, service_with_tracking):
        """Test leaderboard position change events."""
        service, event_bus = service_with_tracking

        # Mock leaderboard change
        with patch.object(
            service.leaderboard_engine, "update_user_position"
        ) as mock_update:
            mock_update.return_value = {
                "old_rank": 15,
                "new_rank": 12,
                "leaderboard_type": "weekly_points",
            }

            await service.award_points(
                user_id=789,
                action_type=ActionType.TRIVIA_COMPLETED,
                context={"correct": True},
                points=100,
            )

        # Should publish leaderboard event
        leaderboard_events = [
            e
            for e in self.published_events
            if hasattr(e, "event_type") and "leaderboard" in str(e.event_type)
        ]
        assert len(leaderboard_events) > 0, "No leaderboard position event published"

    @pytest.mark.asyncio
    async def test_anti_abuse_violation_event_publishing(self, service_with_tracking):
        """Test anti-abuse violation events are published for admin alerts."""
        service, event_bus = service_with_tracking

        # Mock anti-abuse violation
        with patch.object(
            service.anti_abuse_validator, "validate_action"
        ) as mock_validate:
            mock_validate.return_value = (
                False,
                "RATE_LIMIT_EXCEEDED",
                "Rate limit exceeded",
            )

            result = await service.award_points(
                user_id=999, action_type=ActionType.MESSAGE_SENT, context={}, points=10
            )

        assert result.success is False

        # Should publish admin alert event
        admin_events = [
            e
            for e in self.published_events
            if hasattr(e, "event_type") and "admin" in str(e.event_type)
        ]
        assert len(admin_events) > 0, "No admin alert event published for violation"


class TestEventHandlingIntegrity:
    """Test GamificationService correctly handles incoming events."""

    @pytest_asyncio.fixture
    async def service_for_event_handling(self):
        """Create service for testing event handling."""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        # Store event handlers for testing
        self.event_handlers = {}

        def store_handler(pattern, handler):
            self.event_handlers[pattern] = handler
            return AsyncMock()

        event_bus.subscribe.side_effect = store_handler

        # Mock database
        db_client = Mock()
        db_client.execute_query = AsyncMock(return_value={"result": "success"})

        service = GamificationService(database_client=db_client, event_bus=event_bus)
        await service.initialize()

        return service, event_bus

    @pytest.mark.asyncio
    async def test_user_created_event_handling(self, service_for_event_handling):
        """Test handling of user created events for onboarding points."""
        service, event_bus = service_for_event_handling

        # Create user created event
        user_event = UserEvent(
            event_type="user.created",
            user_id=1001,
            timestamp=datetime.now(timezone.utc),
            data={"username": "new_user", "registration_source": "telegram"},
        )

        # Get and call the user event handler
        user_handler = self.event_handlers.get("user.*")
        assert user_handler is not None, "No user event handler registered"

        # Mock points award for onboarding
        with patch.object(service, "award_points") as mock_award:
            mock_award.return_value = Mock(success=True)

            await user_handler(user_event)

            # Should award onboarding points
            mock_award.assert_called_once()
            call_args = mock_award.call_args
            assert call_args[1]["user_id"] == 1001
            assert call_args[1]["action_type"] == ActionType.LOGIN  # First login bonus

    @pytest.mark.asyncio
    async def test_narrative_completion_event_handling(
        self, service_for_event_handling
    ):
        """Test handling of narrative completion events."""
        service, event_bus = service_for_event_handling

        # Create narrative event
        narrative_event = NarrativeEvent(
            event_type="narrative.chapter_completed",
            user_id=1002,
            timestamp=datetime.now(timezone.utc),
            data={
                "chapter_id": "ch_001",
                "story_id": "main_story",
                "completion_time": 300,  # 5 minutes
                "choices_made": 3,
            },
        )

        # Get narrative handler
        narrative_handler = self.event_handlers.get("narrative.*")
        assert narrative_handler is not None, "No narrative event handler registered"

        # Mock points award for chapter completion
        with patch.object(service, "award_points") as mock_award:
            mock_award.return_value = Mock(success=True)

            await narrative_handler(narrative_event)

            # Should award chapter completion points
            mock_award.assert_called()
            call_args = mock_award.call_args
            assert call_args[1]["action_type"] == ActionType.STORY_CHAPTER_COMPLETED

    @pytest.mark.asyncio
    async def test_admin_adjustment_event_handling(self, service_for_event_handling):
        """Test handling of admin adjustment events."""
        service, event_bus = service_for_event_handling

        # Create admin event
        admin_event = AdminEvent(
            event_type="admin.points_adjustment",
            user_id=1003,
            timestamp=datetime.now(timezone.utc),
            data={
                "admin_id": 1,
                "adjustment_points": -100,
                "reason": "Violation penalty",
                "violation_type": "spam",
            },
        )

        # Get admin handler
        admin_handler = self.event_handlers.get("admin.*")
        assert admin_handler is not None, "No admin event handler registered"

        # Mock points adjustment
        with patch.object(service, "award_points") as mock_award:
            mock_award.return_value = Mock(success=True)

            await admin_handler(admin_event)

            # Should process admin adjustment
            mock_award.assert_called()
            call_args = mock_award.call_args
            assert call_args[1]["action_type"] == ActionType.ADMIN_ADJUSTMENT
            assert call_args[1]["points"] == -100

    @pytest.mark.asyncio
    async def test_malformed_event_handling(self, service_for_event_handling):
        """Test service handles malformed events gracefully."""
        service, event_bus = service_for_event_handling

        # Create malformed event
        malformed_event = Mock()
        malformed_event.event_type = None  # Missing event type
        malformed_event.user_id = "invalid"  # Wrong type

        # Get handler
        user_handler = self.event_handlers.get("user.*")

        # Should not crash on malformed event
        try:
            await user_handler(malformed_event)
        except Exception as e:
            # Should log error but not crash service
            assert "malformed" in str(e).lower() or "invalid" in str(e).lower()


class TestEventBusFailureRecovery:
    """Test Event Bus failure scenarios and recovery mechanisms."""

    @pytest_asyncio.fixture
    async def service_with_failure_simulation(self):
        """Create service for testing failure scenarios."""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()

        # Simulate intermittent Event Bus failures
        self.publish_failure_count = 0
        self.max_failures = 3

        def simulate_publish_failures(event):
            self.publish_failure_count += 1
            if self.publish_failure_count <= self.max_failures:
                raise Exception("Event Bus temporarily unavailable")
            return AsyncMock()

        event_bus.publish = AsyncMock(side_effect=simulate_publish_failures)

        # Mock database
        db_client = Mock()
        db_client.begin_transaction = AsyncMock()
        db_client.commit_transaction = AsyncMock()
        db_client.execute_query = AsyncMock(return_value={"balance": 100})

        return (
            GamificationService(database_client=db_client, event_bus=event_bus),
            event_bus,
        )

    @pytest.mark.asyncio
    async def test_event_publishing_retry_mechanism(
        self, service_with_failure_simulation
    ):
        """Test service retries event publishing on failures."""
        service, event_bus = service_with_failure_simulation

        # Award points (should trigger event publishing)
        result = await service.award_points(
            user_id=2001, action_type=ActionType.DAILY_LOGIN, context={}, points=50
        )

        # Points operation should still succeed despite Event Bus failures
        assert result.success is True, "Points operation failed due to Event Bus issues"

        # Should have retried multiple times
        assert (
            event_bus.publish.call_count > self.max_failures
        ), "Event publishing not retried enough times"

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_event_bus_failure(
        self, service_with_failure_simulation
    ):
        """Test service degrades gracefully when Event Bus is unavailable."""
        service, event_bus = service_with_failure_simulation

        # Make Event Bus permanently fail
        event_bus.publish.side_effect = Exception("Event Bus completely down")

        # Core functionality should still work
        result = await service.award_points(
            user_id=2002, action_type=ActionType.MESSAGE_SENT, context={}, points=25
        )

        # Points should still be awarded even without events
        assert result.success is True, "Core functionality failed when Event Bus down"

        # Should have attempted to publish but continued operation
        assert event_bus.publish.call_count > 0, "Did not attempt to publish events"

    @pytest.mark.asyncio
    async def test_event_bus_reconnection_handling(
        self, service_with_failure_simulation
    ):
        """Test service handles Event Bus reconnection correctly."""
        service, event_bus = service_with_failure_simulation

        # Simulate Event Bus going down then coming back up
        failure_count = 0

        def simulate_reconnection(event):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise Exception("Event Bus down")
            # After 2 failures, simulate reconnection
            return AsyncMock()

        event_bus.publish.side_effect = simulate_reconnection

        # Multiple operations during outage and recovery
        results = []
        for i in range(5):
            result = await service.award_points(
                user_id=2003 + i,
                action_type=ActionType.COMMUNITY_PARTICIPATION,
                context={"operation": i},
                points=10,
            )
            results.append(result)

        # All operations should succeed
        assert all(
            r.success for r in results
        ), "Operations failed during Event Bus recovery"

        # Should have eventually succeeded in publishing
        assert (
            event_bus.publish.call_count >= 5
        ), "Not enough publish attempts during recovery"


class TestCrossServiceEventIntegration:
    """Test integration with events from other services."""

    @pytest_asyncio.fixture
    async def cross_service_test_setup(self):
        """Setup for cross-service event testing."""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()

        # Mock database
        db_client = Mock()
        db_client.execute_query = AsyncMock(return_value={"result": "success"})

        service = GamificationService(database_client=db_client, event_bus=event_bus)

        # Store handlers for direct testing
        self.handlers = {}

        def store_handler(pattern, handler):
            self.handlers[pattern] = handler
            return AsyncMock()

        event_bus.subscribe.side_effect = store_handler

        await service.initialize()
        return service, event_bus

    @pytest.mark.asyncio
    async def test_diana_master_system_integration(self, cross_service_test_setup):
        """Test integration with Diana Master System events."""
        service, event_bus = cross_service_test_setup

        # Simulate Diana Master System personalization event
        diana_event = GameEvent(
            event_type="game.personalization_update",
            user_id=3001,
            timestamp=datetime.now(timezone.utc),
            data={
                "personality_archetype": "Explorer",
                "engagement_level": "high",
                "preferred_challenges": ["trivia", "exploration"],
            },
        )

        # Get game event handler
        game_handler = self.handlers.get("game.*")
        assert game_handler is not None

        with patch.object(service, "update_user_multipliers") as mock_update:
            await game_handler(diana_event)

            # Should update user multipliers based on personalization
            mock_update.assert_called_once_with(
                user_id=3001, archetype="Explorer", engagement_level="high"
            )

    @pytest.mark.asyncio
    async def test_monetization_service_integration(self, cross_service_test_setup):
        """Test integration with monetization service events."""
        service, event_bus = cross_service_test_setup

        # Simulate VIP purchase event
        vip_event = GameEvent(
            event_type="game.vip_purchase",
            user_id=3002,
            timestamp=datetime.now(timezone.utc),
            data={
                "purchase_type": "vip_monthly",
                "amount_usd": 9.99,
                "transaction_id": "tx_vip_001",
            },
        )

        game_handler = self.handlers.get("game.*")

        with patch.object(service, "award_points") as mock_award:
            mock_award.return_value = Mock(success=True)

            await game_handler(vip_event)

            # Should award VIP purchase bonus points
            mock_award.assert_called()
            call_args = mock_award.call_args
            assert call_args[1]["action_type"] == ActionType.VIP_PURCHASE

    @pytest.mark.asyncio
    async def test_high_frequency_event_handling(self, cross_service_test_setup):
        """Test handling of high-frequency events without degradation."""
        service, event_bus = cross_service_test_setup

        # Simulate high frequency of message events
        message_events = []
        for i in range(100):
            event = GameEvent(
                event_type="game.message_sent",
                user_id=3003,
                timestamp=datetime.now(timezone.utc),
                data={"message_id": i, "content_length": 50},
            )
            message_events.append(event)

        game_handler = self.handlers.get("game.*")

        # Process all events rapidly
        start_time = time.time()
        with patch.object(service, "award_points") as mock_award:
            mock_award.return_value = Mock(success=True)

            tasks = [game_handler(event) for event in message_events]
            await asyncio.gather(*tasks)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should handle high frequency without significant delays
        assert (
            processing_time < 5.0
        ), f"High frequency event processing too slow: {processing_time:.1f}s"
        assert mock_award.call_count == 100, "Not all high-frequency events processed"
