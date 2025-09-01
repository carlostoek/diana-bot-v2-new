"""
User Repository Integration Tests with TestContainers.

Real PostgreSQL database testing using testcontainers for database operations,
JSONB constraints, and performance validation.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict

from testcontainers.postgres import PostgresContainer
import asyncpg

from src.modules.user.repository import UserRepository
from src.modules.user.models import User, DuplicateUserError, UserNotFoundError


class TestUserRepositoryIntegration:
    """Integration tests with real PostgreSQL database using testcontainers."""

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Start PostgreSQL container for testing."""
        with PostgresContainer("postgres:15") as postgres:
            # Create the users table
            connection_url = postgres.get_connection_url()
            
            # Create table synchronously using psycopg2 for setup
            import psycopg2
            
            conn = psycopg2.connect(postgres.get_connection_url())
            cur = conn.cursor()
            
            # Create users table with JSONB columns
            cur.execute("""
                CREATE TABLE users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100),
                    language_code VARCHAR(10) DEFAULT 'es',
                    is_vip BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    preferences JSONB DEFAULT '{}',
                    telegram_metadata JSONB DEFAULT '{}'
                );
                
                -- Create indexes for better performance
                CREATE INDEX idx_users_username ON users(username) WHERE username IS NOT NULL;
                CREATE INDEX idx_users_language_code ON users(language_code);
                CREATE INDEX idx_users_is_vip ON users(is_vip) WHERE is_vip = TRUE;
                CREATE INDEX idx_users_created_at ON users(created_at);
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            
            yield connection_url

    @pytest.fixture
    async def repository(self, postgres_container):
        """Create UserRepository with real database connection."""
        pool = await asyncpg.create_pool(
            postgres_container,
            min_size=1,
            max_size=3
        )
        
        repository = UserRepository(pool)
        
        yield repository
        
        # Cleanup
        await pool.close()

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return User(
            user_id=12345,
            first_name="Test User",
            username="testuser",
            last_name="Lastname",
            language_code="es",
            is_vip=False,
            preferences={"theme": "dark", "notifications": True},
            telegram_metadata={"chat_id": 12345, "is_bot": False}
        )

    @pytest.mark.asyncio
    async def test_create_user_real_database(self, repository, sample_user):
        """Test user creation with real PostgreSQL database."""
        # Create user
        result = await repository.create(sample_user)
        
        # Verify user was created
        assert result.user_id == sample_user.user_id
        assert result.first_name == sample_user.first_name
        assert result.username == sample_user.username
        
        # Verify user can be retrieved
        retrieved = await repository.get_by_user_id(sample_user.user_id)
        assert retrieved is not None
        assert retrieved.user_id == sample_user.user_id
        assert retrieved.preferences == sample_user.preferences
        assert retrieved.telegram_metadata == sample_user.telegram_metadata

    @pytest.mark.asyncio
    async def test_duplicate_user_constraint(self, repository, sample_user):
        """Test that duplicate users raise DuplicateUserError."""
        # Create user first time
        await repository.create(sample_user)
        
        # Try to create same user again
        with pytest.raises(DuplicateUserError):
            await repository.create(sample_user)

    @pytest.mark.asyncio
    async def test_jsonb_operations_real_database(self, repository):
        """Test JSONB operations with real PostgreSQL constraints."""
        # Create user with complex JSONB data
        complex_user = User(
            user_id=54321,
            first_name="Complex User",
            username="complex",
            preferences={
                "theme": "dark",
                "notifications": {
                    "email": True,
                    "push": False,
                    "sms": None
                },
                "settings": {
                    "language": "es",
                    "timezone": "America/Mexico_City",
                    "features": ["gamification", "narrative", "analytics"]
                }
            },
            telegram_metadata={
                "chat_id": 54321,
                "is_bot": False,
                "is_premium": True,
                "language_code": "es",
                "can_join_groups": True,
                "can_read_all_group_messages": False,
                "supports_inline_queries": False
            }
        )
        
        # Create user
        created = await repository.create(complex_user)
        assert created.user_id == 54321
        
        # Retrieve and verify JSONB data
        retrieved = await repository.get_by_user_id(54321)
        assert retrieved is not None
        
        # Verify nested JSONB structure
        assert retrieved.preferences["theme"] == "dark"
        assert retrieved.preferences["notifications"]["email"] is True
        assert retrieved.preferences["notifications"]["push"] is False
        assert retrieved.preferences["settings"]["features"] == ["gamification", "narrative", "analytics"]
        
        # Verify telegram metadata JSONB
        assert retrieved.telegram_metadata["is_premium"] is True
        assert retrieved.telegram_metadata["can_join_groups"] is True
        assert retrieved.telegram_metadata["supports_inline_queries"] is False

    @pytest.mark.asyncio
    async def test_update_with_jsonb_changes(self, repository):
        """Test updating user with JSONB field changes."""
        # Create initial user
        user = User(
            user_id=98765,
            first_name="Update Test",
            preferences={"theme": "light", "level": 1}
        )
        
        await repository.create(user)
        
        # Update preferences
        user.preferences.update({
            "theme": "dark",
            "level": 5,
            "new_feature": True,
            "achievements": ["first_login", "tutorial_complete"]
        })
        
        # Update user
        updated = await repository.update(user)
        
        # Verify changes
        retrieved = await repository.get_by_user_id(98765)
        assert retrieved.preferences["theme"] == "dark"
        assert retrieved.preferences["level"] == 5
        assert retrieved.preferences["new_feature"] is True
        assert retrieved.preferences["achievements"] == ["first_login", "tutorial_complete"]

    @pytest.mark.asyncio
    async def test_batch_operations_performance(self, repository):
        """Test batch operations and performance with real database."""
        import time
        
        # Create multiple users
        user_ids = list(range(100, 120))  # 20 users
        
        # Measure creation time
        start_time = time.time()
        
        for user_id in user_ids:
            user = User(
                user_id=user_id,
                first_name=f"User {user_id}",
                username=f"user{user_id}",
                preferences={"user_index": user_id, "batch": True}
            )
            await repository.create(user)
        
        creation_time = time.time() - start_time
        
        # Measure batch retrieval time
        start_time = time.time()
        users = await repository.get_users_for_service(user_ids)
        retrieval_time = time.time() - start_time
        
        # Verify results
        assert len(users) == 20
        assert all(user.user_id in user_ids for user in users)
        
        # Performance assertions (reasonable for 20 users)
        assert creation_time < 5.0  # Should create 20 users in under 5 seconds
        assert retrieval_time < 1.0  # Should retrieve 20 users in under 1 second
        
        # Test counting
        total_count = await repository.count_users()
        assert total_count >= 20  # At least the users we created

    @pytest.mark.asyncio
    async def test_database_constraints_validation(self, repository):
        """Test database constraints and validation."""
        # Test username uniqueness constraint
        user1 = User(
            user_id=11111,
            first_name="First User",
            username="unique_username"
        )
        
        user2 = User(
            user_id=22222,
            first_name="Second User", 
            username="unique_username"  # Same username
        )
        
        # Create first user
        await repository.create(user1)
        
        # Try to create second user with same username - should fail
        with pytest.raises(Exception):  # Database constraint violation
            await repository.create(user2)

    @pytest.mark.asyncio
    async def test_transaction_integrity(self, repository):
        """Test transaction integrity with real database."""
        # This test verifies that database operations are properly isolated
        
        user = User(
            user_id=33333,
            first_name="Transaction Test",
            preferences={"transaction": "test"}
        )
        
        # Create user
        await repository.create(user)
        
        # Verify user exists
        retrieved = await repository.get_by_user_id(33333)
        assert retrieved is not None
        
        # Test non-existent user update
        non_existent = User(
            user_id=99999,
            first_name="Does Not Exist"
        )
        
        with pytest.raises(UserNotFoundError):
            await repository.update(non_existent)
        
        # Verify original user is still there and unchanged
        still_there = await repository.get_by_user_id(33333)
        assert still_there is not None
        assert still_there.first_name == "Transaction Test"

    @pytest.mark.asyncio
    async def test_health_check_real_database(self, repository):
        """Test health check with real database connection."""
        health = await repository.health_check()
        
        assert health["status"] == "healthy"
        assert health["database"] == "connected"
        assert isinstance(health["users_count"], int)
        assert health["users_count"] >= 0
        assert "last_check" in health
        assert "error" not in health

    @pytest.mark.asyncio
    async def test_concurrent_operations_safety(self, repository):
        """Test concurrent database operations safety."""
        import asyncio
        
        # Create multiple users concurrently
        async def create_user(user_id: int):
            user = User(
                user_id=user_id,
                first_name=f"Concurrent User {user_id}",
                preferences={"concurrent": True, "id": user_id}
            )
            return await repository.create(user)
        
        # Create 10 users concurrently
        user_ids = range(1000, 1010)
        tasks = [create_user(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 10
        
        # Verify all users exist
        for user_id in user_ids:
            user = await repository.get_by_user_id(user_id)
            assert user is not None
            assert user.preferences["concurrent"] is True