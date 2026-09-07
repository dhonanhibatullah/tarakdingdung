from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.strategy import StrategyConfig, TradingMode


class StrategyRepository(ABC):
    """Stored strategy configurations.

    ``read_enabled`` exists for the cron: a cycle task asks what it should be
    running rather than being told at deploy time, so enabling a strategy is a
    database change that takes effect on the next tick.
    """

    @abstractmethod
    async def create(self, *, name: str, description: str | None, kind: str,
                     mode: TradingMode, universe: tuple[Symbol, ...],
                     parameters: dict | None, is_enabled: bool | None,
                     created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> StrategyConfig | None: ...

    @abstractmethod
    async def read_by_name(self, name: str) -> StrategyConfig | None: ...

    @abstractmethod
    async def read_enabled(self) -> list[StrategyConfig]: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int,
                                 search: str | None,
                                 mode: TradingMode | None) -> tuple[list[StrategyConfig], int]: ...

    @abstractmethod
    async def update_by_id(self, id: UUID, *, name: str | None = None,
                           description: str | None = None, kind: str | None = None,
                           mode: TradingMode | None = None,
                           universe: tuple[Symbol, ...] | None = None,
                           parameters: dict | None = None,
                           is_enabled: bool | None = None,
                           preferences: dict | None = None,
                           updated_by: UUID | None = None) -> None: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None: ...
