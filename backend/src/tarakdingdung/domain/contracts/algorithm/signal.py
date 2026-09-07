from abc import ABC, abstractmethod

from tarakdingdung.domain.models.algorithm import FeatureSet, Signals


class SignalGenerator(ABC):
    """Turns features into conviction per symbol, in ``[-1, 1]``.

    Answers how strongly to believe, never how much to bet — sizing is the
    allocator's decision, and the two have different failure modes.
    """

    @abstractmethod
    def generate(self, features: FeatureSet) -> Signals: ...
