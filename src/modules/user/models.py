"""User Module Models - Minimal Implementation.

This module contains essential user models for Diana Bot V2 MVP.
Focuses on core user management without over-engineering.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class UserState(Enum):
    """Simple user states for basic functionality."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class User:
    """
    Essential user model for Diana Bot V2 MVP.
    
    Focuses on core user data and preferences without over-engineering.
    """
    
    # Core Identity (Required)
    user_id: int  # Telegram ID
    username: Optional[str] = None
    first_name: str = ""
    last_name: Optional[str] = None
    
    # User Settings
    language_code: str = "es"  # Default Spanish for Diana Bot
    is_vip: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Simple preferences storage
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Telegram metadata for integration
    telegram_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate user data after initialization."""
        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValueError("user_id must be a positive integer")
            
        if not self.first_name.strip():
            raise ValueError("first_name cannot be empty")
            
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_active = datetime.now(timezone.utc)
        
    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        self.preferences[key] = value
        
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference with optional default."""
        return self.preferences.get(key, default)


@dataclass 
class UserStats:
    """User statistics for admin and analytics."""
    
    total_interactions: int = 0
    registration_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    vip_since: Optional[datetime] = None


# Exceptions for user operations
class UserNotFoundError(Exception):
    """Raised when a user cannot be found."""
    pass


class DuplicateUserError(Exception):
    """Raised when attempting to create a user that already exists."""
    pass


class InvalidUserDataError(Exception):
    """Raised when user data is invalid."""
    pass