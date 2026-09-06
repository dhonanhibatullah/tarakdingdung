import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.presentation.http.utils.errors import domain_error_response


@pytest.mark.parametrize("etype,status,title", [
    (ErrorType.NOT_FOUND, 404, "Not Found"),
    (ErrorType.VALIDATION, 400, "Invalid Format"),
    (ErrorType.FORBIDDEN, 403, "Access Denied"),
    (ErrorType.UNAUTHORIZED, 401, "Unauthorized"),
    (ErrorType.TOKEN_EXPIRED, 401, "Session Expired"),
    (ErrorType.CONFLICT, 409, "Already Exists"),
    (ErrorType.FAILURE, 500, "Internal Server Error"),
])
def test_status_and_title_mapping(etype, status, title):
    s, body = domain_error_response(DomainError("boom", etype))
    assert s == status and body.error == title


def test_override_message_used_when_present():
    _s, body = domain_error_response(DomainError("raw", ErrorType.USERNAME_EXISTS))
    assert body.message == "This username is already taken."


def test_own_message_used_when_no_override():
    _s, body = domain_error_response(DomainError("name is required", ErrorType.VALIDATION))
    assert body.message == "name is required"


def test_unknown_type_falls_back_to_500(monkeypatch):
    err = DomainError("x", ErrorType.NOT_FOUND)
    object.__setattr__(err, "type", "TOTALLY_UNKNOWN")
    s, body = domain_error_response(err)
    assert s == 500 and body.error == "Internal Server Error"
