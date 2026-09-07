import math
from collections.abc import Sequence
from itertools import combinations

from tarakdingdung.domain.contracts.algorithm.validation import OverfittingTest
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.performance import OverfittingReport, TrialResult
from tarakdingdung.infrastructure.algorithm.shared import statistics


class CombinatorialOverfittingTest(OverfittingTest):
    """Probability of Backtest Overfitting via combinatorially symmetric
    cross-validation.

    The method, and the ~10% rejection threshold, come from the FinRL-Crypto
    work that the research identifies as the one broadly transferable technique
    in the literature — more useful than any particular algorithm.

    How it works: the return series is cut into ``subsets`` equal blocks. For
    every way of choosing half the blocks as in-sample, the best in-sample
    trial is found and its rank among all trials *out-of-sample* is recorded.
    If selection carried real information, the in-sample winner should keep
    ranking well out-of-sample. PBO is the fraction of splits where it lands in
    the bottom half — that is, where picking the backtest winner was no better
    than picking at random.

    A high probability does not mean the strategy loses money. It means the
    *parameter search* learned the noise, so the reported performance is not
    evidence about the future.
    """

    def __init__(self, *, subsets: int = 8, threshold: float = 0.10) -> None:
        if subsets < 2 or subsets % 2 != 0:
            raise DomainError("subsets must be an even number of at least 2",
                              ErrorType.BAD_ARGS)
        self._subsets = subsets
        self._threshold = threshold

    def evaluate(self, trials: tuple[TrialResult, ...]) -> OverfittingReport:
        series = self._validated(trials)
        blocks = self._blocks(len(series[0]))

        indices = range(self._subsets)
        half = self._subsets // 2
        logits = []
        for chosen in combinations(indices, half):
            in_sample = [i for block in chosen for i in blocks[block]]
            out_sample = [i for block in indices if block not in chosen
                          for i in blocks[block]]
            logits.append(self._logit(series, in_sample, out_sample))

        probability = sum(1 for value in logits if value <= 0) / len(logits)
        return OverfittingReport(probability=probability,
                                 threshold=self._threshold,
                                 passed=probability < self._threshold)

    def _validated(self, trials: tuple[TrialResult, ...]) -> list[tuple[float, ...]]:
        if len(trials) < 2:
            raise DomainError(
                "overfitting testing needs at least two trials to rank",
                ErrorType.BAD_ARGS)
        lengths = {len(t.returns) for t in trials}
        if len(lengths) != 1:
            raise DomainError("trials must share one return-series length",
                              ErrorType.BAD_ARGS)
        length = lengths.pop()
        if length < self._subsets:
            raise DomainError(
                f"need at least {self._subsets} observations to form subsets, "
                f"got {length}", ErrorType.BAD_ARGS)
        return [t.returns for t in trials]

    def _blocks(self, length: int) -> list[range]:
        size, extra = divmod(length, self._subsets)
        blocks = []
        start = 0
        for index in range(self._subsets):
            # Spread the remainder over the leading blocks so none is empty.
            stop = start + size + (1 if index < extra else 0)
            blocks.append(range(start, stop))
            start = stop
        return blocks

    def _logit(self, series: list[tuple[float, ...]],
               in_sample: list[int], out_sample: list[int]) -> float:
        best = max(range(len(series)),
                   key=lambda t: self._score(series[t], in_sample))
        scores = [self._score(s, out_sample) for s in series]
        # Rank of the in-sample winner among all trials out-of-sample.
        rank = sum(1 for score in scores if score < scores[best])
        relative = (rank + 1) / (len(series) + 1)
        return math.log(relative / (1.0 - relative))

    def _score(self, returns: Sequence[float], indices: Sequence[int]) -> float:
        sample = [returns[i] for i in indices]
        dispersion = statistics.stdev(sample)
        if dispersion <= 0:
            return statistics.mean(sample)
        return statistics.mean(sample) / dispersion
