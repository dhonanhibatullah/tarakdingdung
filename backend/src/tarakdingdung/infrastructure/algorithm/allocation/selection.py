from tarakdingdung.domain.models.algorithm import Signals
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.infrastructure.algorithm.shared.ordering import symbol_key


def selected(signals: Signals,
             max_positions: int | None) -> list[tuple[Symbol, float]]:
    """The symbols an allocator will hold, in a stable order.

    A zero signal is no opinion, so it is never a position. When a position
    limit applies, the strongest convictions win and ties break on symbol
    identity, keeping the choice reproducible.
    """
    held = [(s, v) for s, v in signals.scores.items() if v != 0.0]
    if max_positions is None:
        return sorted(held, key=lambda item: symbol_key(item[0]))
    ranked = sorted(held, key=lambda item: (-abs(item[1]), symbol_key(item[0])))
    return sorted(ranked[:max_positions], key=lambda item: symbol_key(item[0]))
