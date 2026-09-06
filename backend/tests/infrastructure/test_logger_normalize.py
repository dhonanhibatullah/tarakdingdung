import json

import pytest

from tarakdingdung.infrastructure.logger.normalize import normalize_meta
from tarakdingdung.infrastructure.logger.leveled.json import JsonLeveledLogging
from tarakdingdung.domain.models.logger import LoggerLevel


def test_normalize_meta_stringifies_exceptions():
    out = normalize_meta({"err": ValueError("boom"), "id": 7})
    assert out == {"err": "boom", "id": 7}


def test_normalize_meta_none_is_empty_dict():
    assert normalize_meta(None) == {}


@pytest.mark.asyncio
async def test_json_logger_emits_exception_string(capsys):
    logger = JsonLeveledLogging(LoggerLevel.DEBUG)
    await logger.error("tag", "failed", {"err": RuntimeError("db down")})
    line = capsys.readouterr().out.strip()
    payload = json.loads(line)
    assert payload["meta"]["err"] == "db down"
