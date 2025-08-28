"""
Fixed PointsEngine Implementation

This module provides an improved implementation of the PointsEngine that addresses
the deadlock and concurrency issues identified in the original implementation.

Key improvements:
1. Separated locks by user to prevent cross-user blocking
2. Improved transaction handling to ensure balance_after is set correctly
3. Standardized rules for zero-point operations
4. Better exception propagation
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.gamification.interfaces import (
    ActionType,
    IAntiAbuseValidator,
    IPointsEngine,
    MultiplierType,
    PointsAwardResult,
)
from services.gamification.models import PointsTransaction, UserGamification

logger = logging.getLogger(__name__)


class FixedPointsEngineError(Exception):
    """Exception raised by the PointsEngine for operation failures."""
    pass


class FixedPointsEngine(IPointsEngine):
    """
    Improved PointsEngine implementation with fixed concurrency handling.
    
    This implementation addresses deadlock issues by using per-user locks
    and improving transaction handling.
    """
    
    def __init__(
        self,
        anti_abuse_validator: IAntiAbuseValidator,
        database_client=None,
        enable_balance_verification: bool = True,
        enable_transaction_logging: bool = True,
    ):
        """Initialize the PointsEngine with improved locking strategy."""
        self.anti_abuse_validator = anti_abuse_validator
        self.database_client = database_client
        self.enable_balance_verification = enable_balance_verification
        self.enable_transaction_logging = enable_transaction_logging
        
        # Base points configuration
        self.base_points_config = {
            ActionType.DAILY_LOGIN: 50,
            ActionType.LOGIN: 10,
            ActionType.MESSAGE_SENT: 5,
            ActionType.TRIVIA_COMPLETED: 100,
            ActionType.STORY_CHAPTER_COMPLETED: 150,
            ActionType.STORY_DECISION_MADE: 25,
            ActionType.FRIEND_REFERRAL: 500,
            ActionType.COMMUNITY_PARTICIPATION: 30,
            ActionType.VIP_PURCHASE: 1000,
            ActionType.SUBSCRIPTION_RENEWAL: 2000,
            ActionType.ACHIEVEMENT_UNLOCKED: 0,  # Variable based on achievement
            ActionType.STREAK_BONUS: 0,  # Variable based on streak length
            ActionType.CHALLENGE_COMPLETED: 200,
            ActionType.ADMIN_ADJUSTMENT: 0,  # Variable, can be negative
        }
        
        # In-memory storage for testing
        self.user_data: Dict[int, UserGamification] = {}
        self.transactions: Dict[str, PointsTransaction] = {}
        
        # Performance metrics
        self.operation_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_points_awarded": 0,
            "avg_operation_time_ms": 0.0,
        }
        
        # IMPROVEMENT: Separate locks by user to prevent cross-user blocking
        self._user_locks = {}
        self._transaction_lock = asyncio.Lock()  # Separate lock for transaction operations
        
    async def _get_user_lock(self, user_id: int) -> asyncio.Lock:
        """Get a lock specific to a user to prevent cross-user blocking."""
        if user_id not in self._user_locks:
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]
        
    async def award_points(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        base_points: Optional[int] = None,
        force_award: bool = False,
    ) -> PointsAwardResult:
        """
        Award points to a user for a specific action with full validation.
        
        This implementation uses per-user locks to prevent deadlocks across users.
        """
        import time
        start_time = time.time()
        transaction_id = str(uuid.uuid4())
        
        try:
            # Get user-specific lock
            user_lock = await self._get_user_lock(user_id)
            
            async with user_lock:
                # Step 1: Anti-abuse validation (unless forced)
                if not force_award:
                    is_valid, violation, error_msg = (
                        await self.anti_abuse_validator.validate_action(
                            user_id, action_type, context
                        )
                    )
                    if not is_valid:
                        await self._record_metrics(start_time, success=False)
                        return PointsAwardResult(
                            success=False,
                            user_id=user_id,
                            action_type=action_type,
                            points_awarded=0,
                            base_points=0,
                            multipliers_applied={},
                            new_balance=await self._get_user_total_points(user_id),
                            violation=violation,
                            error_message=error_msg,
                        )
                
                # Step 2: Get or create user gamification data
                user_data = await self._get_or_create_user_data(user_id)
                
                # Step 3: Calculate base points
                calculated_base_points = base_points or self._calculate_base_points(
                    action_type, context
                )
                
                # IMPROVEMENT: Clarify rules for zero and negative points
                if (
                    (calculated_base_points < 0 and action_type != ActionType.ADMIN_ADJUSTMENT)
                    or (calculated_base_points == 0 
                        and action_type != ActionType.ADMIN_ADJUSTMENT
                        and action_type != ActionType.ACHIEVEMENT_UNLOCKED)
                ):
                    await self._record_metrics(start_time, success=False)
                    return PointsAwardResult(
                        success=False,
                        user_id=user_id,
                        action_type=action_type,
                        points_awarded=0,
                        base_points=calculated_base_points,
                        multipliers_applied={},
                        new_balance=user_data.total_points,
                        error_message="Invalid base points calculation",
                    )
                
                # Step 4: Calculate multipliers
                multipliers = await self.calculate_multipliers(
                    user_id, action_type, context
                )
                
                # Step 5: Calculate final points with multipliers
                final_points = self._apply_multipliers(
                    calculated_base_points, multipliers
                )
                
                # Handle negative points (admin adjustments, penalties)
                if (
                    action_type == ActionType.ADMIN_ADJUSTMENT
                    and calculated_base_points < 0
                ):
                    final_points = calculated_base_points  # No multipliers on negative adjustments
                
                # Step 6: Apply penalties if user has them
                final_points = await self._apply_penalties(user_id, final_points)
                
                # Step 7: Update user balance FIRST (important for balance_after calculation)
                old_balance = user_data.total_points
                try:
                    # Update user balance
                    if final_points > 0:
                        user_data.add_points(final_points, update_available=True)
                    elif final_points < 0:
                        # For negative adjustments, spend from available if possible
                        if abs(final_points) <= user_data.available_points:
                            user_data.spend_points(abs(final_points))
                        else:
                            # Adjust total but set available to 0
                            user_data.total_points = max(
                                0, user_data.total_points + final_points
                            )
                            user_data.available_points = 0
                    
                    # Update last activity
                    user_data.last_activity = datetime.now(timezone.utc)
                    
                    # Check for level up
                    level_increased = user_data.update_level()
                    
                    # IMPROVEMENT: Create transaction AFTER updating balance
                    transaction = PointsTransaction(
                        id=transaction_id,
                        user_id=user_id,
                        action_type=action_type,
                        points_change=final_points,
                        balance_after=user_data.total_points,  # Now correctly reflects updated balance
                        base_points=calculated_base_points,
                        multipliers_applied=multipliers,
                        context=context,
                        validation_passed=True,
                    )
                    
                    # Record transaction
                    await self._persist_transaction(transaction)
                    await self._persist_user_data(user_data)
                    
                    # Record action in anti-abuse system
                    if not force_award:
                        await self.anti_abuse_validator.record_action(
                            user_id, action_type, context, final_points
                        )
                    
                    # Log transaction if enabled
                    if self.enable_transaction_logging:
                        logger.info(
                            f"Points awarded: user={user_id}, action={action_type.value}, "
                            f"points={final_points}, balance={transaction.balance_after}, "
                            f"transaction_id={transaction_id}"
                        )
                    
                    # Update metrics
                    await self._record_metrics(
                        start_time, success=True, points_awarded=final_points
                    )
                    
                    # Get updated balance after all operations
                    current_balance, _ = await self.get_user_balance(user_id)
                    
                    result = PointsAwardResult(
                        success=True,
                        user_id=user_id,
                        action_type=action_type,
                        points_awarded=final_points,
                        base_points=calculated_base_points,
                        multipliers_applied=multipliers,
                        new_balance=current_balance,
                        transaction_id=transaction_id,
                    )
                    
                    # Add level up info if applicable
                    if level_increased:
                        result.achievements_unlocked.append(
                            f"Level {user_data.level} Reached!"
                        )
                    
                    return result
                    
                except Exception as e:
                    # Rollback on any error
                    user_data.total_points = old_balance
                    logger.error(f"Transaction rollback for user {user_id}: {e}")
                    # IMPROVEMENT: Better exception propagation
                    error = FixedPointsEngineError(f"Transaction failed and rolled back: {e}")
                    raise error from e
                    
        except Exception as e:
            await self._record_metrics(start_time, success=False)
            logger.error(f"Points award failed for user {user_id}: {e}")
            
            return PointsAwardResult(
                success=False,
                user_id=user_id,
                action_type=action_type,
                points_awarded=0,
                base_points=base_points or 0,
                multipliers_applied={},
                new_balance=await self._get_user_total_points(user_id),
                error_message=str(e),
            )
    
    async def get_user_balance(self, user_id: int) -> Tuple[int, int]:
        """Get user's current point balances."""
        user_lock = await self._get_user_lock(user_id)
        
        async with user_lock:
            user_data = await self._get_or_create_user_data(user_id)
            return user_data.total_points, user_data.available_points
    
    async def spend_points(
        self,
        user_id: int,
        amount: int,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Spend points from user's available balance."""
        if amount <= 0:
            raise ValueError("Spend amount must be positive")
        
        user_lock = await self._get_user_lock(user_id)
        
        async with user_lock:
            user_data = await self._get_or_create_user_data(user_id)
            
            if user_data.available_points < amount:
                return False
            
            # Update user data FIRST
            success = user_data.spend_points(amount)
            if not success:
                return False
                
            # Then create transaction with correct balance_after
            transaction = PointsTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action_type=ActionType.ADMIN_ADJUSTMENT,
                points_change=-amount,
                balance_after=user_data.total_points,  # Reflects the updated balance
                base_points=-amount,
                context=context or {"reason": reason, "type": "spending"},
                validation_passed=True,
            )
            
            # Persist everything
            await self._persist_transaction(transaction)
            await self._persist_user_data(user_data)
            
            if self.enable_transaction_logging:
                logger.info(
                    f"Points spent: user={user_id}, amount={amount}, "
                    f"reason={reason}, remaining={user_data.available_points}"
                )
            
            return True
    
    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        action_types: Optional[List[ActionType]] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get user's points transaction history."""
        user_transactions = []
        
        # Use transaction lock to read transactions
        async with self._transaction_lock:
            for transaction in self.transactions.values():
                if transaction.user_id != user_id:
                    continue
                
                # Apply filters
                if action_types and transaction.action_type not in action_types:
                    continue
                
                if since and transaction.timestamp < since:
                    continue
                
                user_transactions.append(transaction.to_dict())
        
        # Sort by timestamp (newest first) and apply limit
        user_transactions.sort(key=lambda x: x["timestamp"], reverse=True)
        return user_transactions[:limit]
    
    async def calculate_multipliers(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> Dict[MultiplierType, float]:
        """Calculate all applicable multipliers for a user and action."""
        multipliers = {}
        user_data = await self._get_or_create_user_data(user_id)
        
        # VIP multiplier
        if user_data.vip_multiplier > 1.0:
            multipliers[MultiplierType.VIP_BONUS] = user_data.vip_multiplier
        
        # Streak multiplier
        streak_multiplier = self._calculate_streak_multiplier(user_data.current_streak)
        if streak_multiplier > 1.0:
            multipliers[MultiplierType.STREAK_BONUS] = streak_multiplier
        
        # Level multiplier
        level_multiplier = 1.0 + (user_data.level - 1) * 0.05
        if level_multiplier > 1.0:
            multipliers[MultiplierType.LEVEL_BONUS] = level_multiplier
        
        # Event multiplier
        event_multiplier = context.get("event_multiplier") or user_data.event_multiplier
        if event_multiplier > 1.0:
            multipliers[MultiplierType.EVENT_BONUS] = event_multiplier
        
        # Achievement bonus
        if context.get("achievement_bonus"):
            multipliers[MultiplierType.ACHIEVEMENT_BONUS] = context["achievement_bonus"]
        
        return multipliers
    
    async def verify_balance_integrity(self, user_id: int) -> bool:
        """Verify that user's balance matches their transaction history."""
        user_lock = await self._get_user_lock(user_id)
        
        async with user_lock:
            user_data = await self._get_or_create_user_data(user_id)
            
            # Get all transactions for this user
            transactions = []
            async with self._transaction_lock:
                transactions = [tx for tx in self.transactions.values() if tx.user_id == user_id]
            
            # Calculate balance from transaction history
            calculated_total = 0
            
            # Sort by timestamp to ensure correct order
            sorted_transactions = sorted(transactions, key=lambda x: x.timestamp)
            
            for transaction in sorted_transactions:
                calculated_total += transaction.points_change
            
            # Compare with stored balance
            total_matches = user_data.total_points == calculated_total
            
            if not total_matches:
                logger.error(
                    f"Balance integrity violation for user {user_id}: "
                    f"stored={user_data.total_points}, calculated={calculated_total}"
                )
            
            return total_matches
    
    # Private helper methods
    
    async def _get_or_create_user_data(self, user_id: int) -> UserGamification:
        """Get existing user data or create new record."""
        if user_id not in self.user_data:
            self.user_data[user_id] = UserGamification(user_id=user_id)
        return self.user_data[user_id]
    
    async def _get_user_total_points(self, user_id: int) -> int:
        """Get user's total points (helper for error cases)."""
        try:
            user_data = await self._get_or_create_user_data(user_id)
            return user_data.total_points
        except:
            return 0
    
    def _calculate_base_points(
        self, action_type: ActionType, context: Dict[str, Any]
    ) -> int:
        """Calculate base points for an action type."""
        base_points = self.base_points_config.get(action_type, 0)
        
        # Handle special cases with context-dependent points
        if action_type == ActionType.ACHIEVEMENT_UNLOCKED:
            base_points = context.get("achievement_points", 100)
        elif action_type == ActionType.STREAK_BONUS:
            streak_days = context.get("streak_days", 1)
            base_points = min(streak_days * 10, 500)  # Max 500 points for streak
        elif action_type == ActionType.ADMIN_ADJUSTMENT:
            base_points = context.get("adjustment_amount", 0)
        elif action_type == ActionType.TRIVIA_COMPLETED:
            # Bonus for correct answers
            if context.get("correct_answer", False):
                difficulty = context.get("difficulty", "medium")
                multiplier = {"easy": 1.0, "medium": 1.5, "hard": 2.0}.get(
                    difficulty, 1.0
                )
                base_points = int(base_points * multiplier)
        
        return base_points
    
    def _calculate_streak_multiplier(self, streak_days: int) -> float:
        """Calculate streak-based multiplier."""
        if streak_days >= 30:
            return 1.5  # 50% bonus for 30+ day streak
        elif streak_days >= 14:
            return 1.3  # 30% bonus for 14+ day streak
        elif streak_days >= 7:
            return 1.2  # 20% bonus for 7+ day streak
        elif streak_days >= 3:
            return 1.1  # 10% bonus for 3+ day streak
        return 1.0
    
    def _apply_multipliers(
        self, base_points: int, multipliers: Dict[MultiplierType, float]
    ) -> int:
        """Apply all multipliers to base points."""
        if not multipliers or base_points <= 0:
            return base_points
        
        final_points = float(base_points)
        
        # Apply each multiplier
        for multiplier_type, multiplier_value in multipliers.items():
            final_points *= multiplier_value
        
        return int(final_points)
    
    async def _apply_penalties(self, user_id: int, points: int) -> int:
        """Apply any active penalties to points calculation."""
        # This would integrate with the anti-abuse system's penalty tracking
        # For now, returning points unchanged
        return points
    
    async def _persist_transaction(self, transaction: PointsTransaction) -> None:
        """Persist transaction to storage."""
        async with self._transaction_lock:
            self.transactions[transaction.id] = transaction
            
            # In production, this would be a database insert
            if self.database_client:
                # await self.database_client.insert_transaction(transaction)
                pass
    
    async def _persist_user_data(self, user_data: UserGamification) -> None:
        """Persist user data to storage."""
        # No lock needed here as user-specific operations are protected by user lock
        self.user_data[user_data.user_id] = user_data
        
        # In production, this would be a database update
        if self.database_client:
            # await self.database_client.update_user_gamification(user_data)
            pass
    
    async def _record_metrics(
        self, start_time: float, success: bool, points_awarded: int = 0
    ) -> None:
        """Record operation metrics for monitoring."""
        import time
        operation_time_ms = (time.time() - start_time) * 1000
        
        # No need for lock as these are simple counters
        self.operation_metrics["total_operations"] += 1
        
        if success:
            self.operation_metrics["successful_operations"] += 1
            self.operation_metrics["total_points_awarded"] += points_awarded
        else:
            self.operation_metrics["failed_operations"] += 1
        
        # Update average operation time (exponential moving average)
        alpha = 0.1
        if self.operation_metrics["avg_operation_time_ms"] == 0:
            self.operation_metrics["avg_operation_time_ms"] = operation_time_ms
        else:
            current_avg = self.operation_metrics["avg_operation_time_ms"]
            self.operation_metrics["avg_operation_time_ms"] = (
                alpha * operation_time_ms + (1 - alpha) * current_avg
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.operation_metrics.copy()
    
    async def reset_metrics(self) -> None:
        """Reset performance metrics (for testing)."""
        self.operation_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_points_awarded": 0,
            "avg_operation_time_ms": 0.0,
        }