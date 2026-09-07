from decimal import Decimal

from tarakdingdung.domain.models.algorithm import (
    OrderType, RejectionReason, Side, TimeInForce, TradeIntent,
)
from tarakdingdung.infrastructure.algorithm.order.venue_rule import VenueRuleOrderPlanner
from tests.infrastructure.algorithm.conformance import BTC_IDX, ETH_IDX, ETH_TKO, rules


def intent(symbol, side, quantity, price) -> TradeIntent:
    return TradeIntent(symbol=symbol, side=side, quantity=Decimal(quantity),
                       reference_price=Decimal(price))


def test_floors_quantity_to_the_step():
    plan = VenueRuleOrderPlanner().plan(
        (intent(BTC_IDX, Side.BUY, "1.23456789", "100"),),
        {BTC_IDX: rules(BTC_IDX, step="0.001")})
    assert plan.orders[0].quantity == Decimal("1.234")


def test_rounds_price_in_our_favour():
    plan = VenueRuleOrderPlanner().plan(
        (intent(BTC_IDX, Side.BUY, "1", "100.007"),
         intent(ETH_IDX, Side.SELL, "1", "100.003")),
        {BTC_IDX: rules(BTC_IDX), ETH_IDX: rules(ETH_IDX)})
    by_symbol = {o.symbol: o for o in plan.orders}
    assert by_symbol[BTC_IDX].price == Decimal("100.00")
    assert by_symbol[ETH_IDX].price == Decimal("100.01")


def test_reports_why_it_rejected():
    plan = VenueRuleOrderPlanner().plan(
        (intent(BTC_IDX, Side.BUY, "0.00001", "100"),
         intent(ETH_IDX, Side.BUY, "1", "100"),
         intent(ETH_TKO, Side.BUY, "1", "100")),
        {BTC_IDX: rules(BTC_IDX, step="0.001"),
         ETH_IDX: rules(ETH_IDX, min_notional="1000000")})
    reasons = {r.intent.symbol: r.reason for r in plan.rejected}
    assert reasons[BTC_IDX] is RejectionReason.ROUNDS_TO_ZERO
    assert reasons[ETH_IDX] is RejectionReason.BELOW_MIN_NOTIONAL
    assert reasons[ETH_TKO] is RejectionReason.NO_RULES


def test_market_orders_carry_no_price():
    plan = VenueRuleOrderPlanner(order_type=OrderType.MARKET,
                                 time_in_force=TimeInForce.IOC).plan(
        (intent(BTC_IDX, Side.BUY, "1", "100"),), {BTC_IDX: rules(BTC_IDX)})
    assert plan.orders[0].price is None
    assert plan.orders[0].type is OrderType.MARKET


def test_market_orders_value_the_notional_at_the_reference():
    plan = VenueRuleOrderPlanner(order_type=OrderType.MARKET,
                                 time_in_force=TimeInForce.IOC).plan(
        (intent(BTC_IDX, Side.BUY, "1", "100"),),
        {BTC_IDX: rules(BTC_IDX, min_notional="1000")})
    assert plan.rejected[0].reason is RejectionReason.BELOW_MIN_NOTIONAL


def test_carries_the_configured_time_in_force():
    plan = VenueRuleOrderPlanner(order_type=OrderType.LIMIT_MAKER,
                                 time_in_force=TimeInForce.GTX).plan(
        (intent(BTC_IDX, Side.BUY, "1", "100"),), {BTC_IDX: rules(BTC_IDX)})
    assert plan.orders[0].time_in_force is TimeInForce.GTX


def test_a_price_rounding_to_zero_is_rejected():
    plan = VenueRuleOrderPlanner().plan(
        (intent(BTC_IDX, Side.BUY, "1", "0.5"),),
        {BTC_IDX: rules(BTC_IDX, tick="1")})
    assert plan.rejected[0].reason is RejectionReason.NO_PRICE
