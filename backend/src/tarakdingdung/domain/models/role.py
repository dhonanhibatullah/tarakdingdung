from dataclasses import dataclass

from tarakdingdung.domain.models.error import DomainError, ErrorType


@dataclass(frozen=True, slots=True)
class Role:
    id: str
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise DomainError("role name is required", ErrorType.VALIDATION)
