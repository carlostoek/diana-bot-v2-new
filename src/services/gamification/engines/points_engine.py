"""
Points Engine for Diana Bot V2 Gamification System.

This module handles all points-related calculations, anti-abuse logic,
multipliers, and transaction processing with comprehensive validation.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ....core.events.gamification import PointsAwardedEvent, PointsDeductedEvent
from ....models.gamification import PointsTransactionType, UserGamification
from ..interfaces import AntiAbuseError, GamificationError, InsufficientPointsError


class PointsEngine:
    """
    Core engine for points system operations.

    Handles point calculations, multipliers, anti-abuse checks, and transaction logic
    with comprehensive validation and error handling.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Points Engine.

        Args:
            config: Configuration dictionary with points settings and anti-abuse rules
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Anti-abuse tracking
        self._recent_actions: Dict[int, List[datetime]] = {}
        self._suspicious_users: set = set()
        self._hourly_points: Dict[int, Dict[str, int]] = {}  # user_id -> {hour: points}

    def calculate_points_award(
        self,
        user_gamification: UserGamification,
        base_points: int,
        action_type: str,
        multiplier: float = 1.0,
        bonus_points: int = 0,
        streak_multiplier: float = 1.0,
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate the final points to award with all multipliers and bonuses.

        Args:
            user_gamification: User's gamification data
            base_points: Base points for the action
            action_type: Type of action earning points
            multiplier: Base multiplier to apply
            bonus_points: Fixed bonus points to add
            streak_multiplier: Additional streak-based multiplier

        Returns:
            Tuple of (final_points, calculation_details)

        Raises:
            ValueError: If base_points is invalid
            AntiAbuseError: If action violates anti-abuse rules
        """
        if base_points <= 0:
            raise ValueError("Base points must be positive")

        calculation_details = {
            "base_points": base_points,
            "base_multiplier": multiplier,
            "bonus_points": bonus_points,
            "streak_multiplier": streak_multiplier,
            "vip_multiplier": 1.0,
            "level_bonus": 0,
            "final_multiplier": multiplier,
        }

        # Apply VIP multiplier
        if user_gamification.vip_status:
            vip_multiplier = user_gamification.vip_multiplier
            calculation_details["vip_multiplier"] = vip_multiplier
            multiplier *= vip_multiplier

        # Apply streak multiplier
        multiplier *= streak_multiplier

        # Apply level-based bonus (small bonus for higher levels)
        level_bonus = min(
            user_gamification.current_level * 2, 50
        )  # Max 50 bonus points
        calculation_details["level_bonus"] = level_bonus

        # Calculate final points
        calculated_points = int(base_points * multiplier)
        final_points = calculated_points + bonus_points + level_bonus
        calculation_details["final_multiplier"] = multiplier
        calculation_details["calculated_points"] = calculated_points
        calculation_details["total_bonus"] = bonus_points + level_bonus
        calculation_details["final_points"] = final_points

        return final_points, calculation_details

    def validate_points_transaction(
        self,
        user_id: int,
        points_amount: int,
        action_type: str,
        transaction_type: PointsTransactionType,
    ) -> None:
        """
        Validate a points transaction against anti-abuse rules.

        Args:
            user_id: ID of the user
            points_amount: Amount of points in transaction
            action_type: Type of action
            transaction_type: Type of transaction

        Raises:
            AntiAbuseError: If transaction violates anti-abuse rules
        """
        now = datetime.now(timezone.utc)

        # Skip validation for admin adjustments and penalties
        if transaction_type in [
            PointsTransactionType.ADMIN_ADJUSTMENT,
            PointsTransactionType.PENALTY,
        ]:
            return

        # Track recent actions for rate limiting
        self._track_user_action(user_id, now)

        # Check action rate limits
        self._check_action_rate_limits(user_id, now)

        # Check points per hour limits
        self._check_hourly_points_limits(user_id, points_amount, now)

        # Check for suspicious patterns
        self._check_suspicious_patterns(user_id, points_amount, action_type, now)

    def validate_points_deduction(
        self,
        user_gamification: UserGamification,
        points_amount: int,
        allow_negative: bool = False,
    ) -> None:
        """
        Validate that a points deduction is allowed.

        Args:
            user_gamification: User's gamification data
            points_amount: Amount to deduct
            allow_negative: Whether to allow negative balances

        Raises:
            InsufficientPointsError: If user doesn't have enough points
            ValueError: If points_amount is invalid
        """
        if points_amount <= 0:
            raise ValueError("Points amount must be positive")

        if not allow_negative and user_gamification.total_points < points_amount:
            raise InsufficientPointsError(
                f"User {user_gamification.user_id} has {user_gamification.total_points} points, "
                f"cannot deduct {points_amount}"
            )

    def create_transaction_data(
        self,
        user_id: int,
        transaction_type: PointsTransactionType,
        amount: int,
        points_before: int,
        points_after: int,
        action_type: str,
        description: str,
        calculation_details: Optional[Dict[str, Any]] = None,
        source_event_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a complete transaction data dictionary.

        Args:
            user_id: ID of the user
            transaction_type: Type of transaction
            amount: Points amount (positive for gains, negative for losses)
            points_before: Points before transaction
            points_after: Points after transaction
            action_type: Type of action that caused the transaction
            description: Human-readable description
            calculation_details: Details of how points were calculated
            source_event_id: ID of the triggering event
            correlation_id: Correlation ID for tracking
            metadata: Additional metadata

        Returns:
            Complete transaction data dictionary
        """
        transaction_metadata = metadata or {}

        # Add calculation details to metadata
        if calculation_details:
            transaction_metadata["calculation"] = calculation_details

        # Add anti-abuse tracking info
        transaction_metadata.update(
            {
                "is_suspicious": user_id in self._suspicious_users,
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return {
            "user_id": user_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "points_before": points_before,
            "points_after": points_after,
            "action_type": action_type,
            "description": description,
            "source_service": "gamification",
            "source_event_id": source_event_id,
            "correlation_id": correlation_id,
            "multiplier_applied": calculation_details.get("final_multiplier", 1.0)
            if calculation_details
            else 1.0,
            "bonus_applied": calculation_details.get("total_bonus", 0)
            if calculation_details
            else 0,
            "is_suspicious": user_id in self._suspicious_users,
            "transaction_metadata": transaction_metadata,
        }

    def get_points_for_action(self, action_type: str) -> int:
        """
        Get the base points reward for a specific action type.

        Args:
            action_type: Type of action

        Returns:
            Base points for the action, or 0 if not configured
        """
        return self.config.get("points", {}).get(action_type, 0)

    def calculate_level_from_experience(self, experience_points: int) -> int:
        """
        Calculate user level based on experience points.

        Args:
            experience_points: Total experience points

        Returns:
            User level (1-based)
        """
        level_progression = self.config.get("level_progression", [0])

        for level, required_xp in enumerate(level_progression, 1):
            if experience_points < required_xp:
                return max(1, level - 1)

        # If user has more XP than the highest level, return max level
        return len(level_progression)

    def get_experience_for_next_level(self, current_level: int) -> Optional[int]:
        """
        Get experience points required for the next level.

        Args:
            current_level: Current user level

        Returns:
            Experience points needed for next level, or None if at max level
        """
        level_progression = self.config.get("level_progression", [0])

        if current_level >= len(level_progression):
            return None  # At max level

        return level_progression[current_level]  # Next level's requirement

    def _track_user_action(self, user_id: int, timestamp: datetime) -> None:
        """Track a user action for rate limiting."""
        if user_id not in self._recent_actions:
            self._recent_actions[user_id] = []

        # Clean old actions (older than 1 hour)
        cutoff = timestamp - timedelta(hours=1)
        self._recent_actions[user_id] = [
            action_time
            for action_time in self._recent_actions[user_id]
            if action_time > cutoff
        ]

        # Add current action
        self._recent_actions[user_id].append(timestamp)

    def _check_action_rate_limits(self, user_id: int, now: datetime) -> None:
        """Check if user is within action rate limits."""
        if user_id not in self._recent_actions:
            return

        # Check actions per minute
        minute_cutoff = now - timedelta(minutes=1)
        recent_minute_actions = [
            action_time
            for action_time in self._recent_actions[user_id]
            if action_time > minute_cutoff
        ]

        max_actions_per_minute = self.config.get("anti_abuse", {}).get(
            "max_actions_per_minute", 10
        )
        if len(recent_minute_actions) >= max_actions_per_minute:
            self._suspicious_users.add(user_id)
            raise AntiAbuseError(
                f"User {user_id} exceeded action rate limit: "
                f"{len(recent_minute_actions)} actions in the last minute"
            )

    def _check_hourly_points_limits(
        self, user_id: int, points_amount: int, now: datetime
    ) -> None:
        """Check if user is within hourly points limits."""
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        if user_id not in self._hourly_points:
            self._hourly_points[user_id] = {}

        # Clean old hour data
        cutoff_hour = current_hour - timedelta(hours=24)  # Keep 24 hours of data
        self._hourly_points[user_id] = {
            hour: points
            for hour, points in self._hourly_points[user_id].items()
            if hour > cutoff_hour
        }

        # Add current points to this hour
        current_hour_str = current_hour.isoformat()
        current_hour_points = self._hourly_points[user_id].get(current_hour_str, 0)
        new_hour_points = current_hour_points + points_amount

        max_points_per_hour = self.config.get("anti_abuse", {}).get(
            "max_points_per_hour", 1000
        )
        if new_hour_points > max_points_per_hour:
            self._suspicious_users.add(user_id)
            raise AntiAbuseError(
                f"User {user_id} exceeded hourly points limit: "
                f"{new_hour_points} points in current hour (limit: {max_points_per_hour})"
            )

        # Update hourly tracking
        self._hourly_points[user_id][current_hour_str] = new_hour_points

    def _check_suspicious_patterns(
        self,
        user_id: int,
        points_amount: int,
        action_type: str,
        now: datetime,
    ) -> None:
        """Check for suspicious patterns in user behavior."""
        # Check for unusually high single point awards
        suspicious_threshold = self.config.get("anti_abuse", {}).get(
            "suspicious_threshold", 5000
        )
        if points_amount > suspicious_threshold:
            self.logger.warning(
                f"Suspicious high point award: User {user_id}, {points_amount} points for {action_type}"
            )
            self._suspicious_users.add(user_id)

        # Check for rapid repeated actions
        if user_id in self._recent_actions:
            recent_actions = self._recent_actions[user_id]
            if len(recent_actions) >= 5:  # If 5+ actions in the tracking window
                # Check if all recent actions are within a very short timeframe
                latest_actions = recent_actions[-5:]
                if latest_actions[-1] - latest_actions[0] < timedelta(seconds=30):
                    self.logger.warning(
                        f"Suspicious rapid actions: User {user_id}, 5 actions in <30 seconds"
                    )
                    self._suspicious_users.add(user_id)

    def get_anti_abuse_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get anti-abuse status for a user.

        Args:
            user_id: ID of the user

        Returns:
            Dictionary with anti-abuse status information
        """
        now = datetime.now(timezone.utc)
        recent_actions = self._recent_actions.get(user_id, [])

        # Count actions in various time windows
        minute_actions = sum(
            1 for action in recent_actions if now - action < timedelta(minutes=1)
        )
        hour_actions = sum(
            1 for action in recent_actions if now - action < timedelta(hours=1)
        )

        # Get hourly points for current hour
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        current_hour_str = current_hour.isoformat()
        hourly_points = self._hourly_points.get(user_id, {}).get(current_hour_str, 0)

        return {
            "is_suspicious": user_id in self._suspicious_users,
            "actions_last_minute": minute_actions,
            "actions_last_hour": hour_actions,
            "points_current_hour": hourly_points,
            "total_tracked_actions": len(recent_actions),
            "tracking_window_hours": 1,
        }

    def reset_anti_abuse_tracking(self, user_id: int) -> None:
        """
        Reset anti-abuse tracking for a user (admin function).

        Args:
            user_id: ID of the user
        """
        self._recent_actions.pop(user_id, None)
        self._hourly_points.pop(user_id, None)
        self._suspicious_users.discard(user_id)

        self.logger.info(f"Reset anti-abuse tracking for user {user_id}")
