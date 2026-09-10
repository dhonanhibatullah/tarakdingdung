from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def now_ms(self) -> int: ...
