from typing import Any, TypeVar, cast

from sqlalchemy import CursorResult, Result

from tarakdingdung.domain.models.error import DomainError, ErrorType

_T = TypeVar("_T")


def require(value: _T | None, message: str) -> _T:
    """Narrow an ``Optional`` that must not be ``None`` at this point — e.g. the
    id returned by ``INSERT ... RETURNING``. A ``None`` here means the statement
    silently produced no row, which is a failure, not a domain-empty result.
    """
    if value is None:
        raise DomainError(message, ErrorType.FAILURE)
    return value


def rows_affected(result: Result[Any]) -> int:
    """``rowcount`` is declared on ``CursorResult`` (the runtime type for DML
    statements) rather than the ``Result`` that ``AsyncSession.execute`` is
    typed to return, so the cast is static-only and safe for UPDATE/DELETE.
    """
    return cast(CursorResult[Any], result).rowcount
