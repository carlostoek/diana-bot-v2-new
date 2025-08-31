from sqlalchemy.orm import Session
from typing import List, Optional

from .interfaces import IGamificationRepository
from .models import (
    UserGamification,
    PointsTransaction,
    Achievement,
    UserAchievement,
)

class GamificationRepository(IGamificationRepository):
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_user_gamification_stats(self, user_id: int) -> Optional[UserGamification]:
        return self.db.query(UserGamification).filter_by(user_id=user_id).first()

    def create_or_update_user_gamification_stats(self, stats: UserGamification) -> UserGamification:
        self.db.merge(stats)
        self.db.commit()
        return stats

    def create_points_transaction(self, transaction: PointsTransaction) -> PointsTransaction:
        self.db.add(transaction)
        self.db.commit()
        return transaction

    def get_achievements(self) -> List[Achievement]:
        return self.db.query(Achievement).all()

    def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        return self.db.query(UserAchievement).filter_by(user_id=user_id).all()

    def grant_user_achievement(self, user_achievement: UserAchievement) -> UserAchievement:
        self.db.add(user_achievement)
        self.db.commit()
        return user_achievement
