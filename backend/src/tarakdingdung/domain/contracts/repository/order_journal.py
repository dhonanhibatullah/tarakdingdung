from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.algorithm import PlannedOrder
from tarakdingdung.domain.models.execution import ExecutionResult, OrderState


class OrderJournalRepository(ABC):
    """The write-ahead record of every order the engine intended.

    Separate from ``PortfolioRepository`` because it is a log, not state: it
    answers "what did we try to do, and do we know whether it happened",
    which is a different question from "what do we hold".

    The ordering obligation lives with the caller but exists for this
    repository: planned orders are written *before* they are submitted, so a
    process that dies mid-submission leaves a record with no confirmation.
    That record is the only thing that makes the orders findable afterwards.
    """

    @abstractmethod
    async def write_planned(self, *, strategy_id: UUID, timestamp: int,
                            orders: tuple[PlannedOrder, ...]) -> None: ...

    @abstractmethod
    async def write_execution(self, *, strategy_id: UUID, timestamp: int,
                              result: ExecutionResult) -> None: ...

    @abstractmethod
    async def read_unreconciled(self, *, strategy_id: UUID) -> tuple[PlannedOrder, ...]:
        """Orders written but never confirmed accepted or rejected.

        The next cycle queries the venue for each by client order id rather
        than resubmitting: the order may already exist, and a blind retry is
        how one intended position becomes two.
        """
        ...

    @abstractmethod
    async def set_state(self, *, client_order_id: str, state: OrderState,
                        venue_order_id: str | None, reason: str | None) -> None: ...
