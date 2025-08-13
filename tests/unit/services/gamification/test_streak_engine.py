"""
Unit tests for the Streak Engine.

Tests all streak calculations, milestone detection, multiplier logic,
and VIP features like streak freezes.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.models.gamification import StreakRecord, StreakType, UserGamification
from src.services.gamification.engines.streak_engine import StreakEngine


@pytest.fixture
def streak_config():
    """Test configuration for streak engine."""
    return {
        "streak_multipliers": {
            "1-7": 1.1,
            "8-14": 1.2,
            "15-30": 1.3,
            "31+": 1.5,
        },
        "streak_milestones": {
            StreakType.DAILY_LOGIN: [7, 30, 100, 365],
            StreakType.STORY_PROGRESS: [5, 15, 30, 60],
            StreakType.INTERACTION: [10, 25, 50, 100],
            StreakType.ACHIEVEMENT_UNLOCK: [3, 10, 20, 50],
        },
        "vip_features": {
            "max_freezes_per_month": 3,
            "min_streak_for_freeze": 7,
        },
    }


@pytest.fixture
def streak_engine(streak_config):
    """Create a streak engine instance for testing."""
    return StreakEngine(streak_config)


@pytest.fixture
def mock_user():
    """Create a mock user gamification object."""
    user = MagicMock(spec=UserGamification)
    user.user_id = 123
    user.vip_status = False
    user.vip_multiplier = 1.0
    return user


@pytest.fixture
def mock_vip_user():
    """Create a mock VIP user gamification object."""
    user = MagicMock(spec=UserGamification)
    user.user_id = 456
    user.vip_status = True
    user.vip_multiplier = 1.5
    return user


@pytest.fixture
def mock_existing_streak():
    """Create a mock existing streak record."""
    streak = MagicMock(spec=StreakRecord)
    streak.user_id = 123
    streak.streak_type = StreakType.DAILY_LOGIN
    streak.current_count = 5
    streak.longest_count = 10
    streak.last_activity_date = datetime.now(timezone.utc) - timedelta(hours=12)
    streak.streak_start_date = datetime.now(timezone.utc) - timedelta(days=5)
    streak.last_reset_date = None
    streak.current_multiplier = 1.1
    streak.milestones_reached = []
    streak.is_active = True
    streak.freeze_count = 0
    return streak


class TestStreakUpdate:
    """Test streak update logic."""

    def test_new_streak_creation(self, streak_engine):
        """Test creating a new streak from scratch."""
        now = datetime.now(timezone.utc)

        streak_data, milestone_reached = streak_engine.update_streak(
            user_id=123,
            streak_type=StreakType.DAILY_LOGIN,
            existing_streak=None,
            activity_date=now,
        )

        assert streak_data["user_id"] == 123
        assert streak_data["streak_type"] == StreakType.DAILY_LOGIN
        assert streak_data["current_count"] == 1
        assert streak_data["longest_count"] == 1
        assert streak_data["last_activity_date"] == now
        assert streak_data["streak_start_date"] == now
        assert streak_data["is_active"] is True
        assert milestone_reached is False  # First day usually isn't a milestone

    def test_streak_continuation(self, streak_engine, mock_existing_streak):
        """Test continuing an existing streak within grace period."""
        now = datetime.now(timezone.utc)
        # Last activity was 12 hours ago, within grace period for daily login

        streak_data, milestone_reached = streak_engine.update_streak(
            user_id=123,
            streak_type=StreakType.DAILY_LOGIN,
            existing_streak=mock_existing_streak,
            activity_date=now,
        )

        assert streak_data["current_count"] == 6  # 5 + 1
        assert streak_data["longest_count"] == 10  # Unchanged (6 < 10)
        assert streak_data["last_activity_date"] == now

    def test_streak_milestone_reached(self, streak_engine, mock_existing_streak):
        """Test detecting when a milestone is reached."""
        # Set up streak to reach milestone at 7 days
        mock_existing_streak.current_count = 6
        now = datetime.now(timezone.utc)

        streak_data, milestone_reached = streak_engine.update_streak(
            user_id=123,
            streak_type=StreakType.DAILY_LOGIN,
            existing_streak=mock_existing_streak,
            activity_date=now,
        )

        assert streak_data["current_count"] == 7
        assert milestone_reached is True  # 7 is a milestone for daily login

    def test_streak_reset_after_grace_period(self, streak_engine, mock_existing_streak):
        """Test streak reset when activity is beyond grace period."""
        # Set last activity to 3 days ago (beyond grace period)
        mock_existing_streak.last_activity_date = datetime.now(
            timezone.utc
        ) - timedelta(days=3)
        now = datetime.now(timezone.utc)

        streak_data, milestone_reached = streak_engine.update_streak(
            user_id=123,
            streak_type=StreakType.DAILY_LOGIN,
            existing_streak=mock_existing_streak,
            activity_date=now,
        )

        assert streak_data["current_count"] == 1  # Reset to 1
        assert streak_data["longest_count"] == 10  # Preserved from before
        assert streak_data["last_reset_date"] == now

    def test_longest_count_update(self, streak_engine, mock_existing_streak):
        """Test that longest count is updated when current exceeds it."""
        mock_existing_streak.current_count = 10
        mock_existing_streak.longest_count = 8  # Current will exceed this
        now = datetime.now(timezone.utc)

        streak_data, milestone_reached = streak_engine.update_streak(
            user_id=123,
            streak_type=StreakType.DAILY_LOGIN,
            existing_streak=mock_existing_streak,
            activity_date=now,
        )

        assert streak_data["current_count"] == 11
        assert streak_data["longest_count"] == 11  # Updated to match current

    def test_future_activity_date_rejected(self, streak_engine):
        """Test that future activity dates are rejected."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)

        with pytest.raises(ValueError, match="Activity date cannot be in the future"):
            streak_engine.update_streak(
                user_id=123,
                streak_type=StreakType.DAILY_LOGIN,
                activity_date=future_date,
            )

    def test_old_activity_date_rejected(self, streak_engine):
        """Test that very old activity dates are rejected."""
        old_date = datetime.now(timezone.utc) - timedelta(days=10)

        with pytest.raises(ValueError, match="Activity date is too old"):
            streak_engine.update_streak(
                user_id=123, streak_type=StreakType.DAILY_LOGIN, activity_date=old_date
            )

    def test_backdate_allowed_with_flag(self, streak_engine):
        """Test that backdating is allowed when flag is set."""
        old_date = datetime.now(timezone.utc) - timedelta(days=10)

        # Should not raise with allow_backdate=True
        streak_data, milestone_reached = streak_engine.update_streak(
            user_id=123,
            streak_type=StreakType.DAILY_LOGIN,
            activity_date=old_date,
            allow_backdate=True,
        )

        assert streak_data["last_activity_date"] == old_date


class TestStreakMultipliers:
    """Test streak multiplier calculations."""

    def test_base_multipliers(self, streak_engine, mock_user):
        """Test basic multiplier calculation based on streak count."""
        # Test different streak lengths
        assert (
            streak_engine.calculate_streak_multiplier(
                StreakType.DAILY_LOGIN, 5, mock_user
            )
            == 1.1
        )  # 1-7 range
        assert (
            streak_engine.calculate_streak_multiplier(
                StreakType.DAILY_LOGIN, 10, mock_user
            )
            == 1.2
        )  # 8-14 range
        assert (
            streak_engine.calculate_streak_multiplier(
                StreakType.DAILY_LOGIN, 20, mock_user
            )
            == 1.3
        )  # 15-30 range
        assert (
            streak_engine.calculate_streak_multiplier(
                StreakType.DAILY_LOGIN, 50, mock_user
            )
            == 1.5
        )  # 31+ range

    def test_vip_bonus_multiplier(self, streak_engine, mock_vip_user):
        """Test that VIP users get bonus multiplier."""
        multiplier = streak_engine.calculate_streak_multiplier(
            StreakType.DAILY_LOGIN, 5, mock_vip_user
        )

        # Base 1.1 + VIP bonus 0.1 = 1.2
        assert multiplier == 1.2

    def test_streak_type_specific_bonuses(self, streak_engine, mock_user):
        """Test that different streak types have different bonuses."""
        # Story progress streaks should get higher bonuses
        story_multiplier = streak_engine.calculate_streak_multiplier(
            StreakType.STORY_PROGRESS, 15, mock_user
        )
        login_multiplier = streak_engine.calculate_streak_multiplier(
            StreakType.DAILY_LOGIN, 15, mock_user
        )

        # Story progress should have additional bonus
        assert story_multiplier > login_multiplier

    def test_zero_streak_multiplier(self, streak_engine, mock_user):
        """Test multiplier for zero streak count."""
        multiplier = streak_engine.calculate_streak_multiplier(
            StreakType.DAILY_LOGIN, 0, mock_user
        )
        assert multiplier == 1.0

    def test_combined_bonuses(self, streak_engine, mock_vip_user):
        """Test that all bonuses combine correctly."""
        # Long story streak for VIP user should get all bonuses
        multiplier = streak_engine.calculate_streak_multiplier(
            StreakType.STORY_PROGRESS, 15, mock_vip_user
        )

        # Base 1.3 + VIP 0.1 + Story type bonus 0.1 = 1.5
        assert multiplier == 1.5


class TestMilestoneDetection:
    """Test milestone detection logic."""

    def test_milestone_reached(self, streak_engine):
        """Test detecting when milestones are reached."""
        milestones = streak_engine.check_streak_milestones(StreakType.DAILY_LOGIN, 6, 7)
        assert 7 in milestones

        milestones = streak_engine.check_streak_milestones(
            StreakType.DAILY_LOGIN, 29, 30
        )
        assert 30 in milestones

    def test_multiple_milestones_reached(self, streak_engine):
        """Test when multiple milestones are reached in one jump."""
        # Jump from 5 to 35 (skipping 7 and 30)
        milestones = streak_engine.check_streak_milestones(
            StreakType.DAILY_LOGIN, 5, 35
        )
        assert 7 in milestones
        assert 30 in milestones
        assert len(milestones) == 2

    def test_no_milestones_reached(self, streak_engine):
        """Test when no milestones are reached."""
        milestones = streak_engine.check_streak_milestones(StreakType.DAILY_LOGIN, 5, 6)
        assert len(milestones) == 0

    def test_backwards_milestone_check(self, streak_engine):
        """Test that backwards progress doesn't trigger milestones."""
        milestones = streak_engine.check_streak_milestones(
            StreakType.DAILY_LOGIN, 10, 8
        )
        assert len(milestones) == 0


class TestStreakFreeze:
    """Test VIP streak freeze functionality."""

    def test_vip_can_use_freeze(
        self, streak_engine, mock_vip_user, mock_existing_streak
    ):
        """Test that VIP users can use streak freeze."""
        mock_existing_streak.current_count = 10  # Above minimum
        mock_existing_streak.freeze_count = 0  # Under limit

        can_freeze, reason = streak_engine.can_use_streak_freeze(
            mock_vip_user, mock_existing_streak
        )

        assert can_freeze is True
        assert reason == "Freeze available"

    def test_non_vip_cannot_use_freeze(
        self, streak_engine, mock_user, mock_existing_streak
    ):
        """Test that non-VIP users cannot use streak freeze."""
        can_freeze, reason = streak_engine.can_use_streak_freeze(
            mock_user, mock_existing_streak
        )

        assert can_freeze is False
        assert "only available for VIP users" in reason

    def test_freeze_limit_enforced(
        self, streak_engine, mock_vip_user, mock_existing_streak
    ):
        """Test that freeze usage limit is enforced."""
        mock_existing_streak.current_count = 10
        mock_existing_streak.freeze_count = 3  # At limit

        can_freeze, reason = streak_engine.can_use_streak_freeze(
            mock_vip_user, mock_existing_streak
        )

        assert can_freeze is False
        assert "Maximum freezes per month reached" in reason

    def test_minimum_streak_for_freeze(
        self, streak_engine, mock_vip_user, mock_existing_streak
    ):
        """Test minimum streak length requirement for freeze."""
        mock_existing_streak.current_count = 5  # Below minimum of 7
        mock_existing_streak.freeze_count = 0

        can_freeze, reason = streak_engine.can_use_streak_freeze(
            mock_vip_user, mock_existing_streak
        )

        assert can_freeze is False
        assert "must be at least 7 days" in reason

    def test_inactive_streak_cannot_freeze(
        self, streak_engine, mock_vip_user, mock_existing_streak
    ):
        """Test that inactive streaks cannot be frozen."""
        mock_existing_streak.is_active = False

        can_freeze, reason = streak_engine.can_use_streak_freeze(
            mock_vip_user, mock_existing_streak
        )

        assert can_freeze is False
        assert "Cannot freeze an inactive streak" in reason

    def test_apply_streak_freeze(self, streak_engine, mock_existing_streak):
        """Test applying a streak freeze."""
        original_activity_date = mock_existing_streak.last_activity_date
        original_freeze_count = mock_existing_streak.freeze_count

        freeze_data = streak_engine.apply_streak_freeze(
            mock_existing_streak, freeze_duration_days=1
        )

        # Should extend last activity date
        expected_date = original_activity_date + timedelta(days=1)
        assert freeze_data["last_activity_date"] == expected_date
        assert freeze_data["freeze_count"] == original_freeze_count + 1
        assert (
            freeze_data["current_count"] == mock_existing_streak.current_count
        )  # Unchanged


class TestStreakStatistics:
    """Test streak statistics calculation."""

    def test_streak_statistics_calculation(self, streak_engine, mock_user):
        """Test comprehensive streak statistics calculation."""
        user_streaks = [
            MagicMock(
                streak_type=StreakType.DAILY_LOGIN,
                current_count=15,
                longest_count=20,
                is_active=True,
                milestones_reached=[7],
            ),
            MagicMock(
                streak_type=StreakType.STORY_PROGRESS,
                current_count=8,
                longest_count=10,
                is_active=True,
                milestones_reached=[5],
            ),
            MagicMock(
                streak_type=StreakType.INTERACTION,
                current_count=0,
                longest_count=25,
                is_active=False,
                milestones_reached=[10, 25],
            ),
        ]

        stats = streak_engine.get_streak_statistics(user_streaks, mock_user)

        assert stats["active_streaks_count"] == 2  # Two active with count > 0
        assert stats["longest_current_streak"] == 15
        assert stats["longest_ever_streak"] == 25
        assert stats["total_streak_days"] == 55  # 20 + 10 + 25
        assert stats["total_milestones_reached"] == 3  # 1 + 1 + 2
        assert stats["vip_freezes_available"] is False

    def test_streak_health_score(self, streak_engine):
        """Test streak health score calculation."""
        # Create strong active streaks
        strong_streaks = [
            MagicMock(
                current_count=50,
                longest_count=60,
                is_active=True,
                current_multiplier=1.5,
                milestones_reached=[7, 30],
            ),
            MagicMock(
                current_count=15,
                longest_count=20,
                is_active=True,
                current_multiplier=1.3,
                milestones_reached=[5, 15],
            ),
        ]

        stats = streak_engine.get_streak_statistics(strong_streaks, mock_user)

        # Should have high health score
        assert stats["streak_health_score"] > 80

    def test_empty_streaks_statistics(self, streak_engine, mock_user):
        """Test statistics with no streaks."""
        stats = streak_engine.get_streak_statistics([], mock_user)

        assert stats["active_streaks_count"] == 0
        assert stats["longest_current_streak"] == 0
        assert stats["longest_ever_streak"] == 0
        assert stats["total_streak_days"] == 0
        assert stats["streak_health_score"] == 0


class TestStreakRecovery:
    """Test streak recovery and suggestions."""

    def test_streak_at_risk_detection(self, streak_engine, mock_user):
        """Test detection of streaks at risk."""
        # Create streaks with different risk levels
        now = datetime.now(timezone.utc)
        risky_streaks = [
            MagicMock(
                streak_type=StreakType.DAILY_LOGIN,
                current_count=10,
                last_activity_date=now - timedelta(hours=30),  # Overdue
                is_active=True,
            ),
            MagicMock(
                streak_type=StreakType.STORY_PROGRESS,
                current_count=5,
                last_activity_date=now - timedelta(hours=1),  # Safe
                is_active=True,
            ),
        ]

        suggestions = streak_engine.get_streak_recovery_suggestions(
            risky_streaks, mock_user
        )

        # Should suggest recovery for overdue streak
        assert len(suggestions) == 1
        assert suggestions[0]["streak_type"] == "daily_login"
        assert suggestions[0]["hours_overdue"] > 0
        assert suggestions[0]["risk_level"] > 1

    def test_vip_freeze_suggestions(self, streak_engine, mock_vip_user):
        """Test that VIP users get freeze suggestions."""
        now = datetime.now(timezone.utc)
        risky_streak = MagicMock(
            streak_type=StreakType.DAILY_LOGIN,
            current_count=10,
            last_activity_date=now - timedelta(hours=30),
            is_active=True,
            freeze_count=0,
        )

        suggestions = streak_engine.get_streak_recovery_suggestions(
            [risky_streak], mock_vip_user
        )

        assert len(suggestions) == 1
        assert suggestions[0]["can_use_freeze"] is True

    def test_action_suggestions(self, streak_engine, mock_user):
        """Test that appropriate actions are suggested."""
        now = datetime.now(timezone.utc)
        story_streak = MagicMock(
            streak_type=StreakType.STORY_PROGRESS,
            current_count=8,
            last_activity_date=now - timedelta(days=3),  # Overdue
            is_active=True,
        )

        suggestions = streak_engine.get_streak_recovery_suggestions(
            [story_streak], mock_user
        )

        assert len(suggestions) == 1
        suggestion = suggestions[0]
        assert "Complete a story chapter" in suggestion["action_needed"]

    def test_risk_level_calculation(self, streak_engine):
        """Test risk level calculation for overdue streaks."""
        grace_period = timedelta(hours=26)  # Daily login grace period

        # Test different overdue amounts
        low_risk = streak_engine._calculate_risk_level(
            timedelta(hours=20), grace_period
        )
        medium_risk = streak_engine._calculate_risk_level(
            timedelta(hours=50), grace_period
        )
        high_risk = streak_engine._calculate_risk_level(
            timedelta(hours=200), grace_period
        )

        assert low_risk == 1
        assert medium_risk > low_risk
        assert high_risk > medium_risk
