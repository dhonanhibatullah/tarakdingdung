from pydantic import BaseModel


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


class AddPermissionBody(BaseModel):
    name: str
    description: str = ""


class AddRoleBody(BaseModel):
    name: str
    description: str = ""
    is_default: bool = False


class AssignPermissionBody(BaseModel):
    permission_id: str


class AddUserBody(BaseModel):
    username: str
    email: str
    password: str
    role_names: list[str] = []


class ProposeSymbolBody(BaseModel):
    venue: str
    base: str
    quote: str
    external: str
    rationale: str = ""


class ApproveSymbolBody(BaseModel):
    rationale: str = ""


class BacktestBody(BaseModel):
    from_ms: int
    to_ms: int

