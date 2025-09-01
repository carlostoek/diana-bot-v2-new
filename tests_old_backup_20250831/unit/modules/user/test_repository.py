"""Tests for UserRepository - Minimal Implementation."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import json

from src.modules.user.repository import UserRepository, create_user_repository
from src.modules.user.models import User, DuplicateUserError, UserNotFoundError, InvalidUserDataError


class TestUserRepository:
    """Test UserRepository functionality."""

    @pytest.fixture
    def mock_pool(self):
        """Mock database connection pool."""
        pool = AsyncMock()
        conn = AsyncMock()
        
        # Create proper async context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        # Make sure acquire() returns the context manager directly (not a coroutine)
        pool.acquire = MagicMock(return_value=mock_context_manager)
        
        return pool, conn

    @pytest.fixture
    def repository(self, mock_pool):
        """Create repository with mocked pool."""
        pool, conn = mock_pool
        return UserRepository(pool), pool, conn

    @pytest.fixture
    def sample_user(self):
        """Sample user for tests."""
        return User(
            user_id=123456789,
            username="diana_bot",
            first_name="Diana",
            last_name="Bot",
            language_code="es",
            is_vip=False,
            preferences={"theme": "dark"},
            telegram_metadata={"is_bot": False}
        )

    @pytest.mark.asyncio
    async def test_create_user_success(self, repository, sample_user):
        """Test successful user creation."""
        repo, pool, conn = repository
        
        # Mock no existing user
        conn.fetchrow.return_value = None
        conn.execute.return_value = None
        
        result = await repo.create(sample_user)
        
        assert result == sample_user
        conn.execute.assert_called_once()
        
        # Verify SQL call
        call_args = conn.execute.call_args
        assert "INSERT INTO users" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_user_duplicate(self, repository, sample_user):
        """Test creating duplicate user raises error."""
        repo, pool, conn = repository
        
        # Mock existing user
        conn.fetchrow.return_value = {"user_id": sample_user.user_id}
        
        with pytest.raises(DuplicateUserError, match="already exists"):
            await repo.create(sample_user)

    @pytest.mark.asyncio
    async def test_create_user_no_pool(self, sample_user):
        """Test creating user without database pool."""
        repo = UserRepository(None)
        
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            await repo.create(sample_user)

    @pytest.mark.asyncio
    async def test_get_by_user_id_success(self, repository):
        """Test successful user retrieval by ID."""
        repo, pool, conn = repository
        
        # Mock database row
        mock_row = {
            'user_id': 123456789,
            'username': 'diana_bot',
            'first_name': 'Diana',
            'last_name': 'Bot',
            'language_code': 'es',
            'is_vip': False,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': '{"theme": "dark"}',
            'telegram_metadata': '{"is_bot": false}'
        }
        conn.fetchrow.return_value = mock_row
        
        result = await repo.get_by_user_id(123456789)
        
        assert result is not None
        assert result.user_id == 123456789
        assert result.username == 'diana_bot'
        assert result.first_name == 'Diana'
        assert result.preferences == {"theme": "dark"}
        assert result.telegram_metadata == {"is_bot": False}

    @pytest.mark.asyncio
    async def test_get_by_user_id_not_found(self, repository):
        """Test user retrieval when user doesn't exist."""
        repo, pool, conn = repository
        
        conn.fetchrow.return_value = None
        
        result = await repo.get_by_user_id(999999)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_user_id_no_pool(self):
        """Test getting user without database pool."""
        repo = UserRepository(None)
        
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            await repo.get_by_user_id(123)

    @pytest.mark.asyncio
    async def test_update_user_success(self, repository, sample_user):
        """Test successful user update."""
        repo, pool, conn = repository
        
        # Mock successful update
        conn.execute.return_value = "UPDATE 1"
        
        result = await repo.update(sample_user)
        
        assert result == sample_user
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, repository, sample_user):
        """Test updating non-existent user."""
        repo, pool, conn = repository
        
        # Mock no rows updated
        conn.execute.return_value = "UPDATE 0"
        
        with pytest.raises(UserNotFoundError, match="not found"):
            await repo.update(sample_user)

    @pytest.mark.asyncio
    async def test_get_users_for_service_success(self, repository):
        """Test getting multiple users for service."""
        repo, pool, conn = repository
        
        # Mock database rows
        mock_rows = [
            {
                'user_id': 123,
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
                'user_id': 456,
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
        conn.fetch.return_value = mock_rows
        
        result = await repo.get_users_for_service([123, 456])
        
        assert len(result) == 2
        assert result[0].user_id == 123
        assert result[1].user_id == 456
        assert result[1].is_vip is True

    @pytest.mark.asyncio
    async def test_get_users_for_service_empty_list(self, repository):
        """Test getting users with empty ID list."""
        repo, pool, conn = repository
        
        result = await repo.get_users_for_service([])
        
        assert result == []
        conn.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_count_users_success(self, repository):
        """Test counting users successfully."""
        repo, pool, conn = repository
        
        conn.fetchval.return_value = 42
        
        result = await repo.count_users()
        
        assert result == 42
        conn.fetchval.assert_called_once_with("SELECT COUNT(*) FROM users")

    @pytest.mark.asyncio
    async def test_count_users_zero(self, repository):
        """Test counting users returns zero."""
        repo, pool, conn = repository
        
        conn.fetchval.return_value = 0
        
        result = await repo.count_users()
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, repository):
        """Test healthy repository health check."""
        repo, pool, conn = repository
        
        # Mock healthy responses
        conn.fetchval.side_effect = [1, 100]  # Connectivity test, user count
        
        result = await repo.health_check()
        
        assert result["status"] == "healthy"
        assert result["database"] == "connected"
        assert result["users_count"] == 100
        assert "last_check" in result

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, repository):
        """Test unhealthy repository health check."""
        repo, pool, conn = repository
        
        # Mock database error
        conn.fetchval.side_effect = Exception("Database connection failed")
        
        result = await repo.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["database"] == "disconnected"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_check_no_pool(self):
        """Test health check without pool."""
        repo = UserRepository(None)
        
        result = await repo.health_check()
        
        assert result["status"] == "unhealthy"
        assert "Database pool not initialized" in result["error"]

    def test_row_to_user_success(self, repository):
        """Test converting database row to User model."""
        repo, pool, conn = repository
        
        mock_row = {
            'user_id': 123456789,
            'username': 'diana_bot',
            'first_name': 'Diana',
            'last_name': 'Bot',
            'language_code': 'es',
            'is_vip': False,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': '{"theme": "dark"}',
            'telegram_metadata': '{"is_bot": false}'
        }
        
        result = repo._row_to_user(mock_row)
        
        assert isinstance(result, User)
        assert result.user_id == 123456789
        assert result.username == 'diana_bot'
        assert result.preferences == {"theme": "dark"}
        assert result.telegram_metadata == {"is_bot": False}

    def test_row_to_user_invalid_json(self, repository):
        """Test converting row with invalid JSON."""
        repo, pool, conn = repository
        
        mock_row = {
            'user_id': 123456789,
            'username': 'diana_bot',
            'first_name': 'Diana',
            'last_name': 'Bot',
            'language_code': 'es',
            'is_vip': False,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': 'invalid json',
            'telegram_metadata': 'also invalid'
        }
        
        with patch('src.modules.user.repository.logger') as mock_logger:
            result = repo._row_to_user(mock_row)
            
            assert result.preferences == {}
            assert result.telegram_metadata == {}
            mock_logger.warning.assert_called()


class TestCreateUserRepository:
    """Test factory function for UserRepository."""

    @pytest.mark.asyncio
    @patch('src.modules.user.repository.asyncpg')
    async def test_create_user_repository_success(self, mock_asyncpg):
        """Test successful repository creation."""
        # Mock asyncpg - create_pool should be an async function that returns a pool
        mock_pool = AsyncMock()
        mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)
        
        repository = await create_user_repository("postgresql://test")
        
        assert isinstance(repository, UserRepository)
        mock_asyncpg.create_pool.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.modules.user.repository.asyncpg', None)
    async def test_create_user_repository_no_asyncpg(self):
        """Test repository creation without asyncpg."""
        with pytest.raises(ImportError, match="asyncpg is required"):
            await create_user_repository("postgresql://test")

    @pytest.mark.asyncio
    @patch('src.modules.user.repository.asyncpg')
    async def test_create_user_repository_connection_failure(self, mock_asyncpg):
        """Test repository creation with connection failure."""
        mock_asyncpg.create_pool.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await create_user_repository("postgresql://test")


class TestRepositoryErrorHandling:
    """Test error handling in repository operations."""

    @pytest.fixture
    def mock_failing_pool(self):
        """Mock pool that raises database errors."""
        pool = AsyncMock()
        conn = AsyncMock()
        
        # Import asyncpg exceptions for proper mocking
        try:
            import asyncpg
            conn.execute.side_effect = asyncpg.PostgresError("Database error")
            conn.fetchrow.side_effect = asyncpg.PostgresError("Database error")
            conn.fetch.side_effect = asyncpg.PostgresError("Database error")
            conn.fetchval.side_effect = asyncpg.PostgresError("Database error")
        except ImportError:
            # If asyncpg not available, use generic exception
            conn.execute.side_effect = Exception("Database error")
            conn.fetchrow.side_effect = Exception("Database error")
            
        # Create proper async context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        # Make sure acquire() returns the context manager directly (not a coroutine)
        pool.acquire = MagicMock(return_value=mock_context_manager)
        
        return pool, conn

    @pytest.mark.asyncio
    async def test_create_user_database_error(self, mock_failing_pool, sample_user):
        """Test user creation with database error."""
        pool, conn = mock_failing_pool
        repo = UserRepository(pool)
        
        # First call (check duplicate) returns None, second call (insert) fails
        conn.fetchrow.side_effect = [None, Exception("Database error")]
        
        with pytest.raises(InvalidUserDataError):
            await repo.create(sample_user)

    @pytest.mark.asyncio  
    async def test_get_user_database_error(self, mock_failing_pool):
        """Test get user with database error."""
        pool, conn = mock_failing_pool
        repo = UserRepository(pool)
        
        # Should return None on database error, not raise
        result = await repo.get_by_user_id(123)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_database_error(self, mock_failing_pool, sample_user):
        """Test user update with database error."""
        pool, conn = mock_failing_pool
        repo = UserRepository(pool)
        
        with pytest.raises(InvalidUserDataError):
            await repo.update(sample_user)

    @pytest.fixture
    def sample_user(self):
        """Sample user for error handling tests."""
        return User(
            user_id=123456789,
            first_name="Diana",
            preferences={"theme": "dark"}
        )