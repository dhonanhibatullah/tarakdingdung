from tarakdingdung.domain.models.decision import Weight
from tarakdingdung.domain.models.market import Candle


def equal_weight(symbol_ids: list[str]) -> list[Weight]:
    if not symbol_ids:
        return []
    weight = 1.0 / len(symbol_ids)
    return [Weight(symbol_id=s, weight=weight) for s in symbol_ids]


def momentum_top_k(
    candles: dict[str, list[Candle]], top_k: int, lookback: int
) -> list[Weight]:
    scores: dict[str, float] = {}
    for symbol_id, series in candles.items():
        if len(series) < lookback + 1:
            continue
        past = series[-lookback - 1].close
        last = series[-1].close
        if past <= 0:
            continue
        scores[symbol_id] = float(last / past - 1)

    top = sorted(scores, key=lambda s: scores[s], reverse=True)[:top_k]
    if not top:
        return []
    weight = 1.0 / len(top)
    return [Weight(symbol_id=s, weight=weight) for s in top]
