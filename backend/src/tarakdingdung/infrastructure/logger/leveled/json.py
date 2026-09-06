import json
from datetime import datetime
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.logger import LoggerLevel


class JsonLeveledLogging(LeveledLogger):
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
        log_entry = {
            "timestamp": timestamp,
            "level": level.upper(),
            "tag": tag,
            "message": message,
            "meta": meta if meta is not None else {}
        }
        print(json.dumps(log_entry), flush=True)
