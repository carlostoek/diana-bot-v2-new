"""
Anti-Abuse Validator for Gamification System

This module provides comprehensive protection against points gaming, abuse, and
fraudulent behavior while maintaining a smooth user experience. It implements
rate limiting, pattern detection, and behavioral analysis to ensure the integrity
of the points system.

Key Features:
- Rate limiting per action type and user
- Suspicious pattern detection
- Context validation for all actions
- Temporal analysis for gaming detection
- IP and device fingerprinting support
- Graduated penalty system
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from ..interfaces import ActionType, AntiAbuseViolation, IAntiAbuseValidator

# Configure logging
logger = logging.getLogger(__name__)


class AntiAbuseValidator(IAntiAbuseValidator):
    """
    Comprehensive anti-abuse validation system for the gamification engine.

    Provides multiple layers of protection:
    1. Rate limiting per action type
    2. Pattern detection for suspicious behavior
    3. Context validation for action legitimacy
    4. Temporal analysis for gaming detection
    5. IP/device tracking for multi-account detection
    """

    def __init__(
        self,
        enable_rate_limiting: bool = True,
        enable_pattern_detection: bool = True,
        enable_context_validation: bool = True,
        max_memory_entries: int = 10000,
    ):
        """
        Initialize the anti-abuse validator.

        Args:
            enable_rate_limiting: Enable rate limiting checks
            enable_pattern_detection: Enable suspicious pattern detection
            enable_context_validation: Enable context data validation
            max_memory_entries: Maximum entries to keep in memory
        """
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_pattern_detection = enable_pattern_detection
        self.enable_context_validation = enable_context_validation
        self.max_memory_entries = max_memory_entries

        # Rate limiting configuration per action type
        self.rate_limits = {
            ActionType.DAILY_LOGIN: {"max_count": 1, "window_hours": 24},
            ActionType.LOGIN: {"max_count": 10, "window_hours": 1},
            ActionType.MESSAGE_SENT: {"max_count": 100, "window_hours": 1},
            ActionType.TRIVIA_COMPLETED: {"max_count": 20, "window_hours": 1},
            ActionType.STORY_CHAPTER_COMPLETED: {"max_count": 10, "window_hours": 1},
            ActionType.STORY_DECISION_MADE: {"max_count": 50, "window_hours": 1},
            ActionType.FRIEND_REFERRAL: {"max_count": 5, "window_hours": 24},
            ActionType.COMMUNITY_PARTICIPATION: {"max_count": 50, "window_hours": 1},
            ActionType.VIP_PURCHASE: {"max_count": 10, "window_hours": 24},
            ActionType.SUBSCRIPTION_RENEWAL: {"max_count": 5, "window_hours": 24},
            ActionType.ACHIEVEMENT_UNLOCKED: {"max_count": 20, "window_hours": 1},
            ActionType.STREAK_BONUS: {"max_count": 1, "window_hours": 24},
            ActionType.CHALLENGE_COMPLETED: {"max_count": 10, "window_hours": 1},
        }

        # In-memory tracking (in production, this would be Redis-backed)
        self.user_actions: Dict[int, Dict[ActionType, deque]] = defaultdict(
            lambda: defaultdict(deque)
        )
        self.user_ips: Dict[int, Set[str]] = defaultdict(set)
        self.ip_users: Dict[str, Set[int]] = defaultdict(set)
        self.user_penalties: Dict[int, Dict[str, Any]] = defaultdict(dict)
        self.suspicious_patterns: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

        # Pattern detection thresholds
        self.pattern_thresholds = {
            "rapid_fire_actions": {"max_actions": 10, "window_seconds": 30},
            "identical_context": {"max_identical": 5, "window_minutes": 60},
            "session_length_abuse": {"max_hours": 12},
            "multi_account_ip": {"max_accounts": 5},
        }

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def validate_action(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """
        Validate if an action is legitimate and should award points.

        Performs comprehensive validation including rate limiting,
        pattern detection, and context validation.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        async with self._lock:
            try:
                # Check if user has active penalties
                penalty_result = await self._check_user_penalties(user_id, timestamp)
                if not penalty_result[0]:
                    return penalty_result

                # Rate limiting validation
                if self.enable_rate_limiting:
                    rate_limit_result = await self._validate_rate_limit(
                        user_id, action_type, timestamp
                    )
                    if not rate_limit_result[0]:
                        await self._record_violation(
                            user_id,
                            action_type,
                            AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
                            rate_limit_result[2],
                            context,
                            timestamp,
                        )
                        return rate_limit_result

                # Pattern detection validation
                if self.enable_pattern_detection:
                    pattern_result = await self._detect_suspicious_patterns(
                        user_id, action_type, context, timestamp
                    )
                    if not pattern_result[0]:
                        await self._record_violation(
                            user_id,
                            action_type,
                            pattern_result[1],
                            pattern_result[2],
                            context,
                            timestamp,
                        )
                        return pattern_result

                # Context validation
                if self.enable_context_validation:
                    context_result = await self._validate_context(
                        user_id, action_type, context, timestamp
                    )
                    if not context_result[0]:
                        await self._record_violation(
                            user_id,
                            action_type,
                            AntiAbuseViolation.INVALID_CONTEXT,
                            context_result[2],
                            context,
                            timestamp,
                        )
                        return context_result

                # All validations passed
                return True, None, None

            except Exception as e:
                logger.error(f"Error validating action for user {user_id}: {e}")
                # Fail open for user experience, but log for investigation
                return True, None, None

    async def record_action(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        points_awarded: int,
    ) -> None:
        """
        Record a validated action for future anti-abuse checking.

        Stores action data in memory for pattern detection and rate limiting.
        In production, this would be backed by Redis or database.
        """
        timestamp = datetime.now(timezone.utc)

        async with self._lock:
            # Record action with full context
            action_record = {
                "timestamp": timestamp,
                "context": context,
                "points_awarded": points_awarded,
                "ip_address": context.get("ip_address"),
                "user_agent": context.get("user_agent"),
            }

            # Add to user's action history
            user_actions = self.user_actions[user_id][action_type]
            user_actions.append(action_record)

            # Maintain memory limits
            rate_limit = self.rate_limits.get(action_type, {"max_count": 100})
            max_entries = (
                rate_limit["max_count"] * 10
            )  # Keep 10x more for pattern detection
            while len(user_actions) > max_entries:
                user_actions.popleft()

            # Track IP associations
            ip_address = context.get("ip_address")
            if ip_address:
                self.user_ips[user_id].add(ip_address)
                self.ip_users[ip_address].add(user_id)

                # Limit IP tracking memory
                if len(self.user_ips[user_id]) > 10:
                    oldest_ip = list(self.user_ips[user_id])[0]
                    self.user_ips[user_id].remove(oldest_ip)
                    if user_id in self.ip_users[oldest_ip]:
                        self.ip_users[oldest_ip].remove(user_id)

            # Clean up old data periodically
            if len(self.user_actions) > self.max_memory_entries:
                await self._cleanup_old_data()

    async def get_rate_limit_status(
        self,
        user_id: int,
        action_type: ActionType,
    ) -> Dict[str, Any]:
        """
        Get current rate limit status for a user and action type.
        """
        rate_limit = self.rate_limits.get(action_type)
        if not rate_limit:
            return {
                "actions_remaining": 999,
                "reset_time": datetime.now(timezone.utc) + timedelta(hours=1),
                "window_duration": timedelta(hours=1),
            }

        async with self._lock:
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(hours=rate_limit["window_hours"])

            # Count actions in current window
            user_actions = self.user_actions[user_id][action_type]
            actions_in_window = sum(
                1 for action in user_actions if action["timestamp"] >= window_start
            )

            actions_remaining = max(0, rate_limit["max_count"] - actions_in_window)
            reset_time = window_start + timedelta(hours=rate_limit["window_hours"])

            return {
                "actions_remaining": actions_remaining,
                "reset_time": reset_time,
                "window_duration": timedelta(hours=rate_limit["window_hours"]),
                "actions_used": actions_in_window,
                "max_actions": rate_limit["max_count"],
            }

    async def _check_user_penalties(
        self,
        user_id: int,
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Check if user has active penalties that prevent actions."""
        penalties = self.user_penalties.get(user_id, {})

        for penalty_type, penalty_data in penalties.items():
            if penalty_data.get("active", False):
                expiry = penalty_data.get("expiry")
                if expiry and timestamp < expiry:
                    # Penalty still active
                    remaining = expiry - timestamp
                    return (
                        False,
                        AntiAbuseViolation.GAMING_BEHAVIOR,
                        f"User has active {penalty_type} penalty for {remaining}",
                    )
                else:
                    # Penalty expired, remove it
                    penalty_data["active"] = False

        return True, None, None

    async def _validate_rate_limit(
        self,
        user_id: int,
        action_type: ActionType,
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Validate action against rate limits."""
        rate_limit = self.rate_limits.get(action_type)
        if not rate_limit:
            return True, None, None

        window_start = timestamp - timedelta(hours=rate_limit["window_hours"])

        # Count actions in current window
        user_actions = self.user_actions[user_id][action_type]
        actions_in_window = sum(
            1 for action in user_actions if action["timestamp"] >= window_start
        )

        if actions_in_window >= rate_limit["max_count"]:
            return (
                False,
                AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
                f"Rate limit exceeded for {action_type.value}: {actions_in_window}/{rate_limit['max_count']} "
                f"in {rate_limit['window_hours']} hours",
            )

        return True, None, None

    async def _detect_suspicious_patterns(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Detect suspicious behavioral patterns."""

        # Check rapid-fire actions
        rapid_fire_result = await self._check_rapid_fire_actions(user_id, timestamp)
        if not rapid_fire_result[0]:
            return rapid_fire_result

        # Check for identical context abuse
        identical_context_result = await self._check_identical_context(
            user_id, action_type, context, timestamp
        )
        if not identical_context_result[0]:
            return identical_context_result

        # Check session length abuse
        session_result = await self._check_session_length_abuse(user_id, timestamp)
        if not session_result[0]:
            return session_result

        # Check multi-account patterns
        multi_account_result = await self._check_multi_account_patterns(
            user_id, context.get("ip_address"), timestamp
        )
        if not multi_account_result[0]:
            return multi_account_result

        return True, None, None

    async def _check_rapid_fire_actions(
        self,
        user_id: int,
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Check for rapid-fire action patterns."""
        threshold = self.pattern_thresholds["rapid_fire_actions"]
        window_start = timestamp - timedelta(seconds=threshold["window_seconds"])

        # Count all actions across all types in the window
        total_actions = 0
        for action_type, actions in self.user_actions[user_id].items():
            total_actions += sum(
                1 for action in actions if action["timestamp"] >= window_start
            )

        if total_actions >= threshold["max_actions"]:
            return (
                False,
                AntiAbuseViolation.SUSPICIOUS_PATTERN,
                f"Rapid-fire actions detected: {total_actions} actions in {threshold['window_seconds']} seconds",
            )

        return True, None, None

    async def _check_identical_context(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Check for repeated identical context patterns."""
        threshold = self.pattern_thresholds["identical_context"]
        window_start = timestamp - timedelta(minutes=threshold["window_minutes"])

        # Create context fingerprint (excluding metadata)
        context_fingerprint = {
            k: v
            for k, v in context.items()
            if k not in {"ip_address", "user_agent", "timestamp", "session_id"}
        }
        context_hash = hash(json.dumps(context_fingerprint, sort_keys=True))

        # Count identical contexts in window
        user_actions = self.user_actions[user_id][action_type]
        identical_count = 0
        for action in user_actions:
            if action["timestamp"] >= window_start:
                action_context = {
                    k: v
                    for k, v in action["context"].items()
                    if k not in {"ip_address", "user_agent", "timestamp", "session_id"}
                }
                action_hash = hash(json.dumps(action_context, sort_keys=True))
                if action_hash == context_hash:
                    identical_count += 1

        if identical_count >= threshold["max_identical"]:
            return (
                False,
                AntiAbuseViolation.SUSPICIOUS_PATTERN,
                f"Identical context abuse detected: {identical_count} identical actions in {threshold['window_minutes']} minutes",
            )

        return True, None, None

    async def _check_session_length_abuse(
        self,
        user_id: int,
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Check for unreasonably long session patterns."""
        threshold = self.pattern_thresholds["session_length_abuse"]
        window_start = timestamp - timedelta(hours=threshold["max_hours"])

        # Check if user has been active continuously for too long
        has_activity = False
        for action_type, actions in self.user_actions[user_id].items():
            for action in actions:
                if action["timestamp"] >= window_start:
                    has_activity = True
                    break
            if has_activity:
                break

        if has_activity:
            # Check for continuous activity (actions every hour)
            hours_with_activity = set()
            for action_type, actions in self.user_actions[user_id].items():
                for action in actions:
                    if action["timestamp"] >= window_start:
                        hour = action["timestamp"].replace(
                            minute=0, second=0, microsecond=0
                        )
                        hours_with_activity.add(hour)

            if len(hours_with_activity) >= threshold["max_hours"] * 0.8:  # 80% of hours
                return (
                    False,
                    AntiAbuseViolation.SUSPICIOUS_PATTERN,
                    f"Excessive session length detected: active for {len(hours_with_activity)} hours",
                )

        return True, None, None

    async def _check_multi_account_patterns(
        self,
        user_id: int,
        ip_address: Optional[str],
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Check for multi-account abuse patterns."""
        if not ip_address:
            return True, None, None

        threshold = self.pattern_thresholds["multi_account_ip"]

        # Check how many accounts are associated with this IP
        accounts_on_ip = len(self.ip_users.get(ip_address, set()))

        if accounts_on_ip >= threshold["max_accounts"]:
            return (
                False,
                AntiAbuseViolation.SUSPICIOUS_PATTERN,
                f"Multi-account pattern detected: {accounts_on_ip} accounts on IP {ip_address}",
            )

        return True, None, None

    async def _validate_context(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Validate action context for legitimacy."""

        # Basic context validation
        if not isinstance(context, dict):
            return (
                False,
                AntiAbuseViolation.INVALID_CONTEXT,
                "Context must be a dictionary",
            )

        # Action-specific validation
        validation_result = await self._validate_action_specific_context(
            action_type, context
        )
        if not validation_result[0]:
            return validation_result

        # Temporal validation
        temporal_result = await self._validate_temporal_context(
            user_id, action_type, context, timestamp
        )
        if not temporal_result[0]:
            return temporal_result

        return True, None, None

    async def _validate_action_specific_context(
        self,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Validate context specific to the action type."""

        if action_type == ActionType.TRIVIA_COMPLETED:
            # Trivia should have question_id and answer
            if "question_id" not in context or "answer" not in context:
                return (
                    False,
                    AntiAbuseViolation.INVALID_CONTEXT,
                    "Trivia completion requires question_id and answer",
                )

        elif action_type == ActionType.STORY_CHAPTER_COMPLETED:
            # Story should have chapter_id
            if "chapter_id" not in context:
                return (
                    False,
                    AntiAbuseViolation.INVALID_CONTEXT,
                    "Story completion requires chapter_id",
                )

        elif action_type == ActionType.FRIEND_REFERRAL:
            # Referral should have referred_user_id
            if "referred_user_id" not in context:
                return (
                    False,
                    AntiAbuseViolation.INVALID_CONTEXT,
                    "Friend referral requires referred_user_id",
                )

        elif action_type == ActionType.VIP_PURCHASE:
            # Purchase should have transaction info
            if "transaction_id" not in context or "amount" not in context:
                return (
                    False,
                    AntiAbuseViolation.INVALID_CONTEXT,
                    "VIP purchase requires transaction_id and amount",
                )

        return True, None, None

    async def _validate_temporal_context(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        timestamp: datetime,
    ) -> Tuple[bool, Optional[AntiAbuseViolation], Optional[str]]:
        """Validate temporal aspects of the context."""

        # Check for duplicate transactions
        if action_type in [ActionType.VIP_PURCHASE, ActionType.SUBSCRIPTION_RENEWAL]:
            transaction_id = context.get("transaction_id")
            if transaction_id:
                # Check if we've seen this transaction before
                for action in self.user_actions[user_id][action_type]:
                    if action["context"].get("transaction_id") == transaction_id:
                        return (
                            False,
                            AntiAbuseViolation.DUPLICATE_ACTION,
                            f"Duplicate transaction detected: {transaction_id}",
                        )

        # Check for reasonable timing
        if action_type == ActionType.STORY_CHAPTER_COMPLETED:
            # Check if user completed chapter too quickly
            chapter_id = context.get("chapter_id")
            if chapter_id:
                for action in self.user_actions[user_id][
                    ActionType.STORY_DECISION_MADE
                ]:
                    if action["context"].get(
                        "chapter_id"
                    ) == chapter_id and timestamp - action["timestamp"] < timedelta(
                        minutes=1
                    ):
                        return (
                            False,
                            AntiAbuseViolation.SUSPICIOUS_PATTERN,
                            f"Chapter completed too quickly: {chapter_id}",
                        )

        return True, None, None

    async def _record_violation(
        self,
        user_id: int,
        action_type: ActionType,
        violation: AntiAbuseViolation,
        message: str,
        context: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Record an anti-abuse violation and apply penalties if needed."""
        violation_record = {
            "timestamp": timestamp,
            "action_type": action_type,
            "violation": violation,
            "message": message,
            "context": context,
        }

        self.suspicious_patterns[user_id].append(violation_record)

        # Apply graduated penalties based on violation history
        recent_violations = [
            v
            for v in self.suspicious_patterns[user_id]
            if timestamp - v["timestamp"] < timedelta(hours=24)
        ]

        violation_count = len(recent_violations)

        if violation_count >= 5:
            # Severe penalty: 24-hour point reduction
            self.user_penalties[user_id]["point_reduction"] = {
                "active": True,
                "expiry": timestamp + timedelta(hours=24),
                "reduction_factor": 0.5,  # 50% point reduction
                "reason": f"Multiple violations: {violation_count}",
            }
        elif violation_count >= 3:
            # Moderate penalty: 1-hour cooldown
            self.user_penalties[user_id]["cooldown"] = {
                "active": True,
                "expiry": timestamp + timedelta(hours=1),
                "reason": f"Pattern violations: {violation_count}",
            }

        # Log for admin review
        logger.warning(
            f"Anti-abuse violation: user={user_id}, action={action_type.value}, "
            f"violation={violation.value}, message={message}"
        )

    async def _cleanup_old_data(self) -> None:
        """Clean up old tracking data to prevent memory leaks."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        # Clean up old actions
        users_to_remove = []
        for user_id, action_types in self.user_actions.items():
            for action_type, actions in action_types.items():
                # Remove old actions
                while actions and actions[0]["timestamp"] < cutoff:
                    actions.popleft()

            # Remove empty action types
            empty_types = [
                action_type
                for action_type, actions in action_types.items()
                if not actions
            ]
            for action_type in empty_types:
                del action_types[action_type]

            # Mark users with no recent activity for removal
            if not action_types:
                users_to_remove.append(user_id)

        # Remove inactive users
        for user_id in users_to_remove:
            if user_id in self.user_actions:
                del self.user_actions[user_id]
            if user_id in self.user_penalties:
                del self.user_penalties[user_id]
            if user_id in self.suspicious_patterns:
                del self.suspicious_patterns[user_id]

        # Clean up old patterns
        for user_id, patterns in self.suspicious_patterns.items():
            self.suspicious_patterns[user_id] = [
                p for p in patterns if p["timestamp"] >= cutoff
            ]
