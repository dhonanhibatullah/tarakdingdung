import pytest

from sqlalchemy.exc import NoResultFound

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)


@pytest.mark.parametrize("limit,expected", [(-3, 0), (0, 0), (10, 10)])
def test_normalize_limit(limit, expected):
    assert normalize_limit(limit) == expected


@pytest.mark.parametrize("page,limit,expected", [
    (1, 10, 0), (0, 10, 0), (3, 10, 20), (2, 25, 25), (5, 0, 0),
])
def test_normalize_offset(page, limit, expected):
    assert normalize_offset(page, limit) == expected


@pytest.mark.parametrize("value,expected", [
    (None, None), ("", None), ("  ", None), ("grace", "%grace%"),
])
def test_search_pattern(value, expected):
    assert search_pattern(value) == expected


@pytest.mark.parametrize("value,expected", [
    ("50%", "%50\\%%"),
    ("a_b", "%a\\_b%"),
    ("back\\slash", "%back\\\\slash%"),
    ("%_\\", "%\\%\\_\\\\%"),
])
def test_search_pattern_escapes_like_metacharacters(value, expected):
    assert search_pattern(value) == expected


class _FakeAsyncpgError(Exception):
    def __init__(self, sqlstate, constraint_name=""):
        super().__init__("db error")
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


class _FakeIntegrityError(Exception):
    def __init__(self, orig):
        super().__init__("integrity")
        self.orig = orig


def test_map_unique_violation_matches_conflict_target():
    exc = _FakeIntegrityError(_FakeAsyncpgError("23505", "uq_users_username"))
    err = map_db_error("failed to create user", exc,
                       ConflictMatch("username", ErrorType.USERNAME_EXISTS))
    assert isinstance(err, DomainError)
    assert err.type is ErrorType.USERNAME_EXISTS
    assert err.source is exc


def test_map_unique_violation_without_match_is_conflict():
    exc = _FakeIntegrityError(_FakeAsyncpgError("23505", "some_other_idx"))
    assert map_db_error("x", exc).type is ErrorType.CONFLICT


def test_map_no_result_found_is_not_found():
    exc = NoResultFound("no rows")
    err = map_db_error("failed to read role", exc)
    assert err.type is ErrorType.NOT_FOUND
    assert err.source is exc


@pytest.mark.parametrize("sqlstate,expected", [
    ("23503", ErrorType.CONFLICT),
    ("23502", ErrorType.VALIDATION),
    ("22P02", ErrorType.VALIDATION),
    ("22001", ErrorType.VALIDATION),
    ("23514", ErrorType.VALIDATION),
    ("99999", ErrorType.UNKNOWN),
])
def test_map_other_sqlstates(sqlstate, expected):
    exc = _FakeIntegrityError(_FakeAsyncpgError(sqlstate))
    assert map_db_error("x", exc).type is expected
