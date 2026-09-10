from dataclasses import dataclass

from tarakdingdung.domain.models.error import DomainError, ErrorType


@dataclass(frozen=True, slots=True)
class Weight:
    symbol_id: str
    weight: float


@dataclass(frozen=True, slots=True)
class Decision:
    id: str
    universe_id: str
    as_of_ms: int
    weights: list[Weight]
    reasoning: str
    confidence: float
    traces: dict
    prompt: str
    raw_response: str
    status: str

    def __post_init__(self) -> None:
        if any(w.weight < 0 for w in self.weights):
            raise DomainError("weights must be non-negative", ErrorType.VALIDATION)
        if sum(w.weight for w in self.weights) > 1.0:
            raise DomainError("weights must sum to <= 1.0", ErrorType.VALIDATION)
