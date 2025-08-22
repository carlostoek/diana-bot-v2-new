"""
Achievement Engine for Gamification System

This module handles achievement condition evaluation, unlocking mechanics,
and reward distribution with support for multi-level achievements. It provides
real-time achievement tracking and seamless integration with the points system.

Key Features:
- Real-time achievement condition evaluation
- Multi-level achievement support (Bronze, Silver, Gold)
- Progress tracking for incremental achievements
- Automatic reward distribution
- Event-driven achievement unlocking
- Secret achievement support
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.interfaces import IEvent

from ..interfaces import (
    AchievementCategory,
    AchievementUnlockResult,
    IAchievementEngine,
)
from ..models import (
    DEFAULT_ACHIEVEMENTS,
    Achievement,
    UserAchievement,
    UserGamification,
)

# Configure logging
logger = logging.getLogger(__name__)


class AchievementEngineError(Exception):
    """Exception raised by the AchievementEngine for operation failures."""

    pass


class AchievementEngine(IAchievementEngine):
    """
    Achievement management and progression tracking engine.

    Handles all aspects of achievement processing including condition evaluation,
    unlocking mechanics, progress tracking, and reward distribution.
    """

    def __init__(
        self,
        points_engine=None,  # Will be injected by GamificationService
        database_client=None,  # In production, this would be the actual DB client
    ):
        """
        Initialize the AchievementEngine.

        Args:
            points_engine: Points engine for reward distribution
            database_client: Database client for persistence
        """
        self.points_engine = points_engine
        self.database_client = database_client

        # Load achievements (in production, from database)
        self.achievements: Dict[str, Achievement] = {}
        self.user_achievements: Dict[int, Dict[str, UserAchievement]] = {}

        # Achievement progress tracking
        self.achievement_progress: Dict[int, Dict[str, Dict[str, Any]]] = {}

        # Load default achievements
        for achievement in DEFAULT_ACHIEVEMENTS:
            self.achievements[achievement.id] = achievement

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def check_achievements(
        self,
        user_id: int,
        trigger_event: IEvent,
    ) -> List[AchievementUnlockResult]:
        """
        Check if user's action triggers any achievement unlocks.

        Evaluates all relevant achievements based on the trigger event
        and returns any achievements that should be unlocked.
        """
        async with self._lock:
            try:
                unlocked_achievements = []

                # Get user statistics for achievement evaluation
                user_stats = await self._get_user_stats(user_id, trigger_event)

                # Check each active achievement
                for achievement_id, achievement in self.achievements.items():
                    if not achievement.is_active:
                        continue

                    # Skip if user already has max level of this achievement
                    current_user_achievement = self._get_user_achievement(
                        user_id, achievement_id
                    )
                    if (
                        current_user_achievement
                        and current_user_achievement.level >= achievement.max_level
                    ):
                        continue

                    # Check if this achievement is relevant to the trigger event
                    if not self._is_achievement_relevant(achievement, trigger_event):
                        continue

                    # Evaluate achievement conditions for each level
                    level_results = achievement.check_conditions(user_stats)

                    # Find the highest level that can be unlocked
                    for level in range(achievement.max_level, 0, -1):
                        if level_results.get(level, False):
                            # Check if user already has this level
                            current_level = (
                                current_user_achievement.level
                                if current_user_achievement
                                else 0
                            )
                            if level > current_level:
                                # Unlock this achievement level
                                unlock_result = await self._unlock_achievement_level(
                                    user_id, achievement, level
                                )
                                if unlock_result.success:
                                    unlocked_achievements.append(unlock_result)
                                break  # Only unlock one level at a time

                return unlocked_achievements

            except Exception as e:
                logger.error(f"Error checking achievements for user {user_id}: {e}")
                return []

    async def unlock_achievement(
        self,
        user_id: int,
        achievement_id: str,
        level: int = 1,
    ) -> AchievementUnlockResult:
        """
        Manually unlock an achievement for a user.

        Used for admin actions or special achievement unlocks.
        """
        async with self._lock:
            try:
                achievement = self.achievements.get(achievement_id)
                if not achievement:
                    return AchievementUnlockResult(
                        success=False,
                        user_id=user_id,
                        achievement_id=achievement_id,
                        achievement_name="Unknown",
                        level=level,
                        points_reward=0,
                        error_message=f"Achievement {achievement_id} not found",
                    )

                if level < 1 or level > achievement.max_level:
                    return AchievementUnlockResult(
                        success=False,
                        user_id=user_id,
                        achievement_id=achievement_id,
                        achievement_name=achievement.name,
                        level=level,
                        points_reward=0,
                        error_message=f"Invalid level {level} for achievement {achievement_id}",
                    )

                return await self._unlock_achievement_level(user_id, achievement, level)

            except Exception as e:
                logger.error(
                    f"Error manually unlocking achievement {achievement_id} for user {user_id}: {e}"
                )
                return AchievementUnlockResult(
                    success=False,
                    user_id=user_id,
                    achievement_id=achievement_id,
                    achievement_name="Unknown",
                    level=level,
                    points_reward=0,
                    error_message=str(e),
                )

    async def get_user_achievements(
        self,
        user_id: int,
        category: Optional[AchievementCategory] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all achievements unlocked by a user.
        """
        async with self._lock:
            user_achievements = []

            for achievement_id, user_achievement in self.user_achievements.get(
                user_id, {}
            ).items():
                achievement = self.achievements.get(achievement_id)
                if not achievement:
                    continue

                # Apply category filter if specified
                if category and achievement.category != category:
                    continue

                achievement_data = {
                    "id": achievement_id,
                    "name": achievement.name,
                    "description": achievement.description,
                    "category": achievement.category.value,
                    "level": user_achievement.level,
                    "max_level": achievement.max_level,
                    "unlocked_at": user_achievement.unlocked_at.isoformat(),
                    "points_awarded": user_achievement.points_awarded,
                    "special_rewards": user_achievement.special_rewards,
                    "icon_url": achievement.icon_url,
                }

                user_achievements.append(achievement_data)

            # Sort by unlock date (newest first)
            user_achievements.sort(key=lambda x: x["unlocked_at"], reverse=True)
            return user_achievements

    async def get_achievement_progress(
        self,
        user_id: int,
        achievement_id: str,
    ) -> Dict[str, Any]:
        """
        Get user's progress toward a specific achievement.
        """
        async with self._lock:
            achievement = self.achievements.get(achievement_id)
            if not achievement:
                return {"error": f"Achievement {achievement_id} not found"}

            # Get current user achievement (if any)
            user_achievement = self._get_user_achievement(user_id, achievement_id)
            current_level = user_achievement.level if user_achievement else 0

            # If user has max level, they're done
            if current_level >= achievement.max_level:
                return {
                    "achievement_id": achievement_id,
                    "name": achievement.name,
                    "current_level": current_level,
                    "max_level": achievement.max_level,
                    "completed": True,
                    "progress_percentage": 100.0,
                }

            # Calculate progress toward next level
            next_level = current_level + 1
            user_stats = await self._get_user_stats(user_id, None)

            # Get conditions for next level
            level_key = f"level_{next_level}"
            conditions = achievement.conditions.get(level_key, achievement.conditions)

            progress_details = {}
            total_progress = 0.0
            condition_count = 0

            for condition_key, required_value in conditions.items():
                user_value = user_stats.get(condition_key, 0)

                if isinstance(required_value, dict):
                    target_value = required_value.get("value", 0)
                else:
                    target_value = required_value

                progress_percentage = (
                    min(100.0, (user_value / target_value) * 100.0)
                    if target_value > 0
                    else 100.0
                )

                progress_details[condition_key] = {
                    "current": user_value,
                    "required": target_value,
                    "progress_percentage": progress_percentage,
                }

                total_progress += progress_percentage
                condition_count += 1

            average_progress = (
                total_progress / condition_count if condition_count > 0 else 0.0
            )

            return {
                "achievement_id": achievement_id,
                "name": achievement.name,
                "description": achievement.description,
                "category": achievement.category.value,
                "current_level": current_level,
                "next_level": next_level,
                "max_level": achievement.max_level,
                "completed": False,
                "progress_percentage": average_progress,
                "progress_details": progress_details,
                "is_secret": achievement.is_secret,
            }

    async def get_available_achievements(
        self,
        category: Optional[AchievementCategory] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all available achievements in the system.
        """
        async with self._lock:
            available_achievements = []

            for achievement in self.achievements.values():
                if not achievement.is_active:
                    continue

                # Apply category filter if specified
                if category and achievement.category != category:
                    continue

                # Don't include secret achievements unless they've been unlocked
                if achievement.is_secret:
                    continue

                achievement_data = {
                    "id": achievement.id,
                    "name": achievement.name,
                    "description": achievement.description,
                    "category": achievement.category.value,
                    "max_level": achievement.max_level,
                    "icon_url": achievement.icon_url,
                    "conditions": achievement.conditions,
                    "rewards": achievement.rewards,
                }

                available_achievements.append(achievement_data)

            # Sort by category and name
            available_achievements.sort(key=lambda x: (x["category"], x["name"]))
            return available_achievements

    # Private helper methods

    def _get_user_achievement(
        self, user_id: int, achievement_id: str
    ) -> Optional[UserAchievement]:
        """Get user's current achievement record."""
        return self.user_achievements.get(user_id, {}).get(achievement_id)

    async def _get_user_stats(
        self, user_id: int, trigger_event: Optional[IEvent]
    ) -> Dict[str, Any]:
        """
        Get comprehensive user statistics for achievement evaluation.

        This would integrate with the points engine and other systems
        to get current user statistics.
        """
        # In production, this would query various systems for user stats
        # For now, returning basic stats with mock data

        stats = {
            "total_points": 0,
            "total_interactions": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "chapters_completed": 0,
            "trivia_correct": 0,
            "community_interactions": 0,
            "achievements_unlocked": len(self.user_achievements.get(user_id, {})),
            "level": 1,
            "days_active": 1,
            "friend_referrals": 0,
            "story_decisions": 0,
        }

        # If we have a points engine, get real stats
        if self.points_engine:
            try:
                # This would be implemented to get real user stats
                # from the points engine and other systems
                pass
            except Exception as e:
                logger.warning(f"Could not get user stats from points engine: {e}")

        # Update stats based on trigger event if provided
        if trigger_event:
            self._update_stats_from_event(stats, trigger_event)

        return stats

    def _update_stats_from_event(self, stats: Dict[str, Any], event: IEvent) -> None:
        """Update stats based on a trigger event."""
        event_data = event.data

        if event.type.startswith("game."):
            if "trivia" in event.type and event_data.get("correct_answer"):
                stats["trivia_correct"] += 1
            stats["total_interactions"] += 1

        elif event.type.startswith("narrative."):
            if "chapter_completed" in event.type:
                stats["chapters_completed"] += 1
            elif "decision_made" in event.type:
                stats["story_decisions"] += 1

        elif event.type.startswith("user."):
            if "registered" in event.type:
                stats["total_interactions"] = 1
            else:
                stats["total_interactions"] += 1

    def _is_achievement_relevant(
        self, achievement: Achievement, trigger_event: IEvent
    ) -> bool:
        """
        Check if an achievement is relevant to the trigger event.

        This optimization prevents checking every achievement for every event.
        """
        if not trigger_event:
            return True  # Manual checks should evaluate all achievements

        event_type = trigger_event.type

        # Map event types to relevant achievement categories
        relevance_map = {
            "game.": [AchievementCategory.PROGRESS, AchievementCategory.ENGAGEMENT],
            "narrative.": [AchievementCategory.NARRATIVE, AchievementCategory.PROGRESS],
            "user.": [AchievementCategory.PROGRESS, AchievementCategory.SOCIAL],
            "admin.": [
                AchievementCategory.PROGRESS
            ],  # Admin adjustments can affect any achievement
        }

        # Check if achievement category is relevant to event type
        for event_prefix, relevant_categories in relevance_map.items():
            if event_type.startswith(event_prefix):
                return achievement.category in relevant_categories

        return True  # Default to checking if unsure

    async def _unlock_achievement_level(
        self,
        user_id: int,
        achievement: Achievement,
        level: int,
    ) -> AchievementUnlockResult:
        """
        Unlock a specific level of an achievement for a user.
        """
        try:
            # Get or create user achievement record
            if user_id not in self.user_achievements:
                self.user_achievements[user_id] = {}

            current_achievement = self.user_achievements[user_id].get(achievement.id)

            if current_achievement and current_achievement.level >= level:
                return AchievementUnlockResult(
                    success=False,
                    user_id=user_id,
                    achievement_id=achievement.id,
                    achievement_name=achievement.name,
                    level=level,
                    points_reward=0,
                    error_message=f"User already has level {current_achievement.level} of this achievement",
                )

            # Calculate rewards for this level
            rewards = achievement.get_rewards_for_level(level)
            points_reward = rewards.get("points", 0)
            special_rewards = {k: v for k, v in rewards.items() if k != "points"}

            # Create or update user achievement record
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                level=level,
                points_awarded=points_reward,
                special_rewards=special_rewards,
            )

            # Store the achievement
            self.user_achievements[user_id][achievement.id] = user_achievement

            # Award points if any (through points engine)
            if points_reward > 0 and self.points_engine:
                from ..interfaces import ActionType

                try:
                    await self.points_engine.award_points(
                        user_id=user_id,
                        action_type=ActionType.ACHIEVEMENT_UNLOCKED,
                        context={
                            "achievement_id": achievement.id,
                            "achievement_name": achievement.name,
                            "level": level,
                            "achievement_points": points_reward,
                        },
                        force_award=True,  # Achievements bypass anti-abuse
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to award points for achievement {achievement.id}: {e}"
                    )

            # Persist to database
            await self._persist_user_achievement(user_achievement)

            # Log achievement unlock
            logger.info(
                f"Achievement unlocked: user={user_id}, achievement={achievement.id}, "
                f"level={level}, points={points_reward}"
            )

            return AchievementUnlockResult(
                success=True,
                user_id=user_id,
                achievement_id=achievement.id,
                achievement_name=achievement.name,
                level=level,
                points_reward=points_reward,
                special_rewards=special_rewards,
            )

        except Exception as e:
            logger.error(
                f"Error unlocking achievement {achievement.id} for user {user_id}: {e}"
            )
            return AchievementUnlockResult(
                success=False,
                user_id=user_id,
                achievement_id=achievement.id,
                achievement_name=achievement.name,
                level=level,
                points_reward=0,
                error_message=str(e),
            )

    async def _persist_user_achievement(
        self, user_achievement: UserAchievement
    ) -> None:
        """Persist user achievement to storage."""
        # In production, this would be a database insert/update
        if self.database_client:
            # await self.database_client.upsert_user_achievement(user_achievement)
            pass

    async def add_achievement(self, achievement: Achievement) -> bool:
        """
        Add a new achievement to the system.

        Used for dynamic achievement creation.
        """
        async with self._lock:
            try:
                self.achievements[achievement.id] = achievement

                # Persist to database
                if self.database_client:
                    # await self.database_client.insert_achievement(achievement)
                    pass

                logger.info(
                    f"Added new achievement: {achievement.id} - {achievement.name}"
                )
                return True

            except Exception as e:
                logger.error(f"Error adding achievement {achievement.id}: {e}")
                return False

    async def deactivate_achievement(self, achievement_id: str) -> bool:
        """
        Deactivate an achievement (stop checking it).
        """
        async with self._lock:
            achievement = self.achievements.get(achievement_id)
            if achievement:
                achievement.is_active = False
                logger.info(f"Deactivated achievement: {achievement_id}")
                return True
            return False
