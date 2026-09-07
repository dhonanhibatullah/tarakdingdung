from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from tarakdingdung.domain.models.market import Symbol


class TradingMode(StrEnum):
    """Whether a strategy's orders reach an exchange.

    Carried on the config rather than passed per request so that a caller
    cannot accidentally route a paper strategy's orders to a real venue.
    """

    PAPER = "PAPER"
    LIVE = "LIVE"


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    """A stored, auditable description of what the engine should run.

    ``kind`` names the pipeline to build and ``parameters`` configures it, so
    changing what runs is a database change rather than a redeploy. Without
    this, what the engine trades would live in a config file that nothing
    records and no cycle can look up.
    """

    id: UUID
    name: str
    description: str
    kind: str
    mode: TradingMode
    universe: tuple[Symbol, ...]
    parameters: dict
    is_enabled: bool
    preferences: dict
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_by: UUID | None = None
