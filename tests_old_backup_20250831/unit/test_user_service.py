import pytest
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

# --- Test Cases ---

def test_create_user_repository(user_repository):
    user_data = {
        "id": 12345,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser"
    }
    user = user_repository.create_user(user_data)
    assert user.id == 12345
    assert user.first_name == "Test"
    assert user.role == "free"

def test_get_user_by_id_repository(user_repository):
    user_data = {"id": 12345, "first_name": "Test"}
    user_repository.create_user(user_data)
    
    found_user = user_repository.get_user_by_id(12345)
    assert found_user is not None
    assert found_user.id == 12345

    not_found_user = user_repository.get_user_by_id(54321)
    assert not_found_user is None

def test_find_or_create_user_service_finds_existing(user_service, user_repository):
    user_data = {"id": 12345, "first_name": "Existing"}
    user_repository.create_user(user_data)

    user = user_service.find_or_create_user(12345, "Existing", None, None)
    assert user.first_name == "Existing"

def test_find_or_create_user_service_creates_new(user_service):
    user = user_service.find_or_create_user(54321, "New", "User", "newuser")
    assert user.id == 54321
    assert user.first_name == "New"
    assert user.username == "newuser"

def test_find_or_create_user_is_idempotent(user_service, db_session):
    # Call find_or_create_user multiple times for the same new user
    user1 = user_service.find_or_create_user(111, "Idempotent", "User", "idem")
    user2 = user_service.find_or_create_user(111, "Idempotent", "User", "idem")

    # Check that they are the same user object
    assert user1.id == user2.id

    # Verify in the database that only one user was created
    user_count = db_session.query(User).filter(User.id == 111).count()
    assert user_count == 1

def test_create_user_with_missing_optional_data(user_service):
    user = user_service.find_or_create_user(67890, "Optional", None, None)
    assert user.id == 67890
    assert user.first_name == "Optional"
    assert user.last_name is None
    assert user.username is None

def test_find_user_does_not_update_existing_data(user_service, user_repository):
    # Create an initial user
    user_data = {"id": 13579, "first_name": "Initial", "username": "initial_user"}
    user_repository.create_user(user_data)

    # Try to find the user with different data
    found_user = user_service.find_or_create_user(13579, "Updated", None, "updated_user")

    # Verify that the data was NOT updated
    assert found_user.first_name == "Initial"
    assert found_user.username == "initial_user"

# --- Performance Tests ---

import time

NUM_USERS_FOR_PERF_TEST = 1000

def test_performance_create_user_repository(db_session):
    repo = UserRepository(db_session)
    start_time = time.perf_counter()
    for i in range(NUM_USERS_FOR_PERF_TEST):
        user_data = {"id": 200000 + i, "first_name": f"PerfUser{i}", "username": f"perfuser{i}"}
        repo.create_user(user_data)
    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000
    avg_time_ms = total_time_ms / NUM_USERS_FOR_PERF_TEST
    print(f"\nAvg create_user (repo) time: {avg_time_ms:.2f} ms")
    assert avg_time_ms < 100 # RNF001: < 100ms for registration

def test_performance_get_user_by_id_repository(db_session):
    repo = UserRepository(db_session)
    # Pre-populate users
    for i in range(NUM_USERS_FOR_PERF_TEST):
        user_data = {"id": 300000 + i, "first_name": f"LookupUser{i}", "username": f"lookupuser{i}"}
        repo.create_user(user_data)
    
    start_time = time.perf_counter()
    for i in range(NUM_USERS_FOR_PERF_TEST):
        repo.get_user_by_id(300000 + i)
    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000
    avg_time_ms = total_time_ms / NUM_USERS_FOR_PERF_TEST
    print(f"\nAvg get_user_by_id (repo) time: {avg_time_ms:.2f} ms")
    assert avg_time_ms < 50 # RNF002: < 50ms for lookup

def test_performance_find_or_create_user_service(db_session):
    repo = UserRepository(db_session)
    service = UserService(repo)
    
    # Test creating new users
    start_time_create = time.perf_counter()
    for i in range(NUM_USERS_FOR_PERF_TEST):
        service.find_or_create_user(400000 + i, f"ServiceNew{i}", None, None)
    end_time_create = time.perf_counter()
    avg_time_create_ms = ((end_time_create - start_time_create) * 1000) / NUM_USERS_FOR_PERF_TEST
    print(f"\nAvg find_or_create (service, new) time: {avg_time_create_ms:.2f} ms")
    assert avg_time_create_ms < 100 # RNF001: < 100ms for registration

    # Test finding existing users
    start_time_find = time.perf_counter()
    for i in range(NUM_USERS_FOR_PERF_TEST):
        service.find_or_create_user(400000 + i, f"ServiceNew{i}", None, None) # Should find existing
    end_time_find = time.perf_counter()
    avg_time_find_ms = ((end_time_find - start_time_find) * 1000) / NUM_USERS_FOR_PERF_TEST
    print(f"\nAvg find_or_create (service, existing) time: {avg_time_find_ms:.2f} ms")
    assert avg_time_find_ms < 50 # RNF002: < 50ms for lookup
