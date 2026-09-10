from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.rebalance import Rebalancer
from tarakdingdung.domain.contracts.algorithm.risk import RiskOverlay, RiskState
from tarakdingdung.domain.contracts.llm.pipeline import DecisionContext, DecisionMaker
from tarakdingdung.domain.contracts.repository.decision import DecisionRepository
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.news import NewsRepository
from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.universe import UniverseRepository
from tarakdingdung.domain.contracts.trade.executor import Executor
from tarakdingdung.domain.contracts.trade.reconciler import Reconciler
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight
from tarakdingdung.domain.models.order import Order, OrderStatus
from tarakdingdung.domain.models.symbol import MembershipState
from tarakdingdung.domain.usecases.trading.engine import CycleResult, CycleStatus, TradingEngine
from tarakdingdung.infrastructure.algorithm.rebalance.identifiers import client_order_id


class TradingEngineUsecase(TradingEngine):
    def __init__(
        self,
        *,
        enabled: bool,
        universe_id: str,
        venue: str,
        single_flight: SingleFlight,
        universes: UniverseRepository,
        order_journal: OrderJournalRepository,
        reconciler: Reconciler,
        portfolio: PortfolioRepository,
        market_data: MarketDataRepository,
        news: NewsRepository,
        decision_maker: DecisionMaker,
        decisions: DecisionRepository,
        risk_overlay: RiskOverlay,
        rebalancer: Rebalancer,
        executor: Executor,
        clock: Clock,
    ) -> None:
        self._enabled = enabled
        self._universe_id = universe_id
        self._venue = venue
        self._lock_key = f"engine:{universe_id}"
        self._single_flight = single_flight
        self._universes = universes
        self._order_journal = order_journal
        self._reconciler = reconciler
        self._portfolio = portfolio
        self._market_data = market_data
        self._news = news
        self._decision_maker = decision_maker
        self._decisions = decisions
        self._risk_overlay = risk_overlay
        self._rebalancer = rebalancer
        self._executor = executor
        self._clock = clock

    async def run_cycle(self) -> CycleResult:
        return await self._run(dry_run=False)

    async def dry_run(self) -> CycleResult:
        return await self._run(dry_run=True)

    async def _run(self, dry_run: bool) -> CycleResult:
        if not self._enabled:
            return CycleResult(CycleStatus.DISABLED)

        if not await self._single_flight.acquire(self._lock_key):
            return CycleResult(CycleStatus.SKIPPED)

        try:
            await self._reconcile_unconfirmed()

            snapshot = await self._portfolio.read_latest(self._venue)
            if snapshot is None:
                return CycleResult(CycleStatus.NO_DATA, "no portfolio snapshot")

            approved = await self._universes.read_symbols_by_state(
                self._universe_id, MembershipState.APPROVED
            )
            if not approved:
                return CycleResult(CycleStatus.NO_DATA, "no approved symbols")

            symbols_by_id = {s.id: s for s in approved}
            prices = await self._prices(approved)
            balances = await self._portfolio.read_balances(snapshot.id)

            context = await self._compile_context(approved, snapshot, balances, prices)
            decision_result = await self._decision_maker.decide(context)
            if decision_result.held or decision_result.decision is None:
                return CycleResult(CycleStatus.HELD)

            decision = decision_result.decision
            risk_state = RiskState(
                equity=snapshot.equity,
                daily_pnl=Decimal("0"),
                volatility=0.0,
                symbol_venues={s.id: s.venue for s in approved},
            )
            risk_result = self._risk_overlay.apply(decision.weights, risk_state)
            if risk_result.halted:
                return CycleResult(CycleStatus.HALTED, risk_result.rule)

            current_values = self._current_values(approved, balances, prices)
            plan = self._rebalancer.rebalance(
                current=current_values,
                target=risk_result.weights,
                prices=prices,
                equity=snapshot.equity,
            )

            saved_decision = await self._decisions.create(decision)
            orders = await self._persist_orders(plan, decision, symbols_by_id)

            if dry_run:
                return CycleResult(CycleStatus.EXECUTED, "dry run")

            execution = await self._executor.submit(orders, symbols_by_id)
            await self._apply_execution(orders, execution)
            return CycleResult(CycleStatus.EXECUTED)
        finally:
            await self._single_flight.release(self._lock_key)

    async def _reconcile_unconfirmed(self) -> None:
        unconfirmed = await self._order_journal.read_unreconciled()
        if not unconfirmed:
            return
        symbols_by_id = await self._approved_symbols_map()
        result = await self._reconciler.reconcile(unconfirmed, symbols_by_id)
        for client_order_id, status in result.resolved:
            order = await self._order_journal.read_by_client_order_id(client_order_id)
            if order is not None:
                await self._order_journal.update_status(order.id, status)

    async def _approved_symbols_map(self) -> dict:
        approved = await self._universes.read_symbols_by_state(
            self._universe_id, MembershipState.APPROVED
        )
        return {s.id: s for s in approved}

    async def _prices(self, approved) -> dict[str, Decimal]:
        prices: dict[str, Decimal] = {}
        for symbol in approved:
            candle = await self._market_data.read_latest(symbol.id)
            if candle is not None:
                prices[symbol.id] = candle.close
        return prices

    def _current_values(self, approved, balances, prices) -> dict[str, Decimal]:
        by_asset = {b.asset.lower(): b for b in balances}
        values: dict[str, Decimal] = {}
        for symbol in approved:
            balance = by_asset.get(symbol.base.lower())
            if balance is None or symbol.id not in prices:
                continue
            quantity = balance.free + balance.locked
            values[symbol.id] = quantity * prices[symbol.id]
        return values

    async def _compile_context(self, approved, snapshot, balances, prices) -> DecisionContext:
        universe_text = "\n".join(
            f"{s.id} {s.external} ({s.base}/{s.quote})" for s in approved
        )
        candle_lines = []
        for symbol in approved:
            price = prices.get(symbol.id)
            if price is not None:
                candle_lines.append(f"{symbol.id} close={price}")
        portfolio_lines = [f"equity={snapshot.equity}"]
        for b in balances:
            portfolio_lines.append(f"{b.asset} free={b.free} locked={b.locked}")

        analyses = await self._news.read_analyses(self._clock.now_ms() - 86_400_000)
        news_text = "\n".join(
            f"[{a.sentiment:+.2f}] {a.summary}" for a in analyses
        )

        return DecisionContext(
            universe_id=self._universe_id,
            as_of_ms=self._clock.now_ms(),
            universe=universe_text,
            approved_symbol_ids=[s.id for s in approved],
            candles="\n".join(candle_lines),
            news_summaries=news_text,
            portfolio="\n".join(portfolio_lines),
        )

    async def _persist_orders(self, plan, decision, symbols_by_id) -> list[Order]:
        orders: list[Order] = []
        for planned in plan.orders:
            side = planned.side
            price = planned.notional / planned.quantity if planned.quantity else Decimal("0")
            client_id = client_order_id(
                self._universe_id,
                decision.as_of_ms,
                planned.symbol_id,
                side.value,
            )
            order = await self._order_journal.create(
                Order(
                    id="",
                    client_order_id=client_id,
                    symbol_id=planned.symbol_id,
                    side=side,
                    price=price,
                    quantity=planned.quantity,
                    status=OrderStatus.PLANNED,
                    created_at_ms=self._clock.now_ms(),
                )
            )
            orders.append(order)
        return orders

    async def _apply_execution(self, orders: list[Order], execution) -> None:
        unconfirmed = set(execution.unconfirmed)
        for order in orders:
            if order.client_order_id in unconfirmed:
                await self._order_journal.update_status(order.id, OrderStatus.UNCONFIRMED)
                continue
            fills = [f for f in execution.fills if f.order_id == order.id]
            if fills:
                await self._order_journal.append_fills(order.id, fills)
                await self._order_journal.update_status(order.id, OrderStatus.FILLED)
            else:
                await self._order_journal.update_status(order.id, OrderStatus.SUBMITTED)
