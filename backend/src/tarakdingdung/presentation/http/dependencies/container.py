from dataclasses import dataclass

from fastapi import Depends, Request

from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.usecases.admin.permission_management import PermissionManagement
from tarakdingdung.domain.usecases.admin.role_management import RoleManagement
from tarakdingdung.domain.usecases.admin.user_management import UserManagement
from tarakdingdung.domain.usecases.auth.session import Session
from tarakdingdung.domain.usecases.profile.account import Account
from tarakdingdung.domain.usecases.profile.me import Me
from tarakdingdung.domain.usecases.profile.security import Security
from tarakdingdung.domain.usecases.trading.backtest import Backtesting
from tarakdingdung.domain.usecases.trading.collection import MarketDataCollection
from tarakdingdung.domain.usecases.trading.engine import TradingEngine
from tarakdingdung.domain.usecases.trading.history import MarketDataHistory
from tarakdingdung.domain.usecases.trading.portfolio import PortfolioSync
from tarakdingdung.domain.usecases.trading.strategy import StrategyManagement
from tarakdingdung.domain.usecases.trading.validation import StrategyValidation


@dataclass(frozen=True, slots=True)
class Container:
    session: Session
    permission_management: PermissionManagement
    role_management: RoleManagement
    user_management: UserManagement
    profile_me: Me
    profile_account: Account
    profile_security: Security
    trading_collection: MarketDataCollection
    trading_history: MarketDataHistory
    trading_strategy: StrategyManagement
    trading_backtest: Backtesting
    trading_validation: StrategyValidation
    trading_portfolio: PortfolioSync
    trading_engine: TradingEngine
    token: Token


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_token(container: Container = Depends(get_container)) -> Token:
    return container.token


def get_session_usecase(container: Container = Depends(get_container)) -> Session:
    return container.session


def get_permission_management(
        container: Container = Depends(get_container)) -> PermissionManagement:
    return container.permission_management


def get_role_management(container: Container = Depends(get_container)) -> RoleManagement:
    return container.role_management


def get_user_management(container: Container = Depends(get_container)) -> UserManagement:
    return container.user_management


def get_profile_me(container: Container = Depends(get_container)) -> Me:
    return container.profile_me


def get_profile_account(container: Container = Depends(get_container)) -> Account:
    return container.profile_account


def get_profile_security(container: Container = Depends(get_container)) -> Security:
    return container.profile_security


def get_trading_collection(
        container: Container = Depends(get_container)) -> MarketDataCollection:
    return container.trading_collection


def get_trading_history(container: Container = Depends(get_container)) -> MarketDataHistory:
    return container.trading_history


def get_trading_strategy(
        container: Container = Depends(get_container)) -> StrategyManagement:
    return container.trading_strategy


def get_trading_backtest(container: Container = Depends(get_container)) -> Backtesting:
    return container.trading_backtest


def get_trading_validation(
        container: Container = Depends(get_container)) -> StrategyValidation:
    return container.trading_validation


def get_trading_portfolio(container: Container = Depends(get_container)) -> PortfolioSync:
    return container.trading_portfolio


def get_trading_engine(container: Container = Depends(get_container)) -> TradingEngine:
    return container.trading_engine
