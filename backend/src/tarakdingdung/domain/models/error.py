from enum import Enum


class ErrorType(str, Enum):
    VALIDATION = "validation"
    BAD_ARGS = "bad_args"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    INTERNAL = "internal"


class DomainError(Exception):
    def __init__(self, message: str, error_type: ErrorType):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
