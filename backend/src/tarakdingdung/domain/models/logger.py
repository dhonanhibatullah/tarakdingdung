from enum import StrEnum


class LoggerFormat(StrEnum):
    PLAIN = "plain"
    JSON = "json"


class LoggerLevel(StrEnum):
    NONE = "NONE"
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"

    @property
    def order(self) -> int:
        log_level_str = {
            LoggerLevel.NONE: 0,
            LoggerLevel.ERROR: 1,
            LoggerLevel.WARN: 2,
            LoggerLevel.INFO: 3,
            LoggerLevel.DEBUG: 4
        }
        return log_level_str[self]
