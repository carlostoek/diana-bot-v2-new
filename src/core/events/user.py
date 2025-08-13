"""
User Management Events for Diana Bot V2.

This module defines all events related to user management, authentication,
onboarding, and profile operations within the event-driven architecture.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from .base import DomainEvent, EventCategory, EventPriority, ValidationLevel


class UserRegisteredEvent(DomainEvent):
    """Event triggered when a new user registers with the system."""

    def __init__(
        self,
        user_id: int,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: str = "",
        language_code: str = "en",
        is_premium: bool = False,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "language_code": language_code,
            "is_premium": is_premium,
            "registration_source": kwargs.get("registration_source", "telegram"),
            "initial_role": kwargs.get("initial_role", "free"),
        }

        super().__init__(
            event_type="user.registered",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.telegram_id": {"required": True, "type": int, "min": 1},
            "payload.first_name": {"required": True, "type": str, "min_length": 1},
            "payload.language_code": {
                "required": True,
                "type": str,
                "pattern": r"^[a-z]{2}$",
            },
        }


class UserProfileUpdatedEvent(DomainEvent):
    """Event triggered when a user updates their profile information."""

    def __init__(
        self,
        user_id: int,
        updated_fields: Dict[str, Any],
        previous_values: Optional[Dict[str, Any]] = None,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "updated_fields": updated_fields,
            "previous_values": previous_values or {},
            "update_source": kwargs.get("update_source", "user"),
            "field_count": len(updated_fields),
        }

        super().__init__(
            event_type="user.profile.updated",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.updated_fields": {"required": True, "type": dict, "min_keys": 1},
        }


class UserAuthenticationFailedEvent(DomainEvent):
    """Event triggered when user authentication fails."""

    def __init__(
        self,
        user_id: Optional[int],
        telegram_id: Optional[int],
        failure_reason: str,
        attempt_source: str = "telegram",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "telegram_id": telegram_id,
            "failure_reason": failure_reason,
            "attempt_source": attempt_source,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "security_risk_level": kwargs.get("security_risk_level", "low"),
        }

        super().__init__(
            event_type="user.authentication.failed",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "payload.failure_reason": {"required": True, "type": str, "min_length": 1},
            "payload.attempt_source": {"required": True, "type": str, "min_length": 1},
        }


class UserSessionCreatedEvent(DomainEvent):
    """Event triggered when a new user session is created."""

    def __init__(
        self,
        user_id: int,
        session_id: str,
        session_type: str = "telegram_bot",
        device_info: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "session_id": session_id,
            "session_type": session_type,
            "device_info": device_info or {},
            "ip_address": ip_address,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "login_method": kwargs.get("login_method", "telegram"),
        }

        super().__init__(
            event_type="user.session.created",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.session_id": {"required": True, "type": str, "min_length": 1},
            "payload.session_type": {"required": True, "type": str, "min_length": 1},
        }


class UserRoleChangedEvent(DomainEvent):
    """Event triggered when a user's role is changed."""

    def __init__(
        self,
        user_id: int,
        previous_role: str,
        new_role: str,
        changed_by_user_id: Optional[int] = None,
        reason: Optional[str] = None,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "previous_role": previous_role,
            "new_role": new_role,
            "changed_by_user_id": changed_by_user_id,
            "reason": reason,
            "change_timestamp": datetime.utcnow().isoformat(),
            "permissions_affected": kwargs.get("permissions_affected", []),
        }

        super().__init__(
            event_type="user.role.changed",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.previous_role": {"required": True, "type": str, "min_length": 1},
            "payload.new_role": {"required": True, "type": str, "min_length": 1},
        }


class UserSubscriptionChangedEvent(DomainEvent):
    """Event triggered when a user's subscription status changes."""

    def __init__(
        self,
        user_id: int,
        subscription_type: str,
        previous_status: Optional[str],
        new_status: str,
        subscription_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "subscription_type": subscription_type,
            "previous_status": previous_status,
            "new_status": new_status,
            "subscription_id": subscription_id,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "change_reason": kwargs.get("change_reason", "user_action"),
            "payment_provider": kwargs.get("payment_provider"),
        }

        super().__init__(
            event_type="user.subscription.changed",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.subscription_type": {
                "required": True,
                "type": str,
                "min_length": 1,
            },
            "payload.new_status": {"required": True, "type": str, "min_length": 1},
        }


class UserOnboardingStartedEvent(DomainEvent):
    """Event triggered when a user starts the onboarding process."""

    def __init__(
        self,
        user_id: int,
        onboarding_flow: str = "standard",
        starting_step: str = "welcome",
        source_trigger: str = "first_interaction",
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "onboarding_flow": onboarding_flow,
            "starting_step": starting_step,
            "source_trigger": source_trigger,
            "estimated_duration_minutes": kwargs.get("estimated_duration_minutes", 5),
            "user_agent": kwargs.get("user_agent"),
        }

        super().__init__(
            event_type="user.onboarding.started",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.onboarding_flow": {"required": True, "type": str, "min_length": 1},
            "payload.starting_step": {"required": True, "type": str, "min_length": 1},
        }


class UserOnboardingCompletedEvent(DomainEvent):
    """Event triggered when a user completes the onboarding process."""

    def __init__(
        self,
        user_id: int,
        completed_steps: list,
        total_duration_seconds: int,
        personality_traits: Optional[Dict[str, Any]] = None,
        completion_rate: float = 100.0,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "completed_steps": completed_steps,
            "total_duration_seconds": total_duration_seconds,
            "personality_traits": personality_traits or {},
            "completion_rate": completion_rate,
            "tutorial_skipped": kwargs.get("tutorial_skipped", False),
            "user_feedback": kwargs.get("user_feedback"),
        }

        super().__init__(
            event_type="user.onboarding.completed",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.completed_steps": {
                "required": True,
                "type": list,
                "min_length": 1,
            },
            "payload.total_duration_seconds": {"required": True, "type": int, "min": 0},
            "payload.completion_rate": {
                "required": True,
                "type": float,
                "min": 0,
                "max": 100,
            },
        }


class UserPersonalityDetectedEvent(DomainEvent):
    """Event triggered when user personality traits are detected or updated."""

    def __init__(
        self,
        user_id: int,
        personality_traits: Dict[str, Any],
        primary_trait: str,
        confidence_score: int,
        detection_method: str = "onboarding_quiz",
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "personality_traits": personality_traits,
            "primary_trait": primary_trait,
            "confidence_score": confidence_score,
            "detection_method": detection_method,
            "trait_scores": kwargs.get("trait_scores", {}),
            "recommended_content": kwargs.get("recommended_content", []),
        }

        super().__init__(
            event_type="user.personality.detected",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.personality_traits": {
                "required": True,
                "type": dict,
                "min_keys": 1,
            },
            "payload.primary_trait": {"required": True, "type": str, "min_length": 1},
            "payload.confidence_score": {
                "required": True,
                "type": int,
                "min": 0,
                "max": 100,
            },
        }


class UserActivityDetectedEvent(DomainEvent):
    """Event triggered when user activity is detected for various tracking purposes."""

    def __init__(
        self,
        user_id: int,
        activity_type: str,
        activity_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "activity_type": activity_type,
            "activity_data": activity_data or {},
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "platform": kwargs.get("platform", "telegram"),
        }

        super().__init__(
            event_type="user.activity.detected",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.LOW,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.activity_type": {"required": True, "type": str, "min_length": 1},
        }


class UserPreferencesUpdatedEvent(DomainEvent):
    """Event triggered when user preferences are updated."""

    def __init__(
        self,
        user_id: int,
        preference_category: str,
        updated_preferences: Dict[str, Any],
        previous_preferences: Optional[Dict[str, Any]] = None,
        source_service: str = "user_service",
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "preference_category": preference_category,
            "updated_preferences": updated_preferences,
            "previous_preferences": previous_preferences or {},
            "change_source": kwargs.get("change_source", "user"),
            "affects_personalization": kwargs.get("affects_personalization", True),
        }

        super().__init__(
            event_type="user.preferences.updated",
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload=payload,
            **kwargs,
        )

    def _get_event_category(self) -> EventCategory:
        return EventCategory.USER

    def _get_validation_rules(self) -> Dict[str, Any]:
        return {
            "user_id": {"required": True, "type": int, "min": 1},
            "payload.preference_category": {
                "required": True,
                "type": str,
                "min_length": 1,
            },
            "payload.updated_preferences": {
                "required": True,
                "type": dict,
                "min_keys": 1,
            },
        }
