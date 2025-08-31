"""
Main Gamification Service Implementation
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
    IGamificationRepository,
)

# Configure logging
logger = logging.getLogger(__name__)


class GamificationServiceError(Exception):
    """Exception raised by the GamificationService for operation failures."""
    pass


class GamificationService(IGamificationService):
    def __init__(
        self,
        event_bus: EventBus,
        repository: IGamificationRepository,
        enable_auto_achievements: bool = True,
        enable_leaderboard_updates: bool = True,
    ):
        self.event_bus = event_bus
        self.repository = repository
        self.enable_auto_achievements = enable_auto_achievements
        self.enable_leaderboard_updates = enable_leaderboard_updates

        # Initialize engines
        self.anti_abuse_validator = AntiAbuseValidator()
        self.points_engine = PointsEngine(
            anti_abuse_validator=self.anti_abuse_validator,
            repository=self.repository,
        )
        self.achievement_engine = AchievementEngine(
            points_engine=self.points_engine,
            repository=self.repository,
        )
        # LeaderboardEngine would also be initialized here if it were being implemented
        # self.leaderboard_engine = LeaderboardEngine(...)

        self.achievement_engine.points_engine = self.points_engine
        self._initialized = False
        self._service_start_time = None
        self.service_metrics = {
            "total_actions_processed": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "achievements_unlocked": 0,
            "total_points_awarded": 0,
            "avg_processing_time_ms": 0.0,
        }
        self._event_handlers = {}

    async def initialize(self) -> None:
        if self._initialized:
            logger.warning("GamificationService already initialized")
            return
        logger.info("Initializing GamificationService...")
        if not hasattr(self.event_bus, "_is_connected") or not self.event_bus._is_connected:
            await self.event_bus.initialize()
        await self._setup_event_subscriptions()
        self._initialized = True
        self._service_start_time = datetime.now(timezone.utc)
        logger.info("GamificationService initialized successfully")
        await self._publish_system_event("service_started", {"service": "gamification"})

    async def cleanup(self) -> None:
        # Implementation for cleanup
        pass

    async def process_user_action(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> PointsAwardResult:
        if not self._initialized:
            raise GamificationServiceError("Service not initialized")

        points_result = await self.points_engine.award_points(
            user_id=user_id,
            action_type=action_type,
            context=context,
        )

        if points_result.success and self.enable_auto_achievements:
            # Simplified event for now
            mock_event = GameEvent(user_id=user_id, action=action_type.value, points_earned=points_result.points_awarded)
            await self.achievement_engine.check_achievements(user_id, mock_event)

        return points_result

    async def get_user_stats(self, user_id: int) -> UserStats:
        raise NotImplementedError

    async def get_leaderboards(
        self,
        user_id: int,
        types: Optional[List[LeaderboardType]] = None,
    ) -> Dict[LeaderboardType, Dict[str, Any]]:
        raise NotImplementedError

    async def admin_adjust_points(
        self,
        admin_id: int,
        user_id: int,
        adjustment: int,
        reason: str,
    ) -> PointsAwardResult:
        raise NotImplementedError

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok"}

    async def update_daily_streak(self, user_id: int) -> bool:
        """
        Updates the user's daily streak. Returns True if streak was updated.
        """
        stats = self.repository.get_user_gamification_stats(user_id)
        if not stats:
            # If no stats, create them. This is the user's first activity.
            stats = UserGamification(user_id=user_id, current_streak=1, longest_streak=1)
            stats.last_streak_date = datetime.now(timezone.utc)
            self.repository.create_or_update_user_gamification_stats(stats)
            return True

        today = datetime.now(timezone.utc).date()

        if stats.last_streak_date and stats.last_streak_date.date() == today:
            return False # Already updated today

        if stats.last_streak_date and stats.last_streak_date.date() == today - timedelta(days=1):
            stats.current_streak += 1
        else:
            stats.current_streak = 1

        if stats.current_streak > stats.longest_streak:
            stats.longest_streak = stats.current_streak

        stats.last_streak_date = datetime.now(timezone.utc)
        self.repository.create_or_update_user_gamification_stats(stats)

        return True

    async def _setup_event_subscriptions(self) -> None:
        # Placeholder for event subscriptions
        pass

    async def _publish_system_event(self, event_type: str, data: Dict[str, Any]) -> None:
        # Placeholder for publishing system events
        pass
