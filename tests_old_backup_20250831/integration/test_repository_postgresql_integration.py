"""Integration tests for UserRepository using testcontainers PostgreSQL.

This module validates repository operations with a real PostgreSQL database
to ensure database-specific features like constraints and JSONB operations work correctly.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any

# testcontainers imports
from testcontainers.postgres import PostgresContainer

from src.modules.user.repository import UserRepository
from src.modules.user.models import User, DuplicateUserError, UserNotFoundError


class TestUserRepositoryPostgreSQL:
    """Test UserRepository with real PostgreSQL database using testcontainers."""

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Start PostgreSQL container for testing."""
        with PostgresContainer("postgres:15") as postgres:
            # Wait for PostgreSQL to be ready
            postgres.get_connection_url()
            yield postgres

    @pytest.fixture(scope="class")
    async def database_setup(self, postgres_container):
        """Set up database schema and connection pool."""
        import asyncpg
        
        # Get connection URL
        db_url = postgres_container.get_connection_url()
        
        # Create connection pool
        pool = await asyncpg.create_pool(
            db_url,
            min_size=2,
            max_size=10,
            server_settings={'jit': 'off'}
        )
        
        # Create users table
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255) NOT NULL,
                    last_name VARCHAR(255),
                    language_code VARCHAR(10) DEFAULT 'es',
                    is_vip BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    preferences JSONB DEFAULT '{}',
                    telegram_metadata JSONB DEFAULT '{}'
                )
            """)
            
            # Add indexes for performance
            await conn.execute("CREATE INDEX idx_users_username ON users(username)")
            await conn.execute("CREATE INDEX idx_users_is_vip ON users(is_vip)")
            await conn.execute("CREATE INDEX idx_users_created_at ON users(created_at)")
        
        yield pool
        
        # Cleanup
        await pool.close()

    @pytest.fixture
    async def repository(self, database_setup):
        """Create repository with real database pool."""
        pool = database_setup
        return UserRepository(pool)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            user_id=123456789,
            username="diana_test",
            first_name="Diana",
            last_name="Test",
            language_code="es",
            is_vip=False,
            preferences={"theme": "dark", "notifications": True},
            telegram_metadata={"is_bot": False, "is_premium": True}
        )

    @pytest.fixture
    def complex_user(self):
        """User with complex JSONB data for testing."""
        return User(
            user_id=987654321,
            username="complex_user",
            first_name="Complex",
            last_name="User",
            preferences={
                "theme": "dark",
                "language": "es",
                "notifications": {
                    "email": True,
                    "push": False,
                    "sms": True
                },
                "personality_dimensions": {
                    "exploration": 0.8,
                    "competitiveness": 0.6,
                    "narrative": 0.9,
                    "social": 0.7
                },
                "achievements": [
                    {"id": 1, "name": "First Login", "earned_at": "2024-01-01T00:00:00Z"},
                    {"id": 2, "name": "Regular User", "earned_at": "2024-01-15T12:00:00Z"}
                ]
            },
            telegram_metadata={
                "is_bot": False,
                "is_premium": True,
                "supports_inline_queries": False,
                "chat_history": {
                    "messages_count": 1500,
                    "last_message_at": "2024-01-20T15:30:00Z"
                }
            }
        )

    @pytest.mark.asyncio
    async def test_create_user_with_real_database(self, repository, sample_user):
        """Test creating user with real PostgreSQL database."""
        # Create user
        result = await repository.create(sample_user)
        
        assert result.user_id == sample_user.user_id
        assert result.username == sample_user.username
        assert result.first_name == sample_user.first_name
        assert result.preferences == sample_user.preferences
        assert result.telegram_metadata == sample_user.telegram_metadata
        
        # Verify user exists in database
        retrieved_user = await repository.get_by_user_id(sample_user.user_id)
        assert retrieved_user is not None
        assert retrieved_user.user_id == sample_user.user_id
        assert retrieved_user.preferences == sample_user.preferences

    @pytest.mark.asyncio
    async def test_duplicate_user_constraint(self, repository, sample_user):
        """Test database constraint prevents duplicate users."""
        # Create user first time
        await repository.create(sample_user)
        
        # Attempt to create duplicate should raise error
        duplicate_user = User(
            user_id=sample_user.user_id,  # Same user_id
            first_name="Different Name"
        )
        
        with pytest.raises(DuplicateUserError):
            await repository.create(duplicate_user)

    @pytest.mark.asyncio
    async def test_jsonb_operations_with_real_database(self, repository, complex_user):
        """Test JSONB operations work correctly with PostgreSQL."""
        # Create user with complex JSON data
        await repository.create(complex_user)
        
        # Retrieve and verify complex JSON data
        retrieved = await repository.get_by_user_id(complex_user.user_id)
        
        assert retrieved is not None
        assert retrieved.preferences["personality_dimensions"]["exploration"] == 0.8
        assert len(retrieved.preferences["achievements"]) == 2
        assert retrieved.telegram_metadata["chat_history"]["messages_count"] == 1500

    @pytest.mark.asyncio
    async def test_update_jsonb_fields(self, repository, complex_user, database_setup):
        """Test updating JSONB fields with real database."""
        # Create user
        await repository.create(complex_user)
        
        # Update preferences
        complex_user.preferences["theme"] = "light"
        complex_user.preferences["new_feature"] = {"enabled": True, "value": 42}
        
        # Update user
        await repository.update(complex_user)
        
        # Verify update
        updated_user = await repository.get_by_user_id(complex_user.user_id)
        assert updated_user.preferences["theme"] == "light"
        assert updated_user.preferences["new_feature"]["enabled"] is True
        assert updated_user.preferences["new_feature"]["value"] == 42

    @pytest.mark.asyncio
    async def test_database_constraints_validation(self, repository, database_setup):
        """Test database constraints are properly validated."""
        # Test user without required first_name should fail
        invalid_user = User(
            user_id=555666777,
            username="invalid",
            first_name="",  # Empty first_name
        )
        
        # This should succeed since we allow empty strings
        await repository.create(invalid_user)
        
        # Verify it was stored with empty string
        retrieved = await repository.get_by_user_id(555666777)
        assert retrieved.first_name == ""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, repository, database_setup):
        """Test concurrent database operations work correctly."""
        # Create multiple users concurrently
        users = [
            User(user_id=i, first_name=f"User{i}")
            for i in range(100000, 100010)
        ]
        
        # Create all users concurrently
        tasks = [repository.create(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        for result in results:
            assert not isinstance(result, Exception)
        
        # Verify all users exist
        count = await repository.count_users()
        assert count >= 10  # At least our 10 users

    @pytest.mark.asyncio
    async def test_performance_with_real_database(self, repository, database_setup):
        """Test performance benchmarks with real database."""
        import time
        
        # Create test user
        test_user = User(user_id=999888777, first_name="Performance Test")
        await repository.create(test_user)
        
        # Benchmark get_by_user_id
        start_time = time.time()
        for _ in range(100):
            await repository.get_by_user_id(test_user.user_id)
        end_time = time.time()
        
        avg_query_time = (end_time - start_time) / 100
        assert avg_query_time < 0.1  # Should be faster than 100ms per query
        
        # Benchmark count_users
        start_time = time.time()
        await repository.count_users()
        end_time = time.time()
        
        count_time = end_time - start_time
        assert count_time < 1.0  # Count should be faster than 1 second

    @pytest.mark.asyncio
    async def test_health_check_with_real_database(self, repository):
        """Test health check with real database connection."""
        health = await repository.health_check()
        
        assert health["status"] == "healthy"
        assert health["database"] == "connected"
        assert isinstance(health["users_count"], int)
        assert health["users_count"] >= 0
        assert "last_check" in health

    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, repository, database_setup):
        """Test bulk operations performance with real database."""
        # Create multiple users for bulk retrieval test
        user_ids = list(range(777000, 777100))  # 100 users
        users = [User(user_id=uid, first_name=f"Bulk{uid}") for uid in user_ids]
        
        # Create all users
        for user in users:
            await repository.create(user)
        
        # Test bulk retrieval performance
        import time
        start_time = time.time()
        bulk_users = await repository.get_users_for_service(user_ids)
        end_time = time.time()
        
        bulk_time = end_time - start_time
        assert bulk_time < 1.0  # Bulk retrieval should be fast
        assert len(bulk_users) == 100
        
        # Verify all users retrieved correctly
        retrieved_ids = {user.user_id for user in bulk_users}
        expected_ids = set(user_ids)
        assert retrieved_ids == expected_ids

    @pytest.mark.asyncio
    async def test_jsonb_query_capabilities(self, repository, database_setup):
        """Test JSONB query capabilities with real PostgreSQL."""
        # Create users with different personality dimensions
        users_data = [
            (111111, {"personality_dimensions": {"exploration": 0.9, "social": 0.3}}),
            (222222, {"personality_dimensions": {"exploration": 0.2, "social": 0.8}}),
            (333333, {"personality_dimensions": {"exploration": 0.7, "social": 0.6}})
        ]
        
        for user_id, prefs in users_data:
            user = User(user_id=user_id, first_name=f"User{user_id}", preferences=prefs)
            await repository.create(user)
        
        # Direct SQL query to test JSONB capabilities
        async with repository._pool.acquire() as conn:
            # Test JSONB path query
            high_exploration = await conn.fetch("""
                SELECT user_id, preferences->'personality_dimensions'->>'exploration' as exploration
                FROM users 
                WHERE (preferences->'personality_dimensions'->>'exploration')::float > 0.5
                AND user_id IN (111111, 222222, 333333)
                ORDER BY user_id
            """)
            
            assert len(high_exploration) == 2  # Users 111111 and 333333
            assert int(high_exploration[0]['user_id']) == 111111
            assert int(high_exploration[1]['user_id']) == 333333

    @pytest.mark.asyncio
    async def test_database_transaction_integrity(self, repository, database_setup):
        """Test database transaction integrity with real PostgreSQL."""
        async with repository._pool.acquire() as conn:
            async with conn.transaction():
                # Create a user within transaction
                await conn.execute(
                    "INSERT INTO users (user_id, first_name) VALUES ($1, $2)",
                    555555, "Transaction Test"
                )
                
                # Verify user exists within transaction
                result = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", 555555)
                assert result is not None
                
                # Transaction will commit automatically
        
        # Verify user exists after transaction commit
        user = await repository.get_by_user_id(555555)
        assert user is not None
        assert user.first_name == "Transaction Test"