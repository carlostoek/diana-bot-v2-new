from abc import ABC, abstractmethod
from .models import User

class IUserRepository(ABC):

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    def create_user(self, user_data: dict) -> User:
        ...

    @abstractmethod
    def update_user(self, user_id: int, user_data: dict) -> User | None:
        ...

class IUserService(ABC):

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    async def find_or_create_user(self, user_id: int, first_name: str, last_name: str | None, username: str | None) -> User:
        ...

    @abstractmethod
    def update_user_profile(self, user_id: int, update_data: dict) -> User | None:
        ...

    @abstractmethod
    def is_admin(self, user_id: int) -> bool:
        ...

    @abstractmethod
    def has_role(self, user_id: int, role: str) -> bool:
        ...

    @abstractmethod
    def get_user_token(self, user_id: int) -> str | None:
        ...

    @abstractmethod
    def is_rate_limited(self, user_id: int) -> bool:
        ...
