from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, NoResultFound

from tarakdingdung.domain.models.error import DomainError, ErrorType

_VALIDATION_STATES = {"23502", "22P02", "22001", "23514"}


@dataclass(frozen=True, slots=True)
class ConflictMatch:
    contains: str
    type: ErrorType


def map_db_error(message: str, exc: Exception, *conflicts: ConflictMatch) -> DomainError:
    if isinstance(exc, NoResultFound):
        return DomainError(message, ErrorType.NOT_FOUND, exc)

    orig = getattr(exc, "orig", exc)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    constraint = (getattr(orig, "constraint_name", "") or "") + " " + str(orig)

    if isinstance(exc, IntegrityError) or sqlstate is not None:
        if sqlstate == "23505":
            for match in conflicts:
                if match.contains in constraint:
                    return DomainError(message, match.type, exc)
            return DomainError(message, ErrorType.CONFLICT, exc)
        if sqlstate == "23503":
            return DomainError(message, ErrorType.CONFLICT, exc)
        if sqlstate in _VALIDATION_STATES:
            return DomainError(message, ErrorType.VALIDATION, exc)

    return DomainError(message, ErrorType.UNKNOWN, exc)
