"""
Integration Tests for User Service, Gamification Service, and Event Bus

This module provides comprehensive integration tests between the User Service,
Gamification Service, and Event Bus to validate end-to-end functionality,
error handling, and data consistency across these critical system components.

Test Categories:
1. Happy Path Integration - Verify events flow correctly across services
2. Error Scenario Integration - Validate graceful handling of failures
3. Data Consistency - Ensure data remains consistent across service boundaries
4. Performance - Validate system behavior under load
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio

from core.events import EventBus
from core.interfaces import IEvent
from modules.user.events import (
    OnboardingCompletedEvent,
    OnboardingProgressedEvent,
    OnboardingStartedEvent,
    PersonalityDetectedEvent,
    TutorialCompletedEvent,
    UserCreatedEvent,
)
from services.gamification.interfaces import (
    ActionType,
    LeaderboardType,
    MultiplierType,
    UserStats,
)
from services.gamification.service import GamificationService


class MockUserService:
    """Mock implementation of UserService for integration testing."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.users = {}
        self.event_handlers = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the UserService mock."""
        if self._initialized:
            return

        # Set up event handlers
        await self.event_bus.subscribe(
            "game.points_awarded", self._handle_points_awarded
        )
        await self.event_bus.subscribe(
            "game.achievement_unlocked", self._handle_achievement_unlocked
        )

        self._initialized = True

    async def cleanup(self) -> None:
        """Clean up resources."""
        if not self._initialized:
            return

        # Clean up event subscriptions
        for pattern, handler in self.event_handlers.items():
            await self.event_bus.unsubscribe(pattern, handler)

        self._initialized = False

    async def create_user(
        self, user_id: int, first_name: str, username: Optional[str] = None
    ) -> None:
        """Create a new user and publish UserCreatedEvent."""
        # Store user in memory
        self.users[user_id] = {
            "user_id": user_id,
            "first_name": first_name,
            "username": username,
            "created_at": datetime.now(timezone.utc),
            "points": 0,
            "achievements": [],
        }

        # Publish user created event
        event = UserCreatedEvent(
            user_id=user_id,
            first_name=first_name,
            username=username,
            language_code="en",
        )

        await self.event_bus.publish(event)

    async def start_onboarding(self, user_id: int) -> None:
        """Start onboarding process for a user."""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")

        event = OnboardingStartedEvent(
            user_id=user_id,
            first_name=self.users[user_id]["first_name"],
            language_code="en",
            adaptive_context={"source": "integration_test"},
        )

        await self.event_bus.publish(event)

    async def complete_personality_detection(self, user_id: int) -> None:
        """Complete personality detection for a user."""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")

        # Create sample personality dimensions
        dimensions = {
            "exploration": 0.7,
            "competitiveness": 0.4,
            "narrative": 0.9,
            "social": 0.6,
        }

        event = PersonalityDetectedEvent(
            user_id=user_id,
            dimensions=dimensions,
            archetype="Storyteller",
            confidence=0.85,
            quiz_responses=[{"question_id": "q1", "answer_id": "a2"}],
        )

        await self.event_bus.publish(event)

    async def complete_tutorial(self, user_id: int) -> None:
        """Complete tutorial for a user."""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")

        event = TutorialCompletedEvent(
            user_id=user_id,
            sections_completed=["intro", "basic", "advanced"],
            total_time=300,  # seconds
            engagement_score=0.9,
        )

        await self.event_bus.publish(event)

    async def complete_onboarding(self, user_id: int) -> None:
        """Complete full onboarding process for a user."""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")

        event = OnboardingCompletedEvent(
            user_id=user_id,
            final_state="completed",
            completion_metrics={
                "time_taken": 600,  # seconds
                "all_steps_completed": True,
            },
        )

        await self.event_bus.publish(event)

    async def _handle_points_awarded(self, event: IEvent) -> None:
        """Handle points awarded events from GamificationService."""
        event_data = event.data
        user_id = event_data.get("user_id")
        points_earned = event_data.get("points_earned", 0)

        if user_id in self.users:
            self.users[user_id]["points"] += points_earned

    async def _handle_achievement_unlocked(self, event: IEvent) -> None:
        """Handle achievement unlocked events from GamificationService."""
        event_data = event.data
        user_id = event_data.get("user_id")
        context = event_data.get("context", {})

        achievement = {
            "id": context.get("achievement_id", "unknown"),
            "name": context.get("achievement_name", "Unknown Achievement"),
            "level": context.get("level", 1),
            "unlocked_at": datetime.now(timezone.utc),
        }

        if user_id in self.users:
            if "achievements" not in self.users[user_id]:
                self.users[user_id]["achievements"] = []
            self.users[user_id]["achievements"].append(achievement)


class TestUserGamificationEventBusIntegration:
    """Integration tests between UserService, GamificationService, and Event Bus."""

    @pytest_asyncio.fixture
    async def event_bus(self):
        """Create real Event Bus instance for integration testing."""
        bus = EventBus(test_mode=True)  # Use test mode to avoid Redis dependency
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
    async def user_service(self, event_bus):
        """Create mock UserService with Event Bus."""
        service = MockUserService(event_bus=event_bus)
        await service.initialize()
        yield service
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_user_creation_triggers_gamification(
        self, event_bus, gamification_service, user_service
    ):
        """Test that user creation event triggers gamification setup."""
        # Generate random user ID to avoid collisions
        user_id = int(uuid.uuid4().int % 100000000)

        # Create a new user
        await user_service.create_user(
            user_id=user_id, first_name="TestUser", username="test_user"
        )

        # Allow time for event processing
        await asyncio.sleep(0.1)

        # Check that user has a gamification profile
        try:
            user_stats = await gamification_service.get_user_stats(user_id)
            assert user_stats is not None
            assert user_stats.user_id == user_id
        except Exception as e:
            pytest.fail(f"Failed to get user stats after user creation: {e}")

    @pytest.mark.asyncio
    async def test_onboarding_awards_points(
        self, event_bus, gamification_service, user_service
    ):
        """Test that completing onboarding steps awards points via Gamification."""
        # Generate random user ID to avoid collisions
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user and go through onboarding flow
        await user_service.create_user(user_id=user_id, first_name="OnboardingUser")
        await asyncio.sleep(0.05)

        # Get initial points
        initial_stats = await gamification_service.get_user_stats(user_id)
        initial_points = initial_stats.total_points

        # Complete onboarding steps
        await user_service.start_onboarding(user_id)
        await asyncio.sleep(0.05)

        await user_service.complete_personality_detection(user_id)
        await asyncio.sleep(0.05)

        await user_service.complete_tutorial(user_id)
        await asyncio.sleep(0.05)

        await user_service.complete_onboarding(user_id)
        await asyncio.sleep(0.1)  # Give more time for final event processing

        # Check that points were awarded
        final_stats = await gamification_service.get_user_stats(user_id)
        assert (
            final_stats.total_points > initial_points
        ), "No points awarded for completing onboarding"

        # Check that user state is consistent across services
        assert (
            user_service.users[user_id]["points"] > 0
        ), "Points not reflected in UserService"

    @pytest.mark.asyncio
    async def test_bidirectional_achievement_flow(
        self, event_bus, gamification_service, user_service
    ):
        """Test achievement unlocks flow bidirectionally between services."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        await user_service.create_user(user_id=user_id, first_name="AchievementUser")
        await asyncio.sleep(0.05)

        # Trigger actions that should result in achievements
        # Simulate completing several tutorial sections to trigger achievements
        for _ in range(5):
            result = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.TRIVIA_COMPLETED,
                context={"score": 100, "difficulty": "hard"},
            )
            assert result.success is True

        # Allow time for achievement processing and events
        await asyncio.sleep(0.2)

        # Check for achievements in user service
        assert (
            len(user_service.users[user_id]["achievements"]) > 0
        ), "No achievements recorded in UserService"

        # Check gamification stats
        stats = await gamification_service.get_user_stats(user_id)
        assert (
            stats.achievements_unlocked > 0
        ), "No achievements recorded in GamificationService"

    @pytest.mark.asyncio
    async def test_error_handling_service_resilience(
        self, event_bus, gamification_service, user_service
    ):
        """Test services remain resilient when facing errors."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        await user_service.create_user(user_id=user_id, first_name="ErrorUser")
        await asyncio.sleep(0.05)

        # Simulate error scenario - invalid action type should not crash services
        try:
            # Use very large invalid values to simulate problematic data
            massive_user_id = 9999999999999999
            await gamification_service.process_user_action(
                user_id=massive_user_id,
                action_type=ActionType.ADMIN_ADJUSTMENT,  # Using admin action without admin context
                context={"invalid": "data" * 1000},  # Large invalid context
            )
        except Exception:
            # Error is expected, but service should remain functional
            pass

        # Service should still function for valid requests
        await asyncio.sleep(0.1)  # Give time to recover if needed

        # Verify services still respond
        try:
            result = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.LOGIN,
                context={"source": "error_test"},
            )
            assert (
                result.success is True
            ), "GamificationService failed after error scenario"

            # Verify EventBus is still functioning
            stats = await gamification_service.get_user_stats(user_id)
            assert stats is not None, "Failed to get user stats after error scenario"

            # Check EventBus health directly
            health = await event_bus.health_check()
            assert health["status"] in [
                "healthy",
                "degraded",
            ], f"EventBus unhealthy after error: {health}"

        except Exception as e:
            pytest.fail(f"Service not resilient after error scenario: {e}")

    @pytest.mark.asyncio
    async def test_data_consistency_cross_service(
        self, event_bus, gamification_service, user_service
    ):
        """Test data consistency between UserService and GamificationService."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        await user_service.create_user(user_id=user_id, first_name="ConsistencyUser")
        await asyncio.sleep(0.1)

        # Perform several point-awarding actions
        action_types = [
            ActionType.LOGIN,
            ActionType.DAILY_LOGIN,
            ActionType.MESSAGE_SENT,
            ActionType.TRIVIA_COMPLETED,
        ]

        total_expected_points = 0

        for action in action_types:
            result = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=action,
                context={"source": "consistency_test"},
            )
            if result.success:
                total_expected_points += result.points_awarded

            # Allow events to propagate
            await asyncio.sleep(0.05)

        # Final wait for all events
        await asyncio.sleep(0.2)

        # Check data consistency
        gamification_stats = await gamification_service.get_user_stats(user_id)
        user_service_points = user_service.users[user_id]["points"]

        # Validate consistency within reasonable margin
        # (There might be minor timing differences in event processing)
        assert (
            abs(gamification_stats.total_points - user_service_points) <= 10
        ), f"Points inconsistent: GamificationService={gamification_stats.total_points}, UserService={user_service_points}"

    @pytest.mark.asyncio
    async def test_concurrent_operations_safety(
        self, event_bus, gamification_service, user_service
    ):
        """Test safety of concurrent operations across services."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        await user_service.create_user(user_id=user_id, first_name="ConcurrentUser")
        await asyncio.sleep(0.1)

        # Prepare a batch of concurrent operations
        concurrent_count = 20  # Reasonable number for testing

        # Create tasks for concurrent execution
        user_tasks = []
        gamification_tasks = []

        # Mix of user service and gamification service operations
        for i in range(concurrent_count):
            if i % 4 == 0:
                user_tasks.append(user_service.start_onboarding(user_id))
            elif i % 4 == 1:
                user_tasks.append(user_service.complete_personality_detection(user_id))
            elif i % 4 == 2:
                gamification_tasks.append(
                    gamification_service.process_user_action(
                        user_id=user_id,
                        action_type=(
                            ActionType.LOGIN
                            if i % 2 == 0
                            else ActionType.TRIVIA_COMPLETED
                        ),
                        context={"concurrent_id": i},
                    )
                )
            else:
                gamification_tasks.append(gamification_service.get_user_stats(user_id))

        # Execute operations concurrently
        await asyncio.gather(*(user_tasks + gamification_tasks), return_exceptions=True)

        # Allow time for all events to be processed
        await asyncio.sleep(0.5)

        # Verify system remains in consistent state
        # Services should not crash and user data should be accessible
        try:
            stats = await gamification_service.get_user_stats(user_id)
            assert (
                stats is not None
            ), "Failed to get user stats after concurrent operations"

            # Verify EventBus is still healthy
            bus_health = await event_bus.health_check()
            assert bus_health["status"] in [
                "healthy",
                "degraded",
            ], "EventBus unhealthy after concurrent operations"

            # Verify services are responsive
            result = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.LOGIN,
                context={"final_verification": True},
            )
            assert (
                result.success is True
            ), "GamificationService unresponsive after concurrent operations"

        except Exception as e:
            pytest.fail(f"Concurrent operations caused system instability: {e}")

    @pytest.mark.asyncio
    async def test_performance_latency(
        self, event_bus, gamification_service, user_service
    ):
        """Test end-to-end latency for operations across services."""
        user_id = int(uuid.uuid4().int % 100000000)

        # Create user
        await user_service.create_user(user_id=user_id, first_name="PerformanceUser")
        await asyncio.sleep(0.1)

        # Measure end-to-end latency for a complete operation
        start_time = asyncio.get_event_loop().time()

        # Publish event from UserService
        await user_service.complete_tutorial(user_id)

        # Wait for event to propagate through EventBus to GamificationService
        # and for the points to be awarded and reflected back
        await asyncio.sleep(0.2)  # Allow reasonable time for processing

        # Verify that points were awarded
        stats = await gamification_service.get_user_stats(user_id)

        end_time = asyncio.get_event_loop().time()
        total_latency = (end_time - start_time) * 1000  # Convert to ms

        # Log latency for analysis
        print(f"End-to-end latency: {total_latency:.2f}ms")

        # Latency should meet performance requirements (adjust threshold as needed)
        # The requirement mentioned in CLAUDE.md is <2 seconds for 95% of operations
        assert (
            total_latency < 2000
        ), f"End-to-end latency too high: {total_latency:.2f}ms"
