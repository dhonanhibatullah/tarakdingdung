from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.api.market_source import MarketDataSource
from tarakdingdung.domain.contracts.api.tokocrypto.v1.market import TokocryptoV1MarketApi
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.market import (
    BookLevel, Candle, OrderBook, Symbol, SymbolRules, Venue,
)
from tarakdingdung.infrastructure.venue.shared import to_decimal
from tarakdingdung.infrastructure.venue.symbols import underscored

_VENUE = "tokocrypto"

# Binance-standard fee schedule; Tokocrypto exposes no per-account tier through
# the documented endpoints, so this is configuration rather than discovery.
_MAKER_FEE = Decimal("0.0010")
_TAKER_FEE = Decimal("0.0010")


class TokocryptoMarketDataSource(MarketDataSource):
    """Tokocrypto public market data as domain models."""

    def __init__(self, *, market: TokocryptoV1MarketApi, clock: Clock) -> None:
        self._market = market
        self._clock = clock

    async def fetch_candles(self, *, symbol: Symbol, interval: str,
                            limit: int) -> tuple[Candle, ...]:
        payload = await self._market.klines(symbol=underscored(symbol),
                                            interval=interval, limit=limit)
        return tuple(_candle(row) for row in _rows(payload))

    async def fetch_book(self, *, symbol: Symbol, limit: int) -> OrderBook:
        payload = await self._market.depth(symbol=underscored(symbol), limit=limit)
        body = payload if isinstance(payload, dict) else {}
        return OrderBook(symbol=symbol, timestamp=await self._clock.now_ms(),
                         bids=_levels(body.get("bids")),
                         asks=_levels(body.get("asks")))

    async def fetch_price(self, *, symbol: Symbol) -> Decimal:
        # No dedicated ticker on /open/v1; the most recent kline close is the
        # last traded price and avoids a second host's symbol convention.
        candles = await self.fetch_candles(symbol=symbol, interval="1m", limit=1)
        if not candles:
            from tarakdingdung.domain.models.error import DomainError, ErrorType
            raise DomainError(f"no recent trade for {symbol.base}/{symbol.quote}",
                              ErrorType.UPSTREAM)
        return candles[-1].close

    async def fetch_rules(self) -> Mapping[Symbol, SymbolRules]:
        payload = await self._market.symbols()
        rules = {}
        for entry in _rows(payload):
            symbol = _symbol(entry)
            if symbol is None:
                continue
            rules[symbol] = SymbolRules(
                symbol=symbol,
                tick_size=_step(entry.get("filters"), "PRICE_FILTER", "tickSize"),
                step_size=_step(entry.get("filters"), "LOT_SIZE", "stepSize"),
                min_notional=_step(entry.get("filters"), "MIN_NOTIONAL", "minNotional"),
                maker_fee=_MAKER_FEE, taker_fee=_TAKER_FEE)
        return rules


def _rows(payload) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("list", "symbols", "klines"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _symbol(entry: dict) -> Symbol | None:
    base, quote = entry.get("baseAsset"), entry.get("quoteAsset")
    if not base or not quote:
        return None
    return Symbol(venue=Venue.TOKOCRYPTO, base=base.upper(), quote=quote.upper())


def _step(filters, filter_type: str, field: str) -> Decimal:
    for entry in filters or []:
        if entry.get("filterType") == filter_type:
            return to_decimal(entry.get(field), field, venue=_VENUE,
                              default=Decimal(0))
    return Decimal(0)


def _candle(row) -> Candle:
    # Binance kline arrays: [openTime, open, high, low, close, volume, ...]
    return Candle(open_time=int(row[0]),
                  open=to_decimal(row[1], "open", venue=_VENUE),
                  high=to_decimal(row[2], "high", venue=_VENUE),
                  low=to_decimal(row[3], "low", venue=_VENUE),
                  close=to_decimal(row[4], "close", venue=_VENUE),
                  volume=to_decimal(row[5], "volume", venue=_VENUE))


def _levels(raw) -> tuple[BookLevel, ...]:
    if not raw:
        return ()
    return tuple(BookLevel(price=to_decimal(price, "price", venue=_VENUE),
                           quantity=to_decimal(quantity, "quantity", venue=_VENUE))
                 for price, quantity in raw)
