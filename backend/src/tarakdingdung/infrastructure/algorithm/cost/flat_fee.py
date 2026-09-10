from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.cost import CostModel


class FlatFee(CostModel):
    def __init__(self, rate: Decimal) -> None:
        self._rate = rate

    def fee(self, notional: Decimal) -> Decimal:
        return notional * self._rate
