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
from src.infrastructure.repositories import (
    UserRepository,
    WalletRepository,
    TransactionRepository,
    AchievementRepository,
    UserAchievementRepository,
)
from src.infrastructure.uow import UnitOfWork


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

    wallet_repository = providers.Factory(
        WalletRepository,
        session=session_factory,
    )

    transaction_repository = providers.Factory(
        TransactionRepository,
        session=session_factory,
    )

    achievement_repository = providers.Factory(
        AchievementRepository,
        session=session_factory,
    )

    user_achievement_repository = providers.Factory(
        UserAchievementRepository,
        session=session_factory,
    )

    uow = providers.Factory(
        UnitOfWork,
        session_factory=session_factory,
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


from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

class BotContainer(containers.DeclarativeContainer):
    """
    Container for bot-related components.
    """
    config = providers.Object(settings)

    bot = providers.Singleton(
        Bot,
        token=config.provided.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = providers.Singleton(Dispatcher)


from src.services.user_service import UserService
from src.services.onboarding_service import OnboardingService
from src.services.gamification_service import GamificationService
from src.services.notification_service import NotificationService


class ServiceContainer(containers.DeclarativeContainer):
    """
    Container for application services.
    """
    infrastructure = providers.DependenciesContainer()
    bot = providers.DependenciesContainer()

    user_service = providers.Factory(
        UserService,
        event_publisher=infrastructure.event_publisher,
    )

    onboarding_service = providers.Factory(
        OnboardingService,
        bot=bot.bot,
    )

    notification_service = providers.Factory(
        NotificationService,
        bot=bot.bot,
    )

    gamification_service = providers.Factory(
        GamificationService,
        event_publisher=infrastructure.event_publisher,
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

    bot = providers.Container(
        BotContainer,
        config=config,
    )

    services = providers.Container(
        ServiceContainer,
        infrastructure=infrastructure,
        bot=bot,
    )
