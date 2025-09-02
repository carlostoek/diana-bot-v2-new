import logging
from datetime import datetime, timedelta
from src.domain.models import User, Wallet, Transaction, UserAchievement
from src.infrastructure.uow import IUnitOfWork
from src.infrastructure.event_bus import EventPublisher
from src.domain.events import AchievementUnlocked

logger = logging.getLogger(__name__)

class GamificationService:
    """
    Service for handling all gamification logic.
    """

    def __init__(self, event_publisher: EventPublisher):
        self._event_publisher = event_publisher

    async def add_points(self, uow: IUnitOfWork, user_id: int, amount: int, description: str) -> Wallet:
        """Adds points to a user's wallet within a unit of work."""
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        wallet = await uow.wallets.get_by_user_id(user_id)
        if not wallet:
            wallet = Wallet(user_id=user_id, balance=0)
            await uow.wallets.add(wallet)

        wallet.balance += amount
        await uow.wallets.add(wallet)

        transaction = Transaction(user_id=user_id, amount=amount, description=description)
        await uow.transactions.add(transaction)

        logger.info(f"Prepared to add {amount} points to user {user_id} for: {description}")
        return wallet

    async def spend_points(self, uow: IUnitOfWork, user_id: int, amount: int, description: str) -> Wallet:
        """Spends points from a user's wallet within a unit of work."""
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        wallet = await uow.wallets.get_by_user_id(user_id)
        if not wallet or wallet.balance < amount:
            raise ValueError("Insufficient balance.")

        wallet.balance -= amount
        await uow.wallets.add(wallet)

        transaction = Transaction(user_id=user_id, amount=-amount, description=description)
        await uow.transactions.add(transaction)

        logger.info(f"Prepared to spend {amount} points from user {user_id} for: {description}")
        return wallet

    async def update_daily_streak(self, uow: IUnitOfWork, user: User) -> None:
        """Updates the user's daily activity streak within a unit of work."""
        now = datetime.utcnow()
        today = now.date()

        if user.last_active_at:
            last_active_day = user.last_active_at.date()
            if last_active_day == today:
                return

            yesterday = today - timedelta(days=1)
            if last_active_day == yesterday:
                user.current_streak += 1
                if user.current_streak > user.max_streak:
                    user.max_streak = user.current_streak
            else:
                user.current_streak = 1
        else:
            user.current_streak = 1
            user.max_streak = 1

        user.last_active_at = now
        await uow.users.add(user)

    async def get_wallet_by_user_id(self, uow: IUnitOfWork, user_id: int) -> Wallet:
        """Gets a user's wallet within a unit of work."""
        wallet = await uow.wallets.get_by_user_id(user_id)
        if not wallet:
            wallet = Wallet(user_id=user_id, balance=0)
            await uow.wallets.add(wallet)
        return wallet

    async def unlock_achievement(self, uow: IUnitOfWork, user_id: int, achievement_name: str) -> bool:
        """
        Unlocks an achievement for a user within a unit of work.
        Returns True if the achievement was newly unlocked, False otherwise.
        """
        achievement = await uow.achievements.get_by_name(achievement_name)
        if not achievement:
            logger.warning(f"Achievement '{achievement_name}' not found.")
            return False

        already_unlocked = await uow.user_achievements.find_by_user_and_achievement(
            user_id=user_id, achievement_id=achievement.id
        )
        if already_unlocked:
            return False

        user_achievement = UserAchievement(user_id=user_id, achievement_id=achievement.id)
        await uow.user_achievements.add(user_achievement)

        if achievement.reward_points > 0:
            await self.add_points(
                uow=uow,
                user_id=user_id,
                amount=achievement.reward_points,
                description=f"Achievement unlocked: {achievement.name}",
            )

        event = AchievementUnlocked(
            payload={
                "user_id": user_id,
                "achievement_name": achievement.name,
                "reward_points": achievement.reward_points,
            }
        )
        await self._event_publisher.publish("user_events", event)

        logger.info(f"User {user_id} unlocked achievement: {achievement.name}")
        return True
