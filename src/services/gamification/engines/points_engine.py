"""
Points Engine for Gamification System
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..interfaces import (
    ActionType,
    AntiAbuseViolation,
    IAntiAbuseValidator,
    IPointsEngine,
    MultiplierType,
    PointsAwardResult,
    IGamificationRepository,
)
from ..models import PointsTransaction, UserGamification

# Configure logging
logger = logging.getLogger(__name__)


class PointsEngineError(Exception):
    """Exception raised by the PointsEngine for operation failures."""
    pass


class PointsEngine(IPointsEngine):
    def __init__(
        self,
        anti_abuse_validator: IAntiAbuseValidator,
        repository: IGamificationRepository,
        enable_balance_verification: bool = True,
        enable_transaction_logging: bool = True,
    ):
        self.anti_abuse_validator = anti_abuse_validator
        self.repository = repository
        self.enable_balance_verification = enable_balance_verification
        self.enable_transaction_logging = enable_transaction_logging

        self.base_points_config = {
            ActionType.DAILY_LOGIN: 50,
            ActionType.LOGIN: 10,
            ActionType.MESSAGE_SENT: 5,
        }
        self.operation_metrics = {}

    async def _get_or_create_user_data(self, user_id: int) -> UserGamification:
        stats = self.repository.get_user_gamification_stats(user_id)
        if not stats:
            stats = UserGamification(user_id=user_id)
            self.repository.create_or_update_user_gamification_stats(stats)
        return stats

    async def award_points(
        self,
        user_id: int,
        action_type: ActionType,
        context: Dict[str, Any],
        base_points: Optional[int] = None,
        force_award: bool = False,
    ) -> PointsAwardResult:
        user_data = await self._get_or_create_user_data(user_id)

        calculated_base_points = base_points if base_points is not None else self.base_points_config.get(action_type, 0)
        multipliers = await self.calculate_multipliers(user_id, action_type, context)
        final_points = self._apply_multipliers(calculated_base_points, multipliers)

        transaction = PointsTransaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action_type=action_type.value,
            points_change=final_points,
            balance_after=(user_data.total_points or 0) + final_points,
            base_points=calculated_base_points,
            multipliers_applied={k.value: v for k, v in multipliers.items()},
            context=context,
        )

        user_data.total_points = (user_data.total_points or 0) + final_points
        user_data.available_points = (user_data.available_points or 0) + final_points
        user_data.last_activity = datetime.now(timezone.utc)

        self.repository.create_points_transaction(transaction)
        self.repository.create_or_update_user_gamification_stats(user_data)

        return PointsAwardResult(
            success=True, user_id=user_id, action_type=action_type,
            points_awarded=final_points, base_points=calculated_base_points,
            multipliers_applied=multipliers, new_balance=transaction.balance_after,
            transaction_id=transaction.id,
        )

    async def get_user_balance(self, user_id: int) -> Tuple[int, int]:
        user_data = await self._get_or_create_user_data(user_id)
        return user_data.total_points or 0, user_data.available_points or 0

    async def calculate_multipliers(self, user_id: int, action_type: ActionType, context: Dict[str, Any]) -> Dict[MultiplierType, float]:
        return {}

    def _apply_multipliers(self, base_points: int, multipliers: Dict[MultiplierType, float]) -> int:
        return base_points

    async def spend_points(self, user_id: int, amount: int, reason: str, context: Optional[Dict[str, Any]] = None) -> bool:
        raise NotImplementedError
    async def get_transaction_history(self, user_id: int, limit: int = 50, action_types: Optional[List[ActionType]] = None, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError
    async def verify_balance_integrity(self, user_id: int) -> bool:
        raise NotImplementedError
