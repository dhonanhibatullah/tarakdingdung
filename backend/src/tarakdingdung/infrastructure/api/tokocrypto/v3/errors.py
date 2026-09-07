"""Turn a Binance-standard error response into a DomainError.

The `/api/v3/*` endpoints put the real reason in a `{"code","msg"}` JSON body
alongside a 4xx status, unlike `/open/v1` which wraps success and failure in
one 200 envelope. The numeric codes are the same Binance set, so the table in
`tokocrypto/errors.py` is reused rather than duplicated.
"""

import json

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.tokocrypto.errors import ERROR_CODE

_STATUS_FALLBACK: dict[int, ErrorType] = {
    401: ErrorType.UNAUTHORIZED,
    403: ErrorType.UNAUTHORIZED,
    404: ErrorType.NOT_FOUND,
    408: ErrorType.TIMEOUT,
    429: ErrorType.RATE_LIMITED,
}


def map_v3_error(status: int, body: str) -> DomainError:
    code: object = None
    message = body[:200]
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict) and "code" in parsed:
        code = parsed.get("code")
        message = parsed.get("msg") or message

    kind = ERROR_CODE.get(code) if isinstance(code, int) else None
    if kind is None:
        kind = _STATUS_FALLBACK.get(status, ErrorType.UPSTREAM)

    label = f"[{code}]" if isinstance(code, int) else f"HTTP {status}"
    return DomainError(f"tokocrypto.v3 {label}: {message}", kind)
