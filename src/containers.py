"""
Dependency injection containers for the Diana Bot application.
"""

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import create_async_engine
import redis.asyncio as redis

from src.config import settings


class CoreContainer(containers.DeclarativeContainer):
    """
    Core container with basic dependencies like configuration.
    """
    config = providers.Object(settings)


from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.event_bus import EventPublisher
from src.infrastructure.repositories import UserRepository


class InfrastructureContainer(containers.DeclarativeContainer):
    """
    Infrastructure container with dependencies for external services
    like database, redis, etc.
    """
    config = providers.Object(settings)

    db_engine = providers.Singleton(
        create_async_engine,
        url=config.provided.DATABASE_URL,
        echo=config.provided.DEBUG,
    )

    session_factory = providers.Factory(
        sessionmaker,
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    user_repository = providers.Factory(
        UserRepository,
        session=session_factory,
    )

    redis_pool = providers.Singleton(
        redis.ConnectionPool,
        host=config.provided.REDIS_HOST,
        port=config.provided.REDIS_PORT,
        db=config.provided.REDIS_DB,
    )

    redis_client = providers.Singleton(
        redis.Redis,
        connection_pool=redis_pool,
    )

    event_publisher = providers.Factory(
        EventPublisher,
        redis_client=redis_client,
    )


class ApplicationContainer(containers.DeclarativeContainer):
    """
    Application container with all dependencies.
    """
    config = providers.Object(settings)

    core = providers.Container(
        CoreContainer,
        config=config,
    )

    infrastructure = providers.Container(
        InfrastructureContainer,
        config=config,
    )
