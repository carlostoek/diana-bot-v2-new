from src.core.security import create_access_token
from .interfaces import IUserService, IUserRepository
from .models import User
from src.core.interfaces import IEventBus
from src.core.events import UserEvent
import time
from collections import defaultdict

class UserService(IUserService):
    def __init__(self, user_repository: IUserRepository, event_bus: IEventBus):
        self.user_repository = user_repository
        self.event_bus = event_bus
        # Rate limiting state: user_id -> [timestamp1, timestamp2, ...]
        self._rate_limit_requests = defaultdict(list)
        self.rate_limit_max_requests = 100  # Max requests
        self.rate_limit_time_window = 60  # Time window in seconds

    def get_user_by_id(self, user_id: int) -> User | None:
        """
        Retrieves a user by their ID.
        """
        return self.user_repository.get_user_by_id(user_id)

    async def find_or_create_user(self, user_id: int, first_name: str, last_name: str | None, username: str | None) -> User:
        """
        Finds a user by their Telegram ID or creates them if they don't exist.
        Publishes a UserEvent on creation.
        """
        user = self.user_repository.get_user_by_id(user_id)
        if user:
            # Optionally, update user info if it has changed in Telegram
            # For now, we just return the user
            return user
        
        user_data = {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username
        }
        
        new_user = self.user_repository.create_user(user_data)

        # Publish event for user creation
        event = UserEvent(
            user_id=new_user.id,
            event_type="registered",
            user_data={"username": new_user.username, "first_name": new_user.first_name}
        )
        await self.event_bus.publish(event)

        return new_user

    def update_user_profile(self, user_id: int, update_data: dict) -> User | None:
        """
        Updates a user's profile information.
        """
        # Here you could add validation or logic to restrict what can be updated.
        # For now, we'll allow updating any field passed in.
        return self.user_repository.update_user(user_id, update_data)

    def is_admin(self, user_id: int) -> bool:
        """
        Checks if a user is an admin.
        """
        user = self.get_user_by_id(user_id)
        return user.is_admin if user else False

    def has_role(self, user_id: int, role: str) -> bool:
        """
        Checks if a user has a specific role.
        """
        user = self.get_user_by_id(user_id)
        return user.role == role if user else False

    def get_user_token(self, user_id: int) -> str | None:
        """
        Generates a JWT for a given user.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        token_data = {"sub": str(user.id), "role": user.role}
        return create_access_token(data=token_data)

    def is_rate_limited(self, user_id: int) -> bool:
        """
        Checks if a user has exceeded the rate limit.
        """
        now = time.time()

        # Remove old timestamps
        user_requests = self._rate_limit_requests[user_id]
        valid_requests = [t for t in user_requests if now - t < self.rate_limit_time_window]
        self._rate_limit_requests[user_id] = valid_requests

        if len(valid_requests) >= self.rate_limit_max_requests:
            return True # Rate limited

        self._rate_limit_requests[user_id].append(now)
        return False # Not rate limited
