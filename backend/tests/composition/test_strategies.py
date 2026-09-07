import pytest

from tarakdingdung.composition.main.strategies import build_planner
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.algorithm.allocation.conviction_weighted import (
    ConvictionWeightedAllocator,
)
from tarakdingdung.infrastructure.algorithm.risk.halt_flag import HaltFlagRiskRule
from tarakdingdung.infrastructure.algorithm.risk.per_position_cap import PerPositionCapRiskRule
from tarakdingdung.infrastructure.algorithm.signal.moving_average_cross import (
    MovingAverageCrossSignalGenerator,
)
from tarakdingdung.infrastructure.algorithm.strategy.buy_and_hold import BuyAndHoldStrategy
from tarakdingdung.infrastructure.algorithm.strategy.pipeline import PipelineStrategy
from tests.fakes.trading import make_strategy
from tests.infrastructure.algorithm.conformance import BTC_IDX


def config(**kw):
    return make_strategy(universe=(BTC_IDX,), **kw)


def test_builds_a_pipeline_by_default():
    planner = build_planner(config(kind="pipeline"), {})
    assert isinstance(planner._strategy, PipelineStrategy)


def test_builds_the_buy_and_hold_control():
    planner = build_planner(config(kind="buy_and_hold"), {})
    assert isinstance(planner._strategy, BuyAndHoldStrategy)


def test_an_unknown_kind_raises_and_names_the_options():
    with pytest.raises(DomainError) as e:
        build_planner(config(kind="neural_net"), {})
    assert e.value.type is ErrorType.BAD_ARGS
    assert "pipeline" in e.value.message


def test_parameters_select_the_signal():
    planner = build_planner(config(), {"signal": "moving_average_cross"})
    assert isinstance(planner._strategy._signals, MovingAverageCrossSignalGenerator)


def test_parameters_select_the_allocator():
    planner = build_planner(config(), {"allocator": "conviction_weighted"})
    assert isinstance(planner._strategy._allocator, ConvictionWeightedAllocator)


@pytest.mark.parametrize("parameters", [
    {"signal": "telepathy"},
    {"allocator": "vibes"},
])
def test_an_unknown_component_raises(parameters):
    with pytest.raises(DomainError) as e:
        build_planner(config(), parameters)
    assert e.value.type is ErrorType.BAD_ARGS


def test_risk_rules_run_caps_before_halts():
    # A halt empties the weights, so running it first would leave the caps
    # nothing to act on and hide whether they work.
    rules = build_planner(config(), {})._risk_rules
    assert isinstance(rules[0], PerPositionCapRiskRule)
    assert isinstance(rules[-1], HaltFlagRiskRule)


def test_a_string_parameter_is_accepted_like_a_number():
    # Parameters arrive from JSON, where a caller may well quote a number.
    planner = build_planner(config(), {"max_position": "0.1"})
    assert planner._risk_rules[0]._max == pytest.approx(0.1)


def test_a_nonsense_parameter_raises_rather_than_defaulting():
    with pytest.raises(DomainError) as e:
        build_planner(config(), {"max_position": "quite a lot"})
    assert e.value.type is ErrorType.BAD_ARGS
    assert "max_position" in e.value.message


def test_window_parameters_reach_the_feature_extractor():
    planner = build_planner(config(), {"momentum_window": 7})
    assert planner._strategy._features._momentum == 7
