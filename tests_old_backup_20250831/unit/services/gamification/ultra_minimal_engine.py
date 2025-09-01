"""
Ultra-Minimal Points Engine

This is an extremely simplified version of the PointsEngine with no locking,
no transactions, and minimal logic - designed only for basic testing purposes.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from services.gamification.interfaces import ActionType, IPointsEngine, PointsAwardResult


class UltraMinimalEngine(IPointsEngine):
    """
    Ultra minimal implementation of PointsEngine for basic testing.
    
    Implements just enough to run simple tests with no locks or complex logic.
    """
    
    def __init__(self, anti_abuse_validator=None):
        """Initialize with minimal dependencies."""
        self.anti_abuse_validator = anti_abuse_validator
        self.balances = {}  # user_id -> (total, available)
        self.transactions = []  # List of simple dicts
    
    async def award_points(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        base_points: Optional[int] = None,
        force_award: bool = False,
    ) -> PointsAwardResult:
        """Award points with minimal logic and no locking."""
        # Default points based on action
        if base_points is None:
            base_points = self._get_default_points(action_type)
        
        # Record transaction
        transaction = {
            "user_id": user_id,
            "action_type": action_type,
            "points_change": base_points,
            "timestamp": datetime.now(),
            "context": context
        }
        self.transactions.append(transaction)
        
        # Update balance
        if user_id not in self.balances:
            self.balances[user_id] = (0, 0)
        
        total, available = self.balances[user_id]
        new_total = total + base_points
        new_available = available + base_points
        
        # Make sure we don't go negative
        if new_total < 0:
            new_total = 0
        if new_available < 0:
            new_available = 0
            
        self.balances[user_id] = (new_total, new_available)
        
        # Create result
        result = PointsAwardResult(
            success=True,
            user_id=user_id,
            action_type=action_type,
            points_awarded=base_points,
            base_points=base_points,
            multipliers_applied={},
            new_balance=new_total,
        )
        
        return result
    
    async def get_user_balance(self, user_id: int) -> Tuple[int, int]:
        """Get user balance with minimal logic."""
        if user_id not in self.balances:
            return (0, 0)
        return self.balances[user_id]
    
    async def spend_points(
        self,
        user_id: int,
        amount: int,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Spend points with minimal logic."""
        if amount <= 0:
            raise ValueError("Spend amount must be positive")
        
        if user_id not in self.balances:
            return False
        
        total, available = self.balances[user_id]
        
        if available < amount:
            return False
        
        # Update balance
        new_available = available - amount
        self.balances[user_id] = (total, new_available)
        
        # Record transaction
        transaction = {
            "user_id": user_id,
            "action_type": ActionType.ADMIN_ADJUSTMENT,
            "points_change": -amount,
            "timestamp": datetime.now(),
            "context": context or {"reason": reason}
        }
        self.transactions.append(transaction)
        
        return True
    
    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        action_types: Optional[List[ActionType]] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get user's transaction history with minimal logic."""
        user_transactions = [
            tx for tx in self.transactions 
            if tx["user_id"] == user_id
        ]
        
        # Apply filters
        if action_types:
            user_transactions = [
                tx for tx in user_transactions
                if tx["action_type"] in action_types
            ]
        
        if since:
            user_transactions = [
                tx for tx in user_transactions
                if tx["timestamp"] >= since
            ]
        
        # Sort by timestamp (newest first) and apply limit
        user_transactions.sort(key=lambda x: x["timestamp"], reverse=True)
        return user_transactions[:limit]
    
    async def calculate_multipliers(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        """No multipliers in this ultra minimal implementation."""
        return {}
    
    async def verify_balance_integrity(self, user_id: int) -> bool:
        """Verify balance integrity with minimal logic."""
        if user_id not in self.balances:
            return True
        
        total, _ = self.balances[user_id]
        
        # Calculate from transactions
        user_transactions = [tx for tx in self.transactions if tx["user_id"] == user_id]
        calculated_total = sum(tx["points_change"] for tx in user_transactions)
        
        # Don't allow negative balance in calculation
        if calculated_total < 0:
            calculated_total = 0
            
        return total == calculated_total
    
    def _get_default_points(self, action_type: ActionType) -> int:
        """Get default points for an action type."""
        points_map = {
            ActionType.DAILY_LOGIN: 50,
            ActionType.LOGIN: 10,
            ActionType.MESSAGE_SENT: 5,
            ActionType.TRIVIA_COMPLETED: 100,
            ActionType.VIP_PURCHASE: 1000,
            ActionType.ADMIN_ADJUSTMENT: 0,
        }
        return points_map.get(action_type, 10)  # Default 10 points