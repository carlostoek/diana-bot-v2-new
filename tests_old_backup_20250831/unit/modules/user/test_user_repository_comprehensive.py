"""
Comprehensive User Repository Unit Tests.

Complete unit test coverage for UserRepository with all database operations,
error scenarios, edge cases, and performance validation. Focuses on SQLAlchemy
async operations, connection handling, and data integrity.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.repository import UserRepository
from src.modules.user.models import User, DuplicateUserError, UserNotFoundError


@pytest.fixture
def mock_session():
    """Create mock SQLAlchemy session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def user_repository():
    """Create UserRepository with mock session."""
    # Note: Our UserRepository uses asyncpg, not SQLAlchemy
    from unittest.mock import AsyncMock, MagicMock
    
    pool = AsyncMock()
    conn = AsyncMock()
    
    # Create proper async context manager mock
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=conn)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)
    
    # Make sure acquire() returns the context manager directly (not a coroutine)
    pool.acquire = MagicMock(return_value=mock_context_manager)
    
    return UserRepository(pool), pool, conn


@pytest.fixture
def sample_user():
    """Create sample User for testing."""
    return User(
        user_id=12345,
        first_name="Test User",
        username="testuser",
        last_name="Surname",
        language_code="es",
        onboarding_completed=False,
        tutorial_completed=False,
        tutorial_progress=None,
        personality_dimensions=None,
        personality_archetype=None,
        personality_confidence=None,
        personality_quiz_progress=None,
        adaptive_context=None,
        behavioral_profile=None,
        engagement_patterns=None,
    )


@pytest.mark.asyncio
class TestUserRepositoryCreateOperations:
    """Test user creation operations with validation and error handling."""

    async def test_create_user_success(self, user_repository, mock_session, sample_user):
        """Test successful user creation."""
        # Setup mock result
        mock_result = Mock()
        mock_row = Mock()
        mock_row.telegram_id = sample_user.telegram_id
        mock_row.first_name = sample_user.first_name
        mock_row.username = sample_user.username
        mock_row.last_name = sample_user.last_name
        mock_row.language_code = sample_user.language_code
        mock_row.created_at = sample_user.created_at
        mock_row.updated_at = sample_user.updated_at
        mock_row.is_active = sample_user.is_active
        mock_row.onboarding_state = sample_user.onboarding_state
        mock_row.onboarding_completed = sample_user.onboarding_completed
        mock_row.tutorial_completed = sample_user.tutorial_completed
        mock_row.tutorial_progress = sample_user.tutorial_progress
        mock_row.personality_dimensions = sample_user.personality_dimensions
        mock_row.personality_archetype = sample_user.personality_archetype
        mock_row.personality_confidence = sample_user.personality_confidence
        mock_row.personality_quiz_progress = sample_user.personality_quiz_progress
        mock_row.adaptive_context = sample_user.adaptive_context
        mock_row.behavioral_profile = sample_user.behavioral_profile
        mock_row.engagement_patterns = sample_user.engagement_patterns

        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.create(sample_user)

        # Verify
        assert result.telegram_id == sample_user.telegram_id
        assert result.first_name == sample_user.first_name
        assert result.username == sample_user.username

        # Verify database operations
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    async def test_create_user_integrity_error(self, user_repository, mock_session, sample_user):
        """Test user creation with integrity constraint violation."""
        # Setup
        mock_session.execute.side_effect = IntegrityError("Duplicate key", None, None)

        # Execute & Verify
        with pytest.raises(IntegrityError):
            await user_repository.create(sample_user)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    async def test_create_user_general_error(self, user_repository, mock_session, sample_user):
        """Test user creation with general database error."""
        # Setup
        mock_session.execute.side_effect = SQLAlchemyError("Database connection lost")

        # Execute & Verify
        with pytest.raises(SQLAlchemyError):
            await user_repository.create(sample_user)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

    async def test_create_user_with_complex_data(self, user_repository, mock_session):
        """Test user creation with complex JSON data."""
        # Setup user with complex data
        complex_user = TelegramUser(
            telegram_id=67890,
            first_name="Complex User",
            tutorial_progress={
                "sections_completed": ["intro", "basics"],
                "current_section": "advanced",
                "engagement_score": 0.85,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            personality_dimensions={
                "exploration": 0.8,
                "competitiveness": 0.6,
                "narrative": 0.7,
                "social": 0.5,
            },
            adaptive_context={
                "context_type": "onboarding",
                "preferences": {"tutorial_style": "interactive"},
                "behavioral_patterns": ["explorer", "achiever"],
            },
        )

        # Setup mock result
        mock_result = Mock()
        mock_row = Mock()
        # Set all attributes for the complex user
        for attr_name in [
            'telegram_id', 'first_name', 'username', 'last_name', 'language_code',
            'created_at', 'updated_at', 'is_active', 'onboarding_state',
            'onboarding_completed', 'tutorial_completed', 'tutorial_progress',
            'personality_dimensions', 'personality_archetype', 'personality_confidence',
            'personality_quiz_progress', 'adaptive_context', 'behavioral_profile',
            'engagement_patterns'
        ]:
            setattr(mock_row, attr_name, getattr(complex_user, attr_name))

        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.create(complex_user)

        # Verify complex data was preserved
        assert result.tutorial_progress["engagement_score"] == 0.85
        assert result.personality_dimensions["exploration"] == 0.8
        assert result.adaptive_context["context_type"] == "onboarding"


@pytest.mark.asyncio
class TestUserRepositoryReadOperations:
    """Test user retrieval operations with various scenarios."""

    async def test_get_by_telegram_id_success(self, user_repository, mock_session):
        """Test successful user retrieval by telegram_id."""
        # Setup
        telegram_id = 12345
        mock_result = Mock()
        mock_row = self._create_mock_row(telegram_id, "Found User")
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_telegram_id(telegram_id)

        # Verify
        assert result is not None
        assert result.telegram_id == telegram_id
        assert result.first_name == "Found User"

        # Verify SQL query was executed
        mock_session.execute.assert_called_once()

    async def test_get_by_telegram_id_not_found(self, user_repository, mock_session):
        """Test user retrieval when user doesn't exist."""
        # Setup
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_telegram_id(99999)

        # Verify
        assert result is None

    async def test_get_by_telegram_id_database_error(self, user_repository, mock_session):
        """Test user retrieval with database error."""
        # Setup
        mock_session.execute.side_effect = SQLAlchemyError("Connection timeout")

        # Execute & Verify
        with pytest.raises(SQLAlchemyError):
            await user_repository.get_by_telegram_id(12345)

    async def test_get_by_username_success(self, user_repository, mock_session):
        """Test successful user retrieval by username."""
        # Setup
        username = "testuser"
        mock_result = Mock()
        mock_row = self._create_mock_row(12345, "User", username=username)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_username(username)

        # Verify
        assert result is not None
        assert result.username == username

        # Verify case-insensitive query was used
        mock_session.execute.assert_called_once()

    async def test_get_by_username_case_insensitive(self, user_repository, mock_session):
        """Test case-insensitive username search."""
        # Setup
        mock_result = Mock()
        mock_row = self._create_mock_row(12345, "User", username="TestUser")
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Execute with different case
        result = await user_repository.get_by_username("TESTUSER")

        # Verify
        assert result is not None
        assert result.username == "TestUser"

    async def test_get_by_username_not_found(self, user_repository, mock_session):
        """Test username search when user doesn't exist."""
        # Setup
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_username("nonexistent")

        # Verify
        assert result is None

    def _create_mock_row(self, telegram_id: int, first_name: str, username: Optional[str] = None):
        """Helper method to create mock database row."""
        mock_row = Mock()
        mock_row.telegram_id = telegram_id
        mock_row.first_name = first_name
        mock_row.username = username
        mock_row.last_name = None
        mock_row.language_code = "en"
        mock_row.created_at = datetime.now(timezone.utc)
        mock_row.updated_at = datetime.now(timezone.utc)
        mock_row.is_active = True
        mock_row.onboarding_state = "newcomer"
        mock_row.onboarding_completed = False
        mock_row.tutorial_completed = False
        mock_row.tutorial_progress = None
        mock_row.personality_dimensions = None
        mock_row.personality_archetype = None
        mock_row.personality_confidence = None
        mock_row.personality_quiz_progress = None
        mock_row.adaptive_context = None
        mock_row.behavioral_profile = None
        mock_row.engagement_patterns = None
        return mock_row


@pytest.mark.asyncio
class TestUserRepositoryUpdateOperations:
    """Test user update operations with validation and error handling."""

    async def test_update_user_success(self, user_repository, mock_session, sample_user):
        """Test successful user update."""
        # Setup - simulate update with returned row
        mock_result = Mock()
        mock_row = self._create_updated_mock_row(sample_user)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.update(sample_user)

        # Verify
        assert result.telegram_id == sample_user.telegram_id
        assert result.first_name == sample_user.first_name

        # Verify database operations
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    async def test_update_user_not_found(self, user_repository, mock_session, sample_user):
        """Test user update when user doesn't exist."""
        # Setup
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute & Verify
        with pytest.raises(SQLAlchemyError, match="User not found for update"):
            await user_repository.update(sample_user)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

    async def test_update_user_database_error(self, user_repository, mock_session, sample_user):
        """Test user update with database error."""
        # Setup
        mock_session.execute.side_effect = SQLAlchemyError("Update failed")

        # Execute & Verify
        with pytest.raises(SQLAlchemyError):
            await user_repository.update(sample_user)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

    async def test_update_user_with_complex_changes(self, user_repository, mock_session):
        """Test user update with complex data changes."""
        # Setup user with complex updates
        user = TelegramUser(
            telegram_id=12345,
            first_name="Updated User",
            personality_dimensions={
                "exploration": 0.9,  # Changed from 0.8
                "competitiveness": 0.7,  # Changed from 0.6
                "narrative": 0.7,
                "social": 0.5,
            },
            tutorial_progress={
                "sections_completed": ["intro", "basics", "advanced"],  # Added section
                "engagement_score": 0.95,  # Improved score
            },
            adaptive_context={
                "updated_preferences": True,
                "new_behavioral_pattern": "social_explorer",
            },
        )

        # Setup mock result
        mock_result = Mock()
        mock_row = self._create_updated_mock_row(user)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.update(user)

        # Verify complex data was updated
        assert result.personality_dimensions["exploration"] == 0.9
        assert len(result.tutorial_progress["sections_completed"]) == 3
        assert result.adaptive_context["new_behavioral_pattern"] == "social_explorer"

    def _create_updated_mock_row(self, user: User):
        """Helper method to create mock row for updated user."""
        mock_row = Mock()
        for attr_name in [
            'telegram_id', 'first_name', 'username', 'last_name', 'language_code',
            'created_at', 'updated_at', 'is_active', 'onboarding_state',
            'onboarding_completed', 'tutorial_completed', 'tutorial_progress',
            'personality_dimensions', 'personality_archetype', 'personality_confidence',
            'personality_quiz_progress', 'adaptive_context', 'behavioral_profile',
            'engagement_patterns'
        ]:
            setattr(mock_row, attr_name, getattr(user, attr_name))
        return mock_row


@pytest.mark.asyncio
class TestUserRepositoryDeleteOperations:
    """Test user deletion operations (soft delete)."""

    async def test_delete_user_success(self, user_repository, mock_session):
        """Test successful user soft deletion."""
        # Setup
        telegram_id = 12345
        mock_result = Mock()
        mock_result.rowcount = 1  # One row affected
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.delete(telegram_id)

        # Verify
        assert result is True

        # Verify database operations
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    async def test_delete_user_not_found(self, user_repository, mock_session):
        """Test user deletion when user doesn't exist."""
        # Setup
        mock_result = Mock()
        mock_result.rowcount = 0  # No rows affected
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.delete(99999)

        # Verify
        assert result is False

    async def test_delete_user_database_error(self, user_repository, mock_session):
        """Test user deletion with database error."""
        # Setup
        mock_session.execute.side_effect = SQLAlchemyError("Delete failed")

        # Execute & Verify
        with pytest.raises(SQLAlchemyError):
            await user_repository.delete(12345)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
class TestUserRepositoryListOperations:
    """Test user listing and querying operations."""

    async def test_get_active_users_success(self, user_repository, mock_session):
        """Test retrieving all active users."""
        # Setup
        mock_result = Mock()
        mock_rows = [
            self._create_mock_user_row(12345, "User 1", is_active=True),
            self._create_mock_user_row(67890, "User 2", is_active=True),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_active_users()

        # Verify
        assert len(result) == 2
        assert all(user.is_active for user in result)
        assert result[0].telegram_id == 12345
        assert result[1].telegram_id == 67890

    async def test_get_active_users_empty(self, user_repository, mock_session):
        """Test retrieving active users when none exist."""
        # Setup
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_active_users()

        # Verify
        assert len(result) == 0

    async def test_get_by_language_code_success(self, user_repository, mock_session):
        """Test retrieving users by language code."""
        # Setup
        language_code = "es"
        mock_result = Mock()
        mock_rows = [
            self._create_mock_user_row(12345, "Usuario 1", language_code="es"),
            self._create_mock_user_row(67890, "Usuario 2", language_code="es"),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_language_code(language_code)

        # Verify
        assert len(result) == 2
        assert all(user.language_code == "es" for user in result)

    async def test_get_by_language_code_not_found(self, user_repository, mock_session):
        """Test language code search with no results."""
        # Setup
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_by_language_code("fr")

        # Verify
        assert len(result) == 0

    async def test_count_users_success(self, user_repository, mock_session):
        """Test counting total users."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 150
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.count_users()

        # Verify
        assert result == 150

    async def test_count_active_users_success(self, user_repository, mock_session):
        """Test counting active users."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 125
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.count_active_users()

        # Verify
        assert result == 125

    async def test_get_users_paginated_success(self, user_repository, mock_session):
        """Test paginated user retrieval."""
        # Setup
        limit = 10
        offset = 20
        mock_result = Mock()
        mock_rows = [
            self._create_mock_user_row(i, f"User {i}")
            for i in range(20, 30)  # Simulating offset 20, limit 10
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.get_users_paginated(limit, offset)

        # Verify
        assert len(result) == 10
        assert result[0].telegram_id == 20
        assert result[-1].telegram_id == 29

    async def test_search_users_by_name_success(self, user_repository, mock_session):
        """Test searching users by name."""
        # Setup
        search_term = "John"
        mock_result = Mock()
        mock_rows = [
            self._create_mock_user_row(12345, "John Doe"),
            self._create_mock_user_row(67890, "Johnny Cash", last_name="Cash"),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        # Execute
        result = await user_repository.search_users_by_name(search_term)

        # Verify
        assert len(result) == 2
        assert "John" in result[0].first_name
        assert "John" in result[1].first_name

    async def test_search_users_by_name_case_insensitive(self, user_repository, mock_session):
        """Test case-insensitive name search."""
        # Setup
        mock_result = Mock()
        mock_rows = [
            self._create_mock_user_row(12345, "john smith", last_name="smith"),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        # Execute with uppercase search
        result = await user_repository.search_users_by_name("SMITH")

        # Verify
        assert len(result) == 1
        assert result[0].last_name == "smith"

    def _create_mock_user_row(
        self, 
        telegram_id: int, 
        first_name: str, 
        username: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "en",
        is_active: bool = True
    ):
        """Helper method to create mock user row for list operations."""
        mock_row = Mock()
        mock_row.telegram_id = telegram_id
        mock_row.first_name = first_name
        mock_row.username = username
        mock_row.last_name = last_name
        mock_row.language_code = language_code
        mock_row.created_at = datetime.now(timezone.utc)
        mock_row.updated_at = datetime.now(timezone.utc)
        mock_row.is_active = is_active
        mock_row.onboarding_state = "newcomer"
        mock_row.onboarding_completed = False
        mock_row.tutorial_completed = False
        mock_row.tutorial_progress = None
        mock_row.personality_dimensions = None
        mock_row.personality_archetype = None
        mock_row.personality_confidence = None
        mock_row.personality_quiz_progress = None
        mock_row.adaptive_context = None
        mock_row.behavioral_profile = None
        mock_row.engagement_patterns = None
        return mock_row


@pytest.mark.asyncio
class TestUserRepositoryBulkOperations:
    """Test bulk operations for performance."""

    async def test_bulk_create_success(self, user_repository, mock_session):
        """Test bulk user creation."""
        # Setup
        users = [
            TelegramUser(telegram_id=i, first_name=f"User {i}")
            for i in range(1, 6)
        ]

        # Mock successful creation for each user
        async def mock_create(user):
            return user

        user_repository.create = AsyncMock(side_effect=mock_create)

        # Execute
        result = await user_repository.bulk_create(users)

        # Verify
        assert result == 5
        assert user_repository.create.call_count == 5

    async def test_bulk_create_with_duplicates(self, user_repository, mock_session):
        """Test bulk creation with some duplicates."""
        # Setup
        users = [
            TelegramUser(telegram_id=1, first_name="User 1"),
            TelegramUser(telegram_id=2, first_name="User 2"),
            TelegramUser(telegram_id=3, first_name="User 3"),
        ]

        # Mock creation with one duplicate
        async def mock_create_with_duplicate(user):
            if user.telegram_id == 2:
                raise IntegrityError("Duplicate key", None, None)
            return user

        user_repository.create = AsyncMock(side_effect=mock_create_with_duplicate)

        # Execute
        result = await user_repository.bulk_create(users)

        # Verify - should create 2 out of 3 users (skip duplicate)
        assert result == 2
        assert user_repository.create.call_count == 3

    async def test_bulk_create_empty_list(self, user_repository):
        """Test bulk creation with empty list."""
        # Execute
        result = await user_repository.bulk_create([])

        # Verify
        assert result == 0


@pytest.mark.asyncio
class TestUserRepositoryErrorHandling:
    """Test error handling and edge cases."""

    async def test_row_to_telegram_user_conversion_error(self, user_repository):
        """Test error handling in row to TelegramUser conversion."""
        # Setup invalid row data
        mock_row = Mock()
        mock_row.telegram_id = "invalid"  # Should be int
        mock_row.first_name = None  # Required field

        # Execute & Verify
        with pytest.raises(SQLAlchemyError):
            user_repository._row_to_telegram_user(mock_row)

    async def test_database_connection_failure(self, user_repository, mock_session):
        """Test handling of database connection failures."""
        # Setup
        mock_session.execute.side_effect = SQLAlchemyError("Connection lost")

        # Execute & Verify
        with pytest.raises(SQLAlchemyError):
            await user_repository.get_by_telegram_id(12345)

    async def test_concurrent_operations_consistency(self, user_repository, mock_session):
        """Test repository consistency with concurrent operations."""
        # Setup
        telegram_ids = [100001, 100002, 100003]
        
        # Mock successful queries
        def mock_get_result(telegram_id):
            mock_result = Mock()
            mock_row = Mock()
            mock_row.telegram_id = telegram_id
            mock_row.first_name = f"User {telegram_id}"
            # Set all other required attributes
            for attr in ['username', 'last_name', 'language_code', 'created_at', 
                        'updated_at', 'is_active', 'onboarding_state', 'onboarding_completed',
                        'tutorial_completed', 'tutorial_progress', 'personality_dimensions',
                        'personality_archetype', 'personality_confidence', 'personality_quiz_progress',
                        'adaptive_context', 'behavioral_profile', 'engagement_patterns']:
                setattr(mock_row, attr, None if attr not in ['language_code', 'is_active'] 
                       else ('en' if attr == 'language_code' else True))
                        
            mock_result.fetchone.return_value = mock_row
            return mock_result

        async def concurrent_get_user(telegram_id):
            mock_session.execute.return_value = mock_get_result(telegram_id)
            return await user_repository.get_by_telegram_id(telegram_id)

        # Execute concurrent operations
        tasks = [concurrent_get_user(tid) for tid in telegram_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        successful_results = [r for r in results if isinstance(r, TelegramUser)]
        assert len(successful_results) == len(telegram_ids)

    async def test_transaction_rollback_scenarios(self, user_repository, mock_session):
        """Test various transaction rollback scenarios."""
        # Test 1: Create operation rollback
        mock_session.execute.side_effect = IntegrityError("Constraint violation", None, None)
        
        sample_user = TelegramUser(telegram_id=12345, first_name="Test User")
        
        with pytest.raises(IntegrityError):
            await user_repository.create(sample_user)
        
        mock_session.rollback.assert_called()
        
        # Reset mocks
        mock_session.reset_mock()
        
        # Test 2: Update operation rollback
        mock_session.execute.side_effect = SQLAlchemyError("Update failed")
        
        with pytest.raises(SQLAlchemyError):
            await user_repository.update(sample_user)
        
        mock_session.rollback.assert_called()

    async def test_data_integrity_validation(self, user_repository, mock_session):
        """Test data integrity validation during conversions."""
        # Test with valid data
        valid_row = Mock()
        valid_row.telegram_id = 12345
        valid_row.first_name = "Valid User"
        valid_row.username = None
        valid_row.last_name = None
        valid_row.language_code = "en"
        valid_row.created_at = datetime.now(timezone.utc)
        valid_row.updated_at = datetime.now(timezone.utc)
        valid_row.is_active = True
        valid_row.onboarding_state = "newcomer"
        valid_row.onboarding_completed = False
        valid_row.tutorial_completed = False
        valid_row.tutorial_progress = None
        valid_row.personality_dimensions = None
        valid_row.personality_archetype = None
        valid_row.personality_confidence = None
        valid_row.personality_quiz_progress = None
        valid_row.adaptive_context = None
        valid_row.behavioral_profile = None
        valid_row.engagement_patterns = None

        # Should succeed
        result = user_repository._row_to_telegram_user(valid_row)
        assert result.telegram_id == 12345
        assert result.first_name == "Valid User"

        # Test with invalid data (triggers TelegramUser validation)
        invalid_row = Mock()
        invalid_row.telegram_id = -1  # Invalid telegram_id
        invalid_row.first_name = ""   # Empty first_name
        # Set other required fields to avoid AttributeError
        for attr in ['username', 'last_name', 'language_code', 'created_at', 
                    'updated_at', 'is_active', 'onboarding_state', 'onboarding_completed',
                    'tutorial_completed', 'tutorial_progress', 'personality_dimensions',
                    'personality_archetype', 'personality_confidence', 'personality_quiz_progress',
                    'adaptive_context', 'behavioral_profile', 'engagement_patterns']:
            setattr(invalid_row, attr, None if attr != 'language_code' else 'en')

        # Should fail due to TelegramUser validation
        with pytest.raises(Exception):  # Could be ValueError or SQLAlchemyError
            user_repository._row_to_telegram_user(invalid_row)