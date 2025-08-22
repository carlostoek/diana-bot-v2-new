"""
Gamification Service for Diana Bot V2

This package provides the core gamification functionality including:
- Points system ("Besitos") with anti-abuse protection
- Achievement system with multi-level progression
- Dynamic leaderboards with privacy controls
- Event Bus integration for real-time updates

The service follows Clean Architecture principles and integrates
seamlessly with the Event Bus backbone for distributed communication.
"""

from .interfaces import (
    IAchievementEngine,
    IGamificationService,
    ILeaderboardEngine,
    IPointsEngine,
)
from .models import Achievement, PointsTransaction, UserAchievement, UserGamification
from .service import GamificationService

__all__ = [
    "IGamificationService",
    "IPointsEngine",
    "IAchievementEngine",
    "ILeaderboardEngine",
    "UserGamification",
    "PointsTransaction",
    "Achievement",
    "UserAchievement",
    "GamificationService",
]
