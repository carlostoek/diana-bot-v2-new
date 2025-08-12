"""
Event Contracts and Catalog for Diana Bot V2.

This package provides a comprehensive event system with proper validation,
type safety, and clean architecture principles. All events follow established
contracts and are cataloged for service communication mapping.
"""

from .base import (
    BaseEventWithValidation,
    DomainEvent,
    EventCategory,
    EventMetadata,
    IntegrationEvent,
    SystemEvent,
    ValidationLevel,
)

# Import specific event implementations
try:
    from .core import *
except ImportError:
    pass

try:
    from .gamification import *
except ImportError:
    pass

try:
    from .narrative import *
except ImportError:
    pass

try:
    from .admin import *
except ImportError:
    pass

try:
    from .catalog import EventCatalog, ServiceName, event_catalog
except ImportError:
    EventCatalog = None
    event_catalog = None
    ServiceName = None

# Re-export common types and classes
__all__ = [
    # Base classes
    "BaseEventWithValidation",
    "DomainEvent",
    "SystemEvent",
    "IntegrationEvent",
    # Supporting types
    "EventCategory",
    "EventMetadata",
    "ValidationLevel",
    # Event Catalog
    "EventCatalog",
    "ServiceName",
    "event_catalog",
]
