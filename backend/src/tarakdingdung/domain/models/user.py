from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    role_id: UUID
    name: str
    bio: str
    username: str
    password_hash: str
    preferences: dict
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UserListItem:
    user: User
    role_name: str
