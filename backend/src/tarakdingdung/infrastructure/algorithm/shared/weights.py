from tarakdingdung.domain.models.algorithm import TargetWeights

# Guards the gross bound against binary floating-point summation error, which
# would otherwise see a fully-invested book as leveraged and reject it.
GROSS_SAFETY = 1e-12


def budget(max_gross: float) -> float:
    """The exposure actually distributable under a gross limit."""
    return max_gross - GROSS_SAFETY


def flat(weights: TargetWeights) -> TargetWeights:
    """Hold nothing, keeping the timestamp — what a tripped halt returns."""
    return TargetWeights(timestamp=weights.timestamp, weights={})
