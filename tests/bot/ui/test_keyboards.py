import pytest
from aiogram.types import InlineKeyboardMarkup
from src.bot.ui.keyboards import DynamicKeyboardFactory
from src.domain.models import UserProfile, UserMood, UserArchetype


@pytest.fixture
def keyboard_factory():
    return DynamicKeyboardFactory()


@pytest.mark.parametrize(
    "archetype, mood, expected_button_data",
    [
        (UserArchetype.EXPLORER, UserMood.NEUTRAL, "explore"),
        (UserArchetype.ACHIEVER, UserMood.NEUTRAL, "challenges"),
        (UserArchetype.SOCIALIZER, UserMood.HAPPY, "social"),
        (UserArchetype.PHILOSOPHER, UserMood.REFLECTIVE, "actions"),
    ],
)
def test_create_main_menu_archetype_buttons(
    keyboard_factory: DynamicKeyboardFactory,
    archetype: UserArchetype,
    mood: UserMood,
    expected_button_data: str,
):
    """
    Test that the main menu contains the correct primary button for the user's archetype.
    """
    profile = UserProfile(user_id=1, archetype=archetype, mood=mood)
    keyboard = keyboard_factory.create_main_menu(profile)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    # The first button should be the archetype-specific one
    primary_button = keyboard.inline_keyboard[0][0]
    assert primary_button.callback_data == expected_button_data


def test_create_main_menu_mood_button(keyboard_factory: DynamicKeyboardFactory):
    """
    Test that a special button is added for a specific mood (e.g., reflective).
    """
    # Profile with a neutral mood should not have the journal button
    profile_neutral = UserProfile(
        user_id=1, archetype=UserArchetype.EXPLORER, mood=UserMood.NEUTRAL
    )
    keyboard_neutral = keyboard_factory.create_main_menu(profile_neutral)
    assert not any(
        button.callback_data == "journal"
        for row in keyboard_neutral.inline_keyboard
        for button in row
    )

    # Profile with a reflective mood should have the journal button
    profile_reflective = UserProfile(
        user_id=1, archetype=UserArchetype.EXPLORER, mood=UserMood.REFLECTIVE
    )
    keyboard_reflective = keyboard_factory.create_main_menu(profile_reflective)
    assert any(
        button.callback_data == "journal"
        for row in keyboard_reflective.inline_keyboard
        for button in row
    )
