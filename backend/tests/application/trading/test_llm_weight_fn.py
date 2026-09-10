from decimal import Decimal

from tarakdingdung.application.trading.backtest.llm_weight_fn import make_llm_weight_fn
from tarakdingdung.domain.contracts.llm.pipeline import DecisionResult
from tarakdingdung.domain.models.decision import Decision, Weight
from tarakdingdung.domain.models.market import Candle


class FakeDecisionMaker:
    def __init__(self, decision=None, held=False) -> None:
        self.decision = decision
        self.held = held
        self.contexts = []

    async def decide(self, context):
        self.contexts.append(context)
        return DecisionResult(decision=self.decision, held=self.held)


def _candle(ts, close):
    return Candle(
        symbol_id="s1",
        open_time_ms=ts,
        open=Decimal(str(close)),
        high=Decimal(str(close)),
        low=Decimal(str(close)),
        close=Decimal(str(close)),
        volume=Decimal("1"),
    )


async def test_returns_decision_weights():
    decision = Decision(
        id="",
        universe_id="u1",
        as_of_ms=0,
        weights=[Weight(symbol_id="s1", weight=0.5)],
        reasoning="",
        confidence=0.5,
        traces={},
        prompt="",
        raw_response="",
        status="valid",
    )
    dm = FakeDecisionMaker(decision=decision)
    fn = make_llm_weight_fn(dm, "u1", ["s1"])

    candles = {"s1": [_candle(0, 10), _candle(1000, 20)]}
    weights = await fn(candles, 1500)

    assert weights == [Weight(symbol_id="s1", weight=0.5)]
    assert dm.contexts[0].universe_id == "u1"
    assert "s1" in dm.contexts[0].candles


async def test_returns_empty_on_hold():
    dm = FakeDecisionMaker(held=True)
    fn = make_llm_weight_fn(dm, "u1", ["s1"])
    weights = await fn({"s1": [_candle(0, 10)]}, 500)
    assert weights == []


async def test_no_lookahead():
    dm = FakeDecisionMaker(decision=None, held=True)
    fn = make_llm_weight_fn(dm, "u1", ["s1"], lookback=10)
    candles = {"s1": [_candle(0, 10), _candle(1000, 20), _candle(2000, 30)]}
    await fn(candles, 1500)
    context = dm.contexts[0]
    # only closes up to as_of_ms=1500 (candles at 0 and 1000) appear; 30 (at 2000) does not
    assert "30" not in context.candles
    assert "20" in context.candles
