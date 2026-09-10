from dataclasses import dataclass

from tarakdingdung.domain.models.error import DomainError, ErrorType


@dataclass(frozen=True, slots=True)
class User:
    id: str
    username: str
    email: str
    password_hash: str
    is_active: bool = True
    is_deleted: bool = False
    created_at: int = 0
    updated_at: int = 0

    def __post_init__(self) -> None:
        if not self.username:
            raise DomainError("username is required", ErrorType.VALIDATION)
        if not self.email:
            raise DomainError("email is required", ErrorType.VALIDATION)
