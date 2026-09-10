import sys
from typing import TextIO

from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger

_LEVEL_ORDER = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}


class PlainLeveledLogger(LeveledLogger):
    def __init__(
        self,
        name: str = "tarakdingdung",
        level: str = "INFO",
        stream: TextIO | None = None,
    ) -> None:
        self._name = name
        self._level = level.upper()
        self._stream = stream or sys.stdout

    def _emit(self, level: str, message: str, fields: dict) -> None:
        if _LEVEL_ORDER[level.upper()] < _LEVEL_ORDER[self._level]:
            return
        parts = [f"{level.upper():<7}", f"[{self._name}]", message]
        if fields:
            parts.append(" ".join(f"{k}={v}" for k, v in fields.items()))
        print(" ".join(parts), file=self._stream, flush=True)

    def debug(self, message: str, **fields) -> None:
        self._emit("debug", message, fields)

    def info(self, message: str, **fields) -> None:
        self._emit("info", message, fields)

    def warning(self, message: str, **fields) -> None:
        self._emit("warning", message, fields)

    def error(self, message: str, **fields) -> None:
        self._emit("error", message, fields)
