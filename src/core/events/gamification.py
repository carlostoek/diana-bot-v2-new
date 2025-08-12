"""
Gamification Events for Diana Bot V2.

This module defines all events related to the gamification system including
points, achievements, streaks, leaderboards, and other engagement mechanics.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..interfaces import EventPriority
from .base import DomainEvent, EventCategory


class PointsAwardedEvent(DomainEvent):
    """
    Event fired when points (Besitos) are awarded to a user.
    
    This is a core gamification event that tracks all point awards
    and serves as the basis for achievements, streaks, and rankings.
    """
    
    def __init__(
        self,
        user_id: int,
        points_amount: int,
        action_type: str,
        multiplier: float = 1.0,
        bonus_points: int = 0,
        source_event_id: Optional[str] = None,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize PointsAwardedEvent.
        
        Args:
            user_id: ID of the user receiving points
            points_amount: Base amount of points awarded
            action_type: Type of action that earned points (story_complete, daily_login, etc.)
            multiplier: Multiplier applied to base points
            bonus_points: Additional bonus points awarded
            source_event_id: ID of the event that triggered this point award
            source_service: Service awarding the points
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        total_points = int(points_amount * multiplier) + bonus_points
        
        payload = {
            "points_amount": points_amount,
            "multiplier": multiplier,
            "bonus_points": bonus_points,
            "total_points_awarded": total_points,
            "action_type": action_type,
            "source_event_id": source_event_id,
            "awarded_at": datetime.utcnow().isoformat(),
            # These will be set by the gamification service after processing
            "user_total_points_before": None,
            "user_total_points_after": None,
            "daily_points_before": None,
            "daily_points_after": None,
        }
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs
        )
    
    @property
    def points_amount(self) -> int:
        """Base amount of points awarded."""
        return self.payload["points_amount"]
    
    @property
    def multiplier(self) -> float:
        """Multiplier applied to base points."""
        return self.payload["multiplier"]
    
    @property
    def bonus_points(self) -> int:
        """Additional bonus points awarded."""
        return self.payload["bonus_points"]
    
    @property
    def total_points_awarded(self) -> int:
        """Total points awarded (base * multiplier + bonus)."""
        return self.payload["total_points_awarded"]
    
    @property
    def action_type(self) -> str:
        """Type of action that earned these points."""
        return self.payload["action_type"]
    
    @property
    def source_event_id(self) -> Optional[str]:
        """ID of the event that triggered this point award."""
        return self.payload.get("source_event_id")
    
    def _get_event_category(self) -> EventCategory:
        """Points events belong to the GAMIFICATION category."""
        return EventCategory.GAMIFICATION
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate points awarded specific requirements."""
        super()._custom_validation(errors)
        
        if not isinstance(self.points_amount, int) or self.points_amount <= 0:
            errors.append("Points amount must be a positive integer")
        
        if not isinstance(self.multiplier, (int, float)) or self.multiplier <= 0:
            errors.append("Multiplier must be a positive number")
        
        if not isinstance(self.bonus_points, int) or self.bonus_points < 0:
            errors.append("Bonus points must be a non-negative integer")
        
        if not self.action_type or not isinstance(self.action_type, str):
            errors.append("Action type must be a non-empty string")


class PointsDeductedEvent(DomainEvent):
    """
    Event fired when points are deducted from a user.
    
    This event tracks point deductions for penalties, refunds, or corrections.
    """
    
    def __init__(
        self,
        user_id: int,
        points_amount: int,
        deduction_reason: str,
        source_event_id: Optional[str] = None,
        admin_user_id: Optional[int] = None,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize PointsDeductedEvent.
        
        Args:
            user_id: ID of the user losing points
            points_amount: Amount of points deducted
            deduction_reason: Reason for deduction (penalty, refund, correction, etc.)
            source_event_id: ID of the event that triggered this deduction
            admin_user_id: ID of admin who authorized the deduction (if applicable)
            source_service: Service performing the deduction
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "points_amount": points_amount,
            "deduction_reason": deduction_reason,
            "source_event_id": source_event_id,
            "admin_user_id": admin_user_id,
            "deducted_at": datetime.utcnow().isoformat(),
            # These will be set by the gamification service after processing
            "user_total_points_before": None,
            "user_total_points_after": None,
        }
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,  # Deductions are important to track
            payload=payload,
            **kwargs
        )
    
    @property
    def points_amount(self) -> int:
        """Amount of points deducted."""
        return self.payload["points_amount"]
    
    @property
    def deduction_reason(self) -> str:
        """Reason for the deduction."""
        return self.payload["deduction_reason"]
    
    def _get_event_category(self) -> EventCategory:
        """Points events belong to the GAMIFICATION category."""
        return EventCategory.GAMIFICATION


class AchievementUnlockedEvent(DomainEvent):
    """
    Event fired when a user unlocks an achievement.
    
    This is a high-priority event that represents significant user milestones
    and often triggers additional rewards and notifications.
    """
    
    def __init__(
        self,
        user_id: int,
        achievement_id: str,
        achievement_name: str,
        achievement_category: str,
        achievement_tier: str,  # bronze, silver, gold, platinum
        points_reward: int = 0,
        badge_url: Optional[str] = None,
        unlock_criteria: Dict[str, Any] = None,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize AchievementUnlockedEvent.
        
        Args:
            user_id: ID of the user who unlocked the achievement
            achievement_id: Unique identifier for the achievement
            achievement_name: Display name of the achievement
            achievement_category: Category (narrative, social, exploration, etc.)
            achievement_tier: Tier of achievement (bronze, silver, gold, platinum)
            points_reward: Points awarded for unlocking this achievement
            badge_url: URL to the achievement badge/icon
            unlock_criteria: Details about what triggered the unlock
            source_service: Service that detected the achievement unlock
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "achievement_id": achievement_id,
            "achievement_name": achievement_name,
            "achievement_category": achievement_category,
            "achievement_tier": achievement_tier,
            "points_reward": points_reward,
            "badge_url": badge_url,
            "unlock_criteria": unlock_criteria or {},
            "unlocked_at": datetime.utcnow().isoformat(),
            "is_first_unlock": None,  # Set by gamification service
            "user_achievement_count": None,  # Set by gamification service
        }
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,  # Achievements are important events
            payload=payload,
            **kwargs
        )
    
    @property
    def achievement_id(self) -> str:
        """Unique identifier for the achievement."""
        return self.payload["achievement_id"]
    
    @property
    def achievement_name(self) -> str:
        """Display name of the achievement."""
        return self.payload["achievement_name"]
    
    @property
    def achievement_category(self) -> str:
        """Category of the achievement."""
        return self.payload["achievement_category"]
    
    @property
    def achievement_tier(self) -> str:
        """Tier of the achievement."""
        return self.payload["achievement_tier"]
    
    @property
    def points_reward(self) -> int:
        """Points awarded for this achievement."""
        return self.payload["points_reward"]
    
    @property
    def badge_url(self) -> Optional[str]:
        """URL to the achievement badge."""
        return self.payload.get("badge_url")
    
    def _get_event_category(self) -> EventCategory:
        """Achievement events belong to the GAMIFICATION category."""
        return EventCategory.GAMIFICATION
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate achievement unlocked specific requirements."""
        super()._custom_validation(errors)
        
        if not self.achievement_id or not isinstance(self.achievement_id, str):
            errors.append("Achievement ID must be a non-empty string")
        
        if not self.achievement_name or not isinstance(self.achievement_name, str):
            errors.append("Achievement name must be a non-empty string")
        
        if not self.achievement_category or not isinstance(self.achievement_category, str):
            errors.append("Achievement category must be a non-empty string")
        
        valid_tiers = {"bronze", "silver", "gold", "platinum"}
        if self.achievement_tier not in valid_tiers:
            errors.append(f"Achievement tier must be one of {valid_tiers}")


class StreakUpdatedEvent(DomainEvent):
    """
    Event fired when a user's streak is updated (continued or broken).
    
    This event tracks engagement streaks which are important for
    retention and motivation mechanics.
    """
    
    def __init__(
        self,
        user_id: int,
        streak_type: str,  # daily_login, story_progress, interaction, etc.
        previous_count: int,
        new_count: int,
        is_broken: bool = False,
        streak_milestone: Optional[int] = None,  # If a milestone was reached
        bonus_multiplier: float = 1.0,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize StreakUpdatedEvent.
        
        Args:
            user_id: ID of the user whose streak was updated
            streak_type: Type of streak (daily_login, story_progress, etc.)
            previous_count: Previous streak count
            new_count: New streak count
            is_broken: Whether the streak was broken
            streak_milestone: Milestone reached (if any)
            bonus_multiplier: Multiplier applied to rewards due to streak
            source_service: Service that updated the streak
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "streak_type": streak_type,
            "previous_count": previous_count,
            "new_count": new_count,
            "is_broken": is_broken,
            "streak_milestone": streak_milestone,
            "bonus_multiplier": bonus_multiplier,
            "updated_at": datetime.utcnow().isoformat(),
            "days_since_last_activity": None,  # Set by gamification service
            "longest_streak_ever": None,  # Set by gamification service
        }
        
        # Higher priority if milestone reached or streak broken
        priority = EventPriority.HIGH if (streak_milestone or is_broken) else EventPriority.NORMAL
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs
        )
    
    @property
    def streak_type(self) -> str:
        """Type of streak."""
        return self.payload["streak_type"]
    
    @property
    def previous_count(self) -> int:
        """Previous streak count."""
        return self.payload["previous_count"]
    
    @property
    def new_count(self) -> int:
        """New streak count."""
        return self.payload["new_count"]
    
    @property
    def is_broken(self) -> bool:
        """Whether the streak was broken."""
        return self.payload["is_broken"]
    
    @property
    def is_continued(self) -> bool:
        """Whether the streak was continued."""
        return not self.is_broken and self.new_count > self.previous_count
    
    @property
    def streak_milestone(self) -> Optional[int]:
        """Milestone reached (if any)."""
        return self.payload.get("streak_milestone")
    
    @property
    def bonus_multiplier(self) -> float:
        """Multiplier applied due to streak."""
        return self.payload["bonus_multiplier"]
    
    def _get_event_category(self) -> EventCategory:
        """Streak events belong to the GAMIFICATION category."""
        return EventCategory.GAMIFICATION
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate streak updated specific requirements."""
        super()._custom_validation(errors)
        
        if not self.streak_type or not isinstance(self.streak_type, str):
            errors.append("Streak type must be a non-empty string")
        
        if not isinstance(self.previous_count, int) or self.previous_count < 0:
            errors.append("Previous count must be a non-negative integer")
        
        if not isinstance(self.new_count, int) or self.new_count < 0:
            errors.append("New count must be a non-negative integer")


class LeaderboardChangedEvent(DomainEvent):
    """
    Event fired when leaderboard standings change significantly.
    
    This event is used to track and notify about leaderboard position changes,
    especially when users reach new ranks or milestones.
    """
    
    def __init__(
        self,
        user_id: int,
        leaderboard_type: str,  # global, weekly, monthly, friends, etc.
        previous_rank: Optional[int],
        new_rank: int,
        previous_score: Optional[int],
        new_score: int,
        rank_change_delta: Optional[int] = None,
        is_new_personal_best: bool = False,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize LeaderboardChangedEvent.
        
        Args:
            user_id: ID of the user whose rank changed
            leaderboard_type: Type of leaderboard (global, weekly, etc.)
            previous_rank: Previous rank (None if first time on leaderboard)
            new_rank: New rank on the leaderboard
            previous_score: Previous score
            new_score: New score
            rank_change_delta: Change in rank (positive = moved up)
            is_new_personal_best: Whether this is a new personal best score
            source_service: Service that updated the leaderboard
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        rank_change_delta = rank_change_delta or (
            (previous_rank - new_rank) if previous_rank else None
        )
        
        payload = {
            "leaderboard_type": leaderboard_type,
            "previous_rank": previous_rank,
            "new_rank": new_rank,
            "previous_score": previous_score,
            "new_score": new_score,
            "rank_change_delta": rank_change_delta,
            "is_new_personal_best": is_new_personal_best,
            "updated_at": datetime.utcnow().isoformat(),
            "total_participants": None,  # Set by gamification service
        }
        
        # Higher priority for significant rank improvements
        priority = EventPriority.HIGH if (
            rank_change_delta and rank_change_delta >= 10
        ) or is_new_personal_best else EventPriority.NORMAL
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs
        )
    
    @property
    def leaderboard_type(self) -> str:
        """Type of leaderboard."""
        return self.payload["leaderboard_type"]
    
    @property
    def previous_rank(self) -> Optional[int]:
        """Previous rank."""
        return self.payload.get("previous_rank")
    
    @property
    def new_rank(self) -> int:
        """New rank."""
        return self.payload["new_rank"]
    
    @property
    def rank_change_delta(self) -> Optional[int]:
        """Change in rank (positive = moved up)."""
        return self.payload.get("rank_change_delta")
    
    @property
    def moved_up(self) -> bool:
        """Whether the user moved up in rank."""
        return self.rank_change_delta is not None and self.rank_change_delta > 0
    
    @property
    def is_new_personal_best(self) -> bool:
        """Whether this is a new personal best."""
        return self.payload["is_new_personal_best"]
    
    def _get_event_category(self) -> EventCategory:
        """Leaderboard events belong to the GAMIFICATION category."""
        return EventCategory.GAMIFICATION
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate leaderboard changed specific requirements."""
        super()._custom_validation(errors)
        
        if not self.leaderboard_type or not isinstance(self.leaderboard_type, str):
            errors.append("Leaderboard type must be a non-empty string")
        
        if not isinstance(self.new_rank, int) or self.new_rank <= 0:
            errors.append("New rank must be a positive integer")
        
        if self.previous_rank is not None and (
            not isinstance(self.previous_rank, int) or self.previous_rank <= 0
        ):
            errors.append("Previous rank must be a positive integer")


class DailyBonusClaimedEvent(DomainEvent):
    """
    Event fired when a user claims their daily bonus.
    
    This event tracks daily engagement rewards and is important for
    retention mechanics and streak calculations.
    """
    
    def __init__(
        self,
        user_id: int,
        bonus_day: int,  # Day number in the bonus sequence (1-7, etc.)
        points_awarded: int,
        bonus_type: str = "standard",  # standard, premium, streak_bonus
        consecutive_days: int = 1,
        next_bonus_available_at: Optional[datetime] = None,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize DailyBonusClaimedEvent.
        
        Args:
            user_id: ID of the user claiming the bonus
            bonus_day: Day in the bonus sequence
            points_awarded: Points awarded for the daily bonus
            bonus_type: Type of bonus (standard, premium, streak_bonus)
            consecutive_days: Number of consecutive days claimed
            next_bonus_available_at: When the next bonus will be available
            source_service: Service processing the daily bonus
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "bonus_day": bonus_day,
            "points_awarded": points_awarded,
            "bonus_type": bonus_type,
            "consecutive_days": consecutive_days,
            "next_bonus_available_at": next_bonus_available_at.isoformat() if next_bonus_available_at else None,
            "claimed_at": datetime.utcnow().isoformat(),
        }
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs
        )
    
    @property
    def bonus_day(self) -> int:
        """Day in the bonus sequence."""
        return self.payload["bonus_day"]
    
    @property
    def points_awarded(self) -> int:
        """Points awarded for the bonus."""
        return self.payload["points_awarded"]
    
    @property
    def consecutive_days(self) -> int:
        """Number of consecutive days claimed."""
        return self.payload["consecutive_days"]
    
    def _get_event_category(self) -> EventCategory:
        """Daily bonus events belong to the GAMIFICATION category."""
        return EventCategory.GAMIFICATION


# Export all gamification events
__all__ = [
    "PointsAwardedEvent",
    "PointsDeductedEvent", 
    "AchievementUnlockedEvent",
    "StreakUpdatedEvent",
    "LeaderboardChangedEvent",
    "DailyBonusClaimedEvent",
]