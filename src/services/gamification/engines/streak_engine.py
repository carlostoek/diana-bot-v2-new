"""
Streak Engine for Diana Bot V2 Gamification System.

This module handles all streak-related calculations, tracking, and multiplier logic
with support for various streak types and VIP features like streak freezes.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ....models.gamification import StreakRecord, StreakType, UserGamification
from ..interfaces import GamificationError


class StreakEngine:
    """
    Core engine for streak system operations.

    Handles streak tracking, milestone detection, multiplier calculations,
    and VIP features like streak freezes with comprehensive validation.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Streak Engine.

        Args:
            config: Configuration dictionary with streak settings and milestones
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Streak configuration
        self.streak_multipliers = config.get(
            "streak_multipliers",
            {
                "1-7": 1.1,
                "8-14": 1.2,
                "15-30": 1.3,
                "31+": 1.5,
            },
        )

        self.streak_milestones = config.get(
            "streak_milestones",
            {
                StreakType.DAILY_LOGIN: [7, 30, 100, 365],
                StreakType.STORY_PROGRESS: [5, 15, 30, 60],
                StreakType.INTERACTION: [10, 25, 50, 100],
                StreakType.ACHIEVEMENT_UNLOCK: [3, 10, 20, 50],
            },
        )

    def update_streak(
        self,
        user_id: int,
        streak_type: StreakType,
        existing_streak: Optional[StreakRecord] = None,
        activity_date: Optional[datetime] = None,
        allow_backdate: bool = False,
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Update a user's streak for a specific activity type.

        Args:
            user_id: ID of the user
            streak_type: Type of streak to update
            existing_streak: Existing streak record (if any)
            activity_date: Date of the activity (defaults to now)
            allow_backdate: Whether to allow backdated activities

        Returns:
            Tuple of (streak_update_data, milestone_reached)

        Raises:
            ValueError: If activity_date is invalid
            GamificationError: If streak update fails
        """
        activity_date = activity_date or datetime.now(timezone.utc)
        now = datetime.now(timezone.utc)

        # Validate activity date
        if not allow_backdate and activity_date > now:
            raise ValueError("Activity date cannot be in the future")

        if activity_date < now - timedelta(days=7) and not allow_backdate:
            raise ValueError("Activity date is too old (>7 days)")

        # Calculate streak update
        if existing_streak:
            streak_data, milestone_reached = self._update_existing_streak(
                existing_streak, activity_date, now
            )
        else:
            streak_data, milestone_reached = self._create_new_streak(
                user_id, streak_type, activity_date, now
            )

        # Add metadata
        streak_data.update(
            {
                "updated_by": "streak_engine",
                "activity_date": activity_date,
                "processed_at": now,
            }
        )

        return streak_data, milestone_reached

    def calculate_streak_multiplier(
        self,
        streak_type: StreakType,
        current_count: int,
        user_gamification: Optional[UserGamification] = None,
    ) -> float:
        """
        Calculate the current multiplier for a streak.

        Args:
            streak_type: Type of streak
            current_count: Current streak count
            user_gamification: User's gamification data (for VIP status)

        Returns:
            Multiplier value for the streak
        """
        base_multiplier = self._get_base_multiplier(current_count)

        # Apply VIP bonus if applicable
        vip_bonus = 0.0
        if user_gamification and user_gamification.vip_status:
            vip_bonus = 0.1  # 10% additional bonus for VIP users

        # Apply streak type specific bonuses
        type_bonus = self._get_streak_type_bonus(streak_type, current_count)

        final_multiplier = base_multiplier + vip_bonus + type_bonus

        return round(final_multiplier, 2)

    def check_streak_milestones(
        self,
        streak_type: StreakType,
        old_count: int,
        new_count: int,
    ) -> List[int]:
        """
        Check if any milestones were reached with this streak update.

        Args:
            streak_type: Type of streak
            old_count: Previous streak count
            new_count: New streak count

        Returns:
            List of milestone values that were reached
        """
        milestones = self.streak_milestones.get(streak_type, [])
        reached_milestones = []

        for milestone in milestones:
            if old_count < milestone <= new_count:
                reached_milestones.append(milestone)

        return reached_milestones

    def can_use_streak_freeze(
        self,
        user_gamification: UserGamification,
        streak_record: StreakRecord,
    ) -> Tuple[bool, str]:
        """
        Check if a user can use a streak freeze.

        Args:
            user_gamification: User's gamification data
            streak_record: Streak record to freeze

        Returns:
            Tuple of (can_freeze, reason)
        """
        # Only VIP users can use streak freezes
        if not user_gamification.vip_status:
            return False, "Streak freezes are only available for VIP users"

        # Check if streak is active
        if not streak_record.is_active:
            return False, "Cannot freeze an inactive streak"

        # Check freeze usage limits (e.g., max 3 freezes per month)
        max_freezes_per_month = self.config.get("vip_features", {}).get(
            "max_freezes_per_month", 3
        )
        if streak_record.freeze_count >= max_freezes_per_month:
            return False, f"Maximum freezes per month reached ({max_freezes_per_month})"

        # Check minimum streak length for freeze eligibility
        min_streak_for_freeze = self.config.get("vip_features", {}).get(
            "min_streak_for_freeze", 7
        )
        if streak_record.current_count < min_streak_for_freeze:
            return (
                False,
                f"Streak must be at least {min_streak_for_freeze} days to use freeze",
            )

        return True, "Freeze available"

    def apply_streak_freeze(
        self,
        streak_record: StreakRecord,
        freeze_duration_days: int = 1,
    ) -> Dict[str, Any]:
        """
        Apply a streak freeze to protect the streak.

        Args:
            streak_record: Streak record to freeze
            freeze_duration_days: Number of days to freeze

        Returns:
            Updated streak data
        """
        now = datetime.now(timezone.utc)

        # Extend the grace period
        if streak_record.last_activity_date:
            # Extend the last activity date by freeze duration
            extended_date = streak_record.last_activity_date + timedelta(
                days=freeze_duration_days
            )
        else:
            extended_date = now

        return {
            "user_id": streak_record.user_id,
            "streak_type": streak_record.streak_type,
            "current_count": streak_record.current_count,
            "longest_count": streak_record.longest_count,
            "last_activity_date": extended_date,
            "streak_start_date": streak_record.streak_start_date,
            "last_reset_date": streak_record.last_reset_date,
            "current_multiplier": streak_record.current_multiplier,
            "milestones_reached": streak_record.milestones_reached,
            "is_active": True,
            "freeze_count": streak_record.freeze_count + 1,
        }

    def get_streak_statistics(
        self,
        user_streaks: List[StreakRecord],
        user_gamification: UserGamification,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive streak statistics for a user.

        Args:
            user_streaks: User's streak records
            user_gamification: User's gamification data

        Returns:
            Dictionary with streak statistics
        """
        active_streaks = [
            s for s in user_streaks if s.is_active and s.current_count > 0
        ]

        # Find longest current streak
        longest_current = max((s.current_count for s in active_streaks), default=0)

        # Find longest ever streak
        longest_ever = max((s.longest_count for s in user_streaks), default=0)

        # Calculate total streak days (sum of all longest streaks)
        total_streak_days = sum(s.longest_count for s in user_streaks)

        # Count milestones reached across all streaks
        total_milestones = 0
        for streak in user_streaks:
            if streak.milestones_reached:
                total_milestones += len(streak.milestones_reached)

        # Calculate streak health score (0-100)
        health_score = self._calculate_streak_health_score(active_streaks)

        # Get streak multiplier benefits
        total_multiplier_benefit = sum(
            self.calculate_streak_multiplier(
                s.streak_type, s.current_count, user_gamification
            )
            for s in active_streaks
        )

        return {
            "active_streaks_count": len(active_streaks),
            "longest_current_streak": longest_current,
            "longest_ever_streak": longest_ever,
            "total_streak_days": total_streak_days,
            "total_milestones_reached": total_milestones,
            "streak_health_score": health_score,
            "total_multiplier_benefit": round(total_multiplier_benefit, 2),
            "vip_freezes_available": user_gamification.vip_status,
            "streak_breakdown": [
                {
                    "type": s.streak_type.value,
                    "current_count": s.current_count,
                    "longest_count": s.longest_count,
                    "multiplier": self.calculate_streak_multiplier(
                        s.streak_type, s.current_count, user_gamification
                    ),
                    "milestones_reached": s.milestones_reached or [],
                    "next_milestone": self._get_next_milestone(
                        s.streak_type, s.current_count
                    ),
                }
                for s in user_streaks
                if s.is_active
            ],
        }

    def get_streak_recovery_suggestions(
        self,
        user_streaks: List[StreakRecord],
        user_gamification: UserGamification,
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions for recovering broken streaks.

        Args:
            user_streaks: User's streak records
            user_gamification: User's gamification data

        Returns:
            List of recovery suggestions
        """
        suggestions = []
        now = datetime.now(timezone.utc)

        for streak in user_streaks:
            if not streak.is_active or streak.current_count == 0:
                continue

            # Check if streak is at risk (no activity in grace period)
            grace_period = self._get_grace_period(streak.streak_type)
            time_since_activity = now - (streak.last_activity_date or now)

            if time_since_activity > grace_period:
                suggestion = {
                    "streak_type": streak.streak_type.value,
                    "current_count": streak.current_count,
                    "hours_overdue": int(time_since_activity.total_seconds() / 3600),
                    "risk_level": self._calculate_risk_level(
                        time_since_activity, grace_period
                    ),
                    "action_needed": self._get_action_for_streak_type(
                        streak.streak_type
                    ),
                    "can_use_freeze": user_gamification.vip_status
                    and self.can_use_streak_freeze(user_gamification, streak)[0],
                }
                suggestions.append(suggestion)

        # Sort by risk level and streak value
        suggestions.sort(
            key=lambda s: (s["risk_level"], -s["current_count"]), reverse=True
        )

        return suggestions

    def _update_existing_streak(
        self,
        existing_streak: StreakRecord,
        activity_date: datetime,
        now: datetime,
    ) -> Tuple[Dict[str, Any], bool]:
        """Update an existing streak record."""
        grace_period = self._get_grace_period(existing_streak.streak_type)
        last_activity = existing_streak.last_activity_date or now

        # Check if activity is within grace period
        time_since_last = activity_date - last_activity

        if time_since_last <= grace_period:
            # Continue streak
            new_count = existing_streak.current_count + 1
            milestone_reached = self._check_single_milestone_reached(
                existing_streak.streak_type, existing_streak.current_count, new_count
            )
        elif time_since_last <= grace_period * 2:  # Extended grace period
            # Maintain streak (no increment)
            new_count = existing_streak.current_count
            milestone_reached = False
        else:
            # Reset streak
            new_count = 1
            milestone_reached = False

        # Update longest count if necessary
        longest_count = max(existing_streak.longest_count, new_count)

        # Update milestones reached
        milestones_reached = list(existing_streak.milestones_reached or [])
        if milestone_reached:
            milestone_value = self._get_milestone_for_count(
                existing_streak.streak_type, new_count
            )
            if milestone_value and milestone_value not in milestones_reached:
                milestones_reached.append(milestone_value)

        # Calculate new multiplier
        new_multiplier = self._get_base_multiplier(new_count)

        streak_data = {
            "user_id": existing_streak.user_id,
            "streak_type": existing_streak.streak_type,
            "current_count": new_count,
            "longest_count": longest_count,
            "last_activity_date": activity_date,
            "streak_start_date": existing_streak.streak_start_date
            if new_count > 1
            else activity_date,
            "last_reset_date": now
            if new_count == 1 and existing_streak.current_count > 1
            else existing_streak.last_reset_date,
            "current_multiplier": new_multiplier,
            "milestones_reached": milestones_reached,
            "is_active": True,
            "freeze_count": existing_streak.freeze_count,
        }

        return streak_data, milestone_reached

    def _create_new_streak(
        self,
        user_id: int,
        streak_type: StreakType,
        activity_date: datetime,
        now: datetime,
    ) -> Tuple[Dict[str, Any], bool]:
        """Create a new streak record."""
        initial_multiplier = self._get_base_multiplier(1)

        streak_data = {
            "user_id": user_id,
            "streak_type": streak_type,
            "current_count": 1,
            "longest_count": 1,
            "last_activity_date": activity_date,
            "streak_start_date": activity_date,
            "last_reset_date": None,
            "current_multiplier": initial_multiplier,
            "milestones_reached": [],
            "is_active": True,
            "freeze_count": 0,
        }

        # Check if first milestone is reached (usually 1)
        milestone_reached = self._check_single_milestone_reached(streak_type, 0, 1)

        return streak_data, milestone_reached

    def _get_base_multiplier(self, streak_count: int) -> float:
        """Get base multiplier for a streak count."""
        if streak_count >= 31:
            return self.streak_multipliers.get("31+", 1.5)
        elif streak_count >= 15:
            return self.streak_multipliers.get("15-30", 1.3)
        elif streak_count >= 8:
            return self.streak_multipliers.get("8-14", 1.2)
        elif streak_count >= 1:
            return self.streak_multipliers.get("1-7", 1.1)
        else:
            return 1.0

    def _get_streak_type_bonus(self, streak_type: StreakType, count: int) -> float:
        """Get streak type specific bonus multiplier."""
        # Different streak types can have different bonus structures
        type_bonuses = {
            StreakType.DAILY_LOGIN: 0.05
            if count >= 30
            else 0.0,  # Extra bonus for long login streaks
            StreakType.STORY_PROGRESS: 0.1
            if count >= 10
            else 0.0,  # Higher bonus for story streaks
            StreakType.INTERACTION: 0.02 if count >= 20 else 0.0,
            StreakType.ACHIEVEMENT_UNLOCK: 0.15
            if count >= 5
            else 0.0,  # High bonus for achievement streaks
        }

        return type_bonuses.get(streak_type, 0.0)

    def _get_grace_period(self, streak_type: StreakType) -> timedelta:
        """Get grace period for a streak type."""
        grace_periods = {
            StreakType.DAILY_LOGIN: timedelta(hours=26),  # 26 hours for daily login
            StreakType.STORY_PROGRESS: timedelta(days=2),  # 2 days for story progress
            StreakType.INTERACTION: timedelta(hours=30),  # 30 hours for interactions
            StreakType.ACHIEVEMENT_UNLOCK: timedelta(days=7),  # 7 days for achievements
        }

        return grace_periods.get(streak_type, timedelta(days=1))

    def _check_single_milestone_reached(
        self,
        streak_type: StreakType,
        old_count: int,
        new_count: int,
    ) -> bool:
        """Check if a milestone was reached."""
        milestones = self.streak_milestones.get(streak_type, [])
        return any(old_count < milestone <= new_count for milestone in milestones)

    def _get_milestone_for_count(
        self, streak_type: StreakType, count: int
    ) -> Optional[int]:
        """Get the milestone value for a specific count."""
        milestones = self.streak_milestones.get(streak_type, [])
        return next((m for m in milestones if m == count), None)

    def _get_next_milestone(
        self, streak_type: StreakType, current_count: int
    ) -> Optional[int]:
        """Get the next milestone for a streak type."""
        milestones = self.streak_milestones.get(streak_type, [])
        return next((m for m in milestones if m > current_count), None)

    def _calculate_streak_health_score(self, active_streaks: List[StreakRecord]) -> int:
        """Calculate a health score (0-100) for user's streaks."""
        if not active_streaks:
            return 0

        score = 0
        max_score = len(active_streaks) * 100

        for streak in active_streaks:
            # Base score for having an active streak
            streak_score = 20

            # Bonus for streak length
            if streak.current_count >= 30:
                streak_score += 40
            elif streak.current_count >= 7:
                streak_score += 20
            elif streak.current_count >= 3:
                streak_score += 10

            # Bonus for milestones reached
            if streak.milestones_reached:
                streak_score += min(30, len(streak.milestones_reached) * 10)

            # Bonus for high multiplier
            if streak.current_multiplier >= 1.5:
                streak_score += 10
            elif streak.current_multiplier >= 1.3:
                streak_score += 5

            score += min(100, streak_score)

        return min(100, int((score / max_score) * 100))

    def _calculate_risk_level(
        self, time_overdue: timedelta, grace_period: timedelta
    ) -> int:
        """Calculate risk level (1-5) for a streak based on overdue time."""
        overdue_ratio = time_overdue.total_seconds() / grace_period.total_seconds()

        if overdue_ratio <= 1.0:
            return 1  # Low risk
        elif overdue_ratio <= 2.0:
            return 2  # Medium-low risk
        elif overdue_ratio <= 4.0:
            return 3  # Medium risk
        elif overdue_ratio <= 8.0:
            return 4  # High risk
        else:
            return 5  # Critical risk

    def _get_action_for_streak_type(self, streak_type: StreakType) -> str:
        """Get the action needed to maintain a streak type."""
        actions = {
            StreakType.DAILY_LOGIN: "Log in to maintain your daily streak",
            StreakType.STORY_PROGRESS: "Complete a story chapter to continue your progress streak",
            StreakType.INTERACTION: "Make a story decision or interact with content",
            StreakType.ACHIEVEMENT_UNLOCK: "Unlock an achievement to continue your streak",
        }

        return actions.get(streak_type, "Perform relevant activity to maintain streak")
