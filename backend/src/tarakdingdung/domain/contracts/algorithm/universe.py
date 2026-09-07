from abc import ABC, abstractmethod

from tarakdingdung.domain.models.market import MarketSnapshot, Symbol


class UniverseSelector(ABC):
    """Decides which symbols are eligible to hold at this instant.

    Kept apart from conviction: this answers "may I trade it" — listed, liquid
    enough, book deep enough — and never "do I want to". The pinned v1 symbol
    universe becomes an implementation of this rather than a constant buried
    inside a strategy.
    """

    @abstractmethod
    def select(self, snapshot: MarketSnapshot) -> tuple[Symbol, ...]: ...
