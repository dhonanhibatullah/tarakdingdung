from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.user import User, UserListItem
from tarakdingdung.domain.usecases.admin.role_management import RolePermissionResult
from tarakdingdung.domain.usecases.auth.session import LoginResult

T = TypeVar("T")


def uuid_str(value: UUID | None) -> str | None:
    if value is None or value == UUID(int=0):
        return None
    return str(value)


def normalize_preferences(value: dict | None) -> dict:
    return value or {}


class AuditResponse(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None
    deleted_by: str | None = None


def _audit(obj) -> dict:
    return dict(
        created_at=obj.created_at, updated_at=obj.updated_at, deleted_at=obj.deleted_at,
        created_by=uuid_str(obj.created_by), updated_by=uuid_str(obj.updated_by),
        deleted_by=uuid_str(obj.deleted_by),
    )


class PermissionResponse(AuditResponse):
    id: str
    name: str
    description: str
    preferences: dict


def permission_response(p: Permission) -> PermissionResponse:
    return PermissionResponse(id=str(p.id), name=p.name, description=p.description,
                              preferences=normalize_preferences(p.preferences), **_audit(p))


def permissions_response(items: list[Permission]) -> list[PermissionResponse]:
    return [permission_response(p) for p in items]


class RoleResponse(AuditResponse):
    id: str
    name: str
    description: str
    is_default: bool
    preferences: dict


def role_response(role: Role) -> RoleResponse:
    return RoleResponse(id=str(role.id), name=role.name, description=role.description,
                        is_default=role.is_default,
                        preferences=normalize_preferences(role.preferences), **_audit(role))


def roles_response(items: list[Role]) -> list[RoleResponse]:
    return [role_response(r) for r in items]


class UserResponse(AuditResponse):
    id: str
    role_id: str
    role_name: str | None = None
    name: str
    bio: str
    username: str
    preferences: dict


def user_response(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), role_id=str(user.role_id), name=user.name,
                        bio=user.bio, username=user.username,
                        preferences=normalize_preferences(user.preferences), **_audit(user))


def user_list_item_response(item: UserListItem) -> UserResponse:
    resp = user_response(item.user)
    resp.role_name = item.role_name or None
    return resp


def users_response(items: list[User]) -> list[UserResponse]:
    return [user_response(u) for u in items]


def user_list_items_response(items: list[UserListItem]) -> list[UserResponse]:
    return [user_list_item_response(i) for i in items]


class RolePermissionResponse(BaseModel):
    id: str
    role_id: str
    permission_id: str
    created_at: datetime
    created_by: str | None = None


class RolePermissionDetailResponse(BaseModel):
    role_permission: RolePermissionResponse
    role: RoleResponse
    permission: PermissionResponse


def role_permission_detail_response(result: RolePermissionResult) -> RolePermissionDetailResponse:
    rp = result.role_permission
    return RolePermissionDetailResponse(
        role_permission=RolePermissionResponse(
            id=str(rp.id), role_id=str(rp.role_id), permission_id=str(rp.permission_id),
            created_at=rp.created_at, created_by=uuid_str(rp.created_by)),
        role=role_response(result.role),
        permission=permission_response(result.permission),
    )


def role_permission_details_response(
        items: list[RolePermissionResult]) -> list[RolePermissionDetailResponse]:
    return [role_permission_detail_response(i) for i in items]


class LoginResponse(BaseModel):
    user: UserResponse
    role: RoleResponse
    permissions: list[PermissionResponse]
    access_token: str
    refresh_token: str


def login_response(result: LoginResult) -> LoginResponse:
    return LoginResponse(
        user=user_response(result.user), role=role_response(result.role),
        permissions=[permission_response(p) for p in result.permissions],
        access_token=result.access_token, refresh_token=result.refresh_token,
    )


class IdResponse(BaseModel):
    id: str


class ErrorResponse(BaseModel):
    error: str
    message: str


class PageResponse(BaseModel):
    page: int
    limit: int
    total_items: int


class PageDataResponse(BaseModel, Generic[T]):
    data: list[T]
    page: PageResponse


# ---- Trading ---------------------------------------------------------------

class SymbolResponse(BaseModel):
    venue: str
    base: str
    quote: str


def symbol_response(symbol) -> SymbolResponse:
    return SymbolResponse(venue=str(symbol.venue), base=symbol.base,
                          quote=symbol.quote)


class StrategyResponse(AuditResponse):
    id: str
    name: str
    description: str
    kind: str
    mode: str
    universe: list[SymbolResponse]
    parameters: dict
    is_enabled: bool
    preferences: dict


def strategy_response(config) -> StrategyResponse:
    return StrategyResponse(
        id=str(config.id), name=config.name, description=config.description,
        kind=config.kind, mode=str(config.mode),
        universe=[symbol_response(s) for s in config.universe],
        parameters=config.parameters, is_enabled=config.is_enabled,
        preferences=normalize_preferences(config.preferences), **_audit(config))


def strategies_response(items) -> list[StrategyResponse]:
    return [strategy_response(c) for c in items]


class PerformanceResponse(BaseModel):
    total_return: float
    sharpe: float
    sortino: float
    max_drawdown: float
    turnover: float
    gross_return: float
    net_return: float
    cost_drag: float
    trade_count: int


def performance_response(report) -> PerformanceResponse:
    return PerformanceResponse(
        total_return=report.total_return, sharpe=report.sharpe,
        sortino=report.sortino, max_drawdown=report.max_drawdown,
        turnover=report.turnover, gross_return=report.gross_return,
        net_return=report.net_return, cost_drag=report.cost_drag,
        trade_count=report.trade_count)


class BacktestRunResponse(BaseModel):
    id: str
    strategy_id: str
    window_start: int
    window_end: int
    initial_equity: str
    report: PerformanceResponse
    created_at: datetime


def backtest_run_response(run) -> BacktestRunResponse:
    return BacktestRunResponse(
        id=str(run.id), strategy_id=str(run.strategy_id),
        window_start=run.window.start, window_end=run.window.end,
        initial_equity=str(run.initial_equity),
        report=performance_response(run.report), created_at=run.created_at)


def backtest_runs_response(items) -> list[BacktestRunResponse]:
    return [backtest_run_response(r) for r in items]


class OverfittingResponse(BaseModel):
    probability: float
    threshold: float
    passed: bool


class ValidationRunResponse(BaseModel):
    id: str
    strategy_id: str
    window_start: int
    window_end: int
    trials: int
    overfitting: OverfittingResponse
    created_at: datetime


def validation_run_response(run) -> ValidationRunResponse:
    return ValidationRunResponse(
        id=str(run.id), strategy_id=str(run.strategy_id),
        window_start=run.window.start, window_end=run.window.end,
        trials=len(run.trials),
        overfitting=OverfittingResponse(
            probability=run.overfitting.probability,
            threshold=run.overfitting.threshold, passed=run.overfitting.passed),
        created_at=run.created_at)


class PositionResponse(BaseModel):
    symbol: SymbolResponse
    quantity: str
    average_price: str


class PortfolioResponse(BaseModel):
    timestamp: int
    cash: dict[str, str]
    positions: list[PositionResponse]
    equity: str
    # Per-asset free balance of every reachable venue at this sync, keyed
    # {venue: {asset: amount}}. Informational only — `equity` stays scoped to
    # priced positions plus quote cash, so IDR and USDT are never summed.
    balances: dict[str, dict[str, str]] = {}


class RiskStateResponse(BaseModel):
    timestamp: int
    equity_peak: str
    daily_pnl: str
    realized_volatility: float
    halted: bool


class CurrentPortfolioResponse(BaseModel):
    portfolio: PortfolioResponse
    risk_state: RiskStateResponse


def portfolio_response(portfolio) -> PortfolioResponse:
    return PortfolioResponse(
        timestamp=portfolio.timestamp,
        cash={str(venue): str(amount) for venue, amount in portfolio.cash.items()},
        positions=[PositionResponse(symbol=symbol_response(s),
                                    quantity=str(p.quantity),
                                    average_price=str(p.average_price))
                   for s, p in portfolio.positions.items()],
        equity=str(portfolio.equity),
        balances={str(venue): {asset: str(amount) for asset, amount in assets.items()}
                  for venue, assets in portfolio.balances.items()})


def current_portfolio_response(result) -> CurrentPortfolioResponse:
    state = result.risk_state
    return CurrentPortfolioResponse(
        portfolio=portfolio_response(result.portfolio),
        risk_state=RiskStateResponse(
            timestamp=state.timestamp, equity_peak=str(state.equity_peak),
            daily_pnl=str(state.daily_pnl),
            realized_volatility=state.realized_volatility, halted=state.halted))


class EquityPointResponse(BaseModel):
    timestamp: int
    equity: str


class EquityCurveResponse(BaseModel):
    points: list[EquityPointResponse]


class CoverageResponse(BaseModel):
    symbol: SymbolResponse
    interval: str
    expected: int
    present: int
    completeness: float
    gaps: list[dict]


def coverage_response(coverage) -> CoverageResponse:
    return CoverageResponse(
        symbol=symbol_response(coverage.symbol), interval=coverage.interval,
        expected=coverage.expected, present=coverage.present,
        completeness=coverage.completeness,
        gaps=[{"start": g.start, "end": g.end} for g in coverage.gaps])


class CycleResponse(BaseModel):
    timestamp: int
    strategy_id: str
    decision: str
    halted_by: str | None = None
    orders: int
    rejected: int
    reconciled: int


def cycle_response(result) -> CycleResponse:
    return CycleResponse(
        timestamp=result.timestamp, strategy_id=str(result.strategy_id),
        decision=str(result.decision), halted_by=result.halted_by,
        orders=len(result.plan.orders) if result.plan else 0,
        rejected=len(result.plan.rejected) if result.plan else 0,
        reconciled=result.reconciled)
