from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    id: str
    venue: str
    as_of_ms: int
    equity: Decimal


@dataclass(frozen=True, slots=True)
class Balance:
    snapshot_id: str
    asset: str
    free: Decimal
    locked: Decimal
