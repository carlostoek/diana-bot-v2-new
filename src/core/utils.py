"""Utility functions for Diana Bot."""

from typing import List, Optional


def calculate_besitos(base_points: int, multiplier: float = 1.0) -> int:
    """Calculate besitos (points) with optional multiplier.

    Args:
        base_points: Base points to award
        multiplier: Multiplier for bonus calculations

    Returns:
        Total besitos calculated

    Raises:
        ValueError: If base_points is negative
    """
    if base_points < 0:
        raise ValueError("Base points cannot be negative")

    return int(base_points * multiplier)


def validate_username(username: str) -> bool:
    """Validate a Telegram username.

    Args:
        username: Username to validate

    Returns:
        True if valid, False otherwise
    """
    if not username:
        return False

    if not username.startswith("@"):
        return False

    if len(username) < 6 or len(username) > 33:  # @username format
        return False

    # Remove @ and check characters
    clean_username = username[1:]
    if not clean_username.replace("_", "").isalnum():
        return False

    return True


def format_leaderboard(
    scores: List[tuple[str, int]], limit: Optional[int] = None
) -> str:
    """Format a leaderboard display.

    Args:
        scores: List of (username, score) tuples
        limit: Maximum number of entries to display

    Returns:
        Formatted leaderboard string
    """
    if not scores:
        return "No scores available"

    # Sort by score (descending)
    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    if limit:
        sorted_scores = sorted_scores[:limit]

    leaderboard_lines = []
    for i, (username, score) in enumerate(sorted_scores, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_lines.append(f"{medal} {username}: {score} besitos")

    return "\n".join(leaderboard_lines)
