"""
Event Bus Core Implementation

This module provides the concrete implementations of event types and the EventBus
class for the Diana Bot V2 system. It builds on the interfaces defined in
interfaces.py to provide specific event types for different domains.

Event Types:
- GameEvent: Gamification-related events (points, achievements, etc.)
- NarrativeEvent: Story progression and decision events
- AdminEvent: Administrative actions requiring audit trails
- UserEvent: General user interactions and profile changes
- SystemEvent: System-level events for monitoring and operations

The EventBus class provides Redis-based pub/sub functionality with:
- High-performance event publishing and subscription
- Event persistence for audit and replay
- Circuit breaker patterns
- Performance monitoring
- Health checks and metrics
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

# Import exceptions to make them available
from .exceptions import (
    EventBusError,
    EventValidationError,
    PublishError,
    SubscribeError,
)

# Import the abstract interfaces
from .interfaces import IEvent, IEventBus, IEventHandler


class GameEvent(IEvent):
    """
    Event type for gamification-related actions.

    Tracks user actions that affect the gamification system:
    - Points earned from various activities
    - Achievement unlocks and progress
    - Streak bonuses and multipliers
    - Challenge completions and rewards

    Required fields:
    - user_id: User performing the action
    - action: Specific gamification action taken
    - points_earned: Points awarded for the action
    - context: Additional context about the action
    """

    VALID_ACTIONS = {
        "login",
        "daily_login",
        "message_sent",
        "story_completed",
        "achievement_unlocked",
        "referral_bonus",
        "vip_purchase",
        "streak_bonus",
        "challenge_completed",
    }

    def __init__(
        self,
        user_id: int,
        action: str,
        points_earned: Union[int, float],
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Create a GameEvent.

        Args:
            user_id: ID of user performing the action
            action: Gamification action type
            points_earned: Points awarded (0-1,000,000)
            context: Additional context about the action
            **kwargs: Additional IEvent parameters
        """
        # Validate game-specific fields
        if not isinstance(user_id, int):
            raise TypeError("user_id must be an integer")

        if not isinstance(action, str):
            raise TypeError("action must be a string")

        if action not in self.VALID_ACTIONS:
            raise EventValidationError(
                f"Invalid action '{action}'. Must be one of: {sorted(self.VALID_ACTIONS)}"
            )

        if not isinstance(points_earned, (int, float)):
            raise TypeError("points_earned must be a number")

        if points_earned < 0:
            raise EventValidationError("points_earned cannot be negative")

        if points_earned > 1000000:
            raise EventValidationError("points_earned cannot exceed 1,000,000")

        if context is not None and not isinstance(context, dict):
            raise TypeError("context must be a dictionary")

        # Store game-specific data
        self.user_id = user_id
        self.action = action
        self.points_earned = points_earned
        self.context = context or {}

        # Build event data
        event_data = {
            "user_id": user_id,
            "action": action,
            "points_earned": points_earned,
            "context": self.context,
        }

        # Auto-generate event type
        event_type = f"game.{action}"

        # Initialize parent IEvent
        super().__init__(type=event_type, data=event_data, **kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameEvent":
        """Reconstruct GameEvent from dictionary."""
        event_data = data.get("data", {})

        timestamp_str = data.get("timestamp")
        timestamp = None
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return cls(
            user_id=event_data["user_id"],
            action=event_data["action"],
            points_earned=event_data["points_earned"],
            context=event_data.get("context", {}),
            id=data.get("id"),
            timestamp=timestamp,
            correlation_id=data.get("correlation_id"),
            source=data.get("source"),
        )


class NarrativeEvent(IEvent):
    """
    Event type for story progression and narrative decisions.

    Tracks user interactions with the narrative system:
    - Chapter progression and completion
    - Decision making and branching paths
    - Character relationship changes
    - Story content unlocking

    Required fields:
    - user_id: User making the decision
    - chapter_id: Story chapter identifier
    - decision_made: Specific decision chosen
    - character_impact: Impact on character relationships
    """

    def __init__(
        self,
        user_id: int,
        chapter_id: str,
        decision_made: str,
        character_impact: Optional[Dict[str, int]] = None,
        choice_time_seconds: Optional[float] = None,
        previous_choices: Optional[List[str]] = None,
        unlocked_content: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Create a NarrativeEvent.

        Args:
            user_id: ID of user making the decision
            chapter_id: Chapter identifier (chapter_XX_name format)
            decision_made: Decision chosen by user
            character_impact: Impact on character relationships (-10 to +10)
            choice_time_seconds: Time taken to make choice
            previous_choices: List of previous decisions in this chapter
            unlocked_content: Content unlocked by this decision
            **kwargs: Additional IEvent parameters
        """
        # Validate all input parameters
        self._validate_basic_fields(user_id, chapter_id, decision_made)
        character_impact = self._validate_character_impact(character_impact)

        # Store narrative-specific data
        self.user_id = user_id
        self.chapter_id = chapter_id
        self.decision_made = decision_made
        self.character_impact = character_impact
        self.choice_time_seconds = choice_time_seconds
        self.previous_choices = previous_choices or []
        self.unlocked_content = unlocked_content or []

        # Build and initialize event
        event_data = self._build_event_data(
            user_id,
            chapter_id,
            decision_made,
            character_impact,
            choice_time_seconds,
            previous_choices,
            unlocked_content,
        )

        # Initialize parent IEvent
        super().__init__(type="narrative.decision_made", data=event_data, **kwargs)

    def _validate_basic_fields(
        self, user_id: int, chapter_id: str, decision_made: str
    ) -> None:
        """Validate basic narrative event fields."""
        if not isinstance(user_id, int):
            raise TypeError("user_id must be an integer")

        if not isinstance(chapter_id, str):
            raise TypeError("chapter_id must be a string")

        # Validate chapter ID format
        chapter_pattern = r"^(chapter_\d+_\w+|epilogue_\d+)$"
        if not re.match(chapter_pattern, chapter_id):
            raise EventValidationError(
                f"Invalid chapter_id format: {chapter_id}. Must match pattern 'chapter_XX_name' or 'epilogue_XX'"
            )

        if not isinstance(decision_made, str):
            raise TypeError("decision_made must be a string")

    def _validate_character_impact(
        self, character_impact: Optional[Dict[str, int]]
    ) -> Dict[str, int]:
        """Validate and return character impact dictionary."""
        if character_impact is None:
            character_impact = {}

        if not isinstance(character_impact, dict):
            raise TypeError("character_impact must be a dictionary")

        for character, impact in character_impact.items():
            if not isinstance(impact, int):
                raise EventValidationError(
                    f"Character impact for '{character}' must be an integer"
                )
            if impact < -10 or impact > 10:
                raise EventValidationError(
                    f"Character impact for '{character}' must be between -10 and +10"
                )

        return character_impact

    def _build_event_data(
        self,
        user_id: int,
        chapter_id: str,
        decision_made: str,
        character_impact: Dict[str, int],
        choice_time_seconds: Optional[float],
        previous_choices: Optional[List[str]],
        unlocked_content: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Build event data dictionary."""
        event_data = {
            "user_id": user_id,
            "chapter_id": chapter_id,
            "decision_made": decision_made,
            "character_impact": character_impact,
        }

        if choice_time_seconds is not None:
            event_data["choice_time_seconds"] = choice_time_seconds

        if previous_choices:
            event_data["previous_choices"] = previous_choices

        if unlocked_content:
            event_data["unlocked_content"] = unlocked_content

        return event_data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NarrativeEvent":
        """Reconstruct NarrativeEvent from dictionary."""
        event_data = data.get("data", {})

        timestamp_str = data.get("timestamp")
        timestamp = None
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return cls(
            user_id=event_data["user_id"],
            chapter_id=event_data["chapter_id"],
            decision_made=event_data["decision_made"],
            character_impact=event_data.get("character_impact", {}),
            choice_time_seconds=event_data.get("choice_time_seconds"),
            previous_choices=event_data.get("previous_choices"),
            unlocked_content=event_data.get("unlocked_content"),
            id=data.get("id"),
            timestamp=timestamp,
            correlation_id=data.get("correlation_id"),
            source=data.get("source"),
        )


class AdminEvent(IEvent):
    """
    Event type for administrative actions.

    Tracks actions performed by administrators that require audit trails:
    - User moderation (bans, warnings, etc.)
    - Content management and deletion
    - System configuration changes
    - Bulk operations and data migrations

    Required fields:
    - admin_id: Administrator performing the action
    - action_type: Type of administrative action
    - target_user: Target user (for user-specific actions)
    - details: Detailed information for audit trail
    """

    VALID_ACTIONS = {
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
    }

    DESTRUCTIVE_ACTIONS = {"user_banned", "content_deleted", "points_adjusted"}
    USER_REQUIRED_ACTIONS = {
        "user_banned",
        "user_warned",
        "points_adjusted",
        "user_role_changed",
    }
    GLOBAL_ACTIONS = {"system_maintenance", "database_migration"}

    def __init__(
        self,
        admin_id: int,
        action_type: str,
        target_user: Optional[int],
        details: Dict[str, Any],
        **kwargs,
    ):
        """
        Create an AdminEvent.

        Args:
            admin_id: ID of administrator performing action
            action_type: Type of administrative action
            target_user: Target user ID (required for user-specific actions)
            details: Detailed information for audit trail
            **kwargs: Additional IEvent parameters
        """
        # Validate admin-specific fields
        if not isinstance(admin_id, int):
            raise TypeError("admin_id must be an integer")

        if not isinstance(action_type, str):
            raise TypeError("action_type must be a string")

        if action_type not in self.VALID_ACTIONS:
            raise EventValidationError(
                f"Invalid action_type '{action_type}'. Must be one of: {sorted(self.VALID_ACTIONS)}"
            )

        if not isinstance(details, dict):
            raise TypeError("details must be a dictionary")

        # Validate audit requirements for destructive actions
        if action_type in self.DESTRUCTIVE_ACTIONS:
            if "reason" not in details or not details["reason"]:
                raise EventValidationError(
                    f"Destructive action '{action_type}' requires a 'reason' in details"
                )

        # Validate target_user requirements
        if action_type in self.USER_REQUIRED_ACTIONS:
            if target_user is None:
                raise EventValidationError(
                    f"Action '{action_type}' requires target_user"
                )

        if target_user is not None and not isinstance(target_user, int):
            raise TypeError("target_user must be an integer")

        # Store admin-specific data
        self.admin_id = admin_id
        self.action_type = action_type
        self.target_user = target_user
        self.details = details

        # Build event data
        event_data = {
            "admin_id": admin_id,
            "action_type": action_type,
            "target_user": target_user,
            "details": details,
        }

        # Auto-generate event type
        event_type = f"admin.{action_type}"

        # Initialize parent IEvent
        super().__init__(type=event_type, data=event_data, **kwargs)

    def contains_sensitive_data(self) -> bool:
        """
        Check if this admin event contains sensitive data.

        Returns:
            True if the event contains sensitive information
        """
        sensitive_keys = {
            "reported_content",
            "reporter_ids",
            "user_data",
            "personal_info",
        }
        return any(key in self.details for key in sensitive_keys)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdminEvent":
        """Reconstruct AdminEvent from dictionary."""
        event_data = data.get("data", {})

        timestamp_str = data.get("timestamp")
        timestamp = None
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return cls(
            admin_id=event_data["admin_id"],
            action_type=event_data["action_type"],
            target_user=event_data.get("target_user"),
            details=event_data["details"],
            id=data.get("id"),
            timestamp=timestamp,
            correlation_id=data.get("correlation_id"),
            source=data.get("source"),
        )


class UserEvent(IEvent):
    """
    Event type for general user actions.

    Tracks user interactions and profile changes:
    - Registration and authentication
    - Profile updates and settings changes
    - Subscription management
    - Content interactions and sharing

    Required fields:
    - user_id: User performing the action
    - event_type: Type of user action
    - user_data: Action-specific data (privacy compliant)
    """

    VALID_EVENT_TYPES = {
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
        "daily_activity",
    }

    FORBIDDEN_PII_KEYS = {"email", "phone", "address", "full_name", "credit_card"}

    def __init__(
        self, user_id: int, event_type: str, user_data: Dict[str, Any], **kwargs
    ):
        """
        Create a UserEvent.

        Args:
            user_id: ID of user performing action
            event_type: Type of user action
            user_data: Action-specific data (must not contain PII)
            **kwargs: Additional IEvent parameters
        """
        # Validate user-specific fields
        if not isinstance(user_id, int):
            raise TypeError("user_id must be an integer")

        if not isinstance(event_type, str):
            raise TypeError("event_type must be a string")

        if event_type not in self.VALID_EVENT_TYPES:
            raise EventValidationError(
                f"Invalid event_type '{event_type}'. Must be one of: {sorted(self.VALID_EVENT_TYPES)}"
            )

        if not isinstance(user_data, dict):
            raise TypeError("user_data must be a dictionary")

        # Validate privacy compliance - no PII beyond user_id
        for key in user_data.keys():
            if key.lower() in self.FORBIDDEN_PII_KEYS:
                raise EventValidationError(f"user_data cannot contain PII field: {key}")

        # Validate data size for privacy (data minimization)
        data_size = len(json.dumps(user_data))
        if data_size > 5000:  # 5KB limit for user data
            raise EventValidationError(
                f"user_data too large: {data_size} bytes (max 5KB)"
            )

        # Store user-specific data
        self.user_id = user_id
        self.event_type = event_type
        self.user_data = user_data

        # Build event data
        event_data = {
            "user_id": user_id,
            "event_type": event_type,
            "user_data": user_data,
        }

        # Auto-generate event type
        full_event_type = f"user.{event_type}"

        # Initialize parent IEvent
        super().__init__(type=full_event_type, data=event_data, **kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserEvent":
        """Reconstruct UserEvent from dictionary."""
        event_data = data.get("data", {})

        timestamp_str = data.get("timestamp")
        timestamp = None
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return cls(
            user_id=event_data["user_id"],
            event_type=event_data["event_type"],
            user_data=event_data["user_data"],
            id=data.get("id"),
            timestamp=timestamp,
            correlation_id=data.get("correlation_id"),
            source=data.get("source"),
        )


class SystemEvent(IEvent):
    """
    Event type for system-level operations.

    Tracks system events for monitoring and operations:
    - Service lifecycle (start, stop, restart)
    - Health checks and performance monitoring
    - Error conditions and alerts
    - Database operations and migrations
    - Configuration changes and deployments

    Required fields:
    - component: System component generating the event
    - event_type: Type of system event
    - system_data: Event-specific system data
    """

    VALID_COMPONENTS = {
        "telegram_adapter",
        "diana_master",
        "gamification_service",
        "narrative_service",
        "admin_service",
        "event_bus",
        "database",
        "redis_cache",
        "payment_service",
    }

    VALID_EVENT_TYPES = {
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
    }

    ALERTING_EVENT_TYPES = {"error_occurred", "performance_alert", "service_stopped"}

    def __init__(
        self, component: str, event_type: str, system_data: Dict[str, Any], **kwargs
    ):
        """
        Create a SystemEvent.

        Args:
            component: System component generating the event
            event_type: Type of system event
            system_data: Event-specific system data
            **kwargs: Additional IEvent parameters
        """
        # Validate system-specific fields
        if not isinstance(component, str):
            raise TypeError("component must be a string")

        if component not in self.VALID_COMPONENTS:
            raise EventValidationError(
                f"Invalid component '{component}'. Must be one of: {sorted(self.VALID_COMPONENTS)}"
            )

        if not isinstance(event_type, str):
            raise TypeError("event_type must be a string")

        if event_type not in self.VALID_EVENT_TYPES:
            raise EventValidationError(
                f"Invalid event_type '{event_type}'. Must be one of: {sorted(self.VALID_EVENT_TYPES)}"
            )

        if not isinstance(system_data, dict):
            raise TypeError("system_data must be a dictionary")

        # Store system-specific data
        self.component = component
        self.event_type = event_type
        self.system_data = system_data

        # Build event data
        event_data = {
            "component": component,
            "event_type": event_type,
            "system_data": system_data,
        }

        # Auto-generate event type
        full_event_type = f"system.{event_type}"

        # Initialize parent IEvent
        super().__init__(type=full_event_type, data=event_data, **kwargs)

    def should_alert(self) -> bool:
        """
        Check if this system event should trigger alerts.

        Returns:
            True if the event should trigger monitoring alerts
        """
        return self.event_type in self.ALERTING_EVENT_TYPES

    def get_severity(self) -> Optional[str]:
        """
        Get the severity level of this system event.

        Returns:
            Severity level ("critical", "warning", "info") or None
        """
        if self.event_type == "error_occurred":
            return self.system_data.get("severity", "warning")
        elif self.event_type == "service_stopped":
            return "critical"
        elif self.event_type == "performance_alert":
            return "warning"
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemEvent":
        """Reconstruct SystemEvent from dictionary."""
        event_data = data.get("data", {})

        timestamp_str = data.get("timestamp")
        timestamp = None
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return cls(
            component=event_data["component"],
            event_type=event_data["event_type"],
            system_data=event_data["system_data"],
            id=data.get("id"),
            timestamp=timestamp,
            correlation_id=data.get("correlation_id"),
            source=data.get("source"),
        )


# Import EventBus from the concrete implementation
from .event_bus import EventBus
