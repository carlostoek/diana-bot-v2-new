"""
Tests for the Event Catalog system.
"""

from typing import Set

import pytest

from src.core.events.admin import UserBannedEvent, UserRegisteredEvent
from src.core.events.base import EventCategory
from src.core.events.catalog import (
    EventCatalog,
    EventRoute,
    ServiceName,
    event_catalog,
    get_event_publishers,
    get_event_subscribers,
)
from src.core.events.core import ServiceHealthEvent, UserActionEvent
from src.core.events.gamification import AchievementUnlockedEvent, PointsAwardedEvent
from src.core.events.narrative import DecisionMadeEvent, StoryProgressEvent


class TestEventRoute:
    """Test EventRoute functionality."""

    def test_event_route_creation(self):
        """Test creating an EventRoute."""
        route = EventRoute(
            event_class=PointsAwardedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={ServiceName.ANALYTICS, ServiceName.NOTIFICATION},
            secondary_publishers={ServiceName.NARRATIVE},
            requires_persistence=True,
        )

        assert route.event_class == PointsAwardedEvent
        assert route.primary_publisher == ServiceName.GAMIFICATION
        assert ServiceName.ANALYTICS in route.subscribers
        assert ServiceName.NOTIFICATION in route.subscribers
        assert ServiceName.NARRATIVE in route.secondary_publishers
        assert route.requires_persistence

    def test_all_publishers_property(self):
        """Test all_publishers property."""
        route = EventRoute(
            event_class=PointsAwardedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={ServiceName.ANALYTICS},
            secondary_publishers={ServiceName.NARRATIVE, ServiceName.ADMIN},
        )

        all_publishers = route.all_publishers
        assert ServiceName.GAMIFICATION in all_publishers
        assert ServiceName.NARRATIVE in all_publishers
        assert ServiceName.ADMIN in all_publishers
        assert len(all_publishers) == 3

    def test_event_type_property(self):
        """Test event_type property."""
        route = EventRoute(
            event_class=PointsAwardedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={ServiceName.ANALYTICS},
        )

        # Should be able to get event type
        assert "points_awarded" in route.event_type.lower()


class TestEventCatalog:
    """Test EventCatalog functionality."""

    def test_get_route(self):
        """Test getting route for event class."""
        catalog = EventCatalog()
        route = catalog.get_route(PointsAwardedEvent)

        assert route is not None
        assert route.event_class == PointsAwardedEvent
        assert route.primary_publisher == ServiceName.GAMIFICATION
        assert ServiceName.ANALYTICS in route.subscribers

    def test_get_route_by_event_type(self):
        """Test getting route by event type string."""
        catalog = EventCatalog()

        # Try to find a route by event type
        routes = catalog.get_all_routes()
        if routes:
            # Get first route's event type
            first_route = list(routes.values())[0]
            event_type = first_route.event_type

            # Should be able to find it by event type
            found_route = catalog.get_route_by_event_type(event_type)
            assert found_route is not None

    def test_get_publishers(self):
        """Test getting publishers for event class."""
        catalog = EventCatalog()
        publishers = catalog.get_publishers(PointsAwardedEvent)

        assert ServiceName.GAMIFICATION in publishers
        # May have secondary publishers too

    def test_get_subscribers(self):
        """Test getting subscribers for event class."""
        catalog = EventCatalog()
        subscribers = catalog.get_subscribers(PointsAwardedEvent)

        assert ServiceName.ANALYTICS in subscribers
        assert ServiceName.NOTIFICATION in subscribers

    def test_get_events_published_by(self):
        """Test getting events published by a service."""
        catalog = EventCatalog()
        events = catalog.get_events_published_by(ServiceName.GAMIFICATION)

        # Gamification service should publish several events
        assert PointsAwardedEvent in events
        assert AchievementUnlockedEvent in events
        assert len(events) > 0

    def test_get_events_subscribed_by(self):
        """Test getting events subscribed by a service."""
        catalog = EventCatalog()
        events = catalog.get_events_subscribed_by(ServiceName.ANALYTICS)

        # Analytics should subscribe to many events
        assert len(events) > 0
        # Should include various types
        event_categories = set()
        for event_class in events:
            try:
                temp_event = event_class(user_id=1, source_service="test")
                event_categories.add(temp_event.category)
            except Exception:
                pass

        # Should have events from multiple categories
        assert len(event_categories) > 1

    def test_get_service_dependencies(self):
        """Test getting service dependencies."""
        catalog = EventCatalog()
        deps = catalog.get_service_dependencies(ServiceName.GAMIFICATION)

        assert "publishes_to" in deps
        assert "subscribes_from" in deps

        # Gamification publishes to several services
        assert len(deps["publishes_to"]) > 0
        # Gamification subscribes from some services too
        assert len(deps["subscribes_from"]) > 0

    def test_get_events_by_category(self):
        """Test getting events by category."""
        catalog = EventCatalog()

        # Get gamification events
        gamification_events = catalog.get_events_by_category(EventCategory.GAMIFICATION)
        assert PointsAwardedEvent in gamification_events
        assert AchievementUnlockedEvent in gamification_events

        # Get narrative events
        narrative_events = catalog.get_events_by_category(EventCategory.NARRATIVE)
        assert StoryProgressEvent in narrative_events
        assert DecisionMadeEvent in narrative_events

        # Get admin events
        admin_events = catalog.get_events_by_category(EventCategory.ADMIN)
        assert UserRegisteredEvent in admin_events
        assert UserBannedEvent in admin_events

    def test_get_critical_events(self):
        """Test getting critical events."""
        catalog = EventCatalog()
        critical_events = catalog.get_critical_events()

        # Should have some critical events
        assert len(critical_events) > 0

        # User registration should be critical
        assert UserRegisteredEvent in critical_events
        # User banning should be critical
        assert UserBannedEvent in critical_events

    def test_validate_routing(self):
        """Test routing validation."""
        catalog = EventCatalog()
        errors = catalog.validate_routing()

        # Should return error categories
        assert "missing_subscribers" in errors
        assert "circular_dependencies" in errors
        assert "orphaned_events" in errors

        # Ideally, there should be no orphaned events
        assert len(errors["orphaned_events"]) == 0

    def test_generate_routing_table(self):
        """Test generating routing table."""
        catalog = EventCatalog()
        routing_table = catalog.generate_routing_table()

        # Should have entries for various event types
        assert len(routing_table) > 0

        # Each entry should have required fields
        for event_type, info in routing_table.items():
            assert "publishers" in info
            assert "subscribers" in info
            assert "priority_subscribers" in info
            assert "requires_persistence" in info
            assert "delivery_guarantee" in info

            # Publishers and subscribers should be lists
            assert isinstance(info["publishers"], list)
            assert isinstance(info["subscribers"], list)
            assert isinstance(info["priority_subscribers"], list)


class TestServiceName:
    """Test ServiceName enum."""

    def test_service_name_values(self):
        """Test ServiceName enum has expected values."""
        # Core services
        assert ServiceName.TELEGRAM_ADAPTER.value == "telegram_adapter"
        assert ServiceName.EVENT_BUS.value == "event_bus"

        # Business logic services
        assert ServiceName.GAMIFICATION.value == "gamification"
        assert ServiceName.NARRATIVE.value == "narrative"
        assert ServiceName.ADMIN.value == "admin"
        assert ServiceName.MONETIZATION.value == "monetization"

        # Supporting services
        assert ServiceName.ANALYTICS.value == "analytics"
        assert ServiceName.NOTIFICATION.value == "notification"
        assert ServiceName.USER_MANAGEMENT.value == "user_management"

        # Infrastructure services
        assert ServiceName.HEALTH_MONITOR.value == "health_monitor"
        assert ServiceName.CONFIGURATION.value == "configuration"
        assert ServiceName.AUDIT.value == "audit"


class TestGlobalCatalog:
    """Test global catalog instance and utility functions."""

    def test_global_catalog_exists(self):
        """Test that global catalog instance exists."""
        assert event_catalog is not None
        assert isinstance(event_catalog, EventCatalog)

    def test_utility_functions(self):
        """Test utility functions."""
        # Test get_event_publishers
        publishers = get_event_publishers(PointsAwardedEvent)
        assert isinstance(publishers, set)
        assert ServiceName.GAMIFICATION in publishers

        # Test get_event_subscribers
        subscribers = get_event_subscribers(PointsAwardedEvent)
        assert isinstance(subscribers, set)
        assert len(subscribers) > 0

    def test_service_event_functions(self):
        """Test service-specific event functions."""
        from src.core.events.catalog import (
            get_service_published_events,
            get_service_subscribed_events,
        )

        # Test published events
        published = get_service_published_events(ServiceName.GAMIFICATION)
        assert isinstance(published, list)
        assert PointsAwardedEvent in published

        # Test subscribed events
        subscribed = get_service_subscribed_events(ServiceName.ANALYTICS)
        assert isinstance(subscribed, list)
        assert len(subscribed) > 0


class TestEventRoutingScenarios:
    """Test specific event routing scenarios."""

    def test_user_registration_flow(self):
        """Test user registration event routing."""
        catalog = EventCatalog()

        # User registration should be published by telegram adapter
        publishers = catalog.get_publishers(UserRegisteredEvent)
        assert ServiceName.TELEGRAM_ADAPTER in publishers

        # Should be subscribed by multiple services
        subscribers = catalog.get_subscribers(UserRegisteredEvent)
        assert ServiceName.USER_MANAGEMENT in subscribers
        assert ServiceName.GAMIFICATION in subscribers  # For initial setup
        assert ServiceName.ANALYTICS in subscribers

    def test_gamification_flow(self):
        """Test gamification event routing."""
        catalog = EventCatalog()

        # Points awarded by gamification service
        publishers = catalog.get_publishers(PointsAwardedEvent)
        assert ServiceName.GAMIFICATION in publishers

        # Subscribed by notification and analytics
        subscribers = catalog.get_subscribers(PointsAwardedEvent)
        assert ServiceName.NOTIFICATION in subscribers
        assert ServiceName.ANALYTICS in subscribers

    def test_narrative_flow(self):
        """Test narrative event routing."""
        catalog = EventCatalog()

        # Story progress published by narrative service
        publishers = catalog.get_publishers(StoryProgressEvent)
        assert ServiceName.NARRATIVE in publishers

        # Should trigger gamification for points
        subscribers = catalog.get_subscribers(StoryProgressEvent)
        assert ServiceName.GAMIFICATION in subscribers
        assert ServiceName.ANALYTICS in subscribers

    def test_health_monitoring_flow(self):
        """Test health monitoring event routing."""
        catalog = EventCatalog()

        # Health events can be published by any service
        publishers = catalog.get_publishers(ServiceHealthEvent)
        assert ServiceName.HEALTH_MONITOR in publishers
        assert len(publishers) > 1  # Multiple services can publish health events

        # Should be monitored by admin and health monitor
        subscribers = catalog.get_subscribers(ServiceHealthEvent)
        assert ServiceName.HEALTH_MONITOR in subscribers
        assert ServiceName.ADMIN in subscribers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
