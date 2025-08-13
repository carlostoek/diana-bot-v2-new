"""
Leaderboard Engine for Diana Bot V2 Gamification System.

This module handles all leaderboard calculations, ranking logic, competitive mechanics,
and real-time position tracking with support for multiple leaderboard types.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ....models.gamification import LeaderboardEntry, LeaderboardType, UserGamification
from ..interfaces import GamificationError


class LeaderboardEngine:
    """
    Core engine for leaderboard system operations.

    Handles ranking calculations, position tracking, competitive mechanics,
    and leaderboard period management with real-time updates.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Leaderboard Engine.

        Args:
            config: Configuration dictionary with leaderboard settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Leaderboard configuration
        self.leaderboard_settings = config.get(
            "leaderboard_settings",
            {
                "update_frequency_minutes": 5,
                "max_entries_per_board": 1000,
                "position_change_threshold": 5,  # Notify for position changes >= 5
                "personal_best_bonus_points": 100,
            },
        )

    def calculate_user_ranking(
        self,
        user_id: int,
        leaderboard_type: LeaderboardType,
        user_score: int,
        period_start: datetime,
        period_end: datetime,
        existing_entries: List[LeaderboardEntry],
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate a user's ranking on a specific leaderboard.

        Args:
            user_id: ID of the user
            leaderboard_type: Type of leaderboard
            user_score: User's current score
            period_start: Start of the leaderboard period
            period_end: End of the leaderboard period
            existing_entries: Current leaderboard entries

        Returns:
            Tuple of (user_rank, ranking_context)
        """
        # Filter entries for this leaderboard and period
        relevant_entries = [
            entry
            for entry in existing_entries
            if (
                entry.leaderboard_type == leaderboard_type
                and entry.period_start == period_start
                and entry.period_end == period_end
            )
        ]

        # Sort by score descending
        sorted_entries = sorted(relevant_entries, key=lambda x: x.score, reverse=True)

        # Find user's position
        user_rank = 1
        for i, entry in enumerate(sorted_entries, 1):
            if entry.score > user_score:
                user_rank = i + 1
            else:
                break

        # Calculate ranking context
        total_participants = len(sorted_entries) + 1  # +1 for current user

        # Find users ahead and behind
        users_ahead = sum(1 for entry in sorted_entries if entry.score > user_score)
        users_behind = sum(1 for entry in sorted_entries if entry.score < user_score)

        # Calculate percentile
        percentile = max(
            0, ((total_participants - user_rank) / total_participants) * 100
        )

        # Find previous rank for this user
        previous_rank = None
        previous_score = None
        user_entry = next((e for e in sorted_entries if e.user_id == user_id), None)
        if user_entry:
            previous_rank = user_entry.rank
            previous_score = user_entry.score

        ranking_context = {
            "total_participants": total_participants,
            "users_ahead": users_ahead,
            "users_behind": users_behind,
            "percentile": round(percentile, 2),
            "previous_rank": previous_rank,
            "previous_score": previous_score,
            "rank_change": (previous_rank - user_rank) if previous_rank else None,
            "score_change": (user_score - previous_score)
            if previous_score
            else user_score,
        }

        return user_rank, ranking_context

    def create_leaderboard_entry_data(
        self,
        user_id: int,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
        rank: int,
        score: int,
        ranking_context: Dict[str, Any],
        user_gamification: Optional[UserGamification] = None,
    ) -> Dict[str, Any]:
        """
        Create leaderboard entry data for database storage.

        Args:
            user_id: ID of the user
            leaderboard_type: Type of leaderboard
            period_start: Start of the period
            period_end: End of the period
            rank: User's rank
            score: User's score
            ranking_context: Context from ranking calculation
            user_gamification: User's gamification data

        Returns:
            Leaderboard entry data dictionary
        """
        # Check if this is a personal best
        is_personal_best = self._is_personal_best(
            user_id, leaderboard_type, score, ranking_context.get("previous_score")
        )

        # Calculate rewards if applicable
        rewards = self._calculate_leaderboard_rewards(
            rank, leaderboard_type, is_personal_best, user_gamification
        )

        return {
            "user_id": user_id,
            "leaderboard_type": leaderboard_type,
            "period_start": period_start,
            "period_end": period_end,
            "rank": rank,
            "score": score,
            "previous_rank": ranking_context.get("previous_rank"),
            "rank_change": ranking_context.get("rank_change"),
            "is_personal_best": is_personal_best,
            "rewards_claimed": rewards,
        }

    def get_leaderboard_data(
        self,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
        entries: List[LeaderboardEntry],
        user_id: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Format leaderboard data for display.

        Args:
            leaderboard_type: Type of leaderboard
            period_start: Start of the period
            period_end: End of the period
            entries: Leaderboard entries
            user_id: Optional user ID to include their position
            limit: Number of top entries to return

        Returns:
            Formatted leaderboard data
        """
        # Sort entries by rank
        sorted_entries = sorted(entries, key=lambda x: x.rank)
        top_entries = sorted_entries[:limit]

        # Format top entries
        leaderboard_entries = []
        for entry in top_entries:
            entry_data = {
                "rank": entry.rank,
                "user_id": entry.user_id,
                "score": entry.score,
                "rank_change": entry.rank_change,
                "is_personal_best": entry.is_personal_best,
                "badge": self._get_rank_badge(entry.rank),
            }
            leaderboard_entries.append(entry_data)

        # Find user's position if requested
        user_position = None
        if user_id:
            user_entry = next((e for e in sorted_entries if e.user_id == user_id), None)
            if user_entry:
                user_position = {
                    "rank": user_entry.rank,
                    "score": user_entry.score,
                    "rank_change": user_entry.rank_change,
                    "is_personal_best": user_entry.is_personal_best,
                    "percentile": self._calculate_percentile(
                        user_entry.rank, len(sorted_entries)
                    ),
                }

        return {
            "leaderboard_type": leaderboard_type.value,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_participants": len(sorted_entries),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "entries": leaderboard_entries,
            "user_position": user_position,
            "period_info": self._get_period_info(
                leaderboard_type, period_start, period_end
            ),
        }

    def get_leaderboard_periods(
        self,
        leaderboard_type: LeaderboardType,
        reference_date: Optional[datetime] = None,
    ) -> Dict[str, Tuple[datetime, datetime]]:
        """
        Get start and end dates for leaderboard periods.

        Args:
            leaderboard_type: Type of leaderboard
            reference_date: Reference date (defaults to now)

        Returns:
            Dictionary with period names and their date ranges
        """
        reference_date = reference_date or datetime.now(timezone.utc)

        if leaderboard_type == LeaderboardType.WEEKLY:
            return self._get_weekly_periods(reference_date)
        elif leaderboard_type == LeaderboardType.MONTHLY:
            return self._get_monthly_periods(reference_date)
        elif leaderboard_type == LeaderboardType.GLOBAL:
            return self._get_global_periods(reference_date)
        else:
            # For other types, use current week
            return self._get_weekly_periods(reference_date)

    def calculate_competitive_metrics(
        self,
        user_entries: List[LeaderboardEntry],
        all_leaderboards: List[LeaderboardType],
    ) -> Dict[str, Any]:
        """
        Calculate competitive metrics for a user across all leaderboards.

        Args:
            user_entries: User's leaderboard entries
            all_leaderboards: All available leaderboard types

        Returns:
            Comprehensive competitive metrics
        """
        # Best ranks across all leaderboards
        best_ranks = {}
        for lb_type in all_leaderboards:
            user_entries_for_type = [
                e for e in user_entries if e.leaderboard_type == lb_type
            ]
            if user_entries_for_type:
                best_rank = min(e.rank for e in user_entries_for_type)
                best_ranks[lb_type.value] = best_rank

        # Count personal bests
        personal_bests = sum(1 for entry in user_entries if entry.is_personal_best)

        # Calculate average rank across all participations
        all_ranks = [entry.rank for entry in user_entries]
        average_rank = sum(all_ranks) / len(all_ranks) if all_ranks else None

        # Count top positions (top 10, top 5, top 3)
        top_10_count = sum(1 for entry in user_entries if entry.rank <= 10)
        top_5_count = sum(1 for entry in user_entries if entry.rank <= 5)
        top_3_count = sum(1 for entry in user_entries if entry.rank <= 3)

        # Calculate competitive level based on performance
        competitive_level = self._calculate_competitive_level(
            best_ranks, personal_bests, top_3_count
        )

        # Find most improved leaderboard
        most_improved = self._find_most_improved_leaderboard(user_entries)

        return {
            "best_ranks": best_ranks,
            "personal_bests_count": personal_bests,
            "average_rank": round(average_rank, 2) if average_rank else None,
            "top_10_finishes": top_10_count,
            "top_5_finishes": top_5_count,
            "top_3_finishes": top_3_count,
            "competitive_level": competitive_level,
            "most_improved_leaderboard": most_improved,
            "total_participations": len(user_entries),
            "leaderboards_participated": len(
                set(e.leaderboard_type for e in user_entries)
            ),
        }

    def get_leaderboard_insights(
        self,
        user_id: int,
        user_entries: List[LeaderboardEntry],
        recent_activity: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Generate insights and recommendations for leaderboard performance.

        Args:
            user_id: ID of the user
            user_entries: User's leaderboard entries
            recent_activity: Recent user activity data

        Returns:
            List of insight dictionaries
        """
        insights = []

        # Recent performance trend
        recent_entries = sorted(
            [
                e
                for e in user_entries
                if e.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
            ],
            key=lambda x: x.created_at,
            reverse=True,
        )[:5]

        if len(recent_entries) >= 2:
            trend = self._analyze_performance_trend(recent_entries)
            if trend:
                insights.append(trend)

        # Personal best opportunities
        pb_opportunities = self._find_personal_best_opportunities(
            user_entries, recent_activity
        )
        insights.extend(pb_opportunities)

        # Competitive recommendations
        competitive_recs = self._get_competitive_recommendations(
            user_entries, recent_activity
        )
        insights.extend(competitive_recs)

        # Achievement proximity
        achievement_insights = self._get_achievement_proximity_insights(user_entries)
        insights.extend(achievement_insights)

        return insights[:10]  # Limit to top 10 insights

    def _is_personal_best(
        self,
        user_id: int,
        leaderboard_type: LeaderboardType,
        current_score: int,
        previous_score: Optional[int],
    ) -> bool:
        """Check if current score is a personal best."""
        if previous_score is None:
            return True  # First score is always a personal best

        return current_score > previous_score

    def _calculate_leaderboard_rewards(
        self,
        rank: int,
        leaderboard_type: LeaderboardType,
        is_personal_best: bool,
        user_gamification: Optional[UserGamification],
    ) -> Optional[Dict[str, Any]]:
        """Calculate rewards for leaderboard position."""
        rewards = {}

        # Rank-based rewards
        if rank == 1:
            rewards["bonus_points"] = 1000
            rewards["badge"] = "first_place"
        elif rank <= 3:
            rewards["bonus_points"] = 500
            rewards["badge"] = "top_three"
        elif rank <= 10:
            rewards["bonus_points"] = 200
            rewards["badge"] = "top_ten"
        elif rank <= 50:
            rewards["bonus_points"] = 50

        # Personal best bonus
        if is_personal_best:
            pb_bonus = self.leaderboard_settings.get("personal_best_bonus_points", 100)
            rewards["personal_best_bonus"] = pb_bonus

        # VIP multiplier
        if user_gamification and user_gamification.vip_status:
            total_points = rewards.get("bonus_points", 0) + rewards.get(
                "personal_best_bonus", 0
            )
            rewards["vip_multiplier_bonus"] = int(total_points * 0.5)  # 50% VIP bonus

        return rewards if rewards else None

    def _get_rank_badge(self, rank: int) -> str:
        """Get badge for a specific rank."""
        if rank == 1:
            return "🥇"
        elif rank == 2:
            return "🥈"
        elif rank == 3:
            return "🥉"
        elif rank <= 10:
            return "🏆"
        elif rank <= 50:
            return "⭐"
        else:
            return "👤"

    def _calculate_percentile(self, rank: int, total_participants: int) -> float:
        """Calculate percentile for a rank."""
        if total_participants <= 1:
            return 100.0

        percentile = ((total_participants - rank) / total_participants) * 100
        return round(percentile, 2)

    def _get_period_info(
        self,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        """Get information about the leaderboard period."""
        now = datetime.now(timezone.utc)

        # Calculate time remaining
        time_remaining = period_end - now
        is_active = period_start <= now <= period_end

        return {
            "is_active": is_active,
            "time_remaining_hours": max(0, int(time_remaining.total_seconds() / 3600)),
            "progress_percentage": min(
                100, ((now - period_start) / (period_end - period_start)) * 100
            )
            if is_active
            else 100,
            "period_type": leaderboard_type.value,
        }

    def _get_weekly_periods(
        self, reference_date: datetime
    ) -> Dict[str, Tuple[datetime, datetime]]:
        """Get weekly period boundaries."""
        # Start of current week (Monday)
        start_of_week = reference_date - timedelta(days=reference_date.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7) - timedelta(microseconds=1)

        return {
            "current": (start_of_week, end_of_week),
            "previous": (
                start_of_week - timedelta(days=7),
                start_of_week - timedelta(microseconds=1),
            ),
        }

    def _get_monthly_periods(
        self, reference_date: datetime
    ) -> Dict[str, Tuple[datetime, datetime]]:
        """Get monthly period boundaries."""
        # Start of current month
        start_of_month = reference_date.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        # Start of next month
        if start_of_month.month == 12:
            start_of_next_month = start_of_month.replace(
                year=start_of_month.year + 1, month=1
            )
        else:
            start_of_next_month = start_of_month.replace(month=start_of_month.month + 1)

        end_of_month = start_of_next_month - timedelta(microseconds=1)

        # Previous month
        if start_of_month.month == 1:
            start_of_prev_month = start_of_month.replace(
                year=start_of_month.year - 1, month=12
            )
        else:
            start_of_prev_month = start_of_month.replace(month=start_of_month.month - 1)

        return {
            "current": (start_of_month, end_of_month),
            "previous": (
                start_of_prev_month,
                start_of_month - timedelta(microseconds=1),
            ),
        }

    def _get_global_periods(
        self, reference_date: datetime
    ) -> Dict[str, Tuple[datetime, datetime]]:
        """Get global period boundaries (all time)."""
        # Global leaderboard covers all time
        start_of_time = datetime(2020, 1, 1, tzinfo=timezone.utc)  # Bot launch date
        end_of_time = datetime(2099, 12, 31, tzinfo=timezone.utc)

        return {
            "all_time": (start_of_time, end_of_time),
        }

    def _calculate_competitive_level(
        self,
        best_ranks: Dict[str, int],
        personal_bests: int,
        top_3_count: int,
    ) -> str:
        """Calculate competitive level based on performance."""
        if not best_ranks:
            return "newcomer"

        best_rank = min(best_ranks.values())

        if best_rank == 1 and top_3_count >= 3:
            return "champion"
        elif best_rank <= 3 and top_3_count >= 2:
            return "elite"
        elif best_rank <= 10 and personal_bests >= 3:
            return "competitive"
        elif best_rank <= 50:
            return "rising"
        else:
            return "participant"

    def _find_most_improved_leaderboard(
        self,
        user_entries: List[LeaderboardEntry],
    ) -> Optional[Dict[str, Any]]:
        """Find the leaderboard where user has improved the most."""
        improvements = {}

        for leaderboard_type in set(e.leaderboard_type for e in user_entries):
            type_entries = [
                e for e in user_entries if e.leaderboard_type == leaderboard_type
            ]
            type_entries.sort(key=lambda x: x.created_at)

            if len(type_entries) >= 2:
                improvement = type_entries[0].rank - type_entries[-1].rank
                if improvement > 0:
                    improvements[leaderboard_type] = {
                        "improvement": improvement,
                        "from_rank": type_entries[0].rank,
                        "to_rank": type_entries[-1].rank,
                    }

        if improvements:
            best_improvement = max(
                improvements.items(), key=lambda x: x[1]["improvement"]
            )
            return {
                "leaderboard_type": best_improvement[0].value,
                "improvement": best_improvement[1]["improvement"],
                "from_rank": best_improvement[1]["from_rank"],
                "to_rank": best_improvement[1]["to_rank"],
            }

        return None

    def _analyze_performance_trend(
        self, recent_entries: List[LeaderboardEntry]
    ) -> Optional[Dict[str, Any]]:
        """Analyze recent performance trend."""
        if len(recent_entries) < 2:
            return None

        ranks = [entry.rank for entry in recent_entries]

        # Calculate trend
        if ranks[0] < ranks[-1]:
            trend = "improving"
            change = ranks[-1] - ranks[0]
        elif ranks[0] > ranks[-1]:
            trend = "declining"
            change = ranks[0] - ranks[-1]
        else:
            trend = "stable"
            change = 0

        return {
            "type": "performance_trend",
            "trend": trend,
            "rank_change": change,
            "periods_analyzed": len(recent_entries),
            "message": self._get_trend_message(trend, change),
        }

    def _find_personal_best_opportunities(
        self,
        user_entries: List[LeaderboardEntry],
        recent_activity: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Find opportunities for personal bests."""
        opportunities = []

        # Analyze each leaderboard type
        for leaderboard_type in set(e.leaderboard_type for e in user_entries):
            type_entries = [
                e for e in user_entries if e.leaderboard_type == leaderboard_type
            ]
            best_score = max(e.score for e in type_entries)
            recent_entry = max(type_entries, key=lambda x: x.created_at)

            # Check if close to personal best
            if recent_entry.score >= best_score * 0.9:  # Within 10% of personal best
                opportunities.append(
                    {
                        "type": "personal_best_opportunity",
                        "leaderboard_type": leaderboard_type.value,
                        "current_score": recent_entry.score,
                        "personal_best": best_score,
                        "gap": best_score - recent_entry.score,
                        "message": f"You're close to your personal best on {leaderboard_type.value}!",
                    }
                )

        return opportunities

    def _get_competitive_recommendations(
        self,
        user_entries: List[LeaderboardEntry],
        recent_activity: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Get competitive recommendations."""
        recommendations = []

        # Recommend underperforming leaderboards
        leaderboard_performance = {}
        for entry in user_entries:
            lb_type = entry.leaderboard_type
            if lb_type not in leaderboard_performance:
                leaderboard_performance[lb_type] = []
            leaderboard_performance[lb_type].append(entry.rank)

        for lb_type, ranks in leaderboard_performance.items():
            avg_rank = sum(ranks) / len(ranks)
            if avg_rank > 50:  # Poor performance
                recommendations.append(
                    {
                        "type": "improvement_opportunity",
                        "leaderboard_type": lb_type.value,
                        "average_rank": round(avg_rank, 1),
                        "message": f"Focus on {lb_type.value} leaderboard for improvement potential",
                    }
                )

        return recommendations

    def _get_achievement_proximity_insights(
        self, user_entries: List[LeaderboardEntry]
    ) -> List[Dict[str, Any]]:
        """Get insights about proximity to leaderboard achievements."""
        insights = []

        # Check proximity to rank-based achievements
        best_ranks = {}
        for entry in user_entries:
            lb_type = entry.leaderboard_type
            if lb_type not in best_ranks or entry.rank < best_ranks[lb_type]:
                best_ranks[lb_type] = entry.rank

        for lb_type, best_rank in best_ranks.items():
            if 5 < best_rank <= 10:
                insights.append(
                    {
                        "type": "achievement_proximity",
                        "achievement": "top_5_finish",
                        "leaderboard_type": lb_type.value,
                        "current_best": best_rank,
                        "target": 5,
                        "message": f"You're close to a top 5 finish on {lb_type.value}!",
                    }
                )
            elif 3 < best_rank <= 5:
                insights.append(
                    {
                        "type": "achievement_proximity",
                        "achievement": "podium_finish",
                        "leaderboard_type": lb_type.value,
                        "current_best": best_rank,
                        "target": 3,
                        "message": f"A podium finish on {lb_type.value} is within reach!",
                    }
                )

        return insights

    def _get_trend_message(self, trend: str, change: int) -> str:
        """Get message for performance trend."""
        if trend == "improving":
            return f"Great job! You've improved by {change} positions recently."
        elif trend == "declining":
            return f"Focus up! Your rank has dropped by {change} positions."
        else:
            return "Your performance has been consistent lately."
