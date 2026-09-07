from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from tarakdingdung.domain.contracts.algorithm.rebalance import Rebalancer
from tarakdingdung.domain.models.algorithm import Side, TargetWeights, TradeIntent
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.portfolio import Portfolio


class NoTradeBandRebalancer(Rebalancer):
    """Trades only the gaps worth trading.

    A band around each target suppresses the constant small corrections that
    a continuously drifting portfolio would otherwise generate. Turnover is
    the cost the research says kills otherwise-sound strategies, and most of
    it comes from rebalancing noise rather than from changed conviction.

    Symbols held but no longer targeted are exited, so an emptied set of
    weights means "sell everything" rather than "leave it alone".
    """

    def __init__(self, *, band: float = 0.005) -> None:
        self._band = band

    def plan(self, target: TargetWeights, portfolio: Portfolio,
             prices: Mapping[Symbol, Decimal]) -> tuple[TradeIntent, ...]:
        equity = portfolio.equity
        if not equity.is_finite() or equity <= 0:
            return ()

        intents = []
        for symbol in self._symbols(target, portfolio):
            price = prices.get(symbol)
            # No price means no way to size the trade. Skipping is right:
            # a stale or guessed price would size a real order wrongly.
            if price is None or not price.is_finite() or price <= 0:
                continue
            drift = target.weights.get(symbol, 0.0) - self._current(
                symbol, portfolio, price, equity)
            if abs(drift) < self._band:
                continue
            intent = self._intent(symbol, drift, price, equity)
            if intent is not None:
                intents.append(intent)
        return tuple(intents)

    def _symbols(self, target: TargetWeights, portfolio: Portfolio) -> list[Symbol]:
        held = {s for s, p in portfolio.positions.items() if p.quantity != 0}
        return sorted(held | set(target.weights),
                      key=lambda s: (s.venue, s.base, s.quote))

    def _current(self, symbol: Symbol, portfolio: Portfolio,
                 price: Decimal, equity: Decimal) -> float:
        position = portfolio.positions.get(symbol)
        if position is None:
            return 0.0
        return float(position.quantity * price / equity)

    def _intent(self, symbol: Symbol, drift: float, price: Decimal,
                equity: Decimal) -> TradeIntent | None:
        try:
            quantity = abs(Decimal(str(drift))) * equity / price
        except (InvalidOperation, ZeroDivisionError):
            return None
        if not quantity.is_finite() or quantity <= 0:
            return None
        return TradeIntent(symbol=symbol,
                           side=Side.BUY if drift > 0 else Side.SELL,
                           quantity=quantity, reference_price=price)
