"""
User Module Models.

This module contains the domain models for the User Module, following Clean Architecture patterns
and supporting the complete Diana Bot V2 business requirements including onboarding workflows,
personality detection, and Diana Master System integration.

Business Requirements Coverage:
- US-001: Primer Contacto Personalizado (onboarding state machine)
- US-002: Detección de Personalidad Inicial (4-dimension personality scoring)
- UC-001: Primer Contacto con Usuario Nuevo (complete flow)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class OnboardingState(Enum):
    """Enumeration of possible onboarding states for state machine flow."""

    NEWCOMER = "newcomer"
    QUIZ_STARTED = "quiz_started"
    QUIZ_IN_PROGRESS = "quiz_in_progress"
    PERSONALITY_DETECTED = "personality_detected"
    TUTORIAL_STARTED = "tutorial_started"
    TUTORIAL_IN_PROGRESS = "tutorial_in_progress"
    TUTORIAL_COMPLETED = "tutorial_completed"


@dataclass
class TelegramUser:
    """
    Domain model representing a Telegram user in Diana Bot V2.

    Supports the complete business flow from first contact through personality detection
    and onboarding completion. Includes Diana Master System integration fields for
    adaptive context and personalization.

    Business Context:
    - Telegram-specific user identification and profile data
    - Onboarding state machine progression tracking
    - Personality dimensions (exploration, competitiveness, narrative, social)
    - Tutorial and engagement tracking
    - Adaptive context for AI-driven personalization
    """

    # Core Telegram Identity (Required)
    telegram_id: int
    first_name: str

    # Optional Telegram Profile Data
    username: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "en"

    # System Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    # Onboarding and State Management (US-001, UC-001)
    onboarding_state: str = OnboardingState.NEWCOMER.value
    onboarding_completed: bool = False
    tutorial_completed: bool = False

    # Tutorial Progress Tracking
    tutorial_progress: Optional[Dict[str, Any]] = None

    # Personality Detection (US-002)
    personality_dimensions: Optional[Dict[str, float]] = (
        None  # 4 dimensions: exploration, competitiveness, narrative, social
    )
    personality_archetype: Optional[str] = None
    personality_confidence: Optional[float] = None
    personality_quiz_progress: Optional[Dict[str, Any]] = None

    # Diana Master System Integration
    adaptive_context: Optional[Dict[str, Any]] = None
    behavioral_profile: Optional[Dict[str, Any]] = None
    engagement_patterns: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate model data after initialization."""
        self._validate()

    def _validate(self):
        """Validate user data integrity."""
        if not isinstance(self.telegram_id, int) or self.telegram_id <= 0:
            raise ValueError("telegram_id must be a positive integer")

        if not self.first_name or not self.first_name.strip():
            raise ValueError("first_name cannot be empty")

        if self.personality_dimensions:
            self._validate_personality_dimensions()

        if self.personality_confidence is not None:
            if not (0.0 <= self.personality_confidence <= 1.0):
                raise ValueError("personality_confidence must be between 0.0 and 1.0")

    def _validate_personality_dimensions(self):
        """Validate personality dimensions according to US-002 requirements."""
        required_dimensions = {"exploration", "competitiveness", "narrative", "social"}

        if not isinstance(self.personality_dimensions, dict):
            raise ValueError("personality_dimensions must be a dictionary")

        dimension_keys = set(self.personality_dimensions.keys())
        if dimension_keys != required_dimensions:
            missing = required_dimensions - dimension_keys
            extra = dimension_keys - required_dimensions
            error_msg = (
                f"Personality dimensions mismatch. Missing: {missing}, Extra: {extra}"
            )
            raise ValueError(error_msg)

        for dimension, score in self.personality_dimensions.items():
            if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                raise ValueError(
                    f"Dimension '{dimension}' score must be between 0.0 and 1.0"
                )

    def update_onboarding_state(self, new_state: str) -> None:
        """Update onboarding state with validation."""
        try:
            # Validate new state is valid
            OnboardingState(new_state)
            self.onboarding_state = new_state
            self.updated_at = datetime.now(timezone.utc)
        except ValueError:
            valid_states = [state.value for state in OnboardingState]
            raise ValueError(
                f"Invalid onboarding state '{new_state}'. Valid states: {valid_states}"
            )

    def set_personality_data(
        self, dimensions: Dict[str, float], archetype: str, confidence: float
    ) -> None:
        """Set personality detection results with validation."""
        # Temporarily set data for validation
        temp_dimensions = self.personality_dimensions
        temp_archetype = self.personality_archetype
        temp_confidence = self.personality_confidence

        try:
            self.personality_dimensions = dimensions
            self.personality_archetype = archetype
            self.personality_confidence = confidence
            self._validate_personality_dimensions()
            self.updated_at = datetime.now(timezone.utc)
        except Exception as e:
            # Restore original data on validation failure
            self.personality_dimensions = temp_dimensions
            self.personality_archetype = temp_archetype
            self.personality_confidence = temp_confidence
            raise e

    def update_tutorial_progress(
        self, section: str, section_data: Dict[str, Any]
    ) -> None:
        """Update tutorial progress with section completion data."""
        if not self.tutorial_progress:
            self.tutorial_progress = {
                "sections_completed": [],
                "current_section": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "engagement_score": 0.0,
            }

        if section not in self.tutorial_progress["sections_completed"]:
            self.tutorial_progress["sections_completed"].append(section)

        self.tutorial_progress["current_section"] = section

        # Update engagement score based on section performance
        if "completion_score" in section_data:
            current_engagement = self.tutorial_progress["engagement_score"]
            new_score = section_data["completion_score"]
            # Simple average of all section scores
            total_sections = len(self.tutorial_progress["sections_completed"])
            self.tutorial_progress["engagement_score"] = (
                current_engagement * (total_sections - 1) + new_score
            ) / total_sections

        self.updated_at = datetime.now(timezone.utc)

    def complete_tutorial(self) -> None:
        """Mark tutorial as completed and update onboarding state."""
        self.tutorial_completed = True
        self.update_onboarding_state(OnboardingState.TUTORIAL_COMPLETED.value)

        # Mark onboarding as completed if tutorial is finished
        if self.onboarding_state == OnboardingState.TUTORIAL_COMPLETED.value:
            self.onboarding_completed = True

    def is_personality_detected(self) -> bool:
        """Check if personality has been detected and is valid."""
        return (
            self.personality_dimensions is not None
            and self.personality_archetype is not None
            and self.personality_confidence is not None
            and self.personality_confidence > 0.0
        )

    def get_onboarding_progress_percentage(self) -> float:
        """Calculate onboarding progress as percentage."""
        state_weights = {
            OnboardingState.NEWCOMER.value: 0.0,
            OnboardingState.QUIZ_STARTED.value: 0.2,
            OnboardingState.QUIZ_IN_PROGRESS.value: 0.4,
            OnboardingState.PERSONALITY_DETECTED.value: 0.6,
            OnboardingState.TUTORIAL_STARTED.value: 0.7,
            OnboardingState.TUTORIAL_IN_PROGRESS.value: 0.85,
            OnboardingState.TUTORIAL_COMPLETED.value: 1.0,
        }

        return state_weights.get(self.onboarding_state, 0.0)


@dataclass
class UserCreateRequest:
    """
    Data Transfer Object for user creation requests.

    Supports creating users from Telegram update data with proper validation
    and default value handling for Diana Bot V2 onboarding flows.
    """

    telegram_id: int
    first_name: str
    username: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "en"

    @classmethod
    def from_telegram_data(cls, telegram_data: Dict[str, Any]) -> "UserCreateRequest":
        """Create UserCreateRequest from Telegram user data."""
        return cls(
            telegram_id=telegram_data["id"],
            first_name=telegram_data["first_name"],
            username=telegram_data.get("username"),
            last_name=telegram_data.get("last_name"),
            language_code=telegram_data.get("language_code", "en"),
        )

    def __post_init__(self):
        """Validate request data."""
        if not isinstance(self.telegram_id, int) or self.telegram_id <= 0:
            raise ValueError("telegram_id must be a positive integer")

        if not self.first_name or not self.first_name.strip():
            raise ValueError("first_name cannot be empty")


@dataclass
class UserUpdateRequest:
    """
    Data Transfer Object for user update requests.

    Supports partial updates to user profiles with validation for changed fields.
    All fields are optional to support partial updates.
    """

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None

    def has_changes(self) -> bool:
        """Check if request contains any changes."""
        return any(
            [
                self.username is not None,
                self.first_name is not None,
                self.last_name is not None,
                self.language_code is not None,
            ]
        )

    def get_changes(self, original_user: TelegramUser) -> Dict[str, Dict[str, Any]]:
        """Get dictionary of changes compared to original user."""
        changes = {}

        if self.username is not None and self.username != original_user.username:
            changes["username"] = {"old": original_user.username, "new": self.username}

        if self.first_name is not None and self.first_name != original_user.first_name:
            changes["first_name"] = {
                "old": original_user.first_name,
                "new": self.first_name,
            }

        if self.last_name is not None and self.last_name != original_user.last_name:
            changes["last_name"] = {
                "old": original_user.last_name,
                "new": self.last_name,
            }

        if (
            self.language_code is not None
            and self.language_code != original_user.language_code
        ):
            changes["language_code"] = {
                "old": original_user.language_code,
                "new": self.language_code,
            }

        return changes

    def __post_init__(self):
        """Validate update request."""
        if not self.has_changes():
            raise ValueError("Update request must contain at least one change")

        if self.first_name is not None and (
            not self.first_name or not self.first_name.strip()
        ):
            raise ValueError("first_name cannot be empty")
