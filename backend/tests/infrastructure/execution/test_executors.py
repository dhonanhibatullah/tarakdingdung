from decimal import Decimal

import pytest

from tarakdingdung.domain.models.algorithm import (
    OrderType, PlannedOrder, Side, TimeInForce,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import ExecutionResult
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.infrastructure.algorithm.cost.depth_walk import DepthWalkCostModel
from tarakdingdung.infrastructure.execution.live.classify import is_settled
from tarakdingdung.infrastructure.execution.live.indodax import IndodaxLiveExecutor
from tarakdingdung.infrastructure.execution.live.router import RoutingExecutor
from tarakdingdung.infrastructure.execution.paper.executor import PaperExecutor
from tests.fakes.trading import FakeClock, FakeExecutor, FakeMarketDataRepository
from tests.fakes.utilities import NullLogger

IDX = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")
TKO = Symbol(venue=Venue.TOKOCRYPTO, base="BTC", quote="USDT")


def order(symbol=IDX, *, quantity="1", client_order_id="tdd1") -> PlannedOrder:
    return PlannedOrder(symbol=symbol, side=Side.BUY, type=OrderType.LIMIT,
                        quantity=Decimal(quantity), price=Decimal("100"),
                        time_in_force=TimeInForce.GTC,
                        client_order_id=client_order_id)


# --- classification ---------------------------------------------------------

@pytest.mark.parametrize("error_type", [
    ErrorType.BAD_ARGS, ErrorType.VALIDATION, ErrorType.UNAUTHORIZED,
])
def test_a_venue_verdict_is_settled(error_type):
    assert is_settled(error_type) is True


@pytest.mark.parametrize("error_type", [
    ErrorType.TIMEOUT, ErrorType.UPSTREAM, ErrorType.RATE_LIMITED, ErrorType.UNKNOWN,
])
def test_an_unknown_outcome_is_not_settled(error_type):
    # Treating a timeout as a rejection would let the engine forget an order
    # that may be working at the venue.
    assert is_settled(error_type) is False


# --- paper ------------------------------------------------------------------

async def paper() -> tuple[PaperExecutor, FakeMarketDataRepository]:
    from tests.application.trading.conftest import book
    market = FakeMarketDataRepository()
    await market.write_book(book(IDX, size="1000"))
    return PaperExecutor(market_data=market,
                         cost_model=DepthWalkCostModel(fee_rate=Decimal("0.001")),
                         clock=FakeClock()), market


async def test_paper_fills_and_charges_a_fee():
    executor, _ = await paper()
    result = await executor.submit((order(),))
    assert len(result.accepted) == 1
    assert result.fills[0].fee > 0
    assert result.is_complete


async def test_paper_rejects_what_the_book_cannot_absorb():
    # Filling at an invented price is how a backtest reports an edge that
    # execution then eats.
    executor, _ = await paper()
    result = await executor.submit((order(quantity="100000"),))
    assert result.accepted == ()
    assert "depth" in result.rejected[0].reason


async def test_paper_rejects_when_there_is_no_book():
    executor = PaperExecutor(market_data=FakeMarketDataRepository(),
                             cost_model=DepthWalkCostModel(fee_rate=Decimal("0")),
                             clock=FakeClock())
    result = await executor.submit((order(),))
    assert len(result.rejected) == 1


async def test_paper_never_reports_unconfirmed_orders():
    # Nothing can fail in transport here, which is the one place paper
    # legitimately differs from live.
    executor, _ = await paper()
    result = await executor.submit((order(), order(client_order_id="tdd2")))
    assert result.unconfirmed == ()


async def test_paper_cancel_is_safe_when_nothing_rests():
    executor, _ = await paper()
    await executor.cancel_all((IDX,))


# --- indodax live -----------------------------------------------------------

class StubIndodaxTrade:
    def __init__(self, *, error: DomainError | None = None, resting=()) -> None:
        self.error = error
        self.resting = list(resting)
        self.created: list[dict] = []
        self.cancelled: list[dict] = []

    async def create_order(self, **kw):
        if self.error is not None:
            raise self.error
        self.created.append(kw)
        return {"order_id": 42}

    async def open_orders(self, *, symbol=None):
        return self.resting

    async def cancel_order(self, **kw):
        self.cancelled.append(kw)
        return {}


def live(**kw) -> tuple[IndodaxLiveExecutor, StubIndodaxTrade]:
    stub = StubIndodaxTrade(**kw)
    return IndodaxLiveExecutor(trade=stub, logger=NullLogger()), stub


async def test_live_accepts_and_records_the_venue_id():
    executor, stub = live()
    result = await executor.submit((order(),))
    assert result.accepted[0].venue_order_id == "42"
    assert stub.created[0]["new_client_order_id"] == "tdd1"
    assert stub.created[0]["symbol"] == "BTC_IDR"


async def test_a_venue_verdict_becomes_a_rejection():
    executor, _ = live(error=DomainError("bad price", ErrorType.BAD_ARGS))
    result = await executor.submit((order(),))
    assert len(result.rejected) == 1
    assert result.unconfirmed == ()
    assert result.is_complete


async def test_a_timeout_becomes_unconfirmed_not_rejected():
    # The order may exist at the venue; only reconciliation can settle it.
    executor, _ = live(error=DomainError("timed out", ErrorType.TIMEOUT))
    result = await executor.submit((order(),))
    assert result.rejected == ()
    assert len(result.unconfirmed) == 1
    assert result.is_complete is False


async def test_cancel_all_pulls_every_resting_order():
    executor, stub = live(resting=[{"order_id": 1, "client_order_id": "a"},
                                   {"order_id": 2, "client_order_id": "b"}])
    await executor.cancel_all((IDX,))
    assert len(stub.cancelled) == 2


async def test_indodax_lookup_is_refused_rather_than_guessed():
    # The venue needs a symbol to look an order up, which this signature does
    # not carry; guessing one would query the wrong market.
    executor, _ = live()
    with pytest.raises(DomainError) as e:
        await executor.read_by_client_order_id("tdd1")
    assert e.value.type is ErrorType.UNIMPLEMENTED
    with pytest.raises(DomainError):
        await executor.read_by_client_order_id("tdd1", symbol=IDX)


# --- routing ----------------------------------------------------------------

async def test_orders_reach_the_executor_for_their_venue():
    indodax, tokocrypto = FakeExecutor(), FakeExecutor()
    router = RoutingExecutor({Venue.INDODAX: indodax, Venue.TOKOCRYPTO: tokocrypto})
    await router.submit((order(IDX), order(TKO, client_order_id="tdd2")))
    assert [o.symbol for o in indodax.submitted] == [IDX]
    assert [o.symbol for o in tokocrypto.submitted] == [TKO]


async def test_a_venue_without_an_executor_is_unconfirmed_not_rejected():
    # It is a misconfiguration, not a venue verdict; marking it settled would
    # let the engine forget an order it never resolved.
    router = RoutingExecutor({Venue.INDODAX: FakeExecutor()})
    result = await router.submit((order(TKO),))
    assert result.rejected == ()
    assert len(result.unconfirmed) == 1
    assert "no executor" in result.unconfirmed[0].reason


async def test_results_from_every_venue_are_merged():
    router = RoutingExecutor({Venue.INDODAX: FakeExecutor(),
                              Venue.TOKOCRYPTO: FakeExecutor()})
    result = await router.submit((order(IDX), order(TKO, client_order_id="tdd2")))
    assert len(result.accepted) == 2


async def test_cancel_reaches_every_venue_before_surfacing_a_failure():
    # Stopping at the first failure would leave orders working somewhere the
    # halt could have reached.
    failing, working = FakeExecutor(fail_cancel=True), FakeExecutor()
    router = RoutingExecutor({Venue.INDODAX: failing, Venue.TOKOCRYPTO: working})
    with pytest.raises(DomainError):
        await router.cancel_all((IDX, TKO))
    assert working.cancelled == [(TKO,)]
