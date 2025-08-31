"""
Gamification Service Data Models (SQLAlchemy)

This module defines the SQLAlchemy models for the Diana Bot V2 gamification system.
These models represent the database schema for points, achievements, and user statistics.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
from src.modules.user.models import User

class UserGamification(Base):
    __tablename__ = "gamification_user_stats"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    total_points = Column(Integer, default=0, nullable=False)
    available_points = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    experience_points = Column(Integer, default=0, nullable=False)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    last_streak_date = Column(DateTime(timezone=True), nullable=True)

    vip_multiplier = Column(Float, default=1.0, nullable=False)
    streak_multiplier = Column(Float, default=1.0, nullable=False)
    event_multiplier = Column(Float, default=1.0, nullable=False)

    daily_action_counts = Column(JSON, default=dict, nullable=False)
    last_daily_reset = Column(DateTime(timezone=True), nullable=True)

    show_in_leaderboards = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")

class PointsTransaction(Base):
    __tablename__ = "gamification_points_transactions"

    id = Column(String, primary_key=True) # Using UUID as string
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)
    points_change = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    base_points = Column(Integer, nullable=False)
    multipliers_applied = Column(JSON, default=dict)
    context = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

class Achievement(Base):
    __tablename__ = "gamification_achievements"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    conditions = Column(JSON, nullable=False)
    rewards = Column(JSON, nullable=False)
    icon_url = Column(String, nullable=True)
    is_secret = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    max_level = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserAchievement(Base):
    __tablename__ = "gamification_user_achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    achievement_id = Column(String, ForeignKey("gamification_achievements.id"), nullable=False, index=True)
    level = Column(Integer, default=1, nullable=False)
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())
    points_awarded = Column(Integer, default=0, nullable=False)
    special_rewards = Column(JSON, default=dict)

    user = relationship("User")
    achievement = relationship("Achievement")
