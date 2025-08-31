"""
Gamification Service Interfaces

This module defines the abstract interfaces for the Diana Bot V2 gamification system.
These interfaces establish contracts for points management, achievements, leaderboards,
and anti-abuse mechanisms while ensuring bulletproof transaction integrity.

Key Features:
- Type-safe interfaces with full validation
- Atomic transaction guarantees
- Anti-abuse and rate limiting contracts
- Event Bus integration patterns
- Performance requirements enforcement
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.interfaces import IEvent


class ActionType(Enum):
    """Valid actions that can award points in the gamification system."""

    # Daily activities
    DAILY_LOGIN = "daily_login"
    LOGIN = "login"

    # Content interaction
    MESSAGE_SENT = "message_sent"
    TRIVIA_COMPLETED = "trivia_completed"
    STORY_CHAPTER_COMPLETED = "story_chapter_completed"
    STORY_DECISION_MADE = "story_decision_made"

    # Social activities
    FRIEND_REFERRAL = "friend_referral"
    COMMUNITY_PARTICIPATION = "community_participation"

    # Monetization
    VIP_PURCHASE = "vip_purchase"
    SUBSCRIPTION_RENEWAL = "subscription_renewal"

    # Special events
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    STREAK_BONUS = "streak_bonus"
    CHALLENGE_COMPLETED = "challenge_completed"

    # Admin actions
    ADMIN_ADJUSTMENT = "admin_adjustment"


class MultiplierType(Enum):
    """Types of point multipliers that can be applied."""

    VIP_BONUS = "vip_bonus"  # 50% bonus for VIP users
    STREAK_BONUS = "streak_bonus"  # Bonus based on consecutive days
    EVENT_BONUS = "event_bonus"  # Special event multipliers
    LEVEL_BONUS = "level_bonus"  # User level-based bonus
    ACHIEVEMENT_BONUS = "achievement_bonus"  # Special achievement bonuses


class AchievementCategory(Enum):
    """Categories for organizing achievements."""

    PROGRESS = "progress"  # General progress milestones
    SOCIAL = "social"  # Social interaction achievements
    NARRATIVE = "narrative"  # Story-related achievements
    DISCOVERY = "discovery"  # Exploration and finding secrets
    MASTERY = "mastery"  # Advanced skill demonstrations
    ENGAGEMENT = "engagement"  # Long-term engagement rewards


class LeaderboardType(Enum):
    """Types of leaderboards available in the system."""

    WEEKLY_POINTS = "weekly_points"  # Points earned this week
    TOTAL_POINTS = "total_points"  # All-time points
    CURRENT_STREAK = "current_streak"  # Consecutive active days
    NARRATIVE_PROGRESS = "narrative_progress"  # Story completion
    TRIVIA_CHAMPION = "trivia_champion"  # Trivia performance
    ACHIEVEMENTS_COUNT = "achievements_count"  # Total achievements unlocked


class AntiAbuseViolation(Enum):
    """Types of anti-abuse violations detected."""

    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    DUPLICATE_ACTION = "duplicate_action"
    INVALID_CONTEXT = "invalid_context"
    GAMING_BEHAVIOR = "gaming_behavior"


class PointsAwardResult:
    """Result of a points award operation with full transaction details."""

    def __init__(
        self,
        success: bool,
        user_id: int,
        action_type: ActionType,
        points_awarded: int,
        base_points: int,
        multipliers_applied: Dict[MultiplierType, float],
        new_balance: int,
        transaction_id: Optional[str] = None,
        achievements_unlocked: Optional[List[str]] = None,
        violation: Optional[AntiAbuseViolation] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.user_id = user_id
        self.action_type = action_type
        self.points_awarded = points_awarded
        self.base_points = base_points
        self.multipliers_applied = multipliers_applied
        self.new_balance = new_balance
        self.transaction_id = transaction_id
        self.achievements_unlocked = achievements_unlocked or []
        self.violation = violation
        self.error_message = error_message
        self.timestamp = datetime.now(timezone.utc)

    def __str__(self) -> str:
        if self.success:
            return f"PointsAward(user={self.user_id}, action={self.action_type.value}, +{self.points_awarded} → {self.new_balance})"
        else:
            return f"PointsAwardFailed(user={self.user_id}, action={self.action_type.value}, error={self.error_message})"


class AchievementUnlockResult:
    """Result of an achievement unlock operation."""

    def __init__(
        self,
        success: bool,
        user_id: int,
        achievement_id: str,
        achievement_name: str,
        level: int,
        points_reward: int,
        special_rewards: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.user_id = user_id
        self.achievement_id = achievement_id
        self.achievement_name = achievement_name
        self.level = level
        self.points_reward = points_reward
        self.special_rewards = special_rewards or {}
        self.error_message = error_message
        self.timestamp = datetime.now(timezone.utc)


class UserStats:
    """Comprehensive user gamification statistics."""

    def __init__(
        self,
        user_id: int,
        total_points: int,
        available_points: int,
        current_streak: int,
        longest_streak: int,
        achievements_unlocked: int,
        achievements_total: int,
        level: int,
        rank_weekly: Optional[int],
        rank_total: Optional[int],
        multipliers_active: Dict[MultiplierType, float],
        last_activity: datetime,
        created_at: datetime,
    ):
        self.user_id = user_id
        self.total_points = total_points
        self.available_points = available_points
        self.current_streak = current_streak
        self.longest_streak = longest_streak
        self.achievements_unlocked = achievements_unlocked
        self.achievements_total = achievements_total
        self.level = level
        self.rank_weekly = rank_weekly
        self.rank_total = rank_total
        self.multipliers_active = multipliers_active
        self.last_activity = last_activity
        self.created_at = created_at


class IAntiAbuseValidator(ABC):
    """
    Interface for anti-abuse validation system.

    Provides bulletproof protection against points gaming, duplicate awards,
    and suspicious behavior patterns while maintaining user experience.
    """

    @abstractmethod
    async def validate_action(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """
        Validate if an action is legitimate and should award points.

        Args:
            user_id: User performing the action
            action_type: Type of action being validated
            context: Action-specific context data
            timestamp: When the action occurred (defaults to now)

        Returns:
            Tuple of (is_valid, violation_type, error_message)

        Raises:
            ValidationError: If validation cannot be performed
        """
        pass

    @abstractmethod
    async def record_action(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        points_awarded: int,
    ) -> None:
        """
        Record a validated action for future anti-abuse checking.

        Args:
            user_id: User who performed the action
            action_type: Type of action performed
            context: Action context data
            points_awarded: Points awarded for the action
        """
        pass

    @abstractmethod
    async def get_rate_limit_status(
        self,
        user_id: int,
        action_type: ActionType,
    ) -> Dict[str, Any]:
        """
        Get current rate limit status for a user and action type.

        Returns:
            Dictionary with rate limit information:
            - actions_remaining: int
            - reset_time: datetime
            - window_duration: timedelta
        """
        pass


class IPointsEngine(ABC):
    """
    Interface for the core points calculation and transaction engine.

    Ensures atomic operations, prevents race conditions, and maintains
    perfect balance integrity with comprehensive audit trails.
    """

    @abstractmethod
    async def award_points(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        base_points: Optional[int] = None,
        force_award: bool = False,
    ) -> PointsAwardResult:
        """
        Award points to a user for a specific action with full validation.

        This is the primary method for points operations. It handles:
        - Anti-abuse validation
        - Multiplier calculations
        - Atomic database transactions
        - Achievement trigger checks
        - Event Bus notifications

        Args:
            user_id: User receiving the points
            action_type: Type of action that triggered the award
            context: Action-specific context for validation and calculation
            base_points: Override default points for the action
            force_award: Skip anti-abuse validation (admin use only)

        Returns:
            PointsAwardResult with transaction details and any achievements unlocked

        Raises:
            PointsEngineError: If the transaction cannot be completed
        """
        pass

    @abstractmethod
    async def get_user_balance(self, user_id: int) -> Tuple[int, int]:
        """
        Get user's current point balances.

        Args:
            user_id: User to query

        Returns:
            Tuple of (total_points, available_points)

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        pass

    @abstractmethod
    async def spend_points(
        self,
        user_id: int,
        amount: int,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Spend points from user's available balance.

        Args:
            user_id: User spending points
            amount: Points to spend (must be positive)
            reason: Reason for spending (for audit trail)
            context: Optional context data

        Returns:
            True if successful, False if insufficient balance

        Raises:
            PointsEngineError: If transaction fails
        """
        pass

    @abstractmethod
    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        action_types: Optional[List[ActionType]] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get user's points transaction history.

        Args:
            user_id: User to query
            limit: Maximum transactions to return
            action_types: Filter by specific action types
            since: Only return transactions after this date

        Returns:
            List of transaction dictionaries with full details
        """
        pass

    @abstractmethod
    async def calculate_multipliers(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> Dict[MultiplierType, float]:
        """
        Calculate all applicable multipliers for a user and action.

        Args:
            user_id: User to calculate multipliers for
            action_type: Type of action being performed
            context: Action context for multiplier calculation

        Returns:
            Dictionary mapping multiplier types to their values
        """
        pass

    @abstractmethod
    async def verify_balance_integrity(self, user_id: int) -> bool:
        """
        Verify that user's balance matches their transaction history.

        Critical for detecting data corruption or double-spending.

        Args:
            user_id: User to verify

        Returns:
            True if balance is correct, False if discrepancy found
        """
        pass


class IAchievementEngine(ABC):
    """
    Interface for achievement management and progression tracking.

    Handles achievement condition evaluation, unlocking mechanics,
    and reward distribution with support for multi-level achievements.
    """

    @abstractmethod
    async def check_achievements(
        self,
        user_id: int,
        trigger_event: IEvent,
    ) -> List[AchievementUnlockResult]:
        """
        Check if user's action triggers any achievement unlocks.

        Args:
            user_id: User to check achievements for
            trigger_event: Event that might trigger achievements

        Returns:
            List of achievements unlocked (empty if none)
        """
        pass

    @abstractmethod
    async def unlock_achievement(
        self,
        user_id: int,
        achievement_id: str,
        level: int = 1,
    ) -> AchievementUnlockResult:
        """
        Manually unlock an achievement for a user.

        Args:
            user_id: User to unlock achievement for
            achievement_id: Achievement to unlock
            level: Achievement level (Bronze=1, Silver=2, Gold=3)

        Returns:
            Result of the unlock operation
        """
        pass

    @abstractmethod
    async def get_user_achievements(
        self,
        user_id: int,
        category: Optional[AchievementCategory] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all achievements unlocked by a user.

        Args:
            user_id: User to query
            category: Filter by achievement category

        Returns:
            List of achievement data with unlock timestamps and levels
        """
        pass

    @abstractmethod
    async def get_achievement_progress(
        self,
        user_id: int,
        achievement_id: str,
    ) -> Dict[str, Any]:
        """
        Get user's progress toward a specific achievement.

        Args:
            user_id: User to check
            achievement_id: Achievement to check progress for

        Returns:
            Progress data including current/required values and percentage
        """
        pass

    @abstractmethod
    async def get_available_achievements(
        self,
        category: Optional[AchievementCategory] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all available achievements in the system.

        Args:
            category: Filter by specific category

        Returns:
            List of achievement definitions with requirements and rewards
        """
        pass


class ILeaderboardEngine(ABC):
    """
    Interface for dynamic leaderboard generation and ranking.

    Provides efficient ranking calculations with privacy controls,
    caching optimization, and real-time updates via Event Bus.
    """

    @abstractmethod
    async def get_leaderboard(
        self,
        leaderboard_type: LeaderboardType,
        limit: int = 10,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get leaderboard rankings for a specific type.

        Args:
            leaderboard_type: Type of leaderboard to generate
            limit: Number of top entries to return
            user_id: Include this user's rank even if not in top entries

        Returns:
            Leaderboard data with rankings, scores, and user position
        """
        pass

    @abstractmethod
    async def get_user_rankings(
        self,
        user_id: int,
    ) -> Dict[LeaderboardType, int]:
        """
        Get user's current rank across all leaderboard types.

        Args:
            user_id: User to get rankings for

        Returns:
            Dictionary mapping leaderboard types to current rank
        """
        pass

    @abstractmethod
    async def update_leaderboard_cache(
        self,
        leaderboard_type: LeaderboardType,
    ) -> None:
        """
        Force update of leaderboard cache for a specific type.

        Args:
            leaderboard_type: Type of leaderboard to refresh
        """
        pass

    @abstractmethod
    async def set_privacy_preference(
        self,
        user_id: int,
        show_in_leaderboards: bool,
    ) -> None:
        """
        Set user's privacy preference for leaderboard visibility.

        Args:
            user_id: User setting preference
            show_in_leaderboards: Whether to appear in public leaderboards
        """
        pass


class IGamificationService(ABC):
    """
    Main interface for the Gamification Service.

    Orchestrates all gamification functionality including points, achievements,
    and leaderboards while integrating with the Event Bus for real-time updates.
    This is the primary interface that other services will interact with.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the gamification service and all its engines.

        Sets up database connections, event subscriptions, and internal state.
        Must be called before using any other methods.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources and close connections.

        Should be called when shutting down the service.
        """
        pass

    @abstractmethod
    async def process_user_action(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> PointsAwardResult:
        """
        Process a user action for points and achievement evaluation.

        This is the main entry point for gamification events. It:
        1. Validates the action via anti-abuse system
        2. Awards points via points engine
        3. Checks for achievement unlocks
        4. Publishes events for other services

        Args:
            user_id: User performing the action
            action_type: Type of action performed
            context: Action-specific context data

        Returns:
            Result of points award including any achievements unlocked
        """
        pass

    @abstractmethod
    async def get_user_stats(self, user_id: int) -> UserStats:
        """
        Get comprehensive gamification statistics for a user.

        Args:
            user_id: User to get stats for

        Returns:
            Complete user statistics including points, achievements, and rankings
        """
        pass

    @abstractmethod
    async def get_leaderboards(
        self,
        user_id: int,
        types: Optional[List[LeaderboardType]] = None,
    ) -> Dict[LeaderboardType, Dict[str, Any]]:
        """
        Get leaderboard data for display to a user.

        Args:
            user_id: User requesting leaderboards (for privacy and ranking)
            types: Specific leaderboard types to include (all if None)

        Returns:
            Dictionary of leaderboard data keyed by type
        """
        pass

    @abstractmethod
    async def admin_adjust_points(
        self,
        admin_id: int,
        user_id: int,
        adjustment: int,
        reason: str,
    ) -> PointsAwardResult:
        """
        Admin function to manually adjust user points.

        Args:
            admin_id: Administrator making the adjustment
            user_id: User receiving the adjustment
            adjustment: Points to add/subtract (can be negative)
            reason: Reason for the adjustment (for audit)

        Returns:
            Result of the adjustment operation
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Get health status of the gamification service.

        Returns:
            Health information including engine status and performance metrics
        """
        pass
