"""
Comprehensive User Service Unit Tests.

Complete unit test coverage for UserService with all business logic validation,
error scenarios, edge cases, and integration points. Focuses on validating
all CRUD operations, onboarding workflows, personality detection, and
Diana Master System integration.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict, List, Optional

from src.modules.user.service import UserService
from src.modules.user.models import (
    TelegramUser,
    UserCreateRequest,
    UserUpdateRequest,
    OnboardingState,
)
from src.modules.user.events import (
    UserCreatedEvent,
    UserUpdatedEvent,
    UserDeletedEvent,
    OnboardingStartedEvent,
    PersonalityDetectedEvent,
    TutorialCompletedEvent,
    UserNotFoundError,
    DuplicateUserError,
    InvalidUserDataError,
    RepositoryError,
)


@pytest.fixture
def mock_session():
    """Create mock SQLAlchemy session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_event_bus():
    """Create mock EventBus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_diana_master_system():
    """Create mock Diana Master System."""
    diana = AsyncMock()
    diana.initialize_adaptive_context.return_value = {"context": "test"}
    diana.generate_welcome_message.return_value = {"message": "Welcome!"}
    diana.generate_personalization_profile.return_value = {"profile": "test"}
    return diana


@pytest.fixture
def mock_personality_engine():
    """Create mock Personality Engine."""
    engine = AsyncMock()
    engine.get_next_question.return_value = {"question": "test"}
    engine.analyze_responses.return_value = {
        "personality_scores": {
            "exploration": 0.8,
            "competitiveness": 0.6,
            "narrative": 0.7,
            "social": 0.5,
        },
        "archetype": "explorer",
        "confidence": 0.85,
    }
    return engine


@pytest.fixture
def user_service(mock_session, mock_event_bus, mock_diana_master_system, mock_personality_engine):
    """Create UserService with all dependencies."""
    service = UserService(
        session=mock_session,
        event_bus=mock_event_bus,
        diana_master_system=mock_diana_master_system,
        personality_engine=mock_personality_engine,
    )
    
    # Mock repository methods
    service.repository.create = AsyncMock()
    service.repository.get_by_telegram_id = AsyncMock()
    service.repository.get_by_username = AsyncMock()
    service.repository.update = AsyncMock()
    service.repository.delete = AsyncMock()
    service.repository.get_active_users = AsyncMock()
    service.repository.get_by_language_code = AsyncMock()
    
    return service


@pytest.mark.asyncio
class TestUserServiceCRUDOperations:
    """Test all CRUD operations with validation and error handling."""

    async def test_create_user_success(self, user_service, mock_event_bus):
        """Test successful user creation with event publishing."""
        # Setup
        telegram_id = 12345
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="Test User",
            username="testuser",
            language_code="es",
        )

        created_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Test User",
            username="testuser",
            language_code="es",
        )

        user_service.repository.get_by_telegram_id.return_value = None  # No existing user
        user_service.repository.create.return_value = created_user

        # Execute
        result = await user_service.create_user(create_request)

        # Verify
        assert result.telegram_id == telegram_id
        assert result.first_name == "Test User"
        assert result.username == "testuser"
        assert result.language_code == "es"

        # Verify repository calls
        user_service.repository.get_by_telegram_id.assert_called_once_with(telegram_id)
        user_service.repository.create.assert_called_once()

        # Verify event publishing
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserCreatedEvent)
        assert published_event.user_id == telegram_id

    async def test_create_user_duplicate_error(self, user_service):
        """Test user creation with duplicate telegram_id."""
        # Setup
        telegram_id = 12345
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="Test User",
        )

        existing_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Existing User",
        )
        user_service.repository.get_by_telegram_id.return_value = existing_user

        # Execute & Verify
        with pytest.raises(DuplicateUserError):
            await user_service.create_user(create_request)

        # Verify create was not called
        user_service.repository.create.assert_not_called()

    async def test_create_user_validation_errors(self, user_service):
        """Test user creation with invalid data."""
        # Test invalid telegram_id
        with pytest.raises(InvalidUserDataError):
            invalid_request = UserCreateRequest(
                telegram_id=-1,  # Invalid
                first_name="Test",
            )
            await user_service.create_user(invalid_request)

        # Test empty first_name
        with pytest.raises(InvalidUserDataError):
            invalid_request = UserCreateRequest(
                telegram_id=12345,
                first_name="",  # Invalid
            )
            await user_service.create_user(invalid_request)

        # Test empty username when provided
        with pytest.raises(InvalidUserDataError):
            invalid_request = UserCreateRequest(
                telegram_id=12345,
                first_name="Test",
                username="",  # Invalid
            )
            await user_service.create_user(invalid_request)

    async def test_get_user_by_telegram_id_success(self, user_service):
        """Test successful user retrieval by telegram_id."""
        # Setup
        telegram_id = 67890
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Retrieved User",
        )
        user_service.repository.get_by_telegram_id.return_value = user

        # Execute
        result = await user_service.get_user_by_telegram_id(telegram_id)

        # Verify
        assert result.telegram_id == telegram_id
        assert result.first_name == "Retrieved User"
        user_service.repository.get_by_telegram_id.assert_called_once_with(telegram_id)

    async def test_get_user_by_telegram_id_not_found(self, user_service):
        """Test user retrieval when user doesn't exist."""
        # Setup
        telegram_id = 99999
        user_service.repository.get_by_telegram_id.return_value = None

        # Execute & Verify
        with pytest.raises(UserNotFoundError):
            await user_service.get_user_by_telegram_id(telegram_id)

    async def test_get_user_by_telegram_id_validation(self, user_service):
        """Test user retrieval with invalid telegram_id."""
        with pytest.raises(InvalidUserDataError):
            await user_service.get_user_by_telegram_id(-1)

        with pytest.raises(InvalidUserDataError):
            await user_service.get_user_by_telegram_id(0)

    async def test_get_user_by_username_success(self, user_service):
        """Test successful user retrieval by username."""
        # Setup
        username = "testuser"
        user = TelegramUser(
            telegram_id=12345,
            first_name="User",
            username=username,
        )
        user_service.repository.get_by_username.return_value = user

        # Execute
        result = await user_service.get_user_by_username(username)

        # Verify
        assert result is not None
        assert result.username == username
        user_service.repository.get_by_username.assert_called_once_with(username)

    async def test_get_user_by_username_not_found(self, user_service):
        """Test user retrieval by username when not found."""
        # Setup
        user_service.repository.get_by_username.return_value = None

        # Execute
        result = await user_service.get_user_by_username("nonexistent")

        # Verify
        assert result is None

    async def test_get_user_by_username_validation(self, user_service):
        """Test user retrieval by username with validation."""
        with pytest.raises(InvalidUserDataError):
            await user_service.get_user_by_username("")

        with pytest.raises(InvalidUserDataError):
            await user_service.get_user_by_username("   ")

    async def test_update_user_success(self, user_service, mock_event_bus):
        """Test successful user update with event publishing."""
        # Setup
        telegram_id = 12345
        existing_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Old Name",
            username="olduser",
            language_code="en",
        )

        update_request = UserUpdateRequest(
            first_name="New Name",
            username="newuser",
        )

        updated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="New Name",
            username="newuser",
            language_code="en",
        )

        user_service.repository.get_by_telegram_id.return_value = existing_user
        user_service.repository.update.return_value = updated_user

        # Execute
        result = await user_service.update_user(telegram_id, update_request)

        # Verify
        assert result.first_name == "New Name"
        assert result.username == "newuser"

        # Verify repository calls
        user_service.repository.get_by_telegram_id.assert_called_once_with(telegram_id)
        user_service.repository.update.assert_called_once()

        # Verify event publishing
        mock_event_bus.publish.assert_called()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserUpdatedEvent)

    async def test_update_user_language_change_event(self, user_service, mock_event_bus):
        """Test user update with language change triggers separate event."""
        # Setup
        telegram_id = 12345
        existing_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            language_code="en",
        )

        update_request = UserUpdateRequest(
            language_code="es",
        )

        updated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            language_code="es",
        )

        user_service.repository.get_by_telegram_id.return_value = existing_user
        user_service.repository.update.return_value = updated_user

        # Execute
        await user_service.update_user(telegram_id, update_request)

        # Verify two events were published (update + language change)
        assert mock_event_bus.publish.call_count == 2

    async def test_update_user_no_changes(self, user_service):
        """Test user update when no changes detected."""
        # Setup
        telegram_id = 12345
        existing_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            username="same",
        )

        # Create update request with same values
        update_request = UserUpdateRequest(
            username="same",  # Same as existing
        )

        user_service.repository.get_by_telegram_id.return_value = existing_user

        # Execute
        result = await user_service.update_user(telegram_id, update_request)

        # Verify no update was performed
        user_service.repository.update.assert_not_called()
        assert result == existing_user

    async def test_deactivate_user_success(self, user_service, mock_event_bus):
        """Test successful user deactivation."""
        # Setup
        telegram_id = 12345
        active_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            is_active=True,
        )

        deactivated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            is_active=False,
        )

        user_service.repository.get_by_telegram_id.return_value = active_user
        user_service.repository.update.return_value = deactivated_user

        # Execute
        result = await user_service.deactivate_user(telegram_id)

        # Verify
        assert not result.is_active

        # Verify event publishing
        mock_event_bus.publish.assert_called_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, UserDeletedEvent)

    async def test_get_active_users(self, user_service):
        """Test retrieving all active users."""
        # Setup
        active_users = [
            TelegramUser(telegram_id=1, first_name="User1", is_active=True),
            TelegramUser(telegram_id=2, first_name="User2", is_active=True),
        ]
        user_service.repository.get_active_users.return_value = active_users

        # Execute
        result = await user_service.get_active_users()

        # Verify
        assert len(result) == 2
        assert all(user.is_active for user in result)

    async def test_get_users_by_language(self, user_service):
        """Test retrieving users by language code."""
        # Setup
        language_code = "es"
        spanish_users = [
            TelegramUser(telegram_id=1, first_name="Usuario1", language_code="es"),
            TelegramUser(telegram_id=2, first_name="Usuario2", language_code="es"),
        ]
        user_service.repository.get_by_language_code.return_value = spanish_users

        # Execute
        result = await user_service.get_users_by_language(language_code)

        # Verify
        assert len(result) == 2
        assert all(user.language_code == "es" for user in result)

        # Test validation
        with pytest.raises(InvalidUserDataError):
            await user_service.get_users_by_language("")


@pytest.mark.asyncio
class TestUserServiceOnboardingWorkflows:
    """Test onboarding workflow management and state transitions."""

    async def test_create_user_with_onboarding_success(self, user_service, mock_diana_master_system, mock_event_bus):
        """Test successful user creation with onboarding initialization."""
        # Setup
        telegram_id = 12345
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="Onboard User",
        )

        context = {"source": "telegram", "bot_start": True}

        created_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Onboard User",
        )

        user_with_context = TelegramUser(
            telegram_id=telegram_id,
            first_name="Onboard User",
            adaptive_context={"context": "test"},
        )

        user_service.repository.get_by_telegram_id.return_value = None
        user_service.repository.create.return_value = created_user
        user_service.repository.update.return_value = user_with_context

        # Execute
        result = await user_service.create_user_with_onboarding(create_request, context)

        # Verify
        assert result.adaptive_context is not None
        
        # Verify Diana Master System was called
        mock_diana_master_system.initialize_adaptive_context.assert_called_once_with(
            telegram_id, context
        )

        # Verify events were published
        assert mock_event_bus.publish.call_count >= 2  # UserCreated + OnboardingStarted

    async def test_progress_onboarding_state_success(self, user_service, mock_event_bus):
        """Test successful onboarding state progression."""
        # Setup
        telegram_id = 12345
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.NEWCOMER.value,
        )

        updated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.QUIZ_STARTED.value,
        )

        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = updated_user

        # Execute
        result = await user_service.progress_onboarding_state(
            telegram_id, 
            OnboardingState.QUIZ_STARTED.value,
            {"quiz_id": "initial"}
        )

        # Verify
        assert result.onboarding_state == OnboardingState.QUIZ_STARTED.value

        # Verify event publishing
        mock_event_bus.publish.assert_called()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, OnboardingProgressedEvent)

    async def test_progress_onboarding_invalid_state(self, user_service):
        """Test onboarding progression with invalid state."""
        # Setup
        telegram_id = 12345
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
        )
        user_service.repository.get_by_telegram_id.return_value = user

        # Execute & Verify
        with pytest.raises(InvalidUserDataError):
            await user_service.progress_onboarding_state(
                telegram_id, "invalid_state"
            )

    async def test_progress_onboarding_completion_detection(self, user_service, mock_event_bus):
        """Test onboarding completion detection and event publishing."""
        # Setup
        telegram_id = 12345
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.TUTORIAL_IN_PROGRESS.value,
        )

        completed_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.TUTORIAL_COMPLETED.value,
            onboarding_completed=True,
        )

        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = completed_user

        # Execute
        await user_service.progress_onboarding_state(
            telegram_id,
            OnboardingState.TUTORIAL_COMPLETED.value,
            {"completion_metrics": {"score": 0.9}}
        )

        # Verify completion event was published
        assert mock_event_bus.publish.call_count == 2  # Progress + Completion
        events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
        completion_events = [e for e in events if isinstance(e, OnboardingCompletedEvent)]
        assert len(completion_events) == 1

    async def test_generate_personalized_welcome_with_diana(self, user_service, mock_diana_master_system):
        """Test personalized welcome generation with Diana Master System."""
        # Setup
        telegram_id = 12345
        user_data = {"personality": "explorer", "language": "es"}
        
        user = TelegramUser(telegram_id=telegram_id, first_name="User")
        user_service.repository.get_by_telegram_id.return_value = user

        # Execute
        result = await user_service.generate_personalized_welcome(telegram_id, user_data)

        # Verify
        assert result["message"] == "Welcome!"
        mock_diana_master_system.generate_welcome_message.assert_called_once_with(
            telegram_id, user_data
        )

    async def test_generate_personalized_welcome_without_diana(self, user_service):
        """Test welcome generation fallback when Diana Master System not available."""
        # Setup service without Diana Master System
        service_no_diana = UserService(
            session=user_service.session,
            event_bus=user_service.event_bus,
        )
        service_no_diana.repository = user_service.repository

        telegram_id = 12345
        user = TelegramUser(telegram_id=telegram_id, first_name="TestUser")
        service_no_diana.repository.get_by_telegram_id.return_value = user

        # Execute
        result = await service_no_diana.generate_personalized_welcome(telegram_id, {})

        # Verify fallback message
        assert result["message"] == "¡Hola TestUser! Bienvenido a Diana Bot V2. 🌟"
        assert result["personalized"] is False


@pytest.mark.asyncio
class TestUserServicePersonalityDetection:
    """Test personality detection workflow and processing."""

    async def test_process_personality_quiz_completion_success(
        self, user_service, mock_personality_engine, mock_diana_master_system, mock_event_bus
    ):
        """Test successful personality quiz completion processing."""
        # Setup
        telegram_id = 12345
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.QUIZ_IN_PROGRESS.value,
        )

        quiz_responses = [
            {"question_id": "q1", "answer": "option1"},
            {"question_id": "q2", "answer": "option2"},
        ]

        updated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.PERSONALITY_DETECTED.value,
            personality_dimensions={
                "exploration": 0.8,
                "competitiveness": 0.6,
                "narrative": 0.7,
                "social": 0.5,
            },
            personality_archetype="explorer",
            personality_confidence=0.85,
        )

        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = updated_user

        # Execute
        result = await user_service.process_personality_quiz_completion(
            telegram_id, quiz_responses
        )

        # Verify
        assert result.is_personality_detected()
        assert result.personality_archetype == "explorer"
        assert result.onboarding_state == OnboardingState.PERSONALITY_DETECTED.value

        # Verify personality engine was called
        mock_personality_engine.analyze_responses.assert_called_once_with(quiz_responses)

        # Verify Diana Master System was called for customizations
        mock_diana_master_system.generate_personalization_profile.assert_called_once()

        # Verify events were published
        mock_event_bus.publish.assert_called()

    async def test_process_personality_quiz_without_engine(self, user_service):
        """Test personality quiz processing without personality engine."""
        # Setup service without personality engine
        service_no_engine = UserService(
            session=user_service.session,
            event_bus=user_service.event_bus,
        )
        service_no_engine.repository = user_service.repository

        telegram_id = 12345
        quiz_responses = [{"question_id": "q1", "answer": "option1"}]

        # Execute & Verify
        with pytest.raises(InvalidUserDataError, match="Personality engine not available"):
            await service_no_engine.process_personality_quiz_completion(
                telegram_id, quiz_responses
            )

    async def test_get_next_personality_question_success(self, user_service, mock_personality_engine):
        """Test getting next personality question."""
        # Setup
        telegram_id = 12345
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            personality_quiz_progress={"questions_answered": 2},
        )

        user_service.repository.get_by_telegram_id.return_value = user

        # Execute
        result = await user_service.get_next_personality_question(telegram_id)

        # Verify
        assert result["question"] == "test"
        mock_personality_engine.get_next_question.assert_called_once_with(
            {"questions_answered": 2}
        )

    async def test_get_next_personality_question_without_engine(self, user_service):
        """Test getting personality question without engine."""
        # Setup service without personality engine
        service_no_engine = UserService(
            session=user_service.session,
            event_bus=user_service.event_bus,
        )

        # Execute & Verify
        with pytest.raises(InvalidUserDataError, match="Personality engine not available"):
            await service_no_engine.get_next_personality_question(12345)

    async def test_generate_personality_customizations_success(
        self, user_service, mock_diana_master_system
    ):
        """Test personality customization generation."""
        # Setup
        telegram_id = 12345
        personality_data = {
            "dimensions": {"exploration": 0.8},
            "archetype": "explorer",
        }

        user = TelegramUser(telegram_id=telegram_id, first_name="User")
        user_service.repository.get_by_telegram_id.return_value = user

        # Execute
        result = await user_service.generate_personality_customizations(
            telegram_id, personality_data
        )

        # Verify
        assert result["profile"] == "test"
        mock_diana_master_system.generate_personalization_profile.assert_called_once_with(
            telegram_id, {}, "explorer"
        )

    async def test_generate_personality_customizations_without_diana(self, user_service):
        """Test customization generation without Diana Master System."""
        # Setup service without Diana Master System
        service_no_diana = UserService(
            session=user_service.session,
            event_bus=user_service.event_bus,
        )

        telegram_id = 12345
        personality_data = {"archetype": "explorer"}

        # Execute
        result = await service_no_diana.generate_personality_customizations(
            telegram_id, personality_data
        )

        # Verify fallback
        assert result == {"customizations": [], "source": "default"}

    async def test_process_personality_detection_complete(
        self, user_service, mock_personality_engine
    ):
        """Test personality detection completion processing."""
        # Setup
        telegram_id = 12345
        personality_data = {
            "exploration": 0.8,
            "competitiveness": 0.6,
            "narrative": 0.7,
            "social": 0.5,
        }

        user = TelegramUser(telegram_id=telegram_id, first_name="User")
        updated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            personality_dimensions=personality_data,
            personality_archetype="explorer",
            personality_confidence=0.85,
        )

        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = updated_user

        mock_personality_engine.get_archetype_from_scores.return_value = {
            "archetype": "explorer",
            "confidence": 0.85,
        }

        # Execute
        result = await user_service.process_personality_detection_complete(
            telegram_id, personality_data
        )

        # Verify
        assert result.is_personality_detected()
        assert result.personality_archetype == "explorer"
        assert result.personality_confidence == 0.85


@pytest.mark.asyncio
class TestUserServiceTutorialWorkflows:
    """Test tutorial workflow management and progression."""

    async def test_start_tutorial_success(self, user_service, mock_event_bus):
        """Test successful tutorial start."""
        # Setup
        telegram_id = 12345
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            personality_archetype="explorer",
            onboarding_state=OnboardingState.PERSONALITY_DETECTED.value,
        )

        updated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            personality_archetype="explorer",
            onboarding_state=OnboardingState.TUTORIAL_STARTED.value,
        )

        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = updated_user

        # Execute
        await user_service.start_tutorial(telegram_id)

        # Verify state progression was called
        user_service.repository.update.assert_called()

        # Verify tutorial started event was published
        mock_event_bus.publish.assert_called()

    async def test_progress_tutorial_section_success(self, user_service, mock_event_bus):
        """Test successful tutorial section progression."""
        # Setup
        telegram_id = 12345
        section = "introduction"
        section_data = {"completion_score": 0.9, "time_spent": 120}

        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.TUTORIAL_STARTED.value,
        )

        updated_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.TUTORIAL_IN_PROGRESS.value,
            tutorial_progress={
                "sections_completed": ["introduction"],
                "current_section": "introduction",
                "engagement_score": 0.9,
            },
        )

        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = updated_user

        # Execute
        result = await user_service.progress_tutorial_section(
            telegram_id, section, section_data
        )

        # Verify
        assert result.tutorial_progress is not None
        assert "introduction" in result.tutorial_progress["sections_completed"]
        assert result.onboarding_state == OnboardingState.TUTORIAL_IN_PROGRESS.value

        # Verify event publishing
        mock_event_bus.publish.assert_called()

    async def test_complete_tutorial_success(self, user_service, mock_event_bus):
        """Test successful tutorial completion."""
        # Setup
        telegram_id = 12345
        completion_data = {"total_time": 900, "satisfaction_score": 4.5}

        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.TUTORIAL_IN_PROGRESS.value,
            tutorial_progress={
                "sections_completed": ["intro", "basics", "advanced"],
                "engagement_score": 0.85,
            },
        )

        completed_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="User",
            onboarding_state=OnboardingState.TUTORIAL_COMPLETED.value,
            tutorial_completed=True,
            onboarding_completed=True,
            tutorial_progress=user.tutorial_progress,
        )

        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = completed_user

        # Execute
        result = await user_service.complete_tutorial(telegram_id, completion_data)

        # Verify
        assert result.tutorial_completed
        assert result.onboarding_completed
        assert result.onboarding_state == OnboardingState.TUTORIAL_COMPLETED.value

        # Verify event publishing
        mock_event_bus.publish.assert_called()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, TutorialCompletedEvent)


@pytest.mark.asyncio
class TestUserServiceErrorHandling:
    """Test error handling and edge cases."""

    async def test_repository_error_handling(self, user_service):
        """Test handling of repository errors."""
        # Setup
        from sqlalchemy.exc import SQLAlchemyError
        user_service.repository.get_by_telegram_id.side_effect = SQLAlchemyError("DB Error")

        # Execute & Verify
        with pytest.raises(RepositoryError):
            await user_service.get_user_by_telegram_id(12345)

    async def test_event_bus_failure_handling(self, user_service, mock_event_bus):
        """Test handling of event bus failures."""
        # Setup
        telegram_id = 12345
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="Test User",
        )

        created_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Test User",
        )

        user_service.repository.get_by_telegram_id.return_value = None
        user_service.repository.create.return_value = created_user
        mock_event_bus.publish.side_effect = Exception("EventBus Error")

        # Execute & Verify - operation should still succeed
        result = await user_service.create_user(create_request)
        assert result.telegram_id == telegram_id

    async def test_concurrent_operations_safety(self, user_service):
        """Test thread safety of concurrent operations."""
        # Setup
        telegram_ids = [10001, 10002, 10003, 10004, 10005]
        
        async def create_user_task(telegram_id):
            request = UserCreateRequest(
                telegram_id=telegram_id,
                first_name=f"User {telegram_id}",
            )
            
            created_user = TelegramUser(
                telegram_id=telegram_id,
                first_name=f"User {telegram_id}",
            )
            
            user_service.repository.get_by_telegram_id.return_value = None
            user_service.repository.create.return_value = created_user
            
            return await user_service.create_user(request)

        # Execute concurrent operations
        tasks = [create_user_task(telegram_id) for telegram_id in telegram_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        successful_results = [r for r in results if isinstance(r, TelegramUser)]
        assert len(successful_results) == len(telegram_ids)

    async def test_data_validation_edge_cases(self, user_service):
        """Test data validation edge cases."""
        # Test very large telegram_id
        large_id = 2**63 - 1  # Max int64
        request = UserCreateRequest(telegram_id=large_id, first_name="Large ID User")
        
        created_user = TelegramUser(telegram_id=large_id, first_name="Large ID User")
        user_service.repository.get_by_telegram_id.return_value = None
        user_service.repository.create.return_value = created_user

        result = await user_service.create_user(request)
        assert result.telegram_id == large_id

        # Test unicode names
        unicode_request = UserCreateRequest(
            telegram_id=12345,
            first_name="测试用户",  # Chinese characters
            last_name="тест",      # Cyrillic characters
            username="用戶名",     # Mixed unicode
        )

        unicode_user = TelegramUser(
            telegram_id=12345,
            first_name="测试用户",
            last_name="тест",
            username="用戶名",
        )
        
        user_service.repository.get_by_telegram_id.return_value = None
        user_service.repository.create.return_value = unicode_user

        result = await user_service.create_user(unicode_request)
        assert result.first_name == "测试用户"