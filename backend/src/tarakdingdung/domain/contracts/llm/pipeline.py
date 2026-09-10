from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tarakdingdung.domain.models.decision import Decision


@dataclass(frozen=True, slots=True)
class DecisionContext:
    universe_id: str
    as_of_ms: int
    universe: str
    approved_symbol_ids: list[str]
    candles: str
    news_summaries: str
    portfolio: str


@dataclass(frozen=True, slots=True)
class DecisionResult:
    decision: Decision | None
    held: bool
    traces: dict = field(default_factory=dict)


class DecisionMaker(ABC):
    @abstractmethod
    async def decide(self, context: DecisionContext) -> DecisionResult: ...
