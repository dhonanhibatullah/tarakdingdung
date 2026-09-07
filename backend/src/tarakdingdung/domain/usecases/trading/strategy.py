from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.strategy import StrategyConfig, TradingMode


@dataclass(frozen=True, slots=True)
class CreateStrategyRequest:
    name: str
    description: str | None
    kind: str
    mode: TradingMode
    universe: tuple[Symbol, ...]
    parameters: dict | None = None
    is_enabled: bool | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateStrategyRequest:
    id: UUID
    name: str | None = None
    description: str | None = None
    kind: str | None = None
    mode: TradingMode | None = None
    universe: tuple[Symbol, ...] | None = None
    parameters: dict | None = None
    is_enabled: bool | None = None
    preferences: dict | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ListStrategiesRequest:
    page: int
    limit: int
    search: str | None = None
    mode: TradingMode | None = None


@dataclass(frozen=True, slots=True)
class ListStrategiesResult:
    strategies: tuple[StrategyConfig, ...]
    total: int


class StrategyManagement(ABC):
    """CRUD over what the engine is allowed to run.

    Exists so that what trades is stored, audited and changeable without a
    redeploy. Without it the answer to "what is the bot running" lives in a
    config file that nothing records, and a cycle has nothing to look up.
    """

    @abstractmethod
    async def create(self, request: CreateStrategyRequest) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> StrategyConfig: ...

    @abstractmethod
    async def read_by_pagination(self, request: ListStrategiesRequest) -> ListStrategiesResult: ...

    @abstractmethod
    async def update_by_id(self, request: UpdateStrategyRequest) -> None: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None: ...
