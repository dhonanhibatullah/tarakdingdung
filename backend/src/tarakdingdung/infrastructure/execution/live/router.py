from collections.abc import Mapping

from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.models.algorithm import PlannedOrder
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import (
    ExecutionResult, UnconfirmedOrder,
)
from tarakdingdung.domain.models.market import Symbol, Venue


class RoutingExecutor(Executor):
    """Dispatches each order to the executor for its venue.

    A cycle can hold positions on both exchanges, so its plan is not addressed
    to a single venue. Splitting here keeps that fact out of the engine, which
    should not know how many venues exist.

    An order for a venue with no configured executor is reported *unconfirmed*
    rather than rejected. It is a misconfiguration, not a venue verdict, and
    marking it settled would let the engine forget an order it never truly
    resolved.
    """

    def __init__(self, executors: Mapping[Venue, Executor]) -> None:
        self._executors = executors

    async def submit(self, orders: tuple[PlannedOrder, ...]) -> ExecutionResult:
        accepted, rejected, unconfirmed, fills = [], [], [], []

        for venue, batch in _by_venue(orders).items():
            executor = self._executors.get(venue)
            if executor is None:
                unconfirmed.extend(
                    UnconfirmedOrder(order=order, client_order_id=order.client_order_id or "",
                                     reason=f"no executor configured for {venue}")
                    for order in batch)
                continue
            result = await executor.submit(tuple(batch))
            accepted.extend(result.accepted)
            rejected.extend(result.rejected)
            unconfirmed.extend(result.unconfirmed)
            fills.extend(result.fills)

        return ExecutionResult(accepted=tuple(accepted), rejected=tuple(rejected),
                               unconfirmed=tuple(unconfirmed), fills=tuple(fills))

    async def cancel_all(self, symbols: tuple[Symbol, ...]) -> None:
        failures = []
        for venue, batch in _by_venue_symbols(symbols).items():
            executor = self._executors.get(venue)
            if executor is None:
                continue
            try:
                await executor.cancel_all(tuple(batch))
            except DomainError as err:
                # Keep cancelling the other venues before surfacing: a halt
                # that stopped at the first failure would leave orders working
                # somewhere it could have reached.
                failures.append(err)
        if failures:
            raise failures[0]

    async def read_by_client_order_id(self, client_order_id: str, *,
                                      symbol: Symbol | None = None) -> ExecutionResult:
        raise DomainError("reconcile through the venue executor that placed the order",
                          ErrorType.UNIMPLEMENTED)


def _by_venue(orders: tuple[PlannedOrder, ...]) -> dict[Venue, list[PlannedOrder]]:
    grouped: dict[Venue, list[PlannedOrder]] = {}
    for order in orders:
        grouped.setdefault(order.symbol.venue, []).append(order)
    return grouped


def _by_venue_symbols(symbols: tuple[Symbol, ...]) -> dict[Venue, list[Symbol]]:
    grouped: dict[Venue, list[Symbol]] = {}
    for symbol in symbols:
        grouped.setdefault(symbol.venue, []).append(symbol)
    return grouped
