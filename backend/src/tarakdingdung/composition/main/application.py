from dataclasses import dataclass, field

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.backtest import BacktestRepository
from tarakdingdung.domain.contracts.repository.decision import DecisionRepository
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.usecases.trading.backtest import Backtest
from tarakdingdung.domain.usecases.trading.collection import Collection
from tarakdingdung.domain.usecases.trading.engine import TradingEngine
from tarakdingdung.domain.usecases.trading.portfolio import Portfolio
from tarakdingdung.domain.usecases.trading.snapshot import Snapshot
from tarakdingdung.domain.usecases.trading.universe import Universe


@dataclass
class Container:
    session: SessionUsecase
    me: MeUsecase
    security: SecurityUsecase
    permission_management: PermissionManagementUsecase
    role_management: RoleManagementUsecase
    user_management: UserManagementUsecase
    token: Token
    logger: LeveledLogger
    universe_id: str = ""
    venue: str = "indodax"
    universe: Universe | None = None
    portfolio: Portfolio | None = None
    backtest: Backtest | None = None
    snapshot: Snapshot | None = None
    collection: Collection | None = None
    engine: TradingEngine | None = None
    backtests: BacktestRepository | None = None
    decisions: DecisionRepository | None = None
