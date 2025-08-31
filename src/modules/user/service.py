from .interfaces import IUserService, IUserRepository
from .models import User

class UserService(IUserService):
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    def find_or_create_user(self, user_id: int, first_name: str, last_name: str | None, username: str | None) -> User:
        """
        Finds a user by their Telegram ID or creates them if they don't exist.
        This is the core of the zero-friction registration.
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
        
        return self.user_repository.create_user(user_data)
