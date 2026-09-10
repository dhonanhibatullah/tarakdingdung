from abc import ABC, abstractmethod


class Agent(ABC):
    @abstractmethod
    async def analyze(self, context: str) -> str: ...
