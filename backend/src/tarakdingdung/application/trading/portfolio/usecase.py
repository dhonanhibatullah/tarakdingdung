from tarakdingdung.domain.contracts.repository.portfolio import PortfolioRepository
from tarakdingdung.domain.usecases.trading.portfolio import Portfolio, PortfolioView


class PortfolioUsecase(Portfolio):
    def __init__(self, portfolio: PortfolioRepository) -> None:
        self._portfolio = portfolio

    async def read(self, venue: str) -> PortfolioView | None:
        snapshot = await self._portfolio.read_latest(venue)
        if snapshot is None:
            return None
        balances = await self._portfolio.read_balances(snapshot.id)
        return PortfolioView(
            venue=snapshot.venue,
            as_of_ms=snapshot.as_of_ms,
            equity=snapshot.equity,
            balances=balances,
        )
