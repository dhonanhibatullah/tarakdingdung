import json
from datetime import datetime
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.logger import LoggerLevel
from tarakdingdung.infrastructure.logger.normalize import normalize_meta


class BasicLeveledLogging(LeveledLogger):
    def __init__(self, level: LoggerLevel) -> None:
        self.level = level
        
    async def error(self, tag: str, message: str, meta: dict) -> None:
        await self._log(LoggerLevel.ERROR, tag, message, meta)

    async def warn(self, tag: str, message: str, meta: dict) -> None:
        await self._log(LoggerLevel.WARN, tag, message, meta)

    async def info(self, tag: str, message: str, meta: dict) -> None:
        await self._log(LoggerLevel.INFO, tag, message, meta)

    async def debug(self, tag: str, message: str, meta: dict) -> None:
        await self._log(LoggerLevel.DEBUG, tag, message, meta)
    
    async def _log(self, level: LoggerLevel, tag: str, message: str, meta: dict) -> None:
        if self.level.order < level.order:
            return

        now = datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S") + f".{now.microsecond // 1000:03d}"
        level_str = level.upper()
        normalized = normalize_meta(meta)
        meta_str = json.dumps(normalized) if normalized else "{}"
        print(f"{timestamp} [{level_str}] [{tag}] {message} | {meta_str}", flush=True)
