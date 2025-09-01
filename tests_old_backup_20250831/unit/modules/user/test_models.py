"""Tests for User models - Minimal Implementation."""

import pytest
from datetime import datetime, timezone
from src.modules.user.models import User, UserStats, UserState, UserNotFoundError, DuplicateUserError, InvalidUserDataError


class TestUser:
    """Test User model."""
    
    def test_user_creation_valid_data(self):
        """Test creating user with valid data."""
        user = User(
            user_id=123456789,
            first_name="Diana",
            username="diana_bot",
            last_name="Bot",
            language_code="es"
        )
        
        assert user.user_id == 123456789
        assert user.first_name == "Diana"
        assert user.username == "diana_bot"
        assert user.last_name == "Bot"
        assert user.language_code == "es"
        assert user.is_vip is False
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.last_active, datetime)
        assert user.preferences == {}
        assert user.telegram_metadata == {}
    
    def test_user_creation_minimal_data(self):
        """Test creating user with minimal required data."""
        user = User(
            user_id=123456789,
            first_name="Diana"
        )
        
        assert user.user_id == 123456789
        assert user.first_name == "Diana"
        assert user.username is None
        assert user.last_name is None
        assert user.language_code == "es"  # Default
        assert user.is_vip is False
    
    def test_user_creation_invalid_user_id(self):
        """Test user creation with invalid user ID."""
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            User(user_id=0, first_name="Diana")
        
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            User(user_id=-1, first_name="Diana")
    
    def test_user_creation_empty_first_name(self):
        """Test user creation with empty first name."""
        with pytest.raises(ValueError, match="first_name cannot be empty"):
            User(user_id=123, first_name="")
        
        with pytest.raises(ValueError, match="first_name cannot be empty"):
            User(user_id=123, first_name="   ")
    
    def test_update_activity(self):
        """Test updating user activity timestamp."""
        user = User(user_id=123, first_name="Diana")
        old_active = user.last_active
        
        user.update_activity()
        
        assert user.last_active > old_active
    
    def test_set_preference(self):
        """Test setting user preferences."""
        user = User(user_id=123, first_name="Diana")
        
        user.set_preference("notification_enabled", True)
        user.set_preference("theme", "dark")
        
        assert user.preferences["notification_enabled"] is True
        assert user.preferences["theme"] == "dark"
    
    def test_get_preference(self):
        """Test getting user preferences."""
        user = User(user_id=123, first_name="Diana")
        user.preferences = {"theme": "dark"}
        
        assert user.get_preference("theme") == "dark"
        assert user.get_preference("nonexistent") is None
        assert user.get_preference("nonexistent", "default") == "default"
    
    def test_user_with_metadata(self):
        """Test user with telegram metadata."""
        metadata = {
            "id": 123456789,
            "is_bot": False,
            "first_name": "Diana",
            "language_code": "es"
        }
        
        user = User(
            user_id=123456789,
            first_name="Diana",
            telegram_metadata=metadata
        )
        
        assert user.telegram_metadata == metadata


class TestUserStats:
    """Test UserStats model."""
    
    def test_user_stats_default_creation(self):
        """Test creating UserStats with defaults."""
        stats = UserStats()
        
        assert stats.total_interactions == 0
        assert isinstance(stats.registration_date, datetime)
        assert stats.is_active is True
        assert stats.vip_since is None
    
    def test_user_stats_with_data(self):
        """Test creating UserStats with data."""
        vip_date = datetime.now(timezone.utc)
        reg_date = datetime.now(timezone.utc)
        
        stats = UserStats(
            total_interactions=100,
            registration_date=reg_date,
            is_active=False,
            vip_since=vip_date
        )
        
        assert stats.total_interactions == 100
        assert stats.registration_date == reg_date
        assert stats.is_active is False
        assert stats.vip_since == vip_date


class TestUserState:
    """Test UserState enum."""
    
    def test_user_state_values(self):
        """Test UserState enum values."""
        assert UserState.ACTIVE.value == "active"
        assert UserState.INACTIVE.value == "inactive"


class TestUserExceptions:
    """Test user-related exceptions."""
    
    def test_user_not_found_error(self):
        """Test UserNotFoundError."""
        with pytest.raises(UserNotFoundError):
            raise UserNotFoundError("User not found")
    
    def test_duplicate_user_error(self):
        """Test DuplicateUserError."""
        with pytest.raises(DuplicateUserError):
            raise DuplicateUserError("User already exists")
    
    def test_invalid_user_data_error(self):
        """Test InvalidUserDataError."""
        with pytest.raises(InvalidUserDataError):
            raise InvalidUserDataError("Invalid data")


class TestUserModelValidation:
    """Test user model validation scenarios."""
    
    def test_user_creation_with_preferences(self):
        """Test user creation with initial preferences."""
        prefs = {"theme": "dark", "notifications": True}
        
        user = User(
            user_id=123,
            first_name="Diana",
            preferences=prefs
        )
        
        assert user.preferences == prefs
    
    def test_user_preference_updates(self):
        """Test preference updates don't affect original dict."""
        original_prefs = {"theme": "light"}
        user = User(
            user_id=123,
            first_name="Diana",
            preferences=original_prefs.copy()
        )
        
        user.set_preference("theme", "dark")
        
        assert user.preferences["theme"] == "dark"
        assert original_prefs["theme"] == "light"  # Original unchanged
    
    def test_user_timestamp_validation(self):
        """Test that timestamps are set correctly."""
        before = datetime.now(timezone.utc)
        user = User(user_id=123, first_name="Diana")
        after = datetime.now(timezone.utc)
        
        assert before <= user.created_at <= after
        assert before <= user.last_active <= after
    
    def test_user_vip_status_default(self):
        """Test VIP status defaults to False."""
        user = User(user_id=123, first_name="Diana")
        assert user.is_vip is False
    
    def test_user_language_default(self):
        """Test language defaults to Spanish."""
        user = User(user_id=123, first_name="Diana")
        assert user.language_code == "es"