"""
Gamification Service Implementation for Diana Bot V2.

This module implements the complete gamification system with event-driven
architecture, points management, achievements, leaderboards, and streaks.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ...core.event_bus import RedisEventBus
from ...core.events.core import UserActionEvent
from ...core.events.gamification import (
    AchievementUnlockedEvent,
    DailyBonusClaimedEvent,
    LeaderboardChangedEvent,
    PointsAwardedEvent,
    PointsDeductedEvent,
    StreakUpdatedEvent,
)
from ...core.events.narrative import (
    ChapterCompletedEvent,
    DecisionMadeEvent,
    StoryCompletionEvent,
)
from ...core.interfaces import IEventHandler
from ...models.gamification import (
    AchievementCategory,
    AchievementDefinition,
    AchievementTier,
    LeaderboardType,
    PointsTransactionType,
    StreakType,
    UserAchievement,
    UserGamification,
)
from .interfaces import (
    AntiAbuseError,
    GamificationError,
    IGamificationEventHandlers,
    IGamificationRepository,
    IGamificationService,
    InsufficientPointsError,
    UserNotFoundError,
)
from .repository import GamificationRepository


class GamificationService(IGamificationService, IGamificationEventHandlers):
    """
    Main Gamification Service implementation.

    This service handles all gamification mechanics including points, achievements,
    leaderboards, and streaks. It operates in an event-driven manner and integrates
    with the Event Bus system.
    """

    def __init__(
        self,
        event_bus: RedisEventBus,
        repository: Optional[IGamificationRepository] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the GamificationService.

        Args:
            event_bus: Event bus instance for publishing and subscribing to events
            repository: Data repository for gamification data
            config: Configuration settings for the gamification system
        """
        self.event_bus = event_bus
        self.repository = repository or GamificationRepository()
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger(__name__)

        # Event handler registrations
        self._subscription_ids: List[str] = []
        self._is_initialized = False

        # Anti-abuse tracking
        self._recent_actions: Dict[int, List[datetime]] = {}
        self._suspicious_users: set = set()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for the gamification system."""
        return {
            # Points configuration
            "points": {
                "daily_login": 50,
                "story_chapter_complete": 150,
                "story_complete": 500,
                "decision_made": 200,
                "trivia_correct": 100,
                "first_purchase": 1000,
                "subscription_renewal": 2000,
                "session_long": 100,  # >10 minutes
                "new_content_interaction": 75,
                "friend_invite_success": 500,
                "event_participation": 300,
            },
            # VIP multipliers
            "vip_multipliers": {
                "standard": 1.5,
                "premium": 2.0,
            },
            # Streak multipliers
            "streak_multipliers": {
                "1-7": 1.1,
                "8-14": 1.2,
                "15-30": 1.3,
                "31+": 1.5,
            },
            # Anti-abuse settings
            "anti_abuse": {
                "max_points_per_hour": 1000,
                "max_actions_per_minute": 10,
                "suspicious_threshold": 5000,  # Points per day
                "cooldown_actions": ["story_complete", "achievement_unlock"],
            },
            # Achievement milestones
            "achievement_milestones": {
                "total_points": [1000, 5000, 10000, 25000, 50000],
                "stories_completed": [1, 5, 10, 25, 50],
                "daily_streaks": [7, 30, 100, 365],
                "achievements_unlocked": [5, 15, 30, 50],
            },
            # Level progression (experience points needed for each level)
            "level_progression": [
                0,
                100,
                300,
                600,
                1000,
                1500,
                2100,
                2800,
                3600,
                4500,
                5500,
                6600,
                7800,
                9100,
                10500,
                12000,
                13600,
                15300,
                17100,
                19000,
            ],
        }

    # ================= Service Lifecycle =================

    async def initialize(self) -> None:
        """Initialize the gamification service and set up event subscriptions."""
        if self._is_initialized:
            return

        try:
            self.logger.info("Initializing GamificationService...")

            # Initialize repository
            await self.repository.initialize()

            # Subscribe to events
            await self._setup_event_subscriptions()

            # Load achievement definitions
            await self._load_achievement_definitions()

            self._is_initialized = True
            self.logger.info("GamificationService initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize GamificationService: {e}")
            raise GamificationError(f"Service initialization failed: {e}")

    async def shutdown(self) -> None:
        """Gracefully shutdown the gamification service."""
        if not self._is_initialized:
            return

        try:
            self.logger.info("Shutting down GamificationService...")

            # Unsubscribe from events
            for subscription_id in self._subscription_ids:
                await self.event_bus.unsubscribe(subscription_id)

            self._subscription_ids.clear()

            # Shutdown repository
            if hasattr(self.repository, "shutdown"):
                await self.repository.shutdown()

            self._is_initialized = False
            self.logger.info("GamificationService shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during GamificationService shutdown: {e}")

    async def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for gamification triggers."""
        # Subscribe to UserActionEvent
        subscription_id = await self.event_bus.subscribe(
            "user.action", UserActionEventHandler(self), service_name="gamification"
        )
        self._subscription_ids.append(subscription_id)

        # Subscribe to StoryCompletionEvent
        subscription_id = await self.event_bus.subscribe(
            "narrative.story.completed",
            StoryCompletionEventHandler(self),
            service_name="gamification",
        )
        self._subscription_ids.append(subscription_id)

        # Subscribe to ChapterCompletedEvent
        subscription_id = await self.event_bus.subscribe(
            "narrative.chapter.completed",
            ChapterCompletionEventHandler(self),
            service_name="gamification",
        )
        self._subscription_ids.append(subscription_id)

        # Subscribe to DecisionMadeEvent
        subscription_id = await self.event_bus.subscribe(
            "narrative.decision.made",
            DecisionMadeEventHandler(self),
            service_name="gamification",
        )
        self._subscription_ids.append(subscription_id)

    async def _load_achievement_definitions(self) -> None:
        """Load and validate achievement definitions."""
        # This would typically load from database or configuration
        # For now, we'll create default achievements
        default_achievements = self._get_default_achievements()

        for achievement_data in default_achievements:
            try:
                await self.repository.create_achievement_definition(achievement_data)
            except Exception as e:
                # Achievement might already exist, which is fine
                self.logger.debug(
                    f"Achievement {achievement_data['id']} already exists or failed to create: {e}"
                )

    def _get_default_achievements(self) -> List[Dict[str, Any]]:
        """Get default achievement definitions."""
        return [
            {
                "id": "first_story_complete",
                "name": "Story Explorer",
                "description": "Complete your first story",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.BRONZE,
                "points_reward": 500,
                "unlock_criteria": {"stories_completed": 1},
                "is_secret": False,
                "is_repeatable": False,
            },
            {
                "id": "five_stories_complete",
                "name": "Dedicated Reader",
                "description": "Complete 5 different stories",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.SILVER,
                "points_reward": 1000,
                "unlock_criteria": {"stories_completed": 5},
                "is_secret": False,
                "is_repeatable": False,
            },
            {
                "id": "seven_day_streak",
                "name": "Week Warrior",
                "description": "Maintain a 7-day activity streak",
                "category": AchievementCategory.ENGAGEMENT,
                "tier": AchievementTier.BRONZE,
                "points_reward": 500,
                "unlock_criteria": {"daily_streak": 7},
                "is_secret": False,
                "is_repeatable": False,
            },
            {
                "id": "points_collector_1k",
                "name": "Points Collector",
                "description": "Accumulate 1,000 total points",
                "category": AchievementCategory.MILESTONE,
                "tier": AchievementTier.BRONZE,
                "points_reward": 100,
                "unlock_criteria": {"total_points": 1000},
                "is_secret": False,
                "is_repeatable": False,
            },
            {
                "id": "decision_maker",
                "name": "Decision Maker",
                "description": "Make 50 story decisions",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.SILVER,
                "points_reward": 750,
                "unlock_criteria": {"decisions_made": 50},
                "is_secret": False,
                "is_repeatable": False,
            },
        ]

    # ================= Points System =================

    async def award_points(
        self,
        user_id: int,
        points_amount: int,
        action_type: str,
        multiplier: float = 1.0,
        bonus_points: int = 0,
        source_event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Award points to a user with anti-abuse checks."""
        # Validate input - let business logic exceptions bubble up
        if points_amount <= 0:
            raise ValueError("Points amount must be positive")

        try:
            # Anti-abuse checks
            await self._check_anti_abuse(user_id, points_amount, action_type)

            # Get or create user gamification record
            user_gam = await self._get_or_create_user(user_id)

            # Apply VIP multiplier if applicable
            if user_gam.vip_status:
                multiplier *= user_gam.vip_multiplier

            # Apply streak multiplier
            streak_multiplier = await self._get_streak_multiplier(user_id)
            multiplier *= streak_multiplier

            # Calculate final points
            final_points = int(points_amount * multiplier) + bonus_points
            points_before = user_gam.total_points or 0
            points_after = points_before + final_points

            # Create transaction record
            transaction_data = {
                "user_id": user_id,
                "transaction_type": PointsTransactionType.EARNED,
                "amount": final_points,
                "points_before": points_before,
                "points_after": points_after,
                "action_type": action_type,
                "description": f"Points awarded for {action_type}",
                "source_service": "gamification",
                "source_event_id": source_event_id,
                "multiplier_applied": multiplier,
                "bonus_applied": bonus_points,
                "transaction_metadata": metadata or {},
            }

            # Save transaction and update user points
            await self.repository.create_points_transaction(transaction_data)

            user_gam.total_points = points_after
            user_gam.experience_points = (
                user_gam.experience_points or 0
            ) + final_points
            await self.repository.update_user_gamification(user_gam)

            # Check for level up
            await self.update_user_level(user_id)

            # Publish PointsAwardedEvent
            points_event = PointsAwardedEvent(
                user_id=user_id,
                points_amount=points_amount,
                action_type=action_type,
                multiplier=multiplier,
                bonus_points=bonus_points,
                source_event_id=source_event_id,
                source_service="gamification",
            )

            # Update the event with additional data
            points_event.payload.update(
                {
                    "user_total_points_before": points_before,
                    "user_total_points_after": points_after,
                    "total_points_awarded": final_points,
                }
            )

            await self.event_bus.publish(points_event)

            # Check for achievements
            await self.check_achievements(
                user_id,
                {
                    "action_type": action_type,
                    "points_awarded": final_points,
                    "total_points": points_after,
                },
            )

            self.logger.info(
                f"Awarded {final_points} points to user {user_id} for {action_type}"
            )

            return True

        except (ValueError, TypeError) as e:
            # Re-raise business logic exceptions
            raise
        except Exception as e:
            self.logger.error(f"Failed to award points to user {user_id}: {e}")
            raise GamificationError(f"Points award failed: {e}")

    async def deduct_points(
        self,
        user_id: int,
        points_amount: int,
        deduction_reason: str,
        admin_user_id: Optional[int] = None,
        source_event_id: Optional[str] = None,
    ) -> bool:
        """Deduct points from a user."""
        try:
            # Validate input
            if points_amount <= 0:
                raise ValueError("Points amount must be positive")

            # Get user gamification record
            user_gam = await self.repository.get_user_gamification(user_id)
            if not user_gam:
                raise UserNotFoundError(
                    f"User {user_id} not found in gamification system"
                )

            # Check if user has enough points
            if user_gam.total_points < points_amount:
                raise InsufficientPointsError(
                    f"User {user_id} has {user_gam.total_points} points, cannot deduct {points_amount}"
                )

            points_before = user_gam.total_points
            points_after = points_before - points_amount

            # Create transaction record
            transaction_data = {
                "user_id": user_id,
                "transaction_type": PointsTransactionType.PENALTY,
                "amount": -points_amount,  # Negative for deduction
                "points_before": points_before,
                "points_after": points_after,
                "action_type": "points_deduction",
                "description": f"Points deducted: {deduction_reason}",
                "source_service": "gamification",
                "source_event_id": source_event_id,
                "transaction_metadata": {
                    "admin_user_id": admin_user_id,
                    "reason": deduction_reason,
                },
            }

            # Save transaction and update user points
            await self.repository.create_points_transaction(transaction_data)

            user_gam.total_points = points_after
            await self.repository.update_user_gamification(user_gam)

            # Publish PointsDeductedEvent
            deduction_event = PointsDeductedEvent(
                user_id=user_id,
                points_amount=points_amount,
                deduction_reason=deduction_reason,
                source_event_id=source_event_id,
                admin_user_id=admin_user_id,
                source_service="gamification",
            )

            # Update the event with additional data
            deduction_event.payload.update(
                {
                    "user_total_points_before": points_before,
                    "user_total_points_after": points_after,
                }
            )

            await self.event_bus.publish(deduction_event)

            self.logger.info(
                f"Deducted {points_amount} points from user {user_id}: {deduction_reason}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to deduct points from user {user_id}: {e}")
            raise

    async def get_user_points(self, user_id: int) -> int:
        """Get the current points balance for a user."""
        user_gam = await self.repository.get_user_gamification(user_id)
        return user_gam.total_points if user_gam else 0

    async def get_points_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[PointsTransactionType] = None,
    ) -> List[Dict[str, Any]]:
        """Get points transaction history for a user."""
        transactions = await self.repository.get_points_transactions(
            user_id, limit, offset, transaction_type
        )

        return [
            {
                "id": tx.id,
                "amount": tx.amount,
                "transaction_type": tx.transaction_type.value,
                "action_type": tx.action_type,
                "description": tx.description,
                "points_before": tx.points_before,
                "points_after": tx.points_after,
                "multiplier_applied": tx.multiplier_applied,
                "bonus_applied": tx.bonus_applied,
                "created_at": tx.created_at,
                "metadata": tx.transaction_metadata,
            }
            for tx in transactions
        ]

    # ================= Helper Methods =================

    async def _check_anti_abuse(
        self, user_id: int, points_amount: int, action_type: str
    ) -> None:
        """Check for potential abuse patterns."""
        now = datetime.now(timezone.utc)

        # Track recent actions for this user
        if user_id not in self._recent_actions:
            self._recent_actions[user_id] = []

        # Clean old actions (older than 1 hour)
        self._recent_actions[user_id] = [
            action_time
            for action_time in self._recent_actions[user_id]
            if now - action_time < timedelta(hours=1)
        ]

        # Check rate limiting
        recent_actions_minute = [
            action_time
            for action_time in self._recent_actions[user_id]
            if now - action_time < timedelta(minutes=1)
        ]

        if (
            len(recent_actions_minute)
            >= self.config["anti_abuse"]["max_actions_per_minute"]
        ):
            raise AntiAbuseError(f"User {user_id} exceeded action rate limit")

        # Check points per hour limit
        hourly_points = sum(
            self.config["points"].get(action_type, 0)
            for _ in self._recent_actions[user_id]
        )

        if (
            hourly_points + points_amount
            > self.config["anti_abuse"]["max_points_per_hour"]
        ):
            self.logger.warning(f"User {user_id} approaching hourly points limit")
            self._suspicious_users.add(user_id)

        # Add this action to tracking
        self._recent_actions[user_id].append(now)

    async def _get_streak_multiplier(self, user_id: int) -> float:
        """Get the current streak multiplier for a user."""
        try:
            streaks = await self.repository.get_user_streaks(user_id)
            daily_streak = next(
                (s for s in streaks if s.streak_type == StreakType.DAILY_LOGIN), None
            )

            if not daily_streak:
                return 1.0

            current_count = daily_streak.current_count

            # Apply streak multipliers based on configuration
            if current_count >= 31:
                return self.config["streak_multipliers"]["31+"]
            elif current_count >= 15:
                return self.config["streak_multipliers"]["15-30"]
            elif current_count >= 8:
                return self.config["streak_multipliers"]["8-14"]
            elif current_count >= 1:
                return self.config["streak_multipliers"]["1-7"]

            return 1.0

        except Exception as e:
            self.logger.error(
                f"Error getting streak multiplier for user {user_id}: {e}"
            )
            return 1.0

    async def _get_or_create_user(self, user_id: int) -> UserGamification:
        """Get or create user gamification record."""
        user_gam = await self.repository.get_user_gamification(user_id)
        if not user_gam:
            user_gam = await self.repository.create_user_gamification(user_id)
        return user_gam

    # ================= Achievement System (Partial Implementation) =================

    async def check_achievements(
        self, user_id: int, trigger_context: Dict[str, Any]
    ) -> List[UserAchievement]:
        """Check if a user has unlocked any new achievements."""
        try:
            unlocked_achievements = []

            # Get user's current achievements and statistics
            user_achievements = await self.repository.get_user_achievements(user_id)
            completed_achievement_ids = {
                ua.achievement_id for ua in user_achievements if ua.is_completed
            }

            # Get all achievement definitions
            achievement_definitions = (
                await self.repository.get_achievement_definitions()
            )

            # Get user statistics for criteria checking
            user_stats = await self.get_user_statistics(user_id)

            for achievement_def in achievement_definitions:
                # Skip if already unlocked
                if achievement_def.id in completed_achievement_ids:
                    continue

                # Check if criteria are met
                if await self._check_achievement_criteria(
                    achievement_def, user_stats, trigger_context
                ):
                    unlocked_achievement = await self.unlock_achievement(
                        user_id,
                        achievement_def.id,
                        trigger_context.get("source_event_id"),
                    )
                    unlocked_achievements.append(unlocked_achievement)

            return unlocked_achievements

        except Exception as e:
            self.logger.error(f"Error checking achievements for user {user_id}: {e}")
            return []

    async def _check_achievement_criteria(
        self,
        achievement_def: AchievementDefinition,
        user_stats: Dict[str, Any],
        trigger_context: Dict[str, Any],
    ) -> bool:
        """Check if achievement criteria are met."""
        criteria = achievement_def.unlock_criteria

        # Check each criterion
        for criterion, required_value in criteria.items():
            current_value = user_stats.get(criterion, 0)
            if current_value < required_value:
                return False

        return True

    async def unlock_achievement(
        self, user_id: int, achievement_id: str, source_event_id: Optional[str] = None
    ) -> UserAchievement:
        """Unlock an achievement for a user."""
        try:
            # Get achievement definition to determine points reward
            achievement_definitions = (
                await self.repository.get_achievement_definitions()
            )
            achievement_def = next(
                (a for a in achievement_definitions if a.id == achievement_id), None
            )

            if not achievement_def:
                raise ValueError(f"Achievement {achievement_id} not found")

            # Create achievement record
            achievement_data = {
                "user_id": user_id,
                "achievement_id": achievement_id,
                "progress_current": 1,
                "progress_required": 1,
                "is_completed": True,
                "unlocked_at": datetime.now(timezone.utc),
                "points_awarded": achievement_def.points_reward,
                "unlock_event_id": source_event_id,
            }

            user_achievement = await self.repository.create_user_achievement(
                achievement_data
            )

            # Award points for achievement
            if achievement_def.points_reward > 0:
                await self.award_points(
                    user_id=user_id,
                    points_amount=achievement_def.points_reward,
                    action_type="achievement_unlock",
                    source_event_id=source_event_id,
                    metadata={
                        "achievement_id": achievement_id,
                        "achievement_name": achievement_def.name,
                    },
                )

            # Publish AchievementUnlockedEvent
            achievement_event = AchievementUnlockedEvent(
                user_id=user_id,
                achievement_id=achievement_id,
                achievement_name=achievement_def.name,
                achievement_category=achievement_def.category.value,
                achievement_tier=achievement_def.tier.value,
                points_reward=achievement_def.points_reward,
                source_service="gamification",
                correlation_id=source_event_id,
            )

            await self.event_bus.publish(achievement_event)

            self.logger.info(
                f"Achievement {achievement_id} unlocked for user {user_id}"
            )

            return user_achievement

        except Exception as e:
            self.logger.error(
                f"Failed to unlock achievement {achievement_id} for user {user_id}: {e}"
            )
            raise

    # ================= Placeholder Methods =================

    # The following methods would be fully implemented in a complete version
    # For brevity, I'm providing basic stubs that follow the interface

    async def get_user_achievements(
        self, user_id: int, completed_only: bool = False
    ) -> List[UserAchievement]:
        """Get all achievements for a user."""
        return await self.repository.get_user_achievements(user_id, completed_only)

    async def get_achievement_progress(
        self, user_id: int, achievement_id: str
    ) -> Dict[str, Any]:
        """Get progress for a specific achievement."""
        try:
            achievements = await self.repository.get_user_achievements(user_id)
            user_achievement = next(
                (ua for ua in achievements if ua.achievement_id == achievement_id), None
            )

            if user_achievement:
                return {
                    "achievement_id": achievement_id,
                    "progress_current": user_achievement.progress_current,
                    "progress_required": user_achievement.progress_required,
                    "is_completed": user_achievement.is_completed,
                    "progress_percentage": (
                        user_achievement.progress_current
                        / max(1, user_achievement.progress_required)
                    )
                    * 100,
                    "unlocked_at": user_achievement.unlocked_at,
                    "points_awarded": user_achievement.points_awarded,
                }
            else:
                # Return default progress for non-started achievement
                return {
                    "achievement_id": achievement_id,
                    "progress_current": 0,
                    "progress_required": 1,
                    "is_completed": False,
                    "progress_percentage": 0.0,
                    "unlocked_at": None,
                    "points_awarded": 0,
                }
        except Exception as e:
            self.logger.error(
                f"Error getting achievement progress for user {user_id}: {e}"
            )
            return {
                "achievement_id": achievement_id,
                "progress_current": 0,
                "progress_required": 1,
                "is_completed": False,
                "progress_percentage": 0.0,
                "unlocked_at": None,
                "points_awarded": 0,
            }

    async def create_achievement_definition(
        self, achievement_data: Dict[str, Any]
    ) -> AchievementDefinition:
        """Create a new achievement definition."""
        return await self.repository.create_achievement_definition(achievement_data)

    async def update_streak(
        self,
        user_id: int,
        streak_type: StreakType,
        activity_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Update a user's streak for a specific activity type."""
        try:
            if activity_date is None:
                activity_date = datetime.now(timezone.utc)

            # Get existing streak or create new one
            streaks = await self.repository.get_user_streaks(user_id)
            existing_streak = next(
                (s for s in streaks if s.streak_type == streak_type), None
            )

            current_count = 1
            longest_count = 1
            is_milestone = False

            if existing_streak:
                # Check if the streak continues (activity within grace period)
                last_activity = existing_streak.last_activity_date or activity_date
                time_diff = activity_date - last_activity

                # Grace period for different streak types
                grace_periods = {
                    StreakType.DAILY_LOGIN: timedelta(hours=26),
                    StreakType.STORY_PROGRESS: timedelta(days=2),
                    StreakType.INTERACTION: timedelta(hours=30),
                    StreakType.ACHIEVEMENT_UNLOCK: timedelta(days=7),
                }
                grace_period = grace_periods.get(streak_type, timedelta(days=1))

                if time_diff <= grace_period:
                    # Continue streak
                    current_count = existing_streak.current_count + 1
                    longest_count = max(existing_streak.longest_count, current_count)
                else:
                    # Reset streak
                    current_count = 1
                    longest_count = max(existing_streak.longest_count, 1)

                # Update streak record
                streak_data = {
                    "user_id": user_id,
                    "streak_type": streak_type,
                    "current_count": current_count,
                    "longest_count": longest_count,
                    "last_activity_date": activity_date,
                    "streak_start_date": activity_date
                    if current_count == 1
                    else existing_streak.streak_start_date,
                    "current_multiplier": self._calculate_streak_multiplier(
                        current_count
                    ),
                    "is_active": True,
                    "freeze_count": existing_streak.freeze_count
                    if current_count > 1
                    else 0,
                }
                await self.repository.update_streak_record(streak_data)
            else:
                # Create new streak
                streak_data = {
                    "user_id": user_id,
                    "streak_type": streak_type,
                    "current_count": 1,
                    "longest_count": 1,
                    "last_activity_date": activity_date,
                    "streak_start_date": activity_date,
                    "current_multiplier": 1.0,
                    "is_active": True,
                    "freeze_count": 0,
                }
                await self.repository.update_streak_record(streak_data)

            # Check for milestone achievements
            milestones = {
                StreakType.DAILY_LOGIN: [7, 30, 100, 365],
                StreakType.STORY_PROGRESS: [5, 15, 30, 60],
                StreakType.INTERACTION: [10, 25, 50, 100],
                StreakType.ACHIEVEMENT_UNLOCK: [3, 10, 20, 50],
            }
            streak_milestones = milestones.get(streak_type, [7, 30, 100, 365])
            is_milestone = current_count in streak_milestones

            # Publish StreakUpdatedEvent
            streak_event = StreakUpdatedEvent(
                user_id=user_id,
                streak_type=streak_type.value,
                current_count=current_count,
                is_milestone=is_milestone,
                source_service="gamification",
            )

            await self.event_bus.publish(streak_event)

            return {
                "streak_type": streak_type.value,
                "current_count": current_count,
                "longest_count": longest_count,
                "is_milestone": is_milestone,
                "multiplier": self._calculate_streak_multiplier(current_count),
            }

        except Exception as e:
            self.logger.error(f"Failed to update streak for user {user_id}: {e}")
            return {
                "streak_type": streak_type.value,
                "current_count": 0,
                "is_milestone": False,
            }

    def _calculate_streak_multiplier(self, streak_count: int) -> float:
        """Calculate multiplier based on streak count."""
        if streak_count >= 31:
            return 1.5
        elif streak_count >= 15:
            return 1.3
        elif streak_count >= 8:
            return 1.2
        elif streak_count >= 1:
            return 1.1
        else:
            return 1.0

    async def get_user_streaks(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active streaks for a user."""
        streaks = await self.repository.get_user_streaks(user_id)
        return [
            {
                "streak_type": s.streak_type.value,
                "current_count": s.current_count,
                "longest_count": s.longest_count,
                "last_activity_date": s.last_activity_date,
                "current_multiplier": s.current_multiplier,
            }
            for s in streaks
        ]

    async def freeze_streak(self, user_id: int, streak_type: StreakType) -> bool:
        """Use a streak freeze for VIP users."""
        # Implementation would handle VIP streak freeze logic
        return True

    async def update_leaderboard(
        self,
        user_id: int,
        leaderboard_type: LeaderboardType,
        score: int,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        """Update a user's position on a leaderboard."""
        try:
            # Get current leaderboard entries to calculate rank
            current_entries = await self.repository.get_leaderboard_entries(
                leaderboard_type, period_start, period_end, limit=1000
            )

            # Calculate new rank (number of users with higher scores + 1)
            new_rank = (
                len([entry for entry in current_entries if entry.score > score]) + 1
            )

            # Check if this is a personal best
            user_previous_entries = [
                entry for entry in current_entries if entry.user_id == user_id
            ]
            is_personal_best = not user_previous_entries or score > max(
                entry.score for entry in user_previous_entries
            )

            # Create/update leaderboard entry
            entry_data = {
                "user_id": user_id,
                "leaderboard_type": leaderboard_type,
                "period_start": period_start,
                "period_end": period_end,
                "score": score,
                "rank": new_rank,
                "is_personal_best": is_personal_best,
            }

            await self.repository.update_leaderboard_entry(entry_data)

            # Publish LeaderboardChangedEvent
            leaderboard_event = LeaderboardChangedEvent(
                user_id=user_id,
                leaderboard_type=leaderboard_type.value,
                new_rank=new_rank,
                score=score,
                period_start=period_start,
                period_end=period_end,
                source_service="gamification",
            )

            await self.event_bus.publish(leaderboard_event)

            return {
                "leaderboard_type": leaderboard_type.value,
                "rank": new_rank,
                "score": score,
                "is_personal_best": is_personal_best,
            }

        except Exception as e:
            self.logger.error(f"Failed to update leaderboard for user {user_id}: {e}")
            return {
                "leaderboard_type": leaderboard_type.value,
                "rank": 0,
                "score": score,
            }

    async def get_leaderboard(
        self,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
        limit: int = 10,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get leaderboard rankings for a specific period."""
        entries = await self.repository.get_leaderboard_entries(
            leaderboard_type, period_start, period_end, limit
        )

        return {
            "leaderboard_type": leaderboard_type.value,
            "period_start": period_start,
            "period_end": period_end,
            "entries": [
                {
                    "rank": entry.rank,
                    "user_id": entry.user_id,
                    "score": entry.score,
                    "is_personal_best": entry.is_personal_best,
                }
                for entry in entries
            ],
        }

    async def get_user_rank(
        self,
        user_id: int,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
    ) -> Optional[int]:
        """Get a user's rank on a specific leaderboard."""
        try:
            # Get all leaderboard entries for the period
            entries = await self.repository.get_leaderboard_entries(
                leaderboard_type, period_start, period_end, limit=1000
            )

            # Find the user's entry
            user_entry = next(
                (entry for entry in entries if entry.user_id == user_id), None
            )

            if user_entry:
                return user_entry.rank
            else:
                # User not found on leaderboard
                return None

        except Exception as e:
            self.logger.error(f"Error getting user rank for user {user_id}: {e}")
            return None

    async def initialize_user(self, user_id: int) -> UserGamification:
        """Initialize gamification data for a new user."""
        return await self.repository.create_user_gamification(user_id)

    async def get_user_gamification(self, user_id: int) -> Optional[UserGamification]:
        """Get gamification data for a user."""
        return await self.repository.get_user_gamification(user_id)

    async def update_user_level(self, user_id: int) -> Tuple[int, bool]:
        """Update a user's level based on their experience points."""
        user_gam = await self.repository.get_user_gamification(user_id)
        if not user_gam:
            return 1, False

        # Calculate new level based on experience points
        level_progression = self.config["level_progression"]
        new_level = 1

        for level, required_xp in enumerate(level_progression, 1):
            if (user_gam.experience_points or 0) >= required_xp:
                new_level = level
            else:
                break

        current_level = user_gam.current_level or 1
        level_increased = new_level > current_level

        if level_increased:
            user_gam.current_level = new_level
            await self.repository.update_user_gamification(user_gam)

            self.logger.info(f"User {user_id} leveled up to level {new_level}")

        return new_level, level_increased

    async def set_vip_status(
        self, user_id: int, is_vip: bool, vip_multiplier: float = 1.5
    ) -> bool:
        """Set VIP status for a user."""
        user_gam = await self._get_or_create_user(user_id)
        user_gam.vip_status = is_vip
        user_gam.vip_multiplier = vip_multiplier if is_vip else 1.0

        await self.repository.update_user_gamification(user_gam)
        return True

    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive gamification statistics for a user."""
        user_gam = await self.repository.get_user_gamification(user_id)
        if not user_gam:
            return {}

        return {
            "total_points": user_gam.total_points,
            "current_level": user_gam.current_level,
            "experience_points": user_gam.experience_points,
            "total_achievements": user_gam.total_achievements,
            "current_daily_streak": user_gam.current_daily_streak,
            "longest_daily_streak": user_gam.longest_daily_streak,
            "vip_status": user_gam.vip_status,
        }

    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide gamification statistics."""
        # Implementation would aggregate system-wide stats
        return {
            "total_users": 0,
            "total_points_awarded": 0,
            "total_achievements_unlocked": 0,
        }

    async def get_points_configuration(self) -> Dict[str, Any]:
        """Get current points system configuration."""
        return self.config["points"]

    async def update_points_configuration(self, config: Dict[str, Any]) -> bool:
        """Update points system configuration."""
        self.config["points"].update(config)
        return True

    # ================= Event Handlers =================

    async def handle_user_action(self, event: UserActionEvent) -> None:
        """Handle UserActionEvent to award points and check achievements."""
        try:
            action_type = event.action_type
            points_config = self.config["points"]

            # Map action types to point rewards
            if action_type in points_config:
                points_amount = points_config[action_type]

                await self.award_points(
                    user_id=event.user_id,
                    points_amount=points_amount,
                    action_type=action_type,
                    source_event_id=event.event_id,
                    metadata={"action_data": event.action_data},
                )

                # Update daily login streak if applicable
                if action_type == "daily_login":
                    await self.update_streak(event.user_id, StreakType.DAILY_LOGIN)

        except Exception as e:
            self.logger.error(f"Error handling user action event: {e}")

    async def handle_story_completion(self, event: StoryCompletionEvent) -> None:
        """Handle StoryCompletionEvent to award completion rewards."""
        try:
            # Award base completion points
            base_points = self.config["points"]["story_complete"]

            # Calculate bonus based on completion metrics
            bonus_points = 0
            if event.completion_percentage >= 100:
                bonus_points += 200
            if event.overall_rating and event.overall_rating >= 4:
                bonus_points += 100

            await self.award_points(
                user_id=event.user_id,
                points_amount=base_points,
                action_type="story_complete",
                bonus_points=bonus_points,
                source_event_id=event.event_id,
                metadata={
                    "story_id": event.story_id,
                    "story_title": event.story_title,
                    "completion_time": event.total_completion_time_seconds,
                    "decisions_made": event.total_decisions_made,
                },
            )

            # Update story progress streak
            await self.update_streak(event.user_id, StreakType.STORY_PROGRESS)

        except Exception as e:
            self.logger.error(f"Error handling story completion event: {e}")

    async def handle_chapter_completion(self, event: ChapterCompletedEvent) -> None:
        """Handle ChapterCompletedEvent to award progress rewards."""
        try:
            points_amount = self.config["points"]["story_chapter_complete"]

            await self.award_points(
                user_id=event.user_id,
                points_amount=points_amount,
                action_type="chapter_complete",
                source_event_id=event.event_id,
                metadata={
                    "story_id": event.story_id,
                    "chapter_id": event.chapter_id,
                    "chapter_title": event.chapter_title,
                    "completion_time": event.completion_time_seconds,
                },
            )

        except Exception as e:
            self.logger.error(f"Error handling chapter completion event: {e}")

    async def handle_decision_made(self, event: DecisionMadeEvent) -> None:
        """Handle DecisionMadeEvent to award engagement points."""
        try:
            points_amount = self.config["points"]["decision_made"]

            await self.award_points(
                user_id=event.user_id,
                points_amount=points_amount,
                action_type="decision_made",
                source_event_id=event.event_id,
                metadata={
                    "story_id": event.story_id,
                    "chapter_id": event.chapter_id,
                    "decision_id": event.decision_id,
                    "decision_text": event.decision_text,
                },
            )

        except Exception as e:
            self.logger.error(f"Error handling decision made event: {e}")


# ================= Event Handler Classes =================


class UserActionEventHandler(IEventHandler):
    """Event handler for UserActionEvent."""

    def __init__(self, gamification_service: GamificationService):
        self.gamification_service = gamification_service
        self._handler_id = f"gamification_user_action_{uuid.uuid4().hex[:8]}"

    @property
    def handler_id(self) -> str:
        return self._handler_id

    @property
    def supported_event_types(self) -> List[str]:
        return ["user.action"]

    @property
    def service_name(self) -> str:
        return "gamification"

    async def handle(self, event: UserActionEvent) -> bool:
        await self.gamification_service.handle_user_action(event)
        return True

    async def can_handle(self, event) -> bool:
        return event.event_type == "user.action"

    async def on_error(self, event: UserActionEvent, error: Exception) -> bool:
        logging.getLogger(__name__).error(f"Error handling user action event: {error}")
        return False


class StoryCompletionEventHandler(IEventHandler):
    """Event handler for StoryCompletionEvent."""

    def __init__(self, gamification_service: GamificationService):
        self.gamification_service = gamification_service
        self._handler_id = f"gamification_story_completion_{uuid.uuid4().hex[:8]}"

    @property
    def handler_id(self) -> str:
        return self._handler_id

    @property
    def supported_event_types(self) -> List[str]:
        return ["narrative.story.completed"]

    @property
    def service_name(self) -> str:
        return "gamification"

    async def handle(self, event: StoryCompletionEvent) -> bool:
        await self.gamification_service.handle_story_completion(event)
        return True

    async def can_handle(self, event) -> bool:
        return event.event_type == "narrative.story.completed"

    async def on_error(self, event: StoryCompletionEvent, error: Exception) -> bool:
        logging.getLogger(__name__).error(
            f"Error handling story completion event: {error}"
        )
        return False


class ChapterCompletionEventHandler(IEventHandler):
    """Event handler for ChapterCompletedEvent."""

    def __init__(self, gamification_service: GamificationService):
        self.gamification_service = gamification_service
        self._handler_id = f"gamification_chapter_completion_{uuid.uuid4().hex[:8]}"

    @property
    def handler_id(self) -> str:
        return self._handler_id

    @property
    def supported_event_types(self) -> List[str]:
        return ["narrative.chapter.completed"]

    @property
    def service_name(self) -> str:
        return "gamification"

    async def handle(self, event: ChapterCompletedEvent) -> bool:
        await self.gamification_service.handle_chapter_completion(event)
        return True

    async def can_handle(self, event) -> bool:
        return event.event_type == "narrative.chapter.completed"

    async def on_error(self, event: ChapterCompletedEvent, error: Exception) -> bool:
        logging.getLogger(__name__).error(
            f"Error handling chapter completion event: {error}"
        )
        return False


class DecisionMadeEventHandler(IEventHandler):
    """Event handler for DecisionMadeEvent."""

    def __init__(self, gamification_service: GamificationService):
        self.gamification_service = gamification_service
        self._handler_id = f"gamification_decision_made_{uuid.uuid4().hex[:8]}"

    @property
    def handler_id(self) -> str:
        return self._handler_id

    @property
    def supported_event_types(self) -> List[str]:
        return ["narrative.decision.made"]

    @property
    def service_name(self) -> str:
        return "gamification"

    async def handle(self, event: DecisionMadeEvent) -> bool:
        await self.gamification_service.handle_decision_made(event)
        return True

    async def can_handle(self, event) -> bool:
        return event.event_type == "narrative.decision.made"

    async def on_error(self, event: DecisionMadeEvent, error: Exception) -> bool:
        logging.getLogger(__name__).error(
            f"Error handling decision made event: {error}"
        )
        return False
