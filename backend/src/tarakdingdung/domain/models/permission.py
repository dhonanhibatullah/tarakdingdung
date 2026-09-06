from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Permission:
    id: UUID
    name: str
    description: str
    preferences: dict
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_by: UUID | None = None
