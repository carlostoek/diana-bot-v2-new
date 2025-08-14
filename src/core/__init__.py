"""
Core Diana Bot functionality.

This module provides the foundational interfaces and implementations for the
Diana Bot V2 event-driven architecture.

Interfaces:
- IEvent: Abstract base class for all events
- IEventBus: Abstract interface for event publishing and subscription
- IEventHandler: Abstract interface for event processing

Implementations:
- EventBus: Redis-based event bus implementation (stub)
- GameEvent: Events for gamification system
- NarrativeEvent: Events for story progression
- AdminEvent: Events for administrative actions
- UserEvent: Events for user interactions
- SystemEvent: Events for system monitoring

Exceptions:
- EventBusError: Base exception for event bus operations
- PublishError: Exception for publishing failures
- SubscribeError: Exception for subscription failures
- EventValidationError: Exception for event validation failures
"""

# Import concrete implementations
from .events import (
    AdminEvent,
    EventBus,
    GameEvent,
    NarrativeEvent,
    SystemEvent,
    UserEvent,
)

# Import exceptions
from .exceptions import (
    EventBusError,
    EventValidationError,
    PublishError,
    SubscribeError,
)

# Import interfaces
from .interfaces import IEvent, IEventBus, IEventHandler

__all__ = [
    # Interfaces
    "IEvent",
    "IEventBus",
    "IEventHandler",
    # Implementations
    "EventBus",
    "GameEvent",
    "NarrativeEvent",
    "AdminEvent",
    "UserEvent",
    "SystemEvent",
    # Exceptions
    "EventBusError",
    "PublishError",
    "SubscribeError",
    "EventValidationError",
]
