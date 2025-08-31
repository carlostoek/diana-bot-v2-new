"""User Module - Minimal Implementation.

Essential user management components for Diana Bot V2 MVP.
"""

from .models import User
from .interfaces import IUserRepository, IUserService
from .repository import UserRepository
from .service import UserService
from .events import UserCreated

__all__ = [
    # Models
    "User",
    
    # Interfaces
    "IUserRepository",
    "IUserService",
    
    # Implementations
    "UserRepository",
    "UserService",
    
    # Events
    "UserCreated",
]
