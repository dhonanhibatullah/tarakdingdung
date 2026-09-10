import json

from tarakdingdung.domain.contracts.llm.completion import Completion, Message
from tarakdingdung.domain.contracts.repository.news import NewsRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.news import NewsAnalysis
from tarakdingdung.domain.usecases.trading.news_summarize import NewsSummarizer

NEWS_SUMMARIZE_PROMPT = (
    "You are a crypto news analyst. Summarize the provided headlines into a concise "
    "digest of what matters for trading, and rate overall market sentiment from -1.0 "
    "(very bearish) to 1.0 (very bullish). Respond with JSON only: "
    '{"summary": "...", "sentiment": 0.0}.'
)


class NewsSummarizerUsecase(NewsSummarizer):
    def __init__(
        self,
        completion: Completion,
        news: NewsRepository,
        clock: Clock,
        lookback_ms: int = 86_400_000,
        max_articles: int = 30,
    ) -> None:
        self._completion = completion
        self._news = news
        self._clock = clock
        self._lookback_ms = lookback_ms
        self._max_articles = max_articles

    async def summarize(self) -> NewsAnalysis | None:
        articles = await self._news.read_recent(self._clock.now_ms() - self._lookback_ms)
        if not articles:
            return None

        text = "\n".join(
            f"- {a.title}: {a.raw_text[:300]}" for a in articles[: self._max_articles]
        )
        raw = await self._completion.complete(
            [Message(role="system", content=NEWS_SUMMARIZE_PROMPT), Message(role="user", content=text)],
            json_schema='{"summary": "string", "sentiment": 0.0}',
        )
        data = json.loads(raw)
        sentiment = max(-1.0, min(1.0, float(data.get("sentiment", 0.0))))
        return await self._news.create_analysis(
            NewsAnalysis(
                id="",
                article_id=articles[0].id,
                summary=str(data.get("summary", "")),
                sentiment=sentiment,
            )
        )
