from decimal import Decimal

import pytest

from tarakdingdung.domain.models.decision import Decision, Weight
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.order import Order, OrderSide, OrderStatus
from tarakdingdung.domain.models.portfolio import Balance, PortfolioSnapshot
from tarakdingdung.domain.models.symbol import (
    MembershipState,
    Symbol,
    Universe,
    UniverseMembership,
)
from tarakdingdung.infrastructure.repository.decision.repository import (
    SqlAlchemyDecisionRepository,
)
from tarakdingdung.infrastructure.repository.market_data.repository import (
    SqlAlchemyMarketDataRepository,
)
from tarakdingdung.infrastructure.repository.order_journal.repository import (
    SqlAlchemyOrderJournalRepository,
)
from tarakdingdung.infrastructure.repository.portfolio.repository import (
    SqlAlchemyPortfolioRepository,
)
from tarakdingdung.infrastructure.repository.symbol.repository import (
    SqlAlchemySymbolRepository,
)
from tarakdingdung.infrastructure.repository.universe.repository import (
    SqlAlchemyUniverseRepository,
)


@pytest.fixture
def symbol_repo(session_factory):
    return SqlAlchemySymbolRepository(session_factory)


@pytest.fixture
def universe_repo(session_factory):
    return SqlAlchemyUniverseRepository(session_factory)


@pytest.fixture
def market_data_repo(session_factory):
    return SqlAlchemyMarketDataRepository(session_factory)


@pytest.fixture
def decision_repo(session_factory):
    return SqlAlchemyDecisionRepository(session_factory)


@pytest.fixture
def portfolio_repo(session_factory):
    return SqlAlchemyPortfolioRepository(session_factory)


@pytest.fixture
def order_repo(session_factory):
    return SqlAlchemyOrderJournalRepository(session_factory)


async def _symbol(symbol_repo):
    return await symbol_repo.create(
        Symbol(id="", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")
    )


async def test_symbol_and_universe_membership(symbol_repo, universe_repo):
    symbol = await _symbol(symbol_repo)
    universe = await universe_repo.create(Universe(id="", name="default"))
    await universe_repo.add_membership(
        UniverseMembership(
            universe_id=universe.id,
            symbol_id=symbol.id,
            state=MembershipState.APPROVED,
            rationale="liquid",
        )
    )
    approved = await universe_repo.read_symbols_by_state(
        universe.id, MembershipState.APPROVED
    )
    assert [s.external for s in approved] == ["BTCIDR"]


async def test_candle_append_dedupes(symbol_repo, market_data_repo):
    symbol = await _symbol(symbol_repo)
    candle = Candle(
        symbol_id=symbol.id,
        open_time_ms=1000,
        open=Decimal("1"),
        high=Decimal("2"),
        low=Decimal("0.5"),
        close=Decimal("1.5"),
        volume=Decimal("10"),
    )
    await market_data_repo.append_candles([candle, candle])
    rows = await market_data_repo.read_range(symbol.id, 0, 2000)
    assert len(rows) == 1
    coverage = await market_data_repo.read_coverage(symbol.id)
    assert coverage == (1000, 1000)


async def test_decision_json_roundtrip(symbol_repo, universe_repo, decision_repo):
    symbol = await _symbol(symbol_repo)
    universe = await universe_repo.create(Universe(id="", name="default"))
    decision = Decision(
        id="",
        universe_id=universe.id,
        as_of_ms=1234,
        weights=[Weight(symbol_id=symbol.id, weight=0.5)],
        reasoning="r",
        confidence=0.9,
        traces={"market": "bullish"},
        prompt="p",
        raw_response="j",
        status="valid",
    )
    created = await decision_repo.create(decision)
    fetched = await decision_repo.read_by_id(created.id)
    assert fetched.weights == [Weight(symbol_id=symbol.id, weight=0.5)]
    assert fetched.traces == {"market": "bullish"}
    latest = await decision_repo.read_latest(universe.id)
    assert latest.id == created.id


async def test_portfolio_snapshot_and_balances(portfolio_repo):
    snapshot = PortfolioSnapshot(
        id="", venue="indodax", as_of_ms=1000, equity=Decimal("1000")
    )
    created = await portfolio_repo.create_snapshot(
        snapshot, [Balance(snapshot_id="", asset="IDR", free=Decimal("1000"), locked=Decimal("0"))]
    )
    latest = await portfolio_repo.read_latest("indodax")
    assert latest.id == created.id
    assert latest.equity == Decimal("1000")
    balances = await portfolio_repo.read_balances(created.id)
    assert balances[0].asset == "IDR"


async def test_order_journal_unreconciled(symbol_repo, order_repo):
    symbol = await _symbol(symbol_repo)
    order = await order_repo.create(
        Order(
            id="",
            client_order_id="abc",
            symbol_id=symbol.id,
            side=OrderSide.BUY,
            price=Decimal("10"),
            quantity=Decimal("1"),
            status=OrderStatus.UNCONFIRMED,
            created_at_ms=1000,
        )
    )
    unreconciled = await order_repo.read_unreconciled()
    assert [o.client_order_id for o in unreconciled] == ["abc"]
    updated = await order_repo.update_status(order.id, OrderStatus.SUBMITTED)
    assert updated.status is OrderStatus.SUBMITTED
