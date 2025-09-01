"""
Fixed User Repository Unit Tests.

Tests that match the current UserRepository implementation exactly.
Focuses on async mocking and the actual methods that exist.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.modules.user.repository import UserRepository
from src.modules.user.models import User, DuplicateUserError, UserNotFoundError, InvalidUserDataError


@pytest.fixture
def mock_pool():
    """Create a mock database pool."""
    pool = AsyncMock()
    
    # Mock connection
    mock_conn = AsyncMock()
    
    # Create proper async context manager
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)
    
    # Configure pool.acquire() to return the context manager
    pool.acquire = MagicMock(return_value=mock_context_manager)
    
    return pool, mock_conn


@pytest.fixture
def user_repository(mock_pool):
    """Create UserRepository with mocked pool."""
    pool, conn = mock_pool
    return UserRepository(pool), conn


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        user_id=12345,
        first_name="Test User",
        username="testuser",
        last_name="Lastname",
        language_code="es",
        is_vip=False
    )


@pytest.mark.asyncio
class TestUserRepositoryCreate:
    """Test UserRepository.create() method."""

    async def test_create_user_success(self, user_repository, sample_user):
        """Test successful user creation."""
        repo, mock_conn = user_repository
        
        # Mock no existing user
        mock_conn.fetchrow.return_value = None
        mock_conn.execute.return_value = None
        
        result = await repo.create(sample_user)
        
        # Verify the result is the same user
        assert result == sample_user
        
        # Verify database calls
        mock_conn.fetchrow.assert_called_once()  # Check for existing user
        mock_conn.execute.assert_called_once()   # Insert new user

    async def test_create_user_duplicate_error(self, user_repository, sample_user):
        """Test creation fails when user already exists."""
        repo, mock_conn = user_repository
        
        # Mock existing user found
        mock_conn.fetchrow.return_value = {"user_id": 12345}
        
        with pytest.raises(DuplicateUserError):
            await repo.create(sample_user)

    async def test_create_user_no_pool(self, sample_user):
        """Test creation fails when pool is not initialized."""
        repo = UserRepository(None)
        
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            await repo.create(sample_user)


@pytest.mark.asyncio
class TestUserRepositoryRead:
    """Test UserRepository read operations."""

    async def test_get_by_user_id_success(self, user_repository, sample_user):
        """Test successful user retrieval by user_id."""
        repo, mock_conn = user_repository
        
        # Mock database row
        mock_row = {
            'user_id': 12345,
            'username': 'testuser',
            'first_name': 'Test User',
            'last_name': 'Lastname',
            'language_code': 'es',
            'is_vip': False,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': '{}',
            'telegram_metadata': '{}'
        }
        mock_conn.fetchrow.return_value = mock_row
        
        result = await repo.get_by_user_id(12345)
        
        assert result is not None
        assert result.user_id == 12345
        assert result.first_name == "Test User"
        assert result.username == "testuser"

    async def test_get_by_user_id_not_found(self, user_repository):
        """Test user not found returns None."""
        repo, mock_conn = user_repository
        
        # Mock no user found
        mock_conn.fetchrow.return_value = None
        
        result = await repo.get_by_user_id(99999)
        
        assert result is None

    async def test_get_by_user_id_no_pool(self):
        """Test get fails when pool is not initialized."""
        repo = UserRepository(None)
        
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            await repo.get_by_user_id(12345)


@pytest.mark.asyncio
class TestUserRepositoryUpdate:
    """Test UserRepository.update() method."""

    async def test_update_user_success(self, user_repository, sample_user):
        """Test successful user update."""
        repo, mock_conn = user_repository
        
        # Mock successful update (not "UPDATE 0")
        mock_conn.execute.return_value = "UPDATE 1"
        
        result = await repo.update(sample_user)
        
        assert result == sample_user
        mock_conn.execute.assert_called_once()

    async def test_update_user_not_found(self, user_repository, sample_user):
        """Test update fails when user doesn't exist."""
        repo, mock_conn = user_repository
        
        # Mock no rows updated
        mock_conn.execute.return_value = "UPDATE 0"
        
        with pytest.raises(UserNotFoundError):
            await repo.update(sample_user)

    async def test_update_user_no_pool(self, sample_user):
        """Test update fails when pool is not initialized."""
        repo = UserRepository(None)
        
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            await repo.update(sample_user)


@pytest.mark.asyncio
class TestUserRepositoryBatch:
    """Test UserRepository batch operations."""

    async def test_get_users_for_service_success(self, user_repository):
        """Test getting multiple users for service integration."""
        repo, mock_conn = user_repository
        
        # Mock multiple users
        mock_rows = [
            {
                'user_id': 1,
                'username': 'user1',
                'first_name': 'User',
                'last_name': 'One',
                'language_code': 'es',
                'is_vip': False,
                'created_at': datetime.now(timezone.utc),
                'last_active': datetime.now(timezone.utc),
                'preferences': '{}',
                'telegram_metadata': '{}'
            },
            {
                'user_id': 2,
                'username': 'user2',
                'first_name': 'User',
                'last_name': 'Two',
                'language_code': 'en',
                'is_vip': True,
                'created_at': datetime.now(timezone.utc),
                'last_active': datetime.now(timezone.utc),
                'preferences': '{}',
                'telegram_metadata': '{}'
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        result = await repo.get_users_for_service([1, 2])
        
        assert len(result) == 2
        assert result[0].user_id == 1
        assert result[1].user_id == 2
        assert result[1].is_vip is True

    async def test_get_users_for_service_empty_list(self, user_repository):
        """Test getting users with empty ID list."""
        repo, _ = user_repository
        
        result = await repo.get_users_for_service([])
        
        assert result == []

    async def test_count_users_success(self, user_repository):
        """Test counting total users."""
        repo, mock_conn = user_repository
        
        mock_conn.fetchval.return_value = 42
        
        result = await repo.count_users()
        
        assert result == 42

    async def test_count_users_no_pool(self):
        """Test count fails when pool is not initialized."""
        repo = UserRepository(None)
        
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            await repo.count_users()


@pytest.mark.asyncio
class TestUserRepositoryHealthCheck:
    """Test UserRepository health check."""

    async def test_health_check_success(self, user_repository):
        """Test successful health check."""
        repo, mock_conn = user_repository
        
        # Mock successful database operations
        mock_conn.fetchval.side_effect = [1, 100]  # SELECT 1, then COUNT
        
        result = await repo.health_check()
        
        assert result["status"] == "healthy"
        assert result["database"] == "connected"
        assert result["users_count"] == 100

    async def test_health_check_no_pool(self):
        """Test health check when pool is not initialized."""
        repo = UserRepository(None)
        
        result = await repo.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["database"] == "disconnected"
        assert "error" in result


class TestUserRepositoryErrorConditions:
    """Test UserRepository error conditions and edge cases."""

    @patch('src.modules.user.repository.asyncpg', None)
    def test_repository_init_without_asyncpg(self):
        """Test UserRepository initialization fails without asyncpg."""
        with pytest.raises(ImportError, match="asyncpg is required but not installed"):
            from src.modules.user.repository import UserRepository
            UserRepository()

    @pytest.mark.asyncio
    async def test_database_errors_in_operations(self, user_repository, sample_user):
        """Test database error handling in operations."""
        repo, mock_conn = user_repository
        
        # Mock asyncpg.PostgresError - need to import it properly
        import asyncpg
        
        # Test database error in create operation
        mock_conn.fetchrow.side_effect = asyncpg.PostgresError("Database connection error")
        
        with pytest.raises(InvalidUserDataError):
            await repo.create(sample_user)

    @pytest.mark.asyncio
    async def test_database_errors_in_get_operations(self, user_repository):
        """Test database error handling in get operations."""
        repo, mock_conn = user_repository
        
        import asyncpg
        
        # Test database error in get_by_user_id
        mock_conn.fetchrow.side_effect = asyncpg.PostgresError("Database connection error")
        
        result = await repo.get_by_user_id(12345)
        assert result is None  # Should return None on database error

    @pytest.mark.asyncio
    async def test_database_errors_in_update(self, user_repository, sample_user):
        """Test database error handling in update operations.""" 
        repo, mock_conn = user_repository
        
        import asyncpg
        
        # Test database error in update
        mock_conn.execute.side_effect = asyncpg.PostgresError("Database connection error")
        
        with pytest.raises(InvalidUserDataError):
            await repo.update(sample_user)

    @pytest.mark.asyncio
    async def test_database_errors_in_batch_operations(self, user_repository):
        """Test database error handling in batch operations."""
        repo, mock_conn = user_repository
        
        import asyncpg
        
        # Test error in get_users_for_service
        mock_conn.fetch.side_effect = asyncpg.PostgresError("Database connection error")
        
        result = await repo.get_users_for_service([1, 2, 3])
        assert result == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_database_errors_in_count(self, user_repository):
        """Test database error handling in count operations."""
        repo, mock_conn = user_repository
        
        import asyncpg
        
        # Test error in count_users
        mock_conn.fetchval.side_effect = asyncpg.PostgresError("Database connection error")
        
        result = await repo.count_users()
        assert result == 0  # Should return 0 on error

    @pytest.mark.asyncio
    async def test_health_check_with_database_errors(self, user_repository):
        """Test health check behavior with database errors."""
        repo, mock_conn = user_repository
        
        # Test database error in health check
        mock_conn.fetchval.side_effect = Exception("Database connection failed")
        
        health = await repo.health_check()
        
        assert health["status"] == "unhealthy"
        assert "error" in health
        assert "Database connection failed" in health["error"]

    @patch('src.modules.user.repository.asyncpg', None)
    @pytest.mark.asyncio
    async def test_create_user_repository_without_asyncpg(self):
        """Test create_user_repository fails without asyncpg."""
        from src.modules.user.repository import create_user_repository
        
        with pytest.raises(ImportError, match="asyncpg is required but not installed"):
            await create_user_repository("postgresql://test:test@localhost/test")

    @pytest.mark.asyncio
    async def test_create_user_repository_with_connection_error(self):
        """Test create_user_repository handles connection errors."""
        from src.modules.user.repository import create_user_repository
        
        with patch('src.modules.user.repository.asyncpg.create_pool') as mock_create_pool:
            # Make create_pool raise an exception
            async def failing_create_pool(*args, **kwargs):
                raise Exception("Connection failed")
            
            mock_create_pool.side_effect = failing_create_pool
            
            with pytest.raises(Exception, match="Connection failed"):
                await create_user_repository("postgresql://invalid:invalid@localhost/invalid")


class TestUserRepositoryHelpers:
    """Test UserRepository helper methods."""

    def test_row_to_user_success(self, user_repository):
        """Test _row_to_user conversion success."""
        repo, _ = user_repository
        
        mock_row = {
            'user_id': 12345,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'language_code': 'es',
            'is_vip': True,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': '{"theme": "dark"}',
            'telegram_metadata': '{"chat_id": 123}'
        }
        
        user = repo._row_to_user(mock_row)
        
        assert user.user_id == 12345
        assert user.username == 'testuser'
        assert user.first_name == 'Test'
        assert user.is_vip is True
        assert user.preferences == {"theme": "dark"}
        assert user.telegram_metadata == {"chat_id": 123}

    def test_row_to_user_invalid_json(self, user_repository):
        """Test _row_to_user handles invalid JSON gracefully."""
        repo, _ = user_repository
        
        mock_row = {
            'user_id': 12345,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'language_code': 'es',
            'is_vip': False,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': 'invalid json',  # Invalid JSON
            'telegram_metadata': 'also invalid'  # Invalid JSON
        }
        
        user = repo._row_to_user(mock_row)
        
        # Should handle invalid JSON gracefully
        assert user.user_id == 12345
        assert user.preferences == {}  # Defaults to empty dict
        assert user.telegram_metadata == {}  # Defaults to empty dict