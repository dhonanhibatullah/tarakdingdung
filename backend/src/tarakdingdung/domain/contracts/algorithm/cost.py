from abc import ABC, abstractmethod
from decimal import Decimal


class CostModel(ABC):
    @abstractmethod
    def fee(self, notional: Decimal) -> Decimal: ...
