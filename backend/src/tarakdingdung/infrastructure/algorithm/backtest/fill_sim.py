from decimal import Decimal

from tarakdingdung.domain.contracts.algorithm.backtest import (
    FillSimResult,
    FillSimulator,
    RebalanceEvent,
)
from tarakdingdung.domain.contracts.algorithm.cost import CostModel
from tarakdingdung.domain.contracts.algorithm.metric import Metric
from tarakdingdung.domain.contracts.algorithm.rebalance import Rebalancer
from tarakdingdung.domain.models.order import Fill


class SimpleFillSimulator(FillSimulator):
    def __init__(self, metric: Metric) -> None:
        self._metric = metric

    def simulate(
        self,
        events: list[RebalanceEvent],
        rebalancer: Rebalancer,
        cost_model: CostModel,
        initial_equity: Decimal,
    ) -> FillSimResult:
        cash = initial_equity
        holdings: dict[str, Decimal] = {}
        equity_curve: list[Decimal] = []
        fills: list[Fill] = []
        trade_values: list[Decimal] = []

        for event in events:
            current_values = {
                sym: holdings.get(sym, Decimal("0")) * event.prices[sym]
                for sym in holdings
                if sym in event.prices
            }
            equity = cash + sum(current_values.values(), Decimal("0"))

            plan = rebalancer.rebalance(
                current=current_values,
                target=event.target,
                prices=event.prices,
                equity=equity,
            )

            for i, order in enumerate(plan.orders):
                price = event.prices[order.symbol_id]
                notional = order.quantity * price
                fee = cost_model.fee(notional)
                if order.side.value == "buy":
                    cash -= notional + fee
                    holdings[order.symbol_id] = (
                        holdings.get(order.symbol_id, Decimal("0")) + order.quantity
                    )
                else:
                    cash += notional - fee
                    holdings[order.symbol_id] = (
                        holdings.get(order.symbol_id, Decimal("0")) - order.quantity
                    )
                trade_values.append(notional)
                fills.append(
                    Fill(
                        id=f"fill-{event.timestamp_ms}-{i}",
                        order_id=f"{event.timestamp_ms}:{order.symbol_id}:{order.side.value}",
                        price=price,
                        quantity=order.quantity,
                        fee=fee,
                        filled_at_ms=event.timestamp_ms,
                    )
                )

            final_values = {
                sym: holdings.get(sym, Decimal("0")) * event.prices[sym]
                for sym in holdings
                if sym in event.prices
            }
            equity_curve.append(cash + sum(final_values.values(), Decimal("0")))

        returns = [
            float((equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1])
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1] != 0
        ]

        return FillSimResult(
            equity_curve=equity_curve,
            fills=fills,
            sharpe=self._metric.sharpe(returns),
            max_drawdown=self._metric.max_drawdown(equity_curve),
            turnover=self._metric.turnover(trade_values),
        )
