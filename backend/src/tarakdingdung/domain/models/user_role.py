from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserRole:
    user_id: str
    role_id: str
