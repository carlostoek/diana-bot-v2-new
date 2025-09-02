from typing import Tuple
from aiogram import types as tg_types
from src.domain.models import User
from src.infrastructure.uow import IUnitOfWork
from src.domain.events import UserRegistered
from src.infrastructure.event_bus import EventPublisher


class UserService:
    """
    Service for user management.
    """

    def __init__(self, event_publisher: EventPublisher):
        self._event_publisher = event_publisher

    async def get_or_create_user(
        self,
        uow: IUnitOfWork,
        telegram_user: tg_types.User,
    ) -> Tuple[User, bool]:
        """
        Retrieves a user from the database or creates a new one if they don't exist.

        Also updates the user's profile information if it has changed.

        This operation is transactional.

        Args:
            uow: The Unit of Work for the transaction.
            telegram_user: The user object from a Telegram update.

        Returns:
            A tuple containing the User object and a boolean indicating if the user was created.
        """
        user = await uow.users.get(telegram_user.id)
        if user:
            # User exists, check if profile info needs updating
            if (
                user.first_name != telegram_user.first_name
                or user.last_name != telegram_user.last_name
                or user.username != telegram_user.username
            ):
                user.first_name = telegram_user.first_name
                user.last_name = telegram_user.last_name
                user.username = telegram_user.username
                await uow.users.add(user)
            return user, False

        # User does not exist, create a new one
        new_user = User(
            id=telegram_user.id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
        )
        await uow.users.add(new_user)

        # Publish an event for the new user registration
        event = UserRegistered(
            payload={"user_id": new_user.id, "username": new_user.username}
        )
        await self._event_publisher.publish("user_events", event)

        return new_user, True
