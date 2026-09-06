import pytest

from tarakdingdung.application.shared import validation as v
from tarakdingdung.domain.models.error import DomainError, ErrorType


@pytest.mark.parametrize("fn,good", [
    (v.required_person_name, "Grace O'Hara-Hopper"),
    (v.required_username, "grace_hopper-1"),
    (v.required_role_name, "fleet_operator"),
    (v.required_permission_name, "node:get"),
])
def test_required_accepts_valid(fn, good):
    assert fn(good, "field") == good.strip()


def test_required_strips_whitespace():
    assert v.required_username("  grace  ", "username") == "grace"


@pytest.mark.parametrize("fn,bad", [
    (v.required_person_name, ""),
    (v.required_person_name, "  "),
    (v.required_username, "ab"),
    (v.required_username, "bad name"),
    (v.required_role_name, "x" * 129),
    (v.required_permission_name, "no spaces here"),
])
def test_required_rejects_invalid(fn, bad):
    with pytest.raises(DomainError) as ei:
        fn(bad, "field")
    assert ei.value.type is ErrorType.VALIDATION


@pytest.mark.parametrize("value,expected", [(None, None), ("grace", "grace")])
def test_optional_username(value, expected):
    assert v.optional_username(value, "username") == expected


@pytest.mark.parametrize("pw", ["BrewMeUp!42", "abcdefgh"])
def test_required_password_accepts(pw):
    assert v.required_password(pw, "password") == pw


@pytest.mark.parametrize("pw", ["short", "with space", "x" * 73, ""])
def test_required_password_rejects(pw):
    with pytest.raises(DomainError) as ei:
        v.required_password(pw, "password")
    assert ei.value.type is ErrorType.VALIDATION
