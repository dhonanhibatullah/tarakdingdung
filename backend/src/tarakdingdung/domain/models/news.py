from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NewsArticle:
    id: str
    source: str
    url: str
    title: str
    published_ms: int
    raw_text: str


@dataclass(frozen=True, slots=True)
class NewsAnalysis:
    id: str
    article_id: str
    summary: str
    sentiment: float


@dataclass(frozen=True, slots=True)
class NewsFeed:
    id: str
    name: str
    url: str
    enabled: bool = True
