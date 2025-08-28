"""User Module - Minimal Implementation.

Essential user management components for Diana Bot V2 MVP.
"""

from .models import User, UserStats, UserState, UserNotFoundError, DuplicateUserError, InvalidUserDataError
from .interfaces import IUserRepository, IUserService
from .repository import UserRepository, create_user_repository
from .service import UserService, create_user_service
from .events import UserRegisteredEvent, UserPreferencesUpdatedEvent, UserActivityEvent
from .migrations import create_user_table, verify_table_structure, drop_user_table

__all__ = [
    # Models
    "User",
    "UserStats", 
    "UserState",
    
    # Exceptions
    "UserNotFoundError",
    "DuplicateUserError", 
    "InvalidUserDataError",
    
    # Interfaces
    "IUserRepository",
    "IUserService",
    
    # Implementations
    "UserRepository",
    "UserService",
    
    # Factory functions
    "create_user_repository",
    "create_user_service",
    
    # Events
    "UserRegisteredEvent",
    "UserPreferencesUpdatedEvent", 
    "UserActivityEvent",
    
    # Migrations
    "create_user_table",
    "verify_table_structure",
    "drop_user_table"
]