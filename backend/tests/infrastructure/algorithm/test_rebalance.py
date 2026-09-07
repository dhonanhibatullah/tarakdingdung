from decimal import Decimal

import pytest

from tarakdingdung.domain.models.algorithm import Side, TargetWeights
from tarakdingdung.infrastructure.algorithm.rebalance.no_trade_band import NoTradeBandRebalancer
from tests.infrastructure.algorithm.conformance import (
    BTC_IDX, ETH_IDX, TS, portfolio, position,
)

PRICE = {BTC_IDX: Decimal("100")}


def weights(mapping) -> TargetWeights:
    return TargetWeights(timestamp=TS, weights=mapping)


def test_suppresses_drift_inside_the_band():
    intents = NoTradeBandRebalancer(band=0.05).plan(
        weights({BTC_IDX: 0.52}),
        portfolio(equity="1000", positions=[position(BTC_IDX, "5")]), PRICE)
    assert intents == ()


def test_trades_the_gap_outside_the_band():
    intents = NoTradeBandRebalancer(band=0.01).plan(
        weights({BTC_IDX: 0.8}),
        portfolio(equity="1000", positions=[position(BTC_IDX, "5")]), PRICE)
    assert len(intents) == 1
    assert intents[0].side is Side.BUY
    # 0.8 - 0.5 = 0.3 of 1000 equity at 100 = 3 units.
    assert intents[0].quantity == pytest.approx(Decimal("3"))


def test_sells_when_overweight():
    intents = NoTradeBandRebalancer(band=0.01).plan(
        weights({BTC_IDX: 0.2}),
        portfolio(equity="1000", positions=[position(BTC_IDX, "5")]), PRICE)
    assert intents[0].side is Side.SELL
    assert intents[0].quantity == pytest.approx(Decimal("3"))


def test_exits_positions_that_left_the_target():
    # An emptied target means sell everything, not leave it alone.
    intents = NoTradeBandRebalancer(band=0.01).plan(
        weights({}), portfolio(equity="1000", positions=[position(BTC_IDX, "5")]),
        PRICE)
    assert len(intents) == 1
    assert intents[0].side is Side.SELL
    assert intents[0].quantity == pytest.approx(Decimal("5"))


def test_opens_a_position_from_flat():
    intents = NoTradeBandRebalancer(band=0.01).plan(
        weights({BTC_IDX: 0.5}), portfolio(equity="1000"), PRICE)
    assert intents[0].side is Side.BUY
    assert intents[0].quantity == pytest.approx(Decimal("5"))


def test_skips_symbols_without_a_price():
    # A stale or guessed price would size a real order wrongly.
    assert NoTradeBandRebalancer(band=0.01).plan(
        weights({BTC_IDX: 0.5}), portfolio(), {}) == ()


def test_skips_a_non_positive_price():
    assert NoTradeBandRebalancer(band=0.01).plan(
        weights({BTC_IDX: 0.5}), portfolio(), {BTC_IDX: Decimal("0")}) == ()


def test_returns_nothing_without_equity():
    assert NoTradeBandRebalancer().plan(
        weights({BTC_IDX: 0.5}), portfolio(equity="0"), PRICE) == ()


def test_is_deterministically_ordered():
    prices = {BTC_IDX: Decimal("100"), ETH_IDX: Decimal("100")}
    intents = NoTradeBandRebalancer(band=0.01).plan(
        weights({ETH_IDX: 0.3, BTC_IDX: 0.3}), portfolio(equity="1000"), prices)
    assert [i.symbol for i in intents] == [BTC_IDX, ETH_IDX]
