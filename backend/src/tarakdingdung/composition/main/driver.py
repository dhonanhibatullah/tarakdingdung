from dataclasses import dataclass

from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.logger import LoggerLevel
from tarakdingdung.infrastructure.logger.leveled.json import JsonLeveledLogging
from tarakdingdung.infrastructure.logger.leveled.plain import BasicLeveledLogging
from tarakdingdung.infrastructure.repository.database.session import Database


@dataclass(frozen=True, slots=True)
class Driver:
    database: Database
    logger: LeveledLogger


def build_driver(settings: Settings) -> Driver:
    database = Database(settings.postgres_dsn, pool_size=settings.postgres_pool_size)
    try:
        level = LoggerLevel(settings.logger_level.upper())
    except ValueError:
        level = LoggerLevel.INFO
    logger: LeveledLogger = (
        JsonLeveledLogging(level) if settings.logger_format == "json"
        else BasicLeveledLogging(level)
    )
    return Driver(database=database, logger=logger)
