"""
Complete Gamification Service Implementation for Diana Bot V2.

This module implements the complete gamification system orchestrator with
event-driven architecture, all engines integrated, and comprehensive functionality.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ...core.event_bus import RedisEventBus
from ...core.events.gamification import (
    AchievementUnlockedEvent,
    LeaderboardChangedEvent,
    PointsAwardedEvent,
    PointsDeductedEvent,
    StreakUpdatedEvent,
)
from ...models.gamification import (
    AchievementDefinition,
    LeaderboardType,
    PointsTransactionType,
    StreakType,
    UserAchievement,
    UserGamification,
)
from .engines import AchievementEngine, LeaderboardEngine, PointsEngine, StreakEngine
from .event_handlers import create_gamification_event_handlers
from .interfaces import (
    AntiAbuseError,
    GamificationError,
    IGamificationRepository,
    IGamificationService,
    InsufficientPointsError,
    UserNotFoundError,
)
from .repository_impl import GamificationRepositoryImpl


class GamificationServiceImpl(IGamificationService):
    """
    Complete Gamification Service implementation.

    This service orchestrates all gamification mechanics including points, achievements,
    leaderboards, and streaks using dedicated engines and event-driven architecture.
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
        self.repository = repository or GamificationRepositoryImpl()
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger(__name__)

        # Initialize engines
        self.points_engine = PointsEngine(self.config)
        self.achievement_engine = AchievementEngine(self.config)
        self.streak_engine = StreakEngine(self.config)
        self.leaderboard_engine = LeaderboardEngine(self.config)

        # Event handler registrations
        self._subscription_ids: List[str] = []
        self._is_initialized = False

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for the gamification system."""
        return {
            # Points configuration
            "points": {
                "daily_login": 50,
                "story_chapter_complete": 150,
                "story_complete": 500,
                "decision_made": 25,
                "tutorial_completed": 100,
                "session_start": 10,
                "session_long": 100,  # >10 minutes
                "friend_invite": 500,
                "content_share": 25,
                "subscription_purchase": 2000,
                "premium_feature_used": 50,
                "story_started": 25,
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
                "total_points": [1000, 5000, 10000, 25000, 50000, 100000],
                "stories_completed": [1, 5, 10, 25, 50],
                "daily_streaks": [7, 30, 100, 365],
                "achievements_unlocked": [5, 15, 30, 50],
                "decisions_made": [50, 200, 500, 1000],
                "level_reached": [10, 25, 50],
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
                21000,
                23100,
                25300,
                27600,
                30000,
                32500,
                35100,
                37800,
                40600,
                43500,
                46500,
                49600,
                52800,
                56100,
                59500,
                63000,
                66600,
                70300,
                74100,
                78000,
                82000,
                86100,
                90300,
                94600,
                99000,
                103500,
                108100,
                112800,
                117600,
                122500,
            ],
            # Leaderboard settings
            "leaderboard_settings": {
                "update_frequency_minutes": 5,
                "max_entries_per_board": 1000,
                "position_change_threshold": 5,
                "personal_best_bonus_points": 100,
            },
            # Streak milestones
            "streak_milestones": {
                StreakType.DAILY_LOGIN: [7, 30, 100, 365],
                StreakType.STORY_PROGRESS: [5, 15, 30, 60],
                StreakType.INTERACTION: [10, 25, 50, 100],
                StreakType.ACHIEVEMENT_UNLOCK: [3, 10, 20, 50],
            },
            # VIP features
            "vip_features": {
                "max_freezes_per_month": 3,
                "min_streak_for_freeze": 7,
            },
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

            # Load default achievement definitions
            await self._load_default_achievements()

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
        # Create event handlers
        handlers = create_gamification_event_handlers(self)

        # Subscribe each handler
        for handler in handlers:
            for event_type in handler.supported_event_types:
                subscription_id = await self.event_bus.subscribe(
                    event_type, handler, service_name="gamification"
                )
                self._subscription_ids.append(subscription_id)

    async def _load_default_achievements(self) -> None:
        """Load default achievement definitions."""
        default_achievements = self.achievement_engine.get_default_achievements()

        for achievement_data in default_achievements:
            try:
                await self.repository.create_achievement_definition(achievement_data)
            except Exception as e:
                # Achievement might already exist, which is fine
                self.logger.debug(
                    f"Achievement {achievement_data['id']} already exists or failed to create: {e}"
                )

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
        """Award points to a user with comprehensive validation and event publishing."""
        try:
            # Get or create user gamification record
            user_gam = await self._get_or_create_user(user_id)

            # Validate transaction with anti-abuse checks
            self.points_engine.validate_points_transaction(
                user_id, points_amount, action_type, PointsTransactionType.EARNED
            )

            # Get streak multiplier
            user_streaks = await self.repository.get_user_streaks(user_id)
            streak_multiplier = 1.0
            for streak in user_streaks:
                if streak.streak_type == StreakType.DAILY_LOGIN:
                    streak_multiplier = self.streak_engine.calculate_streak_multiplier(
                        streak.streak_type, streak.current_count, user_gam
                    )
                    break

            # Calculate final points
            (
                final_points,
                calculation_details,
            ) = self.points_engine.calculate_points_award(
                user_gam,
                points_amount,
                action_type,
                multiplier,
                bonus_points,
                streak_multiplier,
            )

            points_before = user_gam.total_points
            points_after = points_before + final_points

            # Create transaction record
            transaction_data = self.points_engine.create_transaction_data(
                user_id=user_id,
                transaction_type=PointsTransactionType.EARNED,
                amount=final_points,
                points_before=points_before,
                points_after=points_after,
                action_type=action_type,
                description=f"Points awarded for {action_type}",
                calculation_details=calculation_details,
                source_event_id=source_event_id,
                metadata=metadata,
            )

            # Save transaction and update user points
            await self.repository.create_points_transaction(transaction_data)

            user_gam.total_points = points_after
            user_gam.experience_points += final_points
            await self.repository.update_user_gamification(user_gam)

            # Check for level up
            new_level, level_increased = await self.update_user_level(user_id)

            # Publish PointsAwardedEvent
            points_event = PointsAwardedEvent(
                user_id=user_id,
                points_amount=points_amount,
                action_type=action_type,
                multiplier=calculation_details["final_multiplier"],
                bonus_points=calculation_details["total_bonus"],
                source_event_id=source_event_id,
                source_service="gamification",
            )

            # Update the event with additional data
            points_event.payload.update(
                {
                    "user_total_points_before": points_before,
                    "user_total_points_after": points_after,
                    "total_points_awarded": final_points,
                    "level_increased": level_increased,
                    "new_level": new_level,
                    "calculation_details": calculation_details,
                }
            )

            await self.event_bus.publish(points_event)

            # Check for achievements
            await self._check_achievements_for_points(
                user_id, action_type, final_points, points_after
            )

            self.logger.info(
                f"Awarded {final_points} points to user {user_id} for {action_type}"
            )

            return True

        except (AntiAbuseError, ValueError) as e:
            self.logger.warning(f"Points award rejected for user {user_id}: {e}")
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
            # Get user gamification record
            user_gam = await self.repository.get_user_gamification(user_id)
            if not user_gam:
                raise UserNotFoundError(
                    f"User {user_id} not found in gamification system"
                )

            # Validate deduction
            self.points_engine.validate_points_deduction(user_gam, points_amount)

            points_before = user_gam.total_points
            points_after = points_before - points_amount

            # Create transaction record
            transaction_data = self.points_engine.create_transaction_data(
                user_id=user_id,
                transaction_type=PointsTransactionType.PENALTY,
                amount=-points_amount,  # Negative for deduction
                points_before=points_before,
                points_after=points_after,
                action_type="points_deduction",
                description=f"Points deducted: {deduction_reason}",
                source_event_id=source_event_id,
                metadata={"admin_user_id": admin_user_id, "reason": deduction_reason},
            )

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

        except (InsufficientPointsError, UserNotFoundError) as e:
            self.logger.warning(f"Points deduction failed for user {user_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to deduct points from user {user_id}: {e}")
            raise GamificationError(f"Points deduction failed: {e}")

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
                "created_at": tx.created_at.isoformat(),
                "metadata": tx.transaction_metadata,
            }
            for tx in transactions
        ]

    # ================= Achievement System =================

    async def check_achievements(
        self, user_id: int, trigger_context: Dict[str, Any]
    ) -> List[UserAchievement]:
        """Check if a user has unlocked any new achievements."""
        try:
            # Get user's current achievements and statistics
            user_achievements = await self.repository.get_user_achievements(user_id)
            achievement_definitions = (
                await self.repository.get_achievement_definitions()
            )
            user_stats = await self.get_user_statistics(user_id)

            # Use achievement engine to evaluate
            unlockable = self.achievement_engine.evaluate_achievements(
                user_stats, achievement_definitions, user_achievements, trigger_context
            )

            unlocked_achievements = []

            for achievement_def, unlock_context in unlockable:
                # Create user achievement record
                user_achievement_data = self.achievement_engine.create_user_achievement(
                    user_id,
                    achievement_def,
                    unlock_context,
                    trigger_context.get("source_event_id"),
                )

                # Save to database
                user_achievement = await self.repository.create_user_achievement(
                    user_achievement_data
                )
                unlocked_achievements.append(user_achievement)

                # Award achievement points
                if achievement_def.points_reward > 0:
                    await self.award_points(
                        user_id=user_id,
                        points_amount=achievement_def.points_reward,
                        action_type="achievement_unlock",
                        source_event_id=trigger_context.get("source_event_id"),
                        metadata={
                            "achievement_id": achievement_def.id,
                            "achievement_name": achievement_def.name,
                            "achievement_tier": achievement_def.tier.value,
                        },
                    )

                # Update user achievement count
                user_gam = await self._get_or_create_user(user_id)
                user_gam.total_achievements += 1

                # Update tier counts
                if achievement_def.tier.value == "bronze":
                    user_gam.bronze_achievements += 1
                elif achievement_def.tier.value == "silver":
                    user_gam.silver_achievements += 1
                elif achievement_def.tier.value == "gold":
                    user_gam.gold_achievements += 1
                elif achievement_def.tier.value == "platinum":
                    user_gam.platinum_achievements += 1

                await self.repository.update_user_gamification(user_gam)

                # Publish AchievementUnlockedEvent
                achievement_event = AchievementUnlockedEvent(
                    user_id=user_id,
                    achievement_id=achievement_def.id,
                    achievement_name=achievement_def.name,
                    achievement_category=achievement_def.category.value,
                    achievement_tier=achievement_def.tier.value,
                    points_reward=achievement_def.points_reward,
                    badge_url=achievement_def.badge_url,
                    unlock_criteria=achievement_def.unlock_criteria,
                    source_service="gamification",
                )

                # Update event with additional data
                achievement_event.payload.update(
                    {
                        "is_first_unlock": user_gam.total_achievements == 1,
                        "user_achievement_count": user_gam.total_achievements,
                    }
                )

                await self.event_bus.publish(achievement_event)

                # Update achievement streak
                await self.update_streak(user_id, StreakType.ACHIEVEMENT_UNLOCK)

            return unlocked_achievements

        except Exception as e:
            self.logger.error(f"Error checking achievements for user {user_id}: {e}")
            return []

    async def unlock_achievement(
        self, user_id: int, achievement_id: str, source_event_id: Optional[str] = None
    ) -> UserAchievement:
        """Manually unlock an achievement for a user."""
        # Get achievement definition
        achievement_definitions = await self.repository.get_achievement_definitions()
        achievement_def = next(
            (ad for ad in achievement_definitions if ad.id == achievement_id), None
        )

        if not achievement_def:
            raise GamificationError(f"Achievement {achievement_id} not found")

        # Create unlock context
        unlock_context = {
            "manual_unlock": True,
            "unlock_timestamp": datetime.now(timezone.utc),
        }

        # Create user achievement record
        user_achievement_data = self.achievement_engine.create_user_achievement(
            user_id, achievement_def, unlock_context, source_event_id
        )

        # Save to database
        user_achievement = await self.repository.create_user_achievement(
            user_achievement_data
        )

        # Award points and publish event (similar to check_achievements)
        if achievement_def.points_reward > 0:
            await self.award_points(
                user_id=user_id,
                points_amount=achievement_def.points_reward,
                action_type="achievement_unlock",
                source_event_id=source_event_id,
                metadata={"achievement_id": achievement_id, "manual_unlock": True},
            )

        return user_achievement

    async def get_user_achievements(
        self, user_id: int, completed_only: bool = False
    ) -> List[UserAchievement]:
        """Get all achievements for a user."""
        return await self.repository.get_user_achievements(user_id, completed_only)

    async def get_achievement_progress(
        self, user_id: int, achievement_id: str
    ) -> Optional[UserAchievement]:
        """Get progress for a specific achievement."""
        achievements = await self.repository.get_user_achievements(user_id)
        return next(
            (ua for ua in achievements if ua.achievement_id == achievement_id), None
        )

    async def create_achievement_definition(
        self, achievement_data: Dict[str, Any]
    ) -> AchievementDefinition:
        """Create a new achievement definition."""
        # Validate achievement criteria
        self.achievement_engine.validate_achievement_criteria(
            achievement_data["unlock_criteria"]
        )

        return await self.repository.create_achievement_definition(achievement_data)

    # ================= Streak System =================

    async def update_streak(
        self,
        user_id: int,
        streak_type: StreakType,
        activity_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Update a user's streak for a specific activity type."""
        try:
            # Get existing streak
            user_streaks = await self.repository.get_user_streaks(user_id)
            existing_streak = next(
                (s for s in user_streaks if s.streak_type == streak_type), None
            )

            # Update streak using engine
            streak_data, milestone_reached = self.streak_engine.update_streak(
                user_id, streak_type, existing_streak, activity_date
            )

            # Save streak record
            streak_record = await self.repository.update_streak_record(streak_data)

            # Update user gamification record
            if streak_type == StreakType.DAILY_LOGIN:
                user_gam = await self._get_or_create_user(user_id)
                user_gam.current_daily_streak = streak_record.current_count
                user_gam.longest_daily_streak = streak_record.longest_count
                user_gam.last_activity_date = streak_record.last_activity_date
                await self.repository.update_user_gamification(user_gam)

            # Publish StreakUpdatedEvent
            streak_event = StreakUpdatedEvent(
                user_id=user_id,
                streak_type=streak_type.value,
                previous_count=existing_streak.current_count if existing_streak else 0,
                new_count=streak_record.current_count,
                is_broken=streak_record.current_count == 1
                and existing_streak
                and existing_streak.current_count > 1,
                streak_milestone=streak_record.current_count
                if milestone_reached
                else None,
                bonus_multiplier=streak_record.current_multiplier,
                source_service="gamification",
            )

            # Update event with additional data
            streak_event.payload.update(
                {
                    "days_since_last_activity": None,  # Could be calculated
                    "longest_streak_ever": streak_record.longest_count,
                }
            )

            await self.event_bus.publish(streak_event)

            return {
                "streak_type": streak_type.value,
                "current_count": streak_record.current_count,
                "longest_count": streak_record.longest_count,
                "is_milestone": milestone_reached,
                "multiplier": streak_record.current_multiplier,
            }

        except Exception as e:
            self.logger.error(f"Error updating streak for user {user_id}: {e}")
            raise GamificationError(f"Streak update failed: {e}")

    async def get_user_streaks(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active streaks for a user."""
        streaks = await self.repository.get_user_streaks(user_id)
        return [
            {
                "streak_type": s.streak_type.value,
                "current_count": s.current_count,
                "longest_count": s.longest_count,
                "last_activity_date": s.last_activity_date.isoformat()
                if s.last_activity_date
                else None,
                "current_multiplier": s.current_multiplier,
                "milestones_reached": s.milestones_reached or [],
                "is_active": s.is_active,
            }
            for s in streaks
        ]

    async def freeze_streak(self, user_id: int, streak_type: StreakType) -> bool:
        """Use a streak freeze for VIP users."""
        try:
            # Get user and streak
            user_gam = await self._get_or_create_user(user_id)
            user_streaks = await self.repository.get_user_streaks(user_id)
            streak_record = next(
                (s for s in user_streaks if s.streak_type == streak_type), None
            )

            if not streak_record:
                raise GamificationError(f"No active {streak_type.value} streak found")

            # Check if freeze is allowed
            can_freeze, reason = self.streak_engine.can_use_streak_freeze(
                user_gam, streak_record
            )
            if not can_freeze:
                raise GamificationError(f"Cannot freeze streak: {reason}")

            # Apply freeze
            freeze_data = self.streak_engine.apply_streak_freeze(streak_record)
            await self.repository.update_streak_record(freeze_data)

            self.logger.info(
                f"Applied streak freeze for user {user_id}, streak type {streak_type.value}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error freezing streak for user {user_id}: {e}")
            raise

    # ================= Leaderboard System =================

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
            # Get existing entries for this leaderboard
            existing_entries = await self.repository.get_leaderboard_entries(
                leaderboard_type, period_start, period_end, 1000
            )

            # Calculate user's ranking
            user_gam = await self._get_or_create_user(user_id)
            rank, ranking_context = self.leaderboard_engine.calculate_user_ranking(
                user_id,
                leaderboard_type,
                score,
                period_start,
                period_end,
                existing_entries,
            )

            # Create leaderboard entry data
            entry_data = self.leaderboard_engine.create_leaderboard_entry_data(
                user_id,
                leaderboard_type,
                period_start,
                period_end,
                rank,
                score,
                ranking_context,
                user_gam,
            )

            # Save entry
            entry = await self.repository.update_leaderboard_entry(entry_data)

            # Check if significant rank change occurred
            rank_change = ranking_context.get("rank_change")
            is_significant = rank_change and abs(rank_change) >= self.config.get(
                "leaderboard_settings", {}
            ).get("position_change_threshold", 5)

            if is_significant or entry.is_personal_best:
                # Publish LeaderboardChangedEvent
                leaderboard_event = LeaderboardChangedEvent(
                    user_id=user_id,
                    leaderboard_type=leaderboard_type.value,
                    previous_rank=ranking_context.get("previous_rank"),
                    new_rank=rank,
                    previous_score=ranking_context.get("previous_score"),
                    new_score=score,
                    rank_change_delta=rank_change,
                    is_new_personal_best=entry.is_personal_best,
                    source_service="gamification",
                )

                # Update event with additional data
                leaderboard_event.payload.update(
                    {
                        "total_participants": ranking_context.get("total_participants"),
                    }
                )

                await self.event_bus.publish(leaderboard_event)

            return {
                "leaderboard_type": leaderboard_type.value,
                "rank": rank,
                "score": score,
                "rank_change": rank_change,
                "is_personal_best": entry.is_personal_best,
                "total_participants": ranking_context.get("total_participants"),
            }

        except Exception as e:
            self.logger.error(f"Error updating leaderboard for user {user_id}: {e}")
            raise GamificationError(f"Leaderboard update failed: {e}")

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

        return self.leaderboard_engine.get_leaderboard_data(
            leaderboard_type, period_start, period_end, entries, user_id, limit
        )

    async def get_user_rank(
        self,
        user_id: int,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
    ) -> Optional[int]:
        """Get a user's rank on a specific leaderboard."""
        # Get all entries for the leaderboard
        entries = await self.repository.get_leaderboard_entries(
            leaderboard_type, period_start, period_end, 1000
        )

        # Find user's entry
        user_entry = next((e for e in entries if e.user_id == user_id), None)
        return user_entry.rank if user_entry else None

    # ================= User Management =================

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

        # Calculate new level
        new_level = self.points_engine.calculate_level_from_experience(
            user_gam.experience_points
        )
        level_increased = new_level > user_gam.current_level

        if level_increased:
            user_gam.current_level = new_level
            await self.repository.update_user_gamification(user_gam)

            # Check for level-based achievements
            await self._check_achievements_for_level(user_id, new_level)

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

    # ================= Analytics and Reporting =================

    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive gamification statistics for a user."""
        user_gam = await self.repository.get_user_gamification(user_id)
        if not user_gam:
            return {
                "total_points": 0,
                "current_level": 1,
                "experience_points": 0,
                "total_achievements": 0,
                "current_daily_streak": 0,
                "longest_daily_streak": 0,
                "vip_status": False,
                "stories_completed": 0,
                "decisions_made": 0,
                "level_reached": 1,
            }

        # Get additional stats from transactions and achievements
        achievement_count = await self.repository.get_achievement_completion_count(
            user_id
        )

        return {
            "total_points": user_gam.total_points,
            "current_level": user_gam.current_level,
            "experience_points": user_gam.experience_points,
            "total_achievements": achievement_count,
            "current_daily_streak": user_gam.current_daily_streak,
            "longest_daily_streak": user_gam.longest_daily_streak,
            "vip_status": user_gam.vip_status,
            "level_reached": user_gam.current_level,
            # These would need to be tracked from events or separate tables
            "stories_completed": 0,  # TODO: Implement story completion tracking
            "decisions_made": 0,  # TODO: Implement decision tracking
        }

    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide gamification statistics."""
        return await self.repository.get_system_statistics()

    # ================= Configuration and Settings =================

    async def get_points_configuration(self) -> Dict[str, Any]:
        """Get current points system configuration."""
        return self.config["points"]

    async def update_points_configuration(self, config: Dict[str, Any]) -> bool:
        """Update points system configuration."""
        self.config["points"].update(config)
        return True

    # ================= Helper Methods =================

    async def _get_or_create_user(self, user_id: int) -> UserGamification:
        """Get or create user gamification record."""
        user_gam = await self.repository.get_user_gamification(user_id)
        if not user_gam:
            user_gam = await self.repository.create_user_gamification(user_id)
        return user_gam

    async def _check_achievements_for_points(
        self, user_id: int, action_type: str, points_awarded: int, total_points: int
    ) -> None:
        """Check for achievements triggered by point awards."""
        trigger_context = {
            "action_type": action_type,
            "points_awarded": points_awarded,
            "total_points": total_points,
        }
        await self.check_achievements(user_id, trigger_context)

    async def _check_achievements_for_level(self, user_id: int, new_level: int) -> None:
        """Check for achievements triggered by level increases."""
        trigger_context = {
            "action_type": "level_up",
            "level_reached": new_level,
        }
        await self.check_achievements(user_id, trigger_context)
