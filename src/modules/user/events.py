"""
User Module Events.

This module contains all domain events for the User Module following Event-Driven Architecture
patterns and supporting complete Diana Bot V2 business requirements including onboarding workflows,
personality detection, and Diana Master System integration.

Business Requirements Coverage:
- US-001: Primer Contacto Personalizado (onboarding events)
- US-002: Detección de Personalidad Inicial (personality detection events)
- UC-001: Primer Contacto con Usuario Nuevo (complete new user flow events)
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.interfaces import IEvent


class BaseUserEvent(IEvent):
    """Base class for all user domain events."""

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
        """Return the aggregate identifier."""
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

        # Add all other fields from the instance
        for key, value in self.__dict__.items():
            if key not in result:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseUserEvent":
        """Deserialize event from dictionary."""
        # Convert timestamp strings back to datetime objects
        for key, value in data.items():
            if key.endswith("_at") or key == "timestamp":
                if isinstance(value, str):
                    data[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))

        # Remove fields that aren't part of the constructor
        constructor_data = {
            k: v for k, v in data.items() if k not in ["event_type", "aggregate_id"]
        }

        return cls(**constructor_data)


# Core User Events
class UserCreatedEvent(BaseUserEvent):
    """Event published when a new user is created."""

    def __init__(
        self,
        user_id: int,
        first_name: str,
        username: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "en",
        created_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.first_name = first_name
        self.username = username
        self.last_name = last_name
        self.language_code = language_code
        self.created_at = created_at or datetime.now(timezone.utc)

        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValueError("user_id is required and must be positive")
        if not self.first_name or not self.first_name.strip():
            raise ValueError("first_name cannot be empty")

    @property
    def event_type(self) -> str:
        return "user.created"


class UserUpdatedEvent(BaseUserEvent):
    """Event published when user data is updated."""

    def __init__(
        self,
        user_id: int,
        changes: Dict[str, Dict[str, Any]],
        updated_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.changes = changes
        self.updated_at = updated_at or datetime.now(timezone.utc)

        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValueError("user_id is required and must be positive")
        if not self.changes or len(self.changes) == 0:
            raise ValueError("changes cannot be empty")

    @property
    def event_type(self) -> str:
        return "user.updated"


class UserDeletedEvent(BaseUserEvent):
    """Event published when a user is deleted/deactivated."""

    def __init__(
        self,
        user_id: int,
        username: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        reason: Optional[str] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.username = username
        self.deleted_at = deleted_at or datetime.now(timezone.utc)
        self.reason = reason

    @property
    def event_type(self) -> str:
        return "user.deleted"


class UserLanguageChangedEvent(BaseUserEvent):
    """Event published when user changes their language."""

    def __init__(
        self,
        user_id: int,
        old_language: str,
        new_language: str,
        changed_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.old_language = old_language
        self.new_language = new_language
        self.changed_at = changed_at or datetime.now(timezone.utc)

        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValueError("user_id is required and must be positive")
        if self.old_language == self.new_language:
            raise ValueError("old_language and new_language must be different")

    @property
    def event_type(self) -> str:
        return "user.language_changed"


class UserLoginEvent(BaseUserEvent):
    """Event published when user logs in or starts session."""

    def __init__(
        self,
        user_id: int,
        login_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.login_at = login_at
        self.ip_address = ip_address
        self.user_agent = user_agent

    @property
    def event_type(self) -> str:
        return "user.login"


# Onboarding Business Events (US-001, UC-001)
class OnboardingStartedEvent(BaseUserEvent):
    """Event published when user begins onboarding process with personalized context."""

    def __init__(
        self,
        user_id: int,
        first_name: str,
        language_code: str,
        adaptive_context: Dict[str, Any],
        started_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.first_name = first_name
        self.language_code = language_code
        self.adaptive_context = adaptive_context
        self.started_at = started_at or datetime.now(timezone.utc)

        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValueError("user_id is required and must be positive")
        if not self.first_name or not self.first_name.strip():
            raise ValueError("first_name cannot be empty")

    @property
    def event_type(self) -> str:
        return "user.onboarding_started"


class OnboardingProgressedEvent(BaseUserEvent):
    """Event published when user progresses through onboarding states."""

    def __init__(
        self,
        user_id: int,
        old_state: str,
        new_state: str,
        progression_data: Optional[Dict[str, Any]] = None,
        progressed_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.old_state = old_state
        self.new_state = new_state
        self.progression_data = progression_data
        self.progressed_at = progressed_at or datetime.now(timezone.utc)

        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValueError("user_id is required and must be positive")
        if self.old_state == self.new_state:
            raise ValueError("old_state and new_state must be different")

    @property
    def event_type(self) -> str:
        return "user.onboarding_progressed"


class OnboardingCompletedEvent(BaseUserEvent):
    """Event published when user completes full onboarding process."""

    def __init__(
        self,
        user_id: int,
        final_state: str,
        completion_metrics: Dict[str, Any],
        completed_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.final_state = final_state
        self.completion_metrics = completion_metrics
        self.completed_at = completed_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.onboarding_completed"


# Tutorial Events (UC-001)
class TutorialStartedEvent(BaseUserEvent):
    """Event published when user starts tutorial with personality-based customization."""

    def __init__(
        self,
        user_id: int,
        personality_archetype: str,
        expected_duration: int,
        sections_planned: List[str],
        customizations: Dict[str, Any],
        started_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.personality_archetype = personality_archetype
        self.expected_duration = expected_duration
        self.sections_planned = sections_planned
        self.customizations = customizations
        self.started_at = started_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.tutorial_started"


class TutorialSectionCompletedEvent(BaseUserEvent):
    """Event published when user completes individual tutorial section."""

    def __init__(
        self,
        user_id: int,
        section_name: str,
        section_data: Dict[str, Any],
        completed_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.section_name = section_name
        self.section_data = section_data
        self.completed_at = completed_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.tutorial_section_completed"


class TutorialCompletedEvent(BaseUserEvent):
    """Event published when user completes full tutorial."""

    def __init__(
        self,
        user_id: int,
        sections_completed: List[str],
        total_time: int,
        engagement_score: float,
        completed_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.sections_completed = sections_completed
        self.total_time = total_time
        self.engagement_score = engagement_score
        self.completed_at = completed_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.tutorial_completed"


# Personality Detection Events (US-002)
class PersonalityQuizStartedEvent(BaseUserEvent):
    """Event published when user starts personality detection quiz."""

    def __init__(
        self,
        user_id: int,
        total_questions: int,
        quiz_config: Dict[str, Any],
        started_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.total_questions = total_questions
        self.quiz_config = quiz_config
        self.started_at = started_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.personality_quiz_started"


class PersonalityQuestionAnsweredEvent(BaseUserEvent):
    """Event published when user answers personality quiz question."""

    def __init__(
        self,
        user_id: int,
        question_id: str,
        question_number: int,
        answer_id: str,
        dimension_impact: Dict[str, float],
        answered_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.question_id = question_id
        self.question_number = question_number
        self.answer_id = answer_id
        self.dimension_impact = dimension_impact
        self.answered_at = answered_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.personality_question_answered"


class PersonalityDetectedEvent(BaseUserEvent):
    """Event published when user personality is detected with 4-dimension analysis."""

    def __init__(
        self,
        user_id: int,
        dimensions: Dict[str, float],
        archetype: str,
        confidence: float,
        quiz_responses: List[Dict[str, Any]],
        detected_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.dimensions = dimensions
        self.archetype = archetype
        self.confidence = confidence
        self.quiz_responses = quiz_responses
        self.detected_at = detected_at or datetime.now(timezone.utc)

        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValueError("user_id is required and must be positive")

        # Validate 4 personality dimensions
        required_dimensions = {"exploration", "competitiveness", "narrative", "social"}
        if not isinstance(self.dimensions, dict):
            raise ValueError("dimensions must be a dictionary")

        dimension_keys = set(self.dimensions.keys())
        if dimension_keys != required_dimensions:
            raise ValueError(
                f"Must include exactly 4 dimensions: {required_dimensions}"
            )

        for dimension, score in self.dimensions.items():
            if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                raise ValueError(
                    f"Dimension '{dimension}' score must be between 0.0 and 1.0"
                )

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

    @property
    def event_type(self) -> str:
        return "user.personality_detected"


class CustomizationGeneratedEvent(BaseUserEvent):
    """Event published when personality-based customizations are generated."""

    def __init__(
        self,
        user_id: int,
        personality_archetype: str,
        customizations: Dict[str, Any],
        generated_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.personality_archetype = personality_archetype
        self.customizations = customizations
        self.generated_at = generated_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.customization_generated"


# Diana Master System Integration Events
class AdaptiveContextInitializedEvent(BaseUserEvent):
    """Event published when adaptive context is initialized for personalization."""

    def __init__(
        self,
        user_id: int,
        context_data: Dict[str, Any],
        initialization_source: str,
        initialized_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.context_data = context_data
        self.initialization_source = initialization_source
        self.initialized_at = initialized_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.adaptive_context_initialized"


class ProfileUpdatedEvent(BaseUserEvent):
    """Event published when user profile is refined based on behavioral analysis."""

    def __init__(
        self,
        user_id: int,
        profile_changes: Dict[str, Any],
        update_source: str,
        updated_at: Optional[datetime] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(user_id, event_id, timestamp)
        self.profile_changes = profile_changes
        self.update_source = update_source
        self.updated_at = updated_at or datetime.now(timezone.utc)

    @property
    def event_type(self) -> str:
        return "user.profile_updated"


# User Exceptions for Event System
class UserNotFoundError(Exception):
    """Raised when a user cannot be found."""

    pass


class DuplicateUserError(Exception):
    """Raised when attempting to create a user that already exists."""

    pass


class InvalidUserDataError(Exception):
    """Raised when user data is invalid."""

    pass


class RepositoryError(Exception):
    """Raised when repository operations fail."""

    pass
