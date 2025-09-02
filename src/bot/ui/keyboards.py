from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard() -> InlineKeyboardMarkup:
    """
    Returns the inline keyboard for the start message.
    """
    buttons = [
        [
            InlineKeyboardButton(text="🚀 Explore Features", callback_data="explore_features"),
            InlineKeyboardButton(text="❓ Help", callback_data="help"),
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
