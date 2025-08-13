"""
Tests for base event classes and validation functionality.
"""

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import patch

import pytest

from src.core.events.base import (
    BaseEventWithValidation,
    DomainEvent,
    EventCategory,
    EventMetadata,
    IntegrationEvent,
    SystemEvent,
    ValidationLevel,
)
from src.core.interfaces import EventPriority, EventValidationError


class TestEventMetadata:
    """Test EventMetadata functionality."""

    def test_metadata_creation(self):
        """Test creating event metadata."""
        timestamp = datetime.utcnow()
        metadata = EventMetadata(
            created_at=timestamp,
            source_version="2.0.0",
            trace_id="trace-123",
            span_id="span-456",
            user_agent="TestAgent/1.0",
            ip_address="192.168.1.1",
            request_id="req-789",
        )

        assert metadata.created_at == timestamp
        assert metadata.source_version == "2.0.0"
        assert metadata.trace_id == "trace-123"
        assert metadata.span_id == "span-456"
        assert metadata.user_agent == "TestAgent/1.0"
        assert metadata.ip_address == "192.168.1.1"
        assert metadata.request_id == "req-789"

    def test_metadata_serialization(self):
        """Test metadata to_dict and from_dict."""
        timestamp = datetime.utcnow()
        original = EventMetadata(
            created_at=timestamp,
            source_version="2.0.0",
            trace_id="trace-123",
        )

        data = original.to_dict()
        restored = EventMetadata.from_dict(data)

        assert restored.created_at == original.created_at
        assert restored.source_version == original.source_version
        assert restored.trace_id == original.trace_id


class TestBaseEventWithValidation:
    """Test BaseEventWithValidation functionality."""

    def test_concrete_event_implementation(self):
        """Test concrete implementation of BaseEventWithValidation."""

        class TestEvent(BaseEventWithValidation):
            def __init__(self, user_id: int = 1, **kwargs):
                super().__init__(
                    user_id=user_id, source_service="test_service", **kwargs
                )

            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE

        event = TestEvent()

        assert event.user_id == 1
        assert event.source_service == "test_service"
        assert event.category == EventCategory.CORE
        assert event.priority == EventPriority.NORMAL
        assert isinstance(event.event_id, str)
        assert isinstance(event.timestamp, datetime)
        assert event.event_type == "core.test"

    def test_event_validation_levels(self):
        """Test different validation levels."""

        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE

        # Normal validation should pass
        event = TestEvent(
            source_service="test", validation_level=ValidationLevel.NORMAL
        )
        assert event.validate()

        # Lenient validation should pass even with issues
        event = TestEvent(
            source_service="test",
            validation_level=ValidationLevel.LENIENT,
            payload={"test": "data"},
        )
        assert event.validate()

    def test_strict_validation(self):
        """Test strict validation requirements."""

        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE

        # Recent timestamp should pass strict validation
        event = TestEvent(
            source_service="test",
            validation_level=ValidationLevel.STRICT,
            timestamp=datetime.utcnow(),
        )
        assert event.validate()

        # Old timestamp should fail strict validation
        old_timestamp = datetime.utcnow() - timedelta(hours=2)
        with pytest.raises(EventValidationError):
            TestEvent(
                source_service="test",
                validation_level=ValidationLevel.STRICT,
                timestamp=old_timestamp,
            )

    def test_payload_size_limit_strict(self):
        """Test payload size limit in strict mode."""

        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE

        # Large payload should fail in strict mode
        large_payload = {"data": "x" * (15 * 1024)}  # 15KB

        with pytest.raises(EventValidationError, match="Payload size exceeds"):
            TestEvent(
                source_service="test",
                validation_level=ValidationLevel.STRICT,
                payload=large_payload,
            )

    def test_event_serialization(self):
        """Test event serialization and deserialization."""

        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE

        original = TestEvent(
            event_id="test-123",
            source_service="test_service",
            user_id=42,
            payload={"key": "value"},
            correlation_id="corr-456",
        )

        # Serialize to dict
        data = original.to_dict()

        # Verify serialized data
        assert data["event_id"] == "test-123"
        assert data["source_service"] == "test_service"
        assert data["user_id"] == 42
        assert data["payload"] == {"key": "value"}
        assert data["correlation_id"] == "corr-456"
        assert data["category"] == EventCategory.CORE.value

        # Deserialize from dict
        restored = TestEvent.from_dict(data)

        # Verify restored event
        assert restored.event_id == original.event_id
        assert restored.source_service == original.source_service
        assert restored.user_id == original.user_id
        assert restored.payload == original.payload
        assert restored.correlation_id == original.correlation_id

    def test_validation_errors(self):
        """Test various validation error conditions."""

        class TestEvent(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE

        # Empty event ID should fail
        with pytest.raises(EventValidationError, match="Event ID must be"):
            TestEvent(event_id="", source_service="test")

        # Empty source service should fail
        with pytest.raises(EventValidationError, match="Source service must be"):
            TestEvent(source_service="")

        # Invalid user_id should fail in normal mode
        with pytest.raises(EventValidationError, match="User ID must be"):
            TestEvent(
                source_service="test",
                user_id="invalid",
                validation_level=ValidationLevel.NORMAL,
            )

    def test_custom_validation_hook(self):
        """Test custom validation hook."""

        class TestEventWithCustomValidation(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE

            def _custom_validation(self, errors):
                if self.payload.get("custom_field") != "required_value":
                    errors.append("Custom field must have required value")

        # Should fail custom validation
        with pytest.raises(
            EventValidationError, match="Custom field must have required value"
        ):
            TestEventWithCustomValidation(
                source_service="test", payload={"custom_field": "wrong_value"}
            )

        # Should pass custom validation
        event = TestEventWithCustomValidation(
            source_service="test", payload={"custom_field": "required_value"}
        )
        assert event.validate()

    def test_lifecycle_hook(self):
        """Test lifecycle hook functionality."""

        hook_called = False

        class TestEventWithHook(BaseEventWithValidation):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.CORE

            def _on_event_created(self):
                nonlocal hook_called
                hook_called = True

        TestEventWithHook(source_service="test")
        assert hook_called


class TestDomainEvent:
    """Test DomainEvent functionality."""

    def test_domain_event_creation(self):
        """Test creating a domain event."""

        class TestDomainEvent(DomainEvent):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.GAMIFICATION

        event = TestDomainEvent(
            user_id=123, source_service="gamification", correlation_id="corr-456"
        )

        assert event.user_id == 123
        assert event.source_service == "gamification"
        assert event.correlation_id == "corr-456"
        assert event.category == EventCategory.GAMIFICATION

    def test_domain_event_requires_user_id(self):
        """Test that domain events require user_id."""

        class TestDomainEvent(DomainEvent):
            def _get_event_category(self) -> EventCategory:
                return EventCategory.GAMIFICATION

        # Should fail without user_id
        with pytest.raises(
            TypeError, match="missing 1 required positional argument: 'user_id'"
        ):
            TestDomainEvent(source_service="test")


class TestSystemEvent:
    """Test SystemEvent functionality."""

    def test_system_event_creation(self):
        """Test creating a system event."""
        event = SystemEvent(
            source_service="health_monitor",
            system_component="database",
            payload={"status": "healthy"},
        )

        assert event.source_service == "health_monitor"
        assert event.system_component == "database"
        assert event.category == EventCategory.SYSTEM
        assert event.payload["system_component"] == "database"
        assert event.payload["status"] == "healthy"


class TestIntegrationEvent:
    """Test IntegrationEvent functionality."""

    def test_integration_event_creation(self):
        """Test creating an integration event."""
        event = IntegrationEvent(
            source_service="payment_processor",
            target_services=["billing", "notification"],
            payload={"transaction_id": "txn-123"},
        )

        assert event.source_service == "payment_processor"
        assert event.target_services == ["billing", "notification"]
        assert event.category == EventCategory.CORE
        assert event.payload["transaction_id"] == "txn-123"

    def test_integration_event_no_targets(self):
        """Test integration event without specific targets."""
        event = IntegrationEvent(
            source_service="payment_processor", payload={"transaction_id": "txn-123"}
        )

        assert event.target_services == []


class TestEventCategoryAndTypes:
    """Test event category and type functionality."""

    def test_event_category_enum(self):
        """Test EventCategory enum values."""
        assert EventCategory.GAMIFICATION.value == "gamification"
        assert EventCategory.NARRATIVE.value == "narrative"
        assert EventCategory.USER.value == "user"
        assert EventCategory.ADMIN.value == "admin"
        assert EventCategory.SYSTEM.value == "system"
        assert EventCategory.CORE.value == "core"

    def test_validation_level_enum(self):
        """Test ValidationLevel enum values."""
        assert ValidationLevel.STRICT.value == "strict"
        assert ValidationLevel.NORMAL.value == "normal"
        assert ValidationLevel.LENIENT.value == "lenient"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
