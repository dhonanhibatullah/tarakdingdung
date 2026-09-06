from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RolePermission:
    id: UUID
    role_id: UUID
    permission_id: UUID
    created_at: datetime
    created_by: UUID | None = None
