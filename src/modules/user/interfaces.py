"""
User Module Interfaces.

This module defines the interfaces for the User Module following Clean Architecture patterns
and Repository/Service interfaces. Supports complete Diana Bot V2 business requirements
including onboarding workflows, personality detection, and Diana Master System integration.

Business Requirements Coverage:
- US-001: Primer Contacto Personalizado (onboarding workflows and state management)
- US-002: Detección de Personalidad Inicial (personality detection and quiz flows)
- UC-001: Primer Contacto con Usuario Nuevo (complete new user flow)
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import TelegramUser, UserCreateRequest, UserUpdateRequest


class IUserRepository(ABC):
    """
    Repository interface for User data persistence.

    Defines the contract for all user data storage operations following
    Clean Architecture patterns. Supports advanced querying, pagination,
    and bulk operations for Diana Bot V2 scalability requirements.
    """

    @abstractmethod
    async def create(self, user: TelegramUser) -> TelegramUser:
        """Create a new user in the repository."""
        pass

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[TelegramUser]:
        """Retrieve a user by their Telegram ID."""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[TelegramUser]:
        """Retrieve a user by their username."""
        pass

    @abstractmethod
    async def update(self, user: TelegramUser) -> TelegramUser:
        """Update an existing user in the repository."""
        pass

    @abstractmethod
    async def delete(self, telegram_id: int) -> bool:
        """Delete a user by their Telegram ID."""
        pass

    @abstractmethod
    async def get_active_users(self) -> List[TelegramUser]:
        """Retrieve all active users."""
        pass

    @abstractmethod
    async def get_by_language_code(self, language_code: str) -> List[TelegramUser]:
        """Retrieve users by language code."""
        pass

    @abstractmethod
    async def count_users(self) -> int:
        """Count total number of users."""
        pass

    @abstractmethod
    async def count_active_users(self) -> int:
        """Count total number of active users."""
        pass

    @abstractmethod
    async def get_users_paginated(
        self, limit: int = 50, offset: int = 0
    ) -> List[TelegramUser]:
        """Retrieve users with pagination support."""
        pass

    @abstractmethod
    async def bulk_create(self, users: List[TelegramUser]) -> int:
        """Bulk create multiple users for performance."""
        pass

    @abstractmethod
    async def search_users_by_name(self, search_term: str) -> List[TelegramUser]:
        """Search users by first name or last name."""
        pass


class IUserService(ABC):
    """
    Service interface for User business logic.

    Defines the contract for all user-related business operations following
    Clean Architecture patterns. Supports complete Diana Bot V2 onboarding flows,
    personality detection, tutorial progression, and Diana Master System integration.
    """

    # Basic User Operations
    @abstractmethod
    async def create_user(self, create_request: UserCreateRequest) -> TelegramUser:
        """Create a new user with business validation and event publishing."""
        pass

    @abstractmethod
    async def get_user_by_telegram_id(self, telegram_id: int) -> TelegramUser:
        """Get user by telegram ID with error handling."""
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[TelegramUser]:
        """Get user by username, returns None if not found."""
        pass

    @abstractmethod
    async def update_user(
        self, telegram_id: int, update_request: UserUpdateRequest
    ) -> TelegramUser:
        """Update user with change tracking and event publishing."""
        pass

    @abstractmethod
    async def deactivate_user(self, telegram_id: int) -> TelegramUser:
        """Deactivate user (soft delete) with event publishing."""
        pass

    @abstractmethod
    async def get_active_users(self) -> List[TelegramUser]:
        """Get all active users."""
        pass

    @abstractmethod
    async def get_users_by_language(self, language_code: str) -> List[TelegramUser]:
        """Get users filtered by language code."""
        pass

    # Onboarding and State Management (US-001, UC-001)
    @abstractmethod
    async def create_user_with_onboarding(
        self,
        create_request: UserCreateRequest,
        context: Optional[Dict[str, Any]] = None,
    ) -> TelegramUser:
        """Create user with onboarding initialization and adaptive context."""
        pass

    @abstractmethod
    async def progress_onboarding_state(
        self,
        telegram_id: int,
        new_state: str,
        progression_data: Optional[Dict[str, Any]] = None,
    ) -> TelegramUser:
        """Progress user through onboarding state machine."""
        pass

    @abstractmethod
    async def generate_personalized_welcome(
        self, telegram_id: int, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate personalized welcome message via Diana Master System."""
        pass

    # Personality Detection (US-002)
    @abstractmethod
    async def process_personality_quiz_completion(
        self, telegram_id: int, quiz_responses: List[Dict[str, Any]]
    ) -> TelegramUser:
        """Process personality quiz completion and update user profile."""
        pass

    @abstractmethod
    async def get_next_personality_question(self, telegram_id: int) -> Dict[str, Any]:
        """Get next personality quiz question for user."""
        pass

    @abstractmethod
    async def generate_personality_customizations(
        self, telegram_id: int, personality_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate personality-based customizations."""
        pass

    @abstractmethod
    async def process_personality_detection_complete(
        self, telegram_id: int, personality_data: Dict[str, float]
    ) -> TelegramUser:
        """Process completed personality detection with archetype assignment."""
        pass

    # Tutorial and Learning Flow (UC-001)
    @abstractmethod
    async def start_tutorial(self, telegram_id: int) -> None:
        """Start tutorial process with personality-based customization."""
        pass

    @abstractmethod
    async def progress_tutorial_section(
        self, telegram_id: int, section: str, section_data: Dict[str, Any]
    ) -> TelegramUser:
        """Progress through individual tutorial section."""
        pass

    @abstractmethod
    async def complete_tutorial(
        self, telegram_id: int, tutorial_completion_data: Dict[str, Any]
    ) -> TelegramUser:
        """Complete tutorial and finalize onboarding."""
        pass

    # Diana Master System Integration
    @abstractmethod
    async def initialize_user_with_adaptive_context(
        self, telegram_id: int, user_context: Dict[str, Any]
    ) -> TelegramUser:
        """Initialize user with adaptive context from Diana Master System."""
        pass

    @abstractmethod
    async def update_personalization_profile(self, telegram_id: int) -> Dict[str, Any]:
        """Update user personalization profile based on personality data."""
        pass

    @abstractmethod
    async def update_user_profile_from_interactions(
        self, telegram_id: int, interaction_data: Dict[str, Any]
    ) -> TelegramUser:
        """Update user profile based on behavioral interaction analysis."""
        pass


class IPersonalityEngine(ABC):
    """
    Interface for personality detection and analysis engine.

    Supports US-002 requirements for 4-dimension personality detection
    with archetype assignment and confidence scoring.
    """

    @abstractmethod
    async def get_next_question(
        self, user_progress: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get next personality quiz question based on user progress."""
        pass

    @abstractmethod
    async def analyze_responses(
        self, quiz_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze quiz responses and return personality profile.

        Returns:
            {
                "personality_scores": Dict[str, float],  # 4 dimensions
                "archetype": str,
                "confidence": float
            }
        """
        pass

    @abstractmethod
    async def get_archetype_from_scores(
        self, personality_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Get personality archetype from dimension scores."""
        pass

    @abstractmethod
    async def calculate_confidence_score(
        self, quiz_responses: List[Dict[str, Any]], personality_scores: Dict[str, float]
    ) -> float:
        """Calculate confidence score for personality detection."""
        pass


class IDianaMasterSystem(ABC):
    """
    Interface for Diana Master System integration.

    Supports adaptive context generation, personalization, and AI-driven
    experience customization based on user personality and behavior.
    """

    @abstractmethod
    async def initialize_adaptive_context(
        self, user_id: int, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Initialize adaptive context for new user."""
        pass

    @abstractmethod
    async def generate_initial_context(
        self, user_id: int, first_name: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate initial adaptive context for onboarding."""
        pass

    @abstractmethod
    async def generate_welcome_message(
        self, telegram_id: int, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate personalized welcome message."""
        pass

    @abstractmethod
    async def generate_personalization_profile(
        self, user_id: int, personality_data: Dict[str, float], archetype: str
    ) -> Dict[str, Any]:
        """Generate personalization profile from personality data."""
        pass

    @abstractmethod
    async def update_user_profile(
        self,
        user_id: int,
        current_profile: Dict[str, float],
        interaction_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update user profile based on interaction analysis."""
        pass
