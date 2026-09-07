import math
from collections.abc import Sequence


def simple_returns(values: Sequence[float]) -> tuple[float, ...]:
    """Period-over-period returns. Periods with a non-positive base are
    skipped rather than producing an infinity."""
    out: list[float] = []
    for previous, current in zip(values, values[1:]):
        if previous > 0:
            out.append(current / previous - 1.0)
    return tuple(out)


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stdev(values: Sequence[float]) -> float:
    """Population standard deviation; zero for fewer than two observations."""
    if len(values) < 2:
        return 0.0
    average = mean(values)
    variance = sum((v - average) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def downside_stdev(values: Sequence[float], target: float = 0.0) -> float:
    """Dispersion of the losing periods only — the denominator of Sortino.

    Divided by the full period count, not by the number of losses, so that a
    strategy with few but severe drawdowns is not flattered.
    """
    if len(values) < 2:
        return 0.0
    shortfalls = [min(0.0, v - target) ** 2 for v in values]
    return math.sqrt(sum(shortfalls) / len(values))


def annualised_ratio(returns: Sequence[float], dispersion: float,
                     periods_per_year: float) -> float:
    """Mean over dispersion, scaled to a year.

    Zero dispersion returns zero rather than infinity: a strategy that never
    moved has no risk-adjusted return to report, and an infinity here would
    propagate into a report that reads as spectacular.
    """
    if not returns or dispersion <= 0:
        return 0.0
    return mean(returns) / dispersion * math.sqrt(periods_per_year)


def max_drawdown(values: Sequence[float]) -> float:
    """Deepest peak-to-trough fall, as a positive fraction."""
    peak = float("-inf")
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst
