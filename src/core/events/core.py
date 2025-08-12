"""
Core Events for Diana Bot V2 Event Bus System.

This module defines fundamental events that are used across all services
for core functionality like user actions, service health monitoring,
and system operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..interfaces import EventPriority
from .base import BaseEventWithValidation, DomainEvent, EventCategory, SystemEvent


class UserActionEvent(DomainEvent):
    """
    Event fired when a user performs any action within the bot.
    
    This is a fundamental event that tracks all user interactions and
    serves as the basis for analytics, gamification, and personalization.
    """
    
    def __init__(
        self,
        user_id: int,
        action_type: str,
        action_data: Dict[str, Any],
        source_service: str = "telegram_adapter",
        session_id: Optional[str] = None,
        message_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize UserActionEvent.
        
        Args:
            user_id: ID of the user performing the action
            action_type: Type of action (message_sent, button_clicked, command_used, etc.)
            action_data: Structured data about the action
            source_service: Service recording the action
            session_id: User's current session ID
            message_id: Telegram message ID (if applicable)
            chat_id: Telegram chat ID (if applicable)
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "action_type": action_type,
            "action_data": action_data,
            "session_id": session_id,
            "message_id": message_id,
            "chat_id": chat_id,
            "recorded_at": datetime.utcnow().isoformat(),
        }
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs
        )
    
    @property
    def action_type(self) -> str:
        """The type of action performed."""
        return self.payload["action_type"]
    
    @property
    def action_data(self) -> Dict[str, Any]:
        """Structured data about the action."""
        return self.payload["action_data"]
    
    @property
    def session_id(self) -> Optional[str]:
        """User's current session ID."""
        return self.payload.get("session_id")
    
    @property
    def message_id(self) -> Optional[int]:
        """Telegram message ID if applicable."""
        return self.payload.get("message_id")
    
    @property
    def chat_id(self) -> Optional[int]:
        """Telegram chat ID if applicable."""
        return self.payload.get("chat_id")
    
    def _get_event_category(self) -> EventCategory:
        """User action events belong to the CORE category."""
        return EventCategory.CORE
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate user action specific requirements."""
        super()._custom_validation(errors)
        
        if not self.action_type or not isinstance(self.action_type, str):
            errors.append("Action type must be a non-empty string")
        
        if not isinstance(self.action_data, dict):
            errors.append("Action data must be a dictionary")


class ServiceHealthEvent(SystemEvent):
    """
    Event fired to report service health status and metrics.
    
    This event is crucial for monitoring system health, detecting issues,
    and triggering automated responses to service problems.
    """
    
    def __init__(
        self,
        source_service: str,
        health_status: str,  # healthy, degraded, unhealthy, down
        health_metrics: Dict[str, Any],
        system_component: str = "main",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize ServiceHealthEvent.
        
        Args:
            source_service: Service reporting its health
            health_status: Current health status (healthy/degraded/unhealthy/down)
            health_metrics: Detailed health metrics and measurements
            system_component: Specific component within the service
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "health_status": health_status,
            "health_metrics": health_metrics,
            "check_timestamp": datetime.utcnow().isoformat(),
        }
        
        # Determine priority based on health status
        priority_map = {
            "healthy": EventPriority.LOW,
            "degraded": EventPriority.NORMAL,
            "unhealthy": EventPriority.HIGH,
            "down": EventPriority.CRITICAL,
        }
        priority = priority_map.get(health_status, EventPriority.NORMAL)
        
        super().__init__(
            source_service=source_service,
            system_component=system_component,
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs
        )
    
    @property
    def health_status(self) -> str:
        """Current health status of the service."""
        return self.payload["health_status"]
    
    @property
    def health_metrics(self) -> Dict[str, Any]:
        """Detailed health metrics."""
        return self.payload["health_metrics"]
    
    @property
    def is_healthy(self) -> bool:
        """Whether the service is considered healthy."""
        return self.health_status == "healthy"
    
    @property
    def requires_attention(self) -> bool:
        """Whether this health status requires immediate attention."""
        return self.health_status in ("unhealthy", "down")
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate service health specific requirements."""
        valid_statuses = {"healthy", "degraded", "unhealthy", "down"}
        if self.health_status not in valid_statuses:
            errors.append(f"Health status must be one of {valid_statuses}")
        
        if not isinstance(self.health_metrics, dict):
            errors.append("Health metrics must be a dictionary")


class ServiceStartedEvent(SystemEvent):
    """
    Event fired when a service successfully starts up.
    
    This event provides visibility into service lifecycle and helps
    track deployment and restart patterns.
    """
    
    def __init__(
        self,
        source_service: str,
        service_version: str,
        startup_duration_ms: float,
        configuration: Dict[str, Any],
        system_component: str = "main",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize ServiceStartedEvent.
        
        Args:
            source_service: Service that started
            service_version: Version of the service
            startup_duration_ms: Time taken to start up in milliseconds
            configuration: Key configuration parameters (sanitized)
            system_component: Specific component that started
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "service_version": service_version,
            "startup_duration_ms": startup_duration_ms,
            "configuration": configuration,
            "startup_timestamp": datetime.utcnow().isoformat(),
        }
        
        super().__init__(
            source_service=source_service,
            system_component=system_component,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs
        )
    
    @property
    def service_version(self) -> str:
        """Version of the service that started."""
        return self.payload["service_version"]
    
    @property
    def startup_duration_ms(self) -> float:
        """Startup duration in milliseconds."""
        return self.payload["startup_duration_ms"]
    
    @property
    def configuration(self) -> Dict[str, Any]:
        """Key configuration parameters."""
        return self.payload["configuration"]
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate service started specific requirements."""
        if not self.service_version or not isinstance(self.service_version, str):
            errors.append("Service version must be a non-empty string")
        
        if not isinstance(self.startup_duration_ms, (int, float)) or self.startup_duration_ms < 0:
            errors.append("Startup duration must be a non-negative number")


class ServiceStoppedEvent(SystemEvent):
    """
    Event fired when a service shuts down gracefully.
    
    This event helps track service lifecycle and can trigger cleanup
    or failover procedures.
    """
    
    def __init__(
        self,
        source_service: str,
        shutdown_reason: str,
        uptime_ms: float,
        final_metrics: Dict[str, Any],
        system_component: str = "main",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize ServiceStoppedEvent.
        
        Args:
            source_service: Service that stopped
            shutdown_reason: Reason for shutdown (graceful, restart, error, etc.)
            uptime_ms: How long the service was running in milliseconds
            final_metrics: Final performance metrics before shutdown
            system_component: Specific component that stopped
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "shutdown_reason": shutdown_reason,
            "uptime_ms": uptime_ms,
            "final_metrics": final_metrics,
            "shutdown_timestamp": datetime.utcnow().isoformat(),
        }
        
        # Critical if shutdown was unexpected
        priority = EventPriority.CRITICAL if shutdown_reason == "error" else EventPriority.NORMAL
        
        super().__init__(
            source_service=source_service,
            system_component=system_component,
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs
        )
    
    @property
    def shutdown_reason(self) -> str:
        """Reason for service shutdown."""
        return self.payload["shutdown_reason"]
    
    @property
    def uptime_ms(self) -> float:
        """Service uptime in milliseconds."""
        return self.payload["uptime_ms"]
    
    @property
    def final_metrics(self) -> Dict[str, Any]:
        """Final performance metrics."""
        return self.payload["final_metrics"]
    
    @property
    def was_graceful(self) -> bool:
        """Whether the shutdown was graceful."""
        return self.shutdown_reason in ("graceful", "restart", "maintenance")
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate service stopped specific requirements."""
        if not self.shutdown_reason or not isinstance(self.shutdown_reason, str):
            errors.append("Shutdown reason must be a non-empty string")
        
        if not isinstance(self.uptime_ms, (int, float)) or self.uptime_ms < 0:
            errors.append("Uptime must be a non-negative number")


class SystemErrorEvent(SystemEvent):
    """
    Event fired when a system error occurs that needs attention.
    
    This event helps track errors across the system and can trigger
    alerting or automated recovery procedures.
    """
    
    def __init__(
        self,
        source_service: str,
        error_type: str,
        error_message: str,
        error_context: Dict[str, Any],
        stack_trace: Optional[str] = None,
        affected_user_id: Optional[int] = None,
        system_component: str = "main",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize SystemErrorEvent.
        
        Args:
            source_service: Service where the error occurred
            error_type: Type/category of error
            error_message: Human-readable error description
            error_context: Context information about the error
            stack_trace: Stack trace if available
            affected_user_id: User ID if error affected a specific user
            system_component: Component where error occurred
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "error_type": error_type,
            "error_message": error_message,
            "error_context": error_context,
            "stack_trace": stack_trace,
            "affected_user_id": affected_user_id,
            "error_timestamp": datetime.utcnow().isoformat(),
        }
        
        super().__init__(
            source_service=source_service,
            system_component=system_component,
            correlation_id=correlation_id,
            priority=EventPriority.CRITICAL,
            payload=payload,
            **kwargs
        )
    
    @property
    def error_type(self) -> str:
        """Type/category of error."""
        return self.payload["error_type"]
    
    @property
    def error_message(self) -> str:
        """Human-readable error description."""
        return self.payload["error_message"]
    
    @property
    def error_context(self) -> Dict[str, Any]:
        """Context information about the error."""
        return self.payload["error_context"]
    
    @property
    def stack_trace(self) -> Optional[str]:
        """Stack trace if available."""
        return self.payload.get("stack_trace")
    
    @property
    def affected_user_id(self) -> Optional[int]:
        """User ID if error affected a specific user."""
        return self.payload.get("affected_user_id")
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate system error specific requirements."""
        if not self.error_type or not isinstance(self.error_type, str):
            errors.append("Error type must be a non-empty string")
        
        if not self.error_message or not isinstance(self.error_message, str):
            errors.append("Error message must be a non-empty string")
        
        if not isinstance(self.error_context, dict):
            errors.append("Error context must be a dictionary")


class ConfigurationChangedEvent(SystemEvent):
    """
    Event fired when system configuration is changed.
    
    This event tracks configuration changes for audit purposes and
    can trigger service reloads or other responses.
    """
    
    def __init__(
        self,
        source_service: str,
        config_section: str,
        changed_keys: List[str],
        change_summary: Dict[str, Any],
        changed_by: Optional[str] = None,
        system_component: str = "configuration",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize ConfigurationChangedEvent.
        
        Args:
            source_service: Service whose configuration changed
            config_section: Section/category of configuration that changed
            changed_keys: List of configuration keys that were modified
            change_summary: Summary of changes (without sensitive values)
            changed_by: Who/what made the change (admin user, automated system, etc.)
            system_component: Configuration subsystem
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "config_section": config_section,
            "changed_keys": changed_keys,
            "change_summary": change_summary,
            "changed_by": changed_by,
            "change_timestamp": datetime.utcnow().isoformat(),
        }
        
        super().__init__(
            source_service=source_service,
            system_component=system_component,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
            payload=payload,
            **kwargs
        )
    
    @property
    def config_section(self) -> str:
        """Configuration section that changed."""
        return self.payload["config_section"]
    
    @property
    def changed_keys(self) -> List[str]:
        """List of configuration keys that were modified."""
        return self.payload["changed_keys"]
    
    @property
    def change_summary(self) -> Dict[str, Any]:
        """Summary of changes."""
        return self.payload["change_summary"]
    
    @property
    def changed_by(self) -> Optional[str]:
        """Who/what made the change."""
        return self.payload.get("changed_by")
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate configuration changed specific requirements."""
        if not self.config_section or not isinstance(self.config_section, str):
            errors.append("Config section must be a non-empty string")
        
        if not isinstance(self.changed_keys, list):
            errors.append("Changed keys must be a list")
        
        if not self.changed_keys:
            errors.append("At least one configuration key must have changed")


# Export all core events
__all__ = [
    "UserActionEvent",
    "ServiceHealthEvent", 
    "ServiceStartedEvent",
    "ServiceStoppedEvent",
    "SystemErrorEvent",
    "ConfigurationChangedEvent",
]