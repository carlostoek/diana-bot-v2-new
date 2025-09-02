import pytest
from src.domain.models import User, UserRole
from src.infrastructure.repositories import UserRepository


@pytest.mark.asyncio
async def test_user_repository_add_and_get(db_session):
    """
    Test adding a user with the repository and retrieving it.
    """
    user_repo = UserRepository(db_session)

    # Create a new user
    new_user = User(
        id=12345,
        first_name="John",
        last_name="Doe",
        username="johndoe",
        role=UserRole.FREE,
    )

    # Add the user to the database
    await user_repo.add(new_user)
    await db_session.commit()

    # Retrieve the user by ID
    retrieved_user = await user_repo.get(12345)

    assert retrieved_user is not None
    assert retrieved_user.id == 12345
    assert retrieved_user.first_name == "John"
    assert retrieved_user.username == "johndoe"
    assert retrieved_user.role == UserRole.FREE


@pytest.mark.asyncio
async def test_user_repository_list(db_session):
    """
    Test listing users from the repository.
    """
    user_repo = UserRepository(db_session)

    # Add some users
    user1 = User(id=1, first_name="Alice")
    user2 = User(id=2, first_name="Bob")
    await user_repo.add(user1)
    await user_repo.add(user2)
    await db_session.commit()

    # List all users
    all_users = await user_repo.list()

    assert len(all_users) == 2
    assert {user.id for user in all_users} == {1, 2}
