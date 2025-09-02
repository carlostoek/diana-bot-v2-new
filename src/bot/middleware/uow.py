from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from dependency_injector.providers import Provider
from src.infrastructure.uow import IUnitOfWork


class UoWMiddleware(BaseMiddleware):
    """
    Middleware for providing a Unit of Work to handlers.
    """

    def __init__(self, uow_provider: Provider[IUnitOfWork]):
        self._uow_provider = uow_provider

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self._uow_provider() as uow:
            data["uow"] = uow
            return await handler(event, data)
