"""
Gamification Database Models for Diana Bot V2.

This module defines all database models related to the gamification system
including points, achievements, leaderboards, and user progress tracking.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class AchievementTier(PyEnum):
    """Achievement tier levels."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class AchievementCategory(PyEnum):
    """Achievement categories."""

    NARRATIVE = "narrative"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    ENGAGEMENT = "engagement"
    MILESTONE = "milestone"
    SPECIAL = "special"


class StreakType(PyEnum):
    """Types of streaks users can maintain."""

    DAILY_LOGIN = "daily_login"
    STORY_PROGRESS = "story_progress"
    INTERACTION = "interaction"
    ACHIEVEMENT_UNLOCK = "achievement_unlock"


class LeaderboardType(PyEnum):
    """Types of leaderboards."""

    GLOBAL = "global"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    FRIENDS = "friends"
    STORY_COMPLETION = "story_completion"


class PointsTransactionType(PyEnum):
    """Types of points transactions."""

    EARNED = "earned"
    SPENT = "spent"
    BONUS = "bonus"
    PENALTY = "penalty"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class UserGamification(Base):
    """
    Core gamification data for each user.

    This table stores the main gamification metrics and state for each user,
    serving as the central hub for all gamification calculations.
    """

    __tablename__ = "user_gamification"

    user_id = Column(BigInteger, primary_key=True, index=True)
    total_points = Column(Integer, default=0, nullable=False, index=True)
    current_level = Column(Integer, default=1, nullable=False)
    experience_points = Column(Integer, default=0, nullable=False)

    # Streak tracking
    current_daily_streak = Column(Integer, default=0, nullable=False)
    longest_daily_streak = Column(Integer, default=0, nullable=False)
    last_activity_date = Column(DateTime(timezone=True), nullable=True)

    # Achievement tracking
    total_achievements = Column(Integer, default=0, nullable=False)
    bronze_achievements = Column(Integer, default=0, nullable=False)
    silver_achievements = Column(Integer, default=0, nullable=False)
    gold_achievements = Column(Integer, default=0, nullable=False)
    platinum_achievements = Column(Integer, default=0, nullable=False)

    # Multipliers and bonuses
    current_multiplier = Column(Float, default=1.0, nullable=False)
    vip_status = Column(Boolean, default=False, nullable=False)
    vip_multiplier = Column(Float, default=1.0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    points_transactions = relationship(
        "PointsTransaction", back_populates="user_gamification"
    )
    user_achievements = relationship(
        "UserAchievement", back_populates="user_gamification"
    )
    streak_records = relationship("StreakRecord", back_populates="user_gamification")
    leaderboard_entries = relationship(
        "LeaderboardEntry", back_populates="user_gamification"
    )

    def __repr__(self):
        return f"<UserGamification(user_id={self.user_id}, points={self.total_points}, level={self.current_level})>"


class PointsTransaction(Base):
    """
    Audit trail for all points transactions.

    This table provides complete transaction history for points, enabling
    detailed analytics and anti-abuse detection.
    """

    __tablename__ = "points_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("user_gamification.user_id"), nullable=False, index=True
    )

    # Transaction details
    transaction_type = Column(Enum(PointsTransactionType), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Can be negative for deductions
    points_before = Column(Integer, nullable=False)
    points_after = Column(Integer, nullable=False)

    # Context and metadata
    action_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    source_service = Column(String(50), nullable=False)

    # Event tracking
    source_event_id = Column(String(100), nullable=True, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)

    # Anti-abuse tracking
    multiplier_applied = Column(Float, default=1.0, nullable=False)
    bonus_applied = Column(Integer, default=0, nullable=False)
    is_suspicious = Column(Boolean, default=False, nullable=False, index=True)

    # Additional transaction metadata
    transaction_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user_gamification = relationship(
        "UserGamification", back_populates="points_transactions"
    )

    def __repr__(self):
        return f"<PointsTransaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, type={self.transaction_type.value})>"


class AchievementDefinition(Base):
    """
    Definitions for all available achievements.

    This table defines the criteria and metadata for achievements
    that users can unlock.
    """

    __tablename__ = "achievement_definitions"

    id = Column(String(100), primary_key=True)  # e.g., "first_story_completion"
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # Achievement properties
    category = Column(Enum(AchievementCategory), nullable=False, index=True)
    tier = Column(Enum(AchievementTier), nullable=False, index=True)
    points_reward = Column(Integer, default=0, nullable=False)

    # Unlock criteria
    unlock_criteria = Column(JSON, nullable=False)  # Flexible criteria definition
    is_secret = Column(Boolean, default=False, nullable=False)
    is_repeatable = Column(Boolean, default=False, nullable=False)

    # Display properties
    badge_url = Column(String(500), nullable=True)
    icon_name = Column(String(100), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user_achievements = relationship(
        "UserAchievement", back_populates="achievement_definition"
    )

    def __repr__(self):
        return f"<AchievementDefinition(id={self.id}, name={self.name}, tier={self.tier.value})>"


class UserAchievement(Base):
    """
    Tracks which achievements users have unlocked.

    This table records when users unlock achievements and provides
    progress tracking for multi-step achievements.
    """

    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("user_gamification.user_id"), nullable=False, index=True
    )
    achievement_id = Column(
        String(100),
        ForeignKey("achievement_definitions.id"),
        nullable=False,
        index=True,
    )

    # Progress tracking
    progress_current = Column(Integer, default=0, nullable=False)
    progress_required = Column(Integer, default=1, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False, index=True)

    # Unlock details
    unlocked_at = Column(DateTime(timezone=True), nullable=True)
    points_awarded = Column(Integer, default=0, nullable=False)

    # Event tracking
    unlock_event_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user_gamification = relationship(
        "UserGamification", back_populates="user_achievements"
    )
    achievement_definition = relationship(
        "AchievementDefinition", back_populates="user_achievements"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
        Index("ix_user_achievements_user_completed", "user_id", "is_completed"),
    )

    def __repr__(self):
        return f"<UserAchievement(user_id={self.user_id}, achievement_id={self.achievement_id}, completed={self.is_completed})>"


class StreakRecord(Base):
    """
    Tracks user streaks across different categories.

    This table maintains streak information for various user activities,
    enabling streak-based rewards and achievements.
    """

    __tablename__ = "streak_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("user_gamification.user_id"), nullable=False, index=True
    )

    # Streak details
    streak_type = Column(Enum(StreakType), nullable=False, index=True)
    current_count = Column(Integer, default=0, nullable=False)
    longest_count = Column(Integer, default=0, nullable=False)

    # Date tracking
    last_activity_date = Column(DateTime(timezone=True), nullable=True)
    streak_start_date = Column(DateTime(timezone=True), nullable=True)
    last_reset_date = Column(DateTime(timezone=True), nullable=True)

    # Bonus tracking
    current_multiplier = Column(Float, default=1.0, nullable=False)
    milestones_reached = Column(JSON, nullable=True)  # List of milestone values reached

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    freeze_count = Column(Integer, default=0, nullable=False)  # VIP streak freezes used

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user_gamification = relationship(
        "UserGamification", back_populates="streak_records"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "streak_type", name="uq_user_streak_type"),
        Index("ix_streak_records_type_active", "streak_type", "is_active"),
    )

    def __repr__(self):
        return f"<StreakRecord(user_id={self.user_id}, type={self.streak_type.value}, current={self.current_count})>"


class LeaderboardEntry(Base):
    """
    Tracks user positions on various leaderboards.

    This table maintains leaderboard rankings for different time periods
    and categories, enabling competitive features.
    """

    __tablename__ = "leaderboard_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("user_gamification.user_id"), nullable=False, index=True
    )

    # Leaderboard details
    leaderboard_type = Column(Enum(LeaderboardType), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)

    # Ranking details
    rank = Column(Integer, nullable=False, index=True)
    score = Column(Integer, nullable=False, index=True)
    previous_rank = Column(Integer, nullable=True)
    rank_change = Column(Integer, nullable=True)  # Positive = moved up

    # Achievement tracking
    is_personal_best = Column(Boolean, default=False, nullable=False)
    rewards_claimed = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user_gamification = relationship(
        "UserGamification", back_populates="leaderboard_entries"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "leaderboard_type",
            "period_start",
            name="uq_user_leaderboard_period",
        ),
        Index(
            "ix_leaderboard_entries_type_period",
            "leaderboard_type",
            "period_start",
            "period_end",
        ),
        Index(
            "ix_leaderboard_entries_rank_score",
            "leaderboard_type",
            "period_start",
            "rank",
            "score",
        ),
    )

    def __repr__(self):
        return f"<LeaderboardEntry(user_id={self.user_id}, type={self.leaderboard_type.value}, rank={self.rank})>"


# Convenience alias for backward compatibility
Achievement = AchievementDefinition
