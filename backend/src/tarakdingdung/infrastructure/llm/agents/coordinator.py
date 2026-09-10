from tarakdingdung.domain.contracts.llm.completion import Completion
from tarakdingdung.infrastructure.llm.agents.base import PromptAgent

COORDINATOR_SYSTEM_PROMPT = (
    "You are a disciplined portfolio manager trading a spot crypto universe against IDR. "
    "You receive market analysis, news analysis, and the current portfolio. "
    "Decide target portfolio weights and respond with JSON only of the form "
    '{"weights": [{"symbol_id": "...", "weight": 0.5}], "reasoning": "...", "confidence": 0.8}. '
    "Rules:\n"
    "- Weights must be non-negative and sum to at most 1.0; the remainder stays in cash.\n"
    "- Minimize turnover. Only change a position when your conviction has changed "
    "materially. Prefer holding existing positions over reallocating. Do not churn the "
    "book every decision.\n"
    "- Concentrate in a small number (2 to 8) of high-conviction assets; do not spread "
    "thinly across the whole universe.\n"
    "- When signals are weak, mixed, or the market is range-bound, prefer cash and wait "
    "rather than guessing.\n"
    "- A weight of 0 means fully exit that position."
)

DECISION_JSON_SCHEMA = (
    '{"weights": [{"symbol_id": "string", "weight": 0.0}], "reasoning": "string", "confidence": 0.0}'
)


class CoordinatorAgent(PromptAgent):
    def __init__(self, completion: Completion) -> None:
        super().__init__(
            completion, COORDINATOR_SYSTEM_PROMPT, json_schema=DECISION_JSON_SCHEMA
        )
