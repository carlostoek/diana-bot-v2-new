from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, func
from src.core.database import Base
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class UserState(Enum):
    NEW = "new"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    INACTIVE = "inactive"

class DuplicateUserError(Exception):
    """Raised when attempting to create a user that already exists."""
    pass

class UserNotFoundError(Exception):
    """Raised when a user is not found in the repository."""
    pass

class InvalidUserDataError(Exception):
    """Raised when user data provided is invalid."""
    pass

@dataclass
class UserStats:
    user_id: int
    total_points: int
    level: int
    achievements: list

@dataclass
class TelegramUser:
    id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]

class UserCreateRequest:
    def __init__(self, telegram_user: TelegramUser):
        self.telegram_user = telegram_user

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True, comment="Telegram User ID")
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    username = Column(String, nullable=True, index=True)
    role = Column(String, default='free', nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
