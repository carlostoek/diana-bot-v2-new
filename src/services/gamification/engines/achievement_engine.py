"""
Achievement Engine for Diana Bot V2 Gamification System.

This module handles achievement criteria evaluation, unlocking logic,
progress tracking, and achievement-related calculations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from ....models.gamification import (
    AchievementCategory,
    AchievementDefinition,
    AchievementTier,
    UserAchievement,
    UserGamification,
)
from ..interfaces import AchievementNotFoundError, GamificationError


class AchievementEngine:
    """
    Core engine for achievement system operations.

    Handles achievement criteria evaluation, progress tracking, and unlocking logic
    with comprehensive validation and flexible criteria system.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Achievement Engine.

        Args:
            config: Configuration dictionary with achievement settings and milestones
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Cache for achievement definitions to improve performance
        self._achievement_cache: Dict[str, AchievementDefinition] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes

    def evaluate_achievements(
        self,
        user_stats: Dict[str, Any],
        achievement_definitions: List[AchievementDefinition],
        user_achievements: List[UserAchievement],
        trigger_context: Dict[str, Any],
    ) -> List[Tuple[AchievementDefinition, Dict[str, Any]]]:
        """
        Evaluate which achievements a user can unlock based on current stats.

        Args:
            user_stats: User's current statistics
            achievement_definitions: Available achievement definitions
            user_achievements: User's current achievement progress
            trigger_context: Context about what triggered the evaluation

        Returns:
            List of tuples: (achievement_definition, unlock_context)
        """
        unlockable_achievements = []

        # Get completed achievement IDs for quick lookup
        completed_achievement_ids = {
            ua.achievement_id for ua in user_achievements if ua.is_completed
        }

        # Get in-progress achievements for progress tracking
        in_progress_achievements = {
            ua.achievement_id: ua for ua in user_achievements if not ua.is_completed
        }

        for achievement_def in achievement_definitions:
            # Skip if already completed and not repeatable
            if (
                achievement_def.id in completed_achievement_ids
                and not achievement_def.is_repeatable
            ):
                continue

            # Skip if not active
            if not achievement_def.is_active:
                continue

            # Evaluate criteria
            criteria_result = self._evaluate_criteria(
                achievement_def.unlock_criteria, user_stats, trigger_context
            )

            if criteria_result["is_unlocked"]:
                unlock_context = {
                    "criteria_met": criteria_result["criteria_met"],
                    "trigger_action": trigger_context.get("action_type"),
                    "unlock_timestamp": datetime.now(timezone.utc),
                    "is_repeat_unlock": achievement_def.id in completed_achievement_ids,
                }

                unlockable_achievements.append((achievement_def, unlock_context))
            elif criteria_result["has_progress"]:
                # Update progress for multi-step achievements
                progress_data = criteria_result["progress_data"]
                if achievement_def.id in in_progress_achievements:
                    # Update existing progress
                    user_achievement = in_progress_achievements[achievement_def.id]
                    self._update_achievement_progress(user_achievement, progress_data)

        return unlockable_achievements

    def create_user_achievement(
        self,
        user_id: int,
        achievement_definition: AchievementDefinition,
        unlock_context: Dict[str, Any],
        source_event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create user achievement data for unlocking.

        Args:
            user_id: ID of the user
            achievement_definition: Achievement being unlocked
            unlock_context: Context about the unlock
            source_event_id: ID of the triggering event

        Returns:
            User achievement data dictionary
        """
        now = datetime.now(timezone.utc)

        return {
            "user_id": user_id,
            "achievement_id": achievement_definition.id,
            "progress_current": unlock_context.get("progress_current", 1),
            "progress_required": unlock_context.get("progress_required", 1),
            "is_completed": True,
            "unlocked_at": now,
            "points_awarded": achievement_definition.points_reward,
            "unlock_event_id": source_event_id,
        }

    def calculate_achievement_statistics(
        self,
        user_achievements: List[UserAchievement],
        achievement_definitions: List[AchievementDefinition],
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive achievement statistics for a user.

        Args:
            user_achievements: User's achievement records
            achievement_definitions: All available achievements

        Returns:
            Dictionary with achievement statistics
        """
        completed_achievements = [ua for ua in user_achievements if ua.is_completed]
        in_progress_achievements = [
            ua for ua in user_achievements if not ua.is_completed
        ]

        # Count by tier
        tier_counts = {tier.value: 0 for tier in AchievementTier}
        for ua in completed_achievements:
            achievement_def = self._get_achievement_definition(
                ua.achievement_id, achievement_definitions
            )
            if achievement_def:
                tier_counts[achievement_def.tier.value] += 1

        # Count by category
        category_counts = {category.value: 0 for category in AchievementCategory}
        for ua in completed_achievements:
            achievement_def = self._get_achievement_definition(
                ua.achievement_id, achievement_definitions
            )
            if achievement_def:
                category_counts[achievement_def.category.value] += 1

        # Calculate completion percentage
        total_available = len([ad for ad in achievement_definitions if ad.is_active])
        completion_percentage = (
            len(completed_achievements) / max(1, total_available)
        ) * 100

        # Calculate total points from achievements
        total_points_from_achievements = sum(
            ua.points_awarded for ua in completed_achievements
        )

        # Find rarest achievements (highest tier)
        rarest_achievements = []
        for tier in [
            AchievementTier.PLATINUM,
            AchievementTier.GOLD,
            AchievementTier.SILVER,
        ]:
            tier_achievements = [
                ua
                for ua in completed_achievements
                if self._get_achievement_definition(
                    ua.achievement_id, achievement_definitions
                )
                and self._get_achievement_definition(
                    ua.achievement_id, achievement_definitions
                ).tier
                == tier
            ]
            if tier_achievements:
                rarest_achievements = tier_achievements
                break

        return {
            "total_completed": len(completed_achievements),
            "total_in_progress": len(in_progress_achievements),
            "total_available": total_available,
            "completion_percentage": round(completion_percentage, 2),
            "tier_counts": tier_counts,
            "category_counts": category_counts,
            "total_points_earned": total_points_from_achievements,
            "rarest_tier_unlocked": rarest_achievements[0].achievement_id
            if rarest_achievements
            else None,
            "recent_unlocks": sorted(
                completed_achievements,
                key=lambda ua: ua.unlocked_at
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )[
                :5
            ],  # Last 5 unlocks
        }

    def get_achievement_recommendations(
        self,
        user_stats: Dict[str, Any],
        achievement_definitions: List[AchievementDefinition],
        user_achievements: List[UserAchievement],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get achievement recommendations for a user based on their progress.

        Args:
            user_stats: User's current statistics
            achievement_definitions: Available achievement definitions
            user_achievements: User's current achievement progress
            limit: Maximum number of recommendations

        Returns:
            List of achievement recommendations with progress information
        """
        completed_achievement_ids = {
            ua.achievement_id for ua in user_achievements if ua.is_completed
        }

        recommendations = []

        for achievement_def in achievement_definitions:
            # Skip completed, inactive, or secret achievements
            if (
                achievement_def.id in completed_achievement_ids
                or not achievement_def.is_active
                or achievement_def.is_secret
            ):
                continue

            # Calculate progress towards this achievement
            progress_info = self._calculate_achievement_progress(
                achievement_def.unlock_criteria, user_stats
            )

            if progress_info["progress_percentage"] > 0:
                recommendation = {
                    "achievement_id": achievement_def.id,
                    "name": achievement_def.name,
                    "description": achievement_def.description,
                    "tier": achievement_def.tier.value,
                    "category": achievement_def.category.value,
                    "points_reward": achievement_def.points_reward,
                    "progress_percentage": progress_info["progress_percentage"],
                    "criteria_status": progress_info["criteria_status"],
                    "next_milestone": progress_info["next_milestone"],
                    "badge_url": achievement_def.badge_url,
                }
                recommendations.append(recommendation)

        # Sort by progress percentage (descending) and points reward (descending)
        recommendations.sort(
            key=lambda r: (r["progress_percentage"], r["points_reward"]), reverse=True
        )

        return recommendations[:limit]

    def validate_achievement_criteria(self, criteria: Dict[str, Any]) -> bool:
        """
        Validate achievement criteria format and content.

        Args:
            criteria: Achievement criteria dictionary

        Returns:
            True if criteria are valid

        Raises:
            ValueError: If criteria format is invalid
        """
        if not isinstance(criteria, dict):
            raise ValueError("Achievement criteria must be a dictionary")

        if not criteria:
            raise ValueError("Achievement criteria cannot be empty")

        # Validate known criteria types
        valid_criteria_types = {
            "total_points",
            "stories_completed",
            "chapters_completed",
            "decisions_made",
            "daily_streak",
            "achievements_unlocked",
            "level_reached",
            "days_active",
            "consecutive_logins",
        }

        for criterion, value in criteria.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Criterion '{criterion}' must have a numeric value")

            if value <= 0:
                raise ValueError(f"Criterion '{criterion}' must have a positive value")

            if criterion not in valid_criteria_types:
                self.logger.warning(f"Unknown achievement criterion: {criterion}")

        return True

    def _evaluate_criteria(
        self,
        criteria: Dict[str, Any],
        user_stats: Dict[str, Any],
        trigger_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate achievement criteria against user stats.

        Args:
            criteria: Achievement unlock criteria
            user_stats: User's current statistics
            trigger_context: Context about the trigger

        Returns:
            Dictionary with evaluation results
        """
        criteria_met = {}
        all_criteria_satisfied = True
        has_progress = False

        for criterion, required_value in criteria.items():
            current_value = user_stats.get(criterion, 0)
            is_met = current_value >= required_value

            criteria_met[criterion] = {
                "required": required_value,
                "current": current_value,
                "is_met": is_met,
                "progress_percentage": min(100, (current_value / required_value) * 100),
            }

            if not is_met:
                all_criteria_satisfied = False

            if current_value > 0:
                has_progress = True

        return {
            "is_unlocked": all_criteria_satisfied,
            "has_progress": has_progress,
            "criteria_met": criteria_met,
            "progress_data": criteria_met,
        }

    def _calculate_achievement_progress(
        self,
        criteria: Dict[str, Any],
        user_stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate progress towards an achievement.

        Args:
            criteria: Achievement criteria
            user_stats: User's current statistics

        Returns:
            Progress information dictionary
        """
        criteria_status = {}
        total_progress = 0
        criteria_count = len(criteria)
        next_milestone = None

        for criterion, required_value in criteria.items():
            current_value = user_stats.get(criterion, 0)
            progress_percentage = min(100, (current_value / required_value) * 100)

            criteria_status[criterion] = {
                "current": current_value,
                "required": required_value,
                "progress_percentage": progress_percentage,
                "remaining": max(0, required_value - current_value),
            }

            total_progress += progress_percentage

            # Find the closest milestone (criterion that's not yet met)
            if current_value < required_value:
                if (
                    next_milestone is None
                    or required_value - current_value < next_milestone["remaining"]
                ):
                    next_milestone = {
                        "criterion": criterion,
                        "remaining": required_value - current_value,
                        "current": current_value,
                        "required": required_value,
                    }

        overall_progress = total_progress / max(1, criteria_count)

        return {
            "progress_percentage": round(overall_progress, 2),
            "criteria_status": criteria_status,
            "next_milestone": next_milestone,
        }

    def _update_achievement_progress(
        self,
        user_achievement: UserAchievement,
        progress_data: Dict[str, Any],
    ) -> None:
        """
        Update progress for a multi-step achievement.

        Args:
            user_achievement: User achievement record to update
            progress_data: New progress data
        """
        # For now, this is a placeholder for more complex progress tracking
        # In a full implementation, this would handle multi-step achievements
        # where progress_current and progress_required are meaningful
        pass

    def _get_achievement_definition(
        self,
        achievement_id: str,
        achievement_definitions: List[AchievementDefinition],
    ) -> Optional[AchievementDefinition]:
        """
        Get achievement definition by ID.

        Args:
            achievement_id: ID of the achievement
            achievement_definitions: List of achievement definitions

        Returns:
            Achievement definition or None if not found
        """
        return next(
            (ad for ad in achievement_definitions if ad.id == achievement_id), None
        )

    def get_default_achievements(self) -> List[Dict[str, Any]]:
        """
        Get default achievement definitions for system initialization.

        Returns:
            List of default achievement data dictionaries
        """
        return [
            # Narrative Achievements
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
                "display_order": 10,
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
                "display_order": 11,
            },
            {
                "id": "twenty_stories_complete",
                "name": "Master Storyteller",
                "description": "Complete 20 different stories",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.GOLD,
                "points_reward": 2500,
                "unlock_criteria": {"stories_completed": 20},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 12,
            },
            {
                "id": "fifty_stories_complete",
                "name": "Literary Legend",
                "description": "Complete 50 different stories",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.PLATINUM,
                "points_reward": 5000,
                "unlock_criteria": {"stories_completed": 50},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 13,
            },
            # Engagement Achievements
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
                "display_order": 20,
            },
            {
                "id": "thirty_day_streak",
                "name": "Monthly Master",
                "description": "Maintain a 30-day activity streak",
                "category": AchievementCategory.ENGAGEMENT,
                "tier": AchievementTier.SILVER,
                "points_reward": 1500,
                "unlock_criteria": {"daily_streak": 30},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 21,
            },
            {
                "id": "hundred_day_streak",
                "name": "Century Champion",
                "description": "Maintain a 100-day activity streak",
                "category": AchievementCategory.ENGAGEMENT,
                "tier": AchievementTier.GOLD,
                "points_reward": 5000,
                "unlock_criteria": {"daily_streak": 100},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 22,
            },
            # Milestone Achievements
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
                "display_order": 30,
            },
            {
                "id": "points_collector_10k",
                "name": "Points Master",
                "description": "Accumulate 10,000 total points",
                "category": AchievementCategory.MILESTONE,
                "tier": AchievementTier.SILVER,
                "points_reward": 500,
                "unlock_criteria": {"total_points": 10000},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 31,
            },
            {
                "id": "points_collector_50k",
                "name": "Points Legend",
                "description": "Accumulate 50,000 total points",
                "category": AchievementCategory.MILESTONE,
                "tier": AchievementTier.GOLD,
                "points_reward": 2500,
                "unlock_criteria": {"total_points": 50000},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 32,
            },
            {
                "id": "points_collector_100k",
                "name": "Points Deity",
                "description": "Accumulate 100,000 total points",
                "category": AchievementCategory.MILESTONE,
                "tier": AchievementTier.PLATINUM,
                "points_reward": 10000,
                "unlock_criteria": {"total_points": 100000},
                "is_secret": True,
                "is_repeatable": False,
                "display_order": 33,
            },
            # Decision Making Achievements
            {
                "id": "decision_maker_50",
                "name": "Decision Maker",
                "description": "Make 50 story decisions",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.BRONZE,
                "points_reward": 300,
                "unlock_criteria": {"decisions_made": 50},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 40,
            },
            {
                "id": "decision_maker_200",
                "name": "Choice Champion",
                "description": "Make 200 story decisions",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.SILVER,
                "points_reward": 750,
                "unlock_criteria": {"decisions_made": 200},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 41,
            },
            {
                "id": "decision_maker_500",
                "name": "Master of Choices",
                "description": "Make 500 story decisions",
                "category": AchievementCategory.NARRATIVE,
                "tier": AchievementTier.GOLD,
                "points_reward": 2000,
                "unlock_criteria": {"decisions_made": 500},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 42,
            },
            # Level Achievements
            {
                "id": "level_10",
                "name": "Rising Star",
                "description": "Reach level 10",
                "category": AchievementCategory.MILESTONE,
                "tier": AchievementTier.BRONZE,
                "points_reward": 400,
                "unlock_criteria": {"level_reached": 10},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 50,
            },
            {
                "id": "level_25",
                "name": "Veteran Player",
                "description": "Reach level 25",
                "category": AchievementCategory.MILESTONE,
                "tier": AchievementTier.SILVER,
                "points_reward": 1000,
                "unlock_criteria": {"level_reached": 25},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 51,
            },
            {
                "id": "level_50",
                "name": "Elite Master",
                "description": "Reach level 50",
                "category": AchievementCategory.MILESTONE,
                "tier": AchievementTier.GOLD,
                "points_reward": 2500,
                "unlock_criteria": {"level_reached": 50},
                "is_secret": False,
                "is_repeatable": False,
                "display_order": 52,
            },
        ]
