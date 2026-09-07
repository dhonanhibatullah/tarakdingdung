import math
from decimal import Decimal

import pytest

from tarakdingdung.domain.models.algorithm import (
    CostEstimate, FeatureSet, OrderType, PlannedOrder, Side, Signals, TargetWeights,
    TimeInForce, TradeIntent,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import Candle, Symbol, Venue
from tarakdingdung.domain.models.performance import OverfittingReport

BTC = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")
ETH = Symbol(venue=Venue.TOKOCRYPTO, base="ETH", quote="USDT")
TS = 1_757_000_000_000


def _raises_validation():
    return pytest.raises(DomainError)


def _assert_validation(exc_info):
    assert exc_info.value.type is ErrorType.VALIDATION


# --- FeatureSet -------------------------------------------------------------

def test_feature_set_accepts_finite_values():
    fs = FeatureSet(timestamp=TS, values={BTC: {"sma_20": 1.5, "rsi": -0.0}})
    assert fs.values[BTC]["sma_20"] == 1.5


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_feature_set_rejects_non_finite(bad):
    with _raises_validation() as e:
        FeatureSet(timestamp=TS, values={BTC: {"sma_20": bad}})
    _assert_validation(e)


def test_feature_set_allows_missing_symbols():
    # A symbol with too little history is omitted, not filled — the normal
    # state at the start of a backtest.
    fs = FeatureSet(timestamp=TS, values={BTC: {"sma_20": 1.0}})
    assert ETH not in fs.values


# --- Signals ----------------------------------------------------------------

@pytest.mark.parametrize("score", [-1.0, 0.0, 1.0])
def test_signals_accept_the_closed_unit_interval(score):
    assert Signals(timestamp=TS, scores={BTC: score}).scores[BTC] == score


@pytest.mark.parametrize("score", [1.0000001, -1.0000001, 5.0])
def test_signals_reject_scores_outside_the_interval(score):
    with _raises_validation() as e:
        Signals(timestamp=TS, scores={BTC: score})
    _assert_validation(e)


def test_signals_reject_nan():
    with _raises_validation() as e:
        Signals(timestamp=TS, scores={BTC: float("nan")})
    _assert_validation(e)


# --- TargetWeights ----------------------------------------------------------

def test_target_weights_accept_exactly_full_investment():
    tw = TargetWeights(timestamp=TS, weights={BTC: 0.5, ETH: 0.5})
    assert sum(tw.weights.values()) == 1.0


def test_target_weights_accept_shorts_within_gross_bound():
    TargetWeights(timestamp=TS, weights={BTC: 0.6, ETH: -0.4})


def test_target_weights_accept_empty_meaning_all_cash():
    assert TargetWeights(timestamp=TS, weights={}).weights == {}


def test_target_weights_reject_leverage():
    with _raises_validation() as e:
        TargetWeights(timestamp=TS, weights={BTC: 0.7, ETH: 0.7})
    _assert_validation(e)


def test_target_weights_reject_gross_leverage_from_shorts():
    with _raises_validation() as e:
        TargetWeights(timestamp=TS, weights={BTC: 0.8, ETH: -0.8})
    _assert_validation(e)


def test_target_weights_tolerate_float_summation_error():
    # An allocator normalising raw scores to sum to one lands a hair above it
    # in binary floating point. Without the tolerance this fully-invested,
    # entirely legitimate portfolio would be rejected as leveraged.
    raw = [0.54, 0.63, 0.73]
    total = sum(raw)
    weights = {Symbol(Venue.INDODAX, f"C{i}", "IDR"): w / total
               for i, w in enumerate(raw)}
    accumulated = 0.0
    for w in weights.values():
        accumulated += abs(w)
    assert accumulated > 1.0
    TargetWeights(timestamp=TS, weights=weights)


def test_target_weights_reject_infinity():
    with _raises_validation() as e:
        TargetWeights(timestamp=TS, weights={BTC: float("inf")})
    _assert_validation(e)


# --- TradeIntent ------------------------------------------------------------

def test_trade_intent_accepts_a_positive_trade():
    ti = TradeIntent(symbol=BTC, side=Side.BUY, quantity=Decimal("0.5"),
                     reference_price=Decimal("1000"))
    assert ti.side is Side.BUY


@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-1"), Decimal("NaN")])
def test_trade_intent_rejects_non_positive_quantity(quantity):
    with _raises_validation() as e:
        TradeIntent(symbol=BTC, side=Side.BUY, quantity=quantity,
                    reference_price=Decimal("1000"))
    _assert_validation(e)


def test_trade_intent_rejects_non_positive_price():
    with _raises_validation() as e:
        TradeIntent(symbol=BTC, side=Side.SELL, quantity=Decimal("1"),
                    reference_price=Decimal("0"))
    _assert_validation(e)


# --- PlannedOrder -----------------------------------------------------------

def test_planned_order_accepts_a_limit_with_a_price():
    o = PlannedOrder(symbol=BTC, side=Side.BUY, type=OrderType.LIMIT,
                     quantity=Decimal("1"), price=Decimal("100"),
                     time_in_force=TimeInForce.GTC)
    assert o.client_order_id is None


def test_planned_order_accepts_a_market_without_a_price():
    PlannedOrder(symbol=BTC, side=Side.SELL, type=OrderType.MARKET,
                 quantity=Decimal("1"), price=None, time_in_force=TimeInForce.IOC)


def test_planned_order_rejects_a_market_carrying_a_price():
    with _raises_validation() as e:
        PlannedOrder(symbol=BTC, side=Side.SELL, type=OrderType.MARKET,
                     quantity=Decimal("1"), price=Decimal("100"),
                     time_in_force=TimeInForce.IOC)
    _assert_validation(e)


@pytest.mark.parametrize("order_type", [OrderType.LIMIT, OrderType.LIMIT_MAKER])
def test_planned_order_rejects_a_limit_without_a_price(order_type):
    with _raises_validation() as e:
        PlannedOrder(symbol=BTC, side=Side.BUY, type=order_type,
                     quantity=Decimal("1"), price=None,
                     time_in_force=TimeInForce.GTC)
    _assert_validation(e)


def test_planned_order_rejects_zero_quantity():
    with _raises_validation() as e:
        PlannedOrder(symbol=BTC, side=Side.BUY, type=OrderType.MARKET,
                     quantity=Decimal("0"), price=None,
                     time_in_force=TimeInForce.IOC)
    _assert_validation(e)


# --- CostEstimate -----------------------------------------------------------

def test_cost_estimate_accepts_zero_cost():
    c = CostEstimate(fee=Decimal("0"), slippage=Decimal("0"),
                     total=Decimal("0"), fillable=True)
    assert c.fillable is True


def test_cost_estimate_can_report_an_unfillable_order():
    # The honest answer is sometimes "the book cannot absorb it".
    assert CostEstimate(fee=Decimal("1"), slippage=Decimal("2"),
                        total=Decimal("3"), fillable=False).fillable is False


@pytest.mark.parametrize("field", ["fee", "slippage"])
def test_cost_estimate_rejects_negative_components(field):
    kwargs = {"fee": Decimal("0"), "slippage": Decimal("0"),
              "total": Decimal("0"), "fillable": True}
    kwargs[field] = Decimal("-1")
    with _raises_validation() as e:
        CostEstimate(**kwargs)
    _assert_validation(e)


# --- OverfittingReport ------------------------------------------------------

@pytest.mark.parametrize("probability", [0.0, 0.5, 1.0])
def test_overfitting_report_accepts_a_probability(probability):
    r = OverfittingReport(probability=probability, threshold=0.1,
                          passed=probability < 0.1)
    assert r.probability == probability


@pytest.mark.parametrize("probability", [-0.01, 1.01, float("nan")])
def test_overfitting_report_rejects_a_non_probability(probability):
    with _raises_validation() as e:
        OverfittingReport(probability=probability, threshold=0.1, passed=False)
    _assert_validation(e)


# --- per-row types stay unvalidated ----------------------------------------

def test_candle_is_not_validated():
    # Deliberate: candles are constructed in the millions when replaying
    # history, so they are trusted to the collector that wrote them. Pinning
    # this keeps the performance decision from being "fixed" by accident.
    c = Candle(open_time=-1, open=Decimal("-5"), high=Decimal("0"),
               low=Decimal("99"), close=Decimal("NaN"), volume=Decimal("-1"))
    assert c.close.is_nan()


def test_models_are_frozen():
    tw = TargetWeights(timestamp=TS, weights={})
    with pytest.raises(Exception):
        tw.timestamp = 0


def test_symbol_is_hashable_and_venue_distinguishes_pairs():
    same_pair_elsewhere = Symbol(venue=Venue.TOKOCRYPTO, base="BTC", quote="IDR")
    assert BTC != same_pair_elsewhere
    assert len({BTC, same_pair_elsewhere}) == 2


def test_weight_tolerance_is_tighter_than_any_meaningful_position():
    from tarakdingdung.domain.models.algorithm import _WEIGHT_TOLERANCE
    assert math.isfinite(_WEIGHT_TOLERANCE)
    assert 0 < _WEIGHT_TOLERANCE < 1e-6
