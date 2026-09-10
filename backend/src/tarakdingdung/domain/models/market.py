from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Candle:
    symbol_id: str
    open_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
