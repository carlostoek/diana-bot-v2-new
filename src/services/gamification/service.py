"""
Main Gamification Service Implementation
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from src.core.events import AdminEvent, EventBus, GameEvent, SystemEvent
from src.core.interfaces import IEvent

from .engines import (
    AchievementEngine,
    AntiAbuseValidator,
    PointsEngine,
)
from .interfaces import (
    ActionType,
    IAchievementEngine,
    IAntiAbuseValidator,
    IGamificationService,
    IPointsEngine,
    LeaderboardType,
    PointsAwardResult,
    UserStats,
    IGamificationRepository,
)
from .models import UserGamification

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

        self.anti_abuse_validator = AntiAbuseValidator()
        self.points_engine = PointsEngine(
            anti_abuse_validator=self.anti_abuse_validator,
            repository=self.repository,
        )
        self.achievement_engine = AchievementEngine(
            points_engine=self.points_engine,
            repository=self.repository,
        )

        self._initialized = False
        self._service_start_time = None

    async def initialize(self) -> None:
        if self._initialized:
            return
        logger.info("Initializing GamificationService...")
        if not hasattr(self.event_bus, "_is_connected") or not self.event_bus._is_connected:
            await self.event_bus.initialize()
        await self._setup_event_subscriptions()
        self._initialized = True
        logger.info("GamificationService initialized successfully")

    async def cleanup(self) -> None:
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
            mock_event = GameEvent(user_id=user_id, action=action_type.value, points_earned=points_result.points_awarded)
            await self.achievement_engine.check_achievements(user_id, mock_event)

        return points_result

    async def update_daily_streak(self, user_id: int) -> bool:
        stats = self.repository.get_user_gamification_stats(user_id)
        if not stats:
            stats = UserGamification(user_id=user_id, current_streak=1, longest_streak=1)
            stats.last_streak_date = datetime.now(timezone.utc)
            self.repository.create_or_update_user_gamification_stats(stats)
            return True

        today = datetime.now(timezone.utc).date()

        if stats.last_streak_date and stats.last_streak_date.date() == today:
            return False

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
        """Set up Event Bus subscriptions for relevant events."""
        await self.event_bus.subscribe("user.*", self._handle_user_event)
        logger.info("GamificationService subscribed to user events.")

    async def _handle_user_event(self, event: IEvent) -> None:
        """Handle user-related events."""
        logger.info(f"GamificationService received user event: {event.type}")
        event_data = event.data
        user_id = event_data.get("user_id")
        event_type = event_data.get("event_type")

        if not user_id:
            logger.warning(f"Invalid user event: missing user_id in {event.id}")
            return

        if event_type == "registered":
            logger.info(f"Processing new user registration for user_id: {user_id}")
            await self.process_user_action(
                user_id=user_id,
                action_type=ActionType.LOGIN,
                context={"source": "user_registration"},
            )
            # Streak is also updated on registration
            await self.update_daily_streak(user_id)

        elif event_type == "daily_activity":
            logger.info(f"Processing daily activity for user_id: {user_id}")
            await self.update_daily_streak(user_id)

    # Stubs for other interface methods
    async def get_user_stats(self, user_id: int) -> UserStats:
        raise NotImplementedError
    async def get_leaderboards(self, user_id: int, types: Optional[List[LeaderboardType]] = None) -> Dict[LeaderboardType, Dict[str, Any]]:
        raise NotImplementedError
    async def admin_adjust_points(self, admin_id: int, user_id: int, adjustment: int, reason: str) -> PointsAwardResult:
        raise NotImplementedError
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok"}
