from enum import StrEnum


class ErrorType(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    BAD_ARGS = "BAD_ARGS"
    CONFLICT = "CONFLICT"
    BAD_STATE = "BAD_STATE"
    VALIDATION = "VALIDATION"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TIMEOUT = "TIMEOUT"
    UNIMPLEMENTED = "UNIMPLEMENTED"
    FAILURE = "FAILURE"
    UNKNOWN = "UNKNOWN"
    USERNAME_EXISTS = "USERNAME_EXISTS"
    ROLE_NAME_EXISTS = "ROLE_NAME_EXISTS"
    PERMISSION_NAME_EXISTS = "PERMISSION_NAME_EXISTS"
    ROLE_PERMISSION_EXISTS = "ROLE_PERMISSION_EXISTS"


class DomainError(Exception):
    def __init__(self, message: str, type: ErrorType, source: Exception | None = None) -> None:
        self.message = message
        self.type = type
        self.source = source
        super().__init__(message)

    def __str__(self) -> str:
        if self.source is not None:
            return f"[{self.type}] {self.message}: {self.source}"
        return f"[{self.type}] {self.message}"
