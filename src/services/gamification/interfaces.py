"""
Gamification Service Interfaces for Diana Bot V2.

This module defines the contracts for the gamification system,
following Clean Architecture principles and ensuring clear
separation of concerns.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ...models.gamification import (
    AchievementDefinition,
    AchievementTier,
    LeaderboardType,
    PointsTransactionType,
    StreakType,
    UserAchievement,
    UserGamification,
)


class IGamificationService(ABC):
    """
    Core interface for the Gamification Service.

    This service handles all gamification mechanics including points,
    achievements, leaderboards, and streaks. It operates in an event-driven
    manner, reacting to user actions and story events.
    """

    # ================= Service Lifecycle =================

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the gamification service.

        This method sets up database connections, subscribes to events,
        and performs any necessary startup procedures.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the gamification service.

        This method cleans up resources and unsubscribes from events.
        """
        pass

    # ================= Points System =================

    @abstractmethod
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
        """
        Award points to a user for a specific action.

        Args:
            user_id: ID of the user receiving points
            points_amount: Base amount of points to award
            action_type: Type of action that earned points
            multiplier: Multiplier to apply to base points
            bonus_points: Additional bonus points
            source_event_id: ID of the event that triggered this award
            metadata: Additional metadata for the transaction

        Returns:
            True if points were successfully awarded

        Raises:
            ValueError: If points_amount is invalid
            UserNotFoundError: If user doesn't exist
        """
        pass

    @abstractmethod
    async def deduct_points(
        self,
        user_id: int,
        points_amount: int,
        deduction_reason: str,
        admin_user_id: Optional[int] = None,
        source_event_id: Optional[str] = None,
    ) -> bool:
        """
        Deduct points from a user.

        Args:
            user_id: ID of the user losing points
            points_amount: Amount of points to deduct
            deduction_reason: Reason for the deduction
            admin_user_id: ID of admin authorizing deduction (if applicable)
            source_event_id: ID of the event that triggered this deduction

        Returns:
            True if points were successfully deducted
        """
        pass

    @abstractmethod
    async def get_user_points(self, user_id: int) -> int:
        """
        Get the current points balance for a user.

        Args:
            user_id: ID of the user

        Returns:
            Current points balance
        """
        pass

    @abstractmethod
    async def get_points_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[PointsTransactionType] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get points transaction history for a user.

        Args:
            user_id: ID of the user
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            transaction_type: Filter by specific transaction type

        Returns:
            List of transaction records
        """
        pass

    # ================= Achievement System =================

    @abstractmethod
    async def check_achievements(
        self, user_id: int, trigger_context: Dict[str, Any]
    ) -> List[UserAchievement]:
        """
        Check if a user has unlocked any new achievements.

        Args:
            user_id: ID of the user to check
            trigger_context: Context about what triggered the check

        Returns:
            List of newly unlocked achievements
        """
        pass

    @abstractmethod
    async def unlock_achievement(
        self, user_id: int, achievement_id: str, source_event_id: Optional[str] = None
    ) -> UserAchievement:
        """
        Manually unlock an achievement for a user.

        Args:
            user_id: ID of the user
            achievement_id: ID of the achievement to unlock
            source_event_id: ID of the event that triggered this unlock

        Returns:
            The unlocked achievement record
        """
        pass

    @abstractmethod
    async def get_user_achievements(
        self, user_id: int, completed_only: bool = False
    ) -> List[UserAchievement]:
        """
        Get all achievements for a user.

        Args:
            user_id: ID of the user
            completed_only: Whether to return only completed achievements

        Returns:
            List of user achievements
        """
        pass

    @abstractmethod
    async def get_achievement_progress(
        self, user_id: int, achievement_id: str
    ) -> Optional[UserAchievement]:
        """
        Get progress for a specific achievement.

        Args:
            user_id: ID of the user
            achievement_id: ID of the achievement

        Returns:
            Achievement progress or None if not started
        """
        pass

    @abstractmethod
    async def create_achievement_definition(
        self, achievement_data: Dict[str, Any]
    ) -> AchievementDefinition:
        """
        Create a new achievement definition.

        Args:
            achievement_data: Achievement definition data

        Returns:
            Created achievement definition
        """
        pass

    # ================= Streak System =================

    @abstractmethod
    async def update_streak(
        self,
        user_id: int,
        streak_type: StreakType,
        activity_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Update a user's streak for a specific activity type.

        Args:
            user_id: ID of the user
            streak_type: Type of streak to update
            activity_date: Date of the activity (defaults to now)

        Returns:
            Streak update information including new count and milestones
        """
        pass

    @abstractmethod
    async def get_user_streaks(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all active streaks for a user.

        Args:
            user_id: ID of the user

        Returns:
            List of streak records
        """
        pass

    @abstractmethod
    async def freeze_streak(self, user_id: int, streak_type: StreakType) -> bool:
        """
        Use a streak freeze for VIP users.

        Args:
            user_id: ID of the user
            streak_type: Type of streak to freeze

        Returns:
            True if freeze was successfully applied
        """
        pass

    # ================= Leaderboard System =================

    @abstractmethod
    async def update_leaderboard(
        self,
        user_id: int,
        leaderboard_type: LeaderboardType,
        score: int,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        """
        Update a user's position on a leaderboard.

        Args:
            user_id: ID of the user
            leaderboard_type: Type of leaderboard
            score: User's current score
            period_start: Start of the leaderboard period
            period_end: End of the leaderboard period

        Returns:
            Leaderboard update information including rank and changes
        """
        pass

    @abstractmethod
    async def get_leaderboard(
        self,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
        limit: int = 10,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get leaderboard rankings for a specific period.

        Args:
            leaderboard_type: Type of leaderboard
            period_start: Start of the period
            period_end: End of the period
            limit: Number of top entries to return
            user_id: If provided, also include this user's rank

        Returns:
            Leaderboard data including rankings and user position
        """
        pass

    @abstractmethod
    async def get_user_rank(
        self,
        user_id: int,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
    ) -> Optional[int]:
        """
        Get a user's rank on a specific leaderboard.

        Args:
            user_id: ID of the user
            leaderboard_type: Type of leaderboard
            period_start: Start of the period
            period_end: End of the period

        Returns:
            User's rank or None if not on leaderboard
        """
        pass

    # ================= User Management =================

    @abstractmethod
    async def initialize_user(self, user_id: int) -> UserGamification:
        """
        Initialize gamification data for a new user.

        Args:
            user_id: ID of the user to initialize

        Returns:
            Created user gamification record
        """
        pass

    @abstractmethod
    async def get_user_gamification(self, user_id: int) -> Optional[UserGamification]:
        """
        Get gamification data for a user.

        Args:
            user_id: ID of the user

        Returns:
            User gamification data or None if not found
        """
        pass

    @abstractmethod
    async def update_user_level(self, user_id: int) -> Tuple[int, bool]:
        """
        Update a user's level based on their experience points.

        Args:
            user_id: ID of the user

        Returns:
            Tuple of (new_level, level_increased)
        """
        pass

    @abstractmethod
    async def set_vip_status(
        self, user_id: int, is_vip: bool, vip_multiplier: float = 1.5
    ) -> bool:
        """
        Set VIP status for a user.

        Args:
            user_id: ID of the user
            is_vip: Whether the user should have VIP status
            vip_multiplier: Points multiplier for VIP users

        Returns:
            True if status was successfully updated
        """
        pass

    # ================= Analytics and Reporting =================

    @abstractmethod
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive gamification statistics for a user.

        Args:
            user_id: ID of the user

        Returns:
            Dictionary containing various statistics
        """
        pass

    @abstractmethod
    async def get_system_statistics(self) -> Dict[str, Any]:
        """
        Get system-wide gamification statistics.

        Returns:
            Dictionary containing system statistics
        """
        pass

    # ================= Configuration and Settings =================

    @abstractmethod
    async def get_points_configuration(self) -> Dict[str, Any]:
        """
        Get current points system configuration.

        Returns:
            Points configuration settings
        """
        pass

    @abstractmethod
    async def update_points_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Update points system configuration.

        Args:
            config: New configuration settings

        Returns:
            True if configuration was successfully updated
        """
        pass


class IGamificationEventHandlers(ABC):
    """
    Interface for gamification event handlers.

    This interface defines the methods that handle various events
    that trigger gamification mechanics.
    """

    @abstractmethod
    async def handle_user_action(self, event: Any) -> None:
        """
        Handle UserActionEvent to award points and check achievements.

        Args:
            event: UserActionEvent instance
        """
        pass

    @abstractmethod
    async def handle_story_completion(self, event: Any) -> None:
        """
        Handle StoryCompletionEvent to award completion rewards.

        Args:
            event: StoryCompletionEvent instance
        """
        pass

    @abstractmethod
    async def handle_chapter_completion(self, event: Any) -> None:
        """
        Handle ChapterCompletedEvent to award progress rewards.

        Args:
            event: ChapterCompletedEvent instance
        """
        pass

    @abstractmethod
    async def handle_decision_made(self, event: Any) -> None:
        """
        Handle DecisionMadeEvent to award engagement points.

        Args:
            event: DecisionMadeEvent instance
        """
        pass


class IGamificationRepository(ABC):
    """
    Interface for gamification data access.

    This interface abstracts the data layer for the gamification system,
    enabling easy testing and potential database switching.
    """

    # User Gamification CRUD
    @abstractmethod
    async def get_user_gamification(self, user_id: int) -> Optional[UserGamification]:
        """Get user gamification data."""
        pass

    @abstractmethod
    async def create_user_gamification(self, user_id: int) -> UserGamification:
        """Create new user gamification record."""
        pass

    @abstractmethod
    async def update_user_gamification(
        self, user_gamification: UserGamification
    ) -> UserGamification:
        """Update user gamification record."""
        pass

    # Points Transactions
    @abstractmethod
    async def create_points_transaction(self, transaction_data: Dict[str, Any]) -> Any:
        """Create a new points transaction record."""
        pass

    @abstractmethod
    async def get_points_transactions(
        self,
        user_id: int,
        limit: int,
        offset: int,
        transaction_type: Optional[PointsTransactionType],
    ) -> List[Any]:
        """Get points transaction history."""
        pass

    # Achievements
    @abstractmethod
    async def get_achievement_definitions(
        self, active_only: bool = True
    ) -> List[AchievementDefinition]:
        """Get all achievement definitions."""
        pass

    @abstractmethod
    async def get_user_achievements(
        self, user_id: int, completed_only: bool = False
    ) -> List[UserAchievement]:
        """Get user achievements."""
        pass

    @abstractmethod
    async def create_user_achievement(
        self, achievement_data: Dict[str, Any]
    ) -> UserAchievement:
        """Create a new user achievement record."""
        pass

    @abstractmethod
    async def update_user_achievement(
        self, user_achievement: UserAchievement
    ) -> UserAchievement:
        """Update user achievement progress."""
        pass

    # Streaks
    @abstractmethod
    async def get_user_streaks(self, user_id: int) -> List[Any]:
        """Get user streak records."""
        pass

    @abstractmethod
    async def update_streak_record(self, streak_data: Dict[str, Any]) -> Any:
        """Update or create streak record."""
        pass

    # Leaderboards
    @abstractmethod
    async def update_leaderboard_entry(self, entry_data: Dict[str, Any]) -> Any:
        """Update or create leaderboard entry."""
        pass

    @abstractmethod
    async def get_leaderboard_entries(
        self,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
        limit: int,
    ) -> List[Any]:
        """Get leaderboard entries for a period."""
        pass


# Exception classes for the gamification system
class GamificationError(Exception):
    """Base exception for gamification-related errors."""

    pass


class UserNotFoundError(GamificationError):
    """Raised when a user is not found in the gamification system."""

    pass


class InsufficientPointsError(GamificationError):
    """Raised when a user doesn't have enough points for an operation."""

    pass


class AchievementNotFoundError(GamificationError):
    """Raised when an achievement is not found."""

    pass


class InvalidConfigurationError(GamificationError):
    """Raised when gamification configuration is invalid."""

    pass


class AntiAbuseError(GamificationError):
    """Raised when anti-abuse mechanisms detect suspicious activity."""

    pass
