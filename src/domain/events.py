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
