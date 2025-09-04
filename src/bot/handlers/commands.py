from aiogram import types
from aiogram.filters import CommandStart
from src.bot.ui.keyboards import DynamicKeyboardFactory
from src.domain.models import User, UserProfile
from src.services.gamification_service import GamificationService
from src.services.context_service import ContextService
from src.services.personalization_service import PersonalizationService
from src.infrastructure.uow import IUnitOfWork


async def start_handler(
    message: types.Message,
    user: User,
    uow: IUnitOfWork,
    gamification_service: GamificationService,
    context_service: ContextService,
    personalization_service: PersonalizationService,
):
    """
    This handler will be called when user sends `/start` command.
    It provides a personalized experience based on user context.
    """
    # Get or create user profile
    profile = await uow.user_profiles.get(user.id)
    if not profile:
        profile = UserProfile(user_id=user.id)
        await uow.user_profiles.add(profile)

    # 1. Analyze context
    await context_service.detect_user_mood(profile)
    await context_service.classify_user_archetype(profile)
    await context_service.update_engagement_score(profile)

    # 2. Generate personalized content
    keyboard_factory = DynamicKeyboardFactory()
    keyboard = keyboard_factory.create_main_menu(profile)
    adaptive_message = await personalization_service.generate_adaptive_message(profile)

    # 3. Try to unlock the "First Steps" achievement
    await gamification_service.unlock_achievement(uow, user.id, "First Steps")

    await message.reply(adaptive_message, reply_markup=keyboard)


async def balance_handler(
    message: types.Message,
    user: User,
    uow: IUnitOfWork,
    gamification_service: GamificationService,
):
    """
    This handler will be called when user sends `/balance` command
    """
    wallet = await gamification_service.get_wallet_by_user_id(uow, user.id)
    await message.reply(f"Your current balance is: {wallet.balance} Besitos 💋")
