import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tarakdingdung.domain.contracts.repository.decision import DecisionRepository
from tarakdingdung.domain.models.decision import Decision, Weight
from tarakdingdung.infrastructure.repository.database.orm import DecisionRow


def _weights_to_json(weights: list[Weight]) -> list[dict]:
    return [{"symbol_id": w.symbol_id, "weight": w.weight} for w in weights]


def _weights_from_json(data: list[dict]) -> list[Weight]:
    return [Weight(symbol_id=w["symbol_id"], weight=float(w["weight"])) for w in data]


def _to_domain(row: DecisionRow) -> Decision:
    return Decision(
        id=row.id,
        universe_id=row.universe_id,
        as_of_ms=row.as_of_ms,
        weights=_weights_from_json(row.weights),
        reasoning=row.reasoning,
        confidence=row.confidence,
        traces=row.traces,
        prompt=row.prompt,
        raw_response=row.raw_response,
        status=row.status,
    )


class SqlAlchemyDecisionRepository(DecisionRepository):
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def create(self, entity: Decision) -> Decision:
        id_ = entity.id or str(uuid.uuid4())
        async with self._sessions() as session:
            session.add(
                DecisionRow(
                    id=id_,
                    universe_id=entity.universe_id,
                    as_of_ms=entity.as_of_ms,
                    weights=_weights_to_json(entity.weights),
                    reasoning=entity.reasoning,
                    confidence=entity.confidence,
                    traces=entity.traces,
                    prompt=entity.prompt,
                    raw_response=entity.raw_response,
                    status=entity.status,
                )
            )
            await session.commit()
        return Decision(
            id=id_, universe_id=entity.universe_id, as_of_ms=entity.as_of_ms,
            weights=entity.weights, reasoning=entity.reasoning,
            confidence=entity.confidence, traces=entity.traces, prompt=entity.prompt,
            raw_response=entity.raw_response, status=entity.status,
        )

    async def read_by_id(self, id: str) -> Decision | None:
        async with self._sessions() as session:
            row = await session.get(DecisionRow, id)
            return _to_domain(row) if row else None

    async def read_latest(self, universe_id: str) -> Decision | None:
        async with self._sessions() as session:
            stmt = (
                select(DecisionRow)
                .where(DecisionRow.universe_id == universe_id)
                .order_by(DecisionRow.as_of_ms.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return _to_domain(row) if row else None

    async def read_range(
        self, universe_id: str, from_ms: int, to_ms: int
    ) -> list[Decision]:
        async with self._sessions() as session:
            stmt = (
                select(DecisionRow)
                .where(
                    DecisionRow.universe_id == universe_id,
                    DecisionRow.as_of_ms >= from_ms,
                    DecisionRow.as_of_ms <= to_ms,
                )
                .order_by(DecisionRow.as_of_ms)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_domain(r) for r in rows]
