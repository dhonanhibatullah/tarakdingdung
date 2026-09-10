from abc import ABC, abstractmethod
from decimal import Decimal


class Metric(ABC):
    @abstractmethod
    def sharpe(self, returns: list[float]) -> float: ...

    @abstractmethod
    def max_drawdown(self, equity: list[Decimal]) -> float: ...

    @abstractmethod
    def turnover(self, trade_values: list[Decimal]) -> float: ...
