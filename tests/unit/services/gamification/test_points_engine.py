"""
Unit tests for the Points Engine.

Tests all points calculations, anti-abuse logic, multipliers,
and transaction validation with comprehensive coverage.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.models.gamification import PointsTransactionType, UserGamification
from src.services.gamification.engines.points_engine import PointsEngine
from src.services.gamification.interfaces import AntiAbuseError, InsufficientPointsError


@pytest.fixture
def points_config():
    """Test configuration for points engine."""
    return {
        "points": {
            "daily_login": 50,
            "story_complete": 500,
            "decision_made": 25,
        },
        "vip_multipliers": {
            "standard": 1.5,
            "premium": 2.0,
        },
        "streak_multipliers": {
            "1-7": 1.1,
            "8-14": 1.2,
            "15-30": 1.3,
            "31+": 1.5,
        },
        "anti_abuse": {
            "max_points_per_hour": 1000,
            "max_actions_per_minute": 10,
            "suspicious_threshold": 5000,
        },
        "level_progression": [0, 100, 300, 600, 1000],
    }


@pytest.fixture
def points_engine(points_config):
    """Create a points engine instance for testing."""
    return PointsEngine(points_config)


@pytest.fixture
def mock_user():
    """Create a mock user gamification object."""
    user = MagicMock(spec=UserGamification)
    user.user_id = 123
    user.total_points = 1000
    user.current_level = 5
    user.vip_status = False
    user.vip_multiplier = 1.0
    return user


@pytest.fixture
def mock_vip_user():
    """Create a mock VIP user gamification object."""
    user = MagicMock(spec=UserGamification)
    user.user_id = 456
    user.total_points = 2000
    user.current_level = 10
    user.vip_status = True
    user.vip_multiplier = 1.5
    return user


class TestPointsCalculation:
    """Test points calculation logic."""

    def test_basic_points_calculation(self, points_engine, mock_user):
        """Test basic points calculation without bonuses."""
        final_points, details = points_engine.calculate_points_award(
            mock_user, 100, "test_action"
        )

        assert final_points == 110  # 100 base + 10 level bonus (level 5 * 2)
        assert details["base_points"] == 100
        assert details["level_bonus"] == 10
        assert details["final_points"] == 110

    def test_vip_multiplier_calculation(self, points_engine, mock_vip_user):
        """Test VIP multiplier is applied correctly."""
        final_points, details = points_engine.calculate_points_award(
            mock_vip_user, 100, "test_action"
        )

        # 100 * 1.5 (VIP) = 150, + 20 level bonus (level 10 * 2)
        assert final_points == 170
        assert details["vip_multiplier"] == 1.5
        assert details["level_bonus"] == 20

    def test_streak_multiplier_calculation(self, points_engine, mock_user):
        """Test streak multiplier is applied correctly."""
        final_points, details = points_engine.calculate_points_award(
            mock_user, 100, "test_action", streak_multiplier=1.2
        )

        # 100 * 1.2 (streak) = 120, + 10 level bonus
        assert final_points == 130
        assert details["streak_multiplier"] == 1.2

    def test_bonus_points_calculation(self, points_engine, mock_user):
        """Test bonus points are added correctly."""
        final_points, details = points_engine.calculate_points_award(
            mock_user, 100, "test_action", bonus_points=50
        )

        # 100 base + 10 level bonus + 50 bonus = 160
        assert final_points == 160
        assert details["bonus_points"] == 50
        assert details["total_bonus"] == 60  # 50 bonus + 10 level

    def test_combined_multipliers(self, points_engine, mock_vip_user):
        """Test that all multipliers combine correctly."""
        final_points, details = points_engine.calculate_points_award(
            mock_vip_user,
            100,
            "test_action",
            multiplier=1.1,
            bonus_points=25,
            streak_multiplier=1.3,
        )

        # 100 * 1.1 * 1.5 (VIP) * 1.3 (streak) = 214.5 -> 214
        # + 25 bonus + 20 level bonus = 259
        assert final_points == 259
        assert details["final_multiplier"] == pytest.approx(2.145, rel=1e-3)

    def test_level_bonus_cap(self, points_engine):
        """Test that level bonus is capped at 50 points."""
        high_level_user = MagicMock(spec=UserGamification)
        high_level_user.current_level = 50  # Would give 100 bonus, but cap is 50
        high_level_user.vip_status = False
        high_level_user.vip_multiplier = 1.0

        final_points, details = points_engine.calculate_points_award(
            high_level_user, 100, "test_action"
        )

        assert details["level_bonus"] == 50  # Capped at 50
        assert final_points == 150  # 100 + 50

    def test_invalid_base_points(self, points_engine, mock_user):
        """Test that invalid base points raise ValueError."""
        with pytest.raises(ValueError, match="Base points must be positive"):
            points_engine.calculate_points_award(mock_user, -10, "test_action")

        with pytest.raises(ValueError, match="Base points must be positive"):
            points_engine.calculate_points_award(mock_user, 0, "test_action")


class TestAntiAbuseLogic:
    """Test anti-abuse validation logic."""

    def test_normal_transaction_passes(self, points_engine):
        """Test that normal transactions pass validation."""
        # Should not raise any exception
        points_engine.validate_points_transaction(
            123, 100, "daily_login", PointsTransactionType.EARNED
        )

    def test_admin_adjustments_skip_validation(self, points_engine):
        """Test that admin adjustments skip anti-abuse validation."""
        # Should not raise even with suspicious amounts
        points_engine.validate_points_transaction(
            123, 10000, "admin_adjustment", PointsTransactionType.ADMIN_ADJUSTMENT
        )

    def test_penalties_skip_validation(self, points_engine):
        """Test that penalties skip anti-abuse validation."""
        points_engine.validate_points_transaction(
            123, 5000, "penalty", PointsTransactionType.PENALTY
        )

    def test_rate_limit_enforcement(self, points_engine):
        """Test that rate limiting is enforced."""
        user_id = 123

        # Perform max allowed actions
        for i in range(10):  # max_actions_per_minute = 10
            points_engine.validate_points_transaction(
                user_id, 10, "test_action", PointsTransactionType.EARNED
            )

        # 11th action should trigger rate limit
        with pytest.raises(AntiAbuseError, match="exceeded action rate limit"):
            points_engine.validate_points_transaction(
                user_id, 10, "test_action", PointsTransactionType.EARNED
            )

    def test_hourly_points_limit(self, points_engine):
        """Test that hourly points limit is enforced."""
        user_id = 456

        # Test large single transaction
        with pytest.raises(AntiAbuseError, match="exceeded hourly points limit"):
            points_engine.validate_points_transaction(
                user_id, 1500, "test_action", PointsTransactionType.EARNED
            )

    def test_suspicious_threshold_marking(self, points_engine):
        """Test that suspicious amounts mark users as suspicious."""
        user_id = 789

        # This should mark user as suspicious but not fail
        points_engine.validate_points_transaction(
            user_id, 6000, "test_action", PointsTransactionType.EARNED
        )

        # Check that user is marked as suspicious
        status = points_engine.get_anti_abuse_status(user_id)
        assert status["is_suspicious"] is True

    def test_rapid_actions_detection(self, points_engine):
        """Test detection of rapid repeated actions."""
        user_id = 999

        # Simulate rapid actions (5 actions in quick succession)
        # This will trigger suspicious pattern detection
        for i in range(5):
            points_engine.validate_points_transaction(
                user_id, 10, "test_action", PointsTransactionType.EARNED
            )

        # User should be marked as suspicious
        status = points_engine.get_anti_abuse_status(user_id)
        assert status["is_suspicious"] is True


class TestPointsDeductionValidation:
    """Test points deduction validation logic."""

    def test_valid_deduction(self, points_engine, mock_user):
        """Test that valid deductions pass validation."""
        # Should not raise any exception
        points_engine.validate_points_deduction(mock_user, 500)

    def test_insufficient_points_error(self, points_engine, mock_user):
        """Test that insufficient points raises error."""
        with pytest.raises(InsufficientPointsError):
            points_engine.validate_points_deduction(mock_user, 1500)  # User has 1000

    def test_allow_negative_balance(self, points_engine, mock_user):
        """Test that negative balance can be allowed."""
        # Should not raise with allow_negative=True
        points_engine.validate_points_deduction(mock_user, 1500, allow_negative=True)

    def test_invalid_deduction_amount(self, points_engine, mock_user):
        """Test that invalid deduction amounts raise ValueError."""
        with pytest.raises(ValueError, match="Points amount must be positive"):
            points_engine.validate_points_deduction(mock_user, -10)

        with pytest.raises(ValueError, match="Points amount must be positive"):
            points_engine.validate_points_deduction(mock_user, 0)


class TestTransactionDataCreation:
    """Test transaction data creation logic."""

    def test_basic_transaction_data(self, points_engine):
        """Test basic transaction data creation."""
        transaction_data = points_engine.create_transaction_data(
            user_id=123,
            transaction_type=PointsTransactionType.EARNED,
            amount=100,
            points_before=500,
            points_after=600,
            action_type="test_action",
            description="Test transaction",
        )

        assert transaction_data["user_id"] == 123
        assert transaction_data["transaction_type"] == PointsTransactionType.EARNED
        assert transaction_data["amount"] == 100
        assert transaction_data["points_before"] == 500
        assert transaction_data["points_after"] == 600
        assert transaction_data["action_type"] == "test_action"
        assert transaction_data["description"] == "Test transaction"
        assert transaction_data["source_service"] == "gamification"

    def test_transaction_data_with_calculation_details(self, points_engine):
        """Test transaction data with calculation details."""
        calculation_details = {
            "base_points": 100,
            "final_multiplier": 1.5,
            "total_bonus": 25,
        }

        transaction_data = points_engine.create_transaction_data(
            user_id=123,
            transaction_type=PointsTransactionType.EARNED,
            amount=150,
            points_before=500,
            points_after=650,
            action_type="test_action",
            description="Test transaction",
            calculation_details=calculation_details,
        )

        assert transaction_data["multiplier_applied"] == 1.5
        assert transaction_data["bonus_applied"] == 25
        assert (
            transaction_data["transaction_metadata"]["calculation"]
            == calculation_details
        )

    def test_transaction_data_includes_anti_abuse_info(self, points_engine):
        """Test that transaction data includes anti-abuse information."""
        # Mark user as suspicious first
        points_engine._suspicious_users.add(456)

        transaction_data = points_engine.create_transaction_data(
            user_id=456,
            transaction_type=PointsTransactionType.EARNED,
            amount=100,
            points_before=500,
            points_after=600,
            action_type="test_action",
            description="Test transaction",
        )

        assert transaction_data["is_suspicious"] is True
        assert "validation_timestamp" in transaction_data["transaction_metadata"]


class TestLevelCalculation:
    """Test level calculation logic."""

    def test_level_calculation_from_experience(self, points_engine):
        """Test level calculation from experience points."""
        # level_progression = [0, 100, 300, 600, 1000]
        assert points_engine.calculate_level_from_experience(0) == 1
        assert points_engine.calculate_level_from_experience(50) == 1
        assert points_engine.calculate_level_from_experience(100) == 2
        assert points_engine.calculate_level_from_experience(250) == 2
        assert points_engine.calculate_level_from_experience(300) == 3
        assert points_engine.calculate_level_from_experience(500) == 3
        assert points_engine.calculate_level_from_experience(600) == 4
        assert points_engine.calculate_level_from_experience(800) == 4
        assert points_engine.calculate_level_from_experience(1000) == 5
        assert points_engine.calculate_level_from_experience(1500) == 5  # Max level

    def test_experience_for_next_level(self, points_engine):
        """Test getting experience required for next level."""
        assert points_engine.get_experience_for_next_level(1) == 100
        assert points_engine.get_experience_for_next_level(2) == 300
        assert points_engine.get_experience_for_next_level(3) == 600
        assert points_engine.get_experience_for_next_level(4) == 1000
        assert points_engine.get_experience_for_next_level(5) is None  # Max level


class TestPointsForAction:
    """Test getting points for specific actions."""

    def test_configured_action_points(self, points_engine):
        """Test getting points for configured actions."""
        assert points_engine.get_points_for_action("daily_login") == 50
        assert points_engine.get_points_for_action("story_complete") == 500
        assert points_engine.get_points_for_action("decision_made") == 25

    def test_unconfigured_action_points(self, points_engine):
        """Test getting points for unconfigured actions returns 0."""
        assert points_engine.get_points_for_action("unknown_action") == 0


class TestAntiAbuseStatus:
    """Test anti-abuse status reporting."""

    def test_clean_user_status(self, points_engine):
        """Test status for a clean user."""
        status = points_engine.get_anti_abuse_status(123)

        assert status["is_suspicious"] is False
        assert status["actions_last_minute"] == 0
        assert status["actions_last_hour"] == 0
        assert status["points_current_hour"] == 0
        assert status["total_tracked_actions"] == 0

    def test_active_user_status(self, points_engine):
        """Test status for an active user."""
        user_id = 456

        # Perform some actions
        for i in range(3):
            points_engine.validate_points_transaction(
                user_id, 10, "test_action", PointsTransactionType.EARNED
            )

        status = points_engine.get_anti_abuse_status(user_id)

        assert status["actions_last_minute"] == 3
        assert status["actions_last_hour"] == 3
        assert status["total_tracked_actions"] == 3

    def test_reset_anti_abuse_tracking(self, points_engine):
        """Test resetting anti-abuse tracking for a user."""
        user_id = 789

        # Perform actions and mark as suspicious
        points_engine.validate_points_transaction(
            user_id, 10, "test_action", PointsTransactionType.EARNED
        )
        points_engine._suspicious_users.add(user_id)

        # Verify tracking exists
        status = points_engine.get_anti_abuse_status(user_id)
        assert status["is_suspicious"] is True
        assert status["total_tracked_actions"] > 0

        # Reset tracking
        points_engine.reset_anti_abuse_tracking(user_id)

        # Verify reset
        status_after = points_engine.get_anti_abuse_status(user_id)
        assert status_after["is_suspicious"] is False
        assert status_after["total_tracked_actions"] == 0
