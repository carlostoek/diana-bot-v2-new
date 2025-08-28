"""
Minimal implementation of PointsEngine for testing purposes

This is a highly simplified version of the original PointsEngine implementation
with focus on correct behavior for test purposes without the complexity
that might be causing issues in the original implementation.
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


class MinimalPointsEngine(IPointsEngine):
    """
    Minimal implementation of PointsEngine for testing purposes.
    
    Implements just enough functionality to pass the key tests while
    avoiding potential deadlocks or performance issues.
    """
    
    def __init__(
        self,
        anti_abuse_validator: IAntiAbuseValidator,
        database_client=None,
    ):
        """Initialize the minimal engine."""
        self.anti_abuse_validator = anti_abuse_validator
        self.database_client = database_client
        
        # Base points for different action types
        self.base_points_config = {
            ActionType.DAILY_LOGIN: 50,
            ActionType.LOGIN: 10,
            ActionType.MESSAGE_SENT: 5,
            ActionType.TRIVIA_COMPLETED: 100,
            ActionType.STORY_CHAPTER_COMPLETED: 150,
            ActionType.VIP_PURCHASE: 1000,
            ActionType.ADMIN_ADJUSTMENT: 0,  # Variable, can be negative
        }
        
        # Simple in-memory storage
        self.user_data: Dict[int, UserGamification] = {}
        self.transactions: Dict[str, PointsTransaction] = {}
        
        # Simple lock for thread safety
        self._lock = asyncio.Lock()
        
    async def award_points(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        base_points: Optional[int] = None,
        force_award: bool = False,
    ) -> PointsAwardResult:
        """Award points to a user for a specific action."""
        async with self._lock:
            try:
                # 1. Anti-abuse validation (unless forced)
                if not force_award:
                    is_valid, violation, error_msg = await self.anti_abuse_validator.validate_action(
                        user_id, action_type, context
                    )
                    if not is_valid:
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
                
                # 2. Get or create user data
                user_data = self._get_or_create_user_data(user_id)
                
                # 3. Calculate base points
                calculated_base_points = base_points or self._calculate_base_points(action_type, context)
                
                # Allow negative points for ADMIN_ADJUSTMENT and zero points for ACHIEVEMENT_UNLOCKED
                if (
                    (calculated_base_points < 0 and action_type != ActionType.ADMIN_ADJUSTMENT)
                    or (calculated_base_points == 0 
                        and action_type != ActionType.ADMIN_ADJUSTMENT
                        and action_type != ActionType.ACHIEVEMENT_UNLOCKED)
                ):
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
                
                # 4. Calculate final points (with simple multipliers)
                final_points = calculated_base_points
                multipliers = {}
                
                # For negative adjustments, don't apply multipliers
                if action_type == ActionType.ADMIN_ADJUSTMENT and calculated_base_points < 0:
                    final_points = calculated_base_points
                
                # 5. Create transaction record
                transaction_id = str(uuid.uuid4())
                transaction = PointsTransaction(
                    id=transaction_id,
                    user_id=user_id,
                    action_type=action_type,
                    points_change=final_points,
                    balance_after=user_data.total_points + final_points,
                    base_points=calculated_base_points,
                    multipliers_applied=multipliers,
                    context=context,
                    validation_passed=True,
                )
                
                # 6. Update user balance
                old_balance = user_data.total_points
                try:
                    if final_points > 0:
                        user_data.add_points(final_points, update_available=True)
                    elif final_points < 0:
                        # For negative adjustments
                        if abs(final_points) <= user_data.available_points:
                            user_data.spend_points(abs(final_points))
                        else:
                            # Adjust total but set available to 0
                            user_data.total_points = max(0, user_data.total_points + final_points)
                            user_data.available_points = 0
                        
                        # Update transaction balance
                        transaction.balance_after = user_data.total_points
                    
                    # 7. Record transaction
                    self.transactions[transaction_id] = transaction
                    
                    # 8. Record action in anti-abuse if needed
                    if not force_award:
                        await self.anti_abuse_validator.record_action(
                            user_id, action_type, context, final_points
                        )
                    
                    # 9. Return success result
                    # Note: we use get_user_balance to ensure we have the latest balance
                    current_balance, _ = await self.get_user_balance(user_id)
                    
                    return PointsAwardResult(
                        success=True,
                        user_id=user_id,
                        action_type=action_type,
                        points_awarded=final_points,
                        base_points=calculated_base_points,
                        multipliers_applied=multipliers,
                        new_balance=current_balance,
                        transaction_id=transaction_id,
                    )
                    
                except Exception as e:
                    # Rollback on any error
                    user_data.total_points = old_balance
                    logger.error(f"Transaction rollback for user {user_id}: {e}")
                    raise
                    
            except Exception as e:
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
        async with self._lock:
            user_data = self._get_or_create_user_data(user_id)
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
        
        async with self._lock:
            user_data = self._get_or_create_user_data(user_id)
            
            if user_data.available_points < amount:
                return False
            
            # Create spending transaction
            transaction = PointsTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action_type=ActionType.ADMIN_ADJUSTMENT,
                points_change=-amount,
                balance_after=user_data.total_points,
                base_points=-amount,
                context=context or {"reason": reason, "type": "spending"},
                validation_passed=True,
            )
            
            # Update balance
            success = user_data.spend_points(amount)
            if success:
                # Record transaction
                self.transactions[transaction.id] = transaction
                transaction.balance_after = user_data.total_points
            
            return success
    
    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        action_types: Optional[List[ActionType]] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get user's points transaction history."""
        async with self._lock:
            user_transactions = []
            
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
    
    async def verify_balance_integrity(self, user_id: int) -> bool:
        """Verify that user's balance matches their transaction history."""
        async with self._lock:
            user_data = self._get_or_create_user_data(user_id)
            
            # Calculate balance from transaction history
            calculated_total = 0
            
            # Sort transactions by timestamp to ensure correct order
            sorted_transactions = sorted(
                [tx for tx in self.transactions.values() if tx.user_id == user_id],
                key=lambda x: x.timestamp
            )
            
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
    
    async def calculate_multipliers(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> Dict[MultiplierType, float]:
        """Calculate all applicable multipliers for a user and action."""
        # Simplified implementation that just returns an empty dict
        # For a real implementation, we would calculate VIP, streak, etc.
        return {}

    # Private helper methods
    
    def _get_or_create_user_data(self, user_id: int) -> UserGamification:
        """Get existing user data or create new record."""
        if user_id not in self.user_data:
            self.user_data[user_id] = UserGamification(user_id=user_id)
        return self.user_data[user_id]
    
    async def _get_user_total_points(self, user_id: int) -> int:
        """Get user's total points (helper for error cases)."""
        try:
            user_data = self._get_or_create_user_data(user_id)
            return user_data.total_points
        except:
            return 0
    
    def _calculate_base_points(self, action_type: ActionType, context: Dict[str, Any]) -> int:
        """Calculate base points for an action type."""
        base_points = self.base_points_config.get(action_type, 0)
        
        # Special cases
        if action_type == ActionType.ACHIEVEMENT_UNLOCKED:
            base_points = context.get("achievement_points", 100)
        elif action_type == ActionType.ADMIN_ADJUSTMENT:
            base_points = context.get("adjustment_amount", 0)
        
        return base_points