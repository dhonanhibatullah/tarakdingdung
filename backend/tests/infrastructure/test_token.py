import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh
from tarakdingdung.infrastructure.utility.token.jwt import JwtToken


_ACCESS_SECRET = "a" * 32
_REFRESH_SECRET = "r" * 32


def _token(now=None):
    return JwtToken(access_secret=_ACCESS_SECRET, refresh_secret=_REFRESH_SECRET,
                    access_ttl=timedelta(minutes=15), refresh_ttl=timedelta(days=1),
                    now=now or (lambda: datetime.now(tz=timezone.utc)))


@pytest.mark.asyncio
async def test_access_roundtrip_preserves_claims():
    t = _token()
    uid = uuid.uuid4()
    raw = await t.generate_access(TokenClaimsAccess(
        user_id=uid, name="Grace", username="grace", role="super",
        permissions=("user:get", "user:add")))
    claims = await t.validate_access(raw)
    assert claims.user_id == uid and claims.role == "super"
    assert claims.permissions == ("user:get", "user:add")


@pytest.mark.asyncio
async def test_refresh_roundtrip():
    t = _token()
    uid = uuid.uuid4()
    raw = await t.generate_refresh(TokenClaimsRefresh(user_id=uid))
    assert (await t.validate_refresh(raw)).user_id == uid


@pytest.mark.asyncio
async def test_expired_access_maps_to_token_expired():
    past = lambda: datetime(2020, 1, 1, tzinfo=timezone.utc)
    issuer = _token(now=past)
    raw = await issuer.generate_access(TokenClaimsAccess(
        user_id=uuid.uuid4(), name="n", username="u", role="r", permissions=()))
    with pytest.raises(DomainError) as ei:
        await _token().validate_access(raw)
    assert ei.value.type is ErrorType.TOKEN_EXPIRED


@pytest.mark.asyncio
async def test_tampered_token_maps_to_token_invalid():
    with pytest.raises(DomainError) as ei:
        await _token().validate_access("not.a.jwt")
    assert ei.value.type is ErrorType.TOKEN_INVALID


@pytest.mark.asyncio
async def test_wrong_secret_is_token_invalid():
    other = JwtToken(access_secret="d" * 32, refresh_secret=_REFRESH_SECRET,
                     access_ttl=timedelta(minutes=5), refresh_ttl=timedelta(days=1))
    raw = await other.generate_access(TokenClaimsAccess(
        user_id=uuid.uuid4(), name="n", username="u", role="r", permissions=()))
    with pytest.raises(DomainError) as ei:
        await _token().validate_access(raw)
    assert ei.value.type is ErrorType.TOKEN_INVALID
