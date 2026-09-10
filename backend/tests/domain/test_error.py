from tarakdingdung.domain.models.error import DomainError, ErrorType


def test_domain_error_carries_type():
    err = DomainError("bad input", ErrorType.VALIDATION)
    assert err.message == "bad input"
    assert err.error_type is ErrorType.VALIDATION
    assert str(err) == "bad input"


def test_domain_error_is_an_exception():
    try:
        raise DomainError("boom", ErrorType.INTERNAL)
    except DomainError as err:
        assert err.error_type is ErrorType.INTERNAL
