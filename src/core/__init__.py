"""
Diana Bot V2 - Core Event Bus System

This package provides the foundational Event Bus architecture that serves
as the backbone for all inter-service communication in Diana Bot V2.
"""

from .events.admin import (
    AdminActionPerformedEvent,
    AnalyticsEvent,
    ContentModerationEvent,
    SystemMaintenanceEvent,
    UserBannedEvent,
    UserRegisteredEvent,
)

# Import new event system directly
from .events.base import BaseEventWithValidation
from .events.catalog import EventCatalog, ServiceName, event_catalog
from .events.core import (
    ConfigurationChangedEvent,
    ServiceHealthEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
    SystemErrorEvent,
    UserActionEvent,
)
from .events.gamification import (
    AchievementUnlockedEvent,
    DailyBonusClaimedEvent,
    LeaderboardChangedEvent,
    PointsAwardedEvent,
    PointsDeductedEvent,
    StreakUpdatedEvent,
)
from .events.narrative import (
    ChapterCompletedEvent,
    CharacterInteractionEvent,
    DecisionMadeEvent,
    NarrativeStateChangedEvent,
    StoryProgressEvent,
    StoryStartedEvent,
)


# Import EventType from events package for backward compatibility
def _get_legacy_events():
    """Import EventType from events package for backward compatibility."""
    try:
        # Import EventType from the events package
        from .events import EventType

        return {
            "EventType": EventType,
        }
    except ImportError:
        return {}


# Export legacy events as module-level variables
_legacy_events = _get_legacy_events()
for name, event_class in _legacy_events.items():
    globals()[name] = event_class
from .interfaces import (
    EventBusConfig,
    EventBusError,
    EventHandlingError,
    EventPriority,
    EventPublishError,
    EventSerializationError,
    EventStatus,
    EventSubscriptionError,
    EventValidationError,
    IEvent,
    IEventBus,
    IEventHandler,
    IEventMetrics,
    IEventStore,
)

# Import event_bus components conditionally to avoid Redis dependency issues
try:
    from .event_bus import (
        BaseEventHandler,
        EventProcessingResult,
        RedisEventBus,
        Subscription,
    )

    _EVENT_BUS_AVAILABLE = True
except ImportError as e:
    # Redis not available - create placeholder classes
    RedisEventBus = None
    BaseEventHandler = None
    Subscription = None
    EventProcessingResult = None
    _EVENT_BUS_AVAILABLE = False

__all__ = [
    # Interfaces
    "IEvent",
    "IEventBus",
    "IEventHandler",
    "IEventStore",
    "IEventMetrics",
    "EventBusConfig",
    "EventPriority",
    "EventStatus",
    # Exceptions
    "EventBusError",
    "EventPublishError",
    "EventSubscriptionError",
    "EventHandlingError",
    "EventValidationError",
    "EventSerializationError",
    # Event System - Base Classes
    "BaseEventWithValidation",
    # Gamification Events
    "PointsAwardedEvent",
    "PointsDeductedEvent",
    "AchievementUnlockedEvent",
    "StreakUpdatedEvent",
    "LeaderboardChangedEvent",
    "DailyBonusClaimedEvent",
    # Admin Events
    "UserRegisteredEvent",
    "UserBannedEvent",
    "AdminActionPerformedEvent",
    "ContentModerationEvent",
    "AnalyticsEvent",
    "SystemMaintenanceEvent",
    # Core Events
    "ServiceStartedEvent",
    "ServiceStoppedEvent",
    "ServiceHealthEvent",
    "SystemErrorEvent",
    "UserActionEvent",
    "ConfigurationChangedEvent",
    # Narrative Events
    "StoryProgressEvent",
    "DecisionMadeEvent",
    "ChapterCompletedEvent",
    "NarrativeStateChangedEvent",
    "CharacterInteractionEvent",
    "StoryStartedEvent",
    # Event Catalog System
    "EventCatalog",
    "ServiceName",
    "event_catalog",
    # Event Bus Implementation
    "RedisEventBus",
    "BaseEventHandler",
    "Subscription",
    "EventProcessingResult",
    # Legacy compatibility (dynamically added)
    # These are added via _legacy_events if available:
    # "BaseEvent", "EventType", "EventFactory",
    # "StoryChapterStartedEvent", "StoryDecisionMadeEvent",
    # "UserSubscriptionChangedEvent", "ErrorOccurredEvent",
    # etc.
]

# Dynamically add legacy events to __all__ if they exist
for name in _legacy_events.keys():
    if name not in __all__:
        __all__.append(name)

__version__ = "2.0.0"
