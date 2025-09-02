from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class SQLAlchemyRepository(Generic[ModelType]):
    """
    A generic repository for SQLAlchemy models with basic async CRUD operations.
    """

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self._session = session
        self._model = model

    async def add(self, instance: ModelType) -> ModelType:
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def get(self, id: int) -> Optional[ModelType]:
        return await self._session.get(self._model, id)

    async def list(self) -> List[ModelType]:
        result = await self._session.execute(select(self._model))
        return result.scalars().all()

    async def delete(self, instance: ModelType) -> None:
        await self._session.delete(instance)
        await self._session.flush()


from src.domain.models import User, Wallet, Transaction, Achievement


class UserRepository(SQLAlchemyRepository[User]):
    """
    Repository for the User model.
    """
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)


class WalletRepository(SQLAlchemyRepository[Wallet]):
    """
    Repository for the Wallet model.
    """
    def __init__(self, session: AsyncSession):
        super().__init__(session, Wallet)

    async def get_by_user_id(self, user_id: int) -> Optional[Wallet]:
        result = await self._session.execute(
            select(self._model).filter_by(user_id=user_id)
        )
        return result.scalars().first()


class TransactionRepository(SQLAlchemyRepository[Transaction]):
    """
    Repository for the Transaction model.
    """
    def __init__(self, session: AsyncSession):
        super().__init__(session, Transaction)


from src.domain.models import UserAchievement


class AchievementRepository(SQLAlchemyRepository[Achievement]):
    """
    Repository for the Achievement model.
    """
    def __init__(self, session: AsyncSession):
        super().__init__(session, Achievement)

    async def get_by_name(self, name: str) -> Optional[Achievement]:
        result = await self._session.execute(
            select(self._model).filter_by(name=name)
        )
        return result.scalars().first()


class UserAchievementRepository(SQLAlchemyRepository[UserAchievement]):
    """
    Repository for the UserAchievement model.
    """
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserAchievement)

    async def find_by_user_and_achievement(
        self, user_id: int, achievement_id: int
    ) -> Optional[UserAchievement]:
        result = await self._session.execute(
            select(self._model).filter_by(user_id=user_id, achievement_id=achievement_id)
        )
        return result.scalars().first()
