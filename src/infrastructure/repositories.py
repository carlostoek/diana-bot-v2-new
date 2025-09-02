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


from src.domain.models import User


class UserRepository(SQLAlchemyRepository[User]):
    """
    Repository for the User model.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
