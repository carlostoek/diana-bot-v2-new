from aiogram import types
from aiogram.filters import CommandStart
from src.bot.ui.keyboards import get_start_keyboard
from src.domain.models import User


from aiogram.filters import Command
from src.services.gamification_service import GamificationService


from src.infrastructure.uow import IUnitOfWork


async def start_handler(
    message: types.Message,
    user: User,
    uow: IUnitOfWork,
    gamification_service: GamificationService,
):
    """
    This handler will be called when user sends `/start` command
    """
    # Try to unlock the "First Steps" achievement
    await gamification_service.unlock_achievement(uow, user.id, "First Steps")

    keyboard = get_start_keyboard()
    await message.reply(
        f"Welcome back, {user.first_name}! How can I help you today?",
        reply_markup=keyboard
    )


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
