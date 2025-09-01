import pytest
from unittest.mock import AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.database import Base
from src.modules.user.models import User
from src.modules.user.repository import UserRepository
from src.modules.user.service import UserService

# Setup for in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a new database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def user_repository(db_session):
    return UserRepository(db_session)

@pytest.fixture(scope="function")
def mock_event_bus():
    return AsyncMock()

@pytest.fixture(scope="function")
def user_service(user_repository, mock_event_bus):
    return UserService(user_repository=user_repository, event_bus=mock_event_bus)

@pytest.mark.asyncio
async def test_find_or_create_user_integration(user_service, db_session):
    # Test creating a new user
    user = await user_service.find_or_create_user(1, "John", "Doe", "johndoe")
    assert user.id == 1
    assert user.first_name == "John"

    # Verify user is in the database
    db_user = db_session.query(User).filter(User.id == 1).first()
    assert db_user is not None
    assert db_user.username == "johndoe"

    # Test finding an existing user
    user2 = await user_service.find_or_create_user(1, "John", "Doe", "johndoe")
    assert user2.id == 1

@pytest.mark.asyncio
async def test_update_user_profile_integration(user_service, db_session):
    # Create a user first
    initial_user = User(id=2, first_name="Jane", last_name="Doe", role="free", is_admin=False)
    db_session.add(initial_user)
    db_session.commit()

    # Update the user's profile
    update_data = {"first_name": "Janet", "role": "premium"}
    updated_user = user_service.update_user_profile(2, update_data)

    assert updated_user is not None
    assert updated_user.first_name == "Janet"
    assert updated_user.role == "premium"

    # Verify the changes in the database
    db_user = db_session.query(User).filter(User.id == 2).first()
    assert db_user.first_name == "Janet"

@pytest.mark.asyncio
async def test_create_user_publishes_event_integration(user_service, mock_event_bus):
    # Act
    await user_service.find_or_create_user(3, "Event", "Test", "eventtest")

    # Assert
    mock_event_bus.publish.assert_called_once()
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == "user.registered"
    assert event.data["user_id"] == 3
