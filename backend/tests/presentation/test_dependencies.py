import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess
from tarakdingdung.presentation.http.dependencies.auth import _extract_bearer
from tarakdingdung.presentation.http.dependencies.permission import require


def test_extract_bearer_accepts_prefixed_and_raw():
    assert _extract_bearer("Bearer abc.def") == "abc.def"
    assert _extract_bearer("abc.def") == "abc.def"
    assert _extract_bearer("  Bearer   spaced  ") == "spaced"
    assert _extract_bearer(None) is None
    assert _extract_bearer("") is None


@pytest.mark.asyncio
async def test_require_allows_when_permissions_present():
    claims = TokenClaimsAccess(user_id=uuid.uuid4(), name="n", username="u", role="r",
                               permissions=("user:get", "user:add"))
    dep = require("user:get")
    assert await dep(claims=claims) is None


@pytest.mark.asyncio
async def test_require_forbids_when_missing():
    claims = TokenClaimsAccess(user_id=uuid.uuid4(), name="n", username="u", role="r",
                               permissions=("user:get",))
    dep = require("user:add")
    with pytest.raises(DomainError) as ei:
        await dep(claims=claims)
    assert ei.value.type is ErrorType.FORBIDDEN
