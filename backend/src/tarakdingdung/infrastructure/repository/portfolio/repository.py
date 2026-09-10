import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.models.portfolio import Balance, PortfolioSnapshot
from tarakdingdung.infrastructure.repository.database.orm import BalanceRow, PortfolioSnapshotRow


def _snapshot_to_domain(row: PortfolioSnapshotRow) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        id=row.id, venue=row.venue, as_of_ms=row.as_of_ms, equity=row.equity
    )


def _balance_to_domain(row: BalanceRow) -> Balance:
    return Balance(
        snapshot_id=row.snapshot_id, asset=row.asset, free=row.free, locked=row.locked
    )


class SqlAlchemyPortfolioRepository(PortfolioRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create_snapshot(
        self, snapshot: PortfolioSnapshot, balances: list[Balance]
    ) -> PortfolioSnapshot:
        id_ = snapshot.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(
                PortfolioSnapshotRow(
                    id=id_, venue=snapshot.venue, as_of_ms=snapshot.as_of_ms,
                    equity=snapshot.equity,
                )
            )
            await session.flush()
            for b in balances:
                session.add(
                    BalanceRow(
                        snapshot_id=id_, asset=b.asset, free=b.free, locked=b.locked
                    )
                )
            await session.commit()
        return PortfolioSnapshot(
            id=id_, venue=snapshot.venue, as_of_ms=snapshot.as_of_ms, equity=snapshot.equity
        )

    async def read_latest(self, venue: str) -> PortfolioSnapshot | None:
        async with self._sessions() as session:
            stmt = (
                select(PortfolioSnapshotRow)
                .where(PortfolioSnapshotRow.venue == venue)
                .order_by(PortfolioSnapshotRow.as_of_ms.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _snapshot_to_domain(row) if row else None

    async def read_balances(self, snapshot_id: str) -> list[Balance]:
        async with self._sessions() as session:
            stmt = select(BalanceRow).where(BalanceRow.snapshot_id == snapshot_id)
            rows = (await session.execute(stmt)).scalars().all()
            return [_balance_to_domain(r) for r in rows]
