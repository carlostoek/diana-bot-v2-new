import enum
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    String,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserRole(enum.Enum):
    FREE = "free"
    VIP = "vip"
    ADMIN = "admin"


from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id: int = Column(BigInteger, primary_key=True, index=True)
    first_name: str = Column(String, nullable=False)
    last_name: str = Column(String, nullable=True)
    username: str = Column(String, nullable=True, unique=True)
    role: UserRole = Column(Enum(UserRole), default=UserRole.FREE, nullable=False)
    is_admin: bool = Column(Boolean, default=False, nullable=False)

    # Gamification fields
    current_streak: int = Column(Integer, default=0, nullable=False)
    max_streak: int = Column(Integer, default=0, nullable=False)
    last_active_at: datetime = Column(DateTime, nullable=True)

    created_at: datetime = Column(DateTime, default=func.now(), nullable=False)
    updated_at: datetime = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"
        )


class Wallet(Base):
    __tablename__ = "wallets"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False, unique=True)
    balance: int = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount: int = Column(Integer, nullable=False)
    description: str = Column(String, nullable=True)
    created_at: datetime = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="transactions")


class Achievement(Base):
    __tablename__ = "achievements"

    id: int = Column(Integer, primary_key=True)
    name: str = Column(String, nullable=False, unique=True)
    description: str = Column(String, nullable=False)
    reward_points: int = Column(Integer, default=0, nullable=False)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    achievement_id: int = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    unlocked_at: datetime = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")
