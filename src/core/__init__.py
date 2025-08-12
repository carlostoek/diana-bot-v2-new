"""
Diana Bot V2 - Core Event Bus System

This package provides the foundational Event Bus architecture that serves
as the backbone for all inter-service communication in Diana Bot V2.
"""

from .interfaces import (
    IEvent,
    IEventBus,
    IEventHandler,
    IEventStore,
    IEventMetrics,
    EventBusConfig,
    EventPriority,
    EventStatus,
    EventBusError,
    EventPublishError,
    EventSubscriptionError,
    EventHandlingError,
    EventValidationError,
    EventSerializationError
)

from .events import (
    BaseEvent,
    EventType,
    PointsAwardedEvent,
    AchievementUnlockedEvent,
    StreakUpdatedEvent,
    StoryChapterStartedEvent,
    StoryDecisionMadeEvent,
    UserRegisteredEvent,
    UserSubscriptionChangedEvent,
    AdminActionPerformedEvent,
    ServiceStartedEvent,
    ErrorOccurredEvent,
    EventFactory
)

# Import event_bus components conditionally to avoid Redis dependency issues
try:
    from .event_bus import (
        RedisEventBus,
        BaseEventHandler,
        Subscription,
        EventProcessingResult
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
    
    # Event Types
    "BaseEvent",
    "EventType",
    "PointsAwardedEvent",
    "AchievementUnlockedEvent",
    "StreakUpdatedEvent",
    "StoryChapterStartedEvent",
    "StoryDecisionMadeEvent",
    "UserRegisteredEvent",
    "UserSubscriptionChangedEvent",
    "AdminActionPerformedEvent",
    "ServiceStartedEvent",
    "ErrorOccurredEvent",
    "EventFactory",
    
    # Event Bus Implementation
    "RedisEventBus",
    "BaseEventHandler",
    "Subscription",
    "EventProcessingResult"
]

__version__ = "2.0.0"