"""
Event Bus Core Interfaces

This module defines the abstract base classes that establish the contracts
for the Diana Bot V2 Event Bus system. These interfaces enable loose coupling
between components while providing strong type safety and clear behavioral contracts.

Architecture Overview:
- IEvent: Abstract base for all events with serialization, validation
- IEventBus: Abstract pub/sub interface for event distribution
- IEventHandler: Abstract callback interface for event processing

Performance Requirements:
- Event publishing: <10ms for 95th percentile
- Event subscription: <1ms for 95th percentile
- Memory efficient with proper cleanup

Security Requirements:
- Event validation to prevent malicious payloads
- Data size limits to prevent DoS attacks
- Proper serialization safety
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union


class IEvent(ABC):
    """
    Abstract base class for all events in the Diana Bot V2 system.

    Defines the core interface that all events must implement, including:
    - Event lifecycle (creation, validation, serialization)
    - Metadata management (ID, timestamp, correlation)
    - Type safety and validation
    - Serialization to/from dict and JSON

    All concrete event types must inherit from this interface.
    """

    def __init__(
        self,
        id: Optional[str] = None,
        type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        source: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize an event with core metadata.

        Args:
            id: Unique event identifier (auto-generated if None)
            type: Event type string (must follow namespace.action format) - REQUIRED
            timestamp: Event timestamp (auto-generated as UTC if None)
            data: Event payload data (must be JSON serializable) - REQUIRED
            correlation_id: Optional correlation ID for tracing related events
            source: Optional source system/service identifier
            **kwargs: Additional event-specific fields

        Raises:
            TypeError: If required fields are wrong type
            ValueError: If fields fail validation
        """
        # Validate required fields
        if type is None:
            raise TypeError("Event type is required")
        if data is None:
            raise TypeError("Event data is required")

        # Auto-generate ID if not provided
        self._id = id or str(uuid.uuid4())

        # Auto-generate timestamp if not provided
        if timestamp is None:
            self._timestamp = datetime.now(timezone.utc)
        else:
            # Validate timestamp type before processing
            if not isinstance(timestamp, datetime):
                raise TypeError("timestamp must be a datetime object")

            # Ensure timezone-aware datetime
            if timestamp.tzinfo is None:
                self._timestamp = timestamp.replace(tzinfo=timezone.utc)
            else:
                self._timestamp = timestamp

        self._type = type
        self._data = data
        self._correlation_id = correlation_id
        self._source = source

        # Validate the event
        self.validate()

    @property
    def id(self) -> str:
        """Event unique identifier."""
        return self._id

    @property
    def type(self) -> str:
        """Event type in namespace.action format."""
        return self._type

    @property
    def timestamp(self) -> datetime:
        """Event timestamp (timezone-aware)."""
        return self._timestamp

    @property
    def data(self) -> Dict[str, Any]:
        """Event payload data."""
        return self._data

    @property
    def correlation_id(self) -> Optional[str]:
        """Correlation ID for tracing related events."""
        return self._correlation_id

    @property
    def source(self) -> Optional[str]:
        """Source system/service identifier."""
        return self._source

    def validate(self) -> None:
        """
        Validate event data and structure.

        Raises:
            TypeError: If fields have wrong types
            ValueError: If fields fail validation rules
        """
        # Validate ID
        if not isinstance(self._id, str) or not self._id:
            raise TypeError("Event ID must be a non-empty string")

        # Validate type format (namespace.action)
        if not isinstance(self._type, str):
            raise TypeError("Event type must be a string")

        if not self._type or "." not in self._type:
            raise ValueError("Event type must follow 'namespace.action' format")

        parts = self._type.split(".")
        if len(parts) != 2 or not all(parts):
            raise ValueError(
                "Event type must have exactly one dot separating namespace and action"
            )

        # Validate type doesn't contain invalid characters
        if any(char in self._type for char in [" ", "\t", "\n", "\r"]):
            raise ValueError("Event type cannot contain whitespace")

        if self._type.startswith(".") or self._type.endswith(".") or ".." in self._type:
            raise ValueError("Event type format is invalid")

        # Validate timestamp
        if not isinstance(self._timestamp, datetime):
            raise TypeError("Event timestamp must be a datetime object")

        # Validate data is serializable
        if not isinstance(self._data, dict):
            raise TypeError("Event data must be a dictionary")

        try:
            json.dumps(self._data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Event data must be JSON serializable: {e}")

        # Validate data size (prevent DoS attacks)
        data_size = len(json.dumps(self._data))
        if data_size > 1024 * 1024:  # 1MB limit
            raise ValueError(f"Event data too large: {data_size} bytes (max 1MB)")

        # Validate optional fields
        if self._correlation_id is not None and not isinstance(
            self._correlation_id, str
        ):
            raise TypeError("Correlation ID must be a string")

        if self._source is not None and not isinstance(self._source, str):
            raise TypeError("Source must be a string")

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize event to dictionary.

        Returns:
            Dictionary representation of the event
        """
        result = {
            "id": self._id,
            "type": self._type,
            "timestamp": self._timestamp.isoformat(),
            "data": self._data,
        }

        if self._correlation_id is not None:
            result["correlation_id"] = self._correlation_id

        if self._source is not None:
            result["source"] = self._source

        return result

    def to_json(self) -> str:
        """
        Serialize event to JSON string.

        Returns:
            JSON string representation of the event
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IEvent":
        """
        Create event from dictionary.

        Args:
            data: Dictionary containing event data

        Returns:
            Event instance reconstructed from dictionary
        """
        timestamp_str = data.get("timestamp")
        timestamp = None
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            type=data.get("type"),
            timestamp=timestamp,
            data=data.get("data", {}),
            correlation_id=data.get("correlation_id"),
            source=data.get("source"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "IEvent":
        """
        Create event from JSON string.

        Args:
            json_str: JSON string containing event data

        Returns:
            Event instance reconstructed from JSON
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __eq__(self, other: object) -> bool:
        """
        Check event equality based on ID.

        Args:
            other: Object to compare with

        Returns:
            True if events have same ID, False otherwise
        """
        if not isinstance(other, IEvent):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """
        Hash event based on ID for use in sets/dicts.

        Returns:
            Hash value based on event ID
        """
        return hash(self._id)

    def __str__(self) -> str:
        """
        String representation for debugging.

        Returns:
            Human-readable string representation
        """
        return f"Event(id={self._id}, type={self._type})"

    def __repr__(self) -> str:
        """
        Detailed string representation for debugging.

        Returns:
            Detailed string representation
        """
        return f"IEvent(id='{self._id}', type='{self._type}', timestamp='{self._timestamp.isoformat()}')"


class IEventHandler(ABC):
    """
    Abstract interface for event handlers.

    Event handlers are async callables that process events. This interface
    provides the contract for how handlers should behave, including error
    handling and timeout management.
    """

    @abstractmethod
    async def __call__(self, event: IEvent) -> None:
        """
        Process an event.

        Args:
            event: Event to process

        Raises:
            Exception: Any processing errors (will be caught by EventBus)
        """
        pass


class IEventBus(ABC):
    """
    Abstract interface for event bus implementations.

    Defines the core pub/sub functionality that all event bus implementations
    must provide:
    - Publishing events to subscribers
    - Managing subscriptions and handlers
    - Event filtering and routing
    - Error handling and resilience
    - Performance monitoring and health checks

    This interface enables different implementations (Redis, in-memory, etc.)
    while maintaining consistent behavior.
    """

    @abstractmethod
    async def publish(self, event: IEvent) -> None:
        """
        Publish an event to all subscribers.

        Events are routed to subscribers based on event type matching.
        Publishing should complete within 10ms for 95th percentile.

        Args:
            event: Event to publish

        Raises:
            PublishError: If publishing fails
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        event_type: str,
        handler: Union[IEventHandler, Callable[[IEvent], Awaitable[None]]],
    ) -> None:
        """
        Subscribe a handler to events of specified type.

        Supports exact matching and wildcard patterns:
        - "game.points_earned" - exact match
        - "game.*" - wildcard match for all game events

        Subscription should complete within 1ms for 95th percentile.

        Args:
            event_type: Event type to subscribe to (supports wildcards)
            handler: Async handler function or IEventHandler instance

        Raises:
            SubscribeError: If subscription fails
            TypeError: If handler is not callable
            ValueError: If event_type is invalid
        """
        pass

    @abstractmethod
    async def unsubscribe(
        self,
        event_type: str,
        handler: Union[IEventHandler, Callable[[IEvent], Awaitable[None]]],
    ) -> None:
        """
        Unsubscribe a handler from events of specified type.

        Removes the handler from receiving events of the specified type.
        Should handle gracefully if subscription doesn't exist.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove
        """
        pass

    @abstractmethod
    async def get_published_events(
        self,
        limit: int = 100,
        event_types: Optional[List[str]] = None,
        since: Optional[datetime] = None,
    ) -> List[IEvent]:
        """
        Retrieve recently published events for audit/replay.

        Args:
            limit: Maximum number of events to return
            event_types: Filter by specific event types (None for all)
            since: Only return events after this timestamp

        Returns:
            List of events matching criteria
        """
        pass

    @abstractmethod
    async def replay_events(
        self,
        event_types: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        target_handlers: Optional[List[Union[IEventHandler, Callable]]] = None,
    ) -> None:
        """
        Replay historical events to current subscribers or specific handlers.

        Useful for new subscribers that need to catch up on missed events
        or for recovering from failures.

        Args:
            event_types: Event types to replay (None for all)
            since: Only replay events after this timestamp
            target_handlers: Specific handlers to replay to (None for all subscribers)
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Get health status of the event bus.

        Returns:
            Dictionary containing health information:
            - status: "healthy", "degraded", or "unhealthy"
            - subscribers_count: Number of active subscriptions
            - events_published: Total events published
            - memory_usage: Memory usage information
            - last_publish_time: Timestamp of last event
        """
        pass

    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get operational statistics and metrics.

        Returns:
            Dictionary containing operational metrics:
            - total_events_published: Count of published events
            - total_subscribers: Count of active subscribers
            - events_by_type: Breakdown of events by type
            - avg_publish_time_ms: Average publish latency
            - avg_handler_time_ms: Average handler execution time
        """
        pass
