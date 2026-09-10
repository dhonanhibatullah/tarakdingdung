from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.rebalance import (
    OrderPlan,
    PlannedOrder,
    Rebalancer,
    Rejection,
)
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.order import OrderSide


class NoTradeBandRebalancer(Rebalancer):
    def __init__(self, band: float, min_notional: Decimal) -> None:
        self._band = band
        self._min_notional = min_notional

    def rebalance(
        self,
        current: dict[str, Decimal],
        target: list[Weight],
        prices: dict[str, Decimal],
        equity: Decimal,
    ) -> OrderPlan:
        target_by_symbol = {w.symbol_id: w.weight for w in target}
        symbols = sorted(set(current) | set(target_by_symbol))
        band_value = Decimal(str(self._band)) * equity

        orders: list[PlannedOrder] = []
        rejected: list[Rejection] = []
        for sym in symbols:
            target_weight = target_by_symbol.get(sym, 0.0)
            current_value = current.get(sym, Decimal("0"))
            target_value = Decimal(str(target_weight)) * equity
            delta = target_value - current_value

            if abs(delta) < band_value:
                continue

            price = prices.get(sym)
            if price is None or price <= 0:
                rejected.append(Rejection(symbol_id=sym, reason="no price"))
                continue

            notional = abs(delta)
            if notional < self._min_notional:
                rejected.append(Rejection(symbol_id=sym, reason="below min notional"))
                continue

            side = OrderSide.BUY if delta > 0 else OrderSide.SELL
            orders.append(
                PlannedOrder(
                    symbol_id=sym,
                    side=side,
                    quantity=notional / price,
                    notional=notional,
                )
            )

        return OrderPlan(orders=orders, rejected=rejected)
