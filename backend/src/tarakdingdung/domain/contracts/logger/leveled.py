from abc import ABC, abstractmethod


class LeveledLogger(ABC):
    @abstractmethod
    def debug(self, message: str, **fields) -> None: ...

    @abstractmethod
    def info(self, message: str, **fields) -> None: ...

    @abstractmethod
    def warning(self, message: str, **fields) -> None: ...

    @abstractmethod
    def error(self, message: str, **fields) -> None: ...
