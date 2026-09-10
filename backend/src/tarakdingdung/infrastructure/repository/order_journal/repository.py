import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.order_journal import OrderJournalRepository
from tarakdingdung.domain.models.order import (
    Fill,
    Order,
    OrderSide,
    OrderStatus,
)
from tarakdingdung.infrastructure.repository.database.orm import FillRow, OrderRow


def _order_to_domain(row: OrderRow) -> Order:
    return Order(
        id=row.id,
        client_order_id=row.client_order_id,
        symbol_id=row.symbol_id,
        side=OrderSide(row.side),
        price=row.price,
        quantity=row.quantity,
        status=OrderStatus(row.status),
        created_at_ms=row.created_at_ms,
    )


def _fill_to_domain(row: FillRow) -> Fill:
    return Fill(
        id=row.id,
        order_id=row.order_id,
        price=row.price,
        quantity=row.quantity,
        fee=row.fee,
        filled_at_ms=row.filled_at_ms,
    )


class SqlAlchemyOrderJournalRepository(OrderJournalRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: Order) -> Order:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(
                OrderRow(
                    id=id_,
                    client_order_id=entity.client_order_id,
                    symbol_id=entity.symbol_id,
                    side=entity.side.value,
                    price=entity.price,
                    quantity=entity.quantity,
                    status=entity.status.value,
                    created_at_ms=entity.created_at_ms,
                )
            )
            await session.commit()
        return Order(
            id=id_, client_order_id=entity.client_order_id, symbol_id=entity.symbol_id,
            side=entity.side, price=entity.price, quantity=entity.quantity,
            status=entity.status, created_at_ms=entity.created_at_ms,
        )

    async def read_by_id(self, id: str) -> Order | None:
        async with self._sessions() as session:
            row = await session.get(OrderRow, id)
            return _order_to_domain(row) if row else None

    async def read_by_client_order_id(self, client_order_id: str) -> Order | None:
        async with self._sessions() as session:
            stmt = select(OrderRow).where(OrderRow.client_order_id == client_order_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _order_to_domain(row) if row else None

    async def update_status(self, id: str, status: OrderStatus) -> Order | None:
        async with self._sessions() as session:
            row = await session.get(OrderRow, id)
            if row is None:
                return None
            row.status = status.value
            await session.commit()
            await session.refresh(row)
            return _order_to_domain(row)

    async def append_fills(self, order_id: str, fills: list[Fill]) -> None:
        if not fills:
            return
        async with self._sessions() as session:
            for f in fills:
                session.add(
                    FillRow(
                        id=f.id or str(uuid.uuid4()),
                        order_id=order_id,
                        price=f.price,
                        quantity=f.quantity,
                        fee=f.fee,
                        filled_at_ms=f.filled_at_ms,
                    )
                )
            await session.commit()

    async def read_unreconciled(self) -> list[Order]:
        async with self._sessions() as session:
            stmt = select(OrderRow).where(
                OrderRow.status == OrderStatus.UNCONFIRMED.value
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_order_to_domain(r) for r in rows]
