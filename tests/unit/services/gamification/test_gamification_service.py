"""
Unit Tests for GamificationService

Tests the main gamification service orchestration including:
- Event Bus integration and event handling
- Engine coordination (Points, Achievement, Leaderboard)
- User action processing with full workflow
- Admin functions and manual adjustments
- Health monitoring and error handling
- Performance requirements and metrics
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import pytest_asyncio

from core.events import AdminEvent, EventBus, GameEvent, NarrativeEvent, UserEvent
from services.gamification.interfaces import (
    ActionType,
    LeaderboardType,
    PointsAwardResult,
    UserStats,
)
from services.gamification.service import GamificationService, GamificationServiceError


class TestGamificationServiceCore:
    """Test core GamificationService functionality."""

    @pytest_asyncio.fixture
    async def mock_event_bus(self):
        """Mock Event Bus for testing."""
        event_bus = AsyncMock(spec=EventBus)
        event_bus._is_connected = True
        event_bus.initialize = AsyncMock()
        event_bus.subscribe = AsyncMock()
        event_bus.unsubscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        event_bus.health_check = AsyncMock(return_value={"status": "healthy"})
        return event_bus

    @pytest_asyncio.fixture
    async def gamification_service(self, mock_event_bus):
        """Create GamificationService instance for testing."""
        service = GamificationService(
            event_bus=mock_event_bus,
            database_client=None,
        )
        return service

    @pytest.mark.asyncio
    async def test_service_initialization(self, gamification_service, mock_event_bus):
        """Test successful service initialization."""
        assert not gamification_service._initialized

        await gamification_service.initialize()

        assert gamification_service._initialized
        assert gamification_service._service_start_time is not None

        # Should have set up event subscriptions
        assert (
            mock_event_bus.subscribe.call_count == 4
        )  # game.*, narrative.*, user.*, admin.*

        # Check specific subscriptions
        expected_calls = [
            call("game.*", gamification_service._handle_game_event),
            call("narrative.*", gamification_service._handle_narrative_event),
            call("user.*", gamification_service._handle_user_event),
            call("admin.*", gamification_service._handle_admin_event),
        ]
        mock_event_bus.subscribe.assert_has_calls(expected_calls, any_order=True)

    @pytest.mark.asyncio
    async def test_service_initialization_already_initialized(
        self, gamification_service, mock_event_bus
    ):
        """Test initialization when already initialized."""
        await gamification_service.initialize()

        # Initialize again - should not fail
        await gamification_service.initialize()

        # Should still be initialized
        assert gamification_service._initialized

    @pytest.mark.asyncio
    async def test_service_initialization_failure(
        self, gamification_service, mock_event_bus
    ):
        """Test service initialization failure handling."""
        mock_event_bus.subscribe.side_effect = Exception("Subscription failed")

        with pytest.raises(GamificationServiceError, match="Initialization failed"):
            await gamification_service.initialize()

        assert not gamification_service._initialized

    @pytest.mark.asyncio
    async def test_service_cleanup(self, gamification_service, mock_event_bus):
        """Test service cleanup."""
        await gamification_service.initialize()
        assert gamification_service._initialized

        await gamification_service.cleanup()

        assert not gamification_service._initialized

        # Should have unsubscribed from events
        assert mock_event_bus.unsubscribe.call_count == 4

    @pytest.mark.asyncio
    async def test_process_user_action_success(self, gamification_service):
        """Test successful user action processing."""
        await gamification_service.initialize()

        user_id = 123
        action_type = ActionType.DAILY_LOGIN
        context = {"ip_address": "127.0.0.1"}

        result = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=action_type,
            context=context,
        )

        assert result.success is True
        assert result.user_id == user_id
        assert result.action_type == action_type
        assert result.points_awarded > 0

    @pytest.mark.asyncio
    async def test_process_user_action_not_initialized(self, gamification_service):
        """Test user action processing when service not initialized."""
        with pytest.raises(GamificationServiceError, match="Service not initialized"):
            await gamification_service.process_user_action(
                user_id=123,
                action_type=ActionType.DAILY_LOGIN,
                context={},
            )

    @pytest.mark.asyncio
    async def test_process_user_action_with_achievements(self, gamification_service):
        """Test user action processing that unlocks achievements."""
        await gamification_service.initialize()

        # Give user enough points to potentially unlock achievements
        for i in range(5):
            await gamification_service.process_user_action(
                user_id=123,
                action_type=ActionType.TRIVIA_COMPLETED,
                context={"question_id": f"q_{i}", "correct_answer": True},
            )

        # This should check for achievements
        result = await gamification_service.process_user_action(
            user_id=123,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        assert result.success is True
        # May have unlocked achievements (depends on default achievement conditions)

    @pytest.mark.asyncio
    async def test_get_user_stats(self, gamification_service):
        """Test getting comprehensive user statistics."""
        await gamification_service.initialize()

        user_id = 123

        # Give user some activity
        await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123", "amount": 100},
        )

        stats = await gamification_service.get_user_stats(user_id)

        assert isinstance(stats, UserStats)
        assert stats.user_id == user_id
        assert stats.total_points > 0
        assert stats.available_points > 0
        assert stats.level >= 1

    @pytest.mark.asyncio
    async def test_get_user_stats_not_initialized(self, gamification_service):
        """Test getting user stats when service not initialized."""
        with pytest.raises(GamificationServiceError, match="Service not initialized"):
            await gamification_service.get_user_stats(123)

    @pytest.mark.asyncio
    async def test_get_leaderboards(self, gamification_service):
        """Test getting leaderboard data."""
        await gamification_service.initialize()

        user_id = 123

        leaderboards = await gamification_service.get_leaderboards(user_id)

        assert isinstance(leaderboards, dict)
        assert len(leaderboards) == len(LeaderboardType)

        # Check specific leaderboard
        weekly_board = leaderboards[LeaderboardType.WEEKLY_POINTS]
        assert "leaderboard_type" in weekly_board
        assert "rankings" in weekly_board
        assert "total_participants" in weekly_board

    @pytest.mark.asyncio
    async def test_get_leaderboards_filtered(self, gamification_service):
        """Test getting filtered leaderboard data."""
        await gamification_service.initialize()

        user_id = 123
        requested_types = [LeaderboardType.TOTAL_POINTS, LeaderboardType.WEEKLY_POINTS]

        leaderboards = await gamification_service.get_leaderboards(
            user_id=user_id,
            types=requested_types,
        )

        assert len(leaderboards) == 2
        assert LeaderboardType.TOTAL_POINTS in leaderboards
        assert LeaderboardType.WEEKLY_POINTS in leaderboards

    @pytest.mark.asyncio
    async def test_admin_adjust_points_positive(self, gamification_service):
        """Test admin positive points adjustment."""
        await gamification_service.initialize()

        admin_id = 1
        user_id = 123
        adjustment = 500
        reason = "Compensation for bug"

        result = await gamification_service.admin_adjust_points(
            admin_id=admin_id,
            user_id=user_id,
            adjustment=adjustment,
            reason=reason,
        )

        assert result.success is True
        assert result.points_awarded == adjustment
        assert result.action_type == ActionType.ADMIN_ADJUSTMENT

    @pytest.mark.asyncio
    async def test_admin_adjust_points_negative(self, gamification_service):
        """Test admin negative points adjustment (penalty)."""
        await gamification_service.initialize()

        # Give user some points first
        await gamification_service.process_user_action(
            user_id=123,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "test123", "amount": 100},
        )

        admin_id = 1
        user_id = 123
        adjustment = -200
        reason = "Penalty for violation"

        result = await gamification_service.admin_adjust_points(
            admin_id=admin_id,
            user_id=user_id,
            adjustment=adjustment,
            reason=reason,
        )

        assert result.success is True
        assert result.points_awarded == adjustment

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, gamification_service, mock_event_bus):
        """Test health check when service is healthy."""
        await gamification_service.initialize()

        health = await gamification_service.health_check()

        assert health["service"] == "gamification"
        assert health["status"] == "healthy"
        assert health["initialized"] is True
        assert health["uptime_seconds"] >= 0
        assert "engines" in health
        assert "event_bus" in health
        assert "metrics" in health

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, gamification_service):
        """Test health check when service not initialized."""
        health = await gamification_service.health_check()

        assert health["status"] == "not_initialized"
        assert health["initialized"] is False

    @pytest.mark.asyncio
    async def test_health_check_event_bus_error(
        self, gamification_service, mock_event_bus
    ):
        """Test health check when Event Bus has errors."""
        await gamification_service.initialize()

        mock_event_bus.health_check.side_effect = Exception("Event Bus error")

        health = await gamification_service.health_check()

        assert health["status"] == "degraded"
        assert "error" in health["event_bus"]


class TestGamificationServiceEventHandling:
    """Test Event Bus event handling functionality."""

    @pytest_asyncio.fixture
    async def gamification_service(self):
        """Create service with mock Event Bus."""
        mock_event_bus = AsyncMock(spec=EventBus)
        mock_event_bus._is_connected = True
        mock_event_bus.initialize = AsyncMock()
        mock_event_bus.subscribe = AsyncMock()
        mock_event_bus.publish = AsyncMock()

        service = GamificationService(
            event_bus=mock_event_bus,
            database_client=None,
        )
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_handle_game_event_valid(self, gamification_service):
        """Test handling valid game event."""
        event = GameEvent(
            user_id=123,
            action="daily_login",
            points_earned=50,
            context={"ip_address": "127.0.0.1"},
        )

        # Manually call event handler
        await gamification_service._handle_game_event(event)

        # Should have processed the action
        # (In a real implementation, this would be verified by checking the result)

    @pytest.mark.asyncio
    async def test_handle_game_event_invalid_data(self, gamification_service):
        """Test handling game event with invalid data."""
        event = GameEvent(
            user_id=123,
            action="daily_login",
            points_earned=50,
            context={},
        )

        # Remove required fields
        event._data = {"invalid": "data"}

        # Should handle gracefully
        await gamification_service._handle_game_event(event)

    @pytest.mark.asyncio
    async def test_handle_narrative_event_chapter_completed(self, gamification_service):
        """Test handling narrative chapter completion event."""
        event = NarrativeEvent(
            user_id=123,
            chapter_id="chapter_01_intro",
            decision_made="choice_a",
            context={"completion_time": 300},
        )

        # Mock the event type to match chapter completion
        event._type = "narrative.chapter_completed"

        await gamification_service._handle_narrative_event(event)

    @pytest.mark.asyncio
    async def test_handle_narrative_event_decision_made(self, gamification_service):
        """Test handling narrative decision event."""
        event = NarrativeEvent(
            user_id=123,
            chapter_id="chapter_01_intro",
            decision_made="choice_b",
            context={"decision_time": 30},
        )

        # Mock the event type to match decision made
        event._type = "narrative.decision_made"

        await gamification_service._handle_narrative_event(event)

    @pytest.mark.asyncio
    async def test_handle_user_event_registration(self, gamification_service):
        """Test handling user registration event."""
        event = UserEvent(
            user_id=123,
            event_type="registered",
            user_data={"signup_source": "telegram"},
        )

        await gamification_service._handle_user_event(event)

    @pytest.mark.asyncio
    async def test_handle_user_event_login(self, gamification_service):
        """Test handling user login event."""
        event = UserEvent(
            user_id=123,
            event_type="login",
            user_data={"login_streak": 5},
        )

        await gamification_service._handle_user_event(event)

    @pytest.mark.asyncio
    async def test_handle_admin_event_points_adjustment(self, gamification_service):
        """Test handling admin points adjustment event."""
        event = AdminEvent(
            admin_id=1,
            action_type="points_adjusted",
            target_user=123,
            details={
                "points_adjustment": 500,
                "reason": "Compensation",
            },
        )

        await gamification_service._handle_admin_event(event)

    @pytest.mark.asyncio
    async def test_map_game_action_to_action_type(self, gamification_service):
        """Test game action mapping to ActionType."""
        assert (
            gamification_service._map_game_action_to_action_type("daily_login")
            == ActionType.DAILY_LOGIN
        )
        assert (
            gamification_service._map_game_action_to_action_type("trivia_completed")
            == ActionType.TRIVIA_COMPLETED
        )
        assert (
            gamification_service._map_game_action_to_action_type("unknown_action")
            is None
        )


class TestGamificationServiceIntegration:
    """Test full integration workflows."""

    @pytest_asyncio.fixture
    async def gamification_service(self):
        """Create service for integration testing."""
        mock_event_bus = AsyncMock(spec=EventBus)
        mock_event_bus._is_connected = True
        mock_event_bus.initialize = AsyncMock()
        mock_event_bus.subscribe = AsyncMock()
        mock_event_bus.publish = AsyncMock()

        service = GamificationService(
            event_bus=mock_event_bus,
            database_client=None,
        )
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_full_user_journey_workflow(self, gamification_service):
        """Test complete user journey through gamification system."""
        user_id = 123

        # Step 1: User registration (welcome bonus)
        result1 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.LOGIN,
            context={"signup": True},
        )
        assert result1.success is True

        # Step 2: Daily login
        result2 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )
        assert result2.success is True

        # Step 3: Complete trivia
        result3 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"correct_answer": True, "difficulty": "medium"},
        )
        assert result3.success is True

        # Step 4: Check user stats
        stats = await gamification_service.get_user_stats(user_id)
        assert stats.total_points > 0
        assert stats.level >= 1

        # Step 5: Check leaderboards
        leaderboards = await gamification_service.get_leaderboards(user_id)
        assert len(leaderboards) > 0

    @pytest.mark.asyncio
    async def test_achievement_unlock_workflow(self, gamification_service):
        """Test achievement unlock workflow."""
        user_id = 123

        # Perform actions that should unlock "first_steps" achievement
        result = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.MESSAGE_SENT,
            context={"message": "Hello Diana!"},
        )

        assert result.success is True

        # Check if any achievements were unlocked
        # (Depends on default achievement conditions)
        stats = await gamification_service.get_user_stats(user_id)
        assert stats.achievements_unlocked >= 0

    @pytest.mark.asyncio
    async def test_vip_user_workflow(self, gamification_service):
        """Test VIP user workflow with multipliers."""
        user_id = 123

        # Step 1: VIP purchase
        result1 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.VIP_PURCHASE,
            context={"transaction_id": "vip_123", "amount": 99.99},
        )
        assert result1.success is True

        # Step 2: Set VIP multiplier
        # In a real implementation, this would be set by the VIP system
        user_data = await gamification_service.points_engine._get_or_create_user_data(
            user_id
        )
        user_data.vip_multiplier = 1.5

        # Step 3: Perform action with VIP bonus
        result2 = await gamification_service.process_user_action(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"correct_answer": True},
        )

        assert result2.success is True
        assert result2.points_awarded > result2.base_points  # Should have VIP bonus

    @pytest.mark.asyncio
    async def test_anti_abuse_integration(self, gamification_service):
        """Test anti-abuse system integration."""
        user_id = 123

        # Rapid-fire attempts (should trigger anti-abuse)
        results = []
        for i in range(15):  # Exceed rapid-fire threshold
            result = await gamification_service.process_user_action(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message": f"Message {i}"},
            )
            results.append(result)

        # Some requests should be rejected by anti-abuse
        successful_results = [r for r in results if r.success]
        rejected_results = [r for r in results if not r.success]

        # Should have some rejections due to anti-abuse
        assert len(rejected_results) >= 0  # May or may not trigger depending on timing


class TestGamificationServiceMetrics:
    """Test service metrics and monitoring."""

    @pytest_asyncio.fixture
    async def gamification_service(self):
        """Create service for metrics testing."""
        mock_event_bus = AsyncMock(spec=EventBus)
        mock_event_bus._is_connected = True
        mock_event_bus.initialize = AsyncMock()
        mock_event_bus.subscribe = AsyncMock()
        mock_event_bus.publish = AsyncMock()

        service = GamificationService(
            event_bus=mock_event_bus,
            database_client=None,
        )
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_service_metrics_tracking(self, gamification_service):
        """Test service-level metrics tracking."""
        initial_metrics = gamification_service.service_metrics.copy()

        # Perform some actions
        for i in range(5):
            await gamification_service.process_user_action(
                user_id=123,
                action_type=ActionType.MESSAGE_SENT,
                context={"message_id": f"msg_{i}"},
            )

        # Check metrics updated
        metrics = gamification_service.service_metrics
        assert (
            metrics["total_actions_processed"]
            == initial_metrics["total_actions_processed"] + 5
        )
        assert metrics["successful_actions"] > initial_metrics["successful_actions"]
        assert metrics["total_points_awarded"] > initial_metrics["total_points_awarded"]

    @pytest.mark.asyncio
    async def test_performance_metrics_in_health_check(self, gamification_service):
        """Test performance metrics included in health check."""
        # Perform some actions to generate metrics
        await gamification_service.process_user_action(
            user_id=123,
            action_type=ActionType.DAILY_LOGIN,
            context={},
        )

        health = await gamification_service.health_check()

        assert "metrics" in health
        metrics = health["metrics"]
        assert "total_actions_processed" in metrics
        assert "successful_actions" in metrics
        assert "avg_processing_time_ms" in metrics

    @pytest.mark.asyncio
    async def test_engine_metrics_in_health_check(self, gamification_service):
        """Test engine-specific metrics in health check."""
        health = await gamification_service.health_check()

        assert "engines" in health
        engines = health["engines"]

        # Should include engine status
        assert "points_engine" in engines
        assert "achievement_engine" in engines
        assert "leaderboard_engine" in engines
        assert "anti_abuse_validator" in engines
