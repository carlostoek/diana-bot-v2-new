#!/usr/bin/env python3
"""
Diana Bot V2 - Implementation Validation Script

This script validates the Event Bus implementation without requiring external dependencies.
It tests the core interfaces, events, and basic functionality.
"""

import sys
import traceback
from datetime import datetime
from typing import Dict, Any

def test_interfaces():
    """Test that all interfaces are properly defined."""
    print("Testing core interfaces...")
    
    try:
        from src.core.interfaces import (
            IEvent, IEventBus, IEventHandler, IEventStore, IEventMetrics,
            EventBusConfig, EventPriority, EventStatus
        )
        print("✅ Core interfaces imported successfully")
        
        # Test EventBusConfig creation
        config = EventBusConfig()
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.max_retry_attempts == 3
        print("✅ EventBusConfig creation works")
        
        # Test EventPriority enum
        assert EventPriority.LOW.value == 1
        assert EventPriority.CRITICAL.value == 4
        print("✅ EventPriority enum works")
        
        return True
        
    except Exception as e:
        print(f"❌ Interface test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_events():
    """Test event creation and serialization."""
    print("\nTesting event implementations...")
    
    try:
        from src.core.events import (
            BaseEvent, PointsAwardedEvent, AchievementUnlockedEvent,
            UserRegisteredEvent, EventType, EventFactory
        )
        from src.core.interfaces import EventPriority
        
        print("✅ Event classes imported successfully")
        
        # Test BaseEvent creation
        base_event = BaseEvent(
            _event_id="test-123",
            _event_type="test.event",
            _timestamp=datetime.utcnow(),
            _source_service="test_service",
            _priority=EventPriority.HIGH,
            _payload={"key": "value"}
        )
        
        assert base_event.event_id == "test-123"
        assert base_event.event_type == "test.event"
        assert base_event.priority == EventPriority.HIGH
        print("✅ BaseEvent creation works")
        
        # Test event serialization
        event_dict = base_event.to_dict()
        assert event_dict["event_id"] == "test-123"
        assert event_dict["event_type"] == "test.event"
        print("✅ Event serialization works")
        
        # Test event deserialization
        restored_event = BaseEvent.from_dict(event_dict)
        assert restored_event.event_id == base_event.event_id
        assert restored_event.event_type == base_event.event_type
        print("✅ Event deserialization works")
        
        # Test specific event types
        points_event = PointsAwardedEvent(
            user_id=12345,
            points_amount=100,
            action_type="test_action"
        )
        assert points_event.user_id == 12345
        assert points_event.points_amount == 100
        assert points_event.event_type == EventType.POINTS_AWARDED
        print("✅ PointsAwardedEvent creation works")
        
        # Test achievement event
        achievement_event = AchievementUnlockedEvent(
            user_id=12345,
            achievement_id="first_story",
            achievement_name="First Story",
            achievement_category="narrative"
        )
        assert achievement_event.user_id == 12345
        assert achievement_event.achievement_id == "first_story"
        assert achievement_event.event_type == EventType.ACHIEVEMENT_UNLOCKED
        print("✅ AchievementUnlockedEvent creation works")
        
        # Test user registration event
        user_event = UserRegisteredEvent(
            user_id=67890,
            username="testuser",
            first_name="Test",
            language_code="en"
        )
        assert user_event.payload["user_id"] == 67890
        assert user_event.payload["username"] == "testuser"
        assert user_event.event_type == EventType.USER_REGISTERED
        print("✅ UserRegisteredEvent creation works")
        
        # Test EventFactory
        factory_event = EventFactory.create_event(
            EventType.POINTS_AWARDED,
            user_id=12345,
            points_amount=50,
            action_type="factory_test"
        )
        assert isinstance(factory_event, PointsAwardedEvent)
        assert factory_event.points_amount == 50
        print("✅ EventFactory creation works")
        
        supported_types = EventFactory.get_supported_event_types()
        assert EventType.POINTS_AWARDED in supported_types
        assert EventType.ACHIEVEMENT_UNLOCKED in supported_types
        print("✅ EventFactory supported types works")
        
        return True
        
    except Exception as e:
        print(f"❌ Event test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_base_handler():
    """Test the base event handler implementation."""
    print("\nTesting base event handler...")
    
    try:
        # Check if Redis-dependent components are available
        from src.core import BaseEventHandler
        
        if BaseEventHandler is None:
            print("⚠️ BaseEventHandler not available (Redis dependency missing)")
            print("✅ Redis-dependent components properly isolated")
            return True
        
        from src.core.events import EventType
        from src.core.interfaces import IEvent
        
        # Create a test handler
        class TestHandler(BaseEventHandler):
            def __init__(self):
                super().__init__("test_service", "test_handler")
                self.add_supported_event_type(EventType.POINTS_AWARDED)
                self.processed_events = []
            
            async def _process_event(self, event: IEvent) -> bool:
                self.processed_events.append(event)
                return True
        
        handler = TestHandler()
        
        # Test basic properties
        assert handler.handler_id == "test_handler"
        assert handler.service_name == "test_service"
        assert EventType.POINTS_AWARDED in handler.supported_event_types
        print("✅ BaseEventHandler properties work")
        
        # Test metrics
        metrics = handler.get_performance_metrics()
        assert metrics["handler_id"] == "test_handler"
        assert metrics["service_name"] == "test_service"
        assert metrics["processing_count"] == 0
        print("✅ BaseEventHandler metrics work")
        
        return True
        
    except Exception as e:
        print(f"❌ Base handler test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_event_validation():
    """Test event validation logic."""
    print("\nTesting event validation...")
    
    try:
        from src.core.events import BaseEvent
        from src.core.interfaces import EventValidationError
        from datetime import datetime
        
        # Valid event should pass
        valid_event = BaseEvent(
            _event_id="valid-123",
            _event_type="test.event",
            _timestamp=datetime.utcnow(),
            _source_service="test_service"
        )
        assert valid_event.validate() is True
        print("✅ Valid event validation works")
        
        # Test invalid events
        try:
            BaseEvent(
                _event_id="",  # Empty ID should fail
                _event_type="test.event", 
                _timestamp=datetime.utcnow(),
                _source_service="test_service"
            )
            assert False, "Should have raised EventValidationError"
        except EventValidationError:
            print("✅ Invalid event validation works (empty ID)")
        
        try:
            BaseEvent(
                _event_id="test-123",
                _event_type="",  # Empty type should fail
                _timestamp=datetime.utcnow(),
                _source_service="test_service"
            )
            assert False, "Should have raised EventValidationError"
        except EventValidationError:
            print("✅ Invalid event validation works (empty type)")
        
        return True
        
    except Exception as e:
        print(f"❌ Event validation test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_architecture_compliance():
    """Test that implementation follows Clean Architecture principles."""
    print("\nTesting Clean Architecture compliance...")
    
    try:
        # Test interface segregation
        from src.core.interfaces import IEvent, IEventBus, IEventHandler
        
        # Check that interfaces are properly abstract
        try:
            # Should not be able to instantiate interfaces directly
            event = IEvent()
            assert False, "Should not be able to instantiate IEvent interface"
        except TypeError:
            print("✅ IEvent is properly abstract")
        
        try:
            bus = IEventBus()
            assert False, "Should not be able to instantiate IEventBus interface"
        except TypeError:
            print("✅ IEventBus is properly abstract")
        
        try:
            handler = IEventHandler()
            assert False, "Should not be able to instantiate IEventHandler interface"
        except TypeError:
            print("✅ IEventHandler is properly abstract")
        
        # Test dependency inversion - implementations depend on abstractions
        from src.core.events import BaseEvent
        from src.core.interfaces import IEvent
        
        # BaseEvent should implement IEvent
        assert issubclass(BaseEvent, IEvent)
        print("✅ BaseEvent properly implements IEvent interface")
        
        return True
        
    except Exception as e:
        print(f"❌ Architecture compliance test failed: {str(e)}")
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("Diana Bot V2 - Event Bus Implementation Validation")
    print("=" * 60)
    
    tests = [
        test_interfaces,
        test_events,
        test_base_handler,
        test_event_validation,
        test_architecture_compliance
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Validation Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All validation tests passed! The Event Bus implementation is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit(main())