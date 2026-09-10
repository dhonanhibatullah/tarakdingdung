import uuid

from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.contracts.repository.decision import DecisionRepository
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.news import NewsRepository
from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.symbol import SymbolRepository
from tarakdingdung.domain.contracts.repository.universe import UniverseRepository
from tarakdingdung.domain.models.backtest import BacktestResult
from tarakdingdung.domain.models.decision import Decision
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.news import NewsAnalysis, NewsArticle
from tarakdingdung.domain.models.order import Fill, Order, OrderStatus
from tarakdingdung.domain.models.portfolio import Balance, PortfolioSnapshot
from tarakdingdung.domain.models.symbol import (
    MembershipState,
    Symbol,
    Universe,
    UniverseMembership,
)


class InMemorySymbolRepository(SymbolRepository):
    def __init__(self) -> None:
        self.items: dict[str, Symbol] = {}
        self.created: list[Symbol] = []

    async def create(self, entity: Symbol) -> Symbol:
        stored = Symbol(
            id=entity.id or str(uuid.uuid4()),
            venue=entity.venue,
            base=entity.base,
            quote=entity.quote,
            external=entity.external,
        )
        self.items[stored.id] = stored
        self.created.append(stored)
        return stored

    async def read_by_id(self, id: str) -> Symbol | None:
        return self.items.get(id)

    async def read_by_external(self, venue: str, external: str) -> Symbol | None:
        for s in self.items.values():
            if s.venue == venue and s.external == external:
                return s
        return None

    async def read_by_pagination(self, page: int, per_page: int):
        items = list(self.items.values())
        return items[(page - 1) * per_page : page * per_page], len(items)


class InMemoryUniverseRepository(UniverseRepository):
    def __init__(self, approved_symbols=None, memberships=None) -> None:
        self.approved_symbols = approved_symbols or []
        self.memberships = memberships or []

    async def create(self, entity: Universe) -> Universe:
        return entity

    async def read_by_id(self, id: str) -> Universe | None:
        return None

    async def read_by_name(self, name: str) -> Universe | None:
        return None

    async def read_memberships(self, universe_id: str) -> list[UniverseMembership]:
        return self.memberships

    async def add_membership(self, entity: UniverseMembership) -> UniverseMembership:
        self.memberships.append(entity)
        return entity

    async def update_membership(
        self, universe_id: str, symbol_id: str, state: MembershipState, rationale: str = ""
    ) -> UniverseMembership | None:
        return UniverseMembership(
            universe_id=universe_id, symbol_id=symbol_id, state=state, rationale=rationale
        )

    async def read_symbols_by_state(
        self, universe_id: str, state: MembershipState
    ) -> list[Symbol]:
        return self.approved_symbols


class InMemoryMarketDataRepository(MarketDataRepository):
    def __init__(self) -> None:
        self.candles: list[Candle] = []

    async def append_candles(self, candles: list[Candle]) -> None:
        self.candles.extend(candles)

    async def read_range(self, symbol_id: str, from_ms: int, to_ms: int) -> list[Candle]:
        return [
            c for c in self.candles
            if c.symbol_id == symbol_id and from_ms <= c.open_time_ms <= to_ms
        ]

    async def read_latest(self, symbol_id: str) -> Candle | None:
        matches = [c for c in self.candles if c.symbol_id == symbol_id]
        return max(matches, key=lambda c: c.open_time_ms) if matches else None

    async def read_coverage(self, symbol_id: str) -> tuple[int, int] | None:
        return None


class InMemoryNewsRepository(NewsRepository):
    def __init__(self) -> None:
        self.articles: list[NewsArticle] = []
        self.analyses: list[NewsAnalysis] = []

    async def create(self, entity: NewsArticle) -> NewsArticle:
        self.articles.append(entity)
        return entity

    async def create_analysis(self, entity: NewsAnalysis) -> NewsAnalysis:
        self.analyses.append(entity)
        return entity

    async def read_recent(self, from_ms: int) -> list[NewsArticle]:
        return self.articles

    async def read_analyses(self, from_ms: int) -> list[NewsAnalysis]:
        return self.analyses


class InMemoryDecisionRepository(DecisionRepository):
    def __init__(self, events: list[str] | None = None) -> None:
        self.items: dict[str, Decision] = {}
        self.order: list[str] = []
        self.events = events

    async def create(self, entity: Decision) -> Decision:
        if self.events is not None:
            self.events.append("decision.create")
        id_ = entity.id or str(uuid.uuid4())
        stored = Decision(
            id=id_,
            universe_id=entity.universe_id,
            as_of_ms=entity.as_of_ms,
            weights=entity.weights,
            reasoning=entity.reasoning,
            confidence=entity.confidence,
            traces=entity.traces,
            prompt=entity.prompt,
            raw_response=entity.raw_response,
            status=entity.status,
        )
        self.items[id_] = stored
        self.order.append(id_)
        return stored

    async def read_by_id(self, id: str) -> Decision | None:
        return self.items.get(id)

    async def read_latest(self, universe_id: str) -> Decision | None:
        for id_ in reversed(self.order):
            d = self.items[id_]
            if d.universe_id == universe_id:
                return d
        return None

    async def read_range(
        self, universe_id: str, from_ms: int, to_ms: int
    ) -> list[Decision]:
        return [
            self.items[id_]
            for id_ in self.order
            if self.items[id_].universe_id == universe_id
            and from_ms <= self.items[id_].as_of_ms <= to_ms
        ]


class InMemoryBacktestRepository(BacktestRepository):
    def __init__(self) -> None:
        self.items: dict[str, BacktestResult] = {}
        self.order: list[str] = []

    async def create(self, entity: BacktestResult) -> BacktestResult:
        id_ = entity.id or str(uuid.uuid4())
        stored = BacktestResult(
            id=id_,
            universe_id=entity.universe_id,
            from_ms=entity.from_ms,
            to_ms=entity.to_ms,
            equity_curve=entity.equity_curve,
            sharpe=entity.sharpe,
            max_drawdown=entity.max_drawdown,
            turnover=entity.turnover,
        )
        self.items[id_] = stored
        self.order.append(id_)
        return stored

    async def read_by_id(self, id: str) -> BacktestResult | None:
        return self.items.get(id)

    async def read_by_pagination(self, page: int, per_page: int):
        items = [self.items[i] for i in self.order]
        return items[(page - 1) * per_page : page * per_page], len(items)


class InMemoryPortfolioRepository(PortfolioRepository):
    def __init__(self, snapshot: PortfolioSnapshot | None = None, balances=None) -> None:
        self.snapshot = snapshot
        self.balances = balances or []

    async def create_snapshot(
        self, snapshot: PortfolioSnapshot, balances: list[Balance]
    ) -> PortfolioSnapshot:
        self.snapshot = snapshot
        self.balances = balances
        return snapshot

    async def read_latest(self, venue: str) -> PortfolioSnapshot | None:
        if self.snapshot is None or self.snapshot.venue != venue:
            return None
        return self.snapshot

    async def read_balances(self, snapshot_id: str) -> list[Balance]:
        return self.balances


class InMemoryOrderJournalRepository(OrderJournalRepository):
    def __init__(self, events: list[str] | None = None) -> None:
        self.orders: dict[str, Order] = {}
        self.fills: list[Fill] = []
        self.events = events

    async def create(self, entity: Order) -> Order:
        if self.events is not None:
            self.events.append("order.create")
        stored = Order(
            id=entity.id or str(uuid.uuid4()),
            client_order_id=entity.client_order_id,
            symbol_id=entity.symbol_id,
            side=entity.side,
            price=entity.price,
            quantity=entity.quantity,
            status=entity.status,
            created_at_ms=entity.created_at_ms,
        )
        self.orders[stored.id] = stored
        return stored

    async def read_by_id(self, id: str) -> Order | None:
        return self.orders.get(id)

    async def read_by_client_order_id(self, client_order_id: str) -> Order | None:
        for o in self.orders.values():
            if o.client_order_id == client_order_id:
                return o
        return None

    async def update_status(self, id: str, status: OrderStatus) -> Order | None:
        o = self.orders.get(id)
        if o is None:
            return None
        updated = Order(
            id=o.id,
            client_order_id=o.client_order_id,
            symbol_id=o.symbol_id,
            side=o.side,
            price=o.price,
            quantity=o.quantity,
            status=status,
            created_at_ms=o.created_at_ms,
        )
        self.orders[id] = updated
        return updated

    async def append_fills(self, order_id: str, fills: list[Fill]) -> None:
        self.fills.extend(fills)

    async def read_unreconciled(self) -> list[Order]:
        return [o for o in self.orders.values() if o.status is OrderStatus.UNCONFIRMED]
