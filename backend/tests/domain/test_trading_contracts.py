import inspect

from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.contracts.repository.decision import DecisionRepository
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.news import NewsRepository
from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.symbol import SymbolRepository
from tarakdingdung.domain.contracts.repository.universe import UniverseRepository


def test_trading_repository_contracts_are_abstract():
    classes = (
        SymbolRepository,
        UniverseRepository,
        MarketDataRepository,
        NewsRepository,
        DecisionRepository,
        BacktestRepository,
        PortfolioRepository,
        OrderJournalRepository,
    )
    for cls in classes:
        assert inspect.isabstract(cls), cls.__name__
