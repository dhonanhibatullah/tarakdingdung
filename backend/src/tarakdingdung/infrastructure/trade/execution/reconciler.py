from tarakdingdung.domain.contracts.trade.exchange import Exchange
from tarakdingdung.domain.contracts.trade.reconciler import Reconciler, ReconcileResult
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.order import Order, OrderStatus
from tarakdingdung.domain.models.symbol import Symbol


class StandardReconciler(Reconciler):
    def __init__(self, exchange: Exchange) -> None:
        self._exchange = exchange

    async def reconcile(
        self, orders: list[Order], symbols: dict[str, Symbol]
    ) -> ReconcileResult:
        resolved: list[tuple[str, OrderStatus]] = []
        still_unconfirmed: list[str] = []

        for order in orders:
            symbol = symbols.get(order.symbol_id)
            if symbol is None:
                still_unconfirmed.append(order.client_order_id)
                continue
            try:
                result = await self._exchange.get_order(symbol, order.client_order_id)
                status = (
                    OrderStatus.FILLED
                    if result.status.upper() in ("FILLED", "PARTIALLY_FILLED")
                    else OrderStatus.SUBMITTED
                )
                resolved.append((order.client_order_id, status))
            except DomainError as exc:
                if exc.error_type is ErrorType.NOT_FOUND:
                    resolved.append((order.client_order_id, OrderStatus.REJECTED))
                else:
                    still_unconfirmed.append(order.client_order_id)
            except Exception:
                still_unconfirmed.append(order.client_order_id)

        return ReconcileResult(
            resolved=resolved, still_unconfirmed=still_unconfirmed
        )
