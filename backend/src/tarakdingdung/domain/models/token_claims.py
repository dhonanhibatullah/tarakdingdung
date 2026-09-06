from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TokenClaimsAccess:
    user_id: UUID
    name: str
    username: str
    role: str
    permissions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TokenClaimsRefresh:
    user_id: UUID
