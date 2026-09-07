from typing import Any

from tarakdingdung.domain.models.error import DomainError, ErrorType

_V1_ERROR_CODE: dict[str, ErrorType] = {
    "invalid_credentials": ErrorType.UNAUTHORIZED,
    "no_permission": ErrorType.UNAUTHORIZED,
    "too_many_requests": ErrorType.RATE_LIMITED,
    "invalid_date": ErrorType.BAD_ARGS,
    "invalid_pair": ErrorType.BAD_ARGS,
}

# Indodax Trade API v2 numeric codes (Binance-style).
_V2_ERROR_CODE: dict[int, ErrorType] = {
    -1001: ErrorType.UPSTREAM,
    -1002: ErrorType.UNAUTHORIZED,
    -1021: ErrorType.BAD_ARGS,
    -1022: ErrorType.UNAUTHORIZED,
    -1099: ErrorType.NOT_FOUND,
    -1102: ErrorType.BAD_ARGS,
    -1121: ErrorType.BAD_ARGS,
    -1130: ErrorType.BAD_ARGS,
    -1003: ErrorType.RATE_LIMITED,
    -2010: ErrorType.BAD_STATE,
    -2013: ErrorType.NOT_FOUND,
    -2014: ErrorType.UNAUTHORIZED,
    -2015: ErrorType.FORBIDDEN,
}


def raise_v1_error(body: Any) -> None:
    """Raise if an Indodax v1 "tapi" body carries ``{"success": 0}``."""
    if not isinstance(body, dict) or body.get("success") in (1, "1"):
        return
    message = body.get("error") or body.get("message") or "indodax v1 request failed"
    kind = _V1_ERROR_CODE.get(str(body.get("error_code") or ""), ErrorType.UPSTREAM)
    raise DomainError(f"indodax.v1: {message}", kind)


def raise_v2_error(body: Any) -> None:
    """Raise if an Indodax v2 body carries a negative ``code``."""
    if not isinstance(body, dict):
        return
    code = body.get("code")
    if not isinstance(code, int) or code >= 0:
        return
    message = body.get("msg") or "indodax v2 request failed"
    kind = _V2_ERROR_CODE.get(code, ErrorType.UPSTREAM)
    raise DomainError(f"indodax.v2 [{code}]: {message}", kind)
