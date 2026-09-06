import datetime
import json
import uuid

import pytest

from tarakdingdung.infrastructure.logger.normalize import normalize_meta
from tarakdingdung.infrastructure.logger.leveled.json import JsonLeveledLogging
from tarakdingdung.infrastructure.logger.leveled.plain import BasicLeveledLogging
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


def test_normalize_meta_coerces_non_primitives():
    uid = uuid.uuid4()
    now = datetime.datetime.now()
    out = normalize_meta({"user_id": uid, "when": now, "count": 3, "ok": True, "none": None})
    assert out == {
        "user_id": str(uid),
        "when": str(now),
        "count": 3,
        "ok": True,
        "none": None,
    }


@pytest.mark.asyncio
async def test_json_logger_handles_uuid_and_datetime_meta(capsys):
    logger = JsonLeveledLogging(LoggerLevel.DEBUG)
    uid = uuid.uuid4()
    now = datetime.datetime.now()
    await logger.error("tag", "failed", {"user_id": uid, "when": now})
    line = capsys.readouterr().out.strip()
    payload = json.loads(line)
    assert payload["meta"]["user_id"] == str(uid)
    assert payload["meta"]["when"] == str(now)


@pytest.mark.asyncio
async def test_plain_logger_handles_uuid_and_datetime_meta(capsys):
    logger = BasicLeveledLogging(LoggerLevel.DEBUG)
    uid = uuid.uuid4()
    now = datetime.datetime.now()
    await logger.error("tag", "failed", {"user_id": uid, "when": now})
    line = capsys.readouterr().out.strip()
    assert str(uid) in line
    assert "|" in line
