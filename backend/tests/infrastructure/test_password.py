import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword


@pytest.mark.asyncio
async def test_hash_then_compare_roundtrip():
    pw = BcryptPassword(cost=4)
    h = await pw.hash("BrewMeUp42")
    assert h != "BrewMeUp42"
    await pw.compare(h, "BrewMeUp42")  # no raise


@pytest.mark.asyncio
async def test_compare_mismatch_raises_unauthorized():
    pw = BcryptPassword(cost=4)
    h = await pw.hash("correct-horse")
    with pytest.raises(DomainError) as ei:
        await pw.compare(h, "wrong")
    assert ei.value.type is ErrorType.UNAUTHORIZED


@pytest.mark.asyncio
async def test_compare_overlong_password_is_unauthorized_not_failure():
    pw = BcryptPassword(cost=4)
    h = await pw.hash("something")
    with pytest.raises(DomainError) as ei:
        await pw.compare(h, "x" * 100)
    assert ei.value.type is ErrorType.UNAUTHORIZED
    assert ei.value.type is not ErrorType.FAILURE


@pytest.mark.asyncio
async def test_out_of_range_cost_falls_back():
    pw = BcryptPassword(cost=99)
    h = await pw.hash("x-secret-1")
    await pw.compare(h, "x-secret-1")
