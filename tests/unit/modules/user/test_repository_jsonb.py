"""Tests for UserRepository JSONB operations.

Validates JSONB functionality for personality_dimensions and complex preference storage.
These tests verify that JSON serialization/deserialization works correctly.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.modules.user.repository import UserRepository
from src.modules.user.models import User


class TestRepositoryJSONBOperations:
    """Test JSON operations in repository layer."""

    @pytest.fixture
    def mock_pool(self):
        """Mock database connection pool."""
        pool = AsyncMock()
        conn = AsyncMock()
        
        # Create proper async context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        # Make sure acquire() returns the context manager directly
        pool.acquire = MagicMock(return_value=mock_context_manager)
        
        return pool, conn

    @pytest.fixture
    def repository(self, mock_pool):
        """Create repository with mocked pool."""
        pool, conn = mock_pool
        return UserRepository(pool), pool, conn

    @pytest.fixture
    def user_with_personality_dimensions(self):
        """User with complex personality dimensions."""
        return User(
            user_id=123456,
            first_name="Diana",
            username="diana_test",
            preferences={
                "theme": "dark",
                "personality_dimensions": {
                    "exploration": 0.8,
                    "competitiveness": 0.6,
                    "narrative": 0.9,
                    "social": 0.7
                },
                "achievements": [
                    {"id": 1, "name": "First Steps", "earned_at": "2024-01-01T00:00:00Z"},
                    {"id": 2, "name": "Explorer", "earned_at": "2024-01-15T12:00:00Z"}
                ],
                "settings": {
                    "notifications": {
                        "push": True,
                        "email": False,
                        "sound": True
                    },
                    "privacy": {
                        "share_stats": False,
                        "public_profile": True
                    }
                }
            },
            telegram_metadata={
                "is_bot": False,
                "is_premium": True,
                "supports_inline_queries": False,
                "chat_info": {
                    "message_count": 1500,
                    "last_message_date": "2024-01-20T15:30:00Z",
                    "favorite_commands": ["/start", "/help", "/stats"]
                }
            }
        )

    @pytest.mark.asyncio
    async def test_create_user_with_complex_json(self, repository, user_with_personality_dimensions):
        """Test creating user with complex JSON data in preferences."""
        repo, pool, conn = repository
        user = user_with_personality_dimensions
        
        # Mock no existing user
        conn.fetchrow.return_value = None
        conn.execute.return_value = None
        
        result = await repo.create(user)
        
        # Verify user was created with JSON data
        assert result == user
        conn.execute.assert_called_once()
        
        # Verify SQL call includes JSON dumps
        call_args = conn.execute.call_args
        sql_query = call_args[0][0]
        parameters = call_args[0][1:]
        
        assert "INSERT INTO users" in sql_query
        assert "preferences" in sql_query
        assert "telegram_metadata" in sql_query
        
        # Verify JSON serialization
        preferences_json = parameters[8]  # preferences parameter position
        telegram_metadata_json = parameters[9]  # telegram_metadata parameter position
        
        # Should be valid JSON strings
        parsed_prefs = json.loads(preferences_json)
        parsed_metadata = json.loads(telegram_metadata_json)
        
        assert parsed_prefs["personality_dimensions"]["exploration"] == 0.8
        assert parsed_prefs["achievements"][0]["name"] == "First Steps"
        assert parsed_metadata["chat_info"]["message_count"] == 1500

    @pytest.mark.asyncio
    async def test_retrieve_user_with_complex_json(self, repository):
        """Test retrieving user with complex JSON data."""
        repo, pool, conn = repository
        
        # Mock database row with JSON strings
        mock_row = {
            'user_id': 123456,
            'username': 'diana_test',
            'first_name': 'Diana',
            'last_name': None,
            'language_code': 'es',
            'is_vip': False,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': json.dumps({
                "theme": "dark",
                "personality_dimensions": {
                    "exploration": 0.8,
                    "competitiveness": 0.6,
                    "narrative": 0.9,
                    "social": 0.7
                },
                "nested_config": {
                    "level1": {
                        "level2": {
                            "value": "deep_nested_value"
                        }
                    }
                }
            }),
            'telegram_metadata': json.dumps({
                "is_bot": False,
                "chat_history": {
                    "total_messages": 2500,
                    "categories": ["greeting", "help", "game"]
                }
            })
        }
        
        conn.fetchrow.return_value = mock_row
        
        result = await repo.get_by_user_id(123456)
        
        # Verify JSON was correctly deserialized
        assert result is not None
        assert result.user_id == 123456
        assert result.preferences["personality_dimensions"]["exploration"] == 0.8
        assert result.preferences["nested_config"]["level1"]["level2"]["value"] == "deep_nested_value"
        assert result.telegram_metadata["chat_history"]["total_messages"] == 2500
        assert "game" in result.telegram_metadata["chat_history"]["categories"]

    @pytest.mark.asyncio
    async def test_update_user_with_personality_changes(self, repository, user_with_personality_dimensions):
        """Test updating user with personality dimension changes."""
        repo, pool, conn = repository
        user = user_with_personality_dimensions
        
        # Modify personality dimensions
        user.preferences["personality_dimensions"]["exploration"] = 0.9
        user.preferences["personality_dimensions"]["new_dimension"] = 0.5
        user.preferences["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Mock successful update
        conn.execute.return_value = "UPDATE 1"
        
        result = await repo.update(user)
        
        # Verify update was called with new JSON
        assert result == user
        conn.execute.assert_called_once()
        
        # Verify SQL call
        call_args = conn.execute.call_args
        sql_query = call_args[0][0]
        parameters = call_args[0][1:]
        
        assert "UPDATE users" in sql_query
        
        # Verify updated JSON contains changes
        preferences_json = parameters[7]  # preferences parameter in UPDATE
        parsed_prefs = json.loads(preferences_json)
        
        assert parsed_prefs["personality_dimensions"]["exploration"] == 0.9
        assert parsed_prefs["personality_dimensions"]["new_dimension"] == 0.5
        assert "updated_at" in parsed_prefs

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, repository):
        """Test handling of invalid JSON in database."""
        repo, pool, conn = repository
        
        # Mock database row with invalid JSON
        mock_row = {
            'user_id': 123456,
            'username': 'test_user',
            'first_name': 'Test',
            'last_name': None,
            'language_code': 'es',
            'is_vip': False,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': 'invalid json {',  # Invalid JSON
            'telegram_metadata': 'also invalid json'  # Invalid JSON
        }
        
        conn.fetchrow.return_value = mock_row
        
        # Should handle invalid JSON gracefully
        with pytest.warns(None) as warning_list:
            result = await repo.get_by_user_id(123456)
        
        # Should return user with empty dicts for invalid JSON
        assert result is not None
        assert result.preferences == {}
        assert result.telegram_metadata == {}

    @pytest.mark.asyncio
    async def test_empty_json_handling(self, repository):
        """Test handling of empty/null JSON fields."""
        repo, pool, conn = repository
        
        # Mock database row with null/empty JSON
        mock_row = {
            'user_id': 123456,
            'username': 'test_user',
            'first_name': 'Test',
            'last_name': None,
            'language_code': 'es',
            'is_vip': False,
            'created_at': datetime.now(timezone.utc),
            'last_active': datetime.now(timezone.utc),
            'preferences': None,  # NULL in database
            'telegram_metadata': ''  # Empty string
        }
        
        conn.fetchrow.return_value = mock_row
        
        result = await repo.get_by_user_id(123456)
        
        # Should handle null/empty JSON gracefully
        assert result is not None
        assert result.preferences == {}
        assert result.telegram_metadata == {}

    @pytest.mark.asyncio
    async def test_personality_dimensions_validation(self, repository):
        """Test that personality dimensions are properly stored and retrieved."""
        repo, pool, conn = repository
        
        # Create user with specific personality dimensions
        user = User(
            user_id=555666,
            first_name="Personality Test",
            preferences={
                "personality_dimensions": {
                    "exploration": 0.85,
                    "competitiveness": 0.23,
                    "narrative": 0.97,
                    "social": 0.64
                }
            }
        )
        
        # Test create flow
        conn.fetchrow.return_value = None
        conn.execute.return_value = None
        
        await repo.create(user)
        
        # Verify the JSON was properly serialized
        call_args = conn.execute.call_args
        preferences_json = call_args[0][9]  # preferences parameter
        parsed_prefs = json.loads(preferences_json)
        
        dimensions = parsed_prefs["personality_dimensions"]
        assert dimensions["exploration"] == 0.85
        assert dimensions["competitiveness"] == 0.23
        assert dimensions["narrative"] == 0.97
        assert dimensions["social"] == 0.64
        
        # Verify all values are preserved with correct precision
        for key, value in dimensions.items():
            assert isinstance(value, float)
            assert 0.0 <= value <= 1.0

    @pytest.mark.asyncio
    async def test_bulk_users_json_handling(self, repository):
        """Test bulk retrieval preserves JSON data correctly."""
        repo, pool, conn = repository
        
        # Mock multiple users with different JSON configurations
        mock_rows = [
            {
                'user_id': 1001,
                'username': 'user1',
                'first_name': 'User One',
                'last_name': None,
                'language_code': 'es',
                'is_vip': False,
                'created_at': datetime.now(timezone.utc),
                'last_active': datetime.now(timezone.utc),
                'preferences': json.dumps({"theme": "dark", "level": 5}),
                'telegram_metadata': json.dumps({"is_bot": False})
            },
            {
                'user_id': 1002,
                'username': 'user2',
                'first_name': 'User Two',
                'last_name': None,
                'language_code': 'en',
                'is_vip': True,
                'created_at': datetime.now(timezone.utc),
                'last_active': datetime.now(timezone.utc),
                'preferences': json.dumps({
                    "personality_dimensions": {"exploration": 0.7, "social": 0.9}
                }),
                'telegram_metadata': json.dumps({"is_premium": True})
            }
        ]
        
        conn.fetch.return_value = mock_rows
        
        result = await repo.get_users_for_service([1001, 1002])
        
        assert len(result) == 2
        
        # Verify first user JSON
        user1 = result[0]
        assert user1.preferences["theme"] == "dark"
        assert user1.preferences["level"] == 5
        
        # Verify second user JSON
        user2 = result[1]
        assert user2.preferences["personality_dimensions"]["exploration"] == 0.7
        assert user2.preferences["personality_dimensions"]["social"] == 0.9
        assert user2.telegram_metadata["is_premium"] is True