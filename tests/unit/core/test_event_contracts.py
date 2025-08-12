"""
Tests for the new Event Contracts & Catalog system (ARCH-001.5).

This module tests the comprehensive event contracts system that all
services use for communication in Diana Bot V2.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.core.events.base import (
    BaseEventWithValidation,
    DomainEvent,
    SystemEvent,
    IntegrationEvent,
    EventCategory,
    EventMetadata,
    ValidationLevel,
)
from src.core.events.gamification import (
    PointsAwardedEvent,
    PointsDeductedEvent,
    AchievementUnlockedEvent,
    StreakUpdatedEvent,
    LeaderboardChangedEvent,
    DailyBonusClaimedEvent,
)
from src.core.events.narrative import (
    StoryProgressEvent,
    DecisionMadeEvent,
    ChapterCompletedEvent,
    NarrativeStateChangedEvent,
    CharacterInteractionEvent,
    StoryStartedEvent,
)
from src.core.events.admin import (
    UserRegisteredEvent,
    UserBannedEvent,
    ContentModerationEvent,
    AnalyticsEvent,
    AdminActionPerformedEvent,
    SystemMaintenanceEvent,
)
from src.core.events.core import (
    UserActionEvent,
    ServiceHealthEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
    SystemErrorEvent,
    ConfigurationChangedEvent,
)
from src.core.events.catalog import (
    EventCatalog,
    EventRoute,
    ServiceName,
    event_catalog,
)
from src.core.interfaces import EventPriority, EventValidationError


class TestBaseEventClasses:
    """Test the foundational event base classes."""

    def test_base_event_creation(self):
        """Test creating a base event with validation."""
        
        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE
        
        event = TestEvent(
            source_service="test_service",
            user_id=123,
        )
        
        assert event.source_service == "test_service"
        assert event.user_id == 123
        assert event.category == EventCategory.CORE
        assert event.event_type == "core.test_event"
        assert event.priority == EventPriority.NORMAL
        assert isinstance(event.timestamp, datetime)
        assert len(event.event_id) > 0

    def test_domain_event_requires_user_id(self):
        """Test that domain events require a user_id."""
        
        class TestDomainEvent(DomainEvent):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.GAMIFICATION
        
        # Should work with user_id
        event = TestDomainEvent(
            user_id=123,
            source_service="test_service"
        )
        assert event.user_id == 123
        
        # Should fail without user_id
        with pytest.raises(EventValidationError):
            TestDomainEvent(source_service="test_service")

    def test_system_event_creation(self):
        """Test creating system events."""
        event = SystemEvent(
            source_service="test_service",
            system_component="database"
        )
        
        assert event.source_service == "test_service"
        assert event.system_component == "database"
        assert event.category == EventCategory.SYSTEM

    def test_event_metadata(self):
        """Test event metadata functionality."""
        metadata = EventMetadata(
            created_at=datetime.utcnow(),
            source_version="1.0.0",
            trace_id="test-trace-123"
        )
        
        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE
        
        event = TestEvent(
            source_service="test_service",
            metadata=metadata
        )
        
        assert event.metadata.source_version == "1.0.0"
        assert event.metadata.trace_id == "test-trace-123"

    def test_validation_levels(self):
        """Test different validation strictness levels."""
        
        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE
        
        # Normal validation should pass
        event = TestEvent(
            source_service="test_service",
            validation_level=ValidationLevel.NORMAL
        )
        assert event._validation_level == ValidationLevel.NORMAL
        
        # Lenient validation should be more permissive
        event_lenient = TestEvent(
            source_service="test_service",
            validation_level=ValidationLevel.LENIENT
        )
        assert event_lenient._validation_level == ValidationLevel.LENIENT

    def test_event_serialization(self):
        """Test event serialization and deserialization."""
        
        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE
        
        original_event = TestEvent(
            source_service="test_service",
            user_id=123,
            payload={"test_data": "value"}
        )
        
        # Serialize to dict
        event_dict = original_event.to_dict()
        assert event_dict["source_service"] == "test_service"
        assert event_dict["user_id"] == 123
        assert event_dict["payload"]["test_data"] == "value"
        
        # Deserialize from dict
        restored_event = TestEvent.from_dict(event_dict)
        assert restored_event.source_service == original_event.source_service
        assert restored_event.user_id == original_event.user_id
        assert restored_event.payload == original_event.payload


class TestGamificationEvents:
    """Test gamification domain events."""

    def test_points_awarded_event(self):
        """Test PointsAwardedEvent creation and validation."""
        event = PointsAwardedEvent(
            user_id=123,
            points_amount=50,
            action_type="story_chapter_completed",
            multiplier=1.5,
            bonus_points=10,
            source_service="gamification"
        )
        
        assert event.user_id == 123
        assert event.points_amount == 50
        assert event.action_type == "story_chapter_completed"
        assert event.multiplier == 1.5
        assert event.bonus_points == 10
        assert event.total_points_awarded == 85  # (50 * 1.5) + 10
        assert event.category == EventCategory.GAMIFICATION
        assert event.event_type == "gamification.points_awarded"
        assert event.priority == EventPriority.NORMAL

    def test_points_awarded_validation(self):
        """Test PointsAwardedEvent validation."""
        # Invalid points amount
        with pytest.raises(EventValidationError):
            PointsAwardedEvent(
                user_id=123,
                points_amount=-10,  # Invalid: negative
                action_type="test",
                source_service="gamification"
            )
        
        # Invalid multiplier
        with pytest.raises(EventValidationError):
            PointsAwardedEvent(
                user_id=123,
                points_amount=50,
                action_type="test",
                multiplier=0,  # Invalid: zero
                source_service="gamification"
            )

    def test_achievement_unlocked_event(self):
        """Test AchievementUnlockedEvent creation."""
        event = AchievementUnlockedEvent(
            user_id=123,
            achievement_id="first_story_complete",
            achievement_name="Story Explorer",
            achievement_category="narrative",
            achievement_tier="bronze",
            points_reward=100,
            source_service="gamification"
        )
        
        assert event.achievement_id == "first_story_complete"
        assert event.achievement_name == "Story Explorer"
        assert event.achievement_tier == "bronze"
        assert event.points_reward == 100
        assert event.priority == EventPriority.HIGH  # Achievements are high priority

    def test_streak_updated_event(self):
        """Test StreakUpdatedEvent creation."""
        event = StreakUpdatedEvent(
            user_id=123,
            streak_type="daily_login",
            previous_count=6,
            new_count=7,
            streak_milestone=7,  # Weekly milestone
            source_service="gamification"
        )
        
        assert event.streak_type == "daily_login"
        assert event.previous_count == 6
        assert event.new_count == 7
        assert event.is_continued == True
        assert event.is_broken == False
        assert event.streak_milestone == 7
        assert event.priority == EventPriority.HIGH  # Milestone reached


class TestNarrativeEvents:
    """Test narrative domain events."""

    def test_story_progress_event(self):
        """Test StoryProgressEvent creation."""
        event = StoryProgressEvent(
            user_id=123,
            story_id="diana_story_001",
            chapter_id="chapter_03",
            previous_chapter_id="chapter_02",
            progress_percentage=45.5,
            reading_time_seconds=300,
            interaction_count=5,
            source_service="narrative"
        )
        
        assert event.story_id == "diana_story_001"
        assert event.chapter_id == "chapter_03"
        assert event.previous_chapter_id == "chapter_02"
        assert event.progress_percentage == 45.5
        assert event.reading_time_seconds == 300
        assert event.interaction_count == 5
        assert event.category == EventCategory.NARRATIVE

    def test_decision_made_event(self):
        """Test DecisionMadeEvent creation."""
        event = DecisionMadeEvent(
            user_id=123,
            story_id="diana_story_001",
            chapter_id="chapter_03",
            decision_point_id="choice_001",
            decision_id="option_a",
            decision_text="Help Diana with her research",
            decision_consequences={"relationship_diana": +10, "knowledge_points": +5},
            character_relationships_affected={"diana": 0.1},
            source_service="narrative"
        )
        
        assert event.decision_point_id == "choice_001"
        assert event.decision_id == "option_a"
        assert event.decision_text == "Help Diana with her research"
        assert event.decision_consequences["relationship_diana"] == 10
        assert event.character_relationships_affected["diana"] == 0.1
        assert event.priority == EventPriority.HIGH  # Decisions are important

    def test_chapter_completed_event(self):
        """Test ChapterCompletedEvent creation."""
        event = ChapterCompletedEvent(
            user_id=123,
            story_id="diana_story_001",
            chapter_id="chapter_03",
            chapter_title="The Discovery",
            completion_time_seconds=600,
            decisions_made=3,
            character_interactions=7,
            chapter_rating=5,
            source_service="narrative"
        )
        
        assert event.chapter_title == "The Discovery"
        assert event.completion_time_seconds == 600
        assert event.decisions_made == 3
        assert event.character_interactions == 7
        assert event.chapter_rating == 5
        assert event.priority == EventPriority.HIGH  # Chapter completion is a milestone


class TestAdminEvents:
    """Test admin and system events."""

    def test_user_registered_event(self):
        """Test UserRegisteredEvent creation."""
        telegram_data = {
            "username": "test_user",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en",
            "is_premium": False
        }
        
        event = UserRegisteredEvent(
            user_id=123,
            telegram_data=telegram_data,
            registration_source="telegram",
            referral_code="FRIEND123",
            source_service="telegram_adapter"
        )
        
        assert event.user_id == 123
        assert event.username == "test_user"
        assert event.first_name == "Test"
        assert event.registration_source == "telegram"
        assert event.referral_code == "FRIEND123"
        assert event.category == EventCategory.USER
        assert event.priority == EventPriority.HIGH  # New registrations are important

    def test_user_banned_event(self):
        """Test UserBannedEvent creation."""
        event = UserBannedEvent(
            user_id=123,
            banned_by_admin_id=456,
            ban_reason="Inappropriate content",
            ban_type="temporary",
            ban_duration_hours=24,
            source_service="admin"
        )
        
        assert event.banned_by_admin_id == 456
        assert event.ban_reason == "Inappropriate content"
        assert event.ban_type == "temporary"
        assert event.is_permanent == False
        assert event.priority == EventPriority.CRITICAL  # Bans are critical

    def test_content_moderation_event(self):
        """Test ContentModerationEvent creation."""
        event = ContentModerationEvent(
            content_id="msg_12345",
            content_type="message",
            moderation_action="flagged",
            moderated_by_admin_id=None,  # Automatic moderation
            moderation_reason="Detected inappropriate language",
            automatic_moderation=True,
            confidence_score=0.85,
            affected_user_id=123,
            source_service="moderation"
        )
        
        assert event.content_id == "msg_12345"
        assert event.content_type == "message"
        assert event.moderation_action == "flagged"
        assert event.automatic_moderation == True
        assert event.affected_user_id == 123
        assert event.priority == EventPriority.HIGH  # Flagged content needs attention


class TestCoreEvents:
    """Test core system events."""

    def test_user_action_event(self):
        """Test UserActionEvent creation."""
        event = UserActionEvent(
            user_id=123,
            action_type="message_sent",
            action_data={"message_id": 456, "text": "Hello Diana!"},
            session_id="session_789",
            message_id=456,
            chat_id=111,
            source_service="telegram_adapter"
        )
        
        assert event.user_id == 123
        assert event.action_type == "message_sent"
        assert event.action_data["message_id"] == 456
        assert event.session_id == "session_789"
        assert event.message_id == 456
        assert event.chat_id == 111
        assert event.category == EventCategory.CORE

    def test_service_health_event(self):
        """Test ServiceHealthEvent creation."""
        event = ServiceHealthEvent(
            source_service="gamification",
            health_status="healthy",
            health_metrics={
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "response_time_ms": 120
            },
            system_component="main"
        )
        
        assert event.health_status == "healthy"
        assert event.is_healthy == True
        assert event.requires_attention == False
        assert event.health_metrics["cpu_usage"] == 45.2
        assert event.priority == EventPriority.LOW  # Healthy status is low priority

    def test_service_health_event_unhealthy(self):
        """Test ServiceHealthEvent with unhealthy status."""
        event = ServiceHealthEvent(
            source_service="gamification",
            health_status="unhealthy",
            health_metrics={"error_rate": 25.5},
            system_component="main"
        )
        
        assert event.health_status == "unhealthy"
        assert event.is_healthy == False
        assert event.requires_attention == True
        assert event.priority == EventPriority.HIGH  # Unhealthy services need attention

    def test_system_error_event(self):
        """Test SystemErrorEvent creation."""
        event = SystemErrorEvent(
            source_service="narrative",
            error_type="DatabaseConnectionError",
            error_message="Failed to connect to PostgreSQL",
            error_context={"database_url": "postgresql://localhost:5432/diana"},
            stack_trace="Traceback (most recent call last)...",
            affected_user_id=123,
            system_component="database"
        )
        
        assert event.error_type == "DatabaseConnectionError"
        assert event.error_message == "Failed to connect to PostgreSQL"
        assert event.affected_user_id == 123
        assert event.stack_trace is not None
        assert event.priority == EventPriority.CRITICAL  # Errors are critical


class TestEventCatalog:
    """Test the event catalog and routing system."""

    def test_event_catalog_initialization(self):
        """Test that the event catalog is properly initialized."""
        assert isinstance(event_catalog, EventCatalog)
        
        # Test that we can get routes for known events
        route = event_catalog.get_route(PointsAwardedEvent)
        assert route is not None
        assert route.event_class == PointsAwardedEvent
        assert route.primary_publisher == ServiceName.GAMIFICATION

    def test_event_route_creation(self):
        """Test EventRoute creation and properties."""
        route = EventRoute(
            event_class=PointsAwardedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={ServiceName.ANALYTICS, ServiceName.NOTIFICATION},
            secondary_publishers={ServiceName.NARRATIVE},
            requires_persistence=True
        )
        
        assert route.event_class == PointsAwardedEvent
        assert route.primary_publisher == ServiceName.GAMIFICATION
        assert ServiceName.ANALYTICS in route.subscribers
        assert ServiceName.NARRATIVE in route.secondary_publishers
        assert route.requires_persistence == True
        
        # Test all_publishers property
        all_publishers = route.all_publishers
        assert ServiceName.GAMIFICATION in all_publishers
        assert ServiceName.NARRATIVE in all_publishers

    def test_event_publishers_and_subscribers(self):
        """Test getting publishers and subscribers for events."""
        # Test PointsAwardedEvent routing
        publishers = event_catalog.get_publishers(PointsAwardedEvent)
        subscribers = event_catalog.get_subscribers(PointsAwardedEvent)
        
        assert ServiceName.GAMIFICATION in publishers
        assert ServiceName.ANALYTICS in subscribers
        assert ServiceName.NOTIFICATION in subscribers
        
        # Test UserRegisteredEvent routing
        user_reg_publishers = event_catalog.get_publishers(UserRegisteredEvent)
        user_reg_subscribers = event_catalog.get_subscribers(UserRegisteredEvent)
        
        assert ServiceName.TELEGRAM_ADAPTER in user_reg_publishers
        assert ServiceName.USER_MANAGEMENT in user_reg_subscribers
        assert ServiceName.GAMIFICATION in user_reg_subscribers

    def test_service_event_mapping(self):
        """Test getting events published/subscribed by services."""
        # Test gamification service
        published_events = event_catalog.get_events_published_by(ServiceName.GAMIFICATION)
        subscribed_events = event_catalog.get_events_subscribed_by(ServiceName.GAMIFICATION)
        
        assert PointsAwardedEvent in published_events
        assert AchievementUnlockedEvent in published_events
        assert UserRegisteredEvent in subscribed_events  # Gamification subscribes to user registration

    def test_service_dependencies(self):
        """Test getting service dependencies."""
        deps = event_catalog.get_service_dependencies(ServiceName.GAMIFICATION)
        
        assert "publishes_to" in deps
        assert "subscribes_from" in deps
        
        # Gamification publishes to notification and analytics
        assert ServiceName.NOTIFICATION in deps["publishes_to"]
        assert ServiceName.ANALYTICS in deps["publishes_to"]

    def test_event_catalog_validation(self):
        """Test event catalog validation."""
        errors = event_catalog.validate_routing()
        
        # Should have minimal errors for a well-designed catalog
        assert isinstance(errors, dict)
        assert "missing_subscribers" in errors
        assert "circular_dependencies" in errors
        assert "orphaned_events" in errors

    def test_routing_table_generation(self):
        """Test generating routing table for external systems."""
        routing_table = event_catalog.generate_routing_table()
        
        assert isinstance(routing_table, dict)
        
        # Check that PointsAwardedEvent is in the routing table
        points_event_type = "gamification.points_awarded"
        assert points_event_type in routing_table
        
        route_info = routing_table[points_event_type]
        assert "publishers" in route_info
        assert "subscribers" in route_info
        assert "requires_persistence" in route_info
        assert "delivery_guarantee" in route_info

    def test_event_categories(self):
        """Test getting events by category."""
        gamification_events = event_catalog.get_events_by_category(EventCategory.GAMIFICATION)
        narrative_events = event_catalog.get_events_by_category(EventCategory.NARRATIVE)
        
        assert PointsAwardedEvent in gamification_events
        assert AchievementUnlockedEvent in gamification_events
        assert StoryProgressEvent in narrative_events
        assert DecisionMadeEvent in narrative_events

    def test_critical_events(self):
        """Test identifying critical events."""
        critical_events = event_catalog.get_critical_events()
        
        # Events that require persistence or exactly-once delivery should be critical
        assert UserRegisteredEvent in critical_events  # User registration is critical
        assert DecisionMadeEvent in critical_events  # Decisions are critical for story continuity


class TestEventValidation:
    """Test event validation across different scenarios."""

    def test_strict_validation_mode(self):
        """Test strict validation mode."""
        # Create event with very old timestamp (should fail in strict mode)
        old_timestamp = datetime(2020, 1, 1)
        
        with pytest.raises(EventValidationError, match="too old"):
            PointsAwardedEvent(
                user_id=123,
                points_amount=50,
                action_type="test",
                timestamp=old_timestamp,
                validation_level=ValidationLevel.STRICT,
                source_service="gamification"
            )

    def test_payload_size_validation(self):
        """Test payload size limits in strict mode."""
        # Create a very large payload
        large_payload = {"data": "x" * 15000}  # > 10KB
        
        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE
        
        with pytest.raises(EventValidationError, match="payload size"):
            TestEvent(
                source_service="test",
                payload=large_payload,
                validation_level=ValidationLevel.STRICT
            )

    def test_user_id_validation(self):
        """Test user ID validation in domain events."""
        # Domain events should require positive user IDs
        with pytest.raises(EventValidationError):
            PointsAwardedEvent(
                user_id=-1,  # Invalid: negative
                points_amount=50,
                action_type="test",
                source_service="gamification"
            )


class TestEventInteroperability:
    """Test event system interoperability and integration."""

    def test_event_roundtrip_serialization(self):
        """Test complete serialization roundtrip for all event types."""
        events_to_test = [
            PointsAwardedEvent(
                user_id=123,
                points_amount=50,
                action_type="test",
                source_service="gamification"
            ),
            UserRegisteredEvent(
                user_id=123,
                telegram_data={"username": "test"},
                source_service="telegram_adapter"
            ),
            DecisionMadeEvent(
                user_id=123,
                story_id="test_story",
                chapter_id="chapter_1",
                decision_point_id="choice_1",
                decision_id="option_a",
                decision_text="Test decision",
                decision_consequences={},
                source_service="narrative"
            )
        ]
        
        for original_event in events_to_test:
            # Serialize to dict
            event_dict = original_event.to_dict()
            
            # Deserialize using catalog
            route = event_catalog.get_route_by_event_type(original_event.event_type)
            assert route is not None, f"No route found for {original_event.event_type}"
            
            restored_event = route.event_class.from_dict(event_dict)
            
            # Verify key properties match
            assert restored_event.event_type == original_event.event_type
            assert restored_event.user_id == original_event.user_id
            assert restored_event.source_service == original_event.source_service
            assert restored_event.timestamp == original_event.timestamp

    def test_event_factory_integration(self):
        """Test creating events through the catalog system."""
        # Create a PointsAwardedEvent via the catalog
        route = event_catalog.get_route(PointsAwardedEvent)
        assert route is not None
        
        event = route.event_class(
            user_id=123,
            points_amount=50,
            action_type="test",
            source_service="gamification"
        )
        
        assert isinstance(event, PointsAwardedEvent)
        assert event.user_id == 123
        assert event.points_amount == 50

    def test_service_communication_patterns(self):
        """Test that service communication patterns work as expected."""
        # User registers -> Should trigger multiple service responses
        user_reg_event = UserRegisteredEvent(
            user_id=123,
            telegram_data={"username": "test"},
            source_service="telegram_adapter"
        )
        
        # Get subscribers that should handle this event
        subscribers = event_catalog.get_subscribers(UserRegisteredEvent)
        
        # Verify expected services are subscribed
        expected_subscribers = {
            ServiceName.USER_MANAGEMENT,
            ServiceName.GAMIFICATION,
            ServiceName.NARRATIVE,
            ServiceName.ANALYTICS,
            ServiceName.ADMIN
        }
        
        for expected in expected_subscribers:
            assert expected in subscribers, f"{expected} should subscribe to user registration"
        
        # Points awarded -> Should trigger notifications and analytics
        points_event = PointsAwardedEvent(
            user_id=123,
            points_amount=50,
            action_type="story_complete",
            source_service="gamification"
        )
        
        points_subscribers = event_catalog.get_subscribers(PointsAwardedEvent)
        assert ServiceName.NOTIFICATION in points_subscribers
        assert ServiceName.ANALYTICS in points_subscribers