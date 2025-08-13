"""
Gamification Service Package for Diana Bot V2.

This package provides a complete gamification system with points, achievements,
streaks, and leaderboards using event-driven architecture and Clean Architecture principles.

Main Components:
- GamificationServiceImpl: Main service orchestrator
- Repository: Data access layer with async SQLAlchemy
- Engines: Business logic for points, achievements, streaks, and leaderboards
- Event Handlers: Event-driven integration with other services

Usage Example:
    from src.services.gamification import GamificationServiceImpl
    from src.core.event_bus import RedisEventBus

    # Initialize service
    event_bus = RedisEventBus()
    service = GamificationServiceImpl(event_bus)
    await service.initialize()

    # Award points
    await service.award_points(
        user_id=123,
        points_amount=100,
        action_type="story_complete"
    )

    # Check achievements
    await service.check_achievements(123, {"action_type": "story_complete"})

    # Update streaks
    await service.update_streak(123, StreakType.DAILY_LOGIN)
"""

from .event_handlers import create_gamification_event_handlers

# Keep backward compatibility
from .interfaces import (
    AchievementNotFoundError,
    AntiAbuseError,
    GamificationError,
    IGamificationRepository,
    IGamificationService,
    InsufficientPointsError,
    UserNotFoundError,
)
from .repository_impl import GamificationRepositoryImpl
from .service import GamificationService
from .service_impl import GamificationServiceImpl

# Version info
__version__ = "2.0.0"
__author__ = "Diana Bot V2 Team"

# Export main classes and interfaces
__all__ = [
    # Main service implementations
    "GamificationServiceImpl",
    "GamificationRepositoryImpl",
    # Interfaces
    "IGamificationService",
    "IGamificationRepository",
    # Exceptions
    "GamificationError",
    "UserNotFoundError",
    "InsufficientPointsError",
    "AntiAbuseError",
    "AchievementNotFoundError",
    # Event handlers
    "create_gamification_event_handlers",
    # Backward compatibility
    "GamificationService",
    # Version info
    "__version__",
    "__author__",
]
