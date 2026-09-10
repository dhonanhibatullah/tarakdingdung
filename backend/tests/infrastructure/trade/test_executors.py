from decimal import Decimal

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.order import Order, OrderSide, OrderStatus
from tarakdingdung.domain.models.symbol import Symbol
from tarakdingdung.infrastructure.trade.execution.live.executor import LiveExecutor
from tarakdingdung.infrastructure.trade.execution.paper.exchange import PaperExchange
from tarakdingdung.infrastructure.trade.execution.paper.executor import PaperExecutor
from tarakdingdung.infrastructure.trade.execution.reconciler import StandardReconciler


class FakeClock:
    def now_ms(self) -> int:
        return 1234


class FakeExchange:
    def __init__(self, fail=False, not_found=False) -> None:
        self.fail = fail
        self.not_found = not_found
        self.placed = []

    async def place_order(self, symbol, side, quantity, price, client_order_id):
        if self.fail:
            raise RuntimeError("transport down")
        self.placed.append(client_order_id)
        return object()

    async def get_order(self, symbol, order_id):
        if self.fail:
            raise RuntimeError("transport down")
        if self.not_found:
            raise DomainError("missing", ErrorType.NOT_FOUND)
        return type("R", (), {"status": "FILLED"})()

    async def account(self):
        raise NotImplementedError

    async def cancel_order(self, symbol, order_id):
        raise NotImplementedError


def _symbols():
    return {"s1": Symbol(id="s1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")}


def _order(client_id="c1"):
    return Order(
        id="o1",
        client_order_id=client_id,
        symbol_id="s1",
        side=OrderSide.BUY,
        price=Decimal("10"),
        quantity=Decimal("1"),
        status=OrderStatus.PLANNED,
        created_at_ms=1000,
    )


async def test_paper_executor_fills_all():
    paper = PaperExchange({"IDR": Decimal("1000")})
    executor = PaperExecutor(paper, FakeClock())
    result = await executor.submit([_order()], _symbols())
    assert result.unconfirmed == []
    assert len(result.fills) == 1
    assert result.fills[0].order_id == "o1"


async def test_paper_executor_updates_balances():
    paper = PaperExchange({"IDR": Decimal("1000")})
    executor = PaperExecutor(paper, FakeClock())
    await executor.submit([_order()], _symbols())
    account = await paper.account()
    assets = {b.asset: b.free for b in account.balances}
    # order buys 1 BTC at 10 IDR
    assert assets["IDR"] == Decimal("990")
    assert assets["BTC"] == Decimal("1")


async def test_live_executor_succeeds():
    exchange = FakeExchange()
    executor = LiveExecutor(exchange)
    result = await executor.submit([_order()], _symbols())
    assert result.unconfirmed == []
    assert exchange.placed == ["c1"]


async def test_live_executor_marks_transport_failure_unconfirmed():
    executor = LiveExecutor(FakeExchange(fail=True))
    result = await executor.submit([_order()], _symbols())
    assert result.unconfirmed == ["c1"]


async def test_reconciler_resolves_filled():
    result = await StandardReconciler(FakeExchange()).reconcile([_order()], _symbols())
    assert result.resolved == [("c1", OrderStatus.FILLED)]


async def test_reconciler_rejects_missing_order():
    result = await StandardReconciler(FakeExchange(not_found=True)).reconcile(
        [_order()], _symbols()
    )
    assert result.resolved == [("c1", OrderStatus.REJECTED)]


async def test_reconciler_keeps_transport_failure_unconfirmed():
    result = await StandardReconciler(FakeExchange(fail=True)).reconcile(
        [_order()], _symbols()
    )
    assert result.still_unconfirmed == ["c1"]
