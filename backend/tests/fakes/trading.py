"""In-memory implementations of the trading contracts.

Hand-written rather than mocked, matching ``tests/fakes/repositories.py``: a
fake that actually stores things can assert ordering — that planned orders were
written *before* submission — which a mock's call log can only approximate.
"""

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal

from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight
from tarakdingdung.domain.models.algorithm import PlannedOrder
from tarakdingdung.domain.models.backtest import BacktestRun, ValidationRun
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import (
    ExecutionResult, OrderAck, OrderState, UnconfirmedOrder,
)
from tarakdingdung.domain.models.market import (
    Candle, Coverage, MarketSnapshot, OrderBook, Symbol, SymbolRules, TimeRange,
)
from tarakdingdung.domain.models.performance import EquityPoint, Fill
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState
from tarakdingdung.domain.models.strategy import StrategyConfig, TradingMode

_NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)
TS = 1_757_000_000_000


def make_strategy(**kw) -> StrategyConfig:
    base = dict(id=uuid.uuid4(), name="momentum", description="", kind="pipeline",
                mode=TradingMode.PAPER, universe=(), parameters={},
                is_enabled=True, preferences={}, created_at=_NOW)
    return StrategyConfig(**{**base, **kw})


def make_portfolio(*, equity: str = "10000", positions=(), timestamp: int = TS) -> Portfolio:
    from tarakdingdung.domain.models.market import Venue
    return Portfolio(timestamp=timestamp,
                     cash={Venue.INDODAX: Decimal(equity)},
                     positions={p.symbol: p for p in positions},
                     equity=Decimal(equity))


def make_risk_state(**kw) -> RiskState:
    base = dict(timestamp=TS, equity_peak=Decimal("10000"), daily_pnl=Decimal("0"),
                realized_volatility=0.01, halted=False)
    return RiskState(**{**base, **kw})


class FakeClock(Clock):
    def __init__(self, now: int = TS) -> None:
        self.now = now

    async def now_ms(self) -> int:
        return self.now


class FakeSingleFlight(SingleFlight):
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.held: set[str] = set()
        self.released: list[str] = []

    async def acquire(self, key: str) -> bool:
        if not self.available or key in self.held:
            return False
        self.held.add(key)
        return True

    async def release(self, key: str) -> None:
        self.held.discard(key)
        self.released.append(key)


class FakeMarketDataRepository(MarketDataRepository):
    def __init__(self) -> None:
        self.candles: dict[tuple[Symbol, str], list[Candle]] = {}
        self.books: dict[Symbol, OrderBook] = {}
        self.prices: dict[Symbol, tuple[int, Decimal]] = {}
        self.rules: dict[Symbol, SymbolRules] = {}
        self.snapshot: MarketSnapshot | None = None
        self.coverage: Coverage | None = None

    async def write_candles(self, *, symbol, interval, candles) -> int:
        self.candles.setdefault((symbol, interval), []).extend(candles)
        return len(candles)

    async def write_book(self, book) -> None:
        self.books[book.symbol] = book

    async def write_price(self, *, symbol, timestamp, price) -> None:
        self.prices[symbol] = (timestamp, price)

    async def read_candles(self, *, symbol, interval, window, limit=None):
        stored = self.candles.get((symbol, interval), [])
        found = [c for c in stored if window.start <= c.open_time < window.end]
        return tuple(found[-limit:] if limit else found)

    async def read_book(self, *, symbol, as_of):
        return self.books.get(symbol)

    async def read_prices(self, *, symbols, as_of, max_age) -> Mapping[Symbol, Decimal]:
        return {s: price for s in symbols
                if (entry := self.prices.get(s)) is not None
                and (stamp := entry[0]) <= as_of and as_of - stamp <= max_age
                and (price := entry[1]) is not None}

    async def read_snapshot(self, *, symbols, as_of, interval, lookback, max_age):
        if self.snapshot is not None:
            return self.snapshot
        return MarketSnapshot(timestamp=as_of, candles={}, books={}, last_prices={})

    async def read_coverage(self, *, symbol, interval, window) -> Coverage:
        if self.coverage is not None:
            return self.coverage
        return Coverage(symbol=symbol, interval=interval, window=window,
                        expected=1, present=1, gaps=())

    async def write_rules(self, rules) -> None:
        self.rules.update(rules)

    async def read_rules(self, *, symbols) -> Mapping[Symbol, SymbolRules]:
        return {s: self.rules[s] for s in symbols if s in self.rules}


class FakeStrategyRepository(StrategyRepository):
    def __init__(self, strategies=()) -> None:
        self.items: dict[uuid.UUID, StrategyConfig] = {s.id: s for s in strategies}

    async def create(self, *, name, description, kind, mode, universe,
                     parameters, is_enabled, created_by) -> uuid.UUID:
        config = make_strategy(name=name, description=description or "", kind=kind,
                               mode=mode, universe=universe, parameters=parameters or {},
                               is_enabled=True if is_enabled is None else is_enabled,
                               created_by=created_by)
        self.items[config.id] = config
        return config.id

    async def read_by_id(self, id):
        return self.items.get(id)

    async def read_by_name(self, name):
        return next((s for s in self.items.values() if s.name == name), None)

    async def read_enabled(self):
        return [s for s in self.items.values() if s.is_enabled]

    async def read_by_pagination(self, *, page, limit, search, mode):
        found = [s for s in self.items.values()
                 if (search is None or search in s.name)
                 and (mode is None or s.mode is mode)]
        start = (page - 1) * limit
        return found[start:start + limit], len(found)

    async def update_by_id(self, id, **kw) -> None:
        from dataclasses import replace
        current = self.items.get(id)
        if current is None:
            raise DomainError("strategy not found", ErrorType.NOT_FOUND)
        changes = {k: v for k, v in kw.items() if v is not None and k != "updated_by"}
        self.items[id] = replace(current, **changes)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        if self.items.pop(id, None) is None:
            raise DomainError("strategy not found", ErrorType.NOT_FOUND)


class FakePortfolioRepository(PortfolioRepository):
    def __init__(self, *, portfolio=None, risk_state=None) -> None:
        self.portfolio = portfolio
        self.state = risk_state or make_risk_state()
        self.snapshots: list[Portfolio] = []
        self.equity: list[EquityPoint] = []
        self.fills: list[Fill] = []
        self.halts: dict[uuid.UUID, tuple[bool, str | None]] = {}

    async def write_snapshot(self, portfolio) -> None:
        self.portfolio = portfolio
        self.snapshots.append(portfolio)

    async def read_latest(self, *, as_of):
        return self.portfolio

    async def read_risk_state(self, *, as_of) -> RiskState:
        return self.state

    async def write_equity_point(self, point) -> None:
        self.equity.append(point)

    async def read_equity_curve(self, *, window):
        return tuple(p for p in self.equity if window.start <= p.timestamp < window.end)

    async def append_fills(self, fills) -> None:
        self.fills.extend(fills)

    async def read_fills(self, *, window):
        return tuple(f for f in self.fills if window.start <= f.timestamp < window.end)

    async def set_halt(self, *, strategy_id, halted, reason) -> None:
        self.halts[strategy_id] = (halted, reason)

    async def read_halt(self, *, strategy_id):
        return self.halts.get(strategy_id, (False, None))


class FakeOrderJournalRepository(OrderJournalRepository):
    def __init__(self) -> None:
        self.planned: list[tuple[int, PlannedOrder]] = []
        self.executions: list[ExecutionResult] = []
        self.states: dict[str, OrderState] = {}
        self.unreconciled: list[PlannedOrder] = []
        self.events: list[str] = []

    async def write_planned(self, *, strategy_id, timestamp, orders) -> None:
        self.events.append("write_planned")
        self.planned.extend((timestamp, o) for o in orders)

    async def write_execution(self, *, strategy_id, timestamp, result) -> None:
        self.events.append("write_execution")
        self.executions.append(result)

    async def read_unreconciled(self, *, strategy_id):
        return tuple(self.unreconciled)

    async def set_state(self, *, client_order_id, state, venue_order_id, reason) -> None:
        self.states[client_order_id] = state


class FakeBacktestRepository(BacktestRepository):
    def __init__(self) -> None:
        self.runs: dict[uuid.UUID, BacktestRun] = {}
        self.validations: dict[uuid.UUID, ValidationRun] = {}

    async def create_run(self, *, strategy_id, window, initial_equity, report,
                         created_by) -> uuid.UUID:
        run = BacktestRun(id=uuid.uuid4(), strategy_id=strategy_id, window=window,
                          initial_equity=initial_equity, report=report,
                          created_at=_NOW, created_by=created_by)
        self.runs[run.id] = run
        return run.id

    async def read_run_by_id(self, id):
        return self.runs.get(id)

    async def read_runs_by_pagination(self, *, page, limit, strategy_id):
        found = [r for r in self.runs.values()
                 if strategy_id is None or r.strategy_id == strategy_id]
        start = (page - 1) * limit
        return found[start:start + limit], len(found)

    async def create_validation(self, *, strategy_id, window, trials, overfitting,
                                created_by) -> uuid.UUID:
        run = ValidationRun(id=uuid.uuid4(), strategy_id=strategy_id, window=window,
                            trials=trials, overfitting=overfitting,
                            created_at=_NOW, created_by=created_by)
        self.validations[run.id] = run
        return run.id

    async def read_validation_by_id(self, id):
        return self.validations.get(id)

    async def read_validations_by_pagination(self, *, page, limit, strategy_id):
        found = [v for v in self.validations.values()
                 if strategy_id is None or v.strategy_id == strategy_id]
        start = (page - 1) * limit
        return found[start:start + limit], len(found)


class FakeExecutor(Executor):
    """Records submissions, and can be told to fail.

    ``fail_submit`` simulates a transport failure — the outcome is genuinely
    unknown, so it reports the orders unconfirmed rather than rejected, which
    is the case the engine must handle without retrying.
    """

    def __init__(self, *, fail_submit: bool = False, fail_cancel: bool = False,
                 journal: FakeOrderJournalRepository | None = None) -> None:
        self.fail_submit = fail_submit
        self.fail_cancel = fail_cancel
        self.submitted: list[PlannedOrder] = []
        self.cancelled: list[tuple[Symbol, ...]] = []
        self.known: dict[str, ExecutionResult] = {}
        self._journal = journal

    async def submit(self, orders) -> ExecutionResult:
        if self._journal is not None:
            self._journal.events.append("submit")
        self.submitted.extend(orders)
        if self.fail_submit:
            return ExecutionResult(
                accepted=(), rejected=(),
                unconfirmed=tuple(
                    UnconfirmedOrder(order=o, client_order_id=o.client_order_id or "",
                                     reason="timeout") for o in orders),
                fills=())
        return ExecutionResult(
            accepted=tuple(
                OrderAck(order=o, client_order_id=o.client_order_id or "",
                         venue_order_id=f"venue-{i}") for i, o in enumerate(orders)),
            rejected=(), unconfirmed=(), fills=())

    async def cancel_all(self, symbols) -> None:
        if self.fail_cancel:
            raise DomainError("cancel failed", ErrorType.UPSTREAM)
        self.cancelled.append(tuple(symbols))

    async def read_by_client_order_id(self, client_order_id) -> ExecutionResult:
        if self._journal is not None:
            self._journal.events.append("reconcile")
        return self.known.get(
            client_order_id,
            ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=()))
