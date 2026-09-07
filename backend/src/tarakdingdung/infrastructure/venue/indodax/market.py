from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.api.indodax.v1.public import IndodaxV1PublicApi
from tarakdingdung.domain.contracts.api.market_source import MarketDataSource
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import (
    BookLevel, Candle, OrderBook, Symbol, SymbolRules, Venue,
)
from tarakdingdung.infrastructure.venue.shared import to_decimal
from tarakdingdung.infrastructure.venue.symbols import joined_lower, joined_upper

# Indodax OHLC takes its own timeframe vocabulary, not the exchange-standard
# one, so the mapping is explicit rather than a string transformation.
_TIMEFRAMES = {"1m": "1", "5m": "5", "15m": "15", "30m": "30",
               "1h": "60", "4h": "240", "1d": "1D", "1w": "1W"}

_TIMEFRAME_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800,
                      "1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800}

# Indodax charges a flat spot schedule; there are no volume tiers to read back
# from the API, so these are configuration rather than discovery.
_MAKER_FEE = Decimal("0.0000")
_TAKER_FEE = Decimal("0.0030")


class IndodaxMarketDataSource(MarketDataSource):
    """Indodax public market data as domain models."""

    def __init__(self, *, public: IndodaxV1PublicApi, clock: Clock) -> None:
        self._public = public
        self._clock = clock

    async def fetch_candles(self, *, symbol: Symbol, interval: str,
                            limit: int) -> tuple[Candle, ...]:
        timeframe = _TIMEFRAMES.get(interval)
        if timeframe is None:
            raise DomainError(f"indodax has no timeframe for {interval!r}",
                              ErrorType.BAD_ARGS)
        now = await self._clock.now_ms() // 1000
        span = _TIMEFRAME_SECONDS[interval] * limit
        rows = await self._public.ohlc(symbol=joined_upper(symbol), tf=timeframe,
                                       from_ts=now - span, to_ts=now)
        return tuple(_candle(row) for row in rows)

    async def fetch_book(self, *, symbol: Symbol, limit: int) -> OrderBook:
        payload = await self._public.depth(joined_lower(symbol))
        timestamp = await self._clock.now_ms()
        return OrderBook(symbol=symbol, timestamp=timestamp,
                         bids=_levels(payload.get("buy"), limit),
                         asks=_levels(payload.get("sell"), limit))

    async def fetch_price(self, *, symbol: Symbol) -> Decimal:
        payload = await self._public.ticker(joined_lower(symbol))
        ticker = payload.get("ticker") or {}
        return _decimal(ticker.get("last"), f"ticker for {symbol.base}")

    async def fetch_rules(self) -> Mapping[Symbol, SymbolRules]:
        pairs = await self._public.pairs()
        rules = {}
        for entry in pairs:
            symbol = _symbol(entry)
            if symbol is None:
                continue
            rules[symbol] = SymbolRules(
                symbol=symbol,
                tick_size=_decimal(entry.get("price_round"), "price_round",
                                   default=Decimal("0")),
                step_size=_decimal(entry.get("trade_fee"), "step",
                                   default=Decimal("0")),
                min_notional=_decimal(entry.get("trade_min_base_currency"),
                                      "min notional", default=Decimal("0")),
                maker_fee=_MAKER_FEE, taker_fee=_TAKER_FEE)
        return rules


def _symbol(entry: dict) -> Symbol | None:
    base, quote = entry.get("traded_currency"), entry.get("base_currency")
    if not base or not quote:
        return None
    return Symbol(venue=Venue.INDODAX, base=base.upper(), quote=quote.upper())


def _candle(row: dict) -> Candle:
    return Candle(open_time=int(row["Time"]) * 1000,
                  open=_decimal(row.get("Open"), "open"),
                  high=_decimal(row.get("High"), "high"),
                  low=_decimal(row.get("Low"), "low"),
                  close=_decimal(row.get("Close"), "close"),
                  volume=_decimal(row.get("Volume"), "volume"))


def _levels(raw, limit: int) -> tuple[BookLevel, ...]:
    if not raw:
        return ()
    return tuple(BookLevel(price=_decimal(price, "price"),
                           quantity=_decimal(quantity, "quantity"))
                 for price, quantity in raw[:limit])


def _decimal(value, label: str, *, default: Decimal | None = None) -> Decimal:
    return to_decimal(value, label, venue="indodax", default=default)
