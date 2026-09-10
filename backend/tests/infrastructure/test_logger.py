import json

from tarakdingdung.infrastructure.logger.leveled.json import JsonLeveledLogger
from tarakdingdung.infrastructure.logger.leveled.plain import PlainLeveledLogger


def test_plain_logger_writes_level_and_fields(capsys):
    logger = PlainLeveledLogger(name="test-plain")
    logger.info("hello", foo="bar")
    out = capsys.readouterr().out
    assert "hello" in out
    assert "foo=bar" in out
    assert "INFO" in out


def test_json_logger_writes_valid_json(capsys):
    logger = JsonLeveledLogger(name="test-json")
    logger.error("failed", code=42)
    out = capsys.readouterr().out
    record = json.loads(out.strip())
    assert record["level"] == "ERROR"
    assert record["message"] == "failed"
    assert record["code"] == 42


def test_json_logger_respects_level(capsys):
    logger = JsonLeveledLogger(name="test-json", level="WARNING")
    logger.debug("hidden")
    logger.info("also hidden")
    logger.warning("visible")
    out = capsys.readouterr().out
    assert "hidden" not in out
    assert "visible" in out
