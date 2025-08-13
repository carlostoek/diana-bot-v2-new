"""
Gamification Repository Implementation for Diana Bot V2.

This module implements the data access layer for the gamification system,
providing database operations for all gamification entities.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

from ...models.gamification import (
    AchievementDefinition,
    LeaderboardEntry,
    LeaderboardType,
    PointsTransaction,
    PointsTransactionType,
    StreakRecord,
    StreakType,
    UserAchievement,
    UserGamification,
)
from .interfaces import GamificationError, IGamificationRepository


class GamificationRepository(IGamificationRepository):
    """
    SQLAlchemy-based repository for gamification data.

    This repository handles all database operations for the gamification system
    using async SQLAlchemy and PostgreSQL.
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the repository.

        Args:
            database_url: Optional database URL. If not provided, will use environment variable.
        """
        self.database_url = (
            database_url or "postgresql+asyncpg://localhost/diana_bot_v2"
        )
        self.engine = None
        self.async_session = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """Initialize database connection and session factory."""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            self.logger.info("GamificationRepository initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize GamificationRepository: {e}")
            raise GamificationError(f"Repository initialization failed: {e}")

    async def shutdown(self) -> None:
        """Shutdown database connections."""
        if self.engine:
            await self.engine.dispose()
            self.logger.info("GamificationRepository shutdown complete")

    # ================= User Gamification CRUD =================

    async def get_user_gamification(self, user_id: int) -> Optional[UserGamification]:
        """Get user gamification data."""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(UserGamification).where(UserGamification.user_id == user_id)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                self.logger.error(f"Error getting user gamification for {user_id}: {e}")
                raise GamificationError(f"Failed to get user gamification: {e}")

    async def create_user_gamification(self, user_id: int) -> UserGamification:
        """Create new user gamification record."""
        async with self.async_session() as session:
            try:
                user_gam = UserGamification(user_id=user_id)
                session.add(user_gam)
                await session.commit()
                await session.refresh(user_gam)

                self.logger.info(f"Created gamification record for user {user_id}")
                return user_gam

            except Exception as e:
                await session.rollback()
                self.logger.error(
                    f"Error creating user gamification for {user_id}: {e}"
                )
                raise GamificationError(f"Failed to create user gamification: {e}")

    async def update_user_gamification(
        self, user_gamification: UserGamification
    ) -> UserGamification:
        """Update user gamification record."""
        async with self.async_session() as session:
            try:
                # Merge the object into the session
                merged_user_gam = await session.merge(user_gamification)
                await session.commit()
                await session.refresh(merged_user_gam)

                return merged_user_gam

            except Exception as e:
                await session.rollback()
                self.logger.error(
                    f"Error updating user gamification for {user_gamification.user_id}: {e}"
                )
                raise GamificationError(f"Failed to update user gamification: {e}")

    # ================= Points Transactions =================

    async def create_points_transaction(
        self, transaction_data: Dict[str, Any]
    ) -> PointsTransaction:
        """Create a new points transaction record."""
        async with self.async_session() as session:
            try:
                transaction = PointsTransaction(
                    user_id=transaction_data["user_id"],
                    transaction_type=transaction_data["transaction_type"],
                    amount=transaction_data["amount"],
                    points_before=transaction_data["points_before"],
                    points_after=transaction_data["points_after"],
                    action_type=transaction_data["action_type"],
                    description=transaction_data.get("description"),
                    source_service=transaction_data["source_service"],
                    source_event_id=transaction_data.get("source_event_id"),
                    correlation_id=transaction_data.get("correlation_id"),
                    multiplier_applied=transaction_data.get("multiplier_applied", 1.0),
                    bonus_applied=transaction_data.get("bonus_applied", 0),
                    is_suspicious=transaction_data.get("is_suspicious", False),
                    transaction_metadata=transaction_data.get("transaction_metadata"),
                    processed_at=datetime.now(timezone.utc),
                )

                session.add(transaction)
                await session.commit()
                await session.refresh(transaction)

                return transaction

            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating points transaction: {e}")
                raise GamificationError(f"Failed to create points transaction: {e}")

    async def get_points_transactions(
        self,
        user_id: int,
        limit: int,
        offset: int,
        transaction_type: Optional[PointsTransactionType],
    ) -> List[PointsTransaction]:
        """Get points transaction history."""
        async with self.async_session() as session:
            try:
                query = select(PointsTransaction).where(
                    PointsTransaction.user_id == user_id
                )

                if transaction_type:
                    query = query.where(
                        PointsTransaction.transaction_type == transaction_type
                    )

                query = (
                    query.order_by(desc(PointsTransaction.created_at))
                    .offset(offset)
                    .limit(limit)
                )

                result = await session.execute(query)
                return result.scalars().all()

            except Exception as e:
                self.logger.error(
                    f"Error getting points transactions for user {user_id}: {e}"
                )
                raise GamificationError(f"Failed to get points transactions: {e}")

    # ================= Achievements =================

    async def get_achievement_definitions(
        self, active_only: bool = True
    ) -> List[AchievementDefinition]:
        """Get all achievement definitions."""
        async with self.async_session() as session:
            try:
                query = select(AchievementDefinition)

                if active_only:
                    query = query.where(AchievementDefinition.is_active == True)

                query = query.order_by(
                    AchievementDefinition.display_order, AchievementDefinition.name
                )

                result = await session.execute(query)
                return result.scalars().all()

            except Exception as e:
                self.logger.error(f"Error getting achievement definitions: {e}")
                raise GamificationError(f"Failed to get achievement definitions: {e}")

    async def create_achievement_definition(
        self, achievement_data: Dict[str, Any]
    ) -> AchievementDefinition:
        """Create a new achievement definition."""
        async with self.async_session() as session:
            try:
                achievement = AchievementDefinition(
                    id=achievement_data["id"],
                    name=achievement_data["name"],
                    description=achievement_data["description"],
                    category=achievement_data["category"],
                    tier=achievement_data["tier"],
                    points_reward=achievement_data.get("points_reward", 0),
                    unlock_criteria=achievement_data["unlock_criteria"],
                    is_secret=achievement_data.get("is_secret", False),
                    is_repeatable=achievement_data.get("is_repeatable", False),
                    badge_url=achievement_data.get("badge_url"),
                    icon_name=achievement_data.get("icon_name"),
                    display_order=achievement_data.get("display_order", 0),
                    is_active=achievement_data.get("is_active", True),
                )

                session.add(achievement)
                await session.commit()
                await session.refresh(achievement)

                return achievement

            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating achievement definition: {e}")
                raise GamificationError(f"Failed to create achievement definition: {e}")

    async def get_user_achievements(
        self, user_id: int, completed_only: bool = False
    ) -> List[UserAchievement]:
        """Get user achievements."""
        async with self.async_session() as session:
            try:
                query = select(UserAchievement).where(
                    UserAchievement.user_id == user_id
                )

                if completed_only:
                    query = query.where(UserAchievement.is_completed == True)

                query = query.order_by(
                    desc(UserAchievement.unlocked_at), UserAchievement.created_at
                )

                result = await session.execute(query)
                return result.scalars().all()

            except Exception as e:
                self.logger.error(f"Error getting user achievements for {user_id}: {e}")
                raise GamificationError(f"Failed to get user achievements: {e}")

    async def create_user_achievement(
        self, achievement_data: Dict[str, Any]
    ) -> UserAchievement:
        """Create a new user achievement record."""
        async with self.async_session() as session:
            try:
                user_achievement = UserAchievement(
                    user_id=achievement_data["user_id"],
                    achievement_id=achievement_data["achievement_id"],
                    progress_current=achievement_data.get("progress_current", 0),
                    progress_required=achievement_data.get("progress_required", 1),
                    is_completed=achievement_data.get("is_completed", False),
                    unlocked_at=achievement_data.get("unlocked_at"),
                    points_awarded=achievement_data.get("points_awarded", 0),
                    unlock_event_id=achievement_data.get("unlock_event_id"),
                )

                session.add(user_achievement)
                await session.commit()
                await session.refresh(user_achievement)

                return user_achievement

            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error creating user achievement: {e}")
                raise GamificationError(f"Failed to create user achievement: {e}")

    async def update_user_achievement(
        self, user_achievement: UserAchievement
    ) -> UserAchievement:
        """Update user achievement progress."""
        async with self.async_session() as session:
            try:
                merged_achievement = await session.merge(user_achievement)
                await session.commit()
                await session.refresh(merged_achievement)

                return merged_achievement

            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error updating user achievement: {e}")
                raise GamificationError(f"Failed to update user achievement: {e}")

    # ================= Streaks =================

    async def get_user_streaks(self, user_id: int) -> List[StreakRecord]:
        """Get user streak records."""
        async with self.async_session() as session:
            try:
                query = (
                    select(StreakRecord)
                    .where(
                        and_(
                            StreakRecord.user_id == user_id,
                            StreakRecord.is_active == True,
                        )
                    )
                    .order_by(StreakRecord.streak_type)
                )

                result = await session.execute(query)
                return result.scalars().all()

            except Exception as e:
                self.logger.error(f"Error getting user streaks for {user_id}: {e}")
                raise GamificationError(f"Failed to get user streaks: {e}")

    async def update_streak_record(self, streak_data: Dict[str, Any]) -> StreakRecord:
        """Update or create streak record."""
        async with self.async_session() as session:
            try:
                # Check if streak record exists
                existing_streak = await session.execute(
                    select(StreakRecord).where(
                        and_(
                            StreakRecord.user_id == streak_data["user_id"],
                            StreakRecord.streak_type == streak_data["streak_type"],
                        )
                    )
                )
                streak_record = existing_streak.scalar_one_or_none()

                if streak_record:
                    # Update existing record
                    for key, value in streak_data.items():
                        if hasattr(streak_record, key):
                            setattr(streak_record, key, value)
                else:
                    # Create new record
                    streak_record = StreakRecord(
                        user_id=streak_data["user_id"],
                        streak_type=streak_data["streak_type"],
                        current_count=streak_data.get("current_count", 0),
                        longest_count=streak_data.get("longest_count", 0),
                        last_activity_date=streak_data.get("last_activity_date"),
                        streak_start_date=streak_data.get("streak_start_date"),
                        last_reset_date=streak_data.get("last_reset_date"),
                        current_multiplier=streak_data.get("current_multiplier", 1.0),
                        milestones_reached=streak_data.get("milestones_reached"),
                        is_active=streak_data.get("is_active", True),
                        freeze_count=streak_data.get("freeze_count", 0),
                    )
                    session.add(streak_record)

                await session.commit()
                await session.refresh(streak_record)

                return streak_record

            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error updating streak record: {e}")
                raise GamificationError(f"Failed to update streak record: {e}")

    # ================= Leaderboards =================

    async def update_leaderboard_entry(
        self, entry_data: Dict[str, Any]
    ) -> LeaderboardEntry:
        """Update or create leaderboard entry."""
        async with self.async_session() as session:
            try:
                # Check if entry exists for this period
                existing_entry = await session.execute(
                    select(LeaderboardEntry).where(
                        and_(
                            LeaderboardEntry.user_id == entry_data["user_id"],
                            LeaderboardEntry.leaderboard_type
                            == entry_data["leaderboard_type"],
                            LeaderboardEntry.period_start == entry_data["period_start"],
                            LeaderboardEntry.period_end == entry_data["period_end"],
                        )
                    )
                )
                entry = existing_entry.scalar_one_or_none()

                if entry:
                    # Update existing entry
                    entry.previous_rank = entry.rank
                    entry.rank = entry_data["rank"]
                    entry.score = entry_data["score"]
                    entry.rank_change = entry_data.get("rank_change")
                    entry.is_personal_best = entry_data.get("is_personal_best", False)
                    entry.rewards_claimed = entry_data.get("rewards_claimed")
                else:
                    # Create new entry
                    entry = LeaderboardEntry(
                        user_id=entry_data["user_id"],
                        leaderboard_type=entry_data["leaderboard_type"],
                        period_start=entry_data["period_start"],
                        period_end=entry_data["period_end"],
                        rank=entry_data["rank"],
                        score=entry_data["score"],
                        previous_rank=entry_data.get("previous_rank"),
                        rank_change=entry_data.get("rank_change"),
                        is_personal_best=entry_data.get("is_personal_best", False),
                        rewards_claimed=entry_data.get("rewards_claimed"),
                    )
                    session.add(entry)

                await session.commit()
                await session.refresh(entry)

                return entry

            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error updating leaderboard entry: {e}")
                raise GamificationError(f"Failed to update leaderboard entry: {e}")

    async def get_leaderboard_entries(
        self,
        leaderboard_type: LeaderboardType,
        period_start: datetime,
        period_end: datetime,
        limit: int,
    ) -> List[LeaderboardEntry]:
        """Get leaderboard entries for a period."""
        async with self.async_session() as session:
            try:
                query = (
                    select(LeaderboardEntry)
                    .where(
                        and_(
                            LeaderboardEntry.leaderboard_type == leaderboard_type,
                            LeaderboardEntry.period_start == period_start,
                            LeaderboardEntry.period_end == period_end,
                        )
                    )
                    .order_by(LeaderboardEntry.rank)
                    .limit(limit)
                )

                result = await session.execute(query)
                return result.scalars().all()

            except Exception as e:
                self.logger.error(f"Error getting leaderboard entries: {e}")
                raise GamificationError(f"Failed to get leaderboard entries: {e}")

    # ================= Analytics and Aggregations =================

    async def get_user_points_total(self, user_id: int) -> int:
        """Get total points for a user."""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(func.sum(PointsTransaction.amount)).where(
                        PointsTransaction.user_id == user_id
                    )
                )
                total = result.scalar()
                return total or 0

            except Exception as e:
                self.logger.error(f"Error getting user points total for {user_id}: {e}")
                return 0

    async def get_achievement_completion_count(self, user_id: int) -> int:
        """Get number of completed achievements for a user."""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(func.count()).where(
                        and_(
                            UserAchievement.user_id == user_id,
                            UserAchievement.is_completed == True,
                        )
                    )
                )
                return result.scalar() or 0

            except Exception as e:
                self.logger.error(f"Error getting achievement count for {user_id}: {e}")
                return 0

    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide statistics."""
        async with self.async_session() as session:
            try:
                # Total users with gamification data
                total_users_result = await session.execute(
                    select(func.count(UserGamification.user_id))
                )
                total_users = total_users_result.scalar() or 0

                # Total points awarded
                total_points_result = await session.execute(
                    select(func.sum(PointsTransaction.amount)).where(
                        PointsTransaction.amount > 0
                    )
                )
                total_points = total_points_result.scalar() or 0

                # Total achievements unlocked
                total_achievements_result = await session.execute(
                    select(func.count()).where(UserAchievement.is_completed == True)
                )
                total_achievements = total_achievements_result.scalar() or 0

                return {
                    "total_users": total_users,
                    "total_points_awarded": total_points,
                    "total_achievements_unlocked": total_achievements,
                }

            except Exception as e:
                self.logger.error(f"Error getting system statistics: {e}")
                return {
                    "total_users": 0,
                    "total_points_awarded": 0,
                    "total_achievements_unlocked": 0,
                }
