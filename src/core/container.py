from dependency_injector import containers, providers
from src.core.database import SessionLocal
from src.core.event_bus import EventBus
from src.modules.user.repository import UserRepository
from src.modules.user.service import UserService
from src.services.gamification.repository import GamificationRepository
from src.services.gamification.service import GamificationService

class Container(containers.DeclarativeContainer):

    # Configuration
    # In a real app, you would load config from a file or env vars
    config = providers.Configuration()

    # Core
    db_session = providers.Singleton(SessionLocal)
    event_bus = providers.Singleton(EventBus, redis_url="redis://localhost:6379/0")

    # Repositories
    user_repository = providers.Factory(
        UserRepository,
        db_session=db_session,
    )
    gamification_repository = providers.Factory(
        GamificationRepository,
        db_session=db_session,
    )

    # Services
    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        event_bus=event_bus,
    )
    gamification_service = providers.Factory(
        GamificationService,
        repository=gamification_repository,
        event_bus=event_bus,
    )
