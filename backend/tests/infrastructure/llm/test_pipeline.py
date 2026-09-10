from tarakdingdung.domain.contracts.llm.pipeline import DecisionContext
from tarakdingdung.infrastructure.llm.agents.coordinator import CoordinatorAgent
from tarakdingdung.infrastructure.llm.agents.market import MarketAgent
from tarakdingdung.infrastructure.llm.agents.news import NewsAgent
from tarakdingdung.infrastructure.llm.pipeline import MultiAgentPipeline
from tarakdingdung.infrastructure.llm.validation import PydanticDecisionValidator


class FakeCompletion:
    def __init__(self, responses) -> None:
        self._responses = list(responses)
        self._calls = 0

    async def complete(self, messages, *, json_schema=None):
        idx = min(self._calls, len(self._responses) - 1)
        self._calls += 1
        return self._responses[idx]


def _context(approved=("s1", "s2")):
    return DecisionContext(
        universe_id="u1",
        as_of_ms=1000,
        universe="s1 BTC/IDR, s2 ETH/IDR",
        approved_symbol_ids=list(approved),
        candles="candle data",
        news_summaries="news data",
        portfolio="cash only",
    )


def _pipeline(market_resp="market ok", news_resp="news ok", coordinator_responses=("{}",)):
    market = MarketAgent(FakeCompletion([market_resp]))
    news = NewsAgent(FakeCompletion([news_resp]))
    coordinator = CoordinatorAgent(FakeCompletion(coordinator_responses))
    return MultiAgentPipeline(market, news, coordinator, PydanticDecisionValidator())


async def test_decide_produces_weights():
    pipeline = _pipeline(
        coordinator_responses=(
            '{"weights": [{"symbol_id": "s1", "weight": 0.6}], "reasoning": "bullish", "confidence": 0.9}',
        )
    )
    result = await pipeline.decide(_context())
    assert result.held is False
    assert result.decision is not None
    assert result.decision.weights[0].symbol_id == "s1"
    assert result.decision.reasoning == "bullish"
    assert result.decision.status == "valid"


async def test_decide_filters_hallucinated_symbols():
    pipeline = _pipeline(
        coordinator_responses=(
            '{"weights": [{"symbol_id": "s1", "weight": 0.4}, {"symbol_id": "ghost", "weight": 0.3}]}',
        )
    )
    result = await pipeline.decide(_context())
    assert result.held is False
    assert [w.symbol_id for w in result.decision.weights] == ["s1"]


async def test_decide_retries_then_holds():
    pipeline = _pipeline(
        coordinator_responses=("not json", "still bad", "nope")
    )
    result = await pipeline.decide(_context())
    assert result.held is True
    assert result.decision is None


async def test_decide_recovers_after_retry():
    pipeline = _pipeline(
        coordinator_responses=(
            "not json",
            '{"weights": [{"symbol_id": "s2", "weight": 0.5}]}',
        )
    )
    result = await pipeline.decide(_context())
    assert result.held is False
    assert [w.symbol_id for w in result.decision.weights] == ["s2"]
