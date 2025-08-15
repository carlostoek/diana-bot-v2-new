"""
User Module.

This module provides the complete User domain for Diana Bot V2, supporting:
- Telegram user management and onboarding workflows (US-001, UC-001)
- Personality detection with 4-dimension analysis (US-002)
- Event-driven architecture with comprehensive business events
- Clean Architecture patterns with Repository and Service interfaces
- Diana Master System integration for adaptive personalization

The module follows TDD methodology and supports >90% test coverage requirements.
"""

# Events
from .events import (  # Core User Events; Onboarding Business Events (US-001, UC-001); Tutorial Events (UC-001); Personality Detection Events (US-002); Diana Master System Events; Exceptions
    AdaptiveContextInitializedEvent,
    CustomizationGeneratedEvent,
    DuplicateUserError,
    InvalidUserDataError,
    OnboardingCompletedEvent,
    OnboardingProgressedEvent,
    OnboardingStartedEvent,
    PersonalityDetectedEvent,
    PersonalityQuestionAnsweredEvent,
    PersonalityQuizStartedEvent,
    ProfileUpdatedEvent,
    RepositoryError,
    TutorialCompletedEvent,
    TutorialSectionCompletedEvent,
    TutorialStartedEvent,
    UserCreatedEvent,
    UserDeletedEvent,
    UserLanguageChangedEvent,
    UserLoginEvent,
    UserNotFoundError,
    UserUpdatedEvent,
)

# Interfaces
from .interfaces import (
    IDianaMasterSystem,
    IPersonalityEngine,
    IUserRepository,
    IUserService,
)

# Models
from .models import (
    OnboardingState,
    TelegramUser,
    UserCreateRequest,
    UserUpdateRequest,
)

__all__ = [
    # Models
    "TelegramUser",
    "UserCreateRequest",
    "UserUpdateRequest",
    "OnboardingState",
    # Interfaces
    "IUserRepository",
    "IUserService",
    "IPersonalityEngine",
    "IDianaMasterSystem",
    # Core Events
    "UserCreatedEvent",
    "UserUpdatedEvent",
    "UserDeletedEvent",
    "UserLanguageChangedEvent",
    "UserLoginEvent",
    # Business Events
    "OnboardingStartedEvent",
    "OnboardingProgressedEvent",
    "OnboardingCompletedEvent",
    "TutorialStartedEvent",
    "TutorialSectionCompletedEvent",
    "TutorialCompletedEvent",
    "PersonalityQuizStartedEvent",
    "PersonalityQuestionAnsweredEvent",
    "PersonalityDetectedEvent",
    "CustomizationGeneratedEvent",
    "AdaptiveContextInitializedEvent",
    "ProfileUpdatedEvent",
    # Exceptions
    "UserNotFoundError",
    "DuplicateUserError",
    "InvalidUserDataError",
    "RepositoryError",
]
