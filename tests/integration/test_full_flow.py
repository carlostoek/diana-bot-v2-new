import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from src.core.container import Container
from src.core.events import UserEvent
from src.modules.user.models import User
from src.services.gamification.models import UserGamification
from src.core.database import Base
from dependency_injector import providers

@pytest.mark.asyncio
async def test_full_start_command_flow():
    """
    Tests the full, event-driven flow of the /start command.
    """
    container = Container()

    # --- Mock the Event Bus to prevent network connection ---
    mock_event_bus = AsyncMock()
    subscribers = {}

    async def mock_subscribe(event_pattern, handler):
        if event_pattern not in subscribers:
            subscribers[event_pattern] = []
        subscribers[event_pattern].append(handler)

    async def mock_publish(event):
        # This mock simulates wildcard subscriptions like "user.*"
        for pattern, handlers in subscribers.items():
            if pattern.endswith('*') and event.type.startswith(pattern[:-1]):
                for handler in handlers:
                    await handler(event)

    mock_event_bus.subscribe.side_effect = mock_subscribe
    mock_event_bus.publish.side_effect = mock_publish
    mock_event_bus.initialize.return_value = None
    mock_event_bus.cleanup.return_value = None

    # Override the container's event bus with our mock
    container.event_bus.override(providers.Object(mock_event_bus))
    # --- End Mocking ---

    container.wire(modules=[
        "src.telegram_adapter.handlers.start",
        "src.services.gamification.service"
    ])

    user_service = container.user_service()
    gamification_service = container.gamification_service()
    db_session = container.db_session()

    engine = db_session.get_bind()
    Base.metadata.create_all(engine)

    # Initialize the gamification service, which will subscribe to the mock event bus
    await gamification_service.initialize()

    from src.telegram_adapter.handlers.start import handle_start
    from aiogram.types import User as AiogramUser

    mock_message = MagicMock()
    mock_message.from_user = AiogramUser(id=123, is_bot=False, first_name="Test", last_name="User", username="testuser")
    mock_message.reply = AsyncMock()

    # This will publish events, and our mock bus will deliver them instantly
    await handle_start(mock_message)

    # Assertions
    db_user = db_session.query(User).filter_by(id=123).first()
    assert db_user is not None
    assert db_user.first_name == "Test"

    gamification_stats = db_session.query(UserGamification).filter_by(user_id=123).first()
    assert gamification_stats is not None
    assert gamification_stats.total_points > 0
    assert gamification_stats.current_streak == 1

    # Check that publish was called
    assert mock_event_bus.publish.call_count > 0

    container.shutdown_resources()
