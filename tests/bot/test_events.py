import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch
from src.bot.events import event_listener, _handle_event
from src.domain.events import UserRegistered, AchievementUnlocked


from unittest.mock import MagicMock

@pytest.fixture
def mock_redis_client():
    # redis.pubsub() is sync and returns a pubsub object.
    # The methods on the pubsub object are async.
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.get_message = AsyncMock(
        side_effect = [
            {"data": json.dumps({"event_name": "user_registered", "payload": {"user_id": 1}})},
            {"data": json.dumps({"event_name": "achievement_unlocked", "payload": {"user_id": 2, "achievement_name": "Test", "reward_points": 10}})},
            None, # To stop the loop
        ]
    )

    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    return mock_client

@pytest.fixture
def mock_service_provider():
    provider = AsyncMock()
    provider.onboarding_service.send_welcome_message = AsyncMock()
    provider.notification_service.send_achievement_unlocked_notification = AsyncMock()
    return provider


@pytest.mark.asyncio
async def test_event_listener_dispatches_events(mock_redis_client, mock_service_provider):
    """
    Test that the event_listener correctly receives and dispatches events.
    """
    with patch("src.bot.events._handle_event", new_callable=AsyncMock) as mock_handle_event:
        # This will run the loop until get_message returns None
        listener_task = asyncio.create_task(event_listener(mock_redis_client, mock_service_provider))
        await asyncio.sleep(0.01)  # allow the listener to start
        listener_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await listener_task

    # Check that our handler was called for each event from the mock_redis_client
    assert mock_handle_event.call_count == 2


@pytest.mark.asyncio
async def test_handle_event_calls_onboarding(mock_service_provider):
    """Test that _handle_event calls the correct service for UserRegistered."""
    event = UserRegistered(payload={"user_id": 123})

    await _handle_event(event.event_name, event.payload, mock_service_provider)

    mock_service_provider.onboarding_service.send_welcome_message.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_handle_event_calls_notification(mock_service_provider):
    """Test that _handle_event calls the correct service for AchievementUnlocked."""
    event = AchievementUnlocked(payload={"user_id": 123, "achievement_name": "Test", "reward_points": 50})

    await _handle_event(event.event_name, event.payload, mock_service_provider)

    mock_service_provider.notification_service.send_achievement_unlocked_notification.assert_called_once_with(
        user_id=123, achievement_name="Test", reward_points=50
    )
