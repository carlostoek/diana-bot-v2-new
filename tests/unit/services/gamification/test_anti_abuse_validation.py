"""
Critical Anti-Abuse Validation Tests

These tests ensure the anti-abuse system prevents gaming and protects
the points economy. Failures here could allow users to exploit the system
and create infinite points, destroying the entire gamification economy.

ZERO TOLERANCE for gaming vulnerabilities.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from services.gamification.engines.anti_abuse_validator import AntiAbuseValidator
from services.gamification.interfaces import ActionType, AntiAbuseViolation
from services.gamification.models import UserGamification


class TestAntiAbuseRateLimit:
    """Test rate limiting mechanisms."""

    @pytest_asyncio.fixture
    async def anti_abuse_validator(self):
        """Create AntiAbuseValidator for testing."""
        validator = AntiAbuseValidator()
        return validator

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement_basic(self, anti_abuse_validator):
        """Test basic rate limiting prevents rapid-fire abuse."""
        user_id = 123
        action_type = ActionType.MESSAGE_SENT

        # Should allow initial requests with varying context
        for i in range(50):  # Try to exceed MESSAGE_SENT limit (100/hour)
            context = {"message": f"test_{i}", "session_id": f"session_{i//10}"}
            is_valid, violation, reason = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context=context,
            )

            if is_valid:
                # Record the action
                await anti_abuse_validator.record_action(
                    user_id=user_id,
                    action_type=action_type,
                    context=context,
                    points_awarded=5,
                )

        # Now try to exceed rate limit - should trigger rate limiting
        violations_count = 0
        for i in range(70):  # Definitely exceed rate limit
            context = {
                "message": f"excess_{i}",
                "session_id": f"session_excess_{i//10}",
            }
            is_valid, violation, reason = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context=context,
            )

            if not is_valid:
                violations_count += 1
                # Should be rate limited, pattern detected, or escalated to gaming behavior
                assert violation in [
                    AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
                    AntiAbuseViolation.SUSPICIOUS_PATTERN,
                    AntiAbuseViolation.GAMING_BEHAVIOR,
                ]
            else:
                # Still record successful actions
                await anti_abuse_validator.record_action(
                    user_id=user_id,
                    action_type=action_type,
                    context=context,
                    points_awarded=5,
                )

        # Should have some violations
        assert violations_count > 0, "Anti-abuse protection failed to trigger"

    @pytest.mark.asyncio
    async def test_rate_limit_per_action_type(self, anti_abuse_validator):
        """Test rate limits are enforced per action type."""
        user_id = 123

        # Max out rate limit for MESSAGE_SENT
        for i in range(15):
            await anti_abuse_validator.record_action(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message": f"msg_{i}"},
                points_awarded=5,
            )

        # MESSAGE_SENT should be rate limited
        is_valid, violation, _ = await anti_abuse_validator.validate_action(
            user_id=user_id,
            action_type=ActionType.MESSAGE_SENT,
            context={"message": "rate_limited"},
        )
        assert not is_valid
        # Could be rate limited, suspicious pattern, or gaming behavior
        assert violation in [
            AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
            AntiAbuseViolation.SUSPICIOUS_PATTERN,
            AntiAbuseViolation.GAMING_BEHAVIOR,
        ]

        # But TRIVIA_COMPLETED should still be allowed
        is_valid, violation, _ = await anti_abuse_validator.validate_action(
            user_id=user_id,
            action_type=ActionType.TRIVIA_COMPLETED,
            context={"correct_answer": True},
        )
        assert is_valid, "Different action type should not be rate limited"

    @pytest.mark.asyncio
    async def test_rate_limit_time_window_reset(self, anti_abuse_validator):
        """Test rate limits reset after time window."""
        user_id = 123
        action_type = ActionType.MESSAGE_SENT

        # Fill rate limit
        for i in range(10):
            await anti_abuse_validator.record_action(
                user_id=user_id,
                action_type=action_type,
                context={"message": f"msg_{i}"},
            )

        # Should be rate limited now
        is_valid, violation, _ = await anti_abuse_validator.validate_action(
            user_id=user_id,
            action_type=action_type,
            context={"message": "rate_limited"},
        )
        assert not is_valid

        # Mock time advancement (in real system, this would be actual time)
        with patch(
            "services.gamification.engines.anti_abuse_validator.datetime"
        ) as mock_datetime:
            # Set time to 1 hour in the future
            future_time = datetime.now(timezone.utc) + timedelta(hours=1)
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Should be allowed again after time window reset
            is_valid, violation, _ = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context={"message": "after_reset"},
            )
            assert is_valid, "Rate limit should reset after time window"

    @pytest.mark.asyncio
    async def test_rate_limit_different_users_independent(self, anti_abuse_validator):
        """Test rate limits are independent per user."""
        action_type = ActionType.MESSAGE_SENT

        # Fill rate limit for user 1
        user1_id = 123
        for i in range(15):
            await anti_abuse_validator.record_action(
                user_id=user1_id,
                action_type=action_type,
                context={"message": f"user1_msg_{i}"},
            )

        # User 1 should be rate limited
        is_valid, violation, _ = await anti_abuse_validator.validate_action(
            user_id=user1_id,
            action_type=action_type,
            context={"message": "rate_limited"},
        )
        assert not is_valid

        # User 2 should not be affected
        user2_id = 456
        is_valid, violation, _ = await anti_abuse_validator.validate_action(
            user_id=user2_id,
            action_type=action_type,
            context={"message": "user2_msg"},
        )
        assert is_valid, "Rate limits should be per-user"


class TestAntiAbusePatternDetection:
    """Test pattern detection for gaming prevention."""

    @pytest_asyncio.fixture
    async def anti_abuse_validator(self):
        """Create AntiAbuseValidator for pattern testing."""
        validator = AntiAbuseValidator()
        return validator

    @pytest.mark.asyncio
    async def test_identical_context_pattern_detection(self, anti_abuse_validator):
        """Test detection of identical context abuse patterns."""
        user_id = 123
        action_type = ActionType.TRIVIA_COMPLETED

        # Submit identical contexts rapidly (gaming pattern)
        identical_context = {
            "question_id": "q123",
            "correct_answer": True,
            "completion_time": 5,
        }

        violations_detected = 0
        for i in range(10):
            is_valid, violation, reason = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context=identical_context,
            )

            if not is_valid and violation == AntiAbuseViolation.SUSPICIOUS_PATTERN:
                violations_detected += 1
                assert "identical" in reason.lower() or "pattern" in reason.lower()
            elif is_valid:
                await anti_abuse_validator.record_action(
                    user_id=user_id,
                    action_type=action_type,
                    context=identical_context,
                )

        # Should detect suspicious patterns
        assert (
            violations_detected > 0
        ), "Pattern detection failed for identical contexts"

    @pytest.mark.asyncio
    async def test_rapid_fire_pattern_detection(self, anti_abuse_validator):
        """Test detection of rapid-fire submission patterns."""
        user_id = 123
        action_type = ActionType.MESSAGE_SENT

        # Submit requests too rapidly (< 100ms apart)
        rapid_violations = 0
        for i in range(15):
            start_time = time.time()

            is_valid, violation, reason = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context={"message": f"rapid_msg_{i}", "timestamp": start_time},
            )

            if not is_valid and violation == AntiAbuseViolation.SUSPICIOUS_PATTERN:
                rapid_violations += 1
                assert "rapid" in reason.lower() or "fast" in reason.lower()
            elif is_valid:
                await anti_abuse_validator.record_action(
                    user_id=user_id,
                    action_type=action_type,
                    context={"message": f"rapid_msg_{i}", "timestamp": start_time},
                )

            # Minimal delay to trigger rapid-fire detection
            await asyncio.sleep(0.01)  # 10ms - should trigger rapid-fire detection

        # Should detect rapid-fire patterns
        assert rapid_violations > 0, "Rapid-fire pattern detection failed"

    @pytest.mark.asyncio
    async def test_impossible_completion_time_detection(self, anti_abuse_validator):
        """Test detection of impossible completion times."""
        user_id = 123
        action_type = ActionType.TRIVIA_COMPLETED

        # Submit with impossible completion time
        impossible_context = {
            "question_id": "hard_question_123",
            "correct_answer": True,
            "completion_time": 0.1,  # 100ms - impossible for complex question
            "difficulty": "hard",
        }

        is_valid, violation, reason = await anti_abuse_validator.validate_action(
            user_id=user_id,
            action_type=action_type,
            context=impossible_context,
        )

        # Should detect impossible completion time
        assert not is_valid, "Failed to detect impossible completion time"
        assert violation == AntiAbuseViolation.SUSPICIOUS_PATTERN
        assert "completion time" in reason.lower() or "impossible" in reason.lower()

    @pytest.mark.asyncio
    async def test_legitimate_patterns_not_flagged(self, anti_abuse_validator):
        """Test that legitimate usage patterns are not flagged."""
        user_id = 123

        # Simulate legitimate user behavior
        legitimate_actions = [
            (ActionType.DAILY_LOGIN, {"login_time": "2024-01-01T08:00:00Z"}),
            (ActionType.MESSAGE_SENT, {"message": "Hello Diana!"}),
            (
                ActionType.TRIVIA_COMPLETED,
                {"question_id": "q1", "correct_answer": True, "completion_time": 15},
            ),
            (ActionType.MESSAGE_SENT, {"message": "That was fun!"}),
            (
                ActionType.TRIVIA_COMPLETED,
                {"question_id": "q2", "correct_answer": False, "completion_time": 30},
            ),
        ]

        for action_type, context in legitimate_actions:
            is_valid, violation, reason = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context=context,
            )

            assert (
                is_valid
            ), f"Legitimate action flagged as suspicious: {action_type} - {reason}"

            # Record successful action
            await anti_abuse_validator.record_action(
                user_id=user_id,
                action_type=action_type,
                context=context,
                points_awarded=10,
            )

            # Add realistic delay between actions
            await asyncio.sleep(0.5)


class TestAntiAbuseViolationHandling:
    """Test violation handling and penalty systems."""

    @pytest_asyncio.fixture
    async def anti_abuse_validator(self):
        """Create AntiAbuseValidator for violation testing."""
        validator = AntiAbuseValidator()
        return validator

    @pytest.mark.asyncio
    async def test_escalating_penalties(self, anti_abuse_validator):
        """Test that penalties escalate with repeated violations."""
        user_id = 123
        action_type = ActionType.MESSAGE_SENT

        # First violation - should get warning
        await anti_abuse_validator.record_violation(
            user_id=user_id,
            violation_type=AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
            action_type=action_type,
            details={"reason": "First violation"},
        )

        penalty1 = await anti_abuse_validator.get_current_penalty(user_id)

        # Second violation - should get stronger penalty
        await anti_abuse_validator.record_violation(
            user_id=user_id,
            violation_type=AntiAbuseViolation.SUSPICIOUS_PATTERN,
            action_type=action_type,
            details={"reason": "Second violation"},
        )

        penalty2 = await anti_abuse_validator.get_current_penalty(user_id)

        # Third violation - should get even stronger penalty
        await anti_abuse_validator.record_violation(
            user_id=user_id,
            violation_type=AntiAbuseViolation.RATE_LIMIT_EXCEEDED,
            action_type=action_type,
            details={"reason": "Third violation"},
        )

        penalty3 = await anti_abuse_validator.get_current_penalty(user_id)

        # Penalties should escalate
        assert penalty2["severity"] > penalty1["severity"], "Penalties should escalate"
        assert (
            penalty3["severity"] > penalty2["severity"]
        ), "Penalties should continue escalating"

    @pytest.mark.asyncio
    async def test_temporary_suspension_enforcement(self, anti_abuse_validator):
        """Test temporary suspension prevents all actions."""
        user_id = 123

        # Apply temporary suspension
        await anti_abuse_validator.apply_temporary_suspension(
            user_id=user_id,
            duration_minutes=60,
            reason="Repeated violations",
        )

        # All actions should be blocked during suspension
        action_types = [
            ActionType.MESSAGE_SENT,
            ActionType.TRIVIA_COMPLETED,
            ActionType.DAILY_LOGIN,
        ]

        for action_type in action_types:
            is_valid, violation, reason = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context={},
            )

            assert not is_valid, f"Suspended user action allowed: {action_type}"
            assert violation == AntiAbuseViolation.ACCOUNT_SUSPENDED
            assert "suspended" in reason.lower()

    @pytest.mark.asyncio
    async def test_suspension_expiry(self, anti_abuse_validator):
        """Test that suspensions expire correctly."""
        user_id = 123

        # Apply short suspension
        await anti_abuse_validator.apply_temporary_suspension(
            user_id=user_id,
            duration_minutes=1,  # 1 minute
            reason="Test suspension",
        )

        # Should be suspended initially
        is_valid, violation, _ = await anti_abuse_validator.validate_action(
            user_id=user_id,
            action_type=ActionType.MESSAGE_SENT,
            context={"message": "test"},
        )
        assert not is_valid
        assert violation == AntiAbuseViolation.ACCOUNT_SUSPENDED

        # Mock time advancement
        with patch(
            "services.gamification.engines.anti_abuse_validator.datetime"
        ) as mock_datetime:
            future_time = datetime.now(timezone.utc) + timedelta(minutes=2)
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Should be allowed after suspension expires
            is_valid, violation, _ = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=ActionType.MESSAGE_SENT,
                context={"message": "after_suspension"},
            )
            assert is_valid, "Actions should be allowed after suspension expires"

    @pytest.mark.asyncio
    async def test_violation_history_tracking(self, anti_abuse_validator):
        """Test that violation history is properly tracked."""
        user_id = 123

        # Record multiple violations
        violations = [
            (AntiAbuseViolation.RATE_LIMIT_EXCEEDED, ActionType.MESSAGE_SENT),
            (AntiAbuseViolation.SUSPICIOUS_PATTERN, ActionType.TRIVIA_COMPLETED),
            (AntiAbuseViolation.RATE_LIMIT_EXCEEDED, ActionType.MESSAGE_SENT),
        ]

        for violation_type, action_type in violations:
            await anti_abuse_validator.record_violation(
                user_id=user_id,
                violation_type=violation_type,
                action_type=action_type,
                details={"test": "violation"},
            )

        # Get violation history
        history = await anti_abuse_validator.get_violation_history(user_id)

        assert len(history) == 3, "Should track all violations"
        assert (
            history[0]["violation_type"] == violations[-1][0].value
        ), "Most recent first"

        # Check violation counts
        stats = await anti_abuse_validator.get_user_violation_stats(user_id)
        assert stats["total_violations"] == 3
        assert stats["rate_limit_violations"] == 2
        assert stats["pattern_violations"] == 1


class TestAntiAbuseEdgeCases:
    """Test edge cases and error conditions."""

    @pytest_asyncio.fixture
    async def anti_abuse_validator(self):
        """Create AntiAbuseValidator for edge case testing."""
        validator = AntiAbuseValidator()
        return validator

    @pytest.mark.asyncio
    async def test_concurrent_validation_requests(self, anti_abuse_validator):
        """Test concurrent validation requests don't create race conditions."""
        user_id = 123
        action_type = ActionType.MESSAGE_SENT

        # Create many concurrent validation requests
        async def validate_task(i):
            return await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context={"message": f"concurrent_msg_{i}"},
            )

        tasks = [validate_task(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All validations should complete without exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent validations failed: {exceptions}"

        # Results should be consistent
        valid_results = [r for r in results if r[0]]  # is_valid == True
        invalid_results = [r for r in results if not r[0]]  # is_valid == False

        # Should have some valid and potentially some invalid due to rate limiting
        total_results = len(valid_results) + len(invalid_results)
        assert total_results == 50, "All requests should return results"

    @pytest.mark.asyncio
    async def test_malformed_context_handling(self, anti_abuse_validator):
        """Test handling of malformed or missing context data."""
        user_id = 123
        action_type = ActionType.TRIVIA_COMPLETED

        # Test various malformed contexts
        malformed_contexts = [
            None,
            {},
            {"invalid": "data"},
            {"question_id": None},
            {"completion_time": "not_a_number"},
            {"completion_time": -5},  # Negative time
        ]

        for context in malformed_contexts:
            is_valid, violation, reason = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context=context,
            )

            # Should handle gracefully (either allow or reject with proper reason)
            assert isinstance(is_valid, bool), "Should return boolean result"
            if not is_valid:
                assert violation is not None, "Should provide violation reason"
                assert isinstance(reason, str), "Should provide string reason"

    @pytest.mark.asyncio
    async def test_extreme_user_ids(self, anti_abuse_validator):
        """Test handling of extreme user ID values."""
        action_type = ActionType.MESSAGE_SENT
        context = {"message": "test"}

        extreme_user_ids = [
            0,
            -1,
            999999999999,  # Very large ID
            None,
        ]

        for user_id in extreme_user_ids:
            try:
                is_valid, violation, reason = (
                    await anti_abuse_validator.validate_action(
                        user_id=user_id,
                        action_type=action_type,
                        context=context,
                    )
                )

                # Should handle gracefully
                assert isinstance(is_valid, bool)

            except (ValueError, TypeError) as e:
                # Acceptable to raise validation errors for invalid IDs
                assert user_id in [
                    None,
                    -1,
                ], f"Unexpected error for user_id {user_id}: {e}"

    @pytest.mark.asyncio
    async def test_system_clock_manipulation_resistance(self, anti_abuse_validator):
        """Test resistance to system clock manipulation attempts."""
        user_id = 123
        action_type = ActionType.MESSAGE_SENT

        # Record some actions normally
        for i in range(3):
            await anti_abuse_validator.record_action(
                user_id=user_id,
                action_type=action_type,
                context={"message": f"msg_{i}"},
            )

        # Mock time going backwards (clock manipulation attempt)
        with patch(
            "services.gamification.engines.anti_abuse_validator.datetime"
        ) as mock_datetime:
            past_time = datetime.now(timezone.utc) - timedelta(hours=1)
            mock_datetime.now.return_value = past_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Should detect and handle clock manipulation
            is_valid, violation, reason = await anti_abuse_validator.validate_action(
                user_id=user_id,
                action_type=action_type,
                context={"message": "time_manipulation"},
            )

            # Should either allow (system is robust) or flag as suspicious
            if not is_valid:
                assert violation in [
                    AntiAbuseViolation.SUSPICIOUS_PATTERN,
                    AntiAbuseViolation.SYSTEM_ANOMALY,
                ], "Should detect clock manipulation"
