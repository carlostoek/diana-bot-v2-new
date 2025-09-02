from aiogram import types
from aiogram.filters import CommandStart
from src.bot.ui.keyboards import get_start_keyboard


async def start_handler(message: types.Message):
    """
    This handler will be called when user sends `/start` command
    """
    keyboard = get_start_keyboard()
    await message.reply(
        "Welcome to Diana Bot! How can I help you today?",
        reply_markup=keyboard
    )
