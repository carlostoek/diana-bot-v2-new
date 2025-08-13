"""
Event Contracts and Catalog for Diana Bot V2.

This package provides a comprehensive event system with proper validation,
type safety, and clean architecture principles. All events follow established
contracts and are cataloged for service communication mapping.
"""

from .base import (
    BaseEventWithValidation,
    DomainEvent,
    EventCategory,
    EventMetadata,
    IntegrationEvent,
    SystemEvent,
    ValidationLevel,
)


# Legacy EventType class for backward compatibility
class EventType:
    """Constants for all event types in the system."""

    # Gamification Events
    POINTS_AWARDED = "gamification.points_awarded"
    POINTS_DEDUCTED = "gamification.points_deducted"
    ACHIEVEMENT_UNLOCKED = "gamification.achievement_unlocked"
    STREAK_UPDATED = "gamification.streak_updated"
    LEADERBOARD_UPDATED = "gamification.leaderboard_changed"

    # Narrative Events
    STORY_CHAPTER_STARTED = "narrative.story_started"
    STORY_CHAPTER_COMPLETED = "narrative.chapter_completed"
    STORY_DECISION_MADE = "narrative.decision_made"
    CHARACTER_INTERACTION = "narrative.character_interaction"
    STORY_PROGRESS_UPDATED = "narrative.story_progress"

    # User Events
    USER_REGISTERED = "user.registered"
    USER_PROFILE_UPDATED = "user.profile.updated"
    USER_AUTHENTICATION_FAILED = "user.authentication.failed"
    USER_SESSION_CREATED = "user.session.created"
    USER_ROLE_CHANGED = "user.role.changed"
    USER_SUBSCRIPTION_CHANGED = "user.subscription.changed"
    USER_ONBOARDING_STARTED = "user.onboarding.started"
    USER_ONBOARDING_COMPLETED = "user.onboarding.completed"
    USER_PERSONALITY_DETECTED = "user.personality.detected"
    USER_ACTIVITY_DETECTED = "user.activity.detected"
    USER_PREFERENCES_UPDATED = "user.preferences.updated"

    # Admin Events
    ADMIN_ACTION_PERFORMED = "admin.admin_action_performed"

    # System Events
    SERVICE_STARTED = "core.service_started"
    ERROR_OCCURRED = "core.system_error"


# Import specific event implementations
try:
    from .core import *
except ImportError:
    pass

try:
    from .gamification import *
except ImportError:
    pass

try:
    from .narrative import *
except ImportError:
    pass

try:
    from .user import *
except ImportError:
    pass

try:
    from .admin import *
except ImportError:
    pass

try:
    from .catalog import EventCatalog, ServiceName, event_catalog
except ImportError:
    EventCatalog = None
    event_catalog = None
    ServiceName = None

# Re-export common types and classes
__all__ = [
    # Base classes
    "BaseEventWithValidation",
    "DomainEvent",
    "SystemEvent",
    "IntegrationEvent",
    # Supporting types
    "EventCategory",
    "EventMetadata",
    "ValidationLevel",
    # Legacy compatibility
    "EventType",
    # Event Catalog
    "EventCatalog",
    "ServiceName",
    "event_catalog",
]
