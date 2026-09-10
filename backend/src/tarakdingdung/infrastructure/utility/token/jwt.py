import time

import jwt

from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaims


class JwtToken(Token):
    def __init__(
        self,
        access_secret: str,
        refresh_secret: str,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
        now_seconds: callable = time.time,
    ) -> None:
        self._access_secret = access_secret
        self._refresh_secret = refresh_secret
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds
        self._now = now_seconds

    def _encode(
        self, claims: TokenClaims, secret: str, ttl_seconds: int, token_type: str
    ) -> str:
        now = int(self._now())
        payload = {
            "sub": claims.sub,
            "username": claims.username,
            "roles": claims.roles,
            "permissions": claims.permissions,
            "type": token_type,
            "iat": now,
            "exp": now + ttl_seconds,
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def encode_access(self, claims: TokenClaims) -> str:
        return self._encode(claims, self._access_secret, self._access_ttl, "access")

    def encode_refresh(self, claims: TokenClaims) -> str:
        return self._encode(claims, self._refresh_secret, self._refresh_ttl, "refresh")

    def _decode(self, token: str, secret: str, expected_type: str) -> TokenClaims:
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise DomainError("invalid token", ErrorType.UNAUTHORIZED) from exc
        if payload.get("type") != expected_type:
            raise DomainError("wrong token type", ErrorType.UNAUTHORIZED)
        return TokenClaims(
            sub=payload["sub"],
            username=payload["username"],
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            exp=payload["exp"],
            type=payload["type"],
        )

    def decode(self, token: str) -> TokenClaims:
        return self._decode(token, self._access_secret, "access")

    def decode_refresh(self, token: str) -> TokenClaims:
        return self._decode(token, self._refresh_secret, "refresh")
