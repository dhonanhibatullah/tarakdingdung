from uuid import UUID

from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.strategy import StrategyConfig
from tarakdingdung.domain.usecases.trading.strategy import (
    CreateStrategyRequest, ListStrategiesRequest, ListStrategiesResult,
    StrategyManagement, UpdateStrategyRequest,
)


class StrategyManagementUsecase(StrategyManagement):
    _TAG = "trading/strategy"

    def __init__(self, *, strategies: StrategyRepository,
                 logger: LeveledLogger) -> None:
        self._strategies = strategies
        self._logger = logger

    async def create(self, request: CreateStrategyRequest) -> UUID:
        if not request.universe:
            err = DomainError("strategy universe must not be empty", ErrorType.VALIDATION)
            await self._logger.error(f"{self._TAG}/Create", "failed to create strategy",
                                     {"err": err, "name": request.name})
            raise err
        try:
            return await self._strategies.create(
                name=request.name, description=request.description, kind=request.kind,
                mode=request.mode, universe=request.universe,
                parameters=request.parameters, is_enabled=request.is_enabled,
                created_by=request.created_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/Create", "failed to create strategy",
                                     {"err": err, "name": request.name})
            raise

    async def read_by_id(self, id: UUID) -> StrategyConfig:
        config = await self._strategies.read_by_id(id)
        if config is None:
            err = DomainError("strategy not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/ReadById", "failed to read strategy",
                                     {"err": err, "strategy_id": id})
            raise err
        return config

    async def read_by_pagination(self, request: ListStrategiesRequest) -> ListStrategiesResult:
        strategies, total = await self._strategies.read_by_pagination(
            page=request.page, limit=request.limit, search=request.search,
            mode=request.mode)
        return ListStrategiesResult(strategies=tuple(strategies), total=total)

    async def update_by_id(self, request: UpdateStrategyRequest) -> None:
        if request.universe is not None and not request.universe:
            err = DomainError("strategy universe must not be empty", ErrorType.VALIDATION)
            await self._logger.error(f"{self._TAG}/UpdateById", "failed to update strategy",
                                     {"err": err, "strategy_id": request.id})
            raise err
        try:
            await self._strategies.update_by_id(
                request.id, name=request.name, description=request.description,
                kind=request.kind, mode=request.mode, universe=request.universe,
                parameters=request.parameters, is_enabled=request.is_enabled,
                preferences=request.preferences, updated_by=request.updated_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/UpdateById", "failed to update strategy",
                                     {"err": err, "strategy_id": request.id})
            raise

    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None:
        try:
            await self._strategies.delete_by_id(id, deleted_by=deleted_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/DeleteById", "failed to delete strategy",
                                     {"err": err, "strategy_id": id})
            raise
