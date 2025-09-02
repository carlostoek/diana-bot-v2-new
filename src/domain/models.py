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


class User(Base):
    __tablename__ = "users"

    id: int = Column(BigInteger, primary_key=True, index=True)
    first_name: str = Column(String, nullable=False)
    last_name: str = Column(String, nullable=True)
    username: str = Column(String, nullable=True, unique=True)
    role: UserRole = Column(Enum(UserRole), default=UserRole.FREE, nullable=False)
    is_admin: bool = Column(Boolean, default=False, nullable=False)
    created_at: datetime = Column(DateTime, default=func.now(), nullable=False)
    updated_at: datetime = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"
        )
