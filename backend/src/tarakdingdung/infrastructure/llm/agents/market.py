from tarakdingdung.domain.contracts.llm.completion import Completion
from tarakdingdung.infrastructure.llm.agents.base import PromptAgent

MARKET_SYSTEM_PROMPT = (
    "You are a crypto market analyst. Given recent candle data, identify trends, "
    "momentum, and volatility. Be concise and factual."
)


class MarketAgent(PromptAgent):
    def __init__(self, completion: Completion) -> None:
        super().__init__(completion, MARKET_SYSTEM_PROMPT)
