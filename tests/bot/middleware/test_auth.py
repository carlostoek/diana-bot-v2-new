import pytest
from aiogram import Dispatcher
from aiogram.types import Update, User as TelegramUser
from unittest.mock import AsyncMock
from src.bot.middleware.auth import AuthMiddleware
from src.services.user_service import UserService
from src.infrastructure.repositories import UserRepository
from src.bot.middleware.uow import UoWMiddleware
from src.infrastructure.uow import UnitOfWork


@pytest.mark.asyncio
async def test_auth_middleware_creates_new_user(session_factory):
    """
    Integration test for the AuthMiddleware.
    Checks if a new user is created and passed to the handler.
    """
    # 1. Setup
    event_publisher = AsyncMock()
    user_service = UserService(event_publisher)
    gamification_service = AsyncMock()
    middleware = AuthMiddleware(user_service, gamification_service)

    dp = Dispatcher()
    # This test uses a real UoW with a real session
    uow_provider = lambda: UnitOfWork(session_factory)

    middleware = AuthMiddleware(user_service, gamification_service)
    uow_middleware = UoWMiddleware(uow_provider)

    dp = Dispatcher()
    dp.update.outer_middleware.register(uow_middleware)
    dp.update.outer_middleware.register(middleware)

    # A mock handler that captures the data passed by the middleware
    mock_handler = AsyncMock()

    @dp.message()
    async def test_handler(message, user, is_new_user):
        await mock_handler(user=user, is_new_user=is_new_user)

    # 2. Simulate an update from a new user
    telegram_user = TelegramUser(id=123, is_bot=False, first_name="Test")
    message = {
        "message_id": 1,
        "chat": {"id": 1, "type": "private"},
        "from": telegram_user.model_dump(),
        "text": "/start",
        "date": 1672531200, # 2023-01-01
    }
    update = Update(update_id=1, message=message)

    # 3. Process the update
    await dp.feed_update(AsyncMock(), update)

    # 4. Assertions
    # Check that the handler was called
    mock_handler.assert_called_once()

    # Check the arguments passed to the handler
    handler_args = mock_handler.call_args.kwargs
    assert handler_args["is_new_user"] is True
    assert handler_args["user"].id == 123
    assert handler_args["user"].first_name == "Test"

    # Check that the user was actually created in the database
    async with session_factory() as session:
        user_repo = UserRepository(session)
        db_user = await user_repo.get(123)
        assert db_user is not None
        assert db_user.id == 123
