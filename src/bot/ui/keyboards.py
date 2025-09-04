from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.domain.models import UserProfile


class DynamicKeyboardFactory:
    """
    Factory for generating dynamic and context-aware keyboards (UI-001).
    """

    def create_main_menu(self, profile: UserProfile) -> InlineKeyboardMarkup:
        """
        Creates the main menu keyboard, personalized for the user's archetype and mood.
        """
        buttons = []

        # Personalized buttons based on archetype
        if profile.archetype.value == "explorer":
            buttons.append(
                [InlineKeyboardButton(text="🗺️ Explorar", callback_data="explore")]
            )
        elif profile.archetype.value == "achiever":
            buttons.append(
                [InlineKeyboardButton(text="🏆 Desafíos", callback_data="challenges")]
            )
        elif profile.archetype.value == "socializer":
            buttons.append(
                [InlineKeyboardButton(text="💬 Social", callback_data="social")]
            )
        else:
            buttons.append(
                [InlineKeyboardButton(text="🚀 Acciones", callback_data="actions")]
            )

        # Add a button based on mood
        if profile.mood.value == "reflective":
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="📝 Escribir en el diario", callback_data="journal"
                    )
                ]
            )

        # Common buttons
        buttons.append([InlineKeyboardButton(text="❓ Ayuda", callback_data="help")])

        return InlineKeyboardMarkup(inline_keyboard=buttons)
