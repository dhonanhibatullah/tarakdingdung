from abc import ABC, abstractmethod


class Clock(ABC):
    """Wall-clock time, injected rather than read.

    The live engine takes one; the backtester never does, because its time
    comes from the snapshots it replays. That separation is what makes a
    backtest a function of stored data alone, which in turn is what makes the
    overfitting gate meaningful rather than a measurement of scheduling noise.
    """

    @abstractmethod
    async def now_ms(self) -> int: ...
