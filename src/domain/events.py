import uuid
from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field


class Event(BaseModel):
    """
    Base class for all events in the system.
    """
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_name: str
    payload: Dict[str, Any]

    class Config:
        frozen = True


class UserRegistered(Event):
    """
    Event published when a new user is registered.
    """
    event_name: str = "user_registered"
    payload: Dict[str, Any]  # e.g., {"user_id": 123, "username": "test"}


class AchievementUnlocked(Event):
    """
    Event published when a user unlocks an achievement.
    """
    event_name: str = "achievement_unlocked"
    payload: Dict[str, Any]  # e.g., {"user_id": 123, "achievement_name": "First Steps"}
