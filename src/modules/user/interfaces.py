from abc import ABC, abstractmethod
from .models import User

class IUserRepository(ABC):

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    def create_user(self, user_data: dict) -> User:
        ...

class IUserService(ABC):

    @abstractmethod
    def find_or_create_user(self, user_id: int, first_name: str, last_name: str | None, username: str | None) -> User:
        ...
