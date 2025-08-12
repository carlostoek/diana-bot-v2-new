"""
Core interfaces for Diana Bot V2 Event Bus system.

This module defines the fundamental contracts for event-driven communication
between services, following Clean Architecture principles and ensuring
type safety throughout the system.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, Union

# Type Variables for Generic Type Safety
EventT = TypeVar("EventT", bound="IEvent")
HandlerT = TypeVar("HandlerT", bound="IEventHandler")


class EventPriority(Enum):
    """Event processing priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventStatus(Enum):
    """Event processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class IEvent(ABC):
    """
    Base interface for all events in the Diana Bot system.

    Events are immutable data structures that represent something that
    has happened in the system. They carry all necessary information
    for other services to react appropriately.
    """

    @property
    @abstractmethod
    def event_id(self) -> str:
        """Unique identifier for this event instance."""
        pass

    @property
    @abstractmethod
    def event_type(self) -> str:
        """Type identifier for this event (e.g., 'user.points.awarded')."""
        pass

    @property
    @abstractmethod
    def timestamp(self) -> datetime:
        """When this event occurred."""
        pass

    @property
    @abstractmethod
    def source_service(self) -> str:
        """Service that generated this event."""
        pass

    @property
    @abstractmethod
    def correlation_id(self) -> Optional[str]:
        """Optional correlation ID for tracing related events."""
        pass

    @property
    @abstractmethod
    def priority(self) -> EventPriority:
        """Processing priority for this event."""
        pass

    @property
    @abstractmethod
    def payload(self) -> Dict[str, Any]:
        """Event-specific data payload."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary for persistence/transmission."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IEvent":
        """Deserialize event from dictionary."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate event data integrity."""
        pass


class IEventHandler(ABC, Generic[EventT]):
    """
    Base interface for event handlers.

    Event handlers are responsible for processing specific types of events.
    They should be stateless and idempotent where possible.
    """

    @property
    @abstractmethod
    def handler_id(self) -> str:
        """Unique identifier for this handler instance."""
        pass

    @property
    @abstractmethod
    def supported_event_types(self) -> List[str]:
        """List of event types this handler can process."""
        pass

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Name of the service this handler belongs to."""
        pass

    @abstractmethod
    async def handle(self, event: EventT) -> bool:
        """
        Process the given event.

        Args:
            event: The event to process

        Returns:
            True if handled successfully, False otherwise

        Raises:
            EventHandlingError: If processing fails critically
        """
        pass

    @abstractmethod
    async def can_handle(self, event: IEvent) -> bool:
        """
        Check if this handler can process the given event.

        Args:
            event: The event to check

        Returns:
            True if this handler can process the event
        """
        pass

    @abstractmethod
    async def on_error(self, event: EventT, error: Exception) -> bool:
        """
        Handle processing errors.

        Args:
            event: The event that failed processing
            error: The exception that occurred

        Returns:
            True if error was handled and processing should continue,
            False if event should be marked as failed
        """
        pass


class IEventBus(ABC):
    """
    Core interface for the Event Bus system.

    The Event Bus is the central nervous system that coordinates
    event publishing and subscription between all services.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the event bus and establish connections."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shutdown the event bus and clean up resources."""
        pass

    @abstractmethod
    async def publish(
        self, event: IEvent, target_services: Optional[List[str]] = None
    ) -> bool:
        """
        Publish an event to the bus.

        Args:
            event: The event to publish
            target_services: Optional list of specific services to target

        Returns:
            True if published successfully

        Raises:
            EventPublishError: If publishing fails
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        event_type: str,
        handler: IEventHandler,
        service_name: Optional[str] = None,
    ) -> str:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to
            handler: Handler to process the events
            service_name: Optional service name filter

        Returns:
            Subscription ID for managing the subscription

        Raises:
            EventSubscriptionError: If subscription fails
        """
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove a subscription.

        Args:
            subscription_id: ID of the subscription to remove

        Returns:
            True if unsubscribed successfully
        """
        pass

    @abstractmethod
    async def get_active_subscriptions(self) -> Dict[str, List[str]]:
        """
        Get all active subscriptions grouped by event type.

        Returns:
            Dictionary mapping event types to lists of subscription IDs
        """
        pass

    @abstractmethod
    async def get_subscription_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status of all subscriptions.

        Returns:
            Dictionary with subscription health metrics
        """
        pass


class IEventStore(ABC):
    """
    Interface for event persistence and replay functionality.

    The Event Store provides durability and enables event sourcing
    patterns for critical business events.
    """

    @abstractmethod
    async def store_event(self, event: IEvent) -> bool:
        """
        Persist an event to the store.

        Args:
            event: The event to store

        Returns:
            True if stored successfully
        """
        pass

    @abstractmethod
    async def get_events(
        self,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[IEvent]:
        """
        Retrieve events from the store.

        Args:
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return

        Returns:
            List of matching events
        """
        pass

    @abstractmethod
    async def replay_events(
        self, event_type: str, start_time: datetime, end_time: Optional[datetime] = None
    ) -> None:
        """
        Replay events by republishing them to the bus.

        Args:
            event_type: Type of events to replay
            start_time: Start time for replay
            end_time: Optional end time for replay
        """
        pass


class IEventMetrics(ABC):
    """
    Interface for event bus metrics and monitoring.

    Provides observability into event processing performance
    and system health.
    """

    @abstractmethod
    async def record_event_published(
        self, event_type: str, processing_time: float
    ) -> None:
        """Record successful event publication."""
        pass

    @abstractmethod
    async def record_event_processed(
        self, event_type: str, handler_id: str, processing_time: float, success: bool
    ) -> None:
        """Record event processing result."""
        pass

    @abstractmethod
    async def record_subscription_health(
        self, subscription_id: str, status: str, error_count: int
    ) -> None:
        """Record subscription health status."""
        pass

    @abstractmethod
    async def get_processing_metrics(self) -> Dict[str, Any]:
        """Get current processing performance metrics."""
        pass

    @abstractmethod
    async def get_error_metrics(self) -> Dict[str, Any]:
        """Get current error rate metrics."""
        pass


# Exception Classes for the Event Bus System
class EventBusError(Exception):
    """Base exception for Event Bus related errors."""

    def __init__(self, message: str, event_id: Optional[str] = None):
        super().__init__(message)
        self.event_id = event_id
        self.timestamp = datetime.utcnow()


class EventPublishError(EventBusError):
    """Raised when event publishing fails."""

    pass


class EventSubscriptionError(EventBusError):
    """Raised when event subscription fails."""

    pass


class EventHandlingError(EventBusError):
    """Raised when event handling fails."""

    def __init__(
        self,
        message: str,
        event_id: Optional[str] = None,
        handler_id: Optional[str] = None,
    ):
        super().__init__(message, event_id)
        self.handler_id = handler_id


class EventValidationError(EventBusError):
    """Raised when event validation fails."""

    pass


class EventSerializationError(EventBusError):
    """Raised when event serialization/deserialization fails."""

    pass


# Configuration and Settings
class EventBusConfig:
    """Configuration settings for the Event Bus."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        max_retry_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
        event_ttl_seconds: int = 86400,  # 24 hours
        max_concurrent_handlers: int = 100,
        health_check_interval_seconds: int = 30,
        metrics_enabled: bool = True,
        event_store_enabled: bool = True,
    ):
        self.redis_url = redis_url
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.event_ttl_seconds = event_ttl_seconds
        self.max_concurrent_handlers = max_concurrent_handlers
        self.health_check_interval_seconds = health_check_interval_seconds
        self.metrics_enabled = metrics_enabled
        self.event_store_enabled = event_store_enabled
