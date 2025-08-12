"""
Event Catalog for Diana Bot V2.

This module provides a comprehensive mapping of which services publish
which events and which services subscribe to which events. This catalog
serves as the authoritative source for event routing and dependencies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Type

from .admin import (
    AdminActionPerformedEvent,
    AnalyticsEvent,
    ContentModerationEvent,
    SystemMaintenanceEvent,
    UserBannedEvent,
    UserRegisteredEvent,
)
from .base import BaseEventWithValidation, EventCategory
from .core import (
    ConfigurationChangedEvent,
    ServiceHealthEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
    SystemErrorEvent,
    UserActionEvent,
)
from .gamification import (
    AchievementUnlockedEvent,
    DailyBonusClaimedEvent,
    LeaderboardChangedEvent,
    PointsAwardedEvent,
    PointsDeductedEvent,
    StreakUpdatedEvent,
)
from .narrative import (
    ChapterCompletedEvent,
    CharacterInteractionEvent,
    DecisionMadeEvent,
    NarrativeStateChangedEvent,
    StoryProgressEvent,
    StoryStartedEvent,
)


class ServiceName(Enum):
    """Enumeration of all services in the Diana Bot V2 system."""
    
    # Core Services
    TELEGRAM_ADAPTER = "telegram_adapter"
    EVENT_BUS = "event_bus"
    
    # Business Logic Services
    GAMIFICATION = "gamification"
    NARRATIVE = "narrative"
    ADMIN = "admin"
    MONETIZATION = "monetization"
    
    # Supporting Services
    ANALYTICS = "analytics"
    NOTIFICATION = "notification"
    USER_MANAGEMENT = "user_management"
    CONTENT_MODERATION = "content_moderation"
    
    # Infrastructure Services
    HEALTH_MONITOR = "health_monitor"
    CONFIGURATION = "configuration"
    AUDIT = "audit"


@dataclass
class EventRoute:
    """
    Defines routing information for a specific event type.
    
    This includes which service typically publishes the event,
    which services subscribe to it, and routing preferences.
    """
    
    event_class: Type[BaseEventWithValidation]
    primary_publisher: ServiceName
    subscribers: Set[ServiceName]
    secondary_publishers: Set[ServiceName] = None
    routing_key: Optional[str] = None
    requires_persistence: bool = True
    delivery_guarantee: str = "at_least_once"  # at_most_once, at_least_once, exactly_once
    priority_subscribers: Set[ServiceName] = None  # Subscribers that get priority
    
    def __post_init__(self):
        """Initialize default values."""
        if self.secondary_publishers is None:
            self.secondary_publishers = set()
        if self.priority_subscribers is None:
            self.priority_subscribers = set()
    
    @property
    def all_publishers(self) -> Set[ServiceName]:
        """All services that can publish this event."""
        return {self.primary_publisher} | self.secondary_publishers
    
    @property
    def event_type(self) -> str:
        """Get the event type string."""
        # Create a temporary instance to get the event type
        try:
            temp_instance = self.event_class(
                user_id=1,
                source_service=self.primary_publisher.value
            )
            return temp_instance.event_type
        except Exception:
            # Fallback to class name conversion
            class_name = self.event_class.__name__
            import re
            snake_case = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
            snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_case).lower()
            if snake_case.endswith('_event'):
                snake_case = snake_case[:-6]
            return snake_case


class EventCatalog:
    """
    Central catalog of all event types, their publishers, and subscribers.
    
    This class provides the authoritative mapping of event routing
    throughout the Diana Bot V2 system.
    """
    
    # Core Events Routing
    _CORE_EVENTS = {
        UserActionEvent: EventRoute(
            event_class=UserActionEvent,
            primary_publisher=ServiceName.TELEGRAM_ADAPTER,
            subscribers={
                ServiceName.GAMIFICATION,
                ServiceName.NARRATIVE,
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
            requires_persistence=True,
        ),
        
        ServiceHealthEvent: EventRoute(
            event_class=ServiceHealthEvent,
            primary_publisher=ServiceName.HEALTH_MONITOR,
            subscribers={
                ServiceName.HEALTH_MONITOR,
                ServiceName.ADMIN,
                ServiceName.NOTIFICATION,
                ServiceName.ANALYTICS,
            },
            secondary_publishers={
                ServiceName.GAMIFICATION,
                ServiceName.NARRATIVE,
                ServiceName.TELEGRAM_ADAPTER,
                ServiceName.MONETIZATION,
            },
            delivery_guarantee="at_least_once",
        ),
        
        ServiceStartedEvent: EventRoute(
            event_class=ServiceStartedEvent,
            primary_publisher=ServiceName.HEALTH_MONITOR,
            subscribers={
                ServiceName.HEALTH_MONITOR,
                ServiceName.ADMIN,
                ServiceName.ANALYTICS,
            },
            secondary_publishers=set(ServiceName),  # Any service can report startup
        ),
        
        ServiceStoppedEvent: EventRoute(
            event_class=ServiceStoppedEvent,
            primary_publisher=ServiceName.HEALTH_MONITOR,
            subscribers={
                ServiceName.HEALTH_MONITOR,
                ServiceName.ADMIN,
                ServiceName.ANALYTICS,
            },
            secondary_publishers=set(ServiceName),  # Any service can report shutdown
        ),
        
        SystemErrorEvent: EventRoute(
            event_class=SystemErrorEvent,
            primary_publisher=ServiceName.HEALTH_MONITOR,
            subscribers={
                ServiceName.HEALTH_MONITOR,
                ServiceName.ADMIN,
                ServiceName.NOTIFICATION,
                ServiceName.ANALYTICS,
            },
            secondary_publishers=set(ServiceName),  # Any service can report errors
            priority_subscribers={ServiceName.ADMIN, ServiceName.NOTIFICATION},
        ),
        
        ConfigurationChangedEvent: EventRoute(
            event_class=ConfigurationChangedEvent,
            primary_publisher=ServiceName.CONFIGURATION,
            subscribers={
                ServiceName.GAMIFICATION,
                ServiceName.NARRATIVE,
                ServiceName.TELEGRAM_ADAPTER,
                ServiceName.MONETIZATION,
                ServiceName.ADMIN,
                ServiceName.ANALYTICS,
            },
            secondary_publishers={ServiceName.ADMIN},
        ),
    }
    
    # Gamification Events Routing  
    _GAMIFICATION_EVENTS = {
        PointsAwardedEvent: EventRoute(
            event_class=PointsAwardedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={
                ServiceName.NOTIFICATION,
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
            secondary_publishers={ServiceName.NARRATIVE},  # Can award points for story actions
        ),
        
        PointsDeductedEvent: EventRoute(
            event_class=PointsDeductedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={
                ServiceName.NOTIFICATION,
                ServiceName.ANALYTICS,
                ServiceName.ADMIN,
                ServiceName.USER_MANAGEMENT,
            },
            secondary_publishers={ServiceName.ADMIN},  # Can deduct points as penalty
        ),
        
        AchievementUnlockedEvent: EventRoute(
            event_class=AchievementUnlockedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={
                ServiceName.NOTIFICATION,
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
                ServiceName.MONETIZATION,  # May trigger rewards
            },
            priority_subscribers={ServiceName.NOTIFICATION},
        ),
        
        StreakUpdatedEvent: EventRoute(
            event_class=StreakUpdatedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={
                ServiceName.NOTIFICATION,
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
        ),
        
        LeaderboardChangedEvent: EventRoute(
            event_class=LeaderboardChangedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={
                ServiceName.NOTIFICATION,
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
        ),
        
        DailyBonusClaimedEvent: EventRoute(
            event_class=DailyBonusClaimedEvent,
            primary_publisher=ServiceName.GAMIFICATION,
            subscribers={
                ServiceName.NOTIFICATION,
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
        ),
    }
    
    # Narrative Events Routing
    _NARRATIVE_EVENTS = {
        StoryStartedEvent: EventRoute(
            event_class=StoryStartedEvent,
            primary_publisher=ServiceName.NARRATIVE,
            subscribers={
                ServiceName.GAMIFICATION,  # May award points for starting
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
        ),
        
        StoryProgressEvent: EventRoute(
            event_class=StoryProgressEvent,
            primary_publisher=ServiceName.NARRATIVE,
            subscribers={
                ServiceName.GAMIFICATION,  # May award points for progress
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
        ),
        
        DecisionMadeEvent: EventRoute(
            event_class=DecisionMadeEvent,
            primary_publisher=ServiceName.NARRATIVE,
            subscribers={
                ServiceName.GAMIFICATION,  # May award points for decisions
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
            requires_persistence=True,  # Decisions are critical for story continuity
        ),
        
        ChapterCompletedEvent: EventRoute(
            event_class=ChapterCompletedEvent,
            primary_publisher=ServiceName.NARRATIVE,
            subscribers={
                ServiceName.GAMIFICATION,  # Awards points and checks achievements
                ServiceName.NOTIFICATION,  # May notify about completion
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
            priority_subscribers={ServiceName.GAMIFICATION},
        ),
        
        CharacterInteractionEvent: EventRoute(
            event_class=CharacterInteractionEvent,
            primary_publisher=ServiceName.NARRATIVE,
            subscribers={
                ServiceName.GAMIFICATION,  # May award points
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
        ),
        
        NarrativeStateChangedEvent: EventRoute(
            event_class=NarrativeStateChangedEvent,
            primary_publisher=ServiceName.NARRATIVE,
            subscribers={
                ServiceName.ANALYTICS,
                ServiceName.USER_MANAGEMENT,
            },
            requires_persistence=True,  # State changes are critical
        ),
    }
    
    # Admin Events Routing
    _ADMIN_EVENTS = {
        UserRegisteredEvent: EventRoute(
            event_class=UserRegisteredEvent,
            primary_publisher=ServiceName.TELEGRAM_ADAPTER,
            subscribers={
                ServiceName.USER_MANAGEMENT,
                ServiceName.GAMIFICATION,  # Setup initial points
                ServiceName.NARRATIVE,  # Setup story progress
                ServiceName.ANALYTICS,
                ServiceName.ADMIN,
            },
            priority_subscribers={ServiceName.USER_MANAGEMENT, ServiceName.GAMIFICATION},
            requires_persistence=True,
        ),
        
        UserBannedEvent: EventRoute(
            event_class=UserBannedEvent,
            primary_publisher=ServiceName.ADMIN,
            subscribers={
                ServiceName.TELEGRAM_ADAPTER,  # Stop serving the user
                ServiceName.USER_MANAGEMENT,
                ServiceName.GAMIFICATION,  # Freeze points/achievements
                ServiceName.NARRATIVE,  # Freeze story progress
                ServiceName.ANALYTICS,
                ServiceName.AUDIT,
            },
            priority_subscribers={ServiceName.TELEGRAM_ADAPTER},
            requires_persistence=True,
        ),
        
        ContentModerationEvent: EventRoute(
            event_class=ContentModerationEvent,
            primary_publisher=ServiceName.CONTENT_MODERATION,
            subscribers={
                ServiceName.ADMIN,
                ServiceName.ANALYTICS,
                ServiceName.AUDIT,
                ServiceName.USER_MANAGEMENT,
            },
            secondary_publishers={ServiceName.ADMIN},  # Manual moderation
        ),
        
        AnalyticsEvent: EventRoute(
            event_class=AnalyticsEvent,
            primary_publisher=ServiceName.ANALYTICS,
            subscribers={
                ServiceName.ADMIN,  # For dashboards
            },
            secondary_publishers=set(ServiceName),  # Any service can generate analytics
            delivery_guarantee="at_most_once",  # Analytics can tolerate some loss
        ),
        
        AdminActionPerformedEvent: EventRoute(
            event_class=AdminActionPerformedEvent,
            primary_publisher=ServiceName.ADMIN,
            subscribers={
                ServiceName.AUDIT,
                ServiceName.ANALYTICS,
            },
            requires_persistence=True,  # Critical for audit trail
        ),
        
        SystemMaintenanceEvent: EventRoute(
            event_class=SystemMaintenanceEvent,
            primary_publisher=ServiceName.ADMIN,
            subscribers={
                ServiceName.NOTIFICATION,  # Notify users
                ServiceName.HEALTH_MONITOR,
                ServiceName.ANALYTICS,
            },
            secondary_publishers={ServiceName.HEALTH_MONITOR},
            priority_subscribers={ServiceName.NOTIFICATION},
        ),
    }
    
    def __init__(self):
        """Initialize the event catalog with all route definitions."""
        self._routes = {
            **self._CORE_EVENTS,
            **self._GAMIFICATION_EVENTS,
            **self._NARRATIVE_EVENTS,
            **self._ADMIN_EVENTS,
        }
    
    def get_route(self, event_class: Type[BaseEventWithValidation]) -> Optional[EventRoute]:
        """
        Get routing information for a specific event class.
        
        Args:
            event_class: The event class to look up
            
        Returns:
            EventRoute if found, None otherwise
        """
        return self._routes.get(event_class)
    
    def get_route_by_event_type(self, event_type: str) -> Optional[EventRoute]:
        """
        Get routing information by event type string.
        
        Args:
            event_type: The event type string
            
        Returns:
            EventRoute if found, None otherwise
        """
        for route in self._routes.values():
            if route.event_type == event_type:
                return route
        return None
    
    def get_publishers(self, event_class: Type[BaseEventWithValidation]) -> Set[ServiceName]:
        """
        Get all services that can publish a specific event type.
        
        Args:
            event_class: The event class
            
        Returns:
            Set of services that can publish this event
        """
        route = self.get_route(event_class)
        return route.all_publishers if route else set()
    
    def get_subscribers(self, event_class: Type[BaseEventWithValidation]) -> Set[ServiceName]:
        """
        Get all services that subscribe to a specific event type.
        
        Args:
            event_class: The event class
            
        Returns:
            Set of services that subscribe to this event
        """
        route = self.get_route(event_class)
        return route.subscribers if route else set()
    
    def get_events_published_by(self, service: ServiceName) -> List[Type[BaseEventWithValidation]]:
        """
        Get all event types that a service can publish.
        
        Args:
            service: The service name
            
        Returns:
            List of event classes the service can publish
        """
        events = []
        for event_class, route in self._routes.items():
            if service in route.all_publishers:
                events.append(event_class)
        return events
    
    def get_events_subscribed_by(self, service: ServiceName) -> List[Type[BaseEventWithValidation]]:
        """
        Get all event types that a service subscribes to.
        
        Args:
            service: The service name
            
        Returns:
            List of event classes the service subscribes to
        """
        events = []
        for event_class, route in self._routes.items():
            if service in route.subscribers:
                events.append(event_class)
        return events
    
    def get_service_dependencies(self, service: ServiceName) -> Dict[str, List[ServiceName]]:
        """
        Get dependency information for a service.
        
        Args:
            service: The service name
            
        Returns:
            Dictionary with 'publishes_to' and 'subscribes_from' dependencies
        """
        publishes_to = set()
        subscribes_from = set()
        
        for route in self._routes.values():
            if service in route.all_publishers:
                publishes_to.update(route.subscribers)
            if service in route.subscribers:
                subscribes_from.update(route.all_publishers)
        
        return {
            "publishes_to": list(publishes_to),
            "subscribes_from": list(subscribes_from),
        }
    
    def get_events_by_category(self, category: EventCategory) -> List[Type[BaseEventWithValidation]]:
        """
        Get all event types in a specific category.
        
        Args:
            category: The event category
            
        Returns:
            List of event classes in the category
        """
        events = []
        for event_class in self._routes.keys():
            # Create a temporary instance to check category
            try:
                temp_instance = event_class(
                    user_id=1,
                    source_service="test"
                )
                if temp_instance.category == category:
                    events.append(event_class)
            except Exception:
                # Skip if we can't instantiate
                continue
        
        return events
    
    def get_critical_events(self) -> List[Type[BaseEventWithValidation]]:
        """
        Get all events that require guaranteed delivery.
        
        Returns:
            List of critical event classes
        """
        return [
            event_class for event_class, route in self._routes.items()
            if route.delivery_guarantee == "exactly_once" or route.requires_persistence
        ]
    
    def validate_routing(self) -> Dict[str, List[str]]:
        """
        Validate the routing configuration for consistency.
        
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {
            "missing_subscribers": [],
            "circular_dependencies": [],
            "orphaned_events": [],
        }
        
        # Check for events without subscribers
        for event_class, route in self._routes.items():
            if not route.subscribers:
                errors["orphaned_events"].append(event_class.__name__)
        
        # Check for circular dependencies (simplified check)
        for service in ServiceName:
            deps = self.get_service_dependencies(service)
            common = set(deps["publishes_to"]) & set(deps["subscribes_from"])
            if common:
                errors["circular_dependencies"].append(f"{service.value} <-> {common}")
        
        return errors
    
    def generate_routing_table(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Generate a routing table for external systems.
        
        Returns:
            Dictionary mapping event types to publisher/subscriber info
        """
        routing_table = {}
        
        for event_class, route in self._routes.items():
            event_type = route.event_type
            routing_table[event_type] = {
                "publishers": [s.value for s in route.all_publishers],
                "subscribers": [s.value for s in route.subscribers],
                "priority_subscribers": [s.value for s in route.priority_subscribers],
                "requires_persistence": route.requires_persistence,
                "delivery_guarantee": route.delivery_guarantee,
            }
        
        return routing_table
    
    def get_all_routes(self) -> Dict[Type[BaseEventWithValidation], EventRoute]:
        """
        Get all routing information.
        
        Returns:
            Dictionary of all event routes
        """
        return self._routes.copy()


# Global instance of the event catalog
event_catalog = EventCatalog()


# Utility functions for easy access
def get_event_publishers(event_class: Type[BaseEventWithValidation]) -> Set[ServiceName]:
    """Get publishers for an event type."""
    return event_catalog.get_publishers(event_class)


def get_event_subscribers(event_class: Type[BaseEventWithValidation]) -> Set[ServiceName]:
    """Get subscribers for an event type."""
    return event_catalog.get_subscribers(event_class)


def get_service_published_events(service: ServiceName) -> List[Type[BaseEventWithValidation]]:
    """Get events published by a service."""
    return event_catalog.get_events_published_by(service)


def get_service_subscribed_events(service: ServiceName) -> List[Type[BaseEventWithValidation]]:
    """Get events subscribed by a service."""
    return event_catalog.get_events_subscribed_by(service)


# Export key components
__all__ = [
    "EventCatalog",
    "EventRoute", 
    "ServiceName",
    "event_catalog",
    "get_event_publishers",
    "get_event_subscribers",
    "get_service_published_events",
    "get_service_subscribed_events",
]