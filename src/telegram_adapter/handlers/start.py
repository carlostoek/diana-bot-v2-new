from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from dependency_injector.wiring import inject, Provide

from src.telegram_adapter.keyboards.start_keyboard import get_start_keyboard
from src.core.container import Container
from src.modules.user.interfaces import IUserService

# Create a new router for this command
router = Router()

@router.message(CommandStart())
@inject
async def handle_start(
    message: Message,
    user_service: IUserService = Provide[Container.user_service],
):
    """
    Handler for the /start command.
    Finds or creates a user and welcomes them.
    """
    user = await user_service.find_or_create_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
    )

    keyboard = get_start_keyboard()
    await message.reply(
        f"Hello, {user.first_name}! Your user ID is {user.id}",
        reply_markup=keyboard
    )
