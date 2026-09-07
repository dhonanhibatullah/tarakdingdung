from decimal import Decimal

import pytest

from tarakdingdung.domain.models.algorithm import (
    FeatureSet, OrderType, RejectionReason, Side, Signals, TargetWeights, TimeInForce,
    TradeIntent,
)
from tarakdingdung.domain.models.market import BookLevel, Candle, MarketSnapshot, OrderBook
from tarakdingdung.infrastructure.algorithm.allocation import (
    ConvictionWeightedAllocator, EqualWeightAllocator,
)
from tarakdingdung.infrastructure.algorithm.cost import DepthWalkCostModel, FlatFeeCostModel
from tarakdingdung.infrastructure.algorithm.feature import (
    MOMENTUM, SMA_FAST, SMA_SLOW, VOLATILITY, RollingWindowFeatureExtractor,
)
from tarakdingdung.infrastructure.algorithm.order import VenueRuleOrderPlanner
from tarakdingdung.infrastructure.algorithm.rebalance import NoTradeBandRebalancer
from tarakdingdung.infrastructure.algorithm.risk import (
    PerAssetCapRiskRule, PerVenueCapRiskRule, default_overlay,
)
from tarakdingdung.infrastructure.algorithm.shared.numeric import ceil_to_step, floor_to_step
from tarakdingdung.infrastructure.algorithm.signal import (
    CrossSectionalMomentumSignalGenerator, MovingAverageCrossSignalGenerator,
)
from tarakdingdung.infrastructure.algorithm.universe import (
    LiquidityUniverseSelector, StaticUniverseSelector,
)
from tests.infrastructure.algorithm.conformance import (
    BTC_IDX, BTC_TKO, ETH_IDX, ETH_TKO, TS, book, portfolio, position, risk_state, rules,
)


def candles(prices: list[float]) -> tuple[Candle, ...]:
    return tuple(Candle(open_time=TS + i, open=Decimal(str(p)), high=Decimal(str(p)),
                        low=Decimal(str(p)), close=Decimal(str(p)),
                        volume=Decimal("1"))
                 for i, p in enumerate(prices))


def snapshot(*, candle_map=None, books=None, prices=None) -> MarketSnapshot:
    return MarketSnapshot(timestamp=TS, candles=candle_map or {},
                          books=books or {}, last_prices=prices or {})


# --- numeric ----------------------------------------------------------------

@pytest.mark.parametrize("value,step,expected", [
    ("1.23456", "0.001", "1.234"),
    ("1.0", "0.001", "1.0"),
    ("0.0000001", "0.001", "0"),
    ("5", "0", "5"),
])
def test_floor_to_step(value, step, expected):
    assert floor_to_step(Decimal(value), Decimal(step)) == Decimal(expected)


@pytest.mark.parametrize("value,step,expected", [
    ("1.2341", "0.001", "1.235"),
    ("1.234", "0.001", "1.234"),
    ("5", "0", "5"),
])
def test_ceil_to_step(value, step, expected):
    assert ceil_to_step(Decimal(value), Decimal(step)) == Decimal(expected)


# --- universe ---------------------------------------------------------------

def test_static_universe_drops_symbols_absent_from_the_snapshot():
    selector = StaticUniverseSelector((BTC_IDX, ETH_IDX))
    assert selector.select(snapshot(prices={BTC_IDX: Decimal("100")})) == (BTC_IDX,)


def test_static_universe_is_deterministically_ordered():
    selector = StaticUniverseSelector((ETH_TKO, BTC_IDX, ETH_IDX))
    prices = {s: Decimal("100") for s in (ETH_TKO, BTC_IDX, ETH_IDX)}
    assert selector.select(snapshot(prices=prices)) == (BTC_IDX, ETH_IDX, ETH_TKO)


def test_liquidity_universe_excludes_thin_books():
    deep = book(BTC_IDX, levels=5, size="10")
    thin = book(ETH_IDX, levels=1, size="0.001")
    selector = LiquidityUniverseSelector(min_book_notional=Decimal("1000"))
    selected = selector.select(snapshot(
        books={BTC_IDX: deep, ETH_IDX: thin},
        prices={BTC_IDX: Decimal("100"), ETH_IDX: Decimal("100")}))
    assert selected == (BTC_IDX,)


def test_liquidity_universe_judges_the_thinner_side():
    lopsided = OrderBook(symbol=BTC_IDX, timestamp=TS,
                         bids=(BookLevel(price=Decimal("100"), quantity=Decimal("1000")),),
                         asks=(BookLevel(price=Decimal("101"), quantity=Decimal("0.001")),))
    selector = LiquidityUniverseSelector(min_book_notional=Decimal("1000"))
    assert selector.select(snapshot(books={BTC_IDX: lopsided},
                                    prices={BTC_IDX: Decimal("100")})) == ()


# --- feature ----------------------------------------------------------------

def test_feature_extractor_omits_symbols_with_too_little_history():
    extractor = RollingWindowFeatureExtractor(momentum_window=5, fast_window=2,
                                              slow_window=5, volatility_window=5)
    features = extractor.compute(snapshot(candle_map={
        BTC_IDX: candles([100.0] * 10),
        ETH_IDX: candles([100.0] * 3),
    }))
    assert BTC_IDX in features.values
    assert ETH_IDX not in features.values


def test_feature_extractor_computes_the_documented_features():
    extractor = RollingWindowFeatureExtractor(momentum_window=4, fast_window=2,
                                              slow_window=4, volatility_window=4)
    prices = [100.0, 101.0, 102.0, 103.0, 110.0]
    features = extractor.compute(snapshot(candle_map={BTC_IDX: candles(prices)}))
    values = features.values[BTC_IDX]
    assert set(values) == {MOMENTUM, SMA_FAST, SMA_SLOW, VOLATILITY}
    assert values[MOMENTUM] == pytest.approx(110.0 / 100.0 - 1.0)
    assert values[SMA_FAST] == pytest.approx((103.0 + 110.0) / 2)
    assert values[VOLATILITY] > 0


def test_feature_extractor_survives_a_zero_base_price():
    extractor = RollingWindowFeatureExtractor(momentum_window=2, fast_window=2,
                                              slow_window=2, volatility_window=2)
    # The momentum base is the close two candles back; a zero there would
    # divide by nothing, so the symbol is omitted rather than made infinite.
    features = extractor.compute(snapshot(candle_map={
        BTC_IDX: candles([0.0, 1.0, 2.0])}))
    assert BTC_IDX not in features.values


# --- signal -----------------------------------------------------------------

def _features(values) -> FeatureSet:
    return FeatureSet(timestamp=TS, values=values)


def test_momentum_signal_ranks_across_symbols():
    signals = CrossSectionalMomentumSignalGenerator(long_only=False).generate(
        _features({BTC_IDX: {MOMENTUM: 0.5}, ETH_IDX: {MOMENTUM: 0.1},
                   BTC_TKO: {MOMENTUM: -0.3}}))
    assert signals.scores[BTC_TKO] == pytest.approx(-1.0)
    assert signals.scores[ETH_IDX] == pytest.approx(0.0)
    assert signals.scores[BTC_IDX] == pytest.approx(1.0)


def test_momentum_signal_is_long_only_by_default():
    # Neither venue supports shorting, so a negative weight would describe a
    # position we cannot hold.
    signals = CrossSectionalMomentumSignalGenerator().generate(
        _features({BTC_IDX: {MOMENTUM: 0.5}, ETH_IDX: {MOMENTUM: -0.3}}))
    assert min(signals.scores.values()) >= 0.0


def test_momentum_signal_handles_a_single_symbol():
    generator = CrossSectionalMomentumSignalGenerator(long_only=False)
    assert generator.generate(_features({BTC_IDX: {MOMENTUM: 0.2}})).scores[BTC_IDX] == 1.0
    assert generator.generate(_features({BTC_IDX: {MOMENTUM: -0.2}})).scores[BTC_IDX] == -1.0


def test_momentum_signal_skips_symbols_missing_the_feature():
    signals = CrossSectionalMomentumSignalGenerator().generate(
        _features({BTC_IDX: {MOMENTUM: 0.5}, ETH_IDX: {VOLATILITY: 0.1}}))
    assert set(signals.scores) == {BTC_IDX}


def test_moving_average_cross_signal():
    signals = MovingAverageCrossSignalGenerator().generate(
        _features({BTC_IDX: {SMA_FAST: 10.0, SMA_SLOW: 5.0},
                   ETH_IDX: {SMA_FAST: 5.0, SMA_SLOW: 10.0}}))
    assert signals.scores[BTC_IDX] == 1.0
    assert signals.scores[ETH_IDX] == 0.0


# --- allocation -------------------------------------------------------------

def test_equal_weight_splits_the_budget():
    weights = EqualWeightAllocator().allocate(
        Signals(timestamp=TS, scores={BTC_IDX: 1.0, ETH_IDX: 0.4}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.5)
    assert weights.weights[ETH_IDX] == pytest.approx(0.5)


def test_equal_weight_respects_max_positions_by_conviction():
    weights = EqualWeightAllocator(max_positions=2).allocate(
        Signals(timestamp=TS, scores={BTC_IDX: 0.1, ETH_IDX: 0.9, BTC_TKO: 0.5}),
        portfolio())
    assert set(weights.weights) == {ETH_IDX, BTC_TKO}


def test_equal_weight_honours_a_partial_budget():
    weights = EqualWeightAllocator(max_gross=0.5).allocate(
        Signals(timestamp=TS, scores={BTC_IDX: 1.0}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.5)


def test_conviction_weighting_is_proportional():
    weights = ConvictionWeightedAllocator().allocate(
        Signals(timestamp=TS, scores={BTC_IDX: 0.75, ETH_IDX: 0.25}), portfolio())
    assert weights.weights[BTC_IDX] == pytest.approx(0.75)
    assert weights.weights[ETH_IDX] == pytest.approx(0.25)


# --- risk -------------------------------------------------------------------

def test_per_venue_cap_scales_a_breaching_venue_proportionally():
    rule = PerVenueCapRiskRule(max_weight=0.30)
    capped = rule.apply(
        TargetWeights(timestamp=TS, weights={BTC_IDX: 0.6, ETH_IDX: 0.2, BTC_TKO: 0.2}),
        portfolio(), risk_state())
    indodax = capped.weights[BTC_IDX] + capped.weights[ETH_IDX]
    assert indodax == pytest.approx(0.30)
    # The shape the allocator chose is preserved: 3:1 before and after.
    assert capped.weights[BTC_IDX] / capped.weights[ETH_IDX] == pytest.approx(3.0)
    # An untouched venue is left alone.
    assert capped.weights[BTC_TKO] == pytest.approx(0.2)


def test_per_asset_cap_aggregates_the_same_coin_across_venues():
    # Holding BTC on both exchanges is one bet on BTC, not two.
    rule = PerAssetCapRiskRule(max_weight=0.30)
    capped = rule.apply(
        TargetWeights(timestamp=TS, weights={BTC_IDX: 0.3, BTC_TKO: 0.3}),
        portfolio(), risk_state())
    assert capped.weights[BTC_IDX] + capped.weights[BTC_TKO] == pytest.approx(0.30)


def test_drawdown_halt_flattens_past_the_budget():
    overlay = default_overlay(max_drawdown=0.20)
    weights = TargetWeights(timestamp=TS, weights={BTC_IDX: 0.2})
    survived = overlay.apply(weights, portfolio(equity="9000"), risk_state())
    halted = overlay.apply(weights, portfolio(equity="7000"), risk_state())
    assert survived.weights != {}
    assert halted.weights == {}


def test_daily_loss_halt_is_relative_to_equity():
    overlay = default_overlay(max_daily_loss=0.05)
    weights = TargetWeights(timestamp=TS, weights={BTC_IDX: 0.2})
    ok = overlay.apply(weights, portfolio(), risk_state(daily_pnl="-400"))
    breached = overlay.apply(weights, portfolio(), risk_state(daily_pnl="-600"))
    assert ok.weights != {}
    assert breached.weights == {}


# --- rebalance --------------------------------------------------------------

def test_rebalancer_suppresses_drift_inside_the_band():
    rebalancer = NoTradeBandRebalancer(band=0.05)
    intents = rebalancer.plan(
        TargetWeights(timestamp=TS, weights={BTC_IDX: 0.52}),
        portfolio(equity="1000", positions=[position(BTC_IDX, "5")]),
        {BTC_IDX: Decimal("100")})
    assert intents == ()


def test_rebalancer_trades_the_gap_outside_the_band():
    rebalancer = NoTradeBandRebalancer(band=0.01)
    intents = rebalancer.plan(
        TargetWeights(timestamp=TS, weights={BTC_IDX: 0.8}),
        portfolio(equity="1000", positions=[position(BTC_IDX, "5")]),
        {BTC_IDX: Decimal("100")})
    assert len(intents) == 1
    assert intents[0].side is Side.BUY
    # 0.8 - 0.5 = 0.3 of 1000 equity at 100 = 3 units.
    assert intents[0].quantity == pytest.approx(Decimal("3"))


def test_rebalancer_exits_positions_that_left_the_target():
    rebalancer = NoTradeBandRebalancer(band=0.01)
    intents = rebalancer.plan(
        TargetWeights(timestamp=TS, weights={}),
        portfolio(equity="1000", positions=[position(BTC_IDX, "5")]),
        {BTC_IDX: Decimal("100")})
    assert len(intents) == 1
    assert intents[0].side is Side.SELL
    assert intents[0].quantity == pytest.approx(Decimal("5"))


def test_rebalancer_skips_symbols_without_a_price():
    # A stale or guessed price would size a real order wrongly.
    intents = NoTradeBandRebalancer(band=0.01).plan(
        TargetWeights(timestamp=TS, weights={BTC_IDX: 0.5}), portfolio(), {})
    assert intents == ()


def test_rebalancer_returns_nothing_without_equity():
    intents = NoTradeBandRebalancer().plan(
        TargetWeights(timestamp=TS, weights={BTC_IDX: 0.5}),
        portfolio(equity="0"), {BTC_IDX: Decimal("100")})
    assert intents == ()


# --- order ------------------------------------------------------------------

def test_order_planner_floors_quantity_to_the_step():
    plan = VenueRuleOrderPlanner().plan(
        (TradeIntent(symbol=BTC_IDX, side=Side.BUY, quantity=Decimal("1.23456789"),
                     reference_price=Decimal("100")),),
        {BTC_IDX: rules(BTC_IDX, step="0.001")})
    assert plan.orders[0].quantity == Decimal("1.234")


def test_order_planner_rounds_price_in_our_favour():
    planner = VenueRuleOrderPlanner()
    intents = (
        TradeIntent(symbol=BTC_IDX, side=Side.BUY, quantity=Decimal("1"),
                    reference_price=Decimal("100.007")),
        TradeIntent(symbol=ETH_IDX, side=Side.SELL, quantity=Decimal("1"),
                    reference_price=Decimal("100.003")),
    )
    plan = planner.plan(intents, {BTC_IDX: rules(BTC_IDX), ETH_IDX: rules(ETH_IDX)})
    by_symbol = {o.symbol: o for o in plan.orders}
    assert by_symbol[BTC_IDX].price == Decimal("100.00")
    assert by_symbol[ETH_IDX].price == Decimal("100.01")


def test_order_planner_reports_why_it_rejected():
    planner = VenueRuleOrderPlanner()
    intents = (
        TradeIntent(symbol=BTC_IDX, side=Side.BUY, quantity=Decimal("0.00001"),
                    reference_price=Decimal("100")),
        TradeIntent(symbol=ETH_IDX, side=Side.BUY, quantity=Decimal("1"),
                    reference_price=Decimal("100")),
    )
    plan = planner.plan(intents, {
        BTC_IDX: rules(BTC_IDX, step="0.001"),
        ETH_IDX: rules(ETH_IDX, min_notional="1000000")})
    reasons = {r.intent.symbol: r.reason for r in plan.rejected}
    assert reasons[BTC_IDX] is RejectionReason.ROUNDS_TO_ZERO
    assert reasons[ETH_IDX] is RejectionReason.BELOW_MIN_NOTIONAL


def test_market_orders_carry_no_price():
    plan = VenueRuleOrderPlanner(order_type=OrderType.MARKET,
                                 time_in_force=TimeInForce.IOC).plan(
        (TradeIntent(symbol=BTC_IDX, side=Side.BUY, quantity=Decimal("1"),
                     reference_price=Decimal("100")),),
        {BTC_IDX: rules(BTC_IDX)})
    assert plan.orders[0].price is None


# --- cost -------------------------------------------------------------------

def test_depth_walk_charges_more_than_the_touch_for_a_deep_order():
    model = DepthWalkCostModel(fee_rate=Decimal("0"))
    depth = book(BTC_IDX, levels=5, size="1")
    shallow = model.estimate(_buy("1"), depth)
    deep = model.estimate(_buy("4"), depth)
    # One level in, there is no slippage; four levels in, there is.
    assert shallow.slippage == 0
    assert deep.slippage > 0


def test_flat_fee_is_proportional_to_notional():
    model = FlatFeeCostModel(fee_rate=Decimal("0.002"))
    estimate = model.estimate(_buy("2"), book(BTC_IDX))
    # Best ask is 101.
    assert estimate.fee == Decimal("2") * Decimal("101") * Decimal("0.002")


def test_depth_walk_reports_an_unfillable_order_with_partial_cost():
    model = DepthWalkCostModel(fee_rate=Decimal("0.001"))
    estimate = model.estimate(_buy("1000"), book(BTC_IDX, levels=2, size="1"))
    assert estimate.fillable is False
    assert estimate.total > 0


def _buy(quantity: str):
    from tarakdingdung.domain.models.algorithm import PlannedOrder
    return PlannedOrder(symbol=BTC_IDX, side=Side.BUY, type=OrderType.LIMIT,
                        quantity=Decimal(quantity), price=Decimal("101"),
                        time_in_force=TimeInForce.GTC)
