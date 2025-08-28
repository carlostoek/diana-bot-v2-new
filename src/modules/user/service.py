"""UserService - Minimal Implementation.

Core user service with essential functionality for Diana Bot V2 MVP.
Integrates with Event Bus and provides clean APIs for other services.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.interfaces import IEventBus
from .interfaces import IUserRepository, IUserService
from .models import User, UserStats, UserNotFoundError, DuplicateUserError, InvalidUserDataError
from .events import UserRegisteredEvent, UserPreferencesUpdatedEvent, UserActivityEvent


logger = logging.getLogger(__name__)


class UserService(IUserService):
    """Essential user service implementation."""

    def __init__(self, repository: IUserRepository, event_bus: Optional[IEventBus] = None):
        """Initialize with repository and optional event bus."""
        self._repository = repository
        self._event_bus = event_bus

    async def register_user(self, telegram_user: dict) -> User:
        """Register new user from Telegram data."""
        try:
            # Extract required data from Telegram
            user_id = telegram_user["id"]
            first_name = telegram_user["first_name"]
            username = telegram_user.get("username")
            last_name = telegram_user.get("last_name")
            language_code = telegram_user.get("language_code", "es")

            # Create user with minimal data
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                telegram_metadata=telegram_user.copy()
            )

            # Save to repository
            created_user = await self._repository.create(user)

            # Publish registration event
            if self._event_bus:
                event = UserRegisteredEvent(
                    user_id=user_id,
                    first_name=first_name,
                    username=username,
                    language_code=language_code
                )
                await self._event_bus.publish(event)

            logger.info(f"User registered: {user_id} ({first_name})")
            return created_user

        except Exception as e:
            logger.error(f"Failed to register user {telegram_user.get('id', 'unknown')}: {e}")
            raise InvalidUserDataError(f"Registration failed: {e}")

    async def get_user(self, user_id: int) -> User:
        """Get user by ID with error handling."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise InvalidUserDataError("user_id must be a positive integer")

        user = await self._repository.get_by_user_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        return user

    async def update_preferences(self, user_id: int, preferences: Dict[str, Any]) -> User:
        """Update user preferences."""
        # Get existing user
        user = await self.get_user(user_id)

        # Update preferences
        user.preferences.update(preferences)

        # Save changes
        updated_user = await self._repository.update(user)

        # Publish preferences updated event
        if self._event_bus:
            event = UserPreferencesUpdatedEvent(
                user_id=user_id,
                preferences=preferences
            )
            await self._event_bus.publish(event)

        logger.info(f"Updated preferences for user {user_id}")
        return updated_user

    async def mark_user_active(self, user_id: int) -> None:
        """Mark user as active (update last_active timestamp)."""
        try:
            user = await self.get_user(user_id)
            user.update_activity()
            await self._repository.update(user)

            # Publish activity event
            if self._event_bus:
                event = UserActivityEvent(
                    user_id=user_id,
                    activity_type="user_active",
                    activity_data={"timestamp": user.last_active.isoformat()}
                )
                await self._event_bus.publish(event)

        except UserNotFoundError:
            logger.warning(f"Attempted to mark non-existent user {user_id} as active")

    async def get_user_stats(self, user_id: int) -> UserStats:
        """Get user statistics."""
        user = await self.get_user(user_id)

        return UserStats(
            total_interactions=len(user.preferences.get("interaction_history", [])),
            registration_date=user.created_at,
            is_active=(datetime.now(timezone.utc) - user.last_active).days < 7,
            vip_since=user.created_at if user.is_vip else None
        )

    async def get_users_for_service(self, user_ids: List[int]) -> List[User]:
        """Get users for service integration."""
        if not user_ids:
            return []

        # Validate user IDs
        valid_ids = [uid for uid in user_ids if isinstance(uid, int) and uid > 0]
        if len(valid_ids) != len(user_ids):
            logger.warning(f"Invalid user IDs filtered out: {len(user_ids) - len(valid_ids)}")

        return await self._repository.get_users_for_service(valid_ids)

    async def is_vip_user(self, user_id: int) -> bool:
        """Check if user has VIP status."""
        try:
            user = await self.get_user(user_id)
            return user.is_vip
        except UserNotFoundError:
            return False

    async def set_vip_status(self, user_id: int, is_vip: bool) -> User:
        """Set VIP status for user."""
        user = await self.get_user(user_id)
        
        old_status = user.is_vip
        user.is_vip = is_vip
        
        updated_user = await self._repository.update(user)

        # Publish activity event for VIP status change
        if self._event_bus and old_status != is_vip:
            event = UserActivityEvent(
                user_id=user_id,
                activity_type="vip_status_changed",
                activity_data={"old_status": old_status, "new_status": is_vip}
            )
            await self._event_bus.publish(event)

        logger.info(f"VIP status for user {user_id} changed to {is_vip}")
        return updated_user

    async def get_user_count(self) -> int:
        """Get total user count."""
        return await self._repository.count_users()

    async def health_check(self) -> Dict[str, Any]:
        """Service health check."""
        health = {
            "status": "healthy",
            "service": "UserService",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repository": None,
            "event_bus": "connected" if self._event_bus else "not_configured"
        }

        try:
            # Check repository health
            repo_health = await self._repository.health_check()
            health["repository"] = repo_health
            
            # Service is unhealthy if repository is unhealthy
            if repo_health.get("status") != "healthy":
                health["status"] = "unhealthy"
                health["error"] = "Repository unhealthy"

        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = f"Health check failed: {e}"
            logger.error(f"UserService health check failed: {e}")

        return health

    # Additional utility methods for service integration
    async def get_user_language(self, user_id: int) -> str:
        """Get user's language preference."""
        try:
            user = await self.get_user(user_id)
            return user.language_code
        except UserNotFoundError:
            return "es"  # Default to Spanish

    async def bulk_mark_users_active(self, user_ids: List[int]) -> int:
        """Mark multiple users as active (for performance)."""
        successful_updates = 0
        
        for user_id in user_ids:
            try:
                await self.mark_user_active(user_id)
                successful_updates += 1
            except Exception as e:
                logger.warning(f"Failed to mark user {user_id} active: {e}")

        return successful_updates

    async def get_vip_users(self) -> List[User]:
        """Get all VIP users (useful for admin operations)."""
        try:
            # This is a simple implementation; for large scale, consider pagination
            all_users = await self._repository.get_users_for_service(
                # Would need a better approach for large datasets
                list(range(1, 1000000))  # Placeholder - should implement proper VIP query
            )
            return [user for user in all_users if user.is_vip]
        except Exception as e:
            logger.error(f"Failed to get VIP users: {e}")
            return []

    async def search_users_by_name(self, search_term: str) -> List[User]:
        """Search users by name (basic implementation)."""
        if not search_term or len(search_term.strip()) < 2:
            return []

        # This is a basic implementation - for production, implement proper search in repository
        try:
            # Would need to implement proper search in repository for efficiency
            logger.warning("search_users_by_name using basic implementation - implement in repository for production")
            return []
        except Exception as e:
            logger.error(f"User search failed: {e}")
            return []


# Factory function for creating UserService
async def create_user_service(repository: IUserRepository, event_bus: Optional[IEventBus] = None) -> UserService:
    """Create UserService with repository and event bus."""
    service = UserService(repository, event_bus)
    logger.info("UserService created successfully")
    return service