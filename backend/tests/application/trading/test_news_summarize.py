from tarakdingdung.application.trading.news_summarize.usecase import (
    NewsSummarizerUsecase,
)
from tarakdingdung.domain.models.news import NewsArticle
from tests.fakes.trading import InMemoryNewsRepository


class FakeClock:
    def now_ms(self) -> int:
        return 2000


class FakeCompletion:
    def __init__(self, response='{"summary": "digest", "sentiment": 0.7}') -> None:
        self.response = response

    async def complete(self, messages, *, json_schema=None):
        return self.response


async def test_summarize_returns_analysis():
    news = InMemoryNewsRepository()
    news.articles.append(
        NewsArticle(id="a1", source="s", url="u", title="t", published_ms=1500, raw_text="x")
    )
    usecase = NewsSummarizerUsecase(FakeCompletion(), news, FakeClock())
    result = await usecase.summarize()
    assert result is not None
    assert result.summary == "digest"
    assert result.sentiment == 0.7
    assert len(news.analyses) == 1


async def test_summarize_skips_when_no_articles():
    news = InMemoryNewsRepository()
    usecase = NewsSummarizerUsecase(FakeCompletion(), news, FakeClock())
    result = await usecase.summarize()
    assert result is None


async def test_summarize_clamps_sentiment():
    news = InMemoryNewsRepository()
    news.articles.append(
        NewsArticle(id="a1", source="s", url="u", title="t", published_ms=1500, raw_text="x")
    )
    usecase = NewsSummarizerUsecase(
        FakeCompletion('{"summary": "d", "sentiment": 9.0}'), news, FakeClock()
    )
    result = await usecase.summarize()
    assert result.sentiment == 1.0
