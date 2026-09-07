"""Trading HTTP surface.

Deliberately read-heavy. The two writes that reach the market — running a
backtest and a dry-run cycle — either touch nothing outside the database or
plan without submitting.

**There is no route that executes a live cycle.** The engine runs on a
schedule; an HTTP endpoint that places real orders would be an attack surface
with no compensating benefit.
"""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.market import Symbol, TimeRange, Venue
from tarakdingdung.domain.models.strategy import TradingMode
from tarakdingdung.domain.usecases.trading import backtest as bt
from tarakdingdung.domain.usecases.trading import engine as eng
from tarakdingdung.domain.usecases.trading import history as hist
from tarakdingdung.domain.usecases.trading import portfolio as pf
from tarakdingdung.domain.usecases.trading import strategy as st
from tarakdingdung.domain.usecases.trading import validation as val
from tarakdingdung.presentation.http.dependencies.auth import get_actor_id
from tarakdingdung.presentation.http.dependencies.container import (
    get_trading_backtest, get_trading_engine, get_trading_history,
    get_trading_portfolio, get_trading_strategy, get_trading_validation,
)
from tarakdingdung.presentation.http.dependencies.permission import require
from tarakdingdung.presentation.http.schemas import request as req
from tarakdingdung.presentation.http.schemas import response as res
from tarakdingdung.presentation.http.utils.pagination import (
    PaginationParams, page_response, pagination_params,
)

router = APIRouter(prefix="/v1/trading", tags=["Trading"])


def _symbol(raw: req.SymbolRequest) -> Symbol:
    try:
        return Symbol(venue=Venue(raw.venue.upper()), base=raw.base.upper(),
                      quote=raw.quote.upper())
    except ValueError as exc:
        raise DomainError(f"unknown venue {raw.venue!r}", ErrorType.BAD_ARGS) from exc


def _mode(raw: str) -> TradingMode:
    try:
        return TradingMode(raw.upper())
    except ValueError as exc:
        raise DomainError(f"unknown trading mode {raw!r}", ErrorType.BAD_ARGS) from exc


def _money(raw: str, label: str) -> Decimal:
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise DomainError(f"{label} is not a number: {raw!r}",
                          ErrorType.BAD_ARGS) from exc


def _window(start: int, end: int) -> TimeRange:
    # TimeRange validates that the window advances, so a reversed one is
    # rejected here rather than quietly selecting nothing.
    return TimeRange(start=start, end=end)


# ---- Strategies ------------------------------------------------------------

@router.get("/strategies", response_model=res.PageDataResponse[res.StrategyResponse],
            dependencies=[Depends(require("strategy:get"))])
async def strategy_list(page: PaginationParams = Depends(pagination_params),
                        mode: str | None = Query(default=None),
                        uc: st.StrategyManagement = Depends(get_trading_strategy)):
    result = await uc.read_by_pagination(st.ListStrategiesRequest(
        page=page.page, limit=page.limit, search=page.search,
        mode=_mode(mode) if mode else None))
    return res.PageDataResponse[res.StrategyResponse](
        data=res.strategies_response(list(result.strategies)),
        page=page_response(page, result.total))


@router.post("/strategies", status_code=201, response_model=res.IdResponse,
             dependencies=[Depends(require("strategy:add"))])
async def strategy_create(body: req.StrategyPostRequest,
                          actor: UUID = Depends(get_actor_id),
                          uc: st.StrategyManagement = Depends(get_trading_strategy)):
    new_id = await uc.create(st.CreateStrategyRequest(
        name=body.name, description=body.description, kind=body.kind,
        mode=_mode(body.mode),
        universe=tuple(_symbol(s) for s in body.universe),
        parameters=body.parameters, is_enabled=body.is_enabled, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.get("/strategies/{id}", response_model=res.StrategyResponse,
            dependencies=[Depends(require("strategy:get"))])
async def strategy_detail(id: UUID,
                          uc: st.StrategyManagement = Depends(get_trading_strategy)):
    return res.strategy_response(await uc.read_by_id(id))


@router.patch("/strategies/{id}", status_code=204,
              dependencies=[Depends(require("strategy:set"))])
async def strategy_update(id: UUID, body: req.StrategyPatchRequest,
                          actor: UUID = Depends(get_actor_id),
                          uc: st.StrategyManagement = Depends(get_trading_strategy)):
    await uc.update_by_id(st.UpdateStrategyRequest(
        id=id, name=body.name, description=body.description, kind=body.kind,
        mode=_mode(body.mode) if body.mode else None,
        universe=tuple(_symbol(s) for s in body.universe) if body.universe else None,
        parameters=body.parameters, is_enabled=body.is_enabled,
        preferences=body.preferences, updated_by=actor))
    return Response(status_code=204)


@router.delete("/strategies/{id}", status_code=204,
               dependencies=[Depends(require("strategy:remove"))])
async def strategy_delete(id: UUID, actor: UUID = Depends(get_actor_id),
                          uc: st.StrategyManagement = Depends(get_trading_strategy)):
    await uc.delete_by_id(id, deleted_by=actor)
    return Response(status_code=204)


# ---- Market data -----------------------------------------------------------

@router.get("/coverage", response_model=res.CoverageResponse,
            dependencies=[Depends(require("market_data:get"))])
async def coverage(venue: str, base: str, quote: str,
                   window_start: int, window_end: int, interval: str = "1h",
                   uc: hist.MarketDataHistory = Depends(get_trading_history)):
    """How complete stored history is — the check to run before trusting a
    backtest over a window."""
    symbol = _symbol(req.SymbolRequest(venue=venue, base=base, quote=quote))
    return res.coverage_response(await uc.read_coverage(hist.ReadCoverageRequest(
        symbol=symbol, interval=interval,
        window=_window(window_start, window_end))))


# ---- Backtests -------------------------------------------------------------

@router.get("/backtests", response_model=res.PageDataResponse[res.BacktestRunResponse],
            dependencies=[Depends(require("backtest:get"))])
async def backtest_list(page: PaginationParams = Depends(pagination_params),
                        strategy_id: UUID | None = Query(default=None),
                        uc: bt.Backtesting = Depends(get_trading_backtest)):
    result = await uc.read_by_pagination(bt.ListBacktestsRequest(
        page=page.page, limit=page.limit, strategy_id=strategy_id))
    return res.PageDataResponse[res.BacktestRunResponse](
        data=res.backtest_runs_response(list(result.runs)),
        page=page_response(page, result.total))


@router.post("/backtests", status_code=201, response_model=res.BacktestRunResponse,
             dependencies=[Depends(require("backtest:add"))])
async def backtest_run(body: req.BacktestPostRequest,
                       actor: UUID = Depends(get_actor_id),
                       uc: bt.Backtesting = Depends(get_trading_backtest)):
    result = await uc.run(bt.RunBacktestRequest(
        strategy_id=UUID(body.strategy_id),
        window=_window(body.window_start, body.window_end),
        initial_equity=_money(body.initial_equity, "initial_equity"),
        interval=body.interval, periods_per_year=body.periods_per_year,
        min_completeness=body.min_completeness, created_by=actor))
    return res.backtest_run_response(await uc.read_by_id(result.run_id))


@router.get("/backtests/{id}", response_model=res.BacktestRunResponse,
            dependencies=[Depends(require("backtest:get"))])
async def backtest_detail(id: UUID, uc: bt.Backtesting = Depends(get_trading_backtest)):
    return res.backtest_run_response(await uc.read_by_id(id))


# ---- Validation ------------------------------------------------------------

@router.post("/validations", status_code=201,
             response_model=res.ValidationRunResponse,
             dependencies=[Depends(require("backtest:add"))])
async def validation_run(body: req.ValidationPostRequest,
                         actor: UUID = Depends(get_actor_id),
                         uc: val.StrategyValidation = Depends(get_trading_validation)):
    result = await uc.run_walk_forward(val.RunWalkForwardRequest(
        strategy_id=UUID(body.strategy_id),
        window=_window(body.window_start, body.window_end),
        parameter_grid=tuple(body.parameter_grid),
        initial_equity=_money(body.initial_equity, "initial_equity"),
        interval=body.interval, subsets=body.subsets, threshold=body.threshold,
        created_by=actor))
    return res.validation_run_response(await uc.read_by_id(result.validation_id))


@router.get("/validations/{id}", response_model=res.ValidationRunResponse,
            dependencies=[Depends(require("backtest:get"))])
async def validation_detail(id: UUID,
                            uc: val.StrategyValidation = Depends(get_trading_validation)):
    return res.validation_run_response(await uc.read_by_id(id))


# ---- Portfolio -------------------------------------------------------------

def _venue(raw: str | None) -> Venue | None:
    if raw is None:
        return None
    try:
        return Venue(raw.upper())
    except ValueError as exc:
        raise DomainError(f"unknown venue {raw!r}", ErrorType.BAD_ARGS) from exc


@router.get("/portfolio", response_model=res.CurrentPortfolioResponse,
            dependencies=[Depends(require("portfolio:get"))])
async def portfolio_current(venue: str | None = Query(default=None),
                            uc: pf.PortfolioSync = Depends(get_trading_portfolio)):
    return res.current_portfolio_response(await uc.read_current(_venue(venue)))


@router.get("/portfolio/equity", response_model=res.EquityCurveResponse,
            dependencies=[Depends(require("portfolio:get"))])
async def portfolio_equity(window_start: int, window_end: int,
                           venue: str | None = Query(default=None),
                           uc: pf.PortfolioSync = Depends(get_trading_portfolio)):
    result = await uc.read_equity_curve(pf.EquityCurveRequest(
        window=_window(window_start, window_end), venue=_venue(venue)))
    return res.EquityCurveResponse(points=[
        res.EquityPointResponse(timestamp=p.timestamp, equity=str(p.equity))
        for p in result.points])


# ---- Engine ----------------------------------------------------------------

@router.post("/engine/{strategy_id}/dry-run", response_model=res.CycleResponse,
             dependencies=[Depends(require("engine:run"))])
async def engine_dry_run(strategy_id: UUID,
                         uc: eng.TradingEngine = Depends(get_trading_engine)):
    """What the engine would do right now, without touching the market.

    Plans and returns; persists nothing and submits nothing. Live execution is
    reachable only from the cron.
    """
    return res.cycle_response(await uc.run_cycle(
        eng.RunCycleRequest(strategy_id=strategy_id, dry_run=True)))
