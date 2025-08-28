"""User Module Events - Minimal Implementation.

This module contains essential user events for Diana Bot V2 MVP
following Event-Driven Architecture patterns.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.core.interfaces import IEvent


class BaseUserEvent(IEvent):
    """Base class for user events."""

    def __init__(
        self,
        user_id: int,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.user_id = user_id
        self._event_id = event_id or str(uuid.uuid4())
        self._timestamp = timestamp or datetime.now(timezone.utc)

    @property
    def event_id(self) -> str:
        return self._event_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def aggregate_id(self) -> str:
        return str(self.user_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        result = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
        }

        # Add other fields
        for key, value in self.__dict__.items():
            if key not in result:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value

        return result


class UserRegisteredEvent(BaseUserEvent):
    """Event published when a new user registers."""

    def __init__(
        self,
        user_id: int,
        first_name: str,
        username: Optional[str] = None,
        language_code: str = "es",
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.first_name = first_name
        self.username = username
        self.language_code = language_code

        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValueError("user_id must be positive")
        if not self.first_name.strip():
            raise ValueError("first_name cannot be empty")

    @property
    def event_type(self) -> str:
        return "user.registered"


class UserPreferencesUpdatedEvent(BaseUserEvent):
    """Event published when user preferences are updated."""

    def __init__(
        self,
        user_id: int,
        preferences: Dict[str, Any],
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.preferences = preferences

    @property
    def event_type(self) -> str:
        return "user.preferences_updated"


class UserActivityEvent(BaseUserEvent):
    """Event published when user performs activities."""

    def __init__(
        self,
        user_id: int,
        activity_type: str,
        activity_data: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.activity_type = activity_type
        self.activity_data = activity_data or {}

    @property
    def event_type(self) -> str:
        return "user.activity"