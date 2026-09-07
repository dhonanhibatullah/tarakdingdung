from typing import Any

from tarakdingdung.domain.models.error import DomainError, ErrorType

ERROR_CODE: dict[int, ErrorType] = {
    -1000: ErrorType.UPSTREAM,
    -1001: ErrorType.UPSTREAM,
    -1003: ErrorType.RATE_LIMITED,
    -1013: ErrorType.BAD_ARGS,
    -1015: ErrorType.RATE_LIMITED,
    -1021: ErrorType.BAD_ARGS,
    -1022: ErrorType.UNAUTHORIZED,
    -1100: ErrorType.BAD_ARGS,
    -1102: ErrorType.BAD_ARGS,
    -1104: ErrorType.BAD_ARGS,
    -1106: ErrorType.BAD_ARGS,
    -1111: ErrorType.BAD_ARGS,
    -1121: ErrorType.BAD_ARGS,
    -1131: ErrorType.BAD_ARGS,
    -2010: ErrorType.BAD_STATE,
    -2011: ErrorType.BAD_STATE,
    -2013: ErrorType.NOT_FOUND,
    -2014: ErrorType.UNAUTHORIZED,
    -2015: ErrorType.FORBIDDEN,
    -2021: ErrorType.BAD_STATE,
    -2026: ErrorType.BAD_STATE,
}


def unwrap(body: Any) -> Any:
    """Return ``data`` from a Tokocrypto ``{"code": 0, "msg": "", "data": ...}``
    envelope; raise ``DomainError`` when ``code`` is non-zero.
    """
    if not isinstance(body, dict) or "code" not in body:
        return body
    code = body.get("code")
    if code in (0, "0"):
        return body.get("data")
    message = body.get("msg") or "tokocrypto request failed"
    kind = ERROR_CODE.get(code if isinstance(code, int) else 0, ErrorType.UPSTREAM)
    raise DomainError(f"tokocrypto [{code}]: {message}", kind)
