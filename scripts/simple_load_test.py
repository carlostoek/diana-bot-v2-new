import asyncio
import time
import random
from datetime import datetime

from aiogram import Dispatcher
from aiogram.types import Update, User as TelegramUser, Message, Chat

from src.containers import ApplicationContainer
from src.bot.middleware.uow import UoWMiddleware
from src.bot.middleware.auth import AuthMiddleware
from src.bot.handlers.commands import start_handler
from aiogram.filters import CommandStart

# --- Test Configuration ---
NUM_REQUESTS = 100
CONCURRENCY = 10

async def run_single_request(dp: Dispatcher, user_id: int):
    """Simulates a single user sending a /start command."""
    mock_bot = AsyncMock()
    telegram_user = TelegramUser(id=user_id, is_bot=False, first_name=f"LoadTestUser{user_id}")
    chat = Chat(id=user_id, type="private")
    message = Message(
        message_id=random.randint(1, 100000),
        chat=chat,
        from_user=telegram_user,
        text="/start",
        date=datetime.now()
    )
    update = Update(update_id=random.randint(1, 100000), message=message)

    try:
        await dp.feed_update(mock_bot, update)
    except Exception as e:
        print(f"Request for user {user_id} failed: {e}")

async def main():
    """Main function to run the load test."""
    print("--- Setting up application for load test ---")
    container = ApplicationContainer()

    # We need a real UoW for this test to hit the DB
    uow_provider = container.infrastructure.uow
    user_service = container.services.user_service()
    gamification_service = container.services.gamification_service()

    uow_middleware = UoWMiddleware(uow_provider)
    auth_middleware = AuthMiddleware(user_service, gamification_service)

    dp = Dispatcher()
    dp.update.outer_middleware.register(uow_middleware)
    dp.update.outer_middleware.register(auth_middleware)
    dp["gamification_service"] = gamification_service
    dp.message.register(start_handler, CommandStart())

    print(f"--- Starting Load Test ---")
    print(f"Total Requests: {NUM_REQUESTS}")
    print(f"Concurrency: {CONCURRENCY}")

    start_time = time.time()

    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = []

    async def worker(user_id):
        async with semaphore:
            await run_single_request(dp, user_id)

    for i in range(NUM_REQUESTS):
        task = asyncio.create_task(worker(i))
        tasks.append(task)

    await asyncio.gather(*tasks)

    end_time = time.time()
    duration = end_time - start_time
    reqs_per_second = NUM_REQUESTS / duration

    print("\n--- Load Test Results ---")
    print(f"Processed {NUM_REQUESTS} requests in {duration:.2f} seconds.")
    print(f"Requests per second: {reqs_per_second:.2f}")

if __name__ == "__main__":
    # Need to mock the event publisher to avoid connecting to Redis
    from unittest.mock import patch, AsyncMock
    with patch("src.infrastructure.event_bus.EventPublisher.publish", new_callable=AsyncMock):
        asyncio.run(main())
