from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.news import NewsRepository
from tarakdingdung.domain.contracts.repository.universe import UniverseRepository
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.news import NewsAnalysis, NewsArticle
from tarakdingdung.domain.models.symbol import (
    MembershipState,
    Symbol,
    Universe,
    UniverseMembership,
)


class InMemoryUniverseRepository(UniverseRepository):
    def __init__(self, approved_symbols=None, memberships=None) -> None:
        self.approved_symbols = approved_symbols or []
        self.memberships = memberships or []

    async def create(self, entity: Universe) -> Universe:
        return entity

    async def read_by_id(self, id: str) -> Universe | None:
        return None

    async def read_by_name(self, name: str) -> Universe | None:
        return None

    async def read_memberships(self, universe_id: str) -> list[UniverseMembership]:
        return self.memberships

    async def add_membership(self, entity: UniverseMembership) -> UniverseMembership:
        self.memberships.append(entity)
        return entity

    async def update_membership(
        self, universe_id: str, symbol_id: str, state: MembershipState, rationale: str = ""
    ) -> UniverseMembership | None:
        return None

    async def read_symbols_by_state(
        self, universe_id: str, state: MembershipState
    ) -> list[Symbol]:
        return self.approved_symbols


class InMemoryMarketDataRepository(MarketDataRepository):
    def __init__(self) -> None:
        self.candles: list[Candle] = []

    async def append_candles(self, candles: list[Candle]) -> None:
        self.candles.extend(candles)

    async def read_range(self, symbol_id: str, from_ms: int, to_ms: int) -> list[Candle]:
        return [c for c in self.candles if c.symbol_id == symbol_id]

    async def read_latest(self, symbol_id: str) -> Candle | None:
        return None

    async def read_coverage(self, symbol_id: str) -> tuple[int, int] | None:
        return None


class InMemoryNewsRepository(NewsRepository):
    def __init__(self) -> None:
        self.articles: list[NewsArticle] = []
        self.analyses: list[NewsAnalysis] = []

    async def create(self, entity: NewsArticle) -> NewsArticle:
        self.articles.append(entity)
        return entity

    async def create_analysis(self, entity: NewsAnalysis) -> NewsAnalysis:
        self.analyses.append(entity)
        return entity

    async def read_recent(self, from_ms: int) -> list[NewsArticle]:
        return self.articles

    async def read_analyses(self, from_ms: int) -> list[NewsAnalysis]:
        return self.analyses
