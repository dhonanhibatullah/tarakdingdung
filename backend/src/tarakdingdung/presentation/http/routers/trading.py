from fastapi import APIRouter, Depends

from tarakdingdung.domain.models.symbol import Symbol
from tarakdingdung.presentation.http.dependencies.auth import require_permission
from tarakdingdung.presentation.http.dependencies.container import get_container
from tarakdingdung.presentation.http.schemas.request import (
    ApproveSymbolBody,
    BacktestBody,
    ProposeSymbolBody,
)

router = APIRouter(prefix="/api/trading", tags=["trading"])


@router.get("/universe", dependencies=[Depends(require_permission("universe:get"))])
async def list_universe(container=Depends(get_container)):
    symbols = await container.universe.list(container.universe_id)
    return {
        "items": [
            {"id": s.id, "venue": s.venue, "base": s.base, "quote": s.quote, "external": s.external}
            for s in symbols
        ]
    }


@router.post("/universe/propose", dependencies=[Depends(require_permission("universe:add"))])
async def propose_symbol(body: ProposeSymbolBody, container=Depends(get_container)):
    membership = await container.universe.propose(
        container.universe_id,
        Symbol(id="", venue=body.venue, base=body.base, quote=body.quote, external=body.external),
        body.rationale,
    )
    return {"symbol_id": membership.symbol_id, "state": membership.state.value}


@router.post(
    "/universe/{symbol_id}/approve",
    dependencies=[Depends(require_permission("universe:set"))],
)
async def approve_symbol(
    symbol_id: str, body: ApproveSymbolBody, container=Depends(get_container)
):
    membership = await container.universe.approve(
        container.universe_id, symbol_id, body.rationale
    )
    return {"symbol_id": membership.symbol_id, "state": membership.state.value}


@router.get("/portfolio", dependencies=[Depends(require_permission("portfolio:get"))])
async def portfolio(container=Depends(get_container)):
    view = await container.portfolio.read(container.venue)
    if view is None:
        return {"equity": None, "as_of_ms": None, "balances": []}
    return {
        "equity": str(view.equity),
        "as_of_ms": view.as_of_ms,
        "balances": [
            {"asset": b.asset, "free": str(b.free), "locked": str(b.locked)}
            for b in view.balances
        ],
    }


@router.get("/decision", dependencies=[Depends(require_permission("decision:get"))])
async def latest_decision(container=Depends(get_container)):
    decision = await container.decisions.read_latest(container.universe_id)
    if decision is None:
        return None
    return {
        "id": decision.id,
        "as_of_ms": decision.as_of_ms,
        "weights": [
            {"symbol_id": w.symbol_id, "weight": w.weight} for w in decision.weights
        ],
        "reasoning": decision.reasoning,
        "confidence": decision.confidence,
        "status": decision.status,
    }


@router.post("/backtest", dependencies=[Depends(require_permission("backtest:add"))])
async def run_backtest(body: BacktestBody, container=Depends(get_container)):
    result = await container.backtest.replay(
        container.universe_id, body.from_ms, body.to_ms
    )
    return {
        "id": result.id,
        "sharpe": result.sharpe,
        "max_drawdown": result.max_drawdown,
        "turnover": result.turnover,
    }


@router.get("/backtest", dependencies=[Depends(require_permission("backtest:get"))])
async def list_backtests(page: int = 1, per_page: int = 20, container=Depends(get_container)):
    items, total = await container.backtests.read_by_pagination(page, per_page)
    return {
        "items": [
            {"id": b.id, "from_ms": b.from_ms, "to_ms": b.to_ms, "sharpe": b.sharpe}
            for b in items
        ],
        "total": total,
    }


@router.post("/engine/dry-run", dependencies=[Depends(require_permission("engine:run"))])
async def engine_dry_run(container=Depends(get_container)):
    result = await container.engine.dry_run()
    return {"status": result.status.value, "detail": result.detail}
