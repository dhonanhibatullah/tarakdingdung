import inspect

import pytest

from tarakdingdung.domain.contracts.algorithm.allocation import Allocator
from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.contracts.algorithm.feature import FeatureExtractor
from tarakdingdung.domain.contracts.algorithm.metric import PerformanceEvaluator
from tarakdingdung.domain.contracts.algorithm.order import OrderPlanner
from tarakdingdung.domain.contracts.algorithm.rebalance import Rebalancer
from tarakdingdung.domain.contracts.algorithm.risk import RiskRule
from tarakdingdung.domain.contracts.algorithm.signal import SignalGenerator
from tarakdingdung.domain.contracts.algorithm.strategy import Strategy
from tarakdingdung.domain.contracts.algorithm.universe import UniverseSelector
from tarakdingdung.domain.contracts.algorithm.validation import OverfittingTest

ALL = [UniverseSelector, FeatureExtractor, SignalGenerator, Allocator, RiskRule,
       Rebalancer, OrderPlanner, CostModel, PerformanceEvaluator, OverfittingTest,
       Strategy]

METHODS = {
    UniverseSelector: {"select"},
    FeatureExtractor: {"compute"},
    SignalGenerator: {"generate"},
    Allocator: {"allocate"},
    RiskRule: {"apply"},
    Rebalancer: {"plan"},
    OrderPlanner: {"plan"},
    CostModel: {"estimate"},
    PerformanceEvaluator: {"evaluate"},
    OverfittingTest: {"evaluate"},
    Strategy: {"decide"},
}


@pytest.mark.parametrize("cls", ALL)
def test_cannot_instantiate_abc(cls):
    with pytest.raises(TypeError):
        cls()


@pytest.mark.parametrize("cls", ALL)
def test_declares_exactly_its_expected_methods(cls):
    assert {n for n in vars(cls) if not n.startswith("_")} == METHODS[cls]


@pytest.mark.parametrize("cls", ALL)
def test_every_method_is_abstract(cls):
    assert cls.__abstractmethods__ == frozenset(METHODS[cls])


@pytest.mark.parametrize("cls", ALL)
def test_blocks_are_synchronous(cls):
    # The blocks are pure computation; a coroutine signature here would mean
    # something in the layer had acquired the ability to do I/O.
    for name in METHODS[cls]:
        assert not inspect.iscoroutinefunction(getattr(cls, name))
