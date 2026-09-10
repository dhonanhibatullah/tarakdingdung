from tarakdingdung.domain.contracts.llm.completion import Completion
from tarakdingdung.infrastructure.llm.agents.base import PromptAgent

NEWS_SYSTEM_PROMPT = (
    "You are a crypto news analyst. Given news summaries, assess sentiment and "
    "material risks. Be concise and factual."
)


class NewsAgent(PromptAgent):
    def __init__(self, completion: Completion) -> None:
        super().__init__(completion, NEWS_SYSTEM_PROMPT)
