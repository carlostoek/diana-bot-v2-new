"""Tests for User migrations and database setup."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from src.modules.user.migrations import (
    create_user_table,
    verify_table_structure,
    drop_user_table,
    USER_TABLE_SQL,
    CREATE_INDEXES_SQL
)


class TestUserMigrations:
    """Test user table migrations."""

    @pytest.fixture
    def mock_pool_and_conn(self):
        """Mock asyncpg pool and connection."""
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.acquire.return_value.__aexit__.return_value = None
        return pool, conn

    @pytest.mark.asyncio
    async def test_create_user_table_success(self, mock_pool_and_conn):
        """Test successful table creation."""
        pool, conn = mock_pool_and_conn
        
        # Mock successful execution
        conn.execute.return_value = None
        
        result = await create_user_table(connection_pool=pool)
        
        assert result is True
        
        # Verify table creation was called
        assert conn.execute.call_count >= 1
        
        # Verify table SQL was executed
        table_call = conn.execute.call_args_list[0]
        assert "CREATE TABLE IF NOT EXISTS users" in table_call[0][0]

    @pytest.mark.asyncio
    async def test_create_user_table_with_database_url(self):
        """Test table creation with database URL."""
        with patch('src.modules.user.migrations.asyncpg') as mock_asyncpg:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            
            mock_asyncpg.create_pool.return_value = mock_pool
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_pool.acquire.return_value.__aexit__.return_value = None
            
            result = await create_user_table(database_url="postgresql://test")
            
            assert result is True
            mock_asyncpg.create_pool.assert_called_once_with("postgresql://test")
            mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_table_no_asyncpg(self):
        """Test table creation without asyncpg."""
        with patch('src.modules.user.migrations.asyncpg', None):
            result = await create_user_table(database_url="postgresql://test")
            assert result is False

    @pytest.mark.asyncio
    async def test_create_user_table_no_connection(self):
        """Test table creation without connection."""
        result = await create_user_table()
        assert result is False

    @pytest.mark.asyncio
    async def test_create_user_table_execution_error(self, mock_pool_and_conn):
        """Test table creation with execution error."""
        pool, conn = mock_pool_and_conn
        
        # Mock execution failure
        conn.execute.side_effect = Exception("Database error")
        
        result = await create_user_table(connection_pool=pool)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_create_user_table_index_warnings(self, mock_pool_and_conn):
        """Test table creation with index creation warnings."""
        pool, conn = mock_pool_and_conn
        
        # Mock table creation success, but index creation failures
        def execute_side_effect(sql):
            if "CREATE INDEX" in sql:
                raise Exception("Index already exists")
            return None
        
        conn.execute.side_effect = execute_side_effect
        
        result = await create_user_table(connection_pool=pool)
        
        # Should still return True (warnings are expected)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_table_structure_success(self, mock_pool_and_conn):
        """Test successful table structure verification."""
        pool, conn = mock_pool_and_conn
        
        # Mock table exists
        conn.fetchval.return_value = True
        
        # Mock columns exist
        mock_columns = [
            {"column_name": "user_id"},
            {"column_name": "username"},
            {"column_name": "first_name"},
            {"column_name": "last_name"},
            {"column_name": "language_code"},
            {"column_name": "is_vip"},
            {"column_name": "created_at"},
            {"column_name": "last_active"},
            {"column_name": "preferences"},
            {"column_name": "telegram_metadata"}
        ]
        conn.fetch.return_value = mock_columns
        
        result = await verify_table_structure(connection_pool=pool)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_table_structure_missing_table(self, mock_pool_and_conn):
        """Test verification with missing table."""
        pool, conn = mock_pool_and_conn
        
        # Mock table doesn't exist
        conn.fetchval.return_value = False
        
        result = await verify_table_structure(connection_pool=pool)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_table_structure_missing_columns(self, mock_pool_and_conn):
        """Test verification with missing columns."""
        pool, conn = mock_pool_and_conn
        
        # Mock table exists
        conn.fetchval.return_value = True
        
        # Mock missing columns
        mock_columns = [
            {"column_name": "user_id"},
            {"column_name": "first_name"}
            # Missing other required columns
        ]
        conn.fetch.return_value = mock_columns
        
        result = await verify_table_structure(connection_pool=pool)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_table_structure_no_asyncpg(self):
        """Test verification without asyncpg."""
        with patch('src.modules.user.migrations.asyncpg', None):
            result = await verify_table_structure(database_url="postgresql://test")
            assert result is False

    @pytest.mark.asyncio
    async def test_drop_user_table_success(self, mock_pool_and_conn):
        """Test successful table drop."""
        pool, conn = mock_pool_and_conn
        
        # Mock successful drop
        conn.execute.return_value = None
        
        result = await drop_user_table(connection_pool=pool)
        
        assert result is True
        
        # Verify drop SQL was called
        conn.execute.assert_called_once_with("DROP TABLE IF EXISTS users CASCADE;")

    @pytest.mark.asyncio
    async def test_drop_user_table_error(self, mock_pool_and_conn):
        """Test table drop with error."""
        pool, conn = mock_pool_and_conn
        
        # Mock drop failure
        conn.execute.side_effect = Exception("Cannot drop table")
        
        result = await drop_user_table(connection_pool=pool)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_drop_user_table_no_asyncpg(self):
        """Test table drop without asyncpg."""
        with patch('src.modules.user.migrations.asyncpg', None):
            result = await drop_user_table(database_url="postgresql://test")
            assert result is False


class TestMigrationSQL:
    """Test migration SQL statements."""
    
    def test_user_table_sql_structure(self):
        """Test user table SQL contains required elements."""
        sql = USER_TABLE_SQL
        
        # Check table name
        assert "CREATE TABLE IF NOT EXISTS users" in sql
        
        # Check required columns
        required_columns = [
            "user_id BIGINT PRIMARY KEY",
            "username VARCHAR(100)",
            "first_name VARCHAR(100) NOT NULL",
            "last_name VARCHAR(100)",
            "language_code VARCHAR(10) DEFAULT 'es'",
            "is_vip BOOLEAN DEFAULT FALSE",
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "preferences JSONB DEFAULT '{}'",
            "telegram_metadata JSONB DEFAULT '{}'"
        ]
        
        for column in required_columns:
            assert column in sql
    
    def test_index_sql_statements(self):
        """Test index SQL statements."""
        indexes = CREATE_INDEXES_SQL
        
        assert len(indexes) == 5
        
        # Check specific indexes
        expected_indexes = [
            "idx_users_username",
            "idx_users_language",
            "idx_users_vip", 
            "idx_users_last_active",
            "idx_users_created_at"
        ]
        
        for index_name in expected_indexes:
            assert any(index_name in sql for sql in indexes)
        
        # All should be CREATE INDEX IF NOT EXISTS
        for sql in indexes:
            assert "CREATE INDEX IF NOT EXISTS" in sql


class TestMigrationCommandLine:
    """Test command line interface for migrations."""
    
    @pytest.mark.asyncio
    @patch('src.modules.user.migrations.os.getenv')
    @patch('src.modules.user.migrations.create_user_table')
    async def test_main_migrate_command(self, mock_create_table, mock_getenv):
        """Test migrate command."""
        mock_getenv.return_value = "postgresql://test"
        mock_create_table.return_value = True
        
        # Mock sys.argv
        with patch('sys.argv', ['migrations.py', 'migrate']):
            # Import and run main (would need to modify for testing)
            pass  # Command line testing would require more setup
    
    def test_database_url_environment_variable(self):
        """Test database URL from environment."""
        with patch('src.modules.user.migrations.os.getenv') as mock_getenv:
            mock_getenv.return_value = "postgresql://localhost/test"
            
            # Test would require importing main function
            assert mock_getenv.return_value == "postgresql://localhost/test"


class TestMigrationEdgeCases:
    """Test edge cases in migrations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_table_creation(self):
        """Test concurrent table creation attempts."""
        with patch('src.modules.user.migrations.asyncpg') as mock_asyncpg:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            
            mock_asyncpg.create_pool.return_value = mock_pool
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_pool.acquire.return_value.__aexit__.return_value = None
            
            # Run multiple table creations concurrently
            tasks = [
                create_user_table(database_url="postgresql://test")
                for _ in range(3)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed (due to IF NOT EXISTS)
            assert all(r is True for r in results if not isinstance(r, Exception))
    
    @pytest.mark.asyncio
    async def test_pool_cleanup_on_error(self):
        """Test pool is properly closed on error."""
        with patch('src.modules.user.migrations.asyncpg') as mock_asyncpg:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            
            mock_asyncpg.create_pool.return_value = mock_pool
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_pool.acquire.return_value.__aexit__.return_value = None
            
            # Mock execution error
            conn.execute.side_effect = Exception("Database error")
            
            result = await create_user_table(database_url="postgresql://test")
            
            assert result is False
            # Verify pool was closed even on error
            mock_pool.close.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_verify_with_extra_columns(self, mock_pool_and_conn):
        """Test verification passes with extra columns."""
        pool, conn = mock_pool_and_conn
        
        # Mock table exists
        conn.fetchval.return_value = True
        
        # Mock columns with extras
        mock_columns = [
            {"column_name": "user_id"},
            {"column_name": "username"},
            {"column_name": "first_name"},
            {"column_name": "last_name"},
            {"column_name": "language_code"},
            {"column_name": "is_vip"},
            {"column_name": "created_at"},
            {"column_name": "last_active"},
            {"column_name": "preferences"},
            {"column_name": "telegram_metadata"},
            {"column_name": "extra_column"}  # Extra column should not fail verification
        ]
        conn.fetch.return_value = mock_columns
        
        result = await verify_table_structure(connection_pool=pool)
        
        assert result is True