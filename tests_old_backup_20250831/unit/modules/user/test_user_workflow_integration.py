"""
Complete User Workflow Integration Tests.

Comprehensive test suite for validating complete user workflows including:
- User creation with onboarding
- Personality detection flow
- Tutorial progression
- EventBus integration
- Cross-service communication
- Error scenarios and recovery

Focus on end-to-end validation of critical user workflows for Diana Bot V2.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict, List, Optional

from src.core.event_bus import EventBus
from src.modules.user.service import UserService
from src.modules.user.repository import UserRepository
from src.modules.user.models import TelegramUser, UserCreateRequest, OnboardingState
from src.modules.user.events import (
    UserCreatedEvent,
    OnboardingStartedEvent,
    PersonalityDetectedEvent,
    TutorialCompletedEvent,
    OnboardingCompletedEvent,
)
from src.modules.user.event_handlers import UserEventHandlers


@pytest.fixture
async def event_bus():
    """Create EventBus instance in test mode."""
    bus = EventBus(test_mode=True)
    await bus.initialize()
    yield bus
    await bus.cleanup()


@pytest.fixture
async def mock_session():
    """Create mock SQLAlchemy session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
async def mock_diana_master_system():
    """Create mock Diana Master System."""
    diana = AsyncMock()
    diana.initialize_adaptive_context.return_value = {
        "context_type": "onboarding",
        "personalization_level": "basic",
        "preferences": {},
    }
    diana.generate_welcome_message.return_value = {
        "message": "¡Hola! Bienvenido a Diana Bot V2 🌟",
        "type": "personalized_welcome",
        "personalized": True,
    }
    diana.generate_personalization_profile.return_value = {
        "archetype_customizations": {"tutorial_style": "interactive"},
        "content_preferences": {"difficulty": "medium"},
    }
    return diana


@pytest.fixture
async def mock_personality_engine():
    """Create mock Personality Engine."""
    engine = AsyncMock()
    engine.get_next_question.return_value = {
        "question_id": "q1",
        "question": "How do you prefer to learn?",
        "options": ["hands-on", "reading", "discussion"],
    }
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
    engine.get_archetype_from_scores.return_value = {
        "archetype": "explorer",
        "confidence": 0.85,
    }
    return engine


@pytest.fixture
async def user_service(mock_session, event_bus, mock_diana_master_system, mock_personality_engine):
    """Create UserService instance with all dependencies."""
    service = UserService(
        session=mock_session,
        event_bus=event_bus,
        diana_master_system=mock_diana_master_system,
        personality_engine=mock_personality_engine,
    )
    
    # Mock repository methods
    service.repository.create = AsyncMock()
    service.repository.get_by_telegram_id = AsyncMock()
    service.repository.update = AsyncMock()
    
    return service


@pytest.fixture
async def event_handlers(event_bus):
    """Create UserEventHandlers instance."""
    handlers = UserEventHandlers(event_bus)
    await handlers.register_all_handlers()
    yield handlers
    await handlers.unregister_all_handlers()


@pytest.mark.asyncio
class TestCompleteUserWorkflows:
    """Test complete user workflows from creation to onboarding completion."""

    async def test_complete_user_onboarding_workflow(
        self, user_service, event_bus, mock_diana_master_system
    ):
        """Test complete user onboarding workflow from creation to completion."""
        # Setup
        telegram_id = 12345
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="Test User",
            username="testuser",
            language_code="es",
        )

        # Mock successful user creation
        created_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Test User",
            username="testuser",
            language_code="es",
        )
        user_service.repository.create.return_value = created_user
        user_service.repository.get_by_telegram_id.return_value = created_user
        user_service.repository.update.return_value = created_user

        # Capture published events
        published_events = []
        original_publish = event_bus.publish
        async def capture_events(event):
            published_events.append(event)
            return await original_publish(event)
        event_bus.publish = capture_events

        # Step 1: Create user with onboarding
        user = await user_service.create_user_with_onboarding(
            create_request, {"source": "telegram", "bot_start": True}
        )

        # Verify user creation
        assert user.telegram_id == telegram_id
        assert user.onboarding_state == OnboardingState.NEWCOMER.value
        assert user.adaptive_context is not None

        # Verify events published
        event_types = [event.event_type for event in published_events]
        assert "user.created" in event_types
        assert "user.adaptive_context_initialized" in event_types
        assert "user.onboarding_started" in event_types

        # Step 2: Progress through personality quiz
        quiz_responses = [
            {"question_id": "q1", "answer": "hands-on", "dimension_impact": {"exploration": 0.2}},
            {"question_id": "q2", "answer": "challenge", "dimension_impact": {"competitiveness": 0.3}},
        ]

        updated_user = created_user
        updated_user.personality_dimensions = {
            "exploration": 0.8,
            "competitiveness": 0.6,
            "narrative": 0.7,
            "social": 0.5,
        }
        updated_user.personality_archetype = "explorer"
        updated_user.personality_confidence = 0.85
        updated_user.onboarding_state = OnboardingState.PERSONALITY_DETECTED.value

        user_service.repository.update.return_value = updated_user

        # Process personality quiz
        user = await user_service.process_personality_quiz_completion(
            telegram_id, quiz_responses
        )

        # Verify personality detection
        assert user.personality_archetype == "explorer"
        assert user.is_personality_detected()
        assert user.onboarding_state == OnboardingState.PERSONALITY_DETECTED.value

        # Verify personality event published
        personality_events = [e for e in published_events if e.event_type == "user.personality_detected"]
        assert len(personality_events) == 1
        assert personality_events[0].archetype == "explorer"

        # Step 3: Start tutorial
        await user_service.start_tutorial(telegram_id)

        # Verify tutorial started event
        tutorial_events = [e for e in published_events if e.event_type == "user.tutorial_started"]
        assert len(tutorial_events) == 1

        # Step 4: Progress through tutorial sections
        sections = ["introduction", "basic_features", "gamification"]
        for section in sections:
            section_data = {"completion_score": 0.9, "time_spent": 120}
            await user_service.progress_tutorial_section(telegram_id, section, section_data)

        # Verify section completion events
        section_events = [e for e in published_events if e.event_type == "user.tutorial_section_completed"]
        assert len(section_events) == len(sections)

        # Step 5: Complete tutorial and onboarding
        updated_user.tutorial_completed = True
        updated_user.onboarding_completed = True
        updated_user.onboarding_state = OnboardingState.TUTORIAL_COMPLETED.value
        user_service.repository.update.return_value = updated_user

        completion_data = {"total_time": 900, "satisfaction_score": 4.5}
        final_user = await user_service.complete_tutorial(telegram_id, completion_data)

        # Verify final state
        assert final_user.tutorial_completed
        assert final_user.onboarding_completed
        assert final_user.onboarding_state == OnboardingState.TUTORIAL_COMPLETED.value

        # Verify completion events
        completion_events = [e for e in published_events if e.event_type == "user.tutorial_completed"]
        assert len(completion_events) == 1

        # Verify all workflow events were published
        expected_events = [
            "user.created",
            "user.adaptive_context_initialized",
            "user.onboarding_started",
            "user.personality_detected",
            "user.customization_generated",
            "user.onboarding_progressed",
            "user.tutorial_started",
            "user.tutorial_section_completed",
            "user.tutorial_completed",
            "user.onboarding_progressed",  # Tutorial completion progression
        ]

        for expected_event in expected_events:
            assert expected_event in event_types, f"Missing event: {expected_event}"

    async def test_user_creation_with_duplicate_detection(self, user_service):
        """Test user creation with duplicate detection and proper error handling."""
        telegram_id = 67890
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="Duplicate User",
            username="duplicate",
        )

        # Mock existing user found
        existing_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Existing User",
            username="existing",
        )
        user_service.repository.get_by_telegram_id.return_value = existing_user

        # Attempt to create duplicate user
        from src.modules.user.events import DuplicateUserError
        with pytest.raises(DuplicateUserError):
            await user_service.create_user(create_request)

        # Verify repository methods were called correctly
        user_service.repository.get_by_telegram_id.assert_called_once_with(telegram_id)
        user_service.repository.create.assert_not_called()

    async def test_personality_detection_error_scenarios(self, user_service):
        """Test personality detection with various error scenarios."""
        telegram_id = 11111

        # Setup existing user
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Test User",
            onboarding_state=OnboardingState.QUIZ_IN_PROGRESS.value,
        )
        user_service.repository.get_by_telegram_id.return_value = user

        # Test 1: Invalid quiz responses (empty)
        with pytest.raises(Exception):
            await user_service.process_personality_quiz_completion(telegram_id, [])

        # Test 2: Personality engine failure
        user_service.personality_engine.analyze_responses.side_effect = Exception("Engine failure")
        
        quiz_responses = [{"question_id": "q1", "answer": "test"}]
        with pytest.raises(Exception):
            await user_service.process_personality_quiz_completion(telegram_id, quiz_responses)

        # Reset mock
        user_service.personality_engine.analyze_responses.side_effect = None

        # Test 3: Invalid personality dimensions
        user_service.personality_engine.analyze_responses.return_value = {
            "personality_scores": {"invalid": 0.5},  # Missing required dimensions
            "archetype": "test",
            "confidence": 0.8,
        }

        with pytest.raises(Exception):
            await user_service.process_personality_quiz_completion(telegram_id, quiz_responses)

    async def test_tutorial_progression_validation(self, user_service):
        """Test tutorial progression with validation and error handling."""
        telegram_id = 22222

        # Setup user with personality detected
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Test User",
            onboarding_state=OnboardingState.PERSONALITY_DETECTED.value,
            personality_archetype="explorer",
            personality_dimensions={
                "exploration": 0.8,
                "competitiveness": 0.6,
                "narrative": 0.7,
                "social": 0.5,
            },
            personality_confidence=0.85,
        )
        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = user

        # Test tutorial start
        await user_service.start_tutorial(telegram_id)

        # Test section progression with invalid data
        with pytest.raises(Exception):
            await user_service.progress_tutorial_section(
                telegram_id, "", {"invalid": "data"}  # Empty section name
            )

        # Test valid section progression
        section_data = {"completion_score": 0.85, "time_spent": 180}
        updated_user = await user_service.progress_tutorial_section(
            telegram_id, "introduction", section_data
        )

        # Verify tutorial progress was updated
        assert updated_user.tutorial_progress is not None
        progress = updated_user.tutorial_progress
        assert "introduction" in progress["sections_completed"]

    async def test_event_bus_integration_reliability(self, user_service, event_bus):
        """Test EventBus integration reliability and error handling."""
        telegram_id = 33333
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="Event Test User",
        )

        # Mock user creation
        created_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Event Test User",
        )
        user_service.repository.create.return_value = created_user
        user_service.repository.get_by_telegram_id.return_value = None  # No existing user

        # Test 1: EventBus publish failure
        original_publish = event_bus.publish
        event_bus.publish = AsyncMock(side_effect=Exception("EventBus failure"))

        # User creation should still succeed even if event publishing fails
        user = await user_service.create_user(create_request)
        assert user.telegram_id == telegram_id

        # Restore EventBus
        event_bus.publish = original_publish

        # Test 2: EventBus recovery and successful publishing
        published_events = []
        async def capture_events(event):
            published_events.append(event)
            return await original_publish(event)
        event_bus.publish = capture_events

        # Create another user to verify EventBus recovery
        create_request2 = UserCreateRequest(
            telegram_id=44444,
            first_name="Recovery Test",
        )
        created_user2 = TelegramUser(
            telegram_id=44444,
            first_name="Recovery Test",
        )
        user_service.repository.create.return_value = created_user2

        user2 = await user_service.create_user(create_request2)
        assert user2.telegram_id == 44444

        # Verify event was published
        assert len(published_events) > 0
        assert published_events[0].event_type == "user.created"

    async def test_cross_service_event_handling(self, event_handlers, event_bus):
        """Test cross-service event handling and integration."""
        # Track cross-service events
        cross_service_events = []
        
        # Mock the cross-service event publishing
        original_method = event_handlers._publish_cross_service_event
        async def capture_cross_service_events(event_type, data):
            cross_service_events.append({"type": event_type, "data": data})
            return await original_method(event_type, data)
        event_handlers._publish_cross_service_event = capture_cross_service_events

        # Test 1: User creation triggers gamification and analytics events
        user_event = UserCreatedEvent(
            user_id=55555,
            first_name="Cross Service Test",
            username="crosstest",
            language_code="en",
        )
        await event_handlers.handle_user_created(user_event)

        # Verify cross-service events were triggered
        gamification_events = [e for e in cross_service_events if "gamification" in e["type"]]
        analytics_events = [e for e in cross_service_events if "analytics" in e["type"]]
        admin_events = [e for e in cross_service_events if "admin" in e["type"]]

        assert len(gamification_events) > 0
        assert len(analytics_events) > 0
        assert len(admin_events) > 0

        # Test 2: Personality detection triggers personalization events
        cross_service_events.clear()
        personality_event = PersonalityDetectedEvent(
            user_id=55555,
            dimensions={
                "exploration": 0.8,
                "competitiveness": 0.6,
                "narrative": 0.7,
                "social": 0.5,
            },
            archetype="explorer",
            confidence=0.85,
            quiz_responses=[],
        )
        await event_handlers.handle_personality_detected(personality_event)

        # Verify personalization events were triggered
        personalization_events = [e for e in cross_service_events if "personality_profile_ready" in e["type"]]
        assert len(personalization_events) > 0

    async def test_concurrent_user_operations(self, user_service):
        """Test concurrent user operations for thread safety."""
        # Setup multiple users
        user_ids = [100001, 100002, 100003, 100004, 100005]
        
        # Mock repository to handle concurrent operations
        created_users = {}
        async def mock_create(user):
            await asyncio.sleep(0.01)  # Simulate DB latency
            created_users[user.telegram_id] = user
            return user

        async def mock_get_by_id(telegram_id):
            await asyncio.sleep(0.005)  # Simulate DB latency
            return created_users.get(telegram_id)

        user_service.repository.create = mock_create
        user_service.repository.get_by_telegram_id = mock_get_by_id

        # Create users concurrently
        async def create_user(telegram_id):
            request = UserCreateRequest(
                telegram_id=telegram_id,
                first_name=f"Concurrent User {telegram_id}",
                username=f"user{telegram_id}",
            )
            return await user_service.create_user(request)

        # Execute concurrent operations
        tasks = [create_user(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        successful_results = [r for r in results if isinstance(r, TelegramUser)]
        assert len(successful_results) == len(user_ids)

        # Verify each user was created with correct data
        for result in successful_results:
            assert result.telegram_id in user_ids
            assert result.first_name.startswith("Concurrent User")

    async def test_onboarding_state_machine_validation(self, user_service):
        """Test onboarding state machine with invalid transitions."""
        telegram_id = 77777

        # Setup user
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="State Test User",
            onboarding_state=OnboardingState.NEWCOMER.value,
        )
        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = user

        # Test valid state progression
        updated_user = await user_service.progress_onboarding_state(
            telegram_id, OnboardingState.QUIZ_STARTED.value
        )
        assert updated_user.onboarding_state == OnboardingState.QUIZ_STARTED.value

        # Test invalid state
        from src.modules.user.events import InvalidUserDataError
        with pytest.raises(InvalidUserDataError):
            await user_service.progress_onboarding_state(
                telegram_id, "invalid_state"
            )

        # Test progression validation with data
        progression_data = {"quiz_progress": 0.5, "time_spent": 300}
        updated_user = await user_service.progress_onboarding_state(
            telegram_id, 
            OnboardingState.QUIZ_IN_PROGRESS.value,
            progression_data
        )

        # Verify progression was successful
        assert updated_user.onboarding_state == OnboardingState.QUIZ_IN_PROGRESS.value

    async def test_performance_metrics_tracking(self, user_service, event_bus):
        """Test performance metrics and tracking during user workflows."""
        # Track timing metrics
        operation_times = []
        
        # Wrap service methods to track timing
        original_create = user_service.create_user
        async def timed_create_user(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            result = await original_create(*args, **kwargs)
            end_time = datetime.now(timezone.utc)
            operation_times.append({
                "operation": "create_user",
                "duration": (end_time - start_time).total_seconds(),
            })
            return result
        user_service.create_user = timed_create_user

        # Setup
        telegram_id = 88888
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="Performance Test User",
        )

        created_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Performance Test User",
        )
        user_service.repository.create.return_value = created_user
        user_service.repository.get_by_telegram_id.return_value = None

        # Execute operations
        user = await user_service.create_user(create_request)

        # Verify performance tracking
        assert len(operation_times) == 1
        assert operation_times[0]["operation"] == "create_user"
        assert operation_times[0]["duration"] < 1.0  # Should complete within 1 second

        # Test EventBus performance
        stats = await event_bus.get_statistics()
        assert "total_events_published" in stats
        assert "total_subscribers" in stats
        assert "avg_publish_time_ms" in stats


@pytest.mark.asyncio
class TestUserWorkflowErrorRecovery:
    """Test error recovery and resilience in user workflows."""

    async def test_database_failure_recovery(self, user_service):
        """Test recovery from database failures during user operations."""
        telegram_id = 99999
        create_request = UserCreateRequest(
            telegram_id=telegram_id,
            first_name="DB Failure Test",
        )

        # Test repository failure
        from sqlalchemy.exc import SQLAlchemyError
        user_service.repository.create.side_effect = SQLAlchemyError("DB Connection Lost")

        # Verify error is properly handled
        from src.modules.user.events import RepositoryError
        with pytest.raises(RepositoryError):
            await user_service.create_user(create_request)

        # Test recovery after database reconnection
        created_user = TelegramUser(
            telegram_id=telegram_id,
            first_name="DB Failure Test",
        )
        user_service.repository.create.side_effect = None
        user_service.repository.create.return_value = created_user
        user_service.repository.get_by_telegram_id.return_value = None

        # Operation should succeed after recovery
        user = await user_service.create_user(create_request)
        assert user.telegram_id == telegram_id

    async def test_partial_workflow_recovery(self, user_service):
        """Test recovery from partial workflow failures."""
        telegram_id = 111111

        # Setup user with partial onboarding completion
        user = TelegramUser(
            telegram_id=telegram_id,
            first_name="Partial Recovery Test",
            onboarding_state=OnboardingState.QUIZ_IN_PROGRESS.value,
            personality_quiz_progress={
                "questions_answered": 5,
                "total_questions": 10,
                "last_question_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        user_service.repository.get_by_telegram_id.return_value = user
        user_service.repository.update.return_value = user

        # Simulate personality engine failure during quiz completion
        user_service.personality_engine.analyze_responses.side_effect = Exception("Analysis failed")

        quiz_responses = [{"question_id": "q1", "answer": "test"}]
        with pytest.raises(Exception):
            await user_service.process_personality_quiz_completion(telegram_id, quiz_responses)

        # Verify user state is preserved for recovery
        retrieved_user = await user_service.get_user_by_telegram_id(telegram_id)
        assert retrieved_user.onboarding_state == OnboardingState.QUIZ_IN_PROGRESS.value
        assert retrieved_user.personality_quiz_progress is not None

        # Test successful recovery
        user_service.personality_engine.analyze_responses.side_effect = None
        user_service.personality_engine.analyze_responses.return_value = {
            "personality_scores": {
                "exploration": 0.8,
                "competitiveness": 0.6,
                "narrative": 0.7,
                "social": 0.5,
            },
            "archetype": "explorer",
            "confidence": 0.85,
        }

        # Update mock to return user with detected personality
        recovered_user = user
        recovered_user.personality_dimensions = {
            "exploration": 0.8,
            "competitiveness": 0.6,
            "narrative": 0.7,
            "social": 0.5,
        }
        recovered_user.personality_archetype = "explorer"
        recovered_user.personality_confidence = 0.85
        recovered_user.onboarding_state = OnboardingState.PERSONALITY_DETECTED.value
        user_service.repository.update.return_value = recovered_user

        # Recovery should succeed
        final_user = await user_service.process_personality_quiz_completion(
            telegram_id, quiz_responses
        )
        assert final_user.is_personality_detected()
        assert final_user.onboarding_state == OnboardingState.PERSONALITY_DETECTED.value