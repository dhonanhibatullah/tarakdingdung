from abc import ABC, abstractmethod

from tarakdingdung.domain.models.algorithm import PlannedOrder
from tarakdingdung.domain.models.execution import ExecutionResult
from tarakdingdung.domain.models.market import Symbol


class Executor(ABC):
    """Sends orders somewhere — a real venue, or a simulation of one.

    Paper and live implementations must agree on this contract, because
    promoting a strategy from paper to live rests on the two behaving the same.

    Obligations on every implementation:

    - every submitted order appears exactly once across the result's
      ``accepted``, ``rejected`` and ``unconfirmed``; an order that vanished
      from the result is one nothing will ever reconcile;
    - a submission whose outcome is unknown is reported ``unconfirmed`` rather
      than guessed at, and is never retried internally;
    - resubmitting a client order id that already exists yields one order, not
      two.
    """

    @abstractmethod
    async def submit(self, orders: tuple[PlannedOrder, ...]) -> ExecutionResult: ...

    @abstractmethod
    async def cancel_all(self, symbols: tuple[Symbol, ...]) -> None:
        """Pull every resting order for these symbols.

        Called when a risk rule trips, and the reason ``Executor`` owns it
        rather than the engine reaching into an API client: a halt that only
        stopped placing new orders would leave the existing ones working.
        """
        ...

    @abstractmethod
    async def read_by_client_order_id(self, client_order_id: str) -> ExecutionResult:
        """Reconciliation path for an unconfirmed submission."""
        ...
