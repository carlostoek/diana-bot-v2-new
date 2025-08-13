"""
Database models for Diana Bot V2.

This module defines all database models for the gamification system,
user data, and other core entities following SQLAlchemy best practices.
"""

# Export all models for easy importing
from .gamification import (
    Achievement,
    AchievementDefinition,
    LeaderboardEntry,
    PointsTransaction,
    StreakRecord,
    UserAchievement,
    UserGamification,
)

__all__ = [
    "Achievement",
    "AchievementDefinition",
    "LeaderboardEntry",
    "PointsTransaction",
    "StreakRecord",
    "UserAchievement",
    "UserGamification",
]
