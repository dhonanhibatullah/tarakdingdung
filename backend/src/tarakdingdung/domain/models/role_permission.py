from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RolePermission:
    role_id: str
    permission_id: str
