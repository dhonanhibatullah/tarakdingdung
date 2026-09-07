from uuid import UUID

from pydantic import BaseModel


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class PermissionPostRequest(BaseModel):
    name: str
    description: str | None = None


class PermissionPatchRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class RolePostRequest(BaseModel):
    name: str
    description: str | None = None


class RolePatchRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class UserPostRequest(BaseModel):
    role_id: UUID
    name: str
    bio: str | None = None
    username: str
    password: str


class UserPatchRequest(BaseModel):
    role_id: UUID | None = None
    name: str | None = None
    bio: str | None = None
    username: str | None = None


class UserPasswordPatchRequest(BaseModel):
    password: str


class ProfilePatchRequest(BaseModel):
    name: str | None = None
    bio: str | None = None
    username: str | None = None


class ProfilePasswordPatchRequest(BaseModel):
    current_password: str
    new_password: str


# ---- Trading ---------------------------------------------------------------

class SymbolRequest(BaseModel):
    venue: str
    base: str
    quote: str


class StrategyPostRequest(BaseModel):
    name: str
    kind: str
    mode: str
    universe: list[SymbolRequest]
    description: str | None = None
    parameters: dict | None = None
    is_enabled: bool | None = None


class StrategyPatchRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    kind: str | None = None
    mode: str | None = None
    universe: list[SymbolRequest] | None = None
    parameters: dict | None = None
    is_enabled: bool | None = None
    preferences: dict | None = None


class BacktestPostRequest(BaseModel):
    strategy_id: str
    window_start: int
    window_end: int
    initial_equity: str
    interval: str = "1h"
    periods_per_year: float = 8760.0
    min_completeness: float = 0.99


class ValidationPostRequest(BaseModel):
    strategy_id: str
    window_start: int
    window_end: int
    initial_equity: str
    parameter_grid: list[dict]
    interval: str = "1h"
    subsets: int = 8
    threshold: float = 0.10
