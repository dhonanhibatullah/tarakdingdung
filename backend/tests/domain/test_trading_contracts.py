import inspect

import pytest

from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight
from tarakdingdung.domain.usecases.trading.backtest import Backtesting
from tarakdingdung.domain.usecases.trading.collection import MarketDataCollection
from tarakdingdung.domain.usecases.trading.engine import CycleDecision, TradingEngine
from tarakdingdung.domain.usecases.trading.history import MarketDataHistory
from tarakdingdung.domain.usecases.trading.portfolio import PortfolioSync
from tarakdingdung.domain.usecases.trading.strategy import StrategyManagement
from tarakdingdung.domain.usecases.trading.validation import StrategyValidation

CONTRACTS = [
    MarketDataRepository, StrategyRepository, BacktestRepository,
    PortfolioRepository, OrderJournalRepository, Executor, Clock, SingleFlight,
]

USECASES = [
    MarketDataCollection, MarketDataHistory, StrategyManagement, Backtesting,
    StrategyValidation, PortfolioSync, TradingEngine,
]


@pytest.mark.parametrize("cls", CONTRACTS + USECASES, ids=lambda c: c.__name__)
def test_cannot_instantiate_abc(cls):
    with pytest.raises(TypeError):
        cls()


@pytest.mark.parametrize("cls", CONTRACTS + USECASES, ids=lambda c: c.__name__)
def test_every_method_is_abstract_and_async(cls):
    # These sit on the async side of the layer: they do I/O, unlike the
    # algorithm blocks, and the signature should say so.
    assert cls.__abstractmethods__
    for name in cls.__abstractmethods__:
        assert inspect.iscoroutinefunction(getattr(cls, name)), name


@pytest.mark.parametrize("cls", USECASES, ids=lambda c: c.__name__)
def test_usecases_declare_only_abstract_methods(cls):
    assert {n for n in vars(cls) if not n.startswith("_")} == set(cls.__abstractmethods__)


def test_engine_has_a_decision_for_every_outcome():
    # Each is a distinct operational answer to "why did nothing happen".
    assert {d.value for d in CycleDecision} == {
        "TRADED", "NO_DRIFT", "HALTED", "NO_DATA", "DISABLED", "SKIPPED", "DRY_RUN",
    }
