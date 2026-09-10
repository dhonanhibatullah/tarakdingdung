import json

from pydantic import BaseModel, Field, model_validator

from tarakdingdung.domain.contracts.llm.validation import DecisionDraft, DecisionValidator
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.error import DomainError, ErrorType


class WeightSchema(BaseModel):
    symbol_id: str
    weight: float = Field(ge=0)


class DecisionSchema(BaseModel):
    weights: list[WeightSchema] = Field(default_factory=list)
    reasoning: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)

    @model_validator(mode="after")
    def _check_sum(self) -> "DecisionSchema":
        if sum(w.weight for w in self.weights) > 1.0:
            raise ValueError("weights sum exceeds 1.0")
        return self


class PydanticDecisionValidator(DecisionValidator):
    def validate(self, raw: str) -> DecisionDraft:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DomainError("decision is not valid JSON", ErrorType.VALIDATION) from exc

        try:
            parsed = DecisionSchema.model_validate(data)
        except Exception as exc:
            raise DomainError("decision failed validation", ErrorType.VALIDATION) from exc

        return DecisionDraft(
            weights=[Weight(symbol_id=w.symbol_id, weight=w.weight) for w in parsed.weights],
            reasoning=parsed.reasoning,
            confidence=parsed.confidence,
        )
