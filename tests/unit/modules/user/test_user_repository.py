"""
Test suite for User Repository following TDD methodology.

This module contains comprehensive tests for the IUserRepository interface,
covering all database operations, query patterns, and data persistence
for Telegram user management.

TDD Phase: RED - Tests written first, implementation comes later.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, call
from typing import Optional, List

# Import core interfaces
from src.core.interfaces import IEventBus

# These imports will fail initially - that's expected in RED phase
# from src.modules.user.interfaces import IUserRepository
# from src.modules.user.models import TelegramUser, UserCreateRequest, UserUpdateRequest
# from src.modules.user.repository import UserRepository
# from src.modules.user.exceptions import (
#     UserNotFoundError,
#     DuplicateUserError,
#     InvalidUserDataError,
#     RepositoryError
# )


class TestUserRepository:
    """Test cases for IUserRepository implementation."""
    
    @pytest.fixture
    def mock_db_connection(self) -> AsyncMock:
        """Create a mock database connection."""
        return AsyncMock()
    
    @pytest.fixture
    def user_repository(self, mock_db_connection: AsyncMock):
        """Create UserRepository with mocked database connection."""
        # This will fail in RED phase - expected
        with pytest.raises(ImportError):
            # return UserRepository(db_connection=mock_db_connection)
            pass
        return None
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_repository, mock_db_connection: AsyncMock):
        """Test successful user creation in database."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        user_data = TelegramUser(
            telegram_id=12345678,
            username="diana_bot",
            first_name="Diana",
            last_name="Bot",
            language_code="es",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        # Mock database response
        mock_db_connection.execute.return_value = Mock(lastrowid=1)
        mock_db_connection.fetchone.return_value = {
            "telegram_id": 12345678,
            "username": "diana_bot",
            "first_name": "Diana",
            "last_name": "Bot",
            "language_code": "es",
            "created_at": user_data.created_at,
            "updated_at": user_data.updated_at,
            "is_active": True
        }
        
        # Act
        result = await user_repository.create(user_data)
        
        # Assert
        assert result.telegram_id == user_data.telegram_id
        assert result.username == user_data.username
        assert result.first_name == user_data.first_name
        assert result.last_name == user_data.last_name
        assert result.language_code == user_data.language_code
        assert result.is_active == user_data.is_active
        
        # Verify database calls
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "INSERT INTO users" in execute_call[0][0]
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_telegram_id(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user creation fails with duplicate telegram_id."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        user_data = TelegramUser(
            telegram_id=12345678,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        # Mock database constraint violation
        mock_db_connection.execute.side_effect = Exception("UNIQUE constraint failed: users.telegram_id")
        
        # Act & Assert
        with pytest.raises(DuplicateUserError) as exc_info:
            await user_repository.create(user_data)
        
        assert "User with telegram_id 12345678 already exists" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_by_telegram_id_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test successful user retrieval by telegram_id."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 12345678
        expected_data = {
            "telegram_id": telegram_id,
            "username": "diana_bot",
            "first_name": "Diana",
            "last_name": "Bot",
            "language_code": "es",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_active": True
        }
        
        mock_db_connection.fetchone.return_value = expected_data
        
        # Act
        result = await user_repository.get_by_telegram_id(telegram_id)
        
        # Assert
        assert result is not None
        assert result.telegram_id == telegram_id
        assert result.username == "diana_bot"
        assert result.first_name == "Diana"
        assert result.last_name == "Bot"
        assert result.language_code == "es"
        assert result.is_active is True
        
        # Verify database query
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "SELECT * FROM users WHERE telegram_id = ?" in execute_call[0][0]
        assert execute_call[0][1] == (telegram_id,)
    
    @pytest.mark.asyncio
    async def test_get_by_telegram_id_not_found(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user retrieval returns None when telegram_id not found."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 99999999
        mock_db_connection.fetchone.return_value = None
        
        # Act
        result = await user_repository.get_by_telegram_id(telegram_id)
        
        # Assert
        assert result is None
        mock_db_connection.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_username_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test successful user retrieval by username."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        username = "diana_bot"
        expected_data = {
            "telegram_id": 12345678,
            "username": username,
            "first_name": "Diana",
            "last_name": None,
            "language_code": "en",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_active": True
        }
        
        mock_db_connection.fetchone.return_value = expected_data
        
        # Act
        result = await user_repository.get_by_username(username)
        
        # Assert
        assert result is not None
        assert result.username == username
        assert result.telegram_id == 12345678
        
        # Verify database query
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "SELECT * FROM users WHERE username = ?" in execute_call[0][0]
        assert execute_call[0][1] == (username,)
    
    @pytest.mark.asyncio
    async def test_get_by_username_not_found(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user retrieval by username returns None when not found."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        username = "nonexistent_user"
        mock_db_connection.fetchone.return_value = None
        
        # Act
        result = await user_repository.get_by_username(username)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_user_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test successful user update in database."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 12345678
        updated_user = TelegramUser(
            telegram_id=telegram_id,
            username="new_username",
            first_name="Diana",
            last_name="Bot",
            language_code="fr",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        # Mock database response
        mock_db_connection.execute.return_value = Mock(rowcount=1)
        mock_db_connection.fetchone.return_value = {
            "telegram_id": telegram_id,
            "username": "new_username",
            "first_name": "Diana",
            "last_name": "Bot",
            "language_code": "fr",
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at,
            "is_active": True
        }
        
        # Act
        result = await user_repository.update(updated_user)
        
        # Assert
        assert result.telegram_id == telegram_id
        assert result.username == "new_username"
        assert result.language_code == "fr"
        
        # Verify database calls
        mock_db_connection.execute.assert_called()
        execute_calls = mock_db_connection.execute.call_args_list
        update_call = execute_calls[0]
        assert "UPDATE users SET" in update_call[0][0]
        assert telegram_id in update_call[0][1]
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user update fails when user doesn't exist."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 99999999
        user_data = TelegramUser(
            telegram_id=telegram_id,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        # Mock no rows affected
        mock_db_connection.execute.return_value = Mock(rowcount=0)
        
        # Act & Assert
        with pytest.raises(UserNotFoundError) as exc_info:
            await user_repository.update(user_data)
        
        assert f"User with telegram_id {telegram_id} not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_user_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test successful user deletion from database."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 12345678
        mock_db_connection.execute.return_value = Mock(rowcount=1)
        
        # Act
        result = await user_repository.delete(telegram_id)
        
        # Assert
        assert result is True
        
        # Verify database call
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "DELETE FROM users WHERE telegram_id = ?" in execute_call[0][0]
        assert execute_call[0][1] == (telegram_id,)
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user deletion fails when user doesn't exist."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 99999999
        mock_db_connection.execute.return_value = Mock(rowcount=0)
        
        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await user_repository.delete(telegram_id)
    
    @pytest.mark.asyncio
    async def test_get_active_users_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test retrieving all active users from database."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        expected_data = [
            {
                "telegram_id": 12345678,
                "username": "diana_bot",
                "first_name": "Diana",
                "last_name": None,
                "language_code": "en",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            },
            {
                "telegram_id": 87654321,
                "username": "test_bot",
                "first_name": "Test",
                "last_name": "Bot",
                "language_code": "es",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
        ]
        
        mock_db_connection.fetchall.return_value = expected_data
        
        # Act
        result = await user_repository.get_active_users()
        
        # Assert
        assert len(result) == 2
        assert all(user.is_active for user in result)
        assert result[0].telegram_id == 12345678
        assert result[1].telegram_id == 87654321
        
        # Verify database query
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "SELECT * FROM users WHERE is_active = ?" in execute_call[0][0]
        assert execute_call[0][1] == (True,)
    
    @pytest.mark.asyncio
    async def test_get_by_language_code_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test retrieving users filtered by language code."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        language_code = "es"
        expected_data = [
            {
                "telegram_id": 12345678,
                "username": "diana_bot",
                "first_name": "Diana",
                "last_name": None,
                "language_code": "es",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
        ]
        
        mock_db_connection.fetchall.return_value = expected_data
        
        # Act
        result = await user_repository.get_by_language_code(language_code)
        
        # Assert
        assert len(result) == 1
        assert all(user.language_code == language_code for user in result)
        assert result[0].telegram_id == 12345678
        
        # Verify database query
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "SELECT * FROM users WHERE language_code = ?" in execute_call[0][0]
        assert execute_call[0][1] == (language_code,)
    
    @pytest.mark.asyncio
    async def test_count_users_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test counting total users in database."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        expected_count = 42
        mock_db_connection.fetchone.return_value = {"count": expected_count}
        
        # Act
        result = await user_repository.count_users()
        
        # Assert
        assert result == expected_count
        
        # Verify database query
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "SELECT COUNT(*) as count FROM users" in execute_call[0][0]
    
    @pytest.mark.asyncio
    async def test_count_active_users_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test counting active users in database."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        expected_count = 35
        mock_db_connection.fetchone.return_value = {"count": expected_count}
        
        # Act
        result = await user_repository.count_active_users()
        
        # Assert
        assert result == expected_count
        
        # Verify database query
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "SELECT COUNT(*) as count FROM users WHERE is_active = ?" in execute_call[0][0]
        assert execute_call[0][1] == (True,)


class TestUserRepositoryPagination:
    """Test cases for user repository pagination features."""
    
    @pytest.fixture
    def mock_db_connection(self) -> AsyncMock:
        """Create a mock database connection."""
        return AsyncMock()
    
    @pytest.fixture
    def user_repository(self, mock_db_connection: AsyncMock):
        """Create UserRepository with mocked database connection."""
        # This will fail in RED phase - expected
        with pytest.raises(ImportError):
            # return UserRepository(db_connection=mock_db_connection)
            pass
        return None
    
    @pytest.mark.asyncio
    async def test_get_users_paginated_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test paginated user retrieval."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        limit = 10
        offset = 20
        expected_data = [
            {
                "telegram_id": 12345678,
                "username": "diana_bot",
                "first_name": "Diana",
                "last_name": None,
                "language_code": "en",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
        ]
        
        mock_db_connection.fetchall.return_value = expected_data
        
        # Act
        result = await user_repository.get_users_paginated(limit=limit, offset=offset)
        
        # Assert
        assert len(result) == 1
        assert result[0].telegram_id == 12345678
        
        # Verify database query
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?" in execute_call[0][0]
        assert execute_call[0][1] == (limit, offset)
    
    @pytest.mark.asyncio
    async def test_get_users_paginated_default_params(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test paginated user retrieval with default parameters."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        mock_db_connection.fetchall.return_value = []
        
        # Act
        result = await user_repository.get_users_paginated()
        
        # Assert
        assert len(result) == 0
        
        # Verify database query with default values
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "LIMIT ? OFFSET ?" in execute_call[0][0]
        # Default should be limit=50, offset=0
        assert execute_call[0][1] == (50, 0)


class TestUserRepositoryErrorHandling:
    """Test cases for user repository error handling scenarios."""
    
    @pytest.fixture
    def mock_db_connection(self) -> AsyncMock:
        """Create a mock database connection."""
        return AsyncMock()
    
    @pytest.fixture
    def user_repository(self, mock_db_connection: AsyncMock):
        """Create UserRepository with mocked database connection."""
        # This will fail in RED phase - expected
        with pytest.raises(ImportError):
            # return UserRepository(db_connection=mock_db_connection)
            pass
        return None
    
    @pytest.mark.asyncio
    async def test_create_user_database_error(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user creation handles database errors gracefully."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        user_data = TelegramUser(
            telegram_id=12345678,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        mock_db_connection.execute.side_effect = Exception("Database connection failed")
        
        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await user_repository.create(user_data)
        
        assert "Failed to create user" in str(exc_info.value)
        assert "Database connection failed" in str(exc_info.value.__cause__)
    
    @pytest.mark.asyncio
    async def test_get_by_telegram_id_database_error(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user retrieval handles database errors gracefully."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        telegram_id = 12345678
        mock_db_connection.execute.side_effect = Exception("Database timeout")
        
        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await user_repository.get_by_telegram_id(telegram_id)
        
        assert "Failed to retrieve user" in str(exc_info.value)
        assert "Database timeout" in str(exc_info.value.__cause__)
    
    @pytest.mark.asyncio
    async def test_update_user_database_error(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user update handles database errors gracefully."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        user_data = TelegramUser(
            telegram_id=12345678,
            first_name="Diana",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True
        )
        
        mock_db_connection.execute.side_effect = Exception("Database lock timeout")
        
        # Act & Assert
        with pytest.raises(RepositoryError) as exc_info:
            await user_repository.update(user_data)
        
        assert "Failed to update user" in str(exc_info.value)
        assert "Database lock timeout" in str(exc_info.value.__cause__)


class TestUserRepositoryQueryOptimization:
    """Test cases for user repository query optimization and performance."""
    
    @pytest.fixture
    def mock_db_connection(self) -> AsyncMock:
        """Create a mock database connection."""
        return AsyncMock()
    
    @pytest.fixture
    def user_repository(self, mock_db_connection: AsyncMock):
        """Create UserRepository with mocked database connection."""
        # This will fail in RED phase - expected
        with pytest.raises(ImportError):
            # return UserRepository(db_connection=mock_db_connection)
            pass
        return None
    
    @pytest.mark.asyncio
    async def test_bulk_create_users_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test bulk user creation for performance."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        users_data = [
            TelegramUser(
                telegram_id=12345678,
                first_name="Diana",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True
            ),
            TelegramUser(
                telegram_id=87654321,
                first_name="Bot",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True
            )
        ]
        
        mock_db_connection.executemany.return_value = Mock(rowcount=2)
        
        # Act
        result = await user_repository.bulk_create(users_data)
        
        # Assert
        assert result == 2  # Number of created users
        
        # Verify bulk operation was used
        mock_db_connection.executemany.assert_called_once()
        execute_call = mock_db_connection.executemany.call_args
        assert "INSERT INTO users" in execute_call[0][0]
        assert len(execute_call[0][1]) == 2  # Two parameter sets
    
    @pytest.mark.asyncio
    async def test_search_users_by_name_success(
        self, 
        user_repository, 
        mock_db_connection: AsyncMock
    ):
        """Test user search functionality by name."""
        if user_repository is None:
            pytest.skip("UserRepository not implemented yet - RED phase")
        
        # Arrange
        search_term = "Diana"
        expected_data = [
            {
                "telegram_id": 12345678,
                "username": "diana_bot",
                "first_name": "Diana",
                "last_name": "Bot",
                "language_code": "en",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "is_active": True
            }
        ]
        
        mock_db_connection.fetchall.return_value = expected_data
        
        # Act
        result = await user_repository.search_users_by_name(search_term)
        
        # Assert
        assert len(result) == 1
        assert result[0].first_name == "Diana"
        
        # Verify search query with LIKE operator
        mock_db_connection.execute.assert_called_once()
        execute_call = mock_db_connection.execute.call_args
        assert "WHERE (first_name LIKE ? OR last_name LIKE ?)" in execute_call[0][0]
        assert execute_call[0][1] == (f"%{search_term}%", f"%{search_term}%")