"""
TDD Tests for Specific Event Types

These tests define the exact behavior expected from the specific event types
outlined in the architecture: GameEvent, NarrativeEvent, AdminEvent, UserEvent, SystemEvent.

These tests should initially FAIL (RED phase) until the event types are implemented.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest

from diana_bot.core.events import (
    AdminEvent,
    EventValidationError,
    GameEvent,
    IEvent,
    NarrativeEvent,
    SystemEvent,
    UserEvent,
)


class TestGameEvent:
    """
    Tests for GameEvent - handles gamification-related events.

    Required fields: user_id, action, points_earned, context
    """

    def test_game_event_creation_with_required_fields(self):
        """Test GameEvent creation with all required fields."""
        event = GameEvent(
            user_id=12345,
            action="daily_login",
            points_earned=10,
            context={"streak_day": 5, "bonus_multiplier": 1.5},
        )

        assert event.user_id == 12345
        assert event.action == "daily_login"
        assert event.points_earned == 10
        assert event.context["streak_day"] == 5
        assert event.context["bonus_multiplier"] == 1.5

        # Should inherit from IEvent
        assert isinstance(event, IEvent)
        assert event.type == "game.daily_login"

    def test_game_event_validates_required_fields(self):
        """Test that GameEvent validates required fields."""
        # Missing user_id
        with pytest.raises((TypeError, ValueError)):
            GameEvent(action="login", points_earned=10, context={})

        # Missing action
        with pytest.raises((TypeError, ValueError)):
            GameEvent(user_id=123, points_earned=10, context={})

        # Missing points_earned
        with pytest.raises((TypeError, ValueError)):
            GameEvent(user_id=123, action="login", context={})

        # Missing context (should be optional with default {})
        event = GameEvent(user_id=123, action="login", points_earned=10)
        assert event.context == {}

    def test_game_event_validates_field_types(self):
        """Test that GameEvent validates field data types."""
        # user_id must be integer
        with pytest.raises((TypeError, ValueError)):
            GameEvent(user_id="not-int", action="login", points_earned=10)

        # action must be string
        with pytest.raises((TypeError, ValueError)):
            GameEvent(user_id=123, action=123, points_earned=10)

        # points_earned must be integer or float
        with pytest.raises((TypeError, ValueError)):
            GameEvent(user_id=123, action="login", points_earned="not-numeric")

        # context must be dict
        with pytest.raises((TypeError, ValueError)):
            GameEvent(user_id=123, action="login", points_earned=10, context="not-dict")

    def test_game_event_validates_action_types(self):
        """Test that GameEvent validates allowed action types."""
        valid_actions = [
            "daily_login",
            "message_sent",
            "story_completed",
            "achievement_unlocked",
            "referral_bonus",
            "vip_purchase",
            "streak_bonus",
            "challenge_completed",
        ]

        for action in valid_actions:
            event = GameEvent(user_id=123, action=action, points_earned=10)
            assert event.action == action

        # Invalid actions should be rejected
        with pytest.raises(EventValidationError):
            GameEvent(user_id=123, action="invalid_action", points_earned=10)

    def test_game_event_validates_points_range(self):
        """Test that GameEvent validates point values are reasonable."""
        # Valid point ranges
        valid_points = [0, 1, 10, 100, 1000, 10000]

        for points in valid_points:
            event = GameEvent(user_id=123, action="daily_login", points_earned=points)
            assert event.points_earned == points

        # Negative points should be rejected
        with pytest.raises(EventValidationError):
            GameEvent(user_id=123, action="daily_login", points_earned=-10)

        # Excessively large points should be rejected (> 1 million)
        with pytest.raises(EventValidationError):
            GameEvent(user_id=123, action="daily_login", points_earned=1000001)

    def test_game_event_context_validation(self):
        """Test that GameEvent context contains valid data."""
        # Valid context examples
        valid_contexts = [
            {"source": "telegram_bot"},
            {"streak_day": 7, "bonus_applied": True},
            {"challenge_id": "weekly_login", "difficulty": "easy"},
            {"referrer_id": 456, "referral_tier": 2},
        ]

        for context in valid_contexts:
            event = GameEvent(
                user_id=123, action="daily_login", points_earned=10, context=context
            )
            assert event.context == context

    def test_game_event_serialization(self):
        """Test GameEvent serialization includes all game-specific fields."""
        event = GameEvent(
            user_id=12345,
            action="achievement_unlocked",
            points_earned=100,
            context={"achievement_id": "first_week", "tier": "bronze"},
        )

        event_dict = event.to_dict()

        assert event_dict["type"] == "game.achievement_unlocked"
        assert event_dict["data"]["user_id"] == 12345
        assert event_dict["data"]["action"] == "achievement_unlocked"
        assert event_dict["data"]["points_earned"] == 100
        assert event_dict["data"]["context"]["achievement_id"] == "first_week"

    def test_game_event_deserialization(self):
        """Test GameEvent can be reconstructed from serialized data."""
        original_event = GameEvent(
            user_id=12345,
            action="daily_login",
            points_earned=50,
            context={"streak": 10},
        )

        # Serialize and deserialize
        event_dict = original_event.to_dict()
        reconstructed = GameEvent.from_dict(event_dict)

        assert reconstructed.user_id == original_event.user_id
        assert reconstructed.action == original_event.action
        assert reconstructed.points_earned == original_event.points_earned
        assert reconstructed.context == original_event.context

    def test_game_event_auto_type_generation(self):
        """Test that GameEvent auto-generates type from action."""
        event = GameEvent(user_id=123, action="daily_login", points_earned=10)
        assert event.type == "game.daily_login"

        event2 = GameEvent(
            user_id=123, action="achievement_unlocked", points_earned=100
        )
        assert event2.type == "game.achievement_unlocked"


class TestNarrativeEvent:
    """
    Tests for NarrativeEvent - handles story progression events.

    Required fields: user_id, chapter_id, decision_made, character_impact
    """

    def test_narrative_event_creation_with_required_fields(self):
        """Test NarrativeEvent creation with all required fields."""
        event = NarrativeEvent(
            user_id=12345,
            chapter_id="chapter_01_forest",
            decision_made="help_stranger",
            character_impact={"Diana": 5, "Mysterious_Stranger": 10},
        )

        assert event.user_id == 12345
        assert event.chapter_id == "chapter_01_forest"
        assert event.decision_made == "help_stranger"
        assert event.character_impact["Diana"] == 5
        assert event.character_impact["Mysterious_Stranger"] == 10

        # Should inherit from IEvent
        assert isinstance(event, IEvent)
        assert event.type == "narrative.decision_made"

    def test_narrative_event_validates_required_fields(self):
        """Test that NarrativeEvent validates required fields."""
        # Missing user_id
        with pytest.raises((TypeError, ValueError)):
            NarrativeEvent(
                chapter_id="ch01", decision_made="choice1", character_impact={}
            )

        # Missing chapter_id
        with pytest.raises((TypeError, ValueError)):
            NarrativeEvent(user_id=123, decision_made="choice1", character_impact={})

        # Missing decision_made
        with pytest.raises((TypeError, ValueError)):
            NarrativeEvent(user_id=123, chapter_id="ch01", character_impact={})

        # Missing character_impact (should default to {})
        event = NarrativeEvent(user_id=123, chapter_id="ch01", decision_made="choice1")
        assert event.character_impact == {}

    def test_narrative_event_validates_field_types(self):
        """Test that NarrativeEvent validates field data types."""
        # user_id must be integer
        with pytest.raises((TypeError, ValueError)):
            NarrativeEvent(
                user_id="not-int", chapter_id="ch01", decision_made="choice1"
            )

        # chapter_id must be string
        with pytest.raises((TypeError, ValueError)):
            NarrativeEvent(user_id=123, chapter_id=123, decision_made="choice1")

        # decision_made must be string
        with pytest.raises((TypeError, ValueError)):
            NarrativeEvent(user_id=123, chapter_id="ch01", decision_made=123)

        # character_impact must be dict
        with pytest.raises((TypeError, ValueError)):
            NarrativeEvent(
                user_id=123,
                chapter_id="ch01",
                decision_made="choice1",
                character_impact="not-dict",
            )

    def test_narrative_event_validates_chapter_format(self):
        """Test that NarrativeEvent validates chapter ID format."""
        valid_chapters = [
            "chapter_01_intro",
            "chapter_02_forest",
            "chapter_10_finale",
            "epilogue_01",
        ]

        for chapter in valid_chapters:
            event = NarrativeEvent(
                user_id=123, chapter_id=chapter, decision_made="test_choice"
            )
            assert event.chapter_id == chapter

        # Invalid chapter formats
        invalid_chapters = [
            "",  # Empty
            "ch1",  # Too short
            "chapter_",  # Incomplete
            "invalid chapter",  # Spaces
            "chapter-01-test",  # Wrong separator
        ]

        for invalid_chapter in invalid_chapters:
            with pytest.raises(EventValidationError):
                NarrativeEvent(
                    user_id=123, chapter_id=invalid_chapter, decision_made="choice1"
                )

    def test_narrative_event_validates_character_impact(self):
        """Test that character impact contains valid character names and values."""
        valid_impacts = [
            {"Diana": 5},
            {"Diana": -3, "Marcus": 7},
            {"Mysterious_Stranger": 10, "Diana": 2, "Village_Elder": -1},
        ]

        for impact in valid_impacts:
            event = NarrativeEvent(
                user_id=123,
                chapter_id="chapter_01",
                decision_made="choice1",
                character_impact=impact,
            )
            assert event.character_impact == impact

        # Impact values must be integers in valid range
        with pytest.raises(EventValidationError):
            NarrativeEvent(
                user_id=123,
                chapter_id="chapter_01",
                decision_made="choice1",
                character_impact={"Diana": "not-number"},
            )

        # Impact values must be within range (-10 to +10)
        with pytest.raises(EventValidationError):
            NarrativeEvent(
                user_id=123,
                chapter_id="chapter_01",
                decision_made="choice1",
                character_impact={"Diana": 15},  # Too high
            )

    def test_narrative_event_optional_metadata(self):
        """Test NarrativeEvent supports optional metadata fields."""
        event = NarrativeEvent(
            user_id=123,
            chapter_id="chapter_01",
            decision_made="help_villager",
            character_impact={"Diana": 3},
            choice_time_seconds=45.7,
            previous_choices=["ignore_stranger", "enter_forest"],
            unlocked_content=["character_backstory_diana"],
        )

        assert event.choice_time_seconds == 45.7
        assert event.previous_choices == ["ignore_stranger", "enter_forest"]
        assert event.unlocked_content == ["character_backstory_diana"]

    def test_narrative_event_serialization(self):
        """Test NarrativeEvent serialization includes all fields."""
        event = NarrativeEvent(
            user_id=12345,
            chapter_id="chapter_03_castle",
            decision_made="trust_diana",
            character_impact={"Diana": 8, "Lord_Blackwood": -5},
            choice_time_seconds=32.1,
        )

        event_dict = event.to_dict()

        assert event_dict["type"] == "narrative.decision_made"
        assert event_dict["data"]["user_id"] == 12345
        assert event_dict["data"]["chapter_id"] == "chapter_03_castle"
        assert event_dict["data"]["decision_made"] == "trust_diana"
        assert event_dict["data"]["character_impact"]["Diana"] == 8
        assert event_dict["data"]["choice_time_seconds"] == 32.1


class TestAdminEvent:
    """
    Tests for AdminEvent - handles administrative actions.

    Required fields: admin_id, action_type, target_user, details
    """

    def test_admin_event_creation_with_required_fields(self):
        """Test AdminEvent creation with all required fields."""
        event = AdminEvent(
            admin_id=99999,
            action_type="user_banned",
            target_user=12345,
            details={
                "reason": "spam",
                "duration_days": 7,
                "evidence": "multiple_reports",
            },
        )

        assert event.admin_id == 99999
        assert event.action_type == "user_banned"
        assert event.target_user == 12345
        assert event.details["reason"] == "spam"

        # Should inherit from IEvent
        assert isinstance(event, IEvent)
        assert event.type == "admin.user_banned"

    def test_admin_event_validates_admin_permissions(self):
        """Test that AdminEvent validates admin has permission for action."""
        # This would integrate with permission system in real implementation
        valid_admin_actions = [
            ("user_banned", 12345),
            ("user_unbanned", 12345),
            ("points_adjusted", 12345),
            ("content_deleted", None),  # Global action
            ("system_maintenance", None),
        ]

        for action_type, target in valid_admin_actions:
            event = AdminEvent(
                admin_id=99999,
                action_type=action_type,
                target_user=target,
                details={"reason": "test"},
            )
            assert event.action_type == action_type
            assert event.target_user == target

    def test_admin_event_validates_action_types(self):
        """Test that AdminEvent validates allowed administrative actions."""
        valid_actions = [
            "user_banned",
            "user_unbanned",
            "user_warned",
            "points_adjusted",
            "content_deleted",
            "system_config_changed",
            "database_migration",
            "feature_toggle",
            "user_role_changed",
            "bulk_operation",
        ]

        for action in valid_actions:
            event = AdminEvent(
                admin_id=99999, action_type=action, target_user=12345, details={}
            )
            assert event.action_type == action

        # Invalid actions should be rejected
        with pytest.raises(EventValidationError):
            AdminEvent(
                admin_id=99999,
                action_type="invalid_admin_action",
                target_user=12345,
                details={},
            )

    def test_admin_event_requires_audit_details(self):
        """Test that AdminEvent requires sufficient detail for audit trail."""
        # Should require reason for destructive actions
        destructive_actions = ["user_banned", "content_deleted", "points_adjusted"]

        for action in destructive_actions:
            # Missing reason should be rejected
            with pytest.raises(EventValidationError):
                AdminEvent(
                    admin_id=99999, action_type=action, target_user=12345, details={}
                )

            # Valid with reason
            event = AdminEvent(
                admin_id=99999,
                action_type=action,
                target_user=12345,
                details={"reason": "Valid reason for audit"},
            )
            assert "reason" in event.details

    def test_admin_event_validates_target_user(self):
        """Test AdminEvent validates target user when required."""
        # User-specific actions require target_user
        user_actions = ["user_banned", "user_warned", "points_adjusted"]

        for action in user_actions:
            # Missing target should be rejected
            with pytest.raises(EventValidationError):
                AdminEvent(
                    admin_id=99999,
                    action_type=action,
                    target_user=None,
                    details={"reason": "test"},
                )

        # Global actions don't require target_user
        global_actions = ["system_maintenance", "database_migration"]

        for action in global_actions:
            event = AdminEvent(
                admin_id=99999,
                action_type=action,
                target_user=None,
                details={"reason": "scheduled maintenance"},
            )
            assert event.target_user is None

    def test_admin_event_sensitive_data_handling(self):
        """Test that AdminEvent properly handles sensitive information."""
        # Should allow sensitive details for legitimate admin actions
        event = AdminEvent(
            admin_id=99999,
            action_type="user_banned",
            target_user=12345,
            details={
                "reason": "Terms violation",
                "reported_content": "inappropriate message content",
                "reporter_ids": [67890, 11111],
            },
        )

        # Sensitive fields should be marked for encryption/careful handling
        assert event.contains_sensitive_data() is True

        # Non-sensitive admin events
        maintenance_event = AdminEvent(
            admin_id=99999,
            action_type="system_maintenance",
            target_user=None,
            details={"maintenance_type": "scheduled_update"},
        )

        assert maintenance_event.contains_sensitive_data() is False


class TestUserEvent:
    """
    Tests for UserEvent - handles general user actions.

    Required fields: user_id, event_type, user_data
    """

    def test_user_event_creation_with_required_fields(self):
        """Test UserEvent creation with all required fields."""
        event = UserEvent(
            user_id=12345,
            event_type="profile_updated",
            user_data={
                "changed_fields": ["username", "language"],
                "old_username": "oldname",
                "new_username": "newname",
            },
        )

        assert event.user_id == 12345
        assert event.event_type == "profile_updated"
        assert event.user_data["new_username"] == "newname"

        # Should inherit from IEvent
        assert isinstance(event, IEvent)
        assert event.type == "user.profile_updated"

    def test_user_event_validates_event_types(self):
        """Test UserEvent validates allowed user event types."""
        valid_events = [
            "registered",
            "login",
            "logout",
            "profile_updated",
            "settings_changed",
            "subscription_started",
            "subscription_cancelled",
            "achievement_viewed",
            "content_shared",
            "feedback_submitted",
            "language_changed",
        ]

        for event_type in valid_events:
            event = UserEvent(
                user_id=123, event_type=event_type, user_data={"test": True}
            )
            assert event.event_type == event_type

    def test_user_event_privacy_compliance(self):
        """Test UserEvent respects privacy and data protection requirements."""
        # Should allow tracking necessary user data
        event = UserEvent(
            user_id=123,
            event_type="login",
            user_data={
                "login_time": datetime.now(timezone.utc).isoformat(),
                "device_type": "mobile",
                "app_version": "2.1.0",
            },
        )

        # Should not allow PII beyond user_id
        with pytest.raises(EventValidationError):
            UserEvent(
                user_id=123,
                event_type="profile_updated",
                user_data={
                    "email": "user@example.com",  # PII not allowed
                    "phone": "+1234567890",  # PII not allowed
                },
            )

    def test_user_event_data_minimization(self):
        """Test UserEvent enforces data minimization principles."""
        # Should limit user_data size to prevent excessive data collection
        reasonable_data = {"setting": "dark_mode", "value": True}

        event = UserEvent(
            user_id=123, event_type="settings_changed", user_data=reasonable_data
        )
        assert event.user_data == reasonable_data

        # Should reject excessive data
        excessive_data = {"large_field": "x" * 10000}

        with pytest.raises(EventValidationError):
            UserEvent(
                user_id=123, event_type="settings_changed", user_data=excessive_data
            )


class TestSystemEvent:
    """
    Tests for SystemEvent - handles system-level events.

    Required fields: component, event_type, system_data
    """

    def test_system_event_creation_with_required_fields(self):
        """Test SystemEvent creation with all required fields."""
        event = SystemEvent(
            component="gamification_service",
            event_type="service_started",
            system_data={
                "version": "1.2.3",
                "startup_time_ms": 1234,
                "database_migrations": 5,
            },
        )

        assert event.component == "gamification_service"
        assert event.event_type == "service_started"
        assert event.system_data["version"] == "1.2.3"

        # Should inherit from IEvent
        assert isinstance(event, IEvent)
        assert event.type == "system.service_started"

    def test_system_event_validates_components(self):
        """Test SystemEvent validates known system components."""
        valid_components = [
            "telegram_adapter",
            "diana_master",
            "gamification_service",
            "narrative_service",
            "admin_service",
            "event_bus",
            "database",
            "redis_cache",
            "payment_service",
        ]

        for component in valid_components:
            event = SystemEvent(
                component=component,
                event_type="health_check",
                system_data={"status": "healthy"},
            )
            assert event.component == component

    def test_system_event_validates_event_types(self):
        """Test SystemEvent validates system event types."""
        valid_events = [
            "service_started",
            "service_stopped",
            "health_check",
            "error_occurred",
            "performance_alert",
            "database_migration",
            "cache_cleared",
            "backup_completed",
            "config_updated",
            "scale_event",
        ]

        for event_type in valid_events:
            event = SystemEvent(
                component="test_service", event_type=event_type, system_data={}
            )
            assert event.event_type == event_type

    def test_system_event_monitoring_integration(self):
        """Test SystemEvent integrates with monitoring systems."""
        error_event = SystemEvent(
            component="gamification_service",
            event_type="error_occurred",
            system_data={
                "error_type": "DatabaseConnectionError",
                "error_message": "Connection timeout",
                "stack_trace": "...",
                "severity": "critical",
            },
        )

        # Should be marked for alerting
        assert error_event.should_alert() is True
        assert error_event.get_severity() == "critical"

        # Regular events don't need alerting
        health_event = SystemEvent(
            component="gamification_service",
            event_type="health_check",
            system_data={"status": "healthy", "response_time_ms": 45},
        )

        assert health_event.should_alert() is False


class TestEventTypeIntegration:
    """
    Tests for integration between different event types and cross-cutting concerns.
    """

    def test_all_events_inherit_from_ievent(self):
        """Test that all event types properly inherit from IEvent."""
        events = [
            GameEvent(user_id=123, action="daily_login", points_earned=10),
            NarrativeEvent(user_id=123, chapter_id="ch01", decision_made="choice1"),
            AdminEvent(
                admin_id=999,
                action_type="user_warned",
                target_user=123,
                details={"reason": "test"},
            ),
            UserEvent(user_id=123, event_type="login", user_data={}),
            SystemEvent(component="test", event_type="health_check", system_data={}),
        ]

        for event in events:
            assert isinstance(event, IEvent)
            assert hasattr(event, "id")
            assert hasattr(event, "type")
            assert hasattr(event, "timestamp")
            assert hasattr(event, "data")

    def test_event_correlation_across_types(self):
        """Test that events can be correlated across different types."""
        correlation_id = str(uuid.uuid4())

        # User starts story chapter
        narrative_event = NarrativeEvent(
            user_id=123,
            chapter_id="chapter_01",
            decision_made="enter_forest",
            correlation_id=correlation_id,
        )

        # Points are awarded for story progress
        game_event = GameEvent(
            user_id=123,
            action="story_completed",
            points_earned=50,
            context={"chapter_id": "chapter_01"},
            correlation_id=correlation_id,
        )

        # User profile is updated
        user_event = UserEvent(
            user_id=123,
            event_type="achievement_unlocked",
            user_data={"achievement": "first_chapter"},
            correlation_id=correlation_id,
        )

        # All events should have same correlation ID
        assert narrative_event.correlation_id == correlation_id
        assert game_event.correlation_id == correlation_id
        assert user_event.correlation_id == correlation_id

    def test_event_type_routing_patterns(self):
        """Test that event types generate correct routing patterns for pub/sub."""
        events_and_expected_types = [
            (
                GameEvent(user_id=123, action="daily_login", points_earned=10),
                "game.daily_login",
            ),
            (
                NarrativeEvent(user_id=123, chapter_id="ch01", decision_made="choice1"),
                "narrative.decision_made",
            ),
            (
                AdminEvent(
                    admin_id=999,
                    action_type="user_banned",
                    target_user=123,
                    details={"reason": "test"},
                ),
                "admin.user_banned",
            ),
            (
                UserEvent(user_id=123, event_type="profile_updated", user_data={}),
                "user.profile_updated",
            ),
            (
                SystemEvent(
                    component="database",
                    event_type="migration_completed",
                    system_data={},
                ),
                "system.migration_completed",
            ),
        ]

        for event, expected_type in events_and_expected_types:
            assert event.type == expected_type

    def test_event_serialization_consistency(self):
        """Test that all event types serialize consistently."""
        events = [
            GameEvent(user_id=123, action="daily_login", points_earned=10),
            NarrativeEvent(user_id=123, chapter_id="ch01", decision_made="choice1"),
            AdminEvent(
                admin_id=999,
                action_type="user_warned",
                target_user=123,
                details={"reason": "test"},
            ),
            UserEvent(user_id=123, event_type="login", user_data={}),
            SystemEvent(component="test", event_type="health_check", system_data={}),
        ]

        for event in events:
            # Should serialize to dict
            event_dict = event.to_dict()
            assert isinstance(event_dict, dict)
            assert "id" in event_dict
            assert "type" in event_dict
            assert "timestamp" in event_dict
            assert "data" in event_dict

            # Should serialize to JSON
            json_str = event.to_json()
            assert isinstance(json_str, str)
            assert len(json_str) > 0

            # Should deserialize back to same event
            reconstructed = type(event).from_dict(event_dict)
            assert reconstructed.id == event.id
            assert reconstructed.type == event.type
            assert reconstructed.data == event.data

    def test_event_timestamp_consistency(self):
        """Test that all event types handle timestamps consistently."""
        specific_time = datetime.now(timezone.utc)

        events = [
            GameEvent(
                user_id=123,
                action="daily_login",
                points_earned=10,
                timestamp=specific_time,
            ),
            NarrativeEvent(
                user_id=123,
                chapter_id="ch01",
                decision_made="choice1",
                timestamp=specific_time,
            ),
            AdminEvent(
                admin_id=999,
                action_type="user_warned",
                target_user=123,
                details={"reason": "test"},
                timestamp=specific_time,
            ),
            UserEvent(
                user_id=123, event_type="login", user_data={}, timestamp=specific_time
            ),
            SystemEvent(
                component="test",
                event_type="health_check",
                system_data={},
                timestamp=specific_time,
            ),
        ]

        for event in events:
            assert event.timestamp == specific_time

            # Serialized timestamp should be ISO format
            event_dict = event.to_dict()
            assert event_dict["timestamp"] == specific_time.isoformat()

    def test_event_validation_error_handling(self):
        """Test that event validation errors are handled consistently."""
        validation_test_cases = [
            # GameEvent with invalid action
            (
                lambda: GameEvent(
                    user_id=123, action="invalid_action", points_earned=10
                ),
                EventValidationError,
            ),
            # NarrativeEvent with invalid chapter format
            (
                lambda: NarrativeEvent(
                    user_id=123, chapter_id="invalid", decision_made="choice1"
                ),
                EventValidationError,
            ),
            # AdminEvent with insufficient permissions
            (
                lambda: AdminEvent(
                    admin_id=999, action_type="user_banned", target_user=123, details={}
                ),
                EventValidationError,
            ),
            # UserEvent with PII
            (
                lambda: UserEvent(
                    user_id=123,
                    event_type="profile_updated",
                    user_data={"email": "test@test.com"},
                ),
                EventValidationError,
            ),
            # SystemEvent with invalid component
            (
                lambda: SystemEvent(
                    component="invalid_component", event_type="test", system_data={}
                ),
                EventValidationError,
            ),
        ]

        for event_creator, expected_exception in validation_test_cases:
            with pytest.raises(expected_exception):
                event_creator()
