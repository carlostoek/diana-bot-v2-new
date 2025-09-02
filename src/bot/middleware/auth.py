from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from src.services.user_service import UserService


class AuthMiddleware(BaseMiddleware):
    """
    Middleware for handling user authentication and registration.
    """

    def __init__(self, user_service: UserService):
        self._user_service = user_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Get the telegram user from the event
        telegram_user = data.get("event_from_user")
        if not telegram_user:
            return await handler(event, data)

        # Get or create the user from the database
        user, is_new = await self._user_service.get_or_create_user(telegram_user)

        # Pass the user and is_new flag to the handler
        data["user"] = user
        data["is_new_user"] = is_new

        return await handler(event, data)
