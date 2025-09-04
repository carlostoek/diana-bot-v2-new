import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from aiogram import Dispatcher
from aiogram.types import Update, User as TelegramUser, Message, Chat

from src.containers import ApplicationContainer
from src.bot.middleware.uow import UoWMiddleware
from src.bot.middleware.auth import AuthMiddleware
from src.bot.handlers.commands import start_handler
from src.domain.models import Achievement
from aiogram.filters import CommandStart


from src.domain.models import User

@pytest.mark.asyncio
@patch("src.infrastructure.event_bus.EventPublisher.publish", new_callable=AsyncMock)
async def test_full_onboarding_flow(mock_publish, session_factory):
    """
    Tests the full end-to-end flow for a new user.
    """
    # 1. Setup a test-specific container and dispatcher
    container = ApplicationContainer()

    # Mock the bot object to spy on its messages
    mock_bot = AsyncMock()
    container.bot.bot.override(mock_bot)

    # Override the session factory to use the in-memory test DB
    container.infrastructure.session_factory.override(session_factory)

    # Get all services and middleware from the container
    uow_provider = container.infrastructure.uow
    user_service = container.services.user_service()
    gamification_service = container.services.gamification_service()
    context_service = container.services.context_service()
    personalization_service = container.services.personalization_service()

    uow_middleware = UoWMiddleware(container.infrastructure.uow)
    auth_middleware = AuthMiddleware(user_service, gamification_service)

    dp = Dispatcher()
    dp.update.outer_middleware.register(uow_middleware)
    dp.update.outer_middleware.register(auth_middleware)
    dp["gamification_service"] = gamification_service
    dp["context_service"] = context_service
    dp["personalization_service"] = personalization_service
    dp.message.register(start_handler, CommandStart())

    # Seed the database with an achievement
    async with uow_provider() as uow:
        await uow.achievements.add(Achievement(name="First Steps", description=".", reward_points=10))
        await uow.commit()

    # 2. Simulate an incoming /start message from a new user
    telegram_user = TelegramUser(id=999, is_bot=False, first_name="E2E_Test")
    chat = Chat(id=999, type="private")
    message = Message(message_id=1, chat=chat, from_user=telegram_user, text="/start", date=datetime.now())
    update = Update(update_id=1, message=message)

    await dp.feed_update(mock_bot, update)

    # 3. Assertions
    # The handler should reply, and the events should trigger other messages
    await asyncio.sleep(0.1) # Give events time to be hypothetically processed

    # Check that events were published
    assert mock_publish.call_count == 2

    event_names = [call.args[1].event_name for call in mock_publish.call_args_list]
    assert "user_registered" in event_names
    assert "achievement_unlocked" in event_names

    # Check database state
    async with uow_provider() as uow:
        user = await uow.users.get(999)
        assert user is not None
        wallet = await uow.wallets.get_by_user_id(999)
        assert wallet.balance == 10
        unlocked = await uow.user_achievements.find_by_user_and_achievement(999, 1)
        assert unlocked is not None


@pytest.mark.asyncio
@patch("src.infrastructure.event_bus.EventPublisher.publish", new_callable=AsyncMock)
async def test_returning_user_flow(mock_publish, session_factory):
    """
    Tests the flow for a returning user.
    """
    # 1. Setup
    container = ApplicationContainer()
    mock_bot = AsyncMock()
    container.bot.bot.override(mock_bot)
    container.infrastructure.session_factory.override(session_factory)
    uow_provider = container.infrastructure.uow
    user_service = container.services.user_service()
    gamification_service = container.services.gamification_service()
    context_service = container.services.context_service()
    personalization_service = container.services.personalization_service()
    uow_middleware = UoWMiddleware(uow_provider)
    auth_middleware = AuthMiddleware(user_service, gamification_service)
    dp = Dispatcher()
    dp.update.outer_middleware.register(uow_middleware)
    dp.update.outer_middleware.register(auth_middleware)
    dp["gamification_service"] = gamification_service
    dp["context_service"] = context_service
    dp["personalization_service"] = personalization_service
    dp.message.register(start_handler, CommandStart())

    # 2. Seed the database with an existing user from yesterday
    yesterday = datetime.now() - timedelta(days=1)
    async with uow_provider() as uow:
        await uow.users.add(User(id=888, first_name="Returning", last_active_at=yesterday, current_streak=3))
        await uow.commit()

    # 3. Simulate an incoming /start message
    telegram_user = TelegramUser(id=888, is_bot=False, first_name="Returning")
    chat = Chat(id=888, type="private")
    message = Message(message_id=1, chat=chat, from_user=telegram_user, text="/start", date=datetime.now())
    update = Update(update_id=1, message=message)

    await dp.feed_update(mock_bot, update)
    await asyncio.sleep(0.1)

    # 4. Assertions
    # UserRegistered event should NOT be published
    event_names = [call.args[1].event_name for call in mock_publish.call_args_list]
    assert "user_registered" not in event_names

    # Check that streak was updated
    async with uow_provider() as uow:
        user = await uow.users.get(888)
        assert user.current_streak == 4
