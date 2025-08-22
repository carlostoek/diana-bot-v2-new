"""
Gamification Service Data Models

This module defines the data models for the Diana Bot V2 gamification system.
These models represent the database schema and provide validation, serialization,
and business logic for points, achievements, and user statistics.

All models follow the exact database schema requirements from the Datos document
and ensure perfect data integrity with comprehensive validation.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .interfaces import AchievementCategory, ActionType, MultiplierType


@dataclass
class UserGamification:
    """
    Core user gamification data model.

    Represents the user_gamification table with all points, streaks,
    and multiplier information. Ensures balance integrity and provides
    validation for all gamification operations.
    """

    user_id: int
    total_points: int = 0
    available_points: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    level: int = 1
    experience_points: int = 0
    last_activity: Optional[datetime] = None
    last_streak_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Multiplier tracking
    vip_multiplier: float = 1.0
    streak_multiplier: float = 1.0
    event_multiplier: float = 1.0

    # Anti-abuse tracking
    daily_action_counts: Dict[str, int] = field(default_factory=dict)
    last_daily_reset: Optional[datetime] = None

    # Privacy settings
    show_in_leaderboards: bool = True

    def __post_init__(self):
        """Validate data after initialization."""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")

        if self.total_points < 0:
            raise ValueError("total_points cannot be negative")

        if self.available_points < 0:
            raise ValueError("available_points cannot be negative")

        if self.available_points > self.total_points:
            raise ValueError("available_points cannot exceed total_points")

        if self.current_streak < 0:
            raise ValueError("current_streak cannot be negative")

        if self.longest_streak < 0:
            raise ValueError("longest_streak cannot be negative")

        if self.level < 1:
            raise ValueError("level must be at least 1")

        # Auto-set timestamps
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    def add_points(self, amount: int, update_available: bool = True) -> None:
        """
        Add points to user's balance with validation.

        Args:
            amount: Points to add (must be positive)
            update_available: Whether to also update available points
        """
        if amount <= 0:
            raise ValueError("Points amount must be positive")

        self.total_points += amount
        if update_available:
            self.available_points += amount
        self.updated_at = datetime.now(timezone.utc)

    def spend_points(self, amount: int) -> bool:
        """
        Spend points from available balance.

        Args:
            amount: Points to spend (must be positive)

        Returns:
            True if successful, False if insufficient balance
        """
        if amount <= 0:
            raise ValueError("Spend amount must be positive")

        if self.available_points < amount:
            return False

        self.available_points -= amount
        self.updated_at = datetime.now(timezone.utc)
        return True

    def update_streak(self, is_active_today: bool) -> bool:
        """
        Update user's daily streak.

        Args:
            is_active_today: Whether user was active today

        Returns:
            True if streak increased, False if broken
        """
        today = datetime.now(timezone.utc).date()

        if self.last_streak_date is None:
            # First time tracking streak
            if is_active_today:
                self.current_streak = 1
                self.last_streak_date = datetime.combine(
                    today, datetime.min.time(), timezone.utc
                )
                if self.current_streak > self.longest_streak:
                    self.longest_streak = self.current_streak
                self.updated_at = datetime.now(timezone.utc)
                return True
            return False

        last_date = self.last_streak_date.date()

        if last_date == today:
            # Already counted for today
            return self.current_streak > 0
        elif last_date == today - datetime.timedelta(days=1):
            # Consecutive day
            if is_active_today:
                self.current_streak += 1
                self.last_streak_date = datetime.combine(
                    today, datetime.min.time(), timezone.utc
                )
                if self.current_streak > self.longest_streak:
                    self.longest_streak = self.current_streak
                self.updated_at = datetime.now(timezone.utc)
                return True
            else:
                # Streak broken
                self.current_streak = 0
                self.updated_at = datetime.now(timezone.utc)
                return False
        else:
            # Streak broken (gap > 1 day)
            if is_active_today:
                self.current_streak = 1
                self.last_streak_date = datetime.combine(
                    today, datetime.min.time(), timezone.utc
                )
                self.updated_at = datetime.now(timezone.utc)
                return True
            else:
                self.current_streak = 0
                self.updated_at = datetime.now(timezone.utc)
                return False

    def calculate_level(self) -> int:
        """
        Calculate user level based on total points.

        Level formula: level = floor(sqrt(total_points / 1000)) + 1
        This gives smooth progression:
        - Level 1: 0-999 points
        - Level 2: 1000-3999 points
        - Level 3: 4000-8999 points
        - etc.
        """
        import math

        return int(math.sqrt(self.total_points / 1000)) + 1

    def update_level(self) -> bool:
        """
        Update user level based on current points.

        Returns:
            True if level increased, False if unchanged
        """
        new_level = self.calculate_level()
        if new_level > self.level:
            self.level = new_level
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def get_active_multipliers(self) -> Dict[MultiplierType, float]:
        """Get all currently active point multipliers."""
        multipliers = {}

        if self.vip_multiplier > 1.0:
            multipliers[MultiplierType.VIP_BONUS] = self.vip_multiplier

        if self.streak_multiplier > 1.0:
            multipliers[MultiplierType.STREAK_BONUS] = self.streak_multiplier

        if self.event_multiplier > 1.0:
            multipliers[MultiplierType.EVENT_BONUS] = self.event_multiplier

        if self.level > 1:
            level_bonus = 1.0 + (self.level - 1) * 0.05  # 5% per level
            multipliers[MultiplierType.LEVEL_BONUS] = level_bonus

        return multipliers

    def reset_daily_counts(self) -> None:
        """Reset daily action counts for a new day."""
        self.daily_action_counts = {}
        self.last_daily_reset = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "total_points": self.total_points,
            "available_points": self.available_points,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "level": self.level,
            "experience_points": self.experience_points,
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "last_streak_date": (
                self.last_streak_date.isoformat() if self.last_streak_date else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "vip_multiplier": self.vip_multiplier,
            "streak_multiplier": self.streak_multiplier,
            "event_multiplier": self.event_multiplier,
            "daily_action_counts": self.daily_action_counts,
            "last_daily_reset": (
                self.last_daily_reset.isoformat() if self.last_daily_reset else None
            ),
            "show_in_leaderboards": self.show_in_leaderboards,
        }


@dataclass
class PointsTransaction:
    """
    Individual points transaction record.

    Represents the points_transactions table with complete audit trail
    for every point change in the system. Critical for balance integrity
    and anti-abuse detection.
    """

    id: Optional[str] = None
    user_id: int = 0
    action_type: ActionType = ActionType.LOGIN
    points_change: int = 0
    balance_after: int = 0
    base_points: int = 0
    multipliers_applied: Dict[MultiplierType, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    # Anti-abuse tracking
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    validation_passed: bool = True

    def __post_init__(self):
        """Validate transaction data."""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")

        if self.balance_after < 0:
            raise ValueError("balance_after cannot be negative")

        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

        if self.id is None:
            import uuid

            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action_type": self.action_type.value,
            "points_change": self.points_change,
            "balance_after": self.balance_after,
            "base_points": self.base_points,
            "multipliers_applied": {
                k.value: v for k, v in self.multipliers_applied.items()
            },
            "context": self.context,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "validation_passed": self.validation_passed,
        }


@dataclass
class Achievement:
    """
    Achievement definition model.

    Represents the achievements table with all achievement metadata,
    requirements, and reward information.
    """

    id: str
    name: str
    description: str
    category: AchievementCategory
    conditions: Dict[str, Any]
    rewards: Dict[str, Any]
    icon_url: Optional[str] = None
    is_secret: bool = False
    is_active: bool = True
    max_level: int = 1
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate achievement data."""
        if not self.id:
            raise ValueError("Achievement ID cannot be empty")

        if not self.name:
            raise ValueError("Achievement name cannot be empty")

        if not self.description:
            raise ValueError("Achievement description cannot be empty")

        if not self.conditions:
            raise ValueError("Achievement must have conditions")

        if not self.rewards:
            raise ValueError("Achievement must have rewards")

        if self.max_level < 1:
            raise ValueError("max_level must be at least 1")

        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def check_conditions(self, user_stats: Dict[str, Any]) -> Dict[int, bool]:
        """
        Check if user meets conditions for each achievement level.

        Args:
            user_stats: User statistics to check against

        Returns:
            Dictionary mapping level -> whether conditions are met
        """
        results = {}

        for level in range(1, self.max_level + 1):
            level_key = f"level_{level}"
            if level_key in self.conditions:
                level_conditions = self.conditions[level_key]
                results[level] = self._evaluate_conditions(level_conditions, user_stats)
            else:
                # No specific level conditions, use base conditions
                results[level] = self._evaluate_conditions(self.conditions, user_stats)

        return results

    def _evaluate_conditions(
        self, conditions: Dict[str, Any], user_stats: Dict[str, Any]
    ) -> bool:
        """Evaluate if conditions are met given user stats."""
        for condition_key, required_value in conditions.items():
            user_value = user_stats.get(condition_key, 0)

            if isinstance(required_value, dict):
                # Complex condition with operator
                operator = required_value.get("op", ">=")
                value = required_value.get("value", 0)

                if operator == ">=":
                    if user_value < value:
                        return False
                elif operator == "<=":
                    if user_value > value:
                        return False
                elif operator == "==":
                    if user_value != value:
                        return False
                elif operator == ">":
                    if user_value <= value:
                        return False
                elif operator == "<":
                    if user_value >= value:
                        return False
                else:
                    raise ValueError(f"Unknown operator: {operator}")
            else:
                # Simple >= comparison
                if user_value < required_value:
                    return False

        return True

    def get_rewards_for_level(self, level: int) -> Dict[str, Any]:
        """Get rewards for a specific achievement level."""
        level_key = f"level_{level}"
        if level_key in self.rewards:
            return self.rewards[level_key]
        return self.rewards.get("base", {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "conditions": self.conditions,
            "rewards": self.rewards,
            "icon_url": self.icon_url,
            "is_secret": self.is_secret,
            "is_active": self.is_active,
            "max_level": self.max_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class UserAchievement:
    """
    User's unlocked achievement record.

    Represents the user_achievements table tracking which achievements
    each user has unlocked and at what level.
    """

    user_id: int
    achievement_id: str
    level: int = 1
    unlocked_at: Optional[datetime] = None
    points_awarded: int = 0
    special_rewards: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate user achievement data."""
        if self.user_id <= 0:
            raise ValueError("user_id must be positive")

        if not self.achievement_id:
            raise ValueError("achievement_id cannot be empty")

        if self.level < 1:
            raise ValueError("level must be at least 1")

        if self.points_awarded < 0:
            raise ValueError("points_awarded cannot be negative")

        if self.unlocked_at is None:
            self.unlocked_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "achievement_id": self.achievement_id,
            "level": self.level,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
            "points_awarded": self.points_awarded,
            "special_rewards": self.special_rewards,
        }


# Pre-defined achievements for the Diana Bot V2 system
DEFAULT_ACHIEVEMENTS = [
    Achievement(
        id="first_steps",
        name="Primeros Pasos",
        description="Realiza tu primera interacción con Diana",
        category=AchievementCategory.PROGRESS,
        conditions={"total_interactions": 1},
        rewards={"base": {"points": 100, "title": "Recién Llegado"}},
        max_level=3,
    ),
    Achievement(
        id="faithful_visitor",
        name="Visitante Fiel",
        description="Mantén una racha de días consecutivos",
        category=AchievementCategory.ENGAGEMENT,
        conditions={
            "level_1": {"current_streak": 7},
            "level_2": {"current_streak": 30},
            "level_3": {"current_streak": 100},
        },
        rewards={
            "level_1": {"points": 500, "title": "Fiel"},
            "level_2": {"points": 2000, "title": "Muy Fiel"},
            "level_3": {"points": 10000, "title": "Ultra Fiel"},
        },
        max_level=3,
    ),
    Achievement(
        id="point_collector",
        name="Coleccionista de Besitos",
        description="Acumula una gran cantidad de Besitos",
        category=AchievementCategory.PROGRESS,
        conditions={
            "level_1": {"total_points": 1000},
            "level_2": {"total_points": 10000},
            "level_3": {"total_points": 100000},
        },
        rewards={
            "level_1": {"points": 200, "title": "Ahorrador"},
            "level_2": {"points": 1000, "title": "Rico"},
            "level_3": {"points": 5000, "title": "Millonario del Corazón"},
        },
        max_level=3,
    ),
    Achievement(
        id="story_reader",
        name="Lector Ávido",
        description="Completa capítulos de la historia principal",
        category=AchievementCategory.NARRATIVE,
        conditions={
            "level_1": {"chapters_completed": 5},
            "level_2": {"chapters_completed": 15},
            "level_3": {"chapters_completed": 30},
        },
        rewards={
            "level_1": {"points": 300, "title": "Lector"},
            "level_2": {"points": 1500, "title": "Bookworm"},
            "level_3": {"points": 5000, "title": "Maestro Narrador"},
        },
        max_level=3,
    ),
    Achievement(
        id="social_butterfly",
        name="Mariposa Social",
        description="Interactúa activamente con la comunidad",
        category=AchievementCategory.SOCIAL,
        conditions={
            "level_1": {"community_interactions": 10},
            "level_2": {"community_interactions": 50},
            "level_3": {"community_interactions": 200},
        },
        rewards={
            "level_1": {"points": 250, "title": "Sociable"},
            "level_2": {"points": 1200, "title": "Popular"},
            "level_3": {"points": 4000, "title": "Influencer"},
        },
        max_level=3,
    ),
]
