import pytest
from dependency_injector import providers
from src.containers import ApplicationContainer
from src.config import Settings


@pytest.mark.asyncio
async def test_application_container_creation():
    """
    Test that the ApplicationContainer can be created and provides dependencies.
    """
    container = ApplicationContainer()

    assert container.core is not None
    assert container.infrastructure is not None

    # Test configuration provider
    config = container.config()
    assert isinstance(config, Settings)

    # Test infrastructure providers
    db_engine = container.infrastructure.db_engine()
    assert db_engine is not None

    redis_client = container.infrastructure.redis_client()
    assert redis_client is not None

    event_publisher = container.infrastructure.event_publisher()
    assert event_publisher is not None

    user_repo = container.infrastructure.user_repository()
    assert user_repo is not None
