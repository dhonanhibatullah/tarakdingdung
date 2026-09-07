import httpx
import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.tokocrypto.v3.errors import map_v3_error


def test_map_v3_error_reads_the_binance_code():
    err = map_v3_error(400, '{"code":-1121,"msg":"Invalid symbol."}')
    assert err.type is ErrorType.BAD_ARGS
    assert "Invalid symbol." in err.message


def test_map_v3_error_maps_a_state_code():
    err = map_v3_error(400, '{"code":-2010,"msg":"Account has insufficient balance."}')
    assert err.type is ErrorType.BAD_STATE


def test_map_v3_error_falls_back_to_status_when_body_is_opaque():
    assert map_v3_error(401, "not json").type is ErrorType.UNAUTHORIZED
    assert map_v3_error(500, "boom").type is ErrorType.UPSTREAM


def test_map_v3_error_unknown_code_is_upstream():
    assert map_v3_error(400, '{"code":-9999,"msg":"nope"}').type is ErrorType.UPSTREAM
