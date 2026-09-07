from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.api.account_source import AccountSource
from tarakdingdung.domain.contracts.api.tokocrypto.v3.trade import TokocryptoV3TradeApi
from tarakdingdung.infrastructure.venue.shared import to_decimal


class TokocryptoAccountSource(AccountSource):
    """Free balances per asset from the Binance-standard `/api/v3/account`."""

    _VENUE = "tokocrypto"

    def __init__(self, *, trade: TokocryptoV3TradeApi) -> None:
        self._trade = trade

    async def fetch_balances(self) -> Mapping[str, Decimal]:
        payload = await self._trade.account()
        balances = {}
        for entry in payload.get("balances") or payload.get("accountAssets") or []:
            asset = (entry.get("asset") or "").upper()
            if not asset:
                continue
            free = to_decimal(entry.get("free"), f"free balance for {asset}",
                              venue=self._VENUE, default=Decimal(0))
            if free > 0:
                balances[asset] = free
        return balances
