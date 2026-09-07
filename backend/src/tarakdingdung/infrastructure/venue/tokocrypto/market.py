from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.api.market_source import MarketDataSource
from tarakdingdung.domain.contracts.api.tokocrypto.v3.market import TokocryptoV3MarketApi
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.market import (
    BookLevel, Candle, OrderBook, Symbol, SymbolRules, Venue,
)
from tarakdingdung.infrastructure.venue.shared import to_decimal
from tarakdingdung.infrastructure.venue.symbols import joined_upper

_VENUE = "tokocrypto"

# Binance-standard fee schedule; `/api/v3` exposes no per-account tier, so this
# stays configuration rather than discovery.
_MAKER_FEE = Decimal("0.0010")
_TAKER_FEE = Decimal("0.0010")


class TokocryptoMarketDataSource(MarketDataSource):
    """Tokocrypto market data via the Binance-standard `/api/v3` API."""

    def __init__(self, *, market: TokocryptoV3MarketApi, clock: Clock) -> None:
        self._market = market
        self._clock = clock

    async def fetch_candles(self, *, symbol: Symbol, interval: str,
                            limit: int) -> tuple[Candle, ...]:
        rows = await self._market.klines(symbol=joined_upper(symbol),
                                         interval=interval, limit=limit)
        return tuple(_candle(row) for row in rows)

    async def fetch_book(self, *, symbol: Symbol, limit: int) -> OrderBook:
        payload = await self._market.depth(symbol=joined_upper(symbol), limit=limit)
        body = payload if isinstance(payload, dict) else {}
        return OrderBook(symbol=symbol, timestamp=await self._clock.now_ms(),
                         bids=_levels(body.get("bids")),
                         asks=_levels(body.get("asks")))

    async def fetch_price(self, *, symbol: Symbol) -> Decimal:
        payload = await self._market.ticker_price(symbol=joined_upper(symbol))
        body = payload if isinstance(payload, dict) else {}
        return to_decimal(body.get("price"), f"ticker for {symbol.base}", venue=_VENUE)

    async def fetch_rules(self) -> Mapping[Symbol, SymbolRules]:
        payload = await self._market.exchange_info()
        body = payload if isinstance(payload, dict) else {}
        rules: dict[Symbol, SymbolRules] = {}
        for entry in body.get("symbols") or []:
            symbol = _symbol(entry)
            if symbol is None:
                continue
            filters = entry.get("filters")
            rules[symbol] = SymbolRules(
                symbol=symbol,
                tick_size=_filter(filters, "PRICE_FILTER", "tickSize"),
                step_size=_filter(filters, "LOT_SIZE", "stepSize"),
                min_notional=_min_notional(filters),
                maker_fee=_MAKER_FEE, taker_fee=_TAKER_FEE)
        return rules


def _symbol(entry: dict) -> Symbol | None:
    base, quote = entry.get("baseAsset"), entry.get("quoteAsset")
    if not base or not quote:
        return None
    return Symbol(venue=Venue.TOKOCRYPTO, base=base.upper(), quote=quote.upper())


def _filter(filters, filter_type: str, field: str) -> Decimal:
    for entry in filters or []:
        if entry.get("filterType") == filter_type:
            return to_decimal(entry.get(field), field, venue=_VENUE, default=Decimal(0))
    return Decimal(0)


def _min_notional(filters) -> Decimal:
    # Binance renamed MIN_NOTIONAL to NOTIONAL; the field name stayed
    # `minNotional`. Accept either so an older symbol table still parses.
    for filter_type in ("NOTIONAL", "MIN_NOTIONAL"):
        value = _filter(filters, filter_type, "minNotional")
        if value != 0:
            return value
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
