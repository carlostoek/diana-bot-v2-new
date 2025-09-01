from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class UserCreated:
    user_id: int
    first_name: str

@dataclass
class OnboardingStartedEvent:
    user_id: int
    timestamp: float

@dataclass
class UserRegisteredEvent:
    user_id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]

@dataclass
class UserActivityEvent:
    user_id: int
    action: str
    timestamp: float

@dataclass
class UserPreferencesUpdatedEvent:
    user_id: int
    preferences: Dict[str, Any]

@dataclass
class PersonalityDetectedEvent:
    user_id: int
    personality_type: str
    confidence: float

@dataclass
class UserCreatedEvent:
    user_id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]

@dataclass
class UserLoginEvent:
    user_id: int
    timestamp: float
