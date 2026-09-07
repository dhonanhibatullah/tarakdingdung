from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import httpx

from tarakdingdung.domain.models.error import DomainError, ErrorType

_STATUS_ERROR: dict[int, ErrorType] = {
    400: ErrorType.BAD_ARGS,
    401: ErrorType.UNAUTHORIZED,
    403: ErrorType.UNAUTHORIZED,
    404: ErrorType.NOT_FOUND,
    408: ErrorType.TIMEOUT,
    429: ErrorType.RATE_LIMITED,
}


def clean_params(params: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values and stringify bools so a param dict is wire-ready."""
    out: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        out[key] = "true" if value is True else "false" if value is False else value
    return out


def encode_params(params: dict[str, Any]) -> str:
    return urlencode(clean_params(params))


class RestClient:
    """Thin ``httpx.AsyncClient`` wrapper: sends a request, decodes the JSON
    body and maps transport failures and non-2xx responses to ``DomainError``.

    Exchange-specific success/error envelopes are handled by the callers.
    """

    def __init__(self, client: httpx.AsyncClient, *, base_url: str, tag: str,
                 error_mapper: Callable[[int, str], DomainError] | None = None) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._tag = tag
        self._error_mapper = error_mapper

    async def request(self, method: str, path: str, *, query: str | None = None,
                      body: str | None = None,
                      headers: dict[str, str] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{query}"
        try:
            response = await self._client.request(
                method, url, content=body, headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise DomainError(f"{self._tag} request timed out", ErrorType.TIMEOUT, exc) from exc
        except httpx.HTTPError as exc:
            raise DomainError(f"{self._tag} request failed", ErrorType.UPSTREAM, exc) from exc

        if response.status_code >= 400:
            if self._error_mapper is not None:
                raise self._error_mapper(response.status_code, response.text)
            kind = _STATUS_ERROR.get(response.status_code, ErrorType.UPSTREAM)
            raise DomainError(
                f"{self._tag} responded HTTP {response.status_code}: {response.text[:200]}",
                kind,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise DomainError(f"{self._tag} returned a non-JSON body",
                              ErrorType.UPSTREAM, exc) from exc
