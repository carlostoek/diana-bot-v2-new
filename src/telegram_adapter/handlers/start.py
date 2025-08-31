from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from dependency_injector.wiring import inject, Provide

from src.telegram_adapter.keyboards.start_keyboard import get_start_keyboard
from src.core.container import Container
from src.modules.user.interfaces import IUserService
from src.core.interfaces import IEventBus
from src.core.events import UserEvent

# Create a new router for this command
router = Router()

@router.message(CommandStart())
@inject
async def handle_start(
    message: Message,
    user_service: IUserService = Provide[Container.user_service],
    event_bus: IEventBus = Provide[Container.event_bus],
):
    """
    Handler for the /start command.
    Finds or creates a user and welcomes them.
    Publishes a daily activity event.
    """
    user = await user_service.find_or_create_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
    )

    # Publish daily activity event
    activity_event = UserEvent(
        user_id=user.id,
        event_type="daily_activity",
        user_data={"source": "start_command"}
    )
    await event_bus.publish(activity_event)

    keyboard = get_start_keyboard()
    await message.reply(
        f"Hello, {user.first_name}! Your user ID is {user.id}",
        reply_markup=keyboard
    )
