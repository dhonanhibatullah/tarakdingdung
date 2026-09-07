from abc import ABC, abstractmethod

from tarakdingdung.domain.models.algorithm import FeatureSet
from tarakdingdung.domain.models.market import MarketSnapshot


class FeatureExtractor(ABC):
    """Turns raw market data into named numeric features.

    Symbols with too little history to compute a feature are omitted rather
    than filled with a placeholder — an absent key is the normal state at the
    start of a backtest and after every new listing, and it propagates
    harmlessly through signals and weights into simply not holding the symbol.
    """

    @abstractmethod
    def compute(self, snapshot: MarketSnapshot) -> FeatureSet: ...
