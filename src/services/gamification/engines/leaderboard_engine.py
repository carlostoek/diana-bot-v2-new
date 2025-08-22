"""
Leaderboard Engine for Gamification System

This module provides dynamic leaderboard generation and ranking with privacy
controls, caching optimization, and real-time updates. It handles multiple
leaderboard types and ensures efficient performance even with large user bases.

Key Features:
- Multiple leaderboard types (weekly, total, streaks, etc.)
- Privacy-compliant user filtering
- Efficient caching with smart invalidation
- Real-time ranking calculations
- Tie-breaking rules and fair ranking
- User position tracking even outside top rankings
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..interfaces import ILeaderboardEngine, LeaderboardType
from ..models import UserGamification

# Configure logging
logger = logging.getLogger(__name__)


class LeaderboardEngineError(Exception):
    """Exception raised by the LeaderboardEngine for operation failures."""

    pass


class LeaderboardEngine(ILeaderboardEngine):
    """
    Dynamic leaderboard generation and ranking engine.

    Provides efficient ranking calculations with privacy controls and caching
    optimization for high-performance leaderboard generation.
    """

    def __init__(
        self,
        points_engine=None,  # Will be injected by GamificationService
        database_client=None,  # In production, this would be the actual DB client
        cache_ttl_seconds: int = 300,  # 5 minutes default cache TTL
        max_leaderboard_size: int = 1000,  # Maximum entries to calculate
    ):
        """
        Initialize the LeaderboardEngine.

        Args:
            points_engine: Points engine for user data access
            database_client: Database client for persistence
            cache_ttl_seconds: Cache time-to-live in seconds
            max_leaderboard_size: Maximum entries to process for rankings
        """
        self.points_engine = points_engine
        self.database_client = database_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_leaderboard_size = max_leaderboard_size

        # Leaderboard cache with timestamps
        self.leaderboard_cache: Dict[LeaderboardType, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[LeaderboardType, datetime] = {}

        # User privacy preferences
        self.privacy_preferences: Dict[int, bool] = (
            {}
        )  # user_id -> show_in_leaderboards

        # Performance metrics
        self.generation_metrics = {
            "total_generations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_generation_time_ms": 0.0,
        }

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def get_leaderboard(
        self,
        leaderboard_type: LeaderboardType,
        limit: int = 10,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get leaderboard rankings for a specific type.

        Returns cached data if available and fresh, otherwise generates new rankings.
        """
        start_time = time.time()

        async with self._lock:
            try:
                # Check cache first
                cached_data = await self._get_cached_leaderboard(leaderboard_type)
                if cached_data:
                    self.generation_metrics["cache_hits"] += 1

                    # Extract requested portion and add user position if needed
                    result = self._format_leaderboard_response(
                        cached_data, limit, user_id
                    )

                    await self._record_generation_metrics(start_time)
                    return result

                # Cache miss - generate new leaderboard
                self.generation_metrics["cache_misses"] += 1

                # Generate leaderboard data
                leaderboard_data = await self._generate_leaderboard(leaderboard_type)

                # Cache the results
                await self._cache_leaderboard(leaderboard_type, leaderboard_data)

                # Format response
                result = self._format_leaderboard_response(
                    leaderboard_data, limit, user_id
                )

                await self._record_generation_metrics(start_time)
                return result

            except Exception as e:
                logger.error(
                    f"Error generating leaderboard {leaderboard_type.value}: {e}"
                )
                await self._record_generation_metrics(start_time)
                return {
                    "leaderboard_type": leaderboard_type.value,
                    "rankings": [],
                    "user_position": None,
                    "total_participants": 0,
                    "error": str(e),
                }

    async def get_user_rankings(
        self,
        user_id: int,
    ) -> Dict[LeaderboardType, int]:
        """
        Get user's current rank across all leaderboard types.
        """
        async with self._lock:
            user_rankings = {}

            for leaderboard_type in LeaderboardType:
                try:
                    leaderboard_data = await self._get_cached_leaderboard(
                        leaderboard_type
                    )
                    if not leaderboard_data:
                        leaderboard_data = await self._generate_leaderboard(
                            leaderboard_type
                        )

                    # Find user's position
                    user_position = None
                    for rank, entry in enumerate(leaderboard_data["rankings"], 1):
                        if entry["user_id"] == user_id:
                            user_position = rank
                            break

                    user_rankings[leaderboard_type] = user_position

                except Exception as e:
                    logger.error(
                        f"Error getting user ranking for {leaderboard_type.value}: {e}"
                    )
                    user_rankings[leaderboard_type] = None

            return user_rankings

    async def update_leaderboard_cache(
        self,
        leaderboard_type: LeaderboardType,
    ) -> None:
        """
        Force update of leaderboard cache for a specific type.
        """
        async with self._lock:
            try:
                # Generate fresh leaderboard data
                leaderboard_data = await self._generate_leaderboard(leaderboard_type)

                # Update cache
                await self._cache_leaderboard(leaderboard_type, leaderboard_data)

                logger.info(f"Updated cache for leaderboard: {leaderboard_type.value}")

            except Exception as e:
                logger.error(f"Error updating cache for {leaderboard_type.value}: {e}")

    async def set_privacy_preference(
        self,
        user_id: int,
        show_in_leaderboards: bool,
    ) -> None:
        """
        Set user's privacy preference for leaderboard visibility.
        """
        async with self._lock:
            self.privacy_preferences[user_id] = show_in_leaderboards

            # Invalidate all leaderboard caches since user visibility changed
            await self._invalidate_all_caches()

            logger.info(
                f"Updated privacy preference for user {user_id}: "
                f"show_in_leaderboards={show_in_leaderboards}"
            )

    # Private helper methods

    async def _get_cached_leaderboard(
        self, leaderboard_type: LeaderboardType
    ) -> Optional[Dict[str, Any]]:
        """Get cached leaderboard if available and fresh."""
        cached_time = self.cache_timestamps.get(leaderboard_type)
        if not cached_time:
            return None

        # Check if cache is still fresh
        age = datetime.now(timezone.utc) - cached_time
        if age.total_seconds() > self.cache_ttl_seconds:
            # Cache expired
            if leaderboard_type in self.leaderboard_cache:
                del self.leaderboard_cache[leaderboard_type]
            if leaderboard_type in self.cache_timestamps:
                del self.cache_timestamps[leaderboard_type]
            return None

        return self.leaderboard_cache.get(leaderboard_type)

    async def _cache_leaderboard(
        self, leaderboard_type: LeaderboardType, data: Dict[str, Any]
    ) -> None:
        """Cache leaderboard data with timestamp."""
        self.leaderboard_cache[leaderboard_type] = data
        self.cache_timestamps[leaderboard_type] = datetime.now(timezone.utc)

    async def _generate_leaderboard(
        self, leaderboard_type: LeaderboardType
    ) -> Dict[str, Any]:
        """
        Generate fresh leaderboard data for a specific type.
        """
        # Get user data based on leaderboard type
        user_scores = await self._get_user_scores_for_leaderboard(leaderboard_type)

        # Filter out users who opted out of leaderboards
        filtered_scores = []
        for user_data in user_scores:
            user_id = user_data["user_id"]
            show_in_leaderboards = self.privacy_preferences.get(
                user_id, True
            )  # Default to showing

            if show_in_leaderboards:
                filtered_scores.append(user_data)

        # Sort users by score (descending)
        sorted_users = sorted(filtered_scores, key=lambda x: x["score"], reverse=True)

        # Apply tie-breaking rules
        ranked_users = self._apply_tie_breaking(sorted_users, leaderboard_type)

        # Limit to maximum size for performance
        if len(ranked_users) > self.max_leaderboard_size:
            ranked_users = ranked_users[: self.max_leaderboard_size]

        # Add rank information
        rankings = []
        for rank, user_data in enumerate(ranked_users, 1):
            rankings.append(
                {
                    "rank": rank,
                    "user_id": user_data["user_id"],
                    "username": user_data.get(
                        "username", f"User {user_data['user_id']}"
                    ),
                    "score": user_data["score"],
                    "additional_data": user_data.get("additional_data", {}),
                }
            )

        return {
            "leaderboard_type": leaderboard_type.value,
            "rankings": rankings,
            "total_participants": len(filtered_scores),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _get_user_scores_for_leaderboard(
        self, leaderboard_type: LeaderboardType
    ) -> List[Dict[str, Any]]:
        """
        Get user scores for a specific leaderboard type.

        In production, this would query the database efficiently.
        For now, using mock data based on available user data.
        """
        user_scores = []

        # In production, this would be optimized database queries
        # For now, simulating with available data

        if leaderboard_type == LeaderboardType.TOTAL_POINTS:
            # Total points leaderboard
            for user_id in range(1, 101):  # Mock 100 users
                import random

                score = random.randint(100, 50000)
                user_scores.append(
                    {
                        "user_id": user_id,
                        "username": f"User{user_id}",
                        "score": score,
                        "additional_data": {"total_points": score},
                    }
                )

        elif leaderboard_type == LeaderboardType.WEEKLY_POINTS:
            # Weekly points leaderboard
            for user_id in range(1, 101):  # Mock 100 users
                import random

                score = random.randint(0, 5000)
                user_scores.append(
                    {
                        "user_id": user_id,
                        "username": f"User{user_id}",
                        "score": score,
                        "additional_data": {"weekly_points": score},
                    }
                )

        elif leaderboard_type == LeaderboardType.CURRENT_STREAK:
            # Current streak leaderboard
            for user_id in range(1, 101):  # Mock 100 users
                import random

                score = random.randint(0, 365)
                user_scores.append(
                    {
                        "user_id": user_id,
                        "username": f"User{user_id}",
                        "score": score,
                        "additional_data": {"current_streak": score},
                    }
                )

        elif leaderboard_type == LeaderboardType.NARRATIVE_PROGRESS:
            # Narrative progress leaderboard
            for user_id in range(1, 101):  # Mock 100 users
                import random

                score = random.randint(0, 50)
                user_scores.append(
                    {
                        "user_id": user_id,
                        "username": f"User{user_id}",
                        "score": score,
                        "additional_data": {"chapters_completed": score},
                    }
                )

        elif leaderboard_type == LeaderboardType.TRIVIA_CHAMPION:
            # Trivia champion leaderboard
            for user_id in range(1, 101):  # Mock 100 users
                import random

                score = random.randint(0, 100)
                user_scores.append(
                    {
                        "user_id": user_id,
                        "username": f"User{user_id}",
                        "score": score,
                        "additional_data": {"trivia_streak": score},
                    }
                )

        elif leaderboard_type == LeaderboardType.ACHIEVEMENTS_COUNT:
            # Achievements count leaderboard
            for user_id in range(1, 101):  # Mock 100 users
                import random

                score = random.randint(0, 20)
                user_scores.append(
                    {
                        "user_id": user_id,
                        "username": f"User{user_id}",
                        "score": score,
                        "additional_data": {"achievements_unlocked": score},
                    }
                )

        return user_scores

    def _apply_tie_breaking(
        self, sorted_users: List[Dict[str, Any]], leaderboard_type: LeaderboardType
    ) -> List[Dict[str, Any]]:
        """
        Apply tie-breaking rules for fair ranking.

        Different leaderboard types may have different tie-breaking rules.
        """
        if not sorted_users:
            return sorted_users

        # Group users by score to identify ties
        score_groups = defaultdict(list)
        for user_data in sorted_users:
            score_groups[user_data["score"]].append(user_data)

        # Apply tie-breaking within each score group
        final_ranking = []
        for score in sorted(score_groups.keys(), reverse=True):
            tied_users = score_groups[score]

            if len(tied_users) == 1:
                final_ranking.extend(tied_users)
            else:
                # Apply tie-breaking rules
                if leaderboard_type == LeaderboardType.TOTAL_POINTS:
                    # Tie-break by user registration date (earlier = higher rank)
                    tied_users.sort(
                        key=lambda x: x["user_id"]
                    )  # Lower user_id = earlier registration

                elif leaderboard_type == LeaderboardType.WEEKLY_POINTS:
                    # Tie-break by total points
                    tied_users.sort(
                        key=lambda x: x.get("additional_data", {}).get(
                            "total_points", 0
                        ),
                        reverse=True,
                    )

                elif leaderboard_type == LeaderboardType.CURRENT_STREAK:
                    # Tie-break by total points
                    tied_users.sort(
                        key=lambda x: x.get("additional_data", {}).get(
                            "total_points", 0
                        ),
                        reverse=True,
                    )

                else:
                    # Default tie-breaking by user_id
                    tied_users.sort(key=lambda x: x["user_id"])

                final_ranking.extend(tied_users)

        return final_ranking

    def _format_leaderboard_response(
        self,
        leaderboard_data: Dict[str, Any],
        limit: int,
        user_id: Optional[int],
    ) -> Dict[str, Any]:
        """
        Format leaderboard response with requested limit and user position.
        """
        rankings = leaderboard_data["rankings"]

        # Get top entries up to limit
        top_rankings = rankings[:limit]

        # Find user position if requested
        user_position = None
        user_entry = None

        if user_id:
            for rank, entry in enumerate(rankings, 1):
                if entry["user_id"] == user_id:
                    user_position = rank
                    user_entry = {
                        **entry,
                        "rank": rank,
                    }
                    break

        response = {
            "leaderboard_type": leaderboard_data["leaderboard_type"],
            "rankings": top_rankings,
            "total_participants": leaderboard_data["total_participants"],
            "generated_at": leaderboard_data["generated_at"],
            "user_position": user_position,
            "user_entry": user_entry,
        }

        return response

    async def _invalidate_all_caches(self) -> None:
        """Invalidate all leaderboard caches."""
        self.leaderboard_cache.clear()
        self.cache_timestamps.clear()
        logger.info("Invalidated all leaderboard caches")

    async def _record_generation_metrics(self, start_time: float) -> None:
        """Record metrics for leaderboard generation performance."""
        generation_time_ms = (time.time() - start_time) * 1000

        self.generation_metrics["total_generations"] += 1

        # Update average generation time (exponential moving average)
        alpha = 0.1
        if self.generation_metrics["avg_generation_time_ms"] == 0:
            self.generation_metrics["avg_generation_time_ms"] = generation_time_ms
        else:
            current_avg = self.generation_metrics["avg_generation_time_ms"]
            self.generation_metrics["avg_generation_time_ms"] = (
                alpha * generation_time_ms + (1 - alpha) * current_avg
            )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        cache_hit_rate = 0.0
        total_requests = (
            self.generation_metrics["cache_hits"]
            + self.generation_metrics["cache_misses"]
        )
        if total_requests > 0:
            cache_hit_rate = (
                self.generation_metrics["cache_hits"] / total_requests * 100.0
            )

        return {
            **self.generation_metrics,
            "cache_hit_rate_percentage": cache_hit_rate,
            "cached_leaderboards": len(self.leaderboard_cache),
        }

    async def get_leaderboard_stats(self) -> Dict[str, Any]:
        """Get statistics about all leaderboards."""
        async with self._lock:
            stats = {
                "total_leaderboard_types": len(LeaderboardType),
                "cached_leaderboards": len(self.leaderboard_cache),
                "users_with_privacy_settings": len(self.privacy_preferences),
                "users_opted_out": sum(
                    1 for show in self.privacy_preferences.values() if not show
                ),
                "performance_metrics": self.get_performance_metrics(),
            }

            # Add per-leaderboard stats
            leaderboard_stats = {}
            for leaderboard_type in LeaderboardType:
                cached_data = await self._get_cached_leaderboard(leaderboard_type)
                if cached_data:
                    leaderboard_stats[leaderboard_type.value] = {
                        "total_participants": cached_data["total_participants"],
                        "cache_age_seconds": (
                            datetime.now(timezone.utc)
                            - self.cache_timestamps[leaderboard_type]
                        ).total_seconds(),
                    }

            stats["leaderboard_details"] = leaderboard_stats
            return stats
