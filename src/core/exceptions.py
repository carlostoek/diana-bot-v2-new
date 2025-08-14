"""
Event Bus Exceptions - Stubs for TDD
"""


class EventBusError(Exception):
    """Base exception for Event Bus operations"""

    pass


class PublishError(EventBusError):
    """Exception raised during event publishing"""

    pass


class SubscribeError(EventBusError):
    """Exception raised during event subscription"""

    pass


class EventValidationError(EventBusError):
    """Exception raised for event validation failures"""

    pass
