from abc import ABC, abstractmethod
from collections.abc import Mapping
from decimal import Decimal


class AccountSource(ABC):
    """A venue's balances, in domain terms.

    Returns free quantity per asset code, because that is what a spot venue
    actually reports — there are no positions to read, only holdings. Mapping
    those onto symbols is the reconciler's job, since only it knows which pairs
    we intended to trade.
    """

    @abstractmethod
    async def fetch_balances(self) -> Mapping[str, Decimal]: ...
