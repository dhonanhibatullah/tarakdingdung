from decimal import Decimal

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.infrastructure.venue.indodax.account import IndodaxAccountSource
from tarakdingdung.infrastructure.venue.indodax.market import IndodaxMarketDataSource
from tarakdingdung.infrastructure.venue.shared import to_decimal
from tarakdingdung.infrastructure.venue.symbols import (
    joined_lower, joined_upper, underscored,
)
from tarakdingdung.infrastructure.venue.tokocrypto.account import TokocryptoAccountSource
from tarakdingdung.infrastructure.venue.tokocrypto.market import TokocryptoMarketDataSource
from tests.fakes.trading import FakeClock

BTC = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")
TKO = Symbol(venue=Venue.TOKOCRYPTO, base="BTC", quote="USDT")


# --- symbols ----------------------------------------------------------------

def test_each_venue_gets_the_form_it_expects():
    assert joined_lower(BTC) == "btcidr"
    assert joined_upper(BTC) == "BTCIDR"
    assert underscored(BTC) == "BTC_IDR"


# --- decimal parsing --------------------------------------------------------

def test_a_json_number_does_not_arrive_as_a_float():
    # Decimal(float) would carry the binary approximation into a quantity that
    # becomes an exchange order field.
    assert to_decimal(0.1, "price", venue="test") == Decimal("0.1")


def test_a_missing_field_raises_upstream_unless_defaulted():
    with pytest.raises(DomainError) as e:
        to_decimal(None, "price", venue="test")
    assert e.value.type is ErrorType.UPSTREAM
    assert to_decimal(None, "price", venue="test", default=Decimal(0)) == 0


def test_an_unreadable_field_raises_rather_than_returning_zero():
    with pytest.raises(DomainError) as e:
        to_decimal("not a number", "price", venue="test")
    assert e.value.type is ErrorType.UPSTREAM


# --- indodax ----------------------------------------------------------------

class StubIndodaxPublic:
    def __init__(self, **payloads) -> None:
        self.payloads = payloads
        self.calls: dict[str, object] = {}

    async def ohlc(self, *, symbol, tf, from_ts, to_ts):
        self.calls["ohlc"] = (symbol, tf)
        return self.payloads.get("ohlc", [])

    async def depth(self, pair_id="btcidr"):
        self.calls["depth"] = pair_id
        return self.payloads.get("depth", {})

    async def ticker(self, pair_id="btcidr"):
        self.calls["ticker"] = pair_id
        return self.payloads.get("ticker", {})

    async def pairs(self):
        return self.payloads.get("pairs", [])

    async def server_time(self): ...
    async def price_increments(self): ...
    async def summaries(self): ...
    async def ticker_all(self): ...
    async def trades(self, pair_id="btcidr"): ...


def indodax(**payloads) -> tuple[IndodaxMarketDataSource, StubIndodaxPublic]:
    stub = StubIndodaxPublic(**payloads)
    return IndodaxMarketDataSource(public=stub, clock=FakeClock()), stub


async def test_indodax_candles_convert_seconds_to_milliseconds():
    source, _ = indodax(ohlc=[{"Time": 1_757_000_000, "Open": "1", "High": "2",
                               "Low": "0.5", "Close": "1.5", "Volume": "10"}])
    candles = await source.fetch_candles(symbol=BTC, interval="1h", limit=10)
    assert candles[0].open_time == 1_757_000_000_000
    assert candles[0].close == Decimal("1.5")


async def test_indodax_rejects_an_unsupported_interval():
    # Indodax has its own timeframe vocabulary; guessing would silently step a
    # backtest at the wrong cadence.
    source, _ = indodax()
    with pytest.raises(DomainError) as e:
        await source.fetch_candles(symbol=BTC, interval="3m", limit=10)
    assert e.value.type is ErrorType.BAD_ARGS


async def test_indodax_book_maps_buy_and_sell_to_bids_and_asks():
    source, stub = indodax(depth={"buy": [["100", "1"]], "sell": [["101", "2"]]})
    book = await source.fetch_book(symbol=BTC, limit=10)
    assert book.bids[0].price == Decimal("100")
    assert book.asks[0].quantity == Decimal("2")
    assert stub.calls["depth"] == "btcidr"


async def test_indodax_book_respects_the_level_limit():
    source, _ = indodax(depth={"buy": [["100", "1"], ["99", "1"], ["98", "1"]],
                               "sell": []})
    book = await source.fetch_book(symbol=BTC, limit=2)
    assert len(book.bids) == 2


async def test_indodax_price_reads_the_last_trade():
    source, _ = indodax(ticker={"ticker": {"last": "1234.5"}})
    assert await source.fetch_price(symbol=BTC) == Decimal("1234.5")


async def test_indodax_rules_skip_malformed_pairs():
    source, _ = indodax(pairs=[
        {"traded_currency": "btc", "base_currency": "idr", "price_round": "1"},
        {"base_currency": "idr"},
    ])
    rules = await source.fetch_rules()
    assert list(rules) == [BTC]


async def test_indodax_balances_drop_zeroes():
    class StubTrade:
        async def account(self, *, omit_zero_balances=None):
            return {"balances": [{"asset": "btc", "free": "1.5"},
                                 {"asset": "eth", "free": "0"}]}

    balances = await IndodaxAccountSource(trade=StubTrade()).fetch_balances()
    assert balances == {"BTC": Decimal("1.5")}


# --- tokocrypto -------------------------------------------------------------

class StubTokocryptoV3Market:
    def __init__(self, **payloads) -> None:
        self.payloads = payloads
        self.calls: dict[str, object] = {}

    async def klines(self, *, symbol, interval, start_time=None, end_time=None, limit=None):
        self.calls["klines"] = (symbol, interval, limit)
        return self.payloads.get("klines", [])

    async def depth(self, *, symbol, limit=None):
        self.calls["depth"] = symbol
        return self.payloads.get("depth", {})

    async def ticker_price(self, *, symbol):
        self.calls["ticker_price"] = symbol
        return self.payloads.get("ticker_price", {})

    async def exchange_info(self, *, symbol=None, symbols=None):
        return self.payloads.get("exchange_info", {"symbols": []})

    async def server_time(self): ...


def tokocrypto(**payloads):
    stub = StubTokocryptoV3Market(**payloads)
    return TokocryptoMarketDataSource(market=stub, clock=FakeClock()), stub


async def test_tokocrypto_parses_binance_kline_arrays():
    source, stub = tokocrypto(klines=[[1_757_000_000_000, "1", "2", "0.5", "1.5", "10"]])
    candles = await source.fetch_candles(symbol=TKO, interval="1h", limit=1)
    assert candles[0].open_time == 1_757_000_000_000
    assert candles[0].high == Decimal("2")
    assert stub.calls["klines"][0] == "BTCUSDT"


async def test_tokocrypto_book_maps_bids_and_asks():
    source, stub = tokocrypto(depth={"bids": [["100", "1"]], "asks": [["101", "2"]]})
    book = await source.fetch_book(symbol=TKO, limit=10)
    assert book.bids[0].price == Decimal("100")
    assert book.asks[0].quantity == Decimal("2")
    assert stub.calls["depth"] == "BTCUSDT"


async def test_tokocrypto_price_reads_the_ticker():
    source, stub = tokocrypto(ticker_price={"symbol": "BTCUSDT", "price": "9.75"})
    assert await source.fetch_price(symbol=TKO) == Decimal("9.75")
    assert stub.calls["ticker_price"] == "BTCUSDT"


async def test_tokocrypto_price_raises_when_the_ticker_has_no_price():
    source, _ = tokocrypto(ticker_price={"symbol": "BTCUSDT"})
    with pytest.raises(DomainError) as e:
        await source.fetch_price(symbol=TKO)
    assert e.value.type is ErrorType.UPSTREAM


async def test_tokocrypto_rules_read_the_binance_filters():
    source, _ = tokocrypto(exchange_info={"symbols": [{
        "baseAsset": "BTC", "quoteAsset": "USDT",
        "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.0001"},
                    {"filterType": "NOTIONAL", "minNotional": "10"}]}]})
    rules = await source.fetch_rules()
    assert rules[TKO].tick_size == Decimal("0.01")
    assert rules[TKO].step_size == Decimal("0.0001")
    assert rules[TKO].min_notional == Decimal("10")


async def test_tokocrypto_rules_accept_the_legacy_min_notional_filter():
    source, _ = tokocrypto(exchange_info={"symbols": [{
        "baseAsset": "BTC", "quoteAsset": "USDT",
        "filters": [{"filterType": "MIN_NOTIONAL", "minNotional": "5"}]}]})
    rules = await source.fetch_rules()
    assert rules[TKO].min_notional == Decimal("5")


async def test_tokocrypto_rules_survive_a_missing_filter():
    source, _ = tokocrypto(exchange_info={"symbols": [
        {"baseAsset": "BTC", "quoteAsset": "USDT", "filters": []}]})
    rules = await source.fetch_rules()
    assert rules[TKO].tick_size == Decimal(0)


async def test_tokocrypto_balances_drop_zeroes():
    class StubTrade:
        async def account(self):
            return {"balances": [{"asset": "BTC", "free": "2", "locked": "0"},
                                 {"asset": "ETH", "free": "0", "locked": "0"}]}

    balances = await TokocryptoAccountSource(trade=StubTrade()).fetch_balances()
    assert balances == {"BTC": Decimal("2")}
