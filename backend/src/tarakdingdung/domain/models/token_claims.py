from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub: str
    username: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    exp: int = 0
    type: str = "access"
