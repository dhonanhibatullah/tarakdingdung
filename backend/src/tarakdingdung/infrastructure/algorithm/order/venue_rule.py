from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.order import OrderPlanner
from tarakdingdung.domain.models.algorithm import (
    OrderPlan, OrderType, PlannedOrder, RejectedIntent, RejectionReason, Side,
    TimeInForce, TradeIntent,
)
from tarakdingdung.domain.models.market import Symbol, SymbolRules
from tarakdingdung.infrastructure.algorithm.shared.numeric import ceil_to_step, floor_to_step


class VenueRuleOrderPlanner(OrderPlanner):
    """Rounds intents to a venue's tick and step sizes and drops what it must.

    Quantities are floored rather than rounded: rounding up can exceed the
    position the rebalancer asked for, and on a sell can exceed what is held.

    Limit prices move in the direction that favours us — a buy is floored to
    the tick below the reference, a sell raised to the tick above — so
    rounding never silently worsens the price the rebalancer sized against.

    Every intent leaves as either an order or a ``RejectedIntent``; nothing is
    dropped in silence.
    """

    def __init__(self, *, order_type: OrderType = OrderType.LIMIT,
                 time_in_force: TimeInForce = TimeInForce.GTC) -> None:
        self._type = order_type
        self._time_in_force = time_in_force

    def plan(self, intents: tuple[TradeIntent, ...],
             rules: Mapping[Symbol, SymbolRules]) -> OrderPlan:
        orders: list[PlannedOrder] = []
        rejected: list[RejectedIntent] = []
        for intent in intents:
            outcome = self._plan_one(intent, rules.get(intent.symbol))
            if isinstance(outcome, PlannedOrder):
                orders.append(outcome)
            else:
                rejected.append(RejectedIntent(intent=intent, reason=outcome))
        return OrderPlan(orders=tuple(orders), rejected=tuple(rejected))

    def _plan_one(self, intent: TradeIntent,
                  rules: SymbolRules | None) -> PlannedOrder | RejectionReason:
        if rules is None:
            return RejectionReason.NO_RULES

        quantity = floor_to_step(intent.quantity, rules.step_size)
        if quantity <= 0:
            return RejectionReason.ROUNDS_TO_ZERO

        price = self._price(intent, rules)
        if self._type is not OrderType.MARKET and (price is None or price <= 0):
            return RejectionReason.NO_PRICE

        valuation = price if price is not None else intent.reference_price
        if quantity * valuation < rules.min_notional:
            return RejectionReason.BELOW_MIN_NOTIONAL

        return PlannedOrder(symbol=intent.symbol, side=intent.side,
                            type=self._type, quantity=quantity, price=price,
                            time_in_force=self._time_in_force)

    def _price(self, intent: TradeIntent, rules: SymbolRules) -> Decimal | None:
        if self._type is OrderType.MARKET:
            return None
        if intent.side is Side.BUY:
            return floor_to_step(intent.reference_price, rules.tick_size)
        return ceil_to_step(intent.reference_price, rules.tick_size)
