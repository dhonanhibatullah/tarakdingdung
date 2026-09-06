import re

from tarakdingdung.domain.models.error import DomainError, ErrorType

_PERSON_NAME = re.compile(r"^[A-Za-z0-9' -]+$")
_USERNAME = re.compile(r"^[A-Za-z0-9_-]+$")
_ROLE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
_PERMISSION_NAME = re.compile(r"^[A-Za-z0-9/_:-]+$")
_PASSWORD = re.compile(r"^[\x21-\x7E]+$")


def _validate(value: str, field: str, pattern: re.Pattern[str],
              min_len: int, max_len: int, charset: str) -> str:
    value = value.strip()
    if not value:
        raise DomainError(f"{field} is required", ErrorType.VALIDATION)
    if not (min_len <= len(value) <= max_len):
        raise DomainError(
            f"{field} must be between {min_len} and {max_len} characters",
            ErrorType.VALIDATION)
    if not pattern.match(value):
        raise DomainError(f"{field} may only contain {charset}", ErrorType.VALIDATION)
    return value


def required_person_name(value: str, field: str) -> str:
    return _validate(value, field, _PERSON_NAME, 1, 128,
                     "alphanumeric characters, spaces, dashes, and apostrophes")


def optional_person_name(value: str | None, field: str) -> str | None:
    return None if value is None else required_person_name(value, field)


def required_username(value: str, field: str) -> str:
    return _validate(value, field, _USERNAME, 3, 128,
                     "alphanumeric characters, underscores, and dashes")


def optional_username(value: str | None, field: str) -> str | None:
    return None if value is None else required_username(value, field)


def required_role_name(value: str, field: str) -> str:
    return _validate(value, field, _ROLE_NAME, 3, 128,
                     "alphanumeric characters, underscores, and dashes")


def optional_role_name(value: str | None, field: str) -> str | None:
    return None if value is None else required_role_name(value, field)


def required_permission_name(value: str, field: str) -> str:
    return _validate(value, field, _PERMISSION_NAME, 3, 128,
                     "alphanumeric characters, slashes, underscores, dashes, and colons")


def optional_permission_name(value: str | None, field: str) -> str | None:
    return None if value is None else required_permission_name(value, field)


def required_password(value: str, field: str) -> str:
    if not value:
        raise DomainError(f"{field} is required", ErrorType.VALIDATION)
    if not (8 <= len(value) <= 72):
        raise DomainError(f"{field} must be between 8 and 72 characters", ErrorType.VALIDATION)
    if not _PASSWORD.match(value):
        raise DomainError(
            f"{field} may only contain printable characters and no spaces",
            ErrorType.VALIDATION)
    return value
