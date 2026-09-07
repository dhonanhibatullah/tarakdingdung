from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from tarakdingdung.domain.models.algorithm import PlannedOrder
from tarakdingdung.domain.models.execution import OrderState
from tarakdingdung.infrastructure.repository.database.orm import PlannedOrderORM
from tarakdingdung.infrastructure.repository.shared.trading import symbol_columns

O = PlannedOrderORM

# Everything still awaiting a verdict from the venue.
_UNRESOLVED = (OrderState.PENDING.value, OrderState.UNCONFIRMED.value)


def build_write_planned(*, strategy_id: UUID, timestamp: int,
                        orders: tuple[PlannedOrder, ...]):
    """Idempotent on ``client_order_id``.

    A cycle replayed after a crash journals the same ids. Doing nothing on
    conflict preserves whatever state the first attempt reached rather than
    resetting a resolved order back to pending.
    """
    rows = [{"strategy_id": strategy_id, "client_order_id": o.client_order_id,
             "planned_at": timestamp, **symbol_columns(o.symbol),
             "side": str(o.side), "type": str(o.type), "quantity": o.quantity,
             "price": o.price, "time_in_force": str(o.time_in_force)}
            for o in orders]
    statement = pg_insert(O).values(rows)
    return statement.on_conflict_do_nothing(
        constraint="uq_planned_orders_client_order_id")


def build_read_unreconciled(strategy_id: UUID) -> Select:
    return (select(O)
            .where(O.strategy_id == strategy_id, O.state.in_(_UNRESOLVED))
            .order_by(O.planned_at.asc()))


def build_set_state(*, client_order_id: str, state: OrderState,
                    venue_order_id: str | None, reason: str | None):
    return (update(O).where(O.client_order_id == client_order_id)
            .values(state=str(state), venue_order_id=venue_order_id, reason=reason))
