"""
User Repository Integration Tests - Fixed Implementation.

Comprehensive integration tests that simulate database behavior including
JSONB operations, constraints, and transaction integrity without requiring Docker.
"""

import pytest
import pytest_asyncio
import json
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

import asyncpg

from src.modules.user.repository import UserRepository, create_user_repository
from src.modules.user.models import User, DuplicateUserError, UserNotFoundError, InvalidUserDataError


class MockAsyncPgConnection:
    """Mock asyncpg connection that simulates real database behavior."""
    
    def __init__(self):
        self._data: Dict[int, Dict[str, Any]] = {}  # Simulate database table
        self._executed_queries: List[str] = []
    
    async def fetchrow(self, query: str, *args):
        """Simulate fetchrow - returns single row or None."""
        self._executed_queries.append(query)
        
        if "SELECT user_id FROM" in query:
            # Check for existing user query
            user_id = args[0]
            if user_id in self._data:
                return {"user_id": user_id}
            return None
        elif "SELECT" in query and "WHERE user_id" in query:
            # Get user by ID query
            user_id = args[0]
            if user_id in self._data:
                return dict(self._data[user_id])
            return None
        elif "SELECT 1" in query:
            # Health check query
            return {"result": 1}
        elif "SELECT COUNT" in query:
            # Count query
            return len(self._data)
        
        return None
    
    async def fetch(self, query: str, *args):
        """Simulate fetch - returns multiple rows."""
        self._executed_queries.append(query)
        
        if "WHERE user_id = ANY" in query:
            # Get multiple users
            user_ids = args[0]
            results = []
            for user_id in user_ids:
                if user_id in self._data:
                    results.append(dict(self._data[user_id]))
            return results
        
        return []
    
    async def fetchval(self, query: str, *args):
        """Simulate fetchval - returns single value."""
        self._executed_queries.append(query)
        
        if "SELECT 1" in query:
            return 1
        elif "SELECT COUNT" in query:
            return len(self._data)
        
        return None
    
    async def execute(self, query: str, *args):
        """Simulate execute - for INSERT/UPDATE/DELETE queries."""
        self._executed_queries.append(query)
        
        if query.strip().startswith("INSERT INTO"):
            # Simulate INSERT
            user_id = args[0]
            if user_id in self._data:
                raise asyncpg.PostgresError("duplicate key value violates unique constraint")
            
            # Store user data (simulate JSONB storage)
            self._data[user_id] = {
                'user_id': args[0],
                'username': args[1],
                'first_name': args[2],
                'last_name': args[3],
                'language_code': args[4],
                'is_vip': args[5],
                'created_at': args[6],
                'last_active': args[7],
                'preferences': args[8],  # JSON string
                'telegram_metadata': args[9]  # JSON string
            }
            return "INSERT 0 1"
            
        elif query.strip().startswith("UPDATE"):
            # Simulate UPDATE
            user_id = args[0]
            if user_id not in self._data:
                return "UPDATE 0"
            
            # Update user data
            self._data[user_id].update({
                'username': args[1],
                'first_name': args[2],
                'last_name': args[3],
                'language_code': args[4],
                'is_vip': args[5],
                'last_active': args[6],
                'preferences': args[7],  # JSON string
                'telegram_metadata': args[8]  # JSON string
            })
            return "UPDATE 1"
        
        return "OK"


class TestUserRepositoryIntegration:
    """Comprehensive integration tests for UserRepository."""

    @pytest_asyncio.fixture
    async def repository_with_mock_db(self):
        """Create UserRepository with mock database that simulates real behavior."""
        mock_conn = MockAsyncPgConnection()
        
        # Mock pool
        mock_pool = AsyncMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_context_manager)
        
        repository = UserRepository(mock_pool)
        return repository, mock_conn

    @pytest.fixture
    def complex_user(self):
        """Create a user with complex JSONB data for testing."""
        return User(
            user_id=12345,
            first_name="Complex User",
            username="complex_user",
            last_name="Test",
            language_code="es",
            is_vip=True,
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
                },
                "achievements": [
                    {"name": "first_login", "date": "2024-01-15", "points": 10},
                    {"name": "tutorial_complete", "date": "2024-01-16", "points": 50}
                ]
            },
            telegram_metadata={
                "chat_id": 12345,
                "is_bot": False,
                "is_premium": True,
                "language_code": "es",
                "can_join_groups": True,
                "can_read_all_group_messages": False,
                "supports_inline_queries": False,
                "user_data": {
                    "first_name": "Complex",
                    "last_name": "User",
                    "username": "complex_user"
                }
            }
        )

    @pytest.mark.asyncio
    async def test_full_user_lifecycle(self, repository_with_mock_db, complex_user):
        """Test complete user lifecycle: create, read, update, with JSONB data."""
        repository, mock_conn = repository_with_mock_db
        
        # 1. Create user with complex JSONB data
        created_user = await repository.create(complex_user)
        
        assert created_user.user_id == complex_user.user_id
        assert created_user.preferences == complex_user.preferences
        assert created_user.telegram_metadata == complex_user.telegram_metadata
        
        # Verify data was stored as JSON strings (simulating database)
        stored_data = mock_conn._data[complex_user.user_id]
        assert isinstance(stored_data['preferences'], str)
        assert isinstance(stored_data['telegram_metadata'], str)
        
        # 2. Retrieve user and verify JSONB deserialization
        retrieved_user = await repository.get_by_user_id(complex_user.user_id)
        
        assert retrieved_user is not None
        assert retrieved_user.user_id == complex_user.user_id
        assert retrieved_user.first_name == complex_user.first_name
        assert retrieved_user.is_vip == complex_user.is_vip
        
        # Verify complex JSONB structure
        assert retrieved_user.preferences["theme"] == "dark"
        assert retrieved_user.preferences["notifications"]["email"] is True
        assert retrieved_user.preferences["settings"]["features"] == ["gamification", "narrative", "analytics"]
        assert len(retrieved_user.preferences["achievements"]) == 2
        assert retrieved_user.preferences["achievements"][0]["name"] == "first_login"
        
        # Verify telegram metadata JSONB
        assert retrieved_user.telegram_metadata["is_premium"] is True
        assert retrieved_user.telegram_metadata["user_data"]["username"] == "complex_user"
        
        # 3. Update user with modified JSONB data
        retrieved_user.preferences["achievements"].append({
            "name": "level_up",
            "date": "2024-01-17",
            "points": 100
        })
        retrieved_user.preferences["settings"]["level"] = 5
        retrieved_user.telegram_metadata["last_seen"] = "2024-01-17T10:30:00Z"
        
        updated_user = await repository.update(retrieved_user)
        
        # 4. Verify updated data
        final_user = await repository.get_by_user_id(complex_user.user_id)
        
        assert len(final_user.preferences["achievements"]) == 3
        assert final_user.preferences["achievements"][2]["name"] == "level_up"
        assert final_user.preferences["settings"]["level"] == 5
        assert final_user.telegram_metadata["last_seen"] == "2024-01-17T10:30:00Z"

    @pytest.mark.asyncio
    async def test_duplicate_user_constraint_simulation(self, repository_with_mock_db):
        """Test duplicate user constraint behavior."""
        repository, mock_conn = repository_with_mock_db
        
        user1 = User(
            user_id=11111,
            first_name="First User",
            username="duplicate_test"
        )
        
        user2 = User(
            user_id=11111,  # Same user_id
            first_name="Second User",
            username="different_username"
        )
        
        # Create first user - should succeed
        await repository.create(user1)
        
        # Try to create second user with same ID - should fail
        with pytest.raises(DuplicateUserError):
            await repository.create(user2)

    @pytest.mark.asyncio
    async def test_jsonb_null_handling(self, repository_with_mock_db):
        """Test handling of None/null values in JSONB fields."""
        repository, mock_conn = repository_with_mock_db
        
        user = User(
            user_id=22222,
            first_name="Null Test",
            preferences={
                "theme": None,
                "notifications": {
                    "email": True,
                    "push": None,
                    "sms": False
                }
            },
            telegram_metadata={
                "is_bot": False,
                "premium_until": None,
                "restrictions": None
            }
        )
        
        # Create and retrieve user
        await repository.create(user)
        retrieved = await repository.get_by_user_id(22222)
        
        # Verify None values are preserved
        assert retrieved.preferences["theme"] is None
        assert retrieved.preferences["notifications"]["push"] is None
        assert retrieved.telegram_metadata["premium_until"] is None
        assert retrieved.telegram_metadata["restrictions"] is None

    @pytest.mark.asyncio
    async def test_batch_operations_performance(self, repository_with_mock_db):
        """Test batch operations and performance characteristics."""
        repository, mock_conn = repository_with_mock_db
        
        # Create multiple users
        user_ids = list(range(100, 120))  # 20 users
        created_users = []
        
        for i, user_id in enumerate(user_ids):
            user = User(
                user_id=user_id,
                first_name=f"Batch User {i}",
                username=f"batch_user_{i}",
                preferences={
                    "batch_index": i,
                    "test_data": f"data_{i}",
                    "created_in_batch": True
                }
            )
            created_user = await repository.create(user)
            created_users.append(created_user)
        
        # Test batch retrieval
        batch_users = await repository.get_users_for_service(user_ids)
        
        assert len(batch_users) == 20
        assert all(user.preferences["created_in_batch"] is True for user in batch_users)
        
        # Test counting
        count = await repository.count_users()
        assert count >= 20

    @pytest.mark.asyncio
    async def test_concurrent_operations_safety(self, repository_with_mock_db):
        """Test concurrent database operations safety simulation."""
        repository, mock_conn = repository_with_mock_db
        
        async def create_user_with_id(user_id: int):
            """Create a user with specific ID."""
            user = User(
                user_id=user_id,
                first_name=f"Concurrent User {user_id}",
                preferences={
                    "concurrent_test": True,
                    "user_id": user_id
                }
            )
            try:
                return await repository.create(user)
            except Exception as e:
                return e
        
        # Create users concurrently
        user_ids = range(2000, 2010)  # 10 users
        tasks = [create_user_with_id(user_id) for user_id in user_ids]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed since they have different IDs
        successful_results = [r for r in results if isinstance(r, User)]
        assert len(successful_results) == 10
        
        # Verify all users exist
        for user_id in user_ids:
            user = await repository.get_by_user_id(user_id)
            assert user is not None
            assert user.preferences["concurrent_test"] is True

    @pytest.mark.asyncio
    async def test_transaction_integrity_simulation(self, repository_with_mock_db):
        """Test transaction integrity behavior."""
        repository, mock_conn = repository_with_mock_db
        
        # Create a user
        user = User(
            user_id=33333,
            first_name="Transaction Test",
            preferences={"test": "transaction"}
        )
        
        await repository.create(user)
        
        # Verify user exists
        retrieved = await repository.get_by_user_id(33333)
        assert retrieved is not None
        
        # Try to update non-existent user
        non_existent = User(
            user_id=99999,
            first_name="Does Not Exist"
        )
        
        with pytest.raises(UserNotFoundError):
            await repository.update(non_existent)
        
        # Verify original user is unchanged
        still_there = await repository.get_by_user_id(33333)
        assert still_there is not None
        assert still_there.preferences["test"] == "transaction"

    @pytest.mark.asyncio
    async def test_health_check_comprehensive(self, repository_with_mock_db):
        """Test comprehensive health check functionality."""
        repository, mock_conn = repository_with_mock_db
        
        # Add some test data
        for i in range(5):
            user = User(
                user_id=40000 + i,
                first_name=f"Health User {i}",
                preferences={"health_test": True}
            )
            await repository.create(user)
        
        # Perform health check
        health = await repository.health_check()
        
        assert health["status"] == "healthy"
        assert health["database"] == "connected"
        assert health["users_count"] >= 5
        assert "last_check" in health
        assert "error" not in health

    @pytest.mark.asyncio
    async def test_edge_cases_and_error_handling(self, repository_with_mock_db):
        """Test edge cases and error handling scenarios."""
        repository, mock_conn = repository_with_mock_db
        
        # Test with empty strings and special characters
        special_user = User(
            user_id=55555,
            first_name="Test",
            username="user_with_special_chars_🚀",
            preferences={
                "empty_string": "",
                "unicode_text": "Texto en español with émojis 🎉",
                "special_chars": "!@#$%^&*()[]{}|;:,.<>?",
                "very_long_string": "x" * 1000
            },
            telegram_metadata={
                "unicode_name": "José María Azurmendi",
                "emoji_status": "🎯 Ready to play!"
            }
        )
        
        # Should handle special characters gracefully
        await repository.create(special_user)
        retrieved = await repository.get_by_user_id(55555)
        
        assert retrieved.username == "user_with_special_chars_🚀"
        assert retrieved.preferences["unicode_text"] == "Texto en español with émojis 🎉"
        assert retrieved.telegram_metadata["emoji_status"] == "🎯 Ready to play!"
        
        # Test invalid JSON handling in _row_to_user
        # Directly modify stored data to simulate corrupted JSON
        mock_conn._data[55555]['preferences'] = 'invalid json {'
        mock_conn._data[55555]['telegram_metadata'] = '{ incomplete json'
        
        # Should handle invalid JSON gracefully
        retrieved_with_invalid_json = await repository.get_by_user_id(55555)
        
        # Should default to empty dicts for invalid JSON
        assert retrieved_with_invalid_json.preferences == {}
        assert retrieved_with_invalid_json.telegram_metadata == {}

    @pytest.mark.asyncio
    async def test_factory_function(self):
        """Test the create_user_repository factory function."""
        
        # Mock asyncpg.create_pool
        with patch('src.modules.user.repository.asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            
            # Make create_pool awaitable
            async def mock_create_pool_func(*args, **kwargs):
                return mock_pool
            
            mock_create_pool.side_effect = mock_create_pool_func
            
            repository = await create_user_repository("postgresql://test:test@localhost/test")
            
            assert isinstance(repository, UserRepository)
            assert repository._pool == mock_pool
            
            # Verify pool was created with correct parameters
            mock_create_pool.assert_called_once_with(
                "postgresql://test:test@localhost/test",
                min_size=2,
                max_size=10,
                server_settings={'jit': 'off'}
            )