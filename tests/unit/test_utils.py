"""Unit tests for Diana Bot utility functions."""

import pytest

from diana_bot.core.utils import (
    calculate_besitos,
    format_leaderboard,
    validate_username,
)


class TestCalculateBesitos:
    """Test calculate_besitos function."""

    def test_calculate_basic_points(self) -> None:
        """Test basic points calculation."""
        result = calculate_besitos(100)
        assert result == 100

    def test_calculate_with_multiplier(self) -> None:
        """Test points calculation with multiplier."""
        result = calculate_besitos(100, 1.5)
        assert result == 150

    def test_calculate_with_zero_points(self) -> None:
        """Test calculation with zero points."""
        result = calculate_besitos(0)
        assert result == 0

    def test_calculate_with_fractional_result(self) -> None:
        """Test calculation that results in fractional points."""
        result = calculate_besitos(10, 1.7)
        assert result == 17  # int(10 * 1.7)

    def test_calculate_negative_points_raises_error(self) -> None:
        """Test that negative points raise ValueError."""
        with pytest.raises(ValueError, match="Base points cannot be negative"):
            calculate_besitos(-10)


class TestValidateUsername:
    """Test validate_username function."""

    def test_valid_username(self) -> None:
        """Test validation of valid username."""
        assert validate_username("@testuser123")

    def test_valid_username_with_underscore(self) -> None:
        """Test validation of username with underscore."""
        assert validate_username("@test_user")

    def test_invalid_empty_username(self) -> None:
        """Test validation of empty username."""
        assert not validate_username("")

    def test_invalid_username_without_at_symbol(self) -> None:
        """Test validation of username without @ symbol."""
        assert not validate_username("testuser")

    def test_invalid_username_too_short(self) -> None:
        """Test validation of username that's too short."""
        assert not validate_username("@test")  # 5 chars total, need at least 6

    def test_invalid_username_too_long(self) -> None:
        """Test validation of username that's too long."""
        long_username = "@" + "a" * 33  # 34 chars total, max is 33
        assert not validate_username(long_username)

    def test_invalid_username_with_special_chars(self) -> None:
        """Test validation of username with invalid characters."""
        assert not validate_username("@test-user")
        assert not validate_username("@test.user")


class TestFormatLeaderboard:
    """Test format_leaderboard function."""

    def test_format_basic_leaderboard(self) -> None:
        """Test basic leaderboard formatting."""
        scores = [("@alice", 150), ("@bob", 100), ("@charlie", 200)]
        result = format_leaderboard(scores)
        expected = (
            "🥇 @charlie: 200 besitos\n🥈 @alice: 150 besitos\n🥉 @bob: 100 besitos"
        )
        assert result == expected

    def test_format_empty_leaderboard(self) -> None:
        """Test formatting of empty leaderboard."""
        result = format_leaderboard([])
        assert result == "No scores available"

    def test_format_single_entry(self) -> None:
        """Test formatting with single entry."""
        scores = [("@alice", 100)]
        result = format_leaderboard(scores)
        assert result == "🥇 @alice: 100 besitos"

    def test_format_with_limit(self) -> None:
        """Test formatting with entry limit."""
        scores = [("@alice", 100), ("@bob", 150), ("@charlie", 200), ("@david", 75)]
        result = format_leaderboard(scores, limit=2)
        expected = "🥇 @charlie: 200 besitos\n🥈 @bob: 150 besitos"
        assert result == expected

    def test_format_more_than_three_entries(self) -> None:
        """Test formatting with more than three entries."""
        scores = [("@alice", 100), ("@bob", 150), ("@charlie", 200), ("@david", 75)]
        result = format_leaderboard(scores)
        lines = result.split("\n")
        assert len(lines) == 4
        assert lines[3] == "4. @david: 75 besitos"

    def test_format_preserves_equal_scores_order(self) -> None:
        """Test that equal scores preserve original order."""
        scores = [("@alice", 100), ("@bob", 100)]
        result = format_leaderboard(scores)
        # Should maintain original order when scores are equal
        lines = result.split("\n")
        assert "@alice" in lines[0]
        assert "@bob" in lines[1]
