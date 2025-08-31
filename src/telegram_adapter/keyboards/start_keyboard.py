from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_start_keyboard() -> InlineKeyboardMarkup:
    """
    Returns an inline keyboard for the start message.
    """
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Check out the project!",
        url="https://github.com/diana-bot" # Placeholder URL
    ))
    builder.add(InlineKeyboardButton(
        text="Learn more",
        callback_data="learn_more"
    ))
    return builder.as_markup()
