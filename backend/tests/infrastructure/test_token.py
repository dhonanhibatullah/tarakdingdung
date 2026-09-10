import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaims
from tarakdingdung.infrastructure.utility.token.jwt import JwtToken


def make_token():
    return JwtToken("a" * 32, "r" * 32, 900, 86400)


def test_access_roundtrip():
    t = make_token()
    claims = TokenClaims(sub="1", username="alice", roles=["admin"], permissions=["p:r"])
    token = t.encode_access(claims)
    decoded = t.decode(token)
    assert decoded.sub == "1"
    assert decoded.username == "alice"
    assert decoded.roles == ["admin"]
    assert decoded.permissions == ["p:r"]
    assert decoded.type == "access"


def test_refresh_roundtrip():
    t = make_token()
    token = t.encode_refresh(TokenClaims(sub="1", username="alice"))
    decoded = t.decode_refresh(token)
    assert decoded.sub == "1"
    assert decoded.type == "refresh"


def test_decode_rejects_tampered_token():
    t = make_token()
    token = t.encode_access(TokenClaims(sub="1", username="alice"))
    with pytest.raises(DomainError) as exc:
        t.decode(token[:-1])
    assert exc.value.error_type is ErrorType.UNAUTHORIZED


def test_decode_rejects_wrong_secret():
    t = make_token()
    other = JwtToken("x" * 32, "r" * 32, 900, 86400)
    token = t.encode_access(TokenClaims(sub="1", username="alice"))
    with pytest.raises(DomainError):
        other.decode(token)


def test_decode_rejects_wrong_type():
    t = make_token()
    token = t.encode_refresh(TokenClaims(sub="1", username="alice"))
    with pytest.raises(DomainError):
        t.decode(token)
