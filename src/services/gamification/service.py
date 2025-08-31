"""
Main Gamification Service Implementation

This module provides the central orchestration for all gamification functionality
in Diana Bot V2. It integrates the Event Bus, manages all engines, and provides
the main interface for other services to interact with the gamification system.

Key Features:
- Event Bus integration for real-time event processing
- Orchestration of Points, Achievement, and Leaderboard engines
- Comprehensive error handling and resilience
- Health monitoring and performance metrics
- Admin functions for manual adjustments
- Automatic achievement checking on point awards
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.events import AdminEvent, EventBus, GameEvent, SystemEvent
from src.core.interfaces import IEvent

from .engines import (
    AchievementEngine,
    AntiAbuseValidator,
    LeaderboardEngine,
    PointsEngine,
)
from .interfaces import (
    ActionType,
    IAchievementEngine,
    IAntiAbuseValidator,
    IGamificationService,
    ILeaderboardEngine,
    IPointsEngine,
    LeaderboardType,
    PointsAwardResult,
    UserStats,
)

# Configure logging
logger = logging.getLogger(__name__)


class GamificationServiceError(Exception):
    """Exception raised by the GamificationService for operation failures."""

    pass


class GamificationService(IGamificationService):
    """
    Main gamification service orchestrating all gamification functionality.

    This service serves as the central coordinator for points, achievements,
    and leaderboards while providing Event Bus integration for real-time
    updates across the Diana Bot V2 system.
    """

    def __init__(
        self,
        event_bus: EventBus,
        database_client=None,  # In production, this would be the actual DB client
        enable_auto_achievements: bool = True,
        enable_leaderboard_updates: bool = True,
    ):
        """
        Initialize the GamificationService.

        Args:
            event_bus: Event Bus for system-wide communication
            database_client: Database client for persistence
            enable_auto_achievements: Automatically check achievements on point awards
            enable_leaderboard_updates: Update leaderboards on relevant events
        """
        self.event_bus = event_bus
        self.database_client = database_client
        self.enable_auto_achievements = enable_auto_achievements
        self.enable_leaderboard_updates = enable_leaderboard_updates

        # Initialize engines
        self.anti_abuse_validator = AntiAbuseValidator()
        self.points_engine = PointsEngine(
            anti_abuse_validator=self.anti_abuse_validator,
            database_client=database_client,
        )
        self.achievement_engine = AchievementEngine(
            points_engine=self.points_engine,
            database_client=database_client,
        )
        self.leaderboard_engine = LeaderboardEngine(
            points_engine=self.points_engine,
            database_client=database_client,
        )

        # Set up circular reference for achievement rewards
        self.achievement_engine.points_engine = self.points_engine

        # Service state
        self._initialized = False
        self._service_start_time = None

        # Performance metrics
        self.service_metrics = {
            "total_actions_processed": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "achievements_unlocked": 0,
            "total_points_awarded": 0,
            "avg_processing_time_ms": 0.0,
        }

        # Event subscription handlers
        self._event_handlers = {}

    async def initialize(self) -> None:
        """
        Initialize the gamification service and all its engines.

        Sets up Event Bus subscriptions and prepares all engines for operation.
        """
        if self._initialized:
            logger.warning("GamificationService already initialized")
            return

        try:
            logger.info("Initializing GamificationService...")

            # Initialize Event Bus if not already done
            if (
                not hasattr(self.event_bus, "_is_connected")
                or not self.event_bus._is_connected
            ):
                await self.event_bus.initialize()

            # Set up event subscriptions
            await self._setup_event_subscriptions()

            # Mark as initialized
            self._initialized = True
            self._service_start_time = datetime.now(timezone.utc)

            logger.info("GamificationService initialized successfully")

            # Publish service started event
            await self._publish_system_event(
                "service_started",
                {
                    "service": "gamification",
                    "timestamp": self._service_start_time.isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Failed to initialize GamificationService: {e}")
            raise GamificationServiceError(f"Initialization failed: {e}")

    async def cleanup(self) -> None:
        """
        Clean up resources and close connections.
        """
        if not self._initialized:
            return

        try:
            logger.info("Cleaning up GamificationService...")

            # Unsubscribe from events
            await self._cleanup_event_subscriptions()

            # Cleanup Event Bus if we manage it
            # (In production, Event Bus might be managed externally)

            # Mark as not initialized
            self._initialized = False

            logger.info("GamificationService cleanup completed")

        except Exception as e:
            logger.error(f"Error during GamificationService cleanup: {e}")

    async def process_user_action(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> PointsAwardResult:
        """
        Process a user action for points and achievement evaluation.

        This is the main entry point for gamification events from other services.
        """
        if not self._initialized:
            raise GamificationServiceError("Service not initialized")

        start_time = time.time()

        try:
            # Step 1: Award points through the points engine
            points_result = await self.points_engine.award_points(
                user_id=user_id,
                action_type=action_type,
                context=context,
            )

            # Step 2: Check for achievement unlocks if points were awarded
            achievements_unlocked = []
            if points_result.success and self.enable_auto_achievements:
                # Create a mock event for achievement checking
                mock_event = GameEvent(
                    user_id=user_id,
                    action=action_type.value,
                    points_earned=points_result.points_awarded,
                    context=context,
                )

                achievement_results = await self.achievement_engine.check_achievements(
                    user_id=user_id,
                    trigger_event=mock_event,
                )

                for achievement_result in achievement_results:
                    if achievement_result.success:
                        achievements_unlocked.append(
                            {
                                "id": achievement_result.achievement_id,
                                "name": achievement_result.achievement_name,
                                "level": achievement_result.level,
                                "points_reward": achievement_result.points_reward,
                                "special_rewards": achievement_result.special_rewards,
                            }
                        )

                # Update points result with achievements
                points_result.achievements_unlocked.extend(
                    [f"{a['name']} (Level {a['level']})" for a in achievements_unlocked]
                )

            # Step 3: Update leaderboards if significant points were awarded
            if (
                points_result.success
                and points_result.points_awarded > 0
                and self.enable_leaderboard_updates
            ):

                # Invalidate relevant leaderboard caches
                await self._update_leaderboards_for_action(
                    user_id, action_type, points_result.points_awarded
                )

            # Step 4: Publish events for other services
            if points_result.success:
                await self._publish_points_awarded_event(
                    points_result, achievements_unlocked
                )

                for achievement in achievements_unlocked:
                    await self._publish_achievement_unlocked_event(user_id, achievement)

            # Step 5: Update metrics
            await self._update_service_metrics(
                start_time, points_result.success, points_result.points_awarded
            )

            return points_result

        except Exception as e:
            await self._update_service_metrics(start_time, success=False)
            logger.error(
                f"Error processing user action: user={user_id}, action={action_type.value}, error={e}"
            )

            # Return failed result
            return PointsAwardResult(
                success=False,
                user_id=user_id,
                action_type=action_type,
                points_awarded=0,
                base_points=0,
                multipliers_applied={},
                new_balance=0,
                error_message=str(e),
            )

    async def get_user_stats(self, user_id: int) -> UserStats:
        """
        Get comprehensive gamification statistics for a user.
        """
        if not self._initialized:
            raise GamificationServiceError("Service not initialized")

        try:
            # Get points data
            total_points, available_points = await self.points_engine.get_user_balance(
                user_id
            )

            # Get user achievements
            user_achievements = await self.achievement_engine.get_user_achievements(
                user_id
            )
            achievements_unlocked = len(user_achievements)

            # Get total available achievements
            available_achievements = (
                await self.achievement_engine.get_available_achievements()
            )
            achievements_total = len(available_achievements)

            # Get user rankings
            user_rankings = await self.leaderboard_engine.get_user_rankings(user_id)
            rank_weekly = user_rankings.get(LeaderboardType.WEEKLY_POINTS)
            rank_total = user_rankings.get(LeaderboardType.TOTAL_POINTS)

            # Get multipliers (through points engine)
            multipliers_active = await self.points_engine.calculate_multipliers(
                user_id=user_id,
                action_type=ActionType.LOGIN,  # Default action for multiplier calculation
                context={},
            )

            # Calculate level and other stats
            # (In production, this would come from UserGamification model)
            level = max(1, int((total_points / 1000) ** 0.5) + 1)
            current_streak = 0  # Would come from user data
            longest_streak = 0  # Would come from user data

            # Create UserStats object
            user_stats = UserStats(
                user_id=user_id,
                total_points=total_points,
                available_points=available_points,
                current_streak=current_streak,
                longest_streak=longest_streak,
                achievements_unlocked=achievements_unlocked,
                achievements_total=achievements_total,
                level=level,
                rank_weekly=rank_weekly,
                rank_total=rank_total,
                multipliers_active=multipliers_active,
                last_activity=datetime.now(timezone.utc),  # Would come from user data
                created_at=datetime.now(timezone.utc),  # Would come from user data
            )

            return user_stats

        except Exception as e:
            logger.error(f"Error getting user stats for user {user_id}: {e}")
            raise GamificationServiceError(f"Failed to get user stats: {e}")

    async def get_leaderboards(
        self,
        user_id: int,
        types: Optional[List[LeaderboardType]] = None,
    ) -> Dict[LeaderboardType, Dict[str, Any]]:
        """
        Get leaderboard data for display to a user.
        """
        if not self._initialized:
            raise GamificationServiceError("Service not initialized")

        try:
            leaderboard_types = types or list(LeaderboardType)
            leaderboards = {}

            for leaderboard_type in leaderboard_types:
                leaderboard_data = await self.leaderboard_engine.get_leaderboard(
                    leaderboard_type=leaderboard_type,
                    limit=10,  # Top 10 by default
                    user_id=user_id,
                )
                leaderboards[leaderboard_type] = leaderboard_data

            return leaderboards

        except Exception as e:
            logger.error(f"Error getting leaderboards for user {user_id}: {e}")
            raise GamificationServiceError(f"Failed to get leaderboards: {e}")

    async def admin_adjust_points(
        self,
        admin_id: int,
        user_id: int,
        adjustment: int,
        reason: str,
    ) -> PointsAwardResult:
        """
        Admin function to manually adjust user points.
        """
        if not self._initialized:
            raise GamificationServiceError("Service not initialized")

        try:
            # Create admin adjustment context
            context = {
                "admin_id": admin_id,
                "reason": reason,
                "adjustment_amount": adjustment,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Use points engine with force_award=True to bypass anti-abuse
            result = await self.points_engine.award_points(
                user_id=user_id,
                action_type=ActionType.ADMIN_ADJUSTMENT,
                context=context,
                base_points=adjustment,
                force_award=True,  # Admin adjustments bypass anti-abuse
            )

            # Log admin action
            logger.info(
                f"Admin adjustment: admin={admin_id}, user={user_id}, "
                f"adjustment={adjustment}, reason={reason}, success={result.success}"
            )

            # Publish admin event
            if result.success:
                await self._publish_admin_event(admin_id, user_id, adjustment, reason)

            return result

        except Exception as e:
            logger.error(f"Error in admin points adjustment: {e}")
            raise GamificationServiceError(f"Admin adjustment failed: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Get health status of the gamification service.
        """
        try:
            health_data = {
                "service": "gamification",
                "status": "healthy" if self._initialized else "not_initialized",
                "initialized": self._initialized,
                "uptime_seconds": 0,
                "engines": {
                    "points_engine": "healthy",
                    "achievement_engine": "healthy",
                    "leaderboard_engine": "healthy",
                    "anti_abuse_validator": "healthy",
                },
                "event_bus": {
                    "connected": hasattr(self.event_bus, "_is_connected")
                    and self.event_bus._is_connected,
                    "subscriptions": len(self._event_handlers),
                },
                "metrics": self.service_metrics.copy(),
            }

            # Calculate uptime
            if self._service_start_time:
                uptime = datetime.now(timezone.utc) - self._service_start_time
                health_data["uptime_seconds"] = uptime.total_seconds()

            # Add engine-specific metrics
            if hasattr(self.points_engine, "get_performance_metrics"):
                health_data["engines"][
                    "points_engine_metrics"
                ] = self.points_engine.get_performance_metrics()

            if hasattr(self.leaderboard_engine, "get_performance_metrics"):
                health_data["engines"][
                    "leaderboard_engine_metrics"
                ] = self.leaderboard_engine.get_performance_metrics()

            # Check Event Bus health
            if self.event_bus:
                try:
                    bus_health = await self.event_bus.health_check()
                    health_data["event_bus"]["health"] = bus_health
                except Exception as e:
                    health_data["event_bus"]["error"] = str(e)
                    health_data["status"] = "degraded"

            return health_data

        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {
                "service": "gamification",
                "status": "unhealthy",
                "error": str(e),
            }

    # Private helper methods for Event Bus integration

    async def _setup_event_subscriptions(self) -> None:
        """Set up Event Bus subscriptions for relevant events."""
        try:
            # Subscribe to game events (most common)
            await self.event_bus.subscribe("game.*", self._handle_game_event)
            self._event_handlers["game.*"] = self._handle_game_event

            # Subscribe to narrative events
            await self.event_bus.subscribe("narrative.*", self._handle_narrative_event)
            self._event_handlers["narrative.*"] = self._handle_narrative_event

            # Subscribe to user events
            await self.event_bus.subscribe("user.*", self._handle_user_event)
            self._event_handlers["user.*"] = self._handle_user_event

            # Subscribe to admin events
            await self.event_bus.subscribe("admin.*", self._handle_admin_event)
            self._event_handlers["admin.*"] = self._handle_admin_event

            logger.info("Event Bus subscriptions set up successfully")

        except Exception as e:
            logger.error(f"Failed to set up Event Bus subscriptions: {e}")
            raise

    async def _cleanup_event_subscriptions(self) -> None:
        """Clean up Event Bus subscriptions."""
        try:
            for event_pattern, handler in self._event_handlers.items():
                await self.event_bus.unsubscribe(event_pattern, handler)

            self._event_handlers.clear()
            logger.info("Event Bus subscriptions cleaned up")

        except Exception as e:
            logger.error(f"Error cleaning up Event Bus subscriptions: {e}")

    async def _handle_game_event(self, event: IEvent) -> None:
        """Handle game-related events."""
        try:
            # Extract user_id and action from game event
            event_data = event.data
            user_id = event_data.get("user_id")
            action = event_data.get("action")

            if not user_id or not action:
                logger.warning(
                    f"Invalid game event: missing user_id or action in {event.id}"
                )
                return

            # Map game action to ActionType
            action_type = self._map_game_action_to_action_type(action)
            if not action_type:
                logger.warning(f"Unknown game action: {action}")
                return

            # Process the action
            await self.process_user_action(
                user_id=user_id,
                action_type=action_type,
                context=event_data,
            )

        except Exception as e:
            logger.error(f"Error handling game event {event.id}: {e}")

    async def _handle_narrative_event(self, event: IEvent) -> None:
        """Handle narrative-related events."""
        try:
            event_data = event.data
            user_id = event_data.get("user_id")

            if not user_id:
                logger.warning(
                    f"Invalid narrative event: missing user_id in {event.id}"
                )
                return

            # Determine action type based on event type
            if "chapter_completed" in event.type:
                action_type = ActionType.STORY_CHAPTER_COMPLETED
            elif "decision_made" in event.type:
                action_type = ActionType.STORY_DECISION_MADE
            else:
                logger.warning(f"Unknown narrative event type: {event.type}")
                return

            # Process the action
            await self.process_user_action(
                user_id=user_id,
                action_type=action_type,
                context=event_data,
            )

        except Exception as e:
            logger.error(f"Error handling narrative event {event.id}: {e}")

    async def _handle_user_event(self, event: IEvent) -> None:
        """Handle user-related events."""
        try:
            event_data = event.data
            user_id = event_data.get("user_id")
            event_type = event_data.get("event_type")

            if not user_id:
                logger.warning(f"Invalid user event: missing user_id in {event.id}")
                return

            # Map user event to action type
            if event_type == "registered":
                # New user registration - could award welcome bonus
                action_type = ActionType.LOGIN
            elif event_type == "login":
                action_type = ActionType.DAILY_LOGIN
            else:
                # Skip other user events for now
                return

            # Process the action
            await self.process_user_action(
                user_id=user_id,
                action_type=action_type,
                context=event_data,
            )

        except Exception as e:
            logger.error(f"Error handling user event {event.id}: {e}")

    async def _handle_admin_event(self, event: IEvent) -> None:
        """Handle admin-related events."""
        try:
            event_data = event.data
            admin_id = event_data.get("admin_id")
            target_user = event_data.get("target_user")
            action_type = event_data.get("action_type")

            if action_type == "points_adjusted" and target_user:
                # Admin manually adjusted points
                adjustment = event_data.get("details", {}).get("points_adjustment", 0)
                reason = event_data.get("details", {}).get("reason", "Admin adjustment")

                if adjustment != 0:
                    await self.admin_adjust_points(
                        admin_id, target_user, adjustment, reason
                    )

        except Exception as e:
            logger.error(f"Error handling admin event {event.id}: {e}")

    def _map_game_action_to_action_type(self, action: str) -> Optional[ActionType]:
        """Map game action string to ActionType enum."""
        action_mapping = {
            "daily_login": ActionType.DAILY_LOGIN,
            "login": ActionType.LOGIN,
            "message_sent": ActionType.MESSAGE_SENT,
            "trivia_completed": ActionType.TRIVIA_COMPLETED,
            "story_completed": ActionType.STORY_CHAPTER_COMPLETED,
            "achievement_unlocked": ActionType.ACHIEVEMENT_UNLOCKED,
            "referral_bonus": ActionType.FRIEND_REFERRAL,
            "vip_purchase": ActionType.VIP_PURCHASE,
            "streak_bonus": ActionType.STREAK_BONUS,
            "challenge_completed": ActionType.CHALLENGE_COMPLETED,
        }

        return action_mapping.get(action)

    async def _update_leaderboards_for_action(
        self, user_id: int, action_type: ActionType, points_awarded: int
    ) -> None:
        """Update relevant leaderboards after a significant action."""
        try:
            # Determine which leaderboards need updating
            leaderboards_to_update = []

            if points_awarded > 0:
                leaderboards_to_update.extend(
                    [
                        LeaderboardType.TOTAL_POINTS,
                        LeaderboardType.WEEKLY_POINTS,
                    ]
                )

            if action_type == ActionType.STORY_CHAPTER_COMPLETED:
                leaderboards_to_update.append(LeaderboardType.NARRATIVE_PROGRESS)

            if action_type == ActionType.TRIVIA_COMPLETED:
                leaderboards_to_update.append(LeaderboardType.TRIVIA_CHAMPION)

            # Update caches for relevant leaderboards
            for leaderboard_type in leaderboards_to_update:
                await self.leaderboard_engine.update_leaderboard_cache(leaderboard_type)

        except Exception as e:
            logger.error(f"Error updating leaderboards: {e}")

    async def _publish_points_awarded_event(
        self,
        points_result: PointsAwardResult,
        achievements_unlocked: List[Dict[str, Any]],
    ) -> None:
        """Publish points awarded event to Event Bus."""
        try:
            event = GameEvent(
                user_id=points_result.user_id,
                action="points_awarded",
                points_earned=points_result.points_awarded,
                context={
                    "action_type": points_result.action_type.value,
                    "base_points": points_result.base_points,
                    "multipliers_applied": {
                        k.value: v for k, v in points_result.multipliers_applied.items()
                    },
                    "new_balance": points_result.new_balance,
                    "transaction_id": points_result.transaction_id,
                    "achievements_unlocked": achievements_unlocked,
                },
                source="gamification_service",
            )

            await self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Error publishing points awarded event: {e}")

    async def _publish_achievement_unlocked_event(
        self, user_id: int, achievement: Dict[str, Any]
    ) -> None:
        """Publish achievement unlocked event to Event Bus."""
        try:
            event = GameEvent(
                user_id=user_id,
                action="achievement_unlocked",
                points_earned=achievement["points_reward"],
                context={
                    "achievement_id": achievement["id"],
                    "achievement_name": achievement["name"],
                    "level": achievement["level"],
                    "special_rewards": achievement["special_rewards"],
                },
                source="gamification_service",
            )

            await self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Error publishing achievement unlocked event: {e}")

    async def _publish_admin_event(
        self, admin_id: int, user_id: int, adjustment: int, reason: str
    ) -> None:
        """Publish admin adjustment event to Event Bus."""
        try:
            event = AdminEvent(
                admin_id=admin_id,
                action_type="points_adjusted",
                target_user=user_id,
                details={
                    "points_adjustment": adjustment,
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                source="gamification_service",
            )

            await self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Error publishing admin event: {e}")

    async def _publish_system_event(
        self, event_type: str, data: Dict[str, Any]
    ) -> None:
        """Publish system event to Event Bus."""
        try:
            event = SystemEvent(
                component="gamification_service",
                event_type=event_type,
                system_data=data,
                source="gamification_service",
            )

            await self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Error publishing system event: {e}")

    async def _update_service_metrics(
        self, start_time: float, success: bool, points_awarded: int = 0
    ) -> None:
        """Update service performance metrics."""
        processing_time_ms = (time.time() - start_time) * 1000

        self.service_metrics["total_actions_processed"] += 1

        if success:
            self.service_metrics["successful_actions"] += 1
            self.service_metrics["total_points_awarded"] += points_awarded
        else:
            self.service_metrics["failed_actions"] += 1

        # Update average processing time (exponential moving average)
        alpha = 0.1
        if self.service_metrics["avg_processing_time_ms"] == 0:
            self.service_metrics["avg_processing_time_ms"] = processing_time_ms
        else:
            current_avg = self.service_metrics["avg_processing_time_ms"]
            self.service_metrics["avg_processing_time_ms"] = (
                alpha * processing_time_ms + (1 - alpha) * current_avg
            )
