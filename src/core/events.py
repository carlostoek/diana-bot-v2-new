"""
Concrete Event implementations for Diana Bot V2.

This module provides backward compatibility with the original event structure
while integrating with the new enhanced event contracts system.

DEPRECATED: Use the new events package (src.core.events.*) for new implementations.
This module is maintained for backward compatibility with existing code.
"""

import json
import uuid
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from .interfaces import (
    EventPriority,
    EventSerializationError,
    EventStatus,
    EventValidationError,
    IEvent,
)

# Dynamic imports to avoid circular dependencies
# These will be loaded on-demand when needed


# Deprecation warning helper
def _deprecation_warning(old_class_name: str, new_class_name: str):
    """Issue deprecation warning for old event classes."""
    warnings.warn(
        f"{old_class_name} is deprecated. Use {new_class_name} from src.core.events instead.",
        DeprecationWarning,
        stacklevel=3,
    )


class EventType:
    """Constants for all event types in the system."""

    # Gamification Events
    POINTS_AWARDED = "gamification.points.awarded"
    POINTS_DEDUCTED = "gamification.points.deducted"
    ACHIEVEMENT_UNLOCKED = "gamification.achievement.unlocked"
    STREAK_UPDATED = "gamification.streak.updated"
    LEADERBOARD_UPDATED = "gamification.leaderboard.updated"

    # Narrative Events
    STORY_CHAPTER_STARTED = "narrative.chapter.started"
    STORY_CHAPTER_COMPLETED = "narrative.chapter.completed"
    STORY_DECISION_MADE = "narrative.decision.made"
    CHARACTER_INTERACTION = "narrative.character.interaction"
    STORY_PROGRESS_UPDATED = "narrative.progress.updated"

    # User Events
    USER_REGISTERED = "user.registered"
    USER_PROFILE_UPDATED = "user.profile.updated"
    USER_SUBSCRIPTION_CHANGED = "user.subscription.changed"
    USER_ACTIVITY_DETECTED = "user.activity.detected"

    # Admin Events
    ADMIN_ACTION_PERFORMED = "admin.action.performed"
    USER_MODERATED = "admin.user.moderated"
    CONTENT_MODERATED = "admin.content.moderated"
    SYSTEM_CONFIGURATION_CHANGED = "admin.config.changed"

    # System Events
    SERVICE_STARTED = "system.service.started"
    SERVICE_STOPPED = "system.service.stopped"
    HEALTH_CHECK_FAILED = "system.health.failed"
    ERROR_OCCURRED = "system.error.occurred"


@dataclass
class BaseEvent(IEvent):
    """
    Base implementation of IEvent interface.

    Provides common functionality for all event types while maintaining
    immutability and type safety.
    """

    _event_id: str
    _event_type: str
    _timestamp: datetime
    _source_service: str
    _correlation_id: Optional[str] = None
    _priority: EventPriority = EventPriority.NORMAL
    _payload: Dict[str, Any] = None

    def __post_init__(self):
        """Post-initialization validation and setup."""
        if self._payload is None:
            self._payload = {}
        self.validate()

    @property
    def event_id(self) -> str:
        return self._event_id

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def source_service(self) -> str:
        return self._source_service

    @property
    def correlation_id(self) -> Optional[str]:
        return self._correlation_id

    @property
    def priority(self) -> EventPriority:
        return self._priority

    @property
    def payload(self) -> Dict[str, Any]:
        return self._payload.copy()  # Return copy to maintain immutability

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source_service": self.source_service,
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEvent":
        """Deserialize event from dictionary."""
        try:
            return cls(
                _event_id=data["event_id"],
                _event_type=data["event_type"],
                _timestamp=datetime.fromisoformat(data["timestamp"]),
                _source_service=data["source_service"],
                _correlation_id=data.get("correlation_id"),
                _priority=EventPriority(
                    data.get("priority", EventPriority.NORMAL.value)
                ),
                _payload=data.get("payload", {}),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise EventSerializationError(f"Failed to deserialize event: {str(e)}")

    def validate(self) -> bool:
        """Validate event data integrity."""
        if not self.event_id or not isinstance(self.event_id, str):
            raise EventValidationError("Event ID must be a non-empty string")

        if not self.event_type or not isinstance(self.event_type, str):
            raise EventValidationError("Event type must be a non-empty string")

        if not isinstance(self.timestamp, datetime):
            raise EventValidationError("Timestamp must be a datetime object")

        if not self.source_service or not isinstance(self.source_service, str):
            raise EventValidationError("Source service must be a non-empty string")

        if not isinstance(self.payload, dict):
            raise EventValidationError("Payload must be a dictionary")

        return True


# Gamification Events
@dataclass
class PointsAwardedEvent(BaseEvent):
    """Event fired when points are awarded to a user."""

    def __init__(
        self,
        user_id: int,
        points_amount: int,
        action_type: str,
        multiplier: float = 1.0,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "user_id": user_id,
            "points_amount": points_amount,
            "action_type": action_type,
            "multiplier": multiplier,
            "total_points_after": None,  # Will be set by the gamification service
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.POINTS_AWARDED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.NORMAL,
            _payload=payload,
        )

    @property
    def user_id(self) -> int:
        return self.payload["user_id"]

    @property
    def points_amount(self) -> int:
        return self.payload["points_amount"]

    @property
    def action_type(self) -> str:
        return self.payload["action_type"]

    @property
    def multiplier(self) -> float:
        return self.payload["multiplier"]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PointsAwardedEvent":
        """Deserialize PointsAwardedEvent from dictionary."""
        try:
            payload = data.get("payload", {})
            event = cls(
                user_id=payload["user_id"],
                points_amount=payload["points_amount"],
                action_type=payload["action_type"],
                multiplier=payload.get("multiplier", 1.0),
                source_service=data["source_service"],
                correlation_id=data.get("correlation_id"),
            )
            # Override the auto-generated values with stored ones
            event._event_id = data["event_id"]
            event._timestamp = datetime.fromisoformat(data["timestamp"])
            event._priority = EventPriority(
                data.get("priority", EventPriority.NORMAL.value)
            )
            return event
        except (KeyError, ValueError, TypeError) as e:
            raise EventSerializationError(
                f"Failed to deserialize PointsAwardedEvent: {str(e)}"
            )


@dataclass
class AchievementUnlockedEvent(BaseEvent):
    """Event fired when a user unlocks an achievement."""

    def __init__(
        self,
        user_id: int,
        achievement_id: str,
        achievement_name: str,
        achievement_category: str,
        points_reward: int = 0,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "user_id": user_id,
            "achievement_id": achievement_id,
            "achievement_name": achievement_name,
            "achievement_category": achievement_category,
            "points_reward": points_reward,
            "unlock_timestamp": datetime.utcnow().isoformat(),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.ACHIEVEMENT_UNLOCKED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.HIGH,
            _payload=payload,
        )

    @property
    def user_id(self) -> int:
        return self.payload["user_id"]

    @property
    def achievement_id(self) -> str:
        return self.payload["achievement_id"]

    @property
    def achievement_name(self) -> str:
        return self.payload["achievement_name"]


@dataclass
class StreakUpdatedEvent(BaseEvent):
    """Event fired when a user's streak is updated."""

    def __init__(
        self,
        user_id: int,
        previous_streak: int,
        current_streak: int,
        streak_type: str,
        is_broken: bool = False,
        source_service: str = "gamification",
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "user_id": user_id,
            "previous_streak": previous_streak,
            "current_streak": current_streak,
            "streak_type": streak_type,
            "is_broken": is_broken,
            "streak_bonus_earned": (
                max(0, current_streak - previous_streak) if not is_broken else 0
            ),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.STREAK_UPDATED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.NORMAL,
            _payload=payload,
        )


# Narrative Events
@dataclass
class StoryChapterStartedEvent(BaseEvent):
    """Event fired when a user starts a new story chapter."""

    def __init__(
        self,
        user_id: int,
        chapter_id: str,
        chapter_title: str,
        story_arc: str,
        source_service: str = "narrative",
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "user_id": user_id,
            "chapter_id": chapter_id,
            "chapter_title": chapter_title,
            "story_arc": story_arc,
            "started_at": datetime.utcnow().isoformat(),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.STORY_CHAPTER_STARTED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.NORMAL,
            _payload=payload,
        )


@dataclass
class StoryDecisionMadeEvent(BaseEvent):
    """Event fired when a user makes a story decision."""

    def __init__(
        self,
        user_id: int,
        chapter_id: str,
        decision_id: str,
        decision_text: str,
        consequences: Dict[str, Any],
        character_impacts: Dict[str, Any],
        source_service: str = "narrative",
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "user_id": user_id,
            "chapter_id": chapter_id,
            "decision_id": decision_id,
            "decision_text": decision_text,
            "consequences": consequences,
            "character_impacts": character_impacts,
            "decision_timestamp": datetime.utcnow().isoformat(),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.STORY_DECISION_MADE,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.HIGH,
            _payload=payload,
        )


# User Events
@dataclass
class UserRegisteredEvent(BaseEvent):
    """Event fired when a new user registers."""

    def __init__(
        self,
        user_id: int,
        username: Optional[str],
        first_name: Optional[str],
        language_code: str,
        is_premium: bool = False,
        source_service: str = "telegram_adapter",
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "language_code": language_code,
            "is_premium": is_premium,
            "registration_timestamp": datetime.utcnow().isoformat(),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.USER_REGISTERED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.HIGH,
            _payload=payload,
        )


@dataclass
class UserSubscriptionChangedEvent(BaseEvent):
    """Event fired when a user's subscription status changes."""

    def __init__(
        self,
        user_id: int,
        previous_plan: str,
        new_plan: str,
        subscription_id: str,
        payment_provider: str,
        source_service: str = "monetization",
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "user_id": user_id,
            "previous_plan": previous_plan,
            "new_plan": new_plan,
            "subscription_id": subscription_id,
            "payment_provider": payment_provider,
            "change_timestamp": datetime.utcnow().isoformat(),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.USER_SUBSCRIPTION_CHANGED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.HIGH,
            _payload=payload,
        )


# Admin Events
@dataclass
class AdminActionPerformedEvent(BaseEvent):
    """Event fired when an admin performs an action."""

    def __init__(
        self,
        admin_user_id: int,
        action_type: str,
        target_user_id: Optional[int],
        action_details: Dict[str, Any],
        source_service: str = "admin",
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "admin_user_id": admin_user_id,
            "action_type": action_type,
            "target_user_id": target_user_id,
            "action_details": action_details,
            "admin_timestamp": datetime.utcnow().isoformat(),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.ADMIN_ACTION_PERFORMED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.CRITICAL,
            _payload=payload,
        )


# System Events
@dataclass
class ServiceStartedEvent(BaseEvent):
    """Event fired when a service starts up."""

    def __init__(
        self,
        service_name: str,
        service_version: str,
        startup_time_ms: float,
        source_service: str,
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "service_name": service_name,
            "service_version": service_version,
            "startup_time_ms": startup_time_ms,
            "startup_timestamp": datetime.utcnow().isoformat(),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.SERVICE_STARTED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.NORMAL,
            _payload=payload,
        )


@dataclass
class ErrorOccurredEvent(BaseEvent):
    """Event fired when a system error occurs."""

    def __init__(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str],
        user_id: Optional[int],
        source_service: str,
        correlation_id: Optional[str] = None,
    ):
        payload = {
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "user_id": user_id,
            "error_timestamp": datetime.utcnow().isoformat(),
        }

        super().__init__(
            _event_id=str(uuid.uuid4()),
            _event_type=EventType.ERROR_OCCURRED,
            _timestamp=datetime.utcnow(),
            _source_service=source_service,
            _correlation_id=correlation_id,
            _priority=EventPriority.CRITICAL,
            _payload=payload,
        )


# Event Factory for Dynamic Event Creation
class EventFactory:
    """
    Factory for creating events dynamically.

    Provides type-safe event creation and validation.
    """

    _event_types: Dict[str, Type[BaseEvent]] = {
        EventType.POINTS_AWARDED: PointsAwardedEvent,
        EventType.ACHIEVEMENT_UNLOCKED: AchievementUnlockedEvent,
        EventType.STREAK_UPDATED: StreakUpdatedEvent,
        EventType.STORY_CHAPTER_STARTED: StoryChapterStartedEvent,
        EventType.STORY_DECISION_MADE: StoryDecisionMadeEvent,
        EventType.USER_REGISTERED: UserRegisteredEvent,
        EventType.USER_SUBSCRIPTION_CHANGED: UserSubscriptionChangedEvent,
        EventType.ADMIN_ACTION_PERFORMED: AdminActionPerformedEvent,
        EventType.SERVICE_STARTED: ServiceStartedEvent,
        EventType.ERROR_OCCURRED: ErrorOccurredEvent,
    }

    @classmethod
    def create_event(cls, event_type: str, **kwargs) -> BaseEvent:
        """
        Create an event of the specified type.

        Args:
            event_type: The type of event to create
            **kwargs: Event-specific parameters

        Returns:
            The created event instance

        Raises:
            ValueError: If event type is not supported
        """
        if event_type not in cls._event_types:
            raise ValueError(f"Unsupported event type: {event_type}")

        event_class = cls._event_types[event_type]
        return event_class(**kwargs)

    @classmethod
    def register_event_type(cls, event_type: str, event_class: Type[BaseEvent]) -> None:
        """
        Register a new event type.

        Args:
            event_type: The event type identifier
            event_class: The event class to register
        """
        cls._event_types[event_type] = event_class

    @classmethod
    def get_supported_event_types(cls) -> List[str]:
        """Get list of all supported event types."""
        return list(cls._event_types.keys())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseEvent:
        """
        Create an event from a dictionary representation.

        Args:
            data: Dictionary containing event data

        Returns:
            The deserialized event instance
        """
        event_type = data.get("event_type")
        if event_type in cls._event_types:
            return cls._event_types[event_type].from_dict(data)
        else:
            # Try to use new event system first
            try:
                from .events.catalog import event_catalog

                route = event_catalog.get_route_by_event_type(event_type)
                if route:
                    return route.event_class.from_dict(data)
            except Exception:
                pass

            # Fallback to BaseEvent for unknown types
            return BaseEvent.from_dict(data)


# Compatibility Wrappers for Backward Compatibility
# These provide the same interface as the old events but delegate to new implementations


class PointsAwardedEventCompat(PointsAwardedEvent):
    """Backward compatibility wrapper for PointsAwardedEvent."""

    def __init__(self, *args, **kwargs):
        _deprecation_warning("PointsAwardedEvent", "NewPointsAwardedEvent")
        super().__init__(*args, **kwargs)


class AchievementUnlockedEventCompat(AchievementUnlockedEvent):
    """Backward compatibility wrapper for AchievementUnlockedEvent."""

    def __init__(self, *args, **kwargs):
        _deprecation_warning("AchievementUnlockedEvent", "NewAchievementUnlockedEvent")
        super().__init__(*args, **kwargs)


class UserRegisteredEventCompat(UserRegisteredEvent):
    """Backward compatibility wrapper for UserRegisteredEvent."""

    def __init__(self, *args, **kwargs):
        _deprecation_warning("UserRegisteredEvent", "NewUserRegisteredEvent")
        super().__init__(*args, **kwargs)


class ServiceStartedEventCompat(ServiceStartedEvent):
    """Backward compatibility wrapper for ServiceStartedEvent."""

    def __init__(self, *args, **kwargs):
        _deprecation_warning("ServiceStartedEvent", "NewServiceStartedEvent")
        super().__init__(*args, **kwargs)


# Enhanced EventFactory with new system integration
class EnhancedEventFactory(EventFactory):
    """
    Enhanced Event Factory that bridges old and new event systems.

    This factory tries to use the new event system when possible,
    falling back to the legacy system for backward compatibility.
    """

    @classmethod
    def create_event(cls, event_type: str, **kwargs) -> BaseEvent:
        """Create event using new system if available, fallback to legacy."""
        # Try new system first
        try:
            from .events.catalog import event_catalog

            route = event_catalog.get_route_by_event_type(event_type)
            if route:
                # Map legacy parameters to new event format if needed
                mapped_kwargs = cls._map_legacy_params(event_type, kwargs)
                return route.event_class(**mapped_kwargs)
        except Exception:
            pass

        # Fallback to legacy system
        return super().create_event(event_type, **kwargs)

    @classmethod
    def _map_legacy_params(
        cls, event_type: str, kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map legacy parameter names to new event system parameters."""
        mapped = kwargs.copy()

        # Common mapping for user_id requirement in new domain events
        if event_type.startswith(("gamification.", "narrative.")):
            if "user_id" not in mapped and "payload" in mapped:
                payload = mapped["payload"]
                if isinstance(payload, dict) and "user_id" in payload:
                    mapped["user_id"] = payload["user_id"]

        return mapped


# Update the global EventFactory to use enhanced version
EventFactory = EnhancedEventFactory

# Export compatibility aliases for existing code
CompatPointsAwardedEvent = PointsAwardedEventCompat
CompatAchievementUnlockedEvent = AchievementUnlockedEventCompat
CompatUserRegisteredEvent = UserRegisteredEventCompat
CompatServiceStartedEvent = ServiceStartedEventCompat

# Note: New events should be imported directly from their respective modules
# Example: from src.core.events.gamification import PointsAwardedEvent
# This avoids circular import issues and makes imports explicit
