"""UserRepository - Minimal Implementation.

PostgreSQL-based repository for essential user data operations.
Follows clean architecture patterns with efficient database queries.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None

from .interfaces import IUserRepository
from .models import User, DuplicateUserError, UserNotFoundError, InvalidUserDataError


logger = logging.getLogger(__name__)


class UserRepository(IUserRepository):
    """PostgreSQL implementation of user repository."""

    def __init__(self, connection_pool: Optional[Any] = None):
        """Initialize with database connection pool."""
        if asyncpg is None:
            raise ImportError("asyncpg is required but not installed. Run: pip install asyncpg")
        
        self._pool = connection_pool
        self._table_name = "users"

    async def create(self, user: User) -> User:
        """Create a new user in database."""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")

        try:
            async with self._pool.acquire() as conn:
                # Check for duplicate
                existing = await conn.fetchrow(
                    f"SELECT user_id FROM {self._table_name} WHERE user_id = $1",
                    user.user_id
                )
                if existing:
                    raise DuplicateUserError(f"User {user.user_id} already exists")

                # Insert new user
                await conn.execute(
                    f"""
                    INSERT INTO {self._table_name} 
                    (user_id, username, first_name, last_name, language_code, is_vip,
                     created_at, last_active, preferences, telegram_metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    user.user_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.language_code,
                    user.is_vip,
                    user.created_at,
                    user.last_active,
                    json.dumps(user.preferences),
                    json.dumps(user.telegram_metadata)
                )

                logger.info(f"Created user {user.user_id} ({user.first_name})")
                return user

        except asyncpg.PostgresError as e:
            logger.error(f"Database error creating user {user.user_id}: {e}")
            raise InvalidUserDataError(f"Failed to create user: {e}")

    async def get_by_user_id(self, user_id: int) -> Optional[User]:
        """Get user by user_id (Telegram ID)."""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"""
                    SELECT user_id, username, first_name, last_name, language_code, 
                           is_vip, created_at, last_active, preferences, telegram_metadata
                    FROM {self._table_name} 
                    WHERE user_id = $1
                    """,
                    user_id
                )

                if not row:
                    return None

                return self._row_to_user(row)

        except asyncpg.PostgresError as e:
            logger.error(f"Database error getting user {user_id}: {e}")
            return None

    async def update(self, user: User) -> User:
        """Update existing user."""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    f"""
                    UPDATE {self._table_name}
                    SET username = $2, first_name = $3, last_name = $4, 
                        language_code = $5, is_vip = $6, last_active = $7,
                        preferences = $8, telegram_metadata = $9
                    WHERE user_id = $1
                    """,
                    user.user_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.language_code,
                    user.is_vip,
                    user.last_active,
                    json.dumps(user.preferences),
                    json.dumps(user.telegram_metadata)
                )

                if result == "UPDATE 0":
                    raise UserNotFoundError(f"User {user.user_id} not found")

                logger.info(f"Updated user {user.user_id}")
                return user

        except asyncpg.PostgresError as e:
            logger.error(f"Database error updating user {user.user_id}: {e}")
            raise InvalidUserDataError(f"Failed to update user: {e}")

    async def get_users_for_service(self, user_ids: List[int]) -> List[User]:
        """Get multiple users by IDs for service integration."""
        if not self._pool or not user_ids:
            return []

        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT user_id, username, first_name, last_name, language_code, 
                           is_vip, created_at, last_active, preferences, telegram_metadata
                    FROM {self._table_name} 
                    WHERE user_id = ANY($1)
                    ORDER BY user_id
                    """,
                    user_ids
                )

                return [self._row_to_user(row) for row in rows]

        except asyncpg.PostgresError as e:
            logger.error(f"Database error getting users for service: {e}")
            return []

    async def count_users(self) -> int:
        """Count total number of users."""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")

        try:
            async with self._pool.acquire() as conn:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {self._table_name}")
                return count or 0

        except asyncpg.PostgresError as e:
            logger.error(f"Database error counting users: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """Check repository health and database connectivity."""
        health = {
            "status": "unhealthy",
            "database": "disconnected",
            "users_count": 0,
            "last_check": datetime.now(timezone.utc).isoformat()
        }

        if not self._pool:
            health["error"] = "Database pool not initialized"
            return health

        try:
            async with self._pool.acquire() as conn:
                # Test basic connectivity
                await conn.fetchval("SELECT 1")
                
                # Get user count
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {self._table_name}")
                
                health.update({
                    "status": "healthy",
                    "database": "connected",
                    "users_count": count or 0
                })

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health["error"] = str(e)

        return health

    def _row_to_user(self, row: Any) -> User:
        """Convert database row to User model."""
        try:
            preferences = json.loads(row['preferences']) if row['preferences'] else {}
            telegram_metadata = json.loads(row['telegram_metadata']) if row['telegram_metadata'] else {}
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error for user {row['user_id']}: {e}")
            preferences = {}
            telegram_metadata = {}

        return User(
            user_id=row['user_id'],
            username=row['username'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            language_code=row['language_code'],
            is_vip=row['is_vip'],
            created_at=row['created_at'],
            last_active=row['last_active'],
            preferences=preferences,
            telegram_metadata=telegram_metadata
        )


# Database connection factory
async def create_user_repository(database_url: str) -> UserRepository:
    """Create UserRepository with database connection pool."""
    if asyncpg is None:
        raise ImportError("asyncpg is required but not installed. Run: pip install asyncpg")
    
    try:
        pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            server_settings={
                'jit': 'off'  # Disable JIT for better performance on small queries
            }
        )
        
        repository = UserRepository(pool)
        logger.info("UserRepository created with database pool")
        return repository
        
    except Exception as e:
        logger.error(f"Failed to create UserRepository: {e}")
        raise