from tarakdingdung.domain.contracts.llm.agent import Agent
from tarakdingdung.domain.contracts.llm.completion import Completion, Message


class PromptAgent(Agent):
    def __init__(
        self,
        completion: Completion,
        system_prompt: str,
        *,
        json_schema: str | None = None,
    ) -> None:
        self._completion = completion
        self._system_prompt = system_prompt
        self._json_schema = json_schema

    async def analyze(self, context: str) -> str:
        messages = [
            Message(role="system", content=self._system_prompt),
            Message(role="user", content=context),
        ]
        return await self._completion.complete(messages, json_schema=self._json_schema)
