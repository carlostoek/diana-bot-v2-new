"""User Module Interfaces - Minimal Implementation.

This module defines essential interfaces for the User Module following 
Clean Architecture patterns for Diana Bot V2 MVP.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import User, UserStats


class IUserRepository(ABC):
    """Repository interface for essential user data persistence operations."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user in the repository."""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> Optional[User]:
        """Retrieve a user by their user ID (Telegram ID)."""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user in the repository."""
        pass

    @abstractmethod
    async def get_users_for_service(self, user_ids: List[int]) -> List[User]:
        """Get multiple users by IDs for service integration."""
        pass

    @abstractmethod
    async def count_users(self) -> int:
        """Count total number of users."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check repository health and database connectivity."""
        pass


class IUserService(ABC):
    """Service interface for essential user business operations."""

    # Core user operations
    @abstractmethod
    async def register_user(self, telegram_user: dict) -> User:
        """Register a new user from Telegram data."""
        pass

    @abstractmethod
    async def get_user(self, user_id: int) -> User:
        """Get user by ID with error handling."""
        pass

    @abstractmethod
    async def update_preferences(self, user_id: int, preferences: Dict[str, Any]) -> User:
        """Update user preferences."""
        pass

    # Activity tracking
    @abstractmethod
    async def mark_user_active(self, user_id: int) -> None:
        """Mark user as active (update last_active timestamp)."""
        pass

    @abstractmethod
    async def get_user_stats(self, user_id: int) -> UserStats:
        """Get user statistics."""
        pass

    # Service integration
    @abstractmethod
    async def get_users_for_service(self, user_ids: List[int]) -> List[User]:
        """Get users for service integration (e.g., GamificationService)."""
        pass

    @abstractmethod
    async def is_vip_user(self, user_id: int) -> bool:
        """Check if user has VIP status."""
        pass

    # Admin operations
    @abstractmethod
    async def set_vip_status(self, user_id: int, is_vip: bool) -> User:
        """Set VIP status for user."""
        pass

    @abstractmethod
    async def get_user_count(self) -> int:
        """Get total user count."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Service health check."""
        pass