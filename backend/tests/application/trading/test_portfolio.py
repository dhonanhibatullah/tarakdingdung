from decimal import Decimal

import pytest

from tarakdingdung.application.trading.portfolio.usecase import PortfolioSyncUsecase
from tarakdingdung.domain.contracts.api.account_source import AccountSource
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import TimeRange, Venue
from tarakdingdung.domain.models.portfolio import Position
from tarakdingdung.domain.usecases.trading.portfolio import EquityCurveRequest, SyncRequest
from tests.application.trading.conftest import BTC
from tests.fakes.trading import (
    TS, FakeClock, FakeMarketDataRepository, FakePortfolioRepository,
    FakeStrategyRepository, make_portfolio, make_strategy,
)
from tests.fakes.utilities import NullLogger


class StubAccount(AccountSource):
    def __init__(self, balances=None, *, fail: bool = False) -> None:
        self.balances = balances or {}
        self.fail = fail

    async def fetch_balances(self):
        if self.fail:
            raise DomainError("venue down", ErrorType.UPSTREAM)
        return self.balances


async def build(*, balances=None, stored=None, fail=False):
    market_data = FakeMarketDataRepository()
    await market_data.write_price(symbol=BTC, timestamp=TS, price=Decimal("100"))
    portfolios = FakePortfolioRepository(portfolio=stored)
    usecase = PortfolioSyncUsecase(
        accounts={Venue.INDODAX: StubAccount(balances, fail=fail)},
        portfolios=portfolios, market_data=market_data,
        strategies=FakeStrategyRepository((make_strategy(universe=(BTC,)),)),
        clock=FakeClock(), logger=NullLogger())
    return usecase, portfolios


async def test_builds_a_portfolio_from_venue_balances():
    usecase, _ = await build(balances={"BTC": Decimal("2"), "IDR": Decimal("500")})
    result = await usecase.sync(SyncRequest())
    assert result.portfolio.positions[BTC].quantity == Decimal("2")
    # 2 BTC at 100 plus 500 cash.
    assert result.portfolio.equity == Decimal("700")


async def test_reports_a_discrepancy_against_what_we_recorded():
    # Venue balances are the truth; our record being wrong is the finding.
    stored = make_portfolio(positions=[Position(symbol=BTC, quantity=Decimal("5"),
                                                average_price=Decimal("100"))])
    usecase, _ = await build(balances={"BTC": Decimal("2")}, stored=stored)
    result = await usecase.sync(SyncRequest())
    assert len(result.discrepancies) == 1
    assert result.discrepancies[0].expected == Decimal("5")
    assert result.discrepancies[0].actual == Decimal("2")
    assert result.discrepancies[0].difference == Decimal("-3")


async def test_discrepancies_are_returned_not_raised():
    stored = make_portfolio(positions=[Position(symbol=BTC, quantity=Decimal("5"),
                                                average_price=Decimal("100"))])
    usecase, portfolios = await build(balances={}, stored=stored)
    result = await usecase.sync(SyncRequest())
    assert result.discrepancies
    # The snapshot is still written: a caller must be able to see the state
    # that produced the finding.
    assert portfolios.snapshots


async def test_an_unreachable_venue_is_distinct_from_an_empty_one():
    # Not knowing a balance is not the same as knowing it is zero.
    usecase, _ = await build(fail=True)
    result = await usecase.sync(SyncRequest())
    assert result.unreachable == (Venue.INDODAX,)
    assert result.portfolio.positions == {}


async def test_sync_records_an_equity_point():
    usecase, portfolios = await build(balances={"IDR": Decimal("1000")})
    await usecase.sync(SyncRequest())
    assert [p.equity for p in portfolios.equity] == [Decimal("1000")]


async def test_read_current_returns_portfolio_and_risk_state():
    usecase, _ = await build(balances={"IDR": Decimal("1000")},
                             stored=make_portfolio())
    result = await usecase.read_current()
    assert result.portfolio is not None
    assert result.risk_state.halted is False


async def test_read_current_raises_when_nothing_is_recorded():
    usecase, _ = await build()
    with pytest.raises(DomainError) as e:
        await usecase.read_current()
    assert e.value.type is ErrorType.NOT_FOUND


async def test_reads_the_equity_curve_within_a_window():
    usecase, portfolios = await build(balances={"IDR": Decimal("1000")})
    await usecase.sync(SyncRequest())
    result = await usecase.read_equity_curve(
        EquityCurveRequest(window=TimeRange(start=TS - 1, end=TS + 1)))
    assert len(result.points) == 1
