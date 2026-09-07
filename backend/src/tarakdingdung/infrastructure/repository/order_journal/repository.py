from uuid import UUID

from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.models.algorithm import PlannedOrder
from tarakdingdung.domain.models.execution import ExecutionResult, OrderState
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.order_journal import queries as q
from tarakdingdung.infrastructure.repository.shared.trading import planned_order_from_orm


class SqlAlchemyOrderJournalRepository(OrderJournalRepository):
    """The write-ahead journal in Postgres.

    ``write_planned`` commits on its own rather than joining a wider
    transaction: the record has to survive independently of whatever happens
    next, which is the entire reason it is written first.
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    async def write_planned(self, *, strategy_id: UUID, timestamp: int,
                            orders: tuple[PlannedOrder, ...]) -> None:
        if not orders:
            return
        async with self._db.session() as s:
            await s.execute(q.build_write_planned(
                strategy_id=strategy_id, timestamp=timestamp, orders=orders))
            await self._db.persist(s)

    async def write_execution(self, *, strategy_id: UUID, timestamp: int,
                              result: ExecutionResult) -> None:
        # The per-order verdicts are recorded through set_state; this is the
        # hook for an execution-level audit row once one is needed.
        return None

    async def read_unreconciled(self, *, strategy_id: UUID) -> tuple[PlannedOrder, ...]:
        async with self._db.session() as s:
            rows = (await s.execute(
                q.build_read_unreconciled(strategy_id))).scalars().all()
        return tuple(planned_order_from_orm(r) for r in rows)

    async def set_state(self, *, client_order_id: str, state: OrderState,
                        venue_order_id: str | None, reason: str | None) -> None:
        async with self._db.session() as s:
            await s.execute(q.build_set_state(
                client_order_id=client_order_id, state=state,
                venue_order_id=venue_order_id, reason=reason))
            await self._db.persist(s)
