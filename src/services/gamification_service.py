import logging
from datetime import datetime, timedelta
from src.domain.models import User, Wallet, Transaction, UserAchievement
from src.infrastructure.repositories import (
    UserRepository,
    WalletRepository,
    TransactionRepository,
    AchievementRepository,
    UserAchievementRepository,
)
from src.infrastructure.event_bus import EventPublisher
from src.domain.events import AchievementUnlocked

logger = logging.getLogger(__name__)

class GamificationService:
    """
    Service for handling all gamification logic.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        wallet_repo: WalletRepository,
        transaction_repo: TransactionRepository,
        achievement_repo: AchievementRepository,
        user_achievement_repo: UserAchievementRepository,
        event_publisher: EventPublisher,
    ):
        self._user_repo = user_repo
        self._wallet_repo = wallet_repo
        self._transaction_repo = transaction_repo
        self._achievement_repo = achievement_repo
        self._user_achievement_repo = user_achievement_repo
        self._event_publisher = event_publisher

    async def add_points(self, user_id: int, amount: int, description: str) -> Wallet:
        """Adds points to a user's wallet."""
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        wallet = await self._wallet_repo.get_by_user_id(user_id)
        if not wallet:
            # Create a wallet if it doesn't exist
            wallet = Wallet(user_id=user_id, balance=0)
            await self._wallet_repo.add(wallet)

        wallet.balance += amount
        await self._wallet_repo.add(wallet)

        transaction = Transaction(user_id=user_id, amount=amount, description=description)
        await self._transaction_repo.add(transaction)

        logger.info(f"Added {amount} points to user {user_id} for: {description}")
        return wallet

    async def spend_points(self, user_id: int, amount: int, description: str) -> Wallet:
        """Spends points from a user's wallet."""
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        wallet = await self._wallet_repo.get_by_user_id(user_id)
        if not wallet or wallet.balance < amount:
            raise ValueError("Insufficient balance.")

        wallet.balance -= amount
        await self._wallet_repo.add(wallet)

        transaction = Transaction(user_id=user_id, amount=-amount, description=description)
        await self._transaction_repo.add(transaction)

        logger.info(f"User {user_id} spent {amount} points for: {description}")
        return wallet

    async def update_daily_streak(self, user: User) -> None:
        """Updates the user's daily activity streak."""
        now = datetime.utcnow()
        today = now.date()

        if user.last_active_at:
            last_active_day = user.last_active_at.date()
            if last_active_day == today:
                # Already active today, do nothing
                return

            yesterday = today - timedelta(days=1)
            if last_active_day == yesterday:
                # Continued streak
                user.current_streak += 1
                if user.current_streak > user.max_streak:
                    user.max_streak = user.current_streak
                logger.info(f"User {user.id} continued streak: {user.current_streak} days.")
            else:
                # Streak broken
                user.current_streak = 1
                logger.info(f"User {user.id} streak broken. Reset to 1.")
        else:
            # First activity
            user.current_streak = 1
            user.max_streak = 1
            logger.info(f"User {user.id} started their first streak.")

        user.last_active_at = now
        await self._user_repo.add(user)

    async def get_wallet_by_user_id(self, user_id: int) -> Wallet:
        """Gets a user's wallet, creating one if it doesn't exist."""
        wallet = await self._wallet_repo.get_by_user_id(user_id)
        if not wallet:
            wallet = Wallet(user_id=user_id, balance=0)
            await self._wallet_repo.add(wallet)
        return wallet

    async def unlock_achievement(self, user_id: int, achievement_name: str) -> bool:
        """
        Unlocks an achievement for a user if they haven't already.
        Returns True if the achievement was newly unlocked, False otherwise.
        """
        achievement = await self._achievement_repo.get_by_name(achievement_name)
        if not achievement:
            logger.warning(f"Achievement '{achievement_name}' not found.")
            return False

        already_unlocked = await self._user_achievement_repo.find_by_user_and_achievement(
            user_id=user_id, achievement_id=achievement.id
        )
        if already_unlocked:
            return False

        # Grant the achievement
        user_achievement = UserAchievement(user_id=user_id, achievement_id=achievement.id)
        await self._user_achievement_repo.add(user_achievement)

        # Add reward points
        if achievement.reward_points > 0:
            await self.add_points(
                user_id=user_id,
                amount=achievement.reward_points,
                description=f"Achievement unlocked: {achievement.name}",
            )

        # Publish event
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
