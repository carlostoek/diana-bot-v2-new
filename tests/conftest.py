import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.domain.models import Base

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def async_engine():
    """
    Provides a SQLAlchemy async engine for the test session.
    Creates all tables based on the Base metadata.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
def session_factory(async_engine):
    """Provides a SQLAlchemy async session factory for the test session."""
    return sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture(scope="function")
async def db_session(session_factory):
    """
    Provides a SQLAlchemy async session for a test function.
    """
    async with session_factory() as session:
        yield session
