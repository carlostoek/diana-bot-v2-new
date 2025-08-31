"""
Achievement Engine for Gamification System
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.core.interfaces import IEvent
from ..interfaces import (
    AchievementCategory,
    AchievementUnlockResult,
    IAchievementEngine,
    IGamificationRepository,
    IPointsEngine,
    ActionType,
)
from ..models import Achievement, UserAchievement

# Configure logging
logger = logging.getLogger(__name__)


class AchievementEngineError(Exception):
    """Exception raised by the AchievementEngine for operation failures."""
    pass


class AchievementEngine(IAchievementEngine):
    def __init__(
        self,
        repository: IGamificationRepository,
        points_engine: IPointsEngine,
    ):
        self.repository = repository
        self.points_engine = points_engine
        self.achievements: Dict[str, Achievement] = {
            ach.id: ach for ach in self.repository.get_achievements()
        }
        self._lock = asyncio.Lock()

    async def _get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Gets a user's gamification stats from the repository.
        """
        stats = self.repository.get_user_gamification_stats(user_id)
        if not stats:
            return {"total_points": 0, "current_streak": 0, "level": 1} # Default stats

        return {
            "total_points": stats.total_points,
            "current_streak": stats.current_streak,
            "level": stats.level,
        }

    async def check_achievements(
        self,
        user_id: int,
        trigger_event: IEvent,
    ) -> List[AchievementUnlockResult]:
        async with self._lock:
            unlocked_achievements = []
            user_stats = await self._get_user_stats(user_id)
            user_unlocked = {ua.achievement_id: ua for ua in self.repository.get_user_achievements(user_id)}

            for ach_id, ach in self.achievements.items():
                if ach_id in user_unlocked and user_unlocked[ach_id].level >= ach.max_level:
                    continue

                # Simplified condition check
                if "total_points" in ach.conditions:
                    if user_stats.get("total_points", 0) >= ach.conditions["total_points"]:
                        # Check if this level is new
                        current_level = user_unlocked.get(ach_id).level if ach_id in user_unlocked else 0
                        if 1 > current_level:
                             unlock_result = await self.unlock_achievement(user_id, ach_id, 1)
                             unlocked_achievements.append(unlock_result)

            return unlocked_achievements

    async def unlock_achievement(
        self,
        user_id: int,
        achievement_id: str,
        level: int = 1,
    ) -> AchievementUnlockResult:
        async with self._lock:
            achievement = self.achievements.get(achievement_id)
            if not achievement:
                return AchievementUnlockResult(
                    success=False, user_id=user_id, achievement_id=achievement_id,
                    achievement_name="Unknown", level=level, points_reward=0,
                    error_message=f"Achievement {achievement_id} not found"
                )

            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement_id,
                level=level,
            )
            self.repository.grant_user_achievement(user_achievement)

            rewards = achievement.rewards or {}
            points_reward = rewards.get("points", 0)

            if points_reward > 0:
                await self.points_engine.award_points(
                    user_id=user_id,
                    action_type=ActionType.ACHIEVEMENT_UNLOCKED,
                    context={"achievement_id": achievement_id},
                    base_points=points_reward,
                    force_award=True,
                )

            return AchievementUnlockResult(
                success=True, user_id=user_id, achievement_id=achievement_id,
                achievement_name=achievement.name, level=level,
                points_reward=points_reward
            )

    async def get_user_achievements(
        self,
        user_id: int,
        category: Optional[AchievementCategory] = None,
    ) -> List[Dict[str, Any]]:
        user_achievements = self.repository.get_user_achievements(user_id)
        result = []
        for ua in user_achievements:
            ach = self.achievements.get(ua.achievement_id)
            if ach:
                if category and ach.category != category.value:
                    continue
                result.append({
                    "id": ach.id,
                    "name": ach.name,
                    "level": ua.level,
                    "unlocked_at": ua.unlocked_at.isoformat(),
                })
        return result

    async def get_achievement_progress(
        self,
        user_id: int,
        achievement_id: str,
    ) -> Dict[str, Any]:
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            raise AchievementEngineError(f"Achievement {achievement_id} not found")

        user_achievements = {ua.achievement_id: ua for ua in self.repository.get_user_achievements(user_id)}
        user_achievement = user_achievements.get(achievement_id)
        current_level = user_achievement.level if user_achievement else 0

        if current_level >= achievement.max_level:
            return {"completed": True, "progress": 100}

        next_level = current_level + 1
        user_stats = await self._get_user_stats(user_id)

        conditions = achievement.conditions.get(f"level_{next_level}", achievement.conditions)

        progress = 0
        if "total_points" in conditions:
            required = conditions["total_points"]
            current = user_stats.get("total_points", 0)
            progress = min(100, (current / required) * 100) if required > 0 else 100

        return {"completed": False, "progress": progress, "current_level": current_level, "next_level": next_level}


    async def get_available_achievements(
        self,
        category: Optional[AchievementCategory] = None,
    ) -> List[Dict[str, Any]]:
        achievements = self.repository.get_achievements()
        result = []
        for ach in achievements:
            if category and ach.category != category.value:
                continue
            result.append({
                "id": ach.id,
                "name": ach.name,
                "description": ach.description,
            })
        return result
