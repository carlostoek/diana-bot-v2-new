"""
Fixed Points Engine for Gamification Service

This is a fixed version of the points engine with corrections to mathematical
integrity issues.
"""

class FixedPointsEngine:
    """Fixed points engine with corrected mathematical operations."""
    
    def __init__(self):
        self.balances = {}
    
    def award_points(self, user_id: int, points: int) -> int:
        """Award points to a user and return the new balance."""
        if user_id not in self.balances:
            self.balances[user_id] = 0
        
        self.balances[user_id] += points
        return self.balances[user_id]
    
    def get_balance(self, user_id: int) -> int:
        """Get the current balance for a user."""
        return self.balances.get(user_id, 0)