from tarakdingdung.application.trading.backtest.historical import WeightFn
from tarakdingdung.domain.contracts.llm.pipeline import DecisionContext, DecisionMaker
from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.market import Candle


def make_llm_weight_fn(
    decision_maker: DecisionMaker, universe_id: str, symbol_ids: list[str], lookback: int = 10
) -> WeightFn:
    state: dict = {"weights": []}

    async def fn(candles: dict[str, list[Candle]], as_of_ms: int) -> list[Weight]:
        candle_lines: list[str] = []
        for sid in symbol_ids:
            series = [c for c in candles.get(sid, []) if c.open_time_ms <= as_of_ms]
            recent = series[-lookback:]
            closes = " ".join(str(c.close) for c in recent)
            candle_lines.append(f"{sid}: {closes}")

        if state["weights"]:
            portfolio_text = "current weights: " + ", ".join(
                f"{w.symbol_id}={w.weight:.2f}" for w in state["weights"]
            )
        else:
            portfolio_text = "cash only"

        context = DecisionContext(
            universe_id=universe_id,
            as_of_ms=as_of_ms,
            universe="\n".join(symbol_ids),
            approved_symbol_ids=symbol_ids,
            candles="\n".join(candle_lines),
            news_summaries="",
            portfolio=portfolio_text,
        )
        result = await decision_maker.decide(context)
        if result.decision is None:
            return []
        state["weights"] = result.decision.weights
        return result.decision.weights

    return fn
