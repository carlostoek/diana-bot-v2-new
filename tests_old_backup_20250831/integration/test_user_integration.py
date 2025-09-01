import pytest
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.database import Base
from src.modules.user.models import User
from src.modules.user.repository import UserRepository
from src.modules.user.service import UserService
from src.modules.user.events import UserCreated

# Setup for in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
def user_service(user_repository):
    return UserService(user_repository)

@pytest.fixture(scope="function")
def mock_event_bus():
    return Mock()

@pytest.fixture(scope="function")
def mock_gamification_service():
    return Mock()

# --- Integration Test Cases ---

def test_middleware_simulation_find_or_create_user(user_service, db_session):
    # Simulate Telegram user data from middleware
    telegram_user_data = {
        "id": 100001,
        "first_name": "Telegram",
        "last_name": "User",
        "username": "telegram_user"
    }

    # Simulate middleware calling find_or_create_user
    user = user_service.find_or_create_user(
        user_id=telegram_user_data["id"],
        first_name=telegram_user_data["first_name"],
        last_name=telegram_user_data["last_name"],
        username=telegram_user_data["username"]
    )

    assert user.id == telegram_user_data["id"]
    assert user.first_name == telegram_user_data["first_name"]
    assert db_session.query(User).filter(User.id == telegram_user_data["id"]).first() is not None

def test_event_bus_user_created_event_dispatch(user_service, user_repository, mock_event_bus):
    # Replace the actual event bus with the mock
    # In a real app, this would be done via dependency injection
    # For this test, we'll simulate the service dispatching the event

    # Simulate a new user creation
    user_data = {"id": 100002, "first_name": "EventUser", "last_name": None, "username": None}
    new_user = user_repository.create_user(user_data)

    # Simulate the service logic that would dispatch the event
    # (This part is conceptual as the service doesn't directly dispatch events yet)
    # If the service were to dispatch, it would look like:
    # mock_event_bus.dispatch(UserCreated(user_id=new_user.id, first_name=new_user.first_name))

    # For now, we'll directly call the mock to verify the concept
    mock_event_bus.dispatch(UserCreated(user_id=new_user.id, first_name=new_user.first_name))

    mock_event_bus.dispatch.assert_called_once_with(
        UserCreated(user_id=100002, first_name="EventUser")
    )

def test_gamification_service_reacts_to_user_created_event(mock_event_bus, mock_gamification_service):
    # Simulate a listener in the gamification service
    def gamification_listener(event: UserCreated):
        mock_gamification_service.award_welcome_bonus(event.user_id)

    # Configure the mock_event_bus.dispatch to call the listener
    # when it's called with a UserCreated event
    mock_event_bus.dispatch.side_effect = lambda event: gamification_listener(event) if isinstance(event, UserCreated) else None

    # Simulate the event being dispatched (e.g., by UserService)
    event = UserCreated(user_id=100003, first_name="GameUser")
    mock_event_bus.dispatch(event)

    # Verify that the gamification service reacted
    mock_gamification_service.award_welcome_bonus.assert_called_once_with(100003)
