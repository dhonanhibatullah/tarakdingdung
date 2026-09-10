from tarakdingdung.domain.contracts.llm.completion import Completion
from tarakdingdung.infrastructure.llm.agents.base import PromptAgent

COORDINATOR_SYSTEM_PROMPT = (
    "You are a portfolio manager. Given market and news analysis plus the current "
    "portfolio, decide target portfolio weights. Respond with JSON only, of the form "
    '{"weights": [{"symbol_id": "...", "weight": 0.5}], "reasoning": "...", "confidence": 0.8}. '
    "Weights must be non-negative and sum to at most 1.0 (remainder is cash)."
)

DECISION_JSON_SCHEMA = (
    '{"weights": [{"symbol_id": "string", "weight": 0.0}], "reasoning": "string", "confidence": 0.0}'
)


class CoordinatorAgent(PromptAgent):
    def __init__(self, completion: Completion) -> None:
        super().__init__(
            completion, COORDINATOR_SYSTEM_PROMPT, json_schema=DECISION_JSON_SCHEMA
        )
