from aiogram import types
from aiogram.filters import CommandStart
from src.bot.ui.keyboards import get_start_keyboard
from src.domain.models import User


async def start_handler(message: types.Message, user: User):
    """
    This handler will be called when user sends `/start` command
    """
    keyboard = get_start_keyboard()
    await message.reply(
        f"Welcome back, {user.first_name}! How can I help you today?",
        reply_markup=keyboard
    )
