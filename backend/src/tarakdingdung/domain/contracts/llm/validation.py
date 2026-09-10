from abc import ABC, abstractmethod
from dataclasses import dataclass

from tarakdingdung.domain.models.decision import Weight


@dataclass(frozen=True, slots=True)
class DecisionDraft:
    weights: list[Weight]
    reasoning: str
    confidence: float


class DecisionValidator(ABC):
    @abstractmethod
    def validate(self, raw: str) -> DecisionDraft: ...
