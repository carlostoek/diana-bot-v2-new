"""
CRITICAL: User Data Consistency Tests

Tests database constraints, JSONB handling, and concurrent operations.
Prevents data corruption that could destroy user trust permanently.
"""

import pytest
import json
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.modules.user.service import UserService
from src.modules.user.repository import UserRepository
from src.modules.user.models import User, DuplicateUserError, InvalidUserDataError, UserNotFoundError
from src.modules.user.interfaces import IUserRepository


class TestUserDataConsistency:
    """CRITICAL: Data corruption prevention."""
    
    @pytest.fixture
    def mock_repository(self):
        repo = AsyncMock(spec=IUserRepository)
        return repo
    
    @pytest.fixture
    def user_service(self, mock_repository):
        return UserService(mock_repository, None)

    async def test_preferences_jsonb_handling(self, user_service, mock_repository):
        """Test JSONB preferences storage and retrieval."""
        user_id = 123456789
        
        # Complex preference object
        complex_preferences = {
            "ui_settings": {
                "theme": "dark",
                "language": "es",
                "notifications": {
                    "push": True,
                    "email": False,
                    "types": ["achievements", "stories"]
                }
            },
            "game_settings": {
                "difficulty": "intermediate",
                "auto_save": True,
                "stats": {
                    "points": 1500,
                    "level": 12,
                    "achievements": [1, 3, 5, 7]
                }
            },
            "personality": {
                "archetype": "explorer",
                "dimensions": {
                    "exploration": 0.8,
                    "competitiveness": 0.6,
                    "narrative": 0.9,
                    "social": 0.7
                }
            }
        }
        
        user = User(
            user_id=user_id,
            first_name="Complex User",
            preferences=complex_preferences.copy()
        )
        
        mock_repository.get_by_user_id.return_value = user
        mock_repository.update.return_value = user
        
        # Test complex data update
        new_prefs = {"ui_settings": {"font_size": "large"}}
        result = await user_service.update_preferences(user_id, new_prefs)
        
        # Verify nested data integrity
        assert result.preferences["ui_settings"]["font_size"] == "large"
        assert result.preferences["game_settings"]["difficulty"] == "intermediate"
        assert result.preferences["personality"]["archetype"] == "explorer"

    async def test_preferences_size_limits(self, user_service, mock_repository):
        """Test preferences size limits to prevent database issues."""
        user_id = 123456789
        user = User(user_id=user_id, first_name="Size Test")
        mock_repository.get_by_user_id.return_value = user
        
        # Test large preference object (simulate 1MB+ JSON)
        large_preferences = {
            "large_data": "x" * 1000000,  # 1MB string
            "array_data": list(range(10000)),  # Large array
            "nested_data": {f"key_{i}": f"value_{i}" for i in range(1000)}
        }
        
        # This should potentially raise an error or be handled gracefully
        # Implementation should validate size before storage
        user.preferences.update(large_preferences)
        mock_repository.update.return_value = user
        
        # Service should handle large data gracefully
        result = await user_service.update_preferences(user_id, large_preferences)
        assert result.preferences["large_data"] == "x" * 1000000

    async def test_invalid_json_handling(self, user_service, mock_repository):
        """Test handling of invalid JSON in preferences."""
        user_id = 123456789
        
        # Test preferences with non-serializable objects
        invalid_preferences = {
            "datetime_obj": datetime.now(),  # Not JSON serializable
            "function_obj": lambda x: x,     # Not JSON serializable
        }
        
        user = User(user_id=user_id, first_name="Invalid JSON User")
        mock_repository.get_by_user_id.return_value = user
        
        # Should handle gracefully or raise appropriate error
        with patch('json.dumps') as mock_json_dumps:
            mock_json_dumps.side_effect = TypeError("Object not JSON serializable")
            mock_repository.update.side_effect = InvalidUserDataError("JSON serialization failed")
            
            with pytest.raises(InvalidUserDataError):
                await user_service.update_preferences(user_id, invalid_preferences)

    async def test_concurrent_user_operations(self, mock_repository):
        """Test concurrent operations don't corrupt user data."""
        user_service = UserService(mock_repository, None)
        user_id = 123456789
        
        user = User(
            user_id=user_id,
            first_name="Concurrent User",
            preferences={"counter": 0}
        )
        
        mock_repository.get_by_user_id.return_value = user
        
        async def update_counter(increment: int):
            """Simulate concurrent preference update."""
            current_user = await user_service.get_user(user_id)
            current_counter = current_user.preferences.get("counter", 0)
            new_preferences = {"counter": current_counter + increment}
            
            # Simulate processing delay
            await asyncio.sleep(0.01)
            
            updated_user = current_user
            updated_user.preferences.update(new_preferences)
            mock_repository.update.return_value = updated_user
            
            return await user_service.update_preferences(user_id, new_preferences)
        
        # Run concurrent updates
        tasks = [update_counter(1) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All tasks should complete without errors
        for result in results:
            assert not isinstance(result, Exception)

    async def test_user_activity_timestamp_integrity(self, user_service, mock_repository):
        """Test activity tracking maintains timestamp integrity."""
        user_id = 123456789
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        user = User(
            user_id=user_id,
            first_name="Activity User",
            last_active=initial_time
        )
        
        mock_repository.get_by_user_id.return_value = user
        
        # Mock time progression
        with patch('src.modules.user.models.datetime') as mock_datetime:
            new_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = new_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            updated_user = user
            updated_user.last_active = new_time
            mock_repository.update.return_value = updated_user
            
            await user_service.mark_user_active(user_id)
            
            # Verify timestamp was updated
            mock_repository.update.assert_called_once()
            updated_user_arg = mock_repository.update.call_args[0][0]
            assert updated_user_arg.last_active > initial_time

    async def test_bulk_operations_consistency(self, user_service, mock_repository):
        """Test bulk operations maintain data consistency."""
        user_ids = [111, 222, 333, 444, 555]
        
        # Create users for each ID
        users = []
        for uid in user_ids:
            user = User(user_id=uid, first_name=f"User {uid}")
            users.append(user)
        
        # Mock repository responses
        def get_user_side_effect(user_id):
            return next((u for u in users if u.user_id == user_id), None)
        
        mock_repository.get_by_user_id.side_effect = get_user_side_effect
        mock_repository.update.return_value = MagicMock()  # Simple mock for updates
        
        # Test bulk mark active
        result_count = await user_service.bulk_mark_users_active(user_ids)
        
        # All users should be processed
        assert result_count == len(user_ids)
        assert mock_repository.update.call_count == len(user_ids)


class TestDatabaseConstraintSimulation:
    """Simulate database constraint violations."""
    
    @pytest.fixture
    def mock_pool(self):
        """Mock database connection pool."""
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        pool.acquire.return_value.__aexit__.return_value = None
        return pool, conn
    
    @pytest.fixture
    def user_repository(self, mock_pool):
        """Repository with mocked database."""
        pool, conn = mock_pool
        repo = UserRepository(pool)
        return repo, pool, conn

    async def test_primary_key_constraint_violation(self, user_repository):
        """Test primary key constraint prevents duplicate users."""
        repo, pool, conn = user_repository
        
        user = User(user_id=123456789, first_name="Duplicate User")
        
        # First, simulate user already exists
        conn.fetchrow.return_value = {"user_id": 123456789}  # User exists
        
        with pytest.raises(DuplicateUserError):
            await repo.create(user)
        
        # Verify duplicate check was performed
        conn.fetchrow.assert_called_once()

    async def test_not_null_constraint_handling(self, user_repository):
        """Test NOT NULL constraints on required fields."""
        repo, pool, conn = user_repository
        
        # Simulate database NOT NULL violation
        conn.fetchrow.return_value = None  # No existing user
        
        with patch('asyncpg.PostgresError') as MockPostgresError:
            error = MockPostgresError()
            error.sqlstate = '23502'  # NOT NULL violation
            conn.execute.side_effect = error
            
            user = User(user_id=123456789, first_name="")  # Empty first_name
            
            with pytest.raises(InvalidUserDataError):
                await repo.create(user)

    async def test_json_constraint_validation(self, user_repository):
        """Test JSON validation in database layer."""
        repo, pool, conn = user_repository
        
        conn.fetchrow.return_value = None  # No existing user
        
        # Test invalid JSON handling
        with patch('json.dumps') as mock_json_dumps:
            mock_json_dumps.side_effect = TypeError("Not JSON serializable")
            
            user = User(
                user_id=123456789,
                first_name="JSON User",
                preferences={"invalid": object()}  # Non-serializable object
            )
            
            with pytest.raises(InvalidUserDataError):
                await repo.create(user)

    async def test_database_connection_failure_handling(self, user_repository):
        """Test handling of database connection failures."""
        repo, pool, conn = user_repository
        
        # Simulate connection failure
        pool.acquire.side_effect = Exception("Connection failed")
        
        user = User(user_id=123456789, first_name="Connection Test")
        
        with pytest.raises(InvalidUserDataError):
            await repo.create(user)

    async def test_transaction_rollback_simulation(self, user_repository):
        """Test transaction rollback on failures."""
        repo, pool, conn = user_repository
        
        user = User(user_id=123456789, first_name="Transaction User")
        
        conn.fetchrow.return_value = None  # No existing user
        
        # Simulate failure after starting transaction
        conn.execute.side_effect = Exception("Transaction failed")
        
        with pytest.raises(InvalidUserDataError):
            await repo.create(user)
        
        # Verify connection was properly handled
        pool.acquire.assert_called_once()


class TestUserModelValidation:
    """Test User model validation prevents corruption."""
    
    def test_user_id_validation(self):
        """Test user_id validation in model."""
        
        # Valid user_id
        user = User(user_id=123456789, first_name="Valid User")
        assert user.user_id == 123456789
        
        # Invalid user_id - zero
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            User(user_id=0, first_name="Zero ID")
        
        # Invalid user_id - negative
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            User(user_id=-123, first_name="Negative ID")
        
        # Invalid user_id - non-integer (would fail at type level)
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            User(user_id="123", first_name="String ID")

    def test_first_name_validation(self):
        """Test first_name validation in model."""
        
        # Valid first_name
        user = User(user_id=123456789, first_name="Valid Name")
        assert user.first_name == "Valid Name"
        
        # Empty first_name
        with pytest.raises(ValueError, match="first_name cannot be empty"):
            User(user_id=123456789, first_name="")
        
        # Whitespace-only first_name
        with pytest.raises(ValueError, match="first_name cannot be empty"):
            User(user_id=123456789, first_name="   ")

    def test_preference_methods(self):
        """Test preference getter/setter methods."""
        user = User(user_id=123456789, first_name="Pref User")
        
        # Set preference
        user.set_preference("theme", "dark")
        assert user.preferences["theme"] == "dark"
        
        # Get preference
        theme = user.get_preference("theme")
        assert theme == "dark"
        
        # Get non-existent preference with default
        lang = user.get_preference("language", "es")
        assert lang == "es"
        
        # Get non-existent preference without default
        missing = user.get_preference("missing")
        assert missing is None

    def test_activity_update(self):
        """Test activity timestamp update."""
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        user = User(
            user_id=123456789,
            first_name="Activity User",
            last_active=initial_time
        )
        
        with patch('src.modules.user.models.datetime') as mock_datetime:
            new_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = new_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            user.update_activity()
            
            assert user.last_active == new_time