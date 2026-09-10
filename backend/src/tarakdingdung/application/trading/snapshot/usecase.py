from decimal import Decimal

from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.universe import UniverseRepository
from tarakdingdung.domain.contracts.trade.exchange import Exchange
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.portfolio import Balance, PortfolioSnapshot
from tarakdingdung.domain.models.symbol import MembershipState
from tarakdingdung.domain.usecases.trading.snapshot import Snapshot


class SnapshotUsecase(Snapshot):
    def __init__(
        self,
        exchange: Exchange,
        universe_id: str,
        venue: str,
        universes: UniverseRepository,
        market_data: MarketDataRepository,
        portfolio: PortfolioRepository,
        clock: Clock,
    ) -> None:
        self._exchange = exchange
        self._universe_id = universe_id
        self._venue = venue
        self._universes = universes
        self._market_data = market_data
        self._portfolio = portfolio
        self._clock = clock

    async def take(self) -> PortfolioSnapshot:
        account = await self._exchange.account()
        approved = await self._universes.read_symbols_by_state(
            self._universe_id, MembershipState.APPROVED
        )
        by_base = {s.base.lower(): s for s in approved}

        equity = Decimal("0")
        balances: list[Balance] = []
        for b in account.balances:
            balances.append(
                Balance(
                    snapshot_id="", asset=b.asset, free=b.free, locked=b.locked
                )
            )
            symbol = by_base.get(b.asset.lower())
            if symbol is not None:
                candle = await self._market_data.read_latest(symbol.id)
                if candle is not None:
                    equity += (b.free + b.locked) * candle.close
            else:
                equity += b.free + b.locked

        snapshot = PortfolioSnapshot(
            id="", venue=self._venue, as_of_ms=self._clock.now_ms(), equity=equity
        )
        return await self._portfolio.create_snapshot(snapshot, balances)
