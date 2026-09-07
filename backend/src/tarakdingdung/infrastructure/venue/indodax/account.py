from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.api.account_source import AccountSource
from tarakdingdung.domain.contracts.api.indodax.v2.trade import IndodaxV2TradeApi
from tarakdingdung.infrastructure.venue.shared import to_decimal


class IndodaxAccountSource(AccountSource):
    """Free balances per asset from the Indodax v2 account endpoint.

    Zero balances are dropped rather than carried: an asset we do not hold and
    an asset the venue did not mention mean the same thing to a reconciler, and
    keeping both would make every comparison longer without saying more.
    """

    _VENUE = "indodax"

    def __init__(self, *, trade: IndodaxV2TradeApi) -> None:
        self._trade = trade

    async def fetch_balances(self) -> Mapping[str, Decimal]:
        payload = await self._trade.account(omit_zero_balances=True)
        balances = {}
        for entry in payload.get("balances") or []:
            asset = (entry.get("asset") or "").upper()
            if not asset:
                continue
            free = to_decimal(entry.get("free"), f"free balance for {asset}",
                              venue=self._VENUE, default=Decimal(0))
            if free > 0:
                balances[asset] = free
        return balances
