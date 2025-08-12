"""
Admin Events for Diana Bot V2.

This module defines all events related to administrative operations
including user management, content moderation, analytics, and system administration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..interfaces import EventPriority
from .base import DomainEvent, EventCategory, SystemEvent


class UserRegisteredEvent(DomainEvent):
    """
    Event fired when a new user registers with the bot.
    
    This is a fundamental user lifecycle event that triggers onboarding,
    initial gamification setup, and analytics tracking.
    """
    
    def __init__(
        self,
        user_id: int,
        telegram_data: Dict[str, Any],
        registration_source: str = "telegram",
        referral_code: Optional[str] = None,
        initial_language: str = "en",
        is_bot: bool = False,
        source_service: str = "telegram_adapter",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize UserRegisteredEvent.
        
        Args:
            user_id: Telegram user ID
            telegram_data: Raw Telegram user data
            registration_source: How the user registered (telegram, web, referral)
            referral_code: Referral code used (if any)
            initial_language: User's initial language preference
            is_bot: Whether the registered account is a bot
            source_service: Service handling the registration
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        # Sanitize telegram data to remove sensitive information
        safe_telegram_data = {
            "username": telegram_data.get("username"),
            "first_name": telegram_data.get("first_name"),
            "last_name": telegram_data.get("last_name"),
            "language_code": telegram_data.get("language_code"),
            "is_premium": telegram_data.get("is_premium", False),
        }
        
        payload = {
            "telegram_data": safe_telegram_data,
            "registration_source": registration_source,
            "referral_code": referral_code,
            "initial_language": initial_language,
            "is_bot": is_bot,
            "registered_at": datetime.utcnow().isoformat(),
            # These will be set by various services
            "onboarding_completed": False,
            "initial_points_awarded": None,
            "referrer_user_id": None,
        }
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,  # New user registration is important
            payload=payload,
            **kwargs
        )
    
    @property
    def telegram_data(self) -> Dict[str, Any]:
        """Safe Telegram user data."""
        return self.payload["telegram_data"]
    
    @property
    def registration_source(self) -> str:
        """How the user registered."""
        return self.payload["registration_source"]
    
    @property
    def referral_code(self) -> Optional[str]:
        """Referral code used."""
        return self.payload.get("referral_code")
    
    @property
    def initial_language(self) -> str:
        """User's initial language."""
        return self.payload["initial_language"]
    
    @property
    def username(self) -> Optional[str]:
        """Telegram username."""
        return self.telegram_data.get("username")
    
    @property
    def first_name(self) -> Optional[str]:
        """User's first name."""
        return self.telegram_data.get("first_name")
    
    def _get_event_category(self) -> EventCategory:
        """User registration events belong to the USER category."""
        return EventCategory.USER
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate user registration specific requirements."""
        super()._custom_validation(errors)
        
        if not isinstance(self.telegram_data, dict):
            errors.append("Telegram data must be a dictionary")
        
        if not self.registration_source or not isinstance(self.registration_source, str):
            errors.append("Registration source must be a non-empty string")


class UserBannedEvent(DomainEvent):
    """
    Event fired when a user is banned from the bot.
    
    This is a critical administrative event that affects user access
    and triggers cleanup procedures.
    """
    
    def __init__(
        self,
        user_id: int,
        banned_by_admin_id: int,
        ban_reason: str,
        ban_type: str = "permanent",  # temporary, permanent, shadow
        ban_duration_hours: Optional[int] = None,
        violation_details: Dict[str, Any] = None,
        automatic_ban: bool = False,
        source_service: str = "admin",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize UserBannedEvent.
        
        Args:
            user_id: ID of the banned user
            banned_by_admin_id: ID of the admin who issued the ban
            ban_reason: Reason for the ban
            ban_type: Type of ban (temporary, permanent, shadow)
            ban_duration_hours: Duration in hours (for temporary bans)
            violation_details: Details about the violation
            automatic_ban: Whether this was an automatic ban
            source_service: Service issuing the ban
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        ban_expires_at = None
        if ban_type == "temporary" and ban_duration_hours:
            from datetime import timedelta
            ban_expires_at = (datetime.utcnow() + timedelta(hours=ban_duration_hours)).isoformat()
        
        payload = {
            "banned_by_admin_id": banned_by_admin_id,
            "ban_reason": ban_reason,
            "ban_type": ban_type,
            "ban_duration_hours": ban_duration_hours,
            "ban_expires_at": ban_expires_at,
            "violation_details": violation_details or {},
            "automatic_ban": automatic_ban,
            "banned_at": datetime.utcnow().isoformat(),
            # These will be set by admin service
            "previous_violations": None,
            "ban_appeal_allowed": None,
        }
        
        super().__init__(
            user_id=user_id,
            source_service=source_service,
            correlation_id=correlation_id,
            priority=EventPriority.CRITICAL,  # Bans are critical events
            payload=payload,
            **kwargs
        )
    
    @property
    def banned_by_admin_id(self) -> int:
        """ID of the admin who issued the ban."""
        return self.payload["banned_by_admin_id"]
    
    @property
    def ban_reason(self) -> str:
        """Reason for the ban."""
        return self.payload["ban_reason"]
    
    @property
    def ban_type(self) -> str:
        """Type of ban."""
        return self.payload["ban_type"]
    
    @property
    def is_permanent(self) -> bool:
        """Whether this is a permanent ban."""
        return self.ban_type == "permanent"
    
    @property
    def automatic_ban(self) -> bool:
        """Whether this was an automatic ban."""
        return self.payload["automatic_ban"]
    
    def _get_event_category(self) -> EventCategory:
        """User ban events belong to the ADMIN category."""
        return EventCategory.ADMIN
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate user banned specific requirements."""
        super()._custom_validation(errors)
        
        if not isinstance(self.banned_by_admin_id, int) or self.banned_by_admin_id <= 0:
            errors.append("Banned by admin ID must be a positive integer")
        
        if not self.ban_reason or not isinstance(self.ban_reason, str):
            errors.append("Ban reason must be a non-empty string")
        
        valid_ban_types = {"temporary", "permanent", "shadow"}
        if self.ban_type not in valid_ban_types:
            errors.append(f"Ban type must be one of {valid_ban_types}")


class ContentModerationEvent(SystemEvent):
    """
    Event fired when content is moderated (approved, rejected, flagged).
    
    This event tracks all content moderation activities for
    audit purposes and pattern detection.
    """
    
    def __init__(
        self,
        content_id: str,
        content_type: str,  # message, story, image, etc.
        moderation_action: str,  # approved, rejected, flagged, deleted
        moderated_by_admin_id: Optional[int],
        moderation_reason: Optional[str],
        automatic_moderation: bool = False,
        confidence_score: Optional[float] = None,
        content_metadata: Dict[str, Any] = None,
        affected_user_id: Optional[int] = None,
        source_service: str = "moderation",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize ContentModerationEvent.
        
        Args:
            content_id: ID of the moderated content
            content_type: Type of content being moderated
            moderation_action: Action taken (approved, rejected, flagged, deleted)
            moderated_by_admin_id: ID of the admin (if manual moderation)
            moderation_reason: Reason for the moderation action
            automatic_moderation: Whether this was automatic moderation
            confidence_score: AI confidence score (if automatic)
            content_metadata: Metadata about the content
            affected_user_id: ID of the user whose content was moderated
            source_service: Service performing the moderation
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "content_id": content_id,
            "content_type": content_type,
            "moderation_action": moderation_action,
            "moderated_by_admin_id": moderated_by_admin_id,
            "moderation_reason": moderation_reason,
            "automatic_moderation": automatic_moderation,
            "confidence_score": confidence_score,
            "content_metadata": content_metadata or {},
            "affected_user_id": affected_user_id,
            "moderated_at": datetime.utcnow().isoformat(),
        }
        
        # Higher priority for rejections and flags
        priority = EventPriority.HIGH if moderation_action in ("rejected", "flagged", "deleted") else EventPriority.NORMAL
        
        super().__init__(
            source_service=source_service,
            system_component="content_moderation",
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs
        )
    
    @property
    def content_id(self) -> str:
        """ID of the moderated content."""
        return self.payload["content_id"]
    
    @property
    def content_type(self) -> str:
        """Type of content."""
        return self.payload["content_type"]
    
    @property
    def moderation_action(self) -> str:
        """Action taken."""
        return self.payload["moderation_action"]
    
    @property
    def automatic_moderation(self) -> bool:
        """Whether this was automatic."""
        return self.payload["automatic_moderation"]
    
    @property
    def affected_user_id(self) -> Optional[int]:
        """ID of affected user."""
        return self.payload.get("affected_user_id")
    
    def _get_event_category(self) -> EventCategory:
        """Content moderation events belong to the ADMIN category."""
        return EventCategory.ADMIN
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate content moderation specific requirements."""
        if not self.content_id or not isinstance(self.content_id, str):
            errors.append("Content ID must be a non-empty string")
        
        if not self.content_type or not isinstance(self.content_type, str):
            errors.append("Content type must be a non-empty string")
        
        valid_actions = {"approved", "rejected", "flagged", "deleted", "quarantined"}
        if self.moderation_action not in valid_actions:
            errors.append(f"Moderation action must be one of {valid_actions}")


class AnalyticsEvent(SystemEvent):
    """
    Event fired to record analytics data for business intelligence.
    
    This event aggregates user behavior, system performance,
    and business metrics for reporting and analysis.
    """
    
    def __init__(
        self,
        metric_name: str,
        metric_value: float,
        metric_type: str,  # counter, gauge, histogram, timer
        dimensions: Dict[str, str] = None,
        timestamp_override: Optional[datetime] = None,
        aggregation_period: str = "daily",  # hourly, daily, weekly, monthly
        user_segment: Optional[str] = None,
        source_service: str = "analytics",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize AnalyticsEvent.
        
        Args:
            metric_name: Name of the metric being recorded
            metric_value: Value of the metric
            metric_type: Type of metric (counter, gauge, histogram, timer)
            dimensions: Additional dimensions for filtering/grouping
            timestamp_override: Override timestamp for the metric
            aggregation_period: How the metric should be aggregated
            user_segment: User segment this metric applies to
            source_service: Service generating the analytics
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "metric_type": metric_type,
            "dimensions": dimensions or {},
            "timestamp_override": timestamp_override.isoformat() if timestamp_override else None,
            "aggregation_period": aggregation_period,
            "user_segment": user_segment,
            "recorded_at": datetime.utcnow().isoformat(),
        }
        
        super().__init__(
            source_service=source_service,
            system_component="analytics",
            correlation_id=correlation_id,
            priority=EventPriority.LOW,  # Analytics events are low priority
            payload=payload,
            **kwargs
        )
    
    @property
    def metric_name(self) -> str:
        """Name of the metric."""
        return self.payload["metric_name"]
    
    @property
    def metric_value(self) -> float:
        """Value of the metric."""
        return self.payload["metric_value"]
    
    @property
    def metric_type(self) -> str:
        """Type of metric."""
        return self.payload["metric_type"]
    
    @property
    def dimensions(self) -> Dict[str, str]:
        """Additional dimensions."""
        return self.payload["dimensions"]
    
    def _get_event_category(self) -> EventCategory:
        """Analytics events belong to the ADMIN category."""
        return EventCategory.ADMIN
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate analytics specific requirements."""
        if not self.metric_name or not isinstance(self.metric_name, str):
            errors.append("Metric name must be a non-empty string")
        
        if not isinstance(self.metric_value, (int, float)):
            errors.append("Metric value must be a number")
        
        valid_types = {"counter", "gauge", "histogram", "timer"}
        if self.metric_type not in valid_types:
            errors.append(f"Metric type must be one of {valid_types}")


class AdminActionPerformedEvent(SystemEvent):
    """
    Event fired when an admin performs any administrative action.
    
    This event provides a complete audit trail of all
    administrative operations for security and compliance.
    """
    
    def __init__(
        self,
        admin_user_id: int,
        action_type: str,
        action_description: str,
        target_resource_type: str,  # user, content, system, configuration
        target_resource_id: Optional[str],
        action_parameters: Dict[str, Any] = None,
        action_result: str = "success",  # success, failure, partial
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        source_service: str = "admin",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize AdminActionPerformedEvent.
        
        Args:
            admin_user_id: ID of the admin performing the action
            action_type: Type of action (create, update, delete, ban, etc.)
            action_description: Human-readable description of the action
            target_resource_type: Type of resource being acted upon
            target_resource_id: ID of the target resource
            action_parameters: Parameters used for the action
            action_result: Result of the action
            ip_address: Admin's IP address
            user_agent: Admin's user agent
            source_service: Service handling the admin action
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "admin_user_id": admin_user_id,
            "action_type": action_type,
            "action_description": action_description,
            "target_resource_type": target_resource_type,
            "target_resource_id": target_resource_id,
            "action_parameters": action_parameters or {},
            "action_result": action_result,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "performed_at": datetime.utcnow().isoformat(),
        }
        
        super().__init__(
            source_service=source_service,
            system_component="admin_panel",
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,  # Admin actions are important
            payload=payload,
            **kwargs
        )
    
    @property
    def admin_user_id(self) -> int:
        """ID of the admin."""
        return self.payload["admin_user_id"]
    
    @property
    def action_type(self) -> str:
        """Type of action."""
        return self.payload["action_type"]
    
    @property
    def action_description(self) -> str:
        """Description of the action."""
        return self.payload["action_description"]
    
    @property
    def target_resource_type(self) -> str:
        """Type of target resource."""
        return self.payload["target_resource_type"]
    
    @property
    def action_result(self) -> str:
        """Result of the action."""
        return self.payload["action_result"]
    
    @property
    def was_successful(self) -> bool:
        """Whether the action was successful."""
        return self.action_result == "success"
    
    def _get_event_category(self) -> EventCategory:
        """Admin action events belong to the ADMIN category."""
        return EventCategory.ADMIN
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate admin action specific requirements."""
        if not isinstance(self.admin_user_id, int) or self.admin_user_id <= 0:
            errors.append("Admin user ID must be a positive integer")
        
        required_string_fields = ["action_type", "action_description", "target_resource_type"]
        for field in required_string_fields:
            value = getattr(self, field)
            if not value or not isinstance(value, str):
                errors.append(f"{field.replace('_', ' ').title()} must be a non-empty string")
        
        valid_results = {"success", "failure", "partial"}
        if self.action_result not in valid_results:
            errors.append(f"Action result must be one of {valid_results}")


class SystemMaintenanceEvent(SystemEvent):
    """
    Event fired during system maintenance operations.
    
    This event tracks maintenance windows, updates,
    and system changes for operational visibility.
    """
    
    def __init__(
        self,
        maintenance_type: str,  # scheduled, emergency, update, backup
        maintenance_description: str,
        maintenance_status: str,  # started, completed, failed, cancelled
        affected_services: List[str] = None,
        estimated_duration_minutes: Optional[int] = None,
        maintenance_window_start: Optional[datetime] = None,
        maintenance_window_end: Optional[datetime] = None,
        performed_by: Optional[str] = None,
        source_service: str = "system",
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize SystemMaintenanceEvent.
        
        Args:
            maintenance_type: Type of maintenance
            maintenance_description: Description of what's being done
            maintenance_status: Current status of maintenance
            affected_services: Services affected by maintenance
            estimated_duration_minutes: Estimated duration
            maintenance_window_start: Planned start time
            maintenance_window_end: Planned end time
            performed_by: Who is performing the maintenance
            source_service: Service reporting the maintenance
            correlation_id: ID for tracing related events
            **kwargs: Additional arguments
        """
        payload = {
            "maintenance_type": maintenance_type,
            "maintenance_description": maintenance_description,
            "maintenance_status": maintenance_status,
            "affected_services": affected_services or [],
            "estimated_duration_minutes": estimated_duration_minutes,
            "maintenance_window_start": maintenance_window_start.isoformat() if maintenance_window_start else None,
            "maintenance_window_end": maintenance_window_end.isoformat() if maintenance_window_end else None,
            "performed_by": performed_by,
            "event_timestamp": datetime.utcnow().isoformat(),
        }
        
        # Critical if emergency maintenance
        priority = EventPriority.CRITICAL if maintenance_type == "emergency" else EventPriority.HIGH
        
        super().__init__(
            source_service=source_service,
            system_component="maintenance",
            correlation_id=correlation_id,
            priority=priority,
            payload=payload,
            **kwargs
        )
    
    @property
    def maintenance_type(self) -> str:
        """Type of maintenance."""
        return self.payload["maintenance_type"]
    
    @property
    def maintenance_status(self) -> str:
        """Status of maintenance."""
        return self.payload["maintenance_status"]
    
    @property
    def affected_services(self) -> List[str]:
        """Services affected by maintenance."""
        return self.payload["affected_services"]
    
    def _get_event_category(self) -> EventCategory:
        """Maintenance events belong to the ADMIN category."""
        return EventCategory.ADMIN
    
    def _custom_validation(self, errors: List[str]) -> None:
        """Validate maintenance event specific requirements."""
        valid_types = {"scheduled", "emergency", "update", "backup", "patch"}
        if self.maintenance_type not in valid_types:
            errors.append(f"Maintenance type must be one of {valid_types}")
        
        valid_statuses = {"started", "completed", "failed", "cancelled", "in_progress"}
        if self.maintenance_status not in valid_statuses:
            errors.append(f"Maintenance status must be one of {valid_statuses}")


# Export all admin events
__all__ = [
    "UserRegisteredEvent",
    "UserBannedEvent",
    "ContentModerationEvent",
    "AnalyticsEvent",
    "AdminActionPerformedEvent",
    "SystemMaintenanceEvent",
]