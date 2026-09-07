import random

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.performance import TrialResult
from tarakdingdung.infrastructure.algorithm.validation.combinatorial import (
    CombinatorialOverfittingTest,
)


def trial(label: str, returns) -> TrialResult:
    return TrialResult(label=label, parameters={"n": label}, returns=tuple(returns))


def test_rejects_a_pure_noise_search():
    """Trials that are all noise have no real winner, so the in-sample best
    should rank no better than chance out-of-sample."""
    rng = random.Random(7)
    trials = tuple(trial(str(i), [rng.gauss(0, 0.02) for _ in range(240)])
                   for i in range(20))
    report = CombinatorialOverfittingTest(subsets=8).evaluate(trials)
    assert report.passed is False
    assert report.probability > 0.10


def test_passes_when_one_trial_is_genuinely_better_throughout():
    """A trial with a real, stable edge keeps winning out-of-sample, which is
    what a low overfitting probability is supposed to mean."""
    rng = random.Random(11)
    noise = [trial(str(i), [rng.gauss(0, 0.02) for _ in range(240)])
             for i in range(9)]
    winner = trial("winner", [rng.gauss(0.02, 0.002) for _ in range(240)])
    report = CombinatorialOverfittingTest(subsets=8).evaluate((winner, *noise))
    assert report.probability < 0.10
    assert report.passed is True


def test_probability_is_a_probability():
    rng = random.Random(3)
    trials = tuple(trial(str(i), [rng.gauss(0, 0.01) for _ in range(120)])
                   for i in range(6))
    report = CombinatorialOverfittingTest(subsets=6).evaluate(trials)
    assert 0.0 <= report.probability <= 1.0
    assert report.threshold == 0.10


def test_threshold_is_configurable_and_decides_the_verdict():
    rng = random.Random(5)
    trials = tuple(trial(str(i), [rng.gauss(0, 0.01) for _ in range(120)])
                   for i in range(6))
    lenient = CombinatorialOverfittingTest(subsets=6, threshold=1.0).evaluate(trials)
    strict = CombinatorialOverfittingTest(subsets=6, threshold=0.0).evaluate(trials)
    assert lenient.passed is True
    assert strict.passed is False


def test_is_deterministic():
    rng = random.Random(2)
    trials = tuple(trial(str(i), [rng.gauss(0, 0.01) for _ in range(96)])
                   for i in range(5))
    test = CombinatorialOverfittingTest(subsets=4)
    assert test.evaluate(trials).probability == test.evaluate(trials).probability


@pytest.mark.parametrize("subsets", [1, 3, 0, -2])
def test_rejects_an_unusable_subset_count(subsets):
    with pytest.raises(DomainError) as e:
        CombinatorialOverfittingTest(subsets=subsets)
    assert e.value.type is ErrorType.BAD_ARGS


def test_rejects_a_single_trial():
    # With nothing to rank against, the test has no meaning.
    with pytest.raises(DomainError) as e:
        CombinatorialOverfittingTest().evaluate((trial("only", [0.01] * 100),))
    assert e.value.type is ErrorType.BAD_ARGS


def test_rejects_ragged_trials():
    with pytest.raises(DomainError) as e:
        CombinatorialOverfittingTest().evaluate(
            (trial("a", [0.01] * 100), trial("b", [0.01] * 50)))
    assert e.value.type is ErrorType.BAD_ARGS


def test_rejects_series_shorter_than_the_subset_count():
    with pytest.raises(DomainError) as e:
        CombinatorialOverfittingTest(subsets=8).evaluate(
            (trial("a", [0.01] * 4), trial("b", [0.02] * 4)))
    assert e.value.type is ErrorType.BAD_ARGS


def test_blocks_cover_the_series_without_gaps_or_overlap():
    test = CombinatorialOverfittingTest(subsets=4)
    blocks = test._blocks(10)
    covered = [i for block in blocks for i in block]
    assert covered == list(range(10))
    assert all(len(block) > 0 for block in blocks)
