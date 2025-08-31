from dataclasses import dataclass

@dataclass
class UserCreated:
    user_id: int
    first_name: str
