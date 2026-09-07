from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal

from tarakdingdung.domain.contracts.api.account_source import AccountSource
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.market_data import MarketDataRepository
from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.contracts.repository.strategy import StrategyRepository
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import Discrepancy
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.domain.models.performance import EquityPoint
from tarakdingdung.domain.models.portfolio import Portfolio, Position
from tarakdingdung.domain.usecases.trading.portfolio import (
    CurrentPortfolioResult, EquityCurveRequest, EquityCurveResult, PortfolioSync,
    SyncRequest, SyncResult,
)


class PortfolioSyncUsecase(PortfolioSync):
    """Rebuilds the portfolio from what the venues actually report.

    Venue balances are the truth, not our order history: partial fills, manual
    trades and venue-side actions all move holdings without passing through the
    engine. Discrepancies against what we last recorded are returned rather
    than raised, because they are the finding, not an obstacle to producing one.
    """

    _TAG = "trading/portfolio"
    _MAX_PRICE_AGE_MS = 3_600_000

    def __init__(self, *, accounts: Mapping[Venue, AccountSource],
                 portfolios: PortfolioRepository, market_data: MarketDataRepository,
                 strategies: StrategyRepository, clock: Clock,
                 logger: LeveledLogger) -> None:
        self._accounts = accounts
        self._portfolios = portfolios
        self._market_data = market_data
        self._strategies = strategies
        self._clock = clock
        self._logger = logger

    async def sync(self, request: SyncRequest) -> SyncResult:
        now = await self._clock.now_ms()
        venues = request.venues or tuple(self._accounts)

        balances, unreachable = await self._balances(venues)
        symbols = await self._universe()
        prices = await self._market_data.read_prices(
            symbols=symbols, as_of=now, max_age=self._MAX_PRICE_AGE_MS)

        positions, cash = self._holdings(symbols, balances, venues)
        equity = sum((p.quantity * prices[p.symbol] for p in positions.values()
                      if p.symbol in prices), Decimal(0))
        equity += sum(cash.values(), Decimal(0))
        equity_by_venue = self._equity_by_venue(positions, prices, balances)

        portfolio = Portfolio(timestamp=now, cash=cash, positions=positions,
                              equity=equity, balances=balances,
                              equity_by_venue=equity_by_venue)
        discrepancies = await self._discrepancies(portfolio, now)

        await self._portfolios.write_snapshot(portfolio)
        # The total series (venue=None) is what the risk overlay reads; the
        # per-venue points back the portfolio page's venue toggle.
        await self._portfolios.write_equity_point(
            EquityPoint(timestamp=now, equity=equity))
        for venue, venue_equity in equity_by_venue.items():
            await self._portfolios.write_equity_point(
                EquityPoint(timestamp=now, equity=venue_equity, venue=str(venue)))

        if discrepancies:
            await self._logger.warn(f"{self._TAG}/Sync", "portfolio discrepancies found",
                                    {"count": len(discrepancies)})
        return SyncResult(portfolio=portfolio, discrepancies=discrepancies,
                          unreachable=tuple(unreachable))

    async def read_current(
            self, venue: Venue | None = None) -> CurrentPortfolioResult:
        now = await self._clock.now_ms()
        portfolio = await self._portfolios.read_latest(as_of=now)
        if portfolio is None:
            err = DomainError("no portfolio recorded", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/ReadCurrent", "failed to read portfolio",
                                     {"err": err})
            raise err
        risk_state = await self._portfolios.read_risk_state(
            as_of=now, venue=str(venue) if venue is not None else None)
        if venue is not None:
            portfolio = self._scoped_to_venue(portfolio, venue)
        return CurrentPortfolioResult(portfolio=portfolio, risk_state=risk_state)

    async def read_equity_curve(self, request: EquityCurveRequest) -> EquityCurveResult:
        venue = request.venue
        return EquityCurveResult(
            points=await self._portfolios.read_equity_curve(
                window=request.window,
                venue=str(venue) if venue is not None else None))

    @staticmethod
    def _equity_by_venue(positions: Mapping[Symbol, Position],
                         prices: Mapping[Symbol, Decimal],
                         balances: Mapping[Venue, Mapping[str, Decimal]],
                         ) -> dict[Venue, Decimal]:
        # A venue's equity is its priced positions plus its home-currency (IDR)
        # balance. Non-IDR balances stay visible but out of the figure, so IDR
        # and USDT are never summed.
        out: dict[Venue, Decimal] = {}
        for venue, assets in balances.items():
            priced = sum((p.quantity * prices[p.symbol]
                          for p in positions.values()
                          if p.symbol.venue == venue and p.symbol in prices),
                         Decimal(0))
            out[venue] = priced + assets.get("IDR", Decimal(0))
        return out

    @staticmethod
    def _scoped_to_venue(portfolio: Portfolio, venue: Venue) -> Portfolio:
        # `equity`, `cash` and `positions` narrow to the venue; `balances` and
        # `equity_by_venue` stay whole so a caller still sees every venue (the
        # page builds its toggle from them).
        equity = portfolio.equity_by_venue.get(venue)
        if equity is None:  # pre-migration snapshot
            equity = portfolio.balances.get(venue, {}).get("IDR", Decimal(0))
        return replace(
            portfolio,
            equity=equity,
            cash={v: a for v, a in portfolio.cash.items() if v == venue},
            positions={s: p for s, p in portfolio.positions.items()
                       if s.venue == venue},
        )

    async def _balances(self, venues) -> tuple[dict[Venue, Mapping[str, Decimal]], list[Venue]]:
        balances: dict[Venue, Mapping[str, Decimal]] = {}
        unreachable: list[Venue] = []
        for venue in venues:
            source = self._accounts.get(venue)
            if source is None:
                unreachable.append(venue)
                continue
            try:
                balances[venue] = await source.fetch_balances()
            except DomainError as err:
                await self._logger.warn(f"{self._TAG}/Sync", "failed to read balances",
                                        {"err": err, "venue": venue})
                # Not knowing a venue's balance is different from knowing it is
                # zero, so the venue is reported unreachable rather than empty.
                unreachable.append(venue)
        return balances, unreachable

    async def _universe(self) -> tuple[Symbol, ...]:
        enabled = await self._strategies.read_enabled()
        seen = {symbol for config in enabled for symbol in config.universe}
        return tuple(sorted(seen, key=lambda s: (s.venue, s.base, s.quote)))

    def _holdings(self, symbols, balances, venues):
        positions: dict[Symbol, Position] = {}
        cash: dict[Venue, Decimal] = {}
        for symbol in symbols:
            venue_balances = balances.get(symbol.venue)
            if venue_balances is None:
                continue
            quantity = venue_balances.get(symbol.base, Decimal(0))
            if quantity > 0:
                positions[symbol] = Position(symbol=symbol, quantity=quantity,
                                             average_price=Decimal(0))
            cash.setdefault(symbol.venue,
                            venue_balances.get(symbol.quote, Decimal(0)))
        return positions, cash

    async def _discrepancies(self, actual: Portfolio, now: int) -> tuple[Discrepancy, ...]:
        previous = await self._portfolios.read_latest(as_of=now)
        if previous is None:
            return ()
        found = []
        for symbol in set(previous.positions) | set(actual.positions):
            expected = self._quantity(previous, symbol)
            held = self._quantity(actual, symbol)
            if expected != held:
                found.append(Discrepancy(symbol=symbol, expected=expected, actual=held))
        return tuple(sorted(found, key=lambda d: (d.symbol.venue, d.symbol.base)))

    @staticmethod
    def _quantity(portfolio: Portfolio, symbol: Symbol) -> Decimal:
        position = portfolio.positions.get(symbol)
        return position.quantity if position is not None else Decimal(0)
