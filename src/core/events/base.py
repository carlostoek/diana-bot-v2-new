"""
Base Event Classes with Validation for Diana Bot V2.

This module provides the foundational event classes with robust validation,
serialization support, and proper type safety. All domain events inherit
from these base classes to ensure consistency across the system.
"""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from ..interfaces import EventPriority, EventValidationError, IEvent

# Type variable for generic event handling
EventT = TypeVar("EventT", bound="BaseEventWithValidation")


class EventCategory(Enum):
    """High-level categorization of events for routing and filtering."""

    GAMIFICATION = "gamification"
    NARRATIVE = "narrative"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"
    CORE = "core"


class ValidationLevel(Enum):
    """Validation strictness levels for different environments."""

    STRICT = "strict"  # Production: All validation rules enforced
    NORMAL = "normal"  # Development: Standard validation
    LENIENT = "lenient"  # Testing: Minimal validation for mocking


@dataclass(frozen=True)
class EventMetadata:
    """Metadata associated with an event for enhanced tracking and debugging."""

    created_at: datetime
    source_version: str = "1.0.0"
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "created_at": self.created_at.isoformat(),
            "source_version": self.source_version,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "request_id": self.request_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventMetadata":
        """Create metadata from dictionary representation."""
        return cls(
            created_at=datetime.fromisoformat(data["created_at"]),
            source_version=data.get("source_version", "1.0.0"),
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
            user_agent=data.get("user_agent"),
            ip_address=data.get("ip_address"),
            request_id=data.get("request_id"),
        )


class BaseEventWithValidation(IEvent, ABC):
    """
    Enhanced base event class with comprehensive validation and metadata support.

    This class provides:
    - Comprehensive field validation with different strictness levels
    - Enhanced metadata tracking for debugging and tracing
    - Consistent serialization/deserialization
    - Type-safe payload handling
    - Event lifecycle hooks for custom behavior
    """

    def __init__(
        self,
        event_id: Optional[str] = None,
        event_type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        source_service: str = "unknown",
        user_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[EventMetadata] = None,
        validation_level: ValidationLevel = ValidationLevel.NORMAL,
    ):
        """
        Initialize base event with validation.

        Args:
            event_id: Unique identifier (auto-generated if not provided)
            event_type: Type identifier for the event (auto-detected if not provided)
            timestamp: When event occurred (current time if not provided)
            source_service: Service that generated the event
            user_id: ID of user associated with this event (if applicable)
            correlation_id: ID for tracing related events
            priority: Processing priority
            payload: Event-specific data
            metadata: Additional metadata for tracking
            validation_level: How strict validation should be
        """
        self._event_id = event_id or str(uuid.uuid4())
        self._event_type = event_type or self._get_event_type()
        self._timestamp = timestamp or datetime.utcnow()
        self._source_service = source_service
        self._user_id = user_id
        self._correlation_id = correlation_id
        self._priority = priority
        self._payload = payload or {}
        self._metadata = metadata or EventMetadata(created_at=self._timestamp)
        self._validation_level = validation_level

        # Perform validation after initialization
        self._validate_event()

        # Call lifecycle hook
        self._on_event_created()

    # IEvent interface implementation
    @property
    def event_id(self) -> str:
        """Unique identifier for this event instance."""
        return self._event_id

    @property
    def event_type(self) -> str:
        """Type identifier for this event."""
        return self._event_type

    @property
    def timestamp(self) -> datetime:
        """When this event occurred."""
        return self._timestamp

    @property
    def source_service(self) -> str:
        """Service that generated this event."""
        return self._source_service

    @property
    def correlation_id(self) -> Optional[str]:
        """Optional correlation ID for tracing related events."""
        return self._correlation_id

    @property
    def priority(self) -> EventPriority:
        """Processing priority for this event."""
        return self._priority

    @property
    def payload(self) -> Dict[str, Any]:
        """Event-specific data payload."""
        return self._payload.copy()  # Return copy to maintain immutability

    # Additional properties specific to Diana Bot
    @property
    def user_id(self) -> Optional[int]:
        """ID of user associated with this event."""
        return self._user_id

    @property
    def metadata(self) -> EventMetadata:
        """Metadata associated with this event."""
        return self._metadata

    @property
    def category(self) -> EventCategory:
        """High-level category of this event."""
        return self._get_event_category()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary for persistence/transmission."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source_service": self.source_service,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "payload": self.payload,
            "metadata": self.metadata.to_dict(),
            "category": self.category.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEventWithValidation":
        """Deserialize event from dictionary."""
        try:
            metadata_data = data.get("metadata", {})
            if metadata_data:
                metadata = EventMetadata.from_dict(metadata_data)
            else:
                metadata = None

            return cls(
                event_id=data["event_id"],
                event_type=data["event_type"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                source_service=data["source_service"],
                user_id=data.get("user_id"),
                correlation_id=data.get("correlation_id"),
                priority=EventPriority(
                    data.get("priority", EventPriority.NORMAL.value)
                ),
                payload=data.get("payload", {}),
                metadata=metadata,
            )
        except (KeyError, ValueError, TypeError) as e:
            from ..interfaces import EventSerializationError

            raise EventSerializationError(f"Failed to deserialize event: {str(e)}")

    def validate(self) -> bool:
        """Validate event data integrity (IEvent interface)."""
        return self._validate_event()

    def _validate_event(self) -> bool:
        """
        Comprehensive event validation with different strictness levels.

        Returns:
            True if validation passes

        Raises:
            EventValidationError: If validation fails
        """
        errors = []

        # Always validate critical fields
        if not self.event_id or not isinstance(self.event_id, str):
            errors.append("Event ID must be a non-empty string")

        if not self.event_type or not isinstance(self.event_type, str):
            errors.append("Event type must be a non-empty string")

        if not isinstance(self.timestamp, datetime):
            errors.append("Timestamp must be a datetime object")

        if not self.source_service or not isinstance(self.source_service, str):
            errors.append("Source service must be a non-empty string")

        # Validation based on strictness level
        if self._validation_level == ValidationLevel.STRICT:
            self._strict_validation(errors)
        elif self._validation_level == ValidationLevel.NORMAL:
            self._normal_validation(errors)
        # LENIENT: Only basic validation above

        # Custom validation hook
        self._custom_validation(errors)

        if errors:
            error_msg = "; ".join(errors)
            raise EventValidationError(f"Event validation failed: {error_msg}")

        return True

    def _strict_validation(self, errors: List[str]) -> None:
        """Strict validation for production environments."""
        if not isinstance(self.payload, dict):
            errors.append("Payload must be a dictionary")

        if self.user_id is not None and (
            not isinstance(self.user_id, int) or self.user_id <= 0
        ):
            errors.append("User ID must be a positive integer")

        if self.correlation_id is not None and not isinstance(self.correlation_id, str):
            errors.append("Correlation ID must be a string")

        # Timestamp should be recent (within 1 hour) in strict mode
        age = datetime.utcnow() - self.timestamp
        if age.total_seconds() > 3600:  # 1 hour
            errors.append("Event timestamp is too old (>1 hour)")

        # Payload size limit in strict mode
        payload_str = json.dumps(self.payload)
        if len(payload_str) > 10 * 1024:  # 10KB limit
            errors.append("Payload size exceeds 10KB limit")

    def _normal_validation(self, errors: List[str]) -> None:
        """Normal validation for development environments."""
        if not isinstance(self.payload, dict):
            errors.append("Payload must be a dictionary")

        if self.user_id is not None and not isinstance(self.user_id, int):
            errors.append("User ID must be an integer")

    def _custom_validation(self, errors: List[str]) -> None:
        """
        Custom validation hook for subclasses.

        Subclasses can override this method to add domain-specific validation.

        Args:
            errors: List to append validation errors to
        """
        pass

    def _get_event_type(self) -> str:
        """
        Auto-detect event type from class name.

        Subclasses should override this if they need custom event type detection.
        """
        class_name = self.__class__.__name__
        # Convert from CamelCase to snake_case
        import re

        snake_case = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", class_name)
        snake_case = re.sub("([a-z0-9])([A-Z])", r"\1_\2", snake_case).lower()

        # Remove 'event' suffix if present
        if snake_case.endswith("_event"):
            snake_case = snake_case[:-6]

        # Add category prefix
        category = self._get_event_category()
        return f"{category.value}.{snake_case}"

    @abstractmethod
    def _get_event_category(self) -> EventCategory:
        """
        Get the high-level category for this event type.

        Subclasses must implement this to specify their category.
        """
        pass

    def _on_event_created(self) -> None:
        """
        Lifecycle hook called after event creation and validation.

        Subclasses can override this for custom initialization logic.
        """
        pass

    def __str__(self) -> str:
        """String representation of the event."""
        return f"{self.event_type}[{self.event_id}] at {self.timestamp} from {self.source_service}"

    def __repr__(self) -> str:
        """Developer-friendly representation of the event."""
        return (
            f"{self.__class__.__name__}("
            f"event_id='{self.event_id}', "
            f"event_type='{self.event_type}', "
            f"user_id={self.user_id}, "
            f"source_service='{self.source_service}'"
            f")"
        )


class DomainEvent(BaseEventWithValidation, ABC):
    """
    Base class for domain events that represent business occurrences.

    Domain events are the primary way services communicate business state changes.
    They should be immutable and contain all information necessary for other
    services to react appropriately.
    """

    def __init__(
        self,
        user_id: int,
        source_service: str,
        event_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize domain event.

        Args:
            user_id: ID of the user this event relates to
            source_service: Service generating the event
            event_id: Unique identifier (auto-generated if not provided)
            correlation_id: Correlation ID for tracing
            priority: Processing priority
            payload: Event-specific data
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(
            event_id=event_id,
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs,
        )

    def _custom_validation(self, errors: List[str]) -> None:
        """Domain events require a user ID."""
        if self.user_id is None:
            errors.append("Domain events must have a user_id")


class SystemEvent(BaseEventWithValidation):
    """
    Base class for system-level events (health, monitoring, etc.).

    System events are used for operational concerns like service health,
    monitoring, logging, and administrative operations.
    """

    def __init__(
        self,
        source_service: str,
        system_component: str,
        event_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize system event.

        Args:
            source_service: Service generating the event
            system_component: Component/subsystem generating the event
            event_id: Unique identifier (auto-generated if not provided)
            correlation_id: Correlation ID for tracing
            priority: Processing priority
            payload: Event-specific data
            **kwargs: Additional arguments passed to base class
        """
        payload = payload or {}
        payload["system_component"] = system_component

        super().__init__(
            event_id=event_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs,
        )

    @property
    def system_component(self) -> str:
        """The system component that generated this event."""
        return self.payload["system_component"]

    def _get_event_category(self) -> EventCategory:
        """System events belong to the SYSTEM category."""
        return EventCategory.SYSTEM


class IntegrationEvent(BaseEventWithValidation):
    """
    Base class for integration events that cross service boundaries.

    Integration events are used when services need to notify external
    systems or when events need to be processed by multiple services
    with different timing requirements.
    """

    def __init__(
        self,
        source_service: str,
        target_services: Optional[List[str]] = None,
        event_id: Optional[str] = None,
        user_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        priority: EventPriority = EventPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize integration event.

        Args:
            source_service: Service generating the event
            target_services: Specific services that should receive this event
            event_id: Unique identifier (auto-generated if not provided)
            user_id: ID of user this event relates to (if applicable)
            correlation_id: Correlation ID for tracing
            priority: Processing priority
            payload: Event-specific data
            **kwargs: Additional arguments passed to base class
        """
        payload = payload or {}
        payload["target_services"] = target_services or []

        super().__init__(
            event_id=event_id,
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs,
        )

    @property
    def target_services(self) -> List[str]:
        """List of services that should receive this event."""
        return self.payload.get("target_services", [])

    def _get_event_category(self) -> EventCategory:
        """Integration events belong to the CORE category by default."""
        return EventCategory.CORE
