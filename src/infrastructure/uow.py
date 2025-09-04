from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.repositories import (
    UserRepository,
    WalletRepository,
    TransactionRepository,
    AchievementRepository,
    UserAchievementRepository,
    UserProfileRepository,
)


class IUnitOfWork(ABC):
    users: UserRepository
    wallets: WalletRepository
    transactions: TransactionRepository
    achievements: AchievementRepository
    user_achievements: UserAchievementRepository
    user_profiles: UserProfileRepository

    @abstractmethod
    async def __aenter__(self):
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...

    @abstractmethod
    async def commit(self):
        ...

    @abstractmethod
    async def rollback(self):
        ...


class UnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def __aenter__(self):
        self.session = self._session_factory()

        self.users = UserRepository(self.session)
        self.wallets = WalletRepository(self.session)
        self.transactions = TransactionRepository(self.session)
        self.achievements = AchievementRepository(self.session)
        self.user_achievements = UserAchievementRepository(self.session)
        self.user_profiles = UserProfileRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
