from decimal import Decimal

import pytest

from tarakdingdung.application.trading.collection.usecase import MarketDataCollectionUsecase
from tarakdingdung.domain.contracts.api.market_source import MarketDataSource
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.domain.usecases.trading.collection import CollectRequest
from tests.application.trading.conftest import BTC, ETH, book, rules
from tests.fakes.trading import (
    FakeClock, FakeMarketDataRepository, FakeStrategyRepository, make_strategy,
)
from tests.fakes.utilities import NullLogger

TKO = Symbol(venue=Venue.TOKOCRYPTO, base="BTC", quote="USDT")


class StubSource(MarketDataSource):
    def __init__(self, *, fail: bool = False, fail_rules: bool = False) -> None:
        self.fail = fail
        self.fail_rules = fail_rules
        self.books_fetched = 0

    async def fetch_candles(self, *, symbol, interval, limit):
        if self.fail:
            raise DomainError("venue down", ErrorType.UPSTREAM)
        from tarakdingdung.domain.models.market import Candle
        return (Candle(open_time=1, open=Decimal("1"), high=Decimal("1"),
                       low=Decimal("1"), close=Decimal("1"), volume=Decimal("1")),)

    async def fetch_book(self, *, symbol, limit):
        self.books_fetched += 1
        return book(symbol)

    async def fetch_price(self, *, symbol):
        return Decimal("100")

    async def fetch_rules(self):
        if self.fail_rules:
            raise DomainError("rules unavailable", ErrorType.UPSTREAM)
        return {BTC: rules(BTC)}


def build(sources, *, universe=(BTC,)):
    market_data = FakeMarketDataRepository()
    usecase = MarketDataCollectionUsecase(
        sources=sources, market_data=market_data,
        strategies=FakeStrategyRepository((make_strategy(universe=universe),)),
        clock=FakeClock(), logger=NullLogger())
    return usecase, market_data


async def test_collects_candles_prices_books_and_rules():
    usecase, market_data = build({Venue.INDODAX: StubSource()})
    result = await usecase.collect(CollectRequest())
    assert result.collected == (BTC,)
    assert result.candles_written == 1
    assert market_data.books and market_data.rules


async def test_one_failing_venue_does_not_abort_the_pass():
    # A gap is permanent in a way a failed poll is not, so the other venue's
    # data must still land.
    usecase, market_data = build(
        {Venue.INDODAX: StubSource(fail=True), Venue.TOKOCRYPTO: StubSource()},
        universe=(BTC, TKO))
    result = await usecase.collect(CollectRequest())
    assert result.collected == (TKO,)
    assert [f.symbol for f in result.failed] == [BTC]
    assert result.failed[0].reason == "venue down"


async def test_a_symbol_without_a_source_is_reported_not_skipped_silently():
    usecase, _ = build({}, universe=(BTC,))
    result = await usecase.collect(CollectRequest())
    assert result.collected == ()
    assert result.failed[0].reason == "no source configured"


async def test_failing_rules_are_reported_without_a_symbol():
    usecase, _ = build({Venue.INDODAX: StubSource(fail_rules=True)})
    result = await usecase.collect(CollectRequest())
    # The whole venue's rules failed; there is no single symbol to blame.
    assert any(f.symbol is None for f in result.failed)
    assert result.collected == (BTC,)


async def test_books_can_be_skipped():
    source = StubSource()
    usecase, _ = build({Venue.INDODAX: source})
    await usecase.collect(CollectRequest(include_books=False))
    assert source.books_fetched == 0


async def test_an_empty_request_collects_every_enabled_universe():
    usecase, _ = build({Venue.INDODAX: StubSource()}, universe=(BTC, ETH))
    result = await usecase.collect(CollectRequest())
    assert set(result.collected) == {BTC, ETH}


async def test_an_explicit_symbol_list_overrides_the_universe():
    usecase, _ = build({Venue.INDODAX: StubSource()}, universe=(BTC, ETH))
    result = await usecase.collect(CollectRequest(symbols=(ETH,)))
    assert result.collected == (ETH,)
