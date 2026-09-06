from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh


def _default_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class JwtToken(Token):
    def __init__(self, *, access_secret: str, refresh_secret: str,
                 access_ttl: timedelta, refresh_ttl: timedelta,
                 now: Callable[[], datetime] = _default_now) -> None:
        self._access_secret = access_secret
        self._refresh_secret = refresh_secret
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._now = now

    async def generate_access(self, claims: TokenClaimsAccess) -> str:
        now = self._now()
        payload = {
            "user_id": str(claims.user_id), "name": claims.name,
            "username": claims.username, "role": claims.role,
            "permissions": list(claims.permissions), "sub": str(claims.user_id),
            "iat": now, "nbf": now, "exp": now + self._access_ttl,
        }
        return jwt.encode(payload, self._access_secret, algorithm="HS256")

    async def validate_access(self, token: str) -> TokenClaimsAccess:
        payload = self._decode(token, self._access_secret)
        return TokenClaimsAccess(
            user_id=UUID(payload.get("user_id") or payload["sub"]),
            name=payload["name"], username=payload["username"], role=payload["role"],
            permissions=tuple(payload.get("permissions", [])),
        )

    async def generate_refresh(self, claims: TokenClaimsRefresh) -> str:
        now = self._now()
        payload = {"user_id": str(claims.user_id), "sub": str(claims.user_id),
                   "iat": now, "nbf": now, "exp": now + self._refresh_ttl}
        return jwt.encode(payload, self._refresh_secret, algorithm="HS256")

    async def validate_refresh(self, token: str) -> TokenClaimsRefresh:
        payload = self._decode(token, self._refresh_secret)
        return TokenClaimsRefresh(user_id=UUID(payload.get("user_id") or payload["sub"]))

    @staticmethod
    def _decode(token: str, secret: str) -> dict:
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as exc:
            raise DomainError("token has expired", ErrorType.TOKEN_EXPIRED, exc) from exc
        except jwt.InvalidTokenError as exc:
            raise DomainError("token is invalid", ErrorType.TOKEN_INVALID, exc) from exc
