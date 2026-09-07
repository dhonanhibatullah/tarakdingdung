from collections.abc import Mapping
from dataclasses import replace
from uuid import UUID

from tarakdingdung.domain.contracts.algorithm.cycle import CyclePlanner
from tarakdingdung.domain.contracts.algorithm.order import OrderPlanner
from tarakdingdung.domain.contracts.algorithm.rebalance import Rebalancer
from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.contracts.algorithm.strategy import Strategy
from tarakdingdung.domain.models.algorithm import CyclePlan, OrderPlan, TargetWeights
from tarakdingdung.domain.models.market import MarketSnapshot, Symbol, SymbolRules
from tarakdingdung.domain.models.portfolio import Portfolio, RiskState
from tarakdingdung.infrastructure.algorithm.cycle.identifiers import client_order_id


class StandardCyclePlanner(CyclePlanner):
    """Strategy, then risk, then rebalance, then venue rules.

    Risk rules are held as a sequence rather than one composite so that the
    plan can name *which* rule flattened the book. "The bot did nothing" is the
    most common operational question and the hardest to answer afterwards; a
    composite would only be able to report that something stopped it.

    A halt is not a no-op. Empty weights mean hold nothing, so the rebalancer
    still produces exit orders and the book is liquidated rather than merely
    frozen.
    """

    def __init__(self, *, strategy: Strategy, risk_rules: tuple[RiskRule, ...],
                 rebalancer: Rebalancer, order_planner: OrderPlanner) -> None:
        self._strategy = strategy
        self._risk_rules = risk_rules
        self._rebalancer = rebalancer
        self._order_planner = order_planner

    def plan(self, *, strategy_id: UUID, snapshot: MarketSnapshot,
             portfolio: Portfolio, state: RiskState,
             rules: Mapping[Symbol, SymbolRules]) -> CyclePlan:
        weights, halted_by = self._apply_risk(
            self._strategy.decide(snapshot, portfolio), portfolio, state)

        intents = self._rebalancer.plan(weights, portfolio, snapshot.last_prices)
        orders = self._identify(
            self._order_planner.plan(intents, rules), strategy_id, snapshot.timestamp)

        return CyclePlan(timestamp=snapshot.timestamp, weights=weights,
                         orders=orders, halted_by=halted_by)

    def _apply_risk(self, weights: TargetWeights, portfolio: Portfolio,
                    state: RiskState) -> tuple[TargetWeights, str | None]:
        for rule in self._risk_rules:
            applied = rule.apply(weights, portfolio, state)
            if applied.weights == {} and weights.weights != {}:
                # First rule to flatten the book owns the halt. Later rules
                # could only keep it empty, so stopping here loses nothing and
                # attributes the decision to the rule that actually made it.
                return applied, type(rule).__name__
            weights = applied
        return weights, None

    def _identify(self, plan: OrderPlan, strategy_id: UUID,
                  timestamp: int) -> OrderPlan:
        return OrderPlan(
            orders=tuple(
                replace(order, client_order_id=client_order_id(
                    strategy_id=strategy_id, timestamp=timestamp,
                    symbol=order.symbol, side=order.side))
                for order in plan.orders),
            rejected=plan.rejected)
