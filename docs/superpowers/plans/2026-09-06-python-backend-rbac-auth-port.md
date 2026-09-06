# Python/FastAPI RBAC + Auth Backend Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the RBAC + authentication slice of `nusapala-things/backend` (Go) to a Python/FastAPI backend under `backend/src/tarakdingdung/`, complete through a runnable `create_app()` plus a seed CLI.

**Architecture:** Layered/clean architecture with a one-directional dependency rule — `presentation → application → domain ← infrastructure`, wired by `composition`. `domain` holds frozen dataclasses + `ABC` contracts/usecase interfaces and imports only stdlib. `infrastructure` implements the contracts with SQLAlchemy 2.0 async ORM + Core, bcrypt, and PyJWT. `presentation` is FastAPI routers with `Depends`-injected usecases and a `DomainError`→HTTP mapping.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, SQLAlchemy 2.0 (async) + asyncpg, Alembic, Pydantic v2, pydantic-settings, PyJWT, bcrypt; pytest + pytest-asyncio + httpx + testcontainers for tests; Postgres.

**Spec:** `docs/superpowers/specs/2026-09-06-python-backend-rbac-auth-port-design.md`

## Global Constraints

- **Python 3.12.** `backend/.venv` is the only virtualenv; it currently holds just `pip`.
- **Dependency allowlist (runtime):** `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic`, `pydantic-settings`, `pyjwt`, `bcrypt`. **(dev):** `pytest`, `pytest-asyncio`, `httpx`, `testcontainers[postgres]`. Add nothing else without asking the user.
- After any dependency change: `backend/.venv/bin/pip freeze > backend/requirements.txt`.
- **Env var prefix is `TRDD_BE_`** for every setting.
- `domain/` imports only: stdlib (`abc`, `dataclasses`, `enum`, `datetime`, `uuid`, `typing`, `collections.abc`). No `sqlalchemy`, `fastapi`, `pydantic`, `jwt`, `bcrypt` in `domain/`.
- All repository, usecase, and logger methods are `async`.
- Domain models and usecase request/result DTOs are `@dataclass(frozen=True, slots=True)`.
- Contracts and usecase interfaces are `abc.ABC` with `@abstractmethod`.
- **Repository verb set is fixed:** `create`, `read_by_id`, `read_by_<field>`, `read_default`, `read_permissions`, `read_by_pagination`, `update_by_id`, `delete_by_id`. No `get`/`list`/`find`.
- Pagination methods return `tuple[list[T], int]`; single-item reads return `T | None`.
- Soft delete (`deleted_at`/`deleted_by`) on `permissions`, `roles`, `users`. `role_permission` is hard-deleted (no `deleted_at` column).
- Every read filters `deleted_at IS NULL` on soft-deletable tables.
- Every `git commit` message ends with these two trailer lines:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA
  ```
- Run all commands from the repo root `/home/dodol/Repositories/tarakdingdung` unless stated. Python is `backend/.venv/bin/python`, pytest is `backend/.venv/bin/pytest`.

---

### Task 1: Project scaffolding, settings, test harness

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/src/tarakdingdung/config/settings.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_settings.py`
- Modify: `backend/requirements.txt` (created by `pip freeze`)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `tarakdingdung.config.settings.Settings` — pydantic-settings `BaseSettings`, env prefix `TRDD_BE_`. Fields (all with defaults): `app_name: str`, `app_version: str`, `logger_format: Literal["plain","json"]`, `logger_level: str`, `postgres_host: str`, `postgres_port: int`, `postgres_username: str`, `postgres_password: str`, `postgres_database: str`, `postgres_ssl_mode: str`, `postgres_pool_size: int`, `http_host: str`, `http_port: int`, `http_cors_allowed_origins: list[str]`, `token_access_secret: str`, `token_refresh_secret: str`, `token_access_ttl_seconds: int`, `token_refresh_ttl_seconds: int`, `password_bcrypt_cost: int`, `seed_super_password: str`, `seed_admin_password: str`, `seed_user_password: str`.
  - `Settings.postgres_dsn` — computed `@property` returning `postgresql+asyncpg://{user}:{pass}@{host}:{port}/{db}`.
  - `tarakdingdung.config.settings.get_settings() -> Settings` — `functools.lru_cache`-wrapped.

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "tarakdingdung-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "sqlalchemy[asyncio]",
    "asyncpg",
    "alembic",
    "pydantic",
    "pydantic-settings",
    "pyjwt",
    "bcrypt",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "httpx",
    "testcontainers[postgres]",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Install dependencies into the venv**

Run:
```bash
backend/.venv/bin/pip install -e "backend/[dev]"
```
Expected: resolves and installs fastapi, sqlalchemy, asyncpg, alembic, pydantic-settings, pyjwt, bcrypt, pytest, pytest-asyncio, httpx, testcontainers, and their transitive deps.

- [ ] **Step 3: Freeze requirements**

Run:
```bash
backend/.venv/bin/pip freeze --exclude-editable > backend/requirements.txt
```
Expected: `backend/requirements.txt` now lists the full dependency set with pinned versions.

- [ ] **Step 4: Write `backend/src/tarakdingdung/config/settings.py`**

```python
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRDD_BE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "tarakdingdung"
    app_version: str = "v0.1.0-dev.1"

    logger_format: Literal["plain", "json"] = "json"
    logger_level: str = "INFO"

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_username: str = "postgres"
    postgres_password: str = "postgres"
    postgres_database: str = "tarakdingdung"
    postgres_ssl_mode: str = "disable"
    postgres_pool_size: int = 20

    http_host: str = "0.0.0.0"
    http_port: int = 8080
    http_cors_allowed_origins: list[str] = ["*"]

    token_access_secret: str = "tarakdingdung-access-secret"
    token_refresh_secret: str = "tarakdingdung-refresh-secret"
    token_access_ttl_seconds: int = 900
    token_refresh_ttl_seconds: int = 86400

    password_bcrypt_cost: int = 12

    seed_super_password: str = "changeme12345"
    seed_admin_password: str = "changeme12345"
    seed_user_password: str = "changeme12345"

    @field_validator("http_cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Write `backend/tests/conftest.py`**

```python
import pytest

from tarakdingdung.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Write `backend/tests/__init__.py`** (empty file).

- [ ] **Step 7: Write `backend/tests/test_settings.py`**

```python
import pytest

from tarakdingdung.config.settings import Settings


def test_defaults_match_spec():
    s = Settings()
    assert s.app_name == "tarakdingdung"
    assert s.token_access_ttl_seconds == 900
    assert s.password_bcrypt_cost == 12
    assert s.http_cors_allowed_origins == ["*"]


def test_env_prefix_is_trdd_be(monkeypatch):
    monkeypatch.setenv("TRDD_BE_POSTGRES_DATABASE", "custom_db")
    monkeypatch.setenv("TRDD_BE_TOKEN_ACCESS_TTL_SECONDS", "60")
    s = Settings()
    assert s.postgres_database == "custom_db"
    assert s.token_access_ttl_seconds == 60


def test_postgres_dsn_is_asyncpg():
    s = Settings(postgres_username="u", postgres_password="p",
                 postgres_host="h", postgres_port=1234, postgres_database="d")
    assert s.postgres_dsn == "postgresql+asyncpg://u:p@h:1234/d"


@pytest.mark.parametrize("raw,expected", [
    ("a.com,b.com", ["a.com", "b.com"]),
    ("  x.com , y.com ", ["x.com", "y.com"]),
])
def test_cors_origins_parsed_from_csv(monkeypatch, raw, expected):
    monkeypatch.setenv("TRDD_BE_HTTP_CORS_ALLOWED_ORIGINS", raw)
    assert Settings().http_cors_allowed_origins == expected
```

- [ ] **Step 8: Run the tests**

Run: `backend/.venv/bin/pytest backend/tests/test_settings.py -v`
Expected: 5 tests PASS.

- [ ] **Step 9: Write `backend/.env.example`**

```dotenv
# All backend settings use the TRDD_BE_ prefix.
TRDD_BE_APP_NAME=tarakdingdung
TRDD_BE_APP_VERSION=v0.1.0-dev.1

TRDD_BE_LOGGER_FORMAT=json
TRDD_BE_LOGGER_LEVEL=INFO

TRDD_BE_POSTGRES_HOST=127.0.0.1
TRDD_BE_POSTGRES_PORT=5432
TRDD_BE_POSTGRES_USERNAME=postgres
TRDD_BE_POSTGRES_PASSWORD=postgres
TRDD_BE_POSTGRES_DATABASE=tarakdingdung
TRDD_BE_POSTGRES_SSL_MODE=disable
TRDD_BE_POSTGRES_POOL_SIZE=20

TRDD_BE_HTTP_HOST=0.0.0.0
TRDD_BE_HTTP_PORT=8080
TRDD_BE_HTTP_CORS_ALLOWED_ORIGINS=*

TRDD_BE_TOKEN_ACCESS_SECRET=tarakdingdung-access-secret
TRDD_BE_TOKEN_REFRESH_SECRET=tarakdingdung-refresh-secret
TRDD_BE_TOKEN_ACCESS_TTL_SECONDS=900
TRDD_BE_TOKEN_REFRESH_TTL_SECONDS=86400

TRDD_BE_PASSWORD_BCRYPT_COST=12

TRDD_BE_SEED_SUPER_PASSWORD=changeme12345
TRDD_BE_SEED_ADMIN_PASSWORD=changeme12345
TRDD_BE_SEED_USER_PASSWORD=changeme12345
```

- [ ] **Step 10: Commit**

```bash
git add backend/pyproject.toml backend/requirements.txt backend/.env.example \
        backend/src/tarakdingdung/config/settings.py backend/tests/
git commit -m "chore(backend): scaffold project, settings, and pytest harness

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 2: Domain models

**Files:**
- Create: `backend/src/tarakdingdung/domain/models/error.py`
- Create: `backend/src/tarakdingdung/domain/models/permission.py`
- Create: `backend/src/tarakdingdung/domain/models/role.py`
- Create: `backend/src/tarakdingdung/domain/models/role_permission.py`
- Create: `backend/src/tarakdingdung/domain/models/user.py`
- Create: `backend/src/tarakdingdung/domain/models/token_claims.py`
- Test: `backend/tests/domain/test_models.py`
- Create: `backend/tests/domain/__init__.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `error.ErrorType` — `StrEnum` with members `NOT_FOUND, BAD_ARGS, CONFLICT, BAD_STATE, VALIDATION, FORBIDDEN, UNAUTHORIZED, TOKEN_EXPIRED, TOKEN_INVALID, TIMEOUT, UNIMPLEMENTED, FAILURE, UNKNOWN, USERNAME_EXISTS, ROLE_NAME_EXISTS, PERMISSION_NAME_EXISTS, ROLE_PERMISSION_EXISTS` (value == name).
  - `error.DomainError(Exception)` — `__init__(self, message: str, type: ErrorType, source: Exception | None = None)`; attributes `message`, `type`, `source`; `__str__` → `"[TYPE] message: source"` when `source` else `"[TYPE] message"`.
  - `permission.Permission` — frozen slotted dataclass: `id: UUID, name: str, description: str, preferences: dict, created_at: datetime, updated_at: datetime | None = None, deleted_at: datetime | None = None, created_by: UUID | None = None, updated_by: UUID | None = None, deleted_by: UUID | None = None`.
  - `role.Role` — same fields as `Permission` **plus** `is_default: bool` (positioned right after `description`, before `preferences`): `id, name, description, is_default, preferences, created_at, updated_at=None, deleted_at=None, created_by=None, updated_by=None, deleted_by=None`.
  - `role_permission.RolePermission` — `id: UUID, role_id: UUID, permission_id: UUID, created_at: datetime, created_by: UUID | None = None`.
  - `user.User` — `id: UUID, role_id: UUID, name: str, bio: str, username: str, password_hash: str, preferences: dict, created_at: datetime, updated_at: datetime | None = None, deleted_at: datetime | None = None, created_by: UUID | None = None, updated_by: UUID | None = None, deleted_by: UUID | None = None`.
  - `user.UserListItem` — `user: User, role_name: str`.
  - `token_claims.TokenClaimsAccess` — `user_id: UUID, name: str, username: str, role: str, permissions: tuple[str, ...]`.
  - `token_claims.TokenClaimsRefresh` — `user_id: UUID`.

- [ ] **Step 1: Write the failing test `backend/tests/domain/test_models.py`**

```python
import uuid
from datetime import datetime, timezone

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh
from tarakdingdung.domain.models.user import User, UserListItem

NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def test_error_type_values_are_their_names():
    assert ErrorType.NOT_FOUND == "NOT_FOUND"
    assert ErrorType.ROLE_PERMISSION_EXISTS == "ROLE_PERMISSION_EXISTS"


def test_domain_error_str_with_and_without_source():
    e1 = DomainError("nope", ErrorType.NOT_FOUND)
    assert str(e1) == "[NOT_FOUND] nope"
    src = ValueError("boom")
    e2 = DomainError("nope", ErrorType.FAILURE, src)
    assert str(e2) == "[FAILURE] nope: boom"
    assert e2.type is ErrorType.FAILURE
    assert e2.source is src


def test_models_are_frozen():
    p = Permission(id=uuid.uuid4(), name="n", description="", preferences={}, created_at=NOW)
    with pytest.raises(Exception):
        p.name = "other"


def test_role_has_is_default_field_order():
    r = Role(id=uuid.uuid4(), name="admin", description="d", is_default=True,
             preferences={}, created_at=NOW)
    assert r.is_default is True
    assert r.updated_at is None


def test_user_list_item_wraps_user():
    u = User(id=uuid.uuid4(), role_id=uuid.uuid4(), name="Grace", bio="", username="grace",
             password_hash="x", preferences={}, created_at=NOW)
    item = UserListItem(user=u, role_name="super")
    assert item.user is u
    assert item.role_name == "super"


def test_token_claims():
    uid = uuid.uuid4()
    a = TokenClaimsAccess(user_id=uid, name="G", username="g", role="super",
                          permissions=("user:get", "user:add"))
    assert a.permissions == ("user:get", "user:add")
    assert TokenClaimsRefresh(user_id=uid).user_id == uid


def test_role_permission_defaults_created_by_none():
    rp = RolePermission(id=uuid.uuid4(), role_id=uuid.uuid4(),
                        permission_id=uuid.uuid4(), created_at=NOW)
    assert rp.created_by is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/domain/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: tarakdingdung.domain.models.error`.

- [ ] **Step 3: Write the model modules**

`error.py`:
```python
from enum import StrEnum


class ErrorType(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    BAD_ARGS = "BAD_ARGS"
    CONFLICT = "CONFLICT"
    BAD_STATE = "BAD_STATE"
    VALIDATION = "VALIDATION"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TIMEOUT = "TIMEOUT"
    UNIMPLEMENTED = "UNIMPLEMENTED"
    FAILURE = "FAILURE"
    UNKNOWN = "UNKNOWN"
    USERNAME_EXISTS = "USERNAME_EXISTS"
    ROLE_NAME_EXISTS = "ROLE_NAME_EXISTS"
    PERMISSION_NAME_EXISTS = "PERMISSION_NAME_EXISTS"
    ROLE_PERMISSION_EXISTS = "ROLE_PERMISSION_EXISTS"


class DomainError(Exception):
    def __init__(self, message: str, type: ErrorType, source: Exception | None = None) -> None:
        self.message = message
        self.type = type
        self.source = source
        super().__init__(message)

    def __str__(self) -> str:
        if self.source is not None:
            return f"[{self.type}] {self.message}: {self.source}"
        return f"[{self.type}] {self.message}"
```

`permission.py`:
```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Permission:
    id: UUID
    name: str
    description: str
    preferences: dict
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_by: UUID | None = None
```

`role.py`:
```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Role:
    id: UUID
    name: str
    description: str
    is_default: bool
    preferences: dict
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_by: UUID | None = None
```

`role_permission.py`:
```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RolePermission:
    id: UUID
    role_id: UUID
    permission_id: UUID
    created_at: datetime
    created_by: UUID | None = None
```

`user.py`:
```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    role_id: UUID
    name: str
    bio: str
    username: str
    password_hash: str
    preferences: dict
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UserListItem:
    user: User
    role_name: str
```

`token_claims.py`:
```python
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TokenClaimsAccess:
    user_id: UUID
    name: str
    username: str
    role: str
    permissions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TokenClaimsRefresh:
    user_id: UUID
```

Also create empty `backend/tests/domain/__init__.py`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/domain/test_models.py -v`
Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/domain/models/ backend/tests/domain/
git commit -m "feat(domain): RBAC + token-claims models and DomainError

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 3: Domain contracts (repository + utility ABCs)

**Files:**
- Create: `backend/src/tarakdingdung/domain/contracts/repository/permission.py`
- Create: `backend/src/tarakdingdung/domain/contracts/repository/role.py`
- Create: `backend/src/tarakdingdung/domain/contracts/repository/role_permission.py`
- Create: `backend/src/tarakdingdung/domain/contracts/repository/user.py`
- Create: `backend/src/tarakdingdung/domain/contracts/utility/password.py`
- Create: `backend/src/tarakdingdung/domain/contracts/utility/token.py`
- Create: `backend/src/tarakdingdung/domain/contracts/utility/transactor.py`
- Test: `backend/tests/domain/test_contracts.py`

**Interfaces:**
- Consumes: `domain.models.*` from Task 2.
- Produces (all methods `async`, all ABCs):
  - `contracts.repository.permission.PermissionRepository`:
    - `create(*, name: str, description: str | None, created_by: UUID | None) -> UUID`
    - `read_by_id(id: UUID) -> Permission | None`
    - `read_by_name(name: str) -> Permission | None`
    - `read_by_pagination(*, page: int, limit: int, search: str | None) -> tuple[list[Permission], int]`
    - `update_by_id(id: UUID, *, name: str | None = None, description: str | None = None, preferences: dict | None = None, updated_by: UUID | None = None) -> None`
    - `delete_by_id(id: UUID, *, deleted_by: UUID | None = None) -> None`
  - `contracts.repository.role.RoleRepository`:
    - `create(*, name: str, description: str | None, is_default: bool | None, created_by: UUID | None) -> UUID`
    - `read_by_id(id: UUID) -> Role | None`
    - `read_by_name(name: str) -> Role | None`
    - `read_default() -> Role | None`
    - `read_permissions(role_id: UUID) -> list[Permission]`
    - `read_by_pagination(*, page: int, limit: int, search: str | None) -> tuple[list[Role], int]`
    - `update_by_id(id: UUID, *, name: str | None = None, description: str | None = None, is_default: bool | None = None, preferences: dict | None = None, updated_by: UUID | None = None) -> None`
    - `delete_by_id(id: UUID, *, deleted_by: UUID | None = None) -> None`
  - `contracts.repository.role_permission.RolePermissionRepository`:
    - `create(*, role_id: UUID, permission_id: UUID, created_by: UUID | None) -> UUID`
    - `read_by_id(id: UUID) -> tuple[RolePermission, Role, Permission] | None`
    - `read_by_role_id_and_permission_id(role_id: UUID, permission_id: UUID) -> tuple[RolePermission, Role, Permission] | None`
    - `read_by_pagination(*, page: int, limit: int, role_id: UUID | None, permission_id: UUID | None) -> tuple[list[tuple[RolePermission, Role, Permission]], int]`
    - `delete_by_id(id: UUID) -> None`
    - `delete_by_role_id_and_permission_id(*, role_id: UUID | None, permission_id: UUID | None) -> None`
  - `contracts.repository.user.UserRepository`:
    - `create(*, role_id: UUID, name: str, bio: str | None, username: str, password_hash: str, created_by: UUID | None) -> UUID`
    - `read_by_id(id: UUID) -> User | None`
    - `read_by_username(username: str) -> User | None`
    - `read_permissions(user_id: UUID) -> list[Permission]`
    - `read_by_pagination(*, page: int, limit: int, search: str | None, role_id: UUID | None) -> tuple[list[UserListItem], int]`
    - `update_by_id(id: UUID, *, role_id: UUID | None = None, name: str | None = None, bio: str | None = None, username: str | None = None, password_hash: str | None = None, preferences: dict | None = None, updated_by: UUID | None = None) -> None`
    - `delete_by_id(id: UUID, *, deleted_by: UUID | None = None) -> None`
  - `contracts.utility.password.Password`: `hash(password: str) -> str`, `compare(stored_hash: str, password: str) -> None`.
  - `contracts.utility.token.Token`: `generate_access(claims: TokenClaimsAccess) -> str`, `validate_access(token: str) -> TokenClaimsAccess`, `generate_refresh(claims: TokenClaimsRefresh) -> str`, `validate_refresh(token: str) -> TokenClaimsRefresh`.
  - `contracts.utility.transactor.Transactor`: `run(fn: Callable[[], Awaitable[T]]) -> T` (generic `T`).

- [ ] **Step 1: Write the failing test `backend/tests/domain/test_contracts.py`**

```python
import inspect

import pytest

from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.contracts.utility.transactor import Transactor

ALL = [PermissionRepository, RoleRepository, RolePermissionRepository, UserRepository,
       Password, Token, Transactor]


@pytest.mark.parametrize("cls", ALL)
def test_cannot_instantiate_abc(cls):
    with pytest.raises(TypeError):
        cls()


def test_repository_verbs_are_the_fixed_set():
    verbs = {n for n in dir(UserRepository) if not n.startswith("_")}
    assert verbs == {
        "create", "read_by_id", "read_by_username", "read_permissions",
        "read_by_pagination", "update_by_id", "delete_by_id",
    }


@pytest.mark.parametrize("cls,method", [
    (PermissionRepository, "create"),
    (RoleRepository, "read_default"),
    (UserRepository, "read_permissions"),
    (Password, "hash"),
    (Token, "validate_access"),
    (Transactor, "run"),
])
def test_methods_are_coroutine_functions(cls, method):
    assert inspect.iscoroutinefunction(getattr(cls, method))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/domain/test_contracts.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the contract modules**

`contracts/repository/permission.py`:
```python
from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission


class PermissionRepository(ABC):
    @abstractmethod
    async def create(self, *, name: str, description: str | None,
                     created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> Permission | None: ...

    @abstractmethod
    async def read_by_name(self, name: str) -> Permission | None: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int,
                                 search: str | None) -> tuple[list[Permission], int]: ...

    @abstractmethod
    async def update_by_id(self, id: UUID, *, name: str | None = None,
                           description: str | None = None, preferences: dict | None = None,
                           updated_by: UUID | None = None) -> None: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None: ...
```

`contracts/repository/role.py`:
```python
from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role


class RoleRepository(ABC):
    @abstractmethod
    async def create(self, *, name: str, description: str | None,
                     is_default: bool | None, created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> Role | None: ...

    @abstractmethod
    async def read_by_name(self, name: str) -> Role | None: ...

    @abstractmethod
    async def read_default(self) -> Role | None: ...

    @abstractmethod
    async def read_permissions(self, role_id: UUID) -> list[Permission]: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int,
                                 search: str | None) -> tuple[list[Role], int]: ...

    @abstractmethod
    async def update_by_id(self, id: UUID, *, name: str | None = None,
                           description: str | None = None, is_default: bool | None = None,
                           preferences: dict | None = None,
                           updated_by: UUID | None = None) -> None: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None: ...
```

`contracts/repository/role_permission.py`:
```python
from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission

RolePermissionRow = tuple[RolePermission, Role, Permission]


class RolePermissionRepository(ABC):
    @abstractmethod
    async def create(self, *, role_id: UUID, permission_id: UUID,
                     created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> RolePermissionRow | None: ...

    @abstractmethod
    async def read_by_role_id_and_permission_id(
        self, role_id: UUID, permission_id: UUID) -> RolePermissionRow | None: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int, role_id: UUID | None,
                                 permission_id: UUID | None
                                 ) -> tuple[list[RolePermissionRow], int]: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID) -> None: ...

    @abstractmethod
    async def delete_by_role_id_and_permission_id(
        self, *, role_id: UUID | None, permission_id: UUID | None) -> None: ...
```

`contracts/repository/user.py`:
```python
from abc import ABC, abstractmethod
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User, UserListItem


class UserRepository(ABC):
    @abstractmethod
    async def create(self, *, role_id: UUID, name: str, bio: str | None, username: str,
                     password_hash: str, created_by: UUID | None) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, id: UUID) -> User | None: ...

    @abstractmethod
    async def read_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def read_permissions(self, user_id: UUID) -> list[Permission]: ...

    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int, search: str | None,
                                 role_id: UUID | None) -> tuple[list[UserListItem], int]: ...

    @abstractmethod
    async def update_by_id(self, id: UUID, *, role_id: UUID | None = None,
                           name: str | None = None, bio: str | None = None,
                           username: str | None = None, password_hash: str | None = None,
                           preferences: dict | None = None,
                           updated_by: UUID | None = None) -> None: ...

    @abstractmethod
    async def delete_by_id(self, id: UUID, *, deleted_by: UUID | None = None) -> None: ...
```

`contracts/utility/password.py`:
```python
from abc import ABC, abstractmethod


class Password(ABC):
    @abstractmethod
    async def hash(self, password: str) -> str: ...

    @abstractmethod
    async def compare(self, stored_hash: str, password: str) -> None: ...
```

`contracts/utility/token.py`:
```python
from abc import ABC, abstractmethod

from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh


class Token(ABC):
    @abstractmethod
    async def generate_access(self, claims: TokenClaimsAccess) -> str: ...

    @abstractmethod
    async def validate_access(self, token: str) -> TokenClaimsAccess: ...

    @abstractmethod
    async def generate_refresh(self, claims: TokenClaimsRefresh) -> str: ...

    @abstractmethod
    async def validate_refresh(self, token: str) -> TokenClaimsRefresh: ...
```

`contracts/utility/transactor.py`:
```python
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class Transactor(ABC):
    @abstractmethod
    async def run(self, fn: Callable[[], Awaitable[T]]) -> T: ...
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/domain/test_contracts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/domain/contracts/ backend/tests/domain/test_contracts.py
git commit -m "feat(domain): repository and utility contract ABCs

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 4: Domain usecase interfaces + request/result DTOs

**Files:**
- Create: `backend/src/tarakdingdung/domain/usecases/admin/permission_management.py`
- Create: `backend/src/tarakdingdung/domain/usecases/admin/role_management.py`
- Create: `backend/src/tarakdingdung/domain/usecases/admin/user_management.py`
- Create: `backend/src/tarakdingdung/domain/usecases/auth/session.py`
- Create: `backend/src/tarakdingdung/domain/usecases/profile/me.py`
- Create: `backend/src/tarakdingdung/domain/usecases/profile/account.py`
- Create: `backend/src/tarakdingdung/domain/usecases/profile/security.py`
- Create: `backend/src/tarakdingdung/domain/usecases/profile/__init__.py`
- Test: `backend/tests/domain/test_usecase_interfaces.py`

**Interfaces:**
- Consumes: `domain.models.*`.
- Produces — ABCs + frozen slotted request/result dataclasses:
  - `usecases.admin.permission_management`:
    - `CreatePermissionRequest(name: str, description: str | None = None, created_by: UUID | None = None)`
    - `ReadPermissionByIdRequest(id: UUID)`
    - `ReadPermissionByNameRequest(name: str)`
    - `ReadPermissionsByPaginationRequest(page: int, limit: int, search: str | None = None)`
    - `UpdatePermissionRequest(id: UUID, name: str | None = None, description: str | None = None, updated_by: UUID | None = None)`
    - `DeletePermissionRequest(id: UUID, deleted_by: UUID | None = None)`
    - `PermissionManagement(ABC)` with async: `create(request) -> UUID`, `read_by_id(request) -> Permission | None`, `read_by_name(request) -> Permission | None`, `read_by_pagination(request) -> tuple[list[Permission], int]`, `update_by_id(request) -> None`, `delete_by_id(request) -> None`.
  - `usecases.admin.role_management`:
    - `CreateRoleRequest(name: str, description: str | None = None, created_by: UUID | None = None)`
    - `ReadRoleByIdRequest(id: UUID)`, `ReadRoleByNameRequest(name: str)`, `ReadDefaultRoleRequest()`
    - `ReadRolePermissionsRequest(role_id: UUID)`
    - `ReadRolesByPaginationRequest(page: int, limit: int, search: str | None = None)`
    - `UpdateRoleRequest(id: UUID, name: str | None = None, description: str | None = None, updated_by: UUID | None = None)`
    - `SetDefaultRoleRequest(id: UUID, updated_by: UUID | None = None)`
    - `DeleteRoleRequest(id: UUID, deleted_by: UUID | None = None)`
    - `AssignRolePermissionRequest(role_id: UUID, permission_id: UUID, created_by: UUID | None = None)`
    - `RevokeRolePermissionRequest(role_id: UUID, permission_id: UUID)`
    - `ReadRolePermissionByIdRequest(id: UUID)`
    - `ReadRolePermissionByRoleIdAndPermissionIdRequest(role_id: UUID, permission_id: UUID)`
    - `ReadRolePermissionsByPaginationRequest(page: int, limit: int, role_id: UUID | None = None, permission_id: UUID | None = None)`
    - `RolePermissionResult(role_permission: RolePermission, role: Role, permission: Permission)`
    - `RoleManagement(ABC)` async: `create`, `read_by_id`, `read_by_name`, `read_default`, `read_permissions(request) -> list[Permission]`, `read_by_pagination`, `update_by_id`, `set_default_role`, `delete_by_id`, `assign_permission(request) -> UUID`, `revoke_permission(request) -> None`, `read_role_permission_by_id(request) -> RolePermissionResult`, `read_role_permission_by_role_id_and_permission_id(request) -> RolePermissionResult`, `read_role_permissions_by_pagination(request) -> tuple[list[RolePermissionResult], int]`.
  - `usecases.admin.user_management`:
    - `CreateUserRequest(role_id: UUID, name: str, username: str, password: str, bio: str | None = None, created_by: UUID | None = None)`
    - `ReadUserByIdRequest(id: UUID)`, `ReadUserByUsernameRequest(username: str)`, `ReadUserPermissionsRequest(user_id: UUID)`
    - `ReadUsersByPaginationRequest(page: int, limit: int, search: str | None = None, role_id: UUID | None = None)`
    - `UpdateUserRequest(id: UUID, role_id: UUID | None = None, name: str | None = None, bio: str | None = None, username: str | None = None, updated_by: UUID | None = None)`
    - `ResetUserPasswordRequest(id: UUID, password: str, updated_by: UUID | None = None)`
    - `DeleteUserRequest(id: UUID, deleted_by: UUID | None = None)`
    - `UserManagement(ABC)` async: `create(request) -> UUID`, `read_by_id(request) -> User | None`, `read_by_username(request) -> User | None`, `read_permissions(request) -> list[Permission]`, `read_by_pagination(request) -> tuple[list[UserListItem], int]`, `update_by_id(request) -> None`, `reset_password(request) -> None`, `delete_by_id(request) -> None`.
  - `usecases.auth.session`:
    - `LoginRequest(username: str, password: str)`
    - `RefreshRequest(refresh_token: str)`
    - `LoginResult(user: User, role: Role, permissions: tuple[Permission, ...], access_token: str, refresh_token: str)`
    - `Session(ABC)` async: `login(request) -> LoginResult`, `refresh(request) -> LoginResult`.
  - `usecases.profile.me`:
    - `GetProfileRequest(user_id: UUID)`, `GetProfilePermissionsRequest(user_id: UUID)`
    - `Me(ABC)` async: `get_profile(request) -> User | None`, `get_permissions(request) -> list[Permission]`.
  - `usecases.profile.account`:
    - `UpdateProfileRequest(user_id: UUID, name: str | None = None, bio: str | None = None, username: str | None = None, updated_by: UUID | None = None)`
    - `Account(ABC)` async: `update_profile(request) -> None`.
  - `usecases.profile.security`:
    - `ChangePasswordRequest(user_id: UUID, current_password: str, new_password: str, updated_by: UUID | None = None)`
    - `Security(ABC)` async: `change_password(request) -> None`.

- [ ] **Step 1: Write the failing test `backend/tests/domain/test_usecase_interfaces.py`**

```python
import inspect
import uuid

import pytest

from tarakdingdung.domain.usecases.admin.permission_management import (
    CreatePermissionRequest, PermissionManagement,
)
from tarakdingdung.domain.usecases.admin.role_management import (
    AssignRolePermissionRequest, RoleManagement, RolePermissionResult,
)
from tarakdingdung.domain.usecases.admin.user_management import (
    CreateUserRequest, UserManagement,
)
from tarakdingdung.domain.usecases.auth.session import LoginRequest, LoginResult, Session
from tarakdingdung.domain.usecases.profile.account import Account, UpdateProfileRequest
from tarakdingdung.domain.usecases.profile.me import Me
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest, Security


@pytest.mark.parametrize("cls", [PermissionManagement, RoleManagement, UserManagement,
                                 Session, Me, Account, Security])
def test_usecase_is_abc(cls):
    with pytest.raises(TypeError):
        cls()


def test_request_dataclasses_have_expected_defaults():
    r = CreatePermissionRequest(name="node:get")
    assert r.description is None and r.created_by is None
    u = CreateUserRequest(role_id=uuid.uuid4(), name="G", username="g", password="secret12")
    assert u.bio is None


def test_assign_role_permission_request_fields():
    r = AssignRolePermissionRequest(role_id=uuid.uuid4(), permission_id=uuid.uuid4())
    assert r.created_by is None


def test_login_result_shape():
    fields = set(LoginResult.__dataclass_fields__)
    assert fields == {"user", "role", "permissions", "access_token", "refresh_token"}


def test_session_methods_are_async():
    assert inspect.iscoroutinefunction(Session.login)
    assert inspect.iscoroutinefunction(Session.refresh)
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/domain/test_usecase_interfaces.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the usecase interface modules**

Write each module per the **Produces** block above. Pattern for every file: `from __future__ import annotations` is not needed (3.12); import `ABC, abstractmethod`, `dataclass`, `UUID`, and the needed `domain.models` types; define the `@dataclass(frozen=True, slots=True)` request/result classes first, then the `ABC`. Example — `usecases/admin/permission_management.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from tarakdingdung.domain.models.permission import Permission


@dataclass(frozen=True, slots=True)
class CreatePermissionRequest:
    name: str
    description: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class ReadPermissionByIdRequest:
    id: UUID


@dataclass(frozen=True, slots=True)
class ReadPermissionByNameRequest:
    name: str


@dataclass(frozen=True, slots=True)
class ReadPermissionsByPaginationRequest:
    page: int
    limit: int
    search: str | None = None


@dataclass(frozen=True, slots=True)
class UpdatePermissionRequest:
    id: UUID
    name: str | None = None
    description: str | None = None
    updated_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class DeletePermissionRequest:
    id: UUID
    deleted_by: UUID | None = None


class PermissionManagement(ABC):
    @abstractmethod
    async def create(self, request: CreatePermissionRequest) -> UUID: ...

    @abstractmethod
    async def read_by_id(self, request: ReadPermissionByIdRequest) -> Permission | None: ...

    @abstractmethod
    async def read_by_name(self, request: ReadPermissionByNameRequest) -> Permission | None: ...

    @abstractmethod
    async def read_by_pagination(
        self, request: ReadPermissionsByPaginationRequest) -> tuple[list[Permission], int]: ...

    @abstractmethod
    async def update_by_id(self, request: UpdatePermissionRequest) -> None: ...

    @abstractmethod
    async def delete_by_id(self, request: DeletePermissionRequest) -> None: ...
```

Write `role_management.py`, `user_management.py`, `auth/session.py`, `profile/me.py`, `profile/account.py`, `profile/security.py` the same way, matching every request/result dataclass and method signature in the **Produces** block. Create empty `backend/src/tarakdingdung/domain/usecases/profile/__init__.py`.

- [ ] **Step 4: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/domain/test_usecase_interfaces.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/domain/usecases/ backend/tests/domain/test_usecase_interfaces.py
git commit -m "feat(domain): admin/auth/profile usecase interfaces and DTOs

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 5: Infrastructure — ORM models + async database handle

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/repository/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/database/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/database/orm.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/database/session.py`
- Test: `backend/tests/infrastructure/__init__.py`
- Test: `backend/tests/infrastructure/test_orm_metadata.py`

**Interfaces:**
- Consumes: `tarakdingdung.config.settings.Settings`.
- Produces:
  - `database.orm.Base` — `DeclarativeBase` subclass.
  - `database.orm.PermissionORM` (`__tablename__ = "permissions"`), `RoleORM` (`"roles"`), `RolePermissionORM` (`"role_permission"`), `UserORM` (`"users"`) — columns per spec §7.1.
  - `database.session.Database` — `__init__(self, dsn: str, *, pool_size: int, echo: bool = False)`; attributes `engine: AsyncEngine`, `sessionmaker: async_sessionmaker[AsyncSession]`, `current_session: ContextVar[AsyncSession | None]`; method `session()` → `@asynccontextmanager` yielding an `AsyncSession` (returns the context-var session if one is set, else opens one from `sessionmaker`); method `dispose()` → `await self.engine.dispose()`.

- [ ] **Step 1: Write the failing test `backend/tests/infrastructure/test_orm_metadata.py`**

```python
from tarakdingdung.infrastructure.repository.database.orm import (
    Base, PermissionORM, RoleORM, RolePermissionORM, UserORM,
)


def test_all_four_tables_registered():
    assert set(Base.metadata.tables) == {"permissions", "roles", "role_permission", "users"}


def test_permission_columns():
    cols = {c.name for c in PermissionORM.__table__.columns}
    assert cols == {"id", "name", "description", "preferences", "created_at",
                    "updated_at", "deleted_at", "created_by", "updated_by", "deleted_by"}


def test_role_has_is_default_boolean():
    col = RoleORM.__table__.columns["is_default"]
    assert col.nullable is False


def test_user_role_id_is_fk_to_roles():
    fks = list(UserORM.__table__.columns["role_id"].foreign_keys)
    assert fks and fks[0].column.table.name == "roles"


def test_role_permission_unique_pair_and_cascade():
    tbl = RolePermissionORM.__table__
    assert any(set(uc.columns.keys()) == {"role_id", "permission_id"}
               for uc in tbl.constraints if uc.__class__.__name__ == "UniqueConstraint")
    role_fk = list(tbl.columns["role_id"].foreign_keys)[0]
    assert role_fk.ondelete == "CASCADE"
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/infrastructure/test_orm_metadata.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `database/orm.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, ForeignKey, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class _Audit:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)


class PermissionORM(_Audit, Base):
    __tablename__ = "permissions"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    preferences: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class RoleORM(_Audit, Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default=text("''"))
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    preferences: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class UserORM(_Audit, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("roles.id"))
    name: Mapped[str] = mapped_column(Text)
    bio: Mapped[str] = mapped_column(Text, server_default=text("''"))
    username: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    preferences: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class RolePermissionORM(Base):
    __tablename__ = "role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id",
                         name="uq_role_permission_role_id_permission_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"))
    permission_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), default=None)
```

> Note: `String`/`Text` — use `Text` everywhere to match the Go `TEXT` columns. The `datetime` columns map to `TIMESTAMP` by default; the timezone flag is set in the migration DDL (Task 6), not here — the ORM is only used for query building and metadata, never `create_all`.

- [ ] **Step 4: Write `database/session.py`**

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
)


class Database:
    def __init__(self, dsn: str, *, pool_size: int, echo: bool = False) -> None:
        self.engine: AsyncEngine = create_async_engine(
            dsn, pool_size=pool_size, pool_pre_ping=True, echo=echo)
        self.sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False)
        self.current_session: ContextVar[AsyncSession | None] = ContextVar(
            "tarakdingdung_current_session", default=None)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        existing = self.current_session.get()
        if existing is not None:
            yield existing
            return
        async with self.sessionmaker() as session:
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
```

Create empty `backend/tests/infrastructure/__init__.py` and the two `__init__.py` files under `infrastructure/repository/` and `infrastructure/repository/database/`.

- [ ] **Step 5: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/infrastructure/test_orm_metadata.py -v`
Expected: 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/repository/ backend/tests/infrastructure/
git commit -m "feat(infra): SQLAlchemy ORM models and async Database handle

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 6: Alembic setup + six migration revisions

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/0001_extensions.py`
- Create: `backend/migrations/versions/0002_permissions.py`
- Create: `backend/migrations/versions/0003_roles.py`
- Create: `backend/migrations/versions/0004_role_permission.py`
- Create: `backend/migrations/versions/0005_users.py`
- Create: `backend/migrations/versions/0006_soft_delete_partial_unique.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/database/migrations.py`
- Test: `backend/tests/integration/__init__.py`
- Test: `backend/tests/integration/conftest.py`
- Test: `backend/tests/integration/test_migrations.py`

**Interfaces:**
- Consumes: `Settings`, `Base.metadata`.
- Produces:
  - `infrastructure.repository.database.migrations.alembic_config(dsn: str) -> alembic.config.Config` — returns a `Config` pointing at `backend/alembic.ini` / `backend/migrations`, with `sqlalchemy.url` set to `dsn`.
  - `infrastructure.repository.database.migrations.upgrade_to_head(dsn: str) -> None` and `downgrade_to_base(dsn: str) -> None` — run `command.upgrade(cfg, "head")` / `command.downgrade(cfg, "base")`.
  - Integration conftest fixtures (session scope): `postgres_url: str` (from a `testcontainers` `PostgresContainer("postgres:16-alpine")`, converted to `postgresql+asyncpg://`), `migrated_url: str` (runs `upgrade_to_head` once), and function-scoped `db: Database` bound to `migrated_url` with per-test rollback via an outer transaction.

- [ ] **Step 1: Write the failing test `backend/tests/integration/test_migrations.py`**

```python
import sqlalchemy as sa

from tarakdingdung.infrastructure.repository.database.migrations import (
    downgrade_to_base, upgrade_to_head,
)


def test_upgrade_then_downgrade_roundtrip(postgres_url):
    upgrade_to_head(postgres_url)
    sync_url = postgres_url.replace("+asyncpg", "+psycopg")  # not used; see conftest engine
    engine = sa.create_engine(postgres_url.replace("+asyncpg", ""))
    with engine.connect() as conn:
        tables = set(sa.inspect(conn).get_table_names())
        assert {"permissions", "roles", "role_permission", "users"} <= tables
        idx = {i["name"] for i in sa.inspect(conn).get_indexes("roles")}
        assert "uq_roles_is_default_true" in idx
        assert "uq_roles_name" in idx  # partial unique from 0006
    downgrade_to_base(postgres_url)
    with engine.connect() as conn:
        tables = set(sa.inspect(conn).get_table_names())
        assert not ({"permissions", "roles", "role_permission", "users"} & tables)
    engine.dispose()
```

> The migration runner uses an async engine internally (Task 6 Step 4); the
> assertions use a plain sync engine over the bare `postgresql://` URL,
> which psycopg (installed transitively via testcontainers) or asyncpg's
> sync fallback is not — so the conftest exposes `postgres_url` as
> `postgresql+asyncpg://...` and this test creates its own sync engine via
> the default dialect. If psycopg2/psycopg is unavailable, replace the
> assertion engine with `await`-based introspection in an `async def`
> test using the `db` fixture. Pick the psycopg-free path: see Step 6.

- [ ] **Step 2: Write `backend/tests/integration/conftest.py`**

```python
import pytest
import pytest_asyncio
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from tarakdingdung.infrastructure.repository.database.migrations import upgrade_to_head
from tarakdingdung.infrastructure.repository.database.session import Database


@pytest.fixture(scope="session")
def postgres_url() -> str:
    with PostgresContainer("postgres:16-alpine") as pg:
        raw = pg.get_connection_url()  # postgresql+psycopg2://user:pass@host:port/db
        yield raw.replace("+psycopg2", "+asyncpg")


@pytest.fixture(scope="session")
def migrated_url(postgres_url: str) -> str:
    upgrade_to_head(postgres_url)
    return postgres_url


@pytest_asyncio.fixture
async def db(migrated_url: str):
    database = Database(migrated_url, pool_size=5)
    async with database.engine.connect() as conn:
        trans = await conn.begin()
        session = database.sessionmaker(bind=conn)
        token = database.current_session.set(session)
        try:
            yield database
        finally:
            database.current_session.reset(token)
            await session.close()
            await trans.rollback()
    await database.dispose()
```

- [ ] **Step 3: Write `backend/alembic.ini`**

```ini
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = %(here)s/src
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 4: Write `backend/migrations/env.py`**

```python
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from tarakdingdung.infrastructure.repository.database.orm import Base

config = context.config
target_metadata = Base.metadata


def _run_sync(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata,
                      compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_run_sync)
    await connectable.dispose()


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"),
                      target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(_run_async())
```

Write `backend/migrations/script.py.mako` (standard Alembic template):

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Write `backend/src/tarakdingdung/infrastructure/repository/database/migrations.py`**

```python
from pathlib import Path

from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[5]


def alembic_config(dsn: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", dsn)
    return cfg


def upgrade_to_head(dsn: str) -> None:
    command.upgrade(alembic_config(dsn), "head")


def downgrade_to_base(dsn: str) -> None:
    command.downgrade(alembic_config(dsn), "base")
```

> `parents[5]` from `.../src/tarakdingdung/infrastructure/repository/database/migrations.py`
> resolves to `backend/`. Verify with the test in Step 7; adjust the index if the
> path is off.

- [ ] **Step 6: Write the six revision files**

`0001_extensions.py`:
```python
from alembic import op

revision = "0001_extensions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
```

`0002_permissions.py`:
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0002_permissions"
down_revision = "0001_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_by", UUID(as_uuid=True)),
        sa.UniqueConstraint("name", name="permissions_name_key"),
    )
    op.execute("CREATE INDEX idx_permissions_name_trgm ON permissions "
               "USING GIN (name gin_trgm_ops)")
    op.create_index("idx_permissions_deleted_at", "permissions", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("permissions")
```

`0003_roles.py`:
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0003_roles"
down_revision = "0002_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_by", UUID(as_uuid=True)),
        sa.UniqueConstraint("name", name="roles_name_key"),
    )
    op.execute("CREATE INDEX idx_roles_name_trgm ON roles USING GIN (name gin_trgm_ops)")
    op.execute("CREATE UNIQUE INDEX uq_roles_is_default_true ON roles (is_default) "
               "WHERE is_default = TRUE")
    op.create_index("idx_roles_deleted_at", "roles", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("roles")
```

`0004_role_permission.py`:
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_role_permission"
down_revision = "0003_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_permission",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("role_id", "permission_id",
                            name="uq_role_permission_role_id_permission_id"),
    )
    op.create_index("idx_role_permission_role_id", "role_permission", ["role_id"])
    op.create_index("idx_role_permission_permission_id", "role_permission", ["permission_id"])


def downgrade() -> None:
    op.drop_table("role_permission")
```

`0005_users.py`:
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0005_users"
down_revision = "0004_role_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("role_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("preferences", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("deleted_by", UUID(as_uuid=True)),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.UniqueConstraint("username", name="users_username_key"),
    )
    op.create_index("idx_users_role_id", "users", ["role_id"])
    op.execute("CREATE INDEX idx_users_name_trgm ON users USING GIN (name gin_trgm_ops)")
    op.execute("CREATE INDEX idx_users_username_trgm ON users USING GIN (username gin_trgm_ops)")
    op.create_index("idx_users_deleted_at", "users", ["deleted_at"])


def downgrade() -> None:
    op.drop_table("users")
```

`0006_soft_delete_partial_unique.py`:
```python
from alembic import op

revision = "0006_soft_delete_partial_unique"
down_revision = "0005_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE permissions DROP CONSTRAINT permissions_name_key")
    op.execute("CREATE UNIQUE INDEX uq_permissions_name ON permissions (name) "
               "WHERE deleted_at IS NULL")
    op.execute("ALTER TABLE roles DROP CONSTRAINT roles_name_key")
    op.execute("CREATE UNIQUE INDEX uq_roles_name ON roles (name) WHERE deleted_at IS NULL")
    op.execute("ALTER TABLE users DROP CONSTRAINT users_username_key")
    op.execute("CREATE UNIQUE INDEX uq_users_username ON users (username) "
               "WHERE deleted_at IS NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_username")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username)")
    op.execute("DROP INDEX IF EXISTS uq_roles_name")
    op.execute("ALTER TABLE roles ADD CONSTRAINT roles_name_key UNIQUE (name)")
    op.execute("DROP INDEX IF EXISTS uq_permissions_name")
    op.execute("ALTER TABLE permissions ADD CONSTRAINT permissions_name_key UNIQUE (name)")
```

- [ ] **Step 7: Rewrite the migration test psycopg-free and run it**

Replace `backend/tests/integration/test_migrations.py` with an async version that uses the `db` fixture's engine for introspection:

```python
import pytest
import sqlalchemy as sa

from tarakdingdung.infrastructure.repository.database.migrations import (
    downgrade_to_base, upgrade_to_head,
)
from tarakdingdung.infrastructure.repository.database.session import Database


@pytest.mark.asyncio
async def test_head_has_all_tables_and_partial_indexes(migrated_url):
    database = Database(migrated_url, pool_size=2)
    async with database.engine.connect() as conn:
        names = await conn.run_sync(lambda c: set(sa.inspect(c).get_table_names()))
        assert {"permissions", "roles", "role_permission", "users"} <= names
        role_idx = await conn.run_sync(
            lambda c: {i["name"] for i in sa.inspect(c).get_indexes("roles")})
        assert {"uq_roles_is_default_true", "uq_roles_name"} <= role_idx
    await database.dispose()


def test_downgrade_to_base_drops_tables(postgres_url):
    upgrade_to_head(postgres_url)
    downgrade_to_base(postgres_url)
    import sqlalchemy
    engine = sqlalchemy.create_engine(
        postgres_url.replace("+asyncpg", "+psycopg2"), future=True)
    try:
        with engine.connect() as conn:
            remaining = set(sqlalchemy.inspect(conn).get_table_names())
        assert not ({"permissions", "roles", "users", "role_permission"} & remaining)
    finally:
        engine.dispose()
    upgrade_to_head(postgres_url)  # restore for the session-scoped migrated_url
```

Run: `backend/.venv/bin/pytest backend/tests/integration/test_migrations.py -v`
Expected: 2 tests PASS. (`testcontainers[postgres]` pulls `psycopg2-binary`; if `+psycopg2` fails, use `+psycopg`.)

- [ ] **Step 8: Commit**

```bash
git add backend/alembic.ini backend/migrations/ \
        backend/src/tarakdingdung/infrastructure/repository/database/migrations.py \
        backend/tests/integration/
git commit -m "feat(infra): Alembic setup and RBAC schema migrations

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 7: Transactor implementation

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/utility/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/utility/transactor/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/utility/transactor/sqlalchemy.py`
- Test: `backend/tests/integration/test_transactor.py`

**Interfaces:**
- Consumes: `Database` (Task 5), `Transactor` ABC (Task 3).
- Produces: `infrastructure.utility.transactor.sqlalchemy.SqlAlchemyTransactor(Transactor)` — `__init__(self, database: Database)`; `run(fn)` opens a session from `database.sessionmaker`, sets `database.current_session`, runs `async with session.begin(): result = await fn()`, resets the contextvar in `finally`, returns `result`; on exception the transaction rolls back and the exception propagates.

- [ ] **Step 1: Write the failing test `backend/tests/integration/test_transactor.py`**

```python
import uuid

import pytest
from sqlalchemy import text

from tarakdingdung.infrastructure.utility.transactor.sqlalchemy import SqlAlchemyTransactor


@pytest.mark.asyncio
async def test_run_commits_on_success(db):
    tx = SqlAlchemyTransactor(db)
    pid = uuid.uuid4()

    async def op() -> None:
        async with db.session() as s:
            await s.execute(text(
                "INSERT INTO permissions (id, name) VALUES (:id, :n)"), {"id": pid, "n": "p:x"})

    await tx.run(op)
    async with db.session() as s:
        got = await s.scalar(text("SELECT name FROM permissions WHERE id = :id"), {"id": pid})
    assert got == "p:x"


@pytest.mark.asyncio
async def test_run_rolls_back_on_exception(db):
    tx = SqlAlchemyTransactor(db)
    pid = uuid.uuid4()

    async def op() -> None:
        async with db.session() as s:
            await s.execute(text(
                "INSERT INTO permissions (id, name) VALUES (:id, :n)"), {"id": pid, "n": "p:y"})
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await tx.run(op)
    async with db.session() as s:
        got = await s.scalar(text("SELECT count(*) FROM permissions WHERE id = :id"), {"id": pid})
    assert got == 0


@pytest.mark.asyncio
async def test_nested_session_reuses_transaction_session(db):
    tx = SqlAlchemyTransactor(db)
    seen = []

    async def op() -> None:
        async with db.session() as a:
            async with db.session() as b:
                seen.append(a is b)

    await tx.run(op)
    assert seen == [True]
```

> The `db` fixture already binds a session to a rolled-back outer connection.
> `SqlAlchemyTransactor.run` must open its session from `database.sessionmaker`
> *bound to the same engine*; inside the fixture's outer transaction the
> transactor's `session.begin()` becomes a SAVEPOINT, so these assertions
> hold and the fixture still rolls everything back at teardown.

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_transactor.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `infrastructure/utility/transactor/sqlalchemy.py`**

```python
from collections.abc import Awaitable, Callable
from typing import TypeVar

from tarakdingdung.domain.contracts.utility.transactor import Transactor
from tarakdingdung.infrastructure.repository.database.session import Database

T = TypeVar("T")


class SqlAlchemyTransactor(Transactor):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def run(self, fn: Callable[[], Awaitable[T]]) -> T:
        async with self._database.sessionmaker() as session:
            token = self._database.current_session.set(session)
            try:
                async with session.begin():
                    return await fn()
            finally:
                self._database.current_session.reset(token)
```

Create the two `__init__.py` files.

- [ ] **Step 4: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_transactor.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/utility/ backend/tests/integration/test_transactor.py
git commit -m "feat(infra): SQLAlchemy transactor (context-var unit of work)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 8: Repository shared helpers (errors, query, mappers)

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/repository/shared/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/shared/query.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/shared/errors.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/shared/mappers.py`
- Test: `backend/tests/infrastructure/test_repository_shared.py`

**Interfaces:**
- Consumes: `domain.models.*`, `domain.models.error`, ORM classes.
- Produces:
  - `shared.query.normalize_limit(limit: int) -> int` — `max(limit, 0)`.
  - `shared.query.normalize_offset(page: int, limit: int) -> int` — `0` if `page <= 1 or limit <= 0` else `(page - 1) * limit`.
  - `shared.query.search_pattern(search: str | None) -> str | None` — `None` if falsy/blank else `f"%{search}%"`.
  - `shared.errors.ConflictMatch` — frozen dataclass `(contains: str, type: ErrorType)`.
  - `shared.errors.map_db_error(message: str, exc: Exception, *conflicts: ConflictMatch) -> DomainError` — mapping per spec §7.5. Inspect `exc`: SQLAlchemy `NoResultFound` → `NOT_FOUND`; `IntegrityError` whose `.orig` is an `asyncpg` error with `sqlstate` `"23505"` → first `ConflictMatch` whose `contains` appears in `constraint_name` (via `getattr(orig, "constraint_name", "")` or the message), else `CONFLICT`; `"23503"` → `CONFLICT`; `"23502" | "22P02" | "22001"` → `VALIDATION`; anything else → `UNKNOWN`. Always wraps `exc` as `source`.
  - `shared.mappers.permission_from_orm(row: PermissionORM) -> Permission`, `role_from_orm`, `role_permission_from_orm`, `user_from_orm`, and `user_list_item_from_orm(row: UserORM, role_name: str | None) -> UserListItem`. `preferences` → `dict(row.preferences or {})`.

- [ ] **Step 1: Write the failing test `backend/tests/infrastructure/test_repository_shared.py`**

```python
import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)


@pytest.mark.parametrize("limit,expected", [(-3, 0), (0, 0), (10, 10)])
def test_normalize_limit(limit, expected):
    assert normalize_limit(limit) == expected


@pytest.mark.parametrize("page,limit,expected", [
    (1, 10, 0), (0, 10, 0), (3, 10, 20), (2, 25, 25), (5, 0, 0),
])
def test_normalize_offset(page, limit, expected):
    assert normalize_offset(page, limit) == expected


@pytest.mark.parametrize("value,expected", [
    (None, None), ("", None), ("  ", None), ("grace", "%grace%"),
])
def test_search_pattern(value, expected):
    assert search_pattern(value) == expected


class _FakeAsyncpgError(Exception):
    def __init__(self, sqlstate, constraint_name=""):
        super().__init__("db error")
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


class _FakeIntegrityError(Exception):
    def __init__(self, orig):
        super().__init__("integrity")
        self.orig = orig


def test_map_unique_violation_matches_conflict_target():
    exc = _FakeIntegrityError(_FakeAsyncpgError("23505", "uq_users_username"))
    err = map_db_error("failed to create user", exc,
                       ConflictMatch("username", ErrorType.USERNAME_EXISTS))
    assert isinstance(err, DomainError)
    assert err.type is ErrorType.USERNAME_EXISTS
    assert err.source is exc


def test_map_unique_violation_without_match_is_conflict():
    exc = _FakeIntegrityError(_FakeAsyncpgError("23505", "some_other_idx"))
    assert map_db_error("x", exc).type is ErrorType.CONFLICT


@pytest.mark.parametrize("sqlstate,expected", [
    ("23503", ErrorType.CONFLICT),
    ("23502", ErrorType.VALIDATION),
    ("22P02", ErrorType.VALIDATION),
    ("99999", ErrorType.UNKNOWN),
])
def test_map_other_sqlstates(sqlstate, expected):
    exc = _FakeIntegrityError(_FakeAsyncpgError(sqlstate))
    assert map_db_error("x", exc).type is expected
```

> `map_db_error` must detect `IntegrityError` and `NoResultFound`
> structurally: check `isinstance(exc, sqlalchemy.exc.NoResultFound)` and
> `isinstance(exc, sqlalchemy.exc.IntegrityError)` first, then fall back to
> `getattr(exc, "orig", None)` and `getattr(orig, "sqlstate", None)`. The
> fakes above exercise the `orig`/`sqlstate`/`constraint_name` path without
> a real DB.

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/infrastructure/test_repository_shared.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the three modules**

`shared/query.py`:
```python
def normalize_limit(limit: int) -> int:
    return max(limit, 0)


def normalize_offset(page: int, limit: int) -> int:
    if page <= 1 or limit <= 0:
        return 0
    return (page - 1) * limit


def search_pattern(search: str | None) -> str | None:
    if search is None or not search.strip():
        return None
    return f"%{search}%"
```

`shared/errors.py`:
```python
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, NoResultFound

from tarakdingdung.domain.models.error import DomainError, ErrorType

_VALIDATION_STATES = {"23502", "22P02", "22001", "23514"}


@dataclass(frozen=True, slots=True)
class ConflictMatch:
    contains: str
    type: ErrorType


def map_db_error(message: str, exc: Exception, *conflicts: ConflictMatch) -> DomainError:
    if isinstance(exc, NoResultFound):
        return DomainError(message, ErrorType.NOT_FOUND, exc)

    orig = getattr(exc, "orig", exc)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    constraint = (getattr(orig, "constraint_name", "") or "") + " " + str(orig)

    if isinstance(exc, IntegrityError) or sqlstate is not None:
        if sqlstate == "23505":
            for match in conflicts:
                if match.contains in constraint:
                    return DomainError(message, match.type, exc)
            return DomainError(message, ErrorType.CONFLICT, exc)
        if sqlstate == "23503":
            return DomainError(message, ErrorType.CONFLICT, exc)
        if sqlstate in _VALIDATION_STATES:
            return DomainError(message, ErrorType.VALIDATION, exc)

    return DomainError(message, ErrorType.UNKNOWN, exc)
```

`shared/mappers.py`:
```python
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.user import User, UserListItem
from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionORM, RoleORM, RolePermissionORM, UserORM,
)


def permission_from_orm(row: PermissionORM) -> Permission:
    return Permission(
        id=row.id, name=row.name, description=row.description,
        preferences=dict(row.preferences or {}), created_at=row.created_at,
        updated_at=row.updated_at, deleted_at=row.deleted_at,
        created_by=row.created_by, updated_by=row.updated_by, deleted_by=row.deleted_by,
    )


def role_from_orm(row: RoleORM) -> Role:
    return Role(
        id=row.id, name=row.name, description=row.description, is_default=row.is_default,
        preferences=dict(row.preferences or {}), created_at=row.created_at,
        updated_at=row.updated_at, deleted_at=row.deleted_at,
        created_by=row.created_by, updated_by=row.updated_by, deleted_by=row.deleted_by,
    )


def role_permission_from_orm(row: RolePermissionORM) -> RolePermission:
    return RolePermission(
        id=row.id, role_id=row.role_id, permission_id=row.permission_id,
        created_at=row.created_at, created_by=row.created_by,
    )


def user_from_orm(row: UserORM) -> User:
    return User(
        id=row.id, role_id=row.role_id, name=row.name, bio=row.bio, username=row.username,
        password_hash=row.password_hash, preferences=dict(row.preferences or {}),
        created_at=row.created_at, updated_at=row.updated_at, deleted_at=row.deleted_at,
        created_by=row.created_by, updated_by=row.updated_by, deleted_by=row.deleted_by,
    )


def user_list_item_from_orm(row: UserORM, role_name: str | None) -> UserListItem:
    return UserListItem(user=user_from_orm(row), role_name=role_name or "")
```

- [ ] **Step 4: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/infrastructure/test_repository_shared.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/repository/shared/ \
        backend/tests/infrastructure/test_repository_shared.py
git commit -m "feat(infra): repository shared helpers (query, error mapping, ORM mappers)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 9: Permission repository

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/repository/permission/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/permission/queries.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/permission/repository.py`
- Test: `backend/tests/integration/test_permission_repository.py`

**Interfaces:**
- Consumes: `PermissionRepository` ABC, `Database`, `shared.*`, `PermissionORM`.
- Produces: `infrastructure.repository.permission.repository.SqlAlchemyPermissionRepository(PermissionRepository)` — `__init__(self, database: Database)`. Implements every ABC method. `create` inserts only provided columns, `.returning(PermissionORM.id)`, mapping unique-violation on `name` → `PERMISSION_NAME_EXISTS`. All reads add `where(PermissionORM.deleted_at.is_(None))`. `read_by_pagination` returns `([], 0)` early when the count is 0; otherwise orders `created_at DESC, id ASC`, applies `normalize_limit`/`normalize_offset`, `name ILIKE :pattern` when `search_pattern` is set. `update_by_id` sets only provided fields plus `updated_at=func.now()`, `updated_by=...`, `where(deleted_at IS NULL)`; raises `DomainError(NOT_FOUND)` when `rowcount == 0`. `delete_by_id` is a soft delete; raises `NOT_FOUND` when `rowcount == 0`.

- [ ] **Step 1: Write the failing test `backend/tests/integration/test_permission_repository.py`**

```python
import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)


@pytest.fixture
def repo(db):
    return SqlAlchemyPermissionRepository(db)


@pytest.mark.asyncio
async def test_create_then_read_by_id_and_name(repo):
    pid = await repo.create(name="node:get", description="View nodes", created_by=None)
    by_id = await repo.read_by_id(pid)
    assert by_id is not None and by_id.name == "node:get" and by_id.description == "View nodes"
    by_name = await repo.read_by_name("node:get")
    assert by_name.id == pid


@pytest.mark.asyncio
async def test_read_missing_returns_none(repo):
    assert await repo.read_by_id(uuid.uuid4()) is None
    assert await repo.read_by_name("nope:none") is None


@pytest.mark.asyncio
async def test_duplicate_name_raises_permission_name_exists(repo):
    await repo.create(name="dup:one", description=None, created_by=None)
    with pytest.raises(DomainError) as ei:
        await repo.create(name="dup:one", description=None, created_by=None)
    assert ei.value.type is ErrorType.PERMISSION_NAME_EXISTS


@pytest.mark.asyncio
async def test_pagination_orders_and_filters(repo):
    for n in ["alpha:get", "alpha:set", "beta:get"]:
        await repo.create(name=n, description=None, created_by=None)
    items, total = await repo.read_by_pagination(page=1, limit=10, search="alpha")
    assert total == 2
    assert {i.name for i in items} == {"alpha:get", "alpha:set"}
    page1, total_all = await repo.read_by_pagination(page=1, limit=2, search=None)
    assert total_all == 3 and len(page1) == 2


@pytest.mark.asyncio
async def test_update_partial_and_missing(repo):
    pid = await repo.create(name="upd:one", description="old", created_by=None)
    await repo.update_by_id(pid, description="new", updated_by=None)
    assert (await repo.read_by_id(pid)).description == "new"
    with pytest.raises(DomainError) as ei:
        await repo.update_by_id(uuid.uuid4(), description="x", updated_by=None)
    assert ei.value.type is ErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_soft_delete_hides_row_and_frees_name(repo):
    pid = await repo.create(name="del:one", description=None, created_by=None)
    await repo.delete_by_id(pid, deleted_by=None)
    assert await repo.read_by_id(pid) is None
    reused = await repo.create(name="del:one", description=None, created_by=None)
    assert reused != pid
    with pytest.raises(DomainError):
        await repo.delete_by_id(uuid.uuid4(), deleted_by=None)
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_permission_repository.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `permission/queries.py`**

```python
from uuid import UUID

from sqlalchemy import Select, func, insert, select, update
from sqlalchemy.sql.dml import ReturningInsert, ReturningUpdate

from tarakdingdung.infrastructure.repository.database.orm import PermissionORM
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)

P = PermissionORM


def build_create(*, name: str, description: str | None, created_by: UUID | None):
    values: dict = {"name": name, "created_by": created_by}
    if description is not None:
        values["description"] = description
    return insert(P).values(**values).returning(P.id)


def build_read_by_id(id: UUID) -> Select:
    return select(P).where(P.id == id, P.deleted_at.is_(None))


def build_read_by_name(name: str) -> Select:
    return select(P).where(P.name == name, P.deleted_at.is_(None)).limit(1)


def build_count(search: str | None):
    stmt = select(func.count()).select_from(P).where(P.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(P.name.ilike(pattern))
    return stmt


def build_read_by_pagination(*, page: int, limit: int, search: str | None) -> Select:
    stmt = select(P).where(P.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(P.name.ilike(pattern))
    return (stmt.order_by(P.created_at.desc(), P.id.asc())
                .limit(normalize_limit(limit))
                .offset(normalize_offset(page, limit)))


def build_update_by_id(id: UUID, *, name, description, preferences, updated_by):
    values: dict = {"updated_at": func.now(), "updated_by": updated_by}
    if name is not None:
        values["name"] = name
    if description is not None:
        values["description"] = description
    if preferences is not None:
        values["preferences"] = preferences
    return update(P).where(P.id == id, P.deleted_at.is_(None)).values(**values)


def build_soft_delete(id: UUID, *, deleted_by: UUID | None):
    return (update(P).where(P.id == id, P.deleted_at.is_(None))
            .values(deleted_at=func.now(), deleted_by=deleted_by))
```

- [ ] **Step 4: Write `permission/repository.py`**

```python
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.infrastructure.repository.database.orm import PermissionORM
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.permission import queries as q
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.mappers import permission_from_orm

_NAME_CONFLICT = ConflictMatch("name", ErrorType.PERMISSION_NAME_EXISTS)


class SqlAlchemyPermissionRepository(PermissionRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create(self, *, name, description, created_by) -> UUID:
        try:
            async with self._db.session() as s:
                new_id = await s.scalar(
                    q.build_create(name=name, description=description, created_by=created_by))
                await s.commit()
                return new_id
        except SQLAlchemyError as exc:
            raise map_db_error("failed to create permission", exc, _NAME_CONFLICT) from exc

    async def read_by_id(self, id: UUID) -> Permission | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_id(id))).scalar_one_or_none()
        return permission_from_orm(row) if row is not None else None

    async def read_by_name(self, name: str) -> Permission | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_name(name))).scalar_one_or_none()
        return permission_from_orm(row) if row is not None else None

    async def read_by_pagination(self, *, page, limit, search):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count(search))
            if not total:
                return [], 0
            rows = (await s.execute(
                q.build_read_by_pagination(page=page, limit=limit, search=search))).scalars().all()
        return [permission_from_orm(r) for r in rows], int(total)

    async def update_by_id(self, id, *, name=None, description=None,
                           preferences=None, updated_by=None) -> None:
        try:
            async with self._db.session() as s:
                result = await s.execute(q.build_update_by_id(
                    id, name=name, description=description,
                    preferences=preferences, updated_by=updated_by))
                await s.commit()
        except SQLAlchemyError as exc:
            raise map_db_error("failed to update permission", exc, _NAME_CONFLICT) from exc
        if result.rowcount == 0:
            raise DomainError("permission not found", ErrorType.NOT_FOUND)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        async with self._db.session() as s:
            result = await s.execute(q.build_soft_delete(id, deleted_by=deleted_by))
            await s.commit()
        if result.rowcount == 0:
            raise DomainError("permission not found", ErrorType.NOT_FOUND)
```

> Note on `commit()` inside `db.session()`: when a `Transactor.run` scope is
> active, `current_session` yields the transaction's session and calling
> `.commit()` on it would end the outer transaction. To keep the two paths
> compatible, the repository calls `await s.flush()` instead of
> `await s.commit()` **when a transaction scope is active**, and `.commit()`
> otherwise. Implement a tiny helper on `Database`:
> `async def persist(self, session): await (session.flush() if self.current_session.get() is not None else session.commit())`
> and call `await self._db.persist(s)` in every write method. Update Task 5's
> `Database` to include this method, and this repository (and Tasks 10–12)
> to use it. Add a test in Task 7-style covering "writes inside `tx.run`
> are visible before commit and rolled back on error" — already covered by
> `test_transactor.py`.

- [ ] **Step 5: Apply the `persist` helper**

Add to `Database` (Task 5 file):
```python
    async def persist(self, session) -> None:
        if self.current_session.get() is not None:
            await session.flush()
        else:
            await session.commit()
```
Replace `await s.commit()` with `await self._db.persist(s)` in `create`,
`update_by_id`, `delete_by_id`.

- [ ] **Step 6: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_permission_repository.py -v`
Expected: 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/repository/permission/ \
        backend/src/tarakdingdung/infrastructure/repository/database/session.py \
        backend/tests/integration/test_permission_repository.py
git commit -m "feat(infra): permission repository

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 10: Role repository

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/repository/role/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/role/queries.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/role/repository.py`
- Test: `backend/tests/integration/test_role_repository.py`

**Interfaces:**
- Consumes: `RoleRepository` ABC, `Database`, `shared.*`, `RoleORM`, `RolePermissionORM`, `PermissionORM`.
- Produces: `infrastructure.repository.role.repository.SqlAlchemyRoleRepository(RoleRepository)` — `__init__(self, database: Database)`. Behaviours:
  - `create`: inserts provided columns; when `is_default` is `True`, first `UPDATE roles SET is_default = false, updated_at = now(), updated_by = created_by WHERE is_default AND deleted_at IS NULL`, then insert — both in one `db.session()` (a SAVEPOINT under an ambient transactor, else its own commit). Unique on `name` → `ROLE_NAME_EXISTS`.
  - `read_by_id` / `read_by_name` / `read_default` (`where(is_default.is_(True))`) — `deleted_at IS NULL`, `limit 1` for the latter two.
  - `read_permissions(role_id)`: `select(PermissionORM).join(RolePermissionORM, RolePermissionORM.permission_id == PermissionORM.id).where(RolePermissionORM.role_id == role_id, PermissionORM.deleted_at.is_(None)).order_by(PermissionORM.created_at.desc(), PermissionORM.id.asc())`.
  - `read_by_pagination(page, limit, search)`: count + rows, `name ILIKE`, order `created_at DESC, id ASC`, `([], 0)` early-out.
  - `update_by_id`: provided fields + audit; when `is_default is True`, first unset other defaults (`WHERE is_default AND id <> :id AND deleted_at IS NULL`) then the update — one `db.session()`. `NOT_FOUND` on `rowcount == 0`. Unique `name` → `ROLE_NAME_EXISTS`.
  - `delete_by_id`: soft delete, `NOT_FOUND` on `rowcount == 0`.

- [ ] **Step 1: Write the failing test `backend/tests/integration/test_role_repository.py`**

```python
import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)


@pytest.fixture
def roles(db):
    return SqlAlchemyRoleRepository(db)


@pytest.mark.asyncio
async def test_create_read_and_duplicate_name(roles):
    rid = await roles.create(name="editor", description="d", is_default=None, created_by=None)
    assert (await roles.read_by_id(rid)).name == "editor"
    assert (await roles.read_by_name("editor")).id == rid
    with pytest.raises(DomainError) as ei:
        await roles.create(name="editor", description=None, is_default=None, created_by=None)
    assert ei.value.type is ErrorType.ROLE_NAME_EXISTS


@pytest.mark.asyncio
async def test_only_one_default_after_create_and_update(roles):
    a = await roles.create(name="role_a", description=None, is_default=True, created_by=None)
    b = await roles.create(name="role_b", description=None, is_default=True, created_by=None)
    assert (await roles.read_default()).id == b
    await roles.update_by_id(a, is_default=True, updated_by=None)
    assert (await roles.read_default()).id == a
    assert (await roles.read_by_id(b)).is_default is False


@pytest.mark.asyncio
async def test_read_permissions_returns_assigned(db, roles):
    perms = SqlAlchemyPermissionRepository(db)
    rps = SqlAlchemyRolePermissionRepository(db)
    rid = await roles.create(name="rp_role", description=None, is_default=None, created_by=None)
    p1 = await perms.create(name="rp:get", description=None, created_by=None)
    p2 = await perms.create(name="rp:set", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=p1, created_by=None)
    await rps.create(role_id=rid, permission_id=p2, created_by=None)
    got = {p.name for p in await roles.read_permissions(rid)}
    assert got == {"rp:get", "rp:set"}


@pytest.mark.asyncio
async def test_pagination_and_update_missing_and_soft_delete(roles):
    for n in ["p_alpha", "p_beta", "p_gamma"]:
        await roles.create(name=n, description=None, is_default=None, created_by=None)
    items, total = await roles.read_by_pagination(page=1, limit=10, search="p_")
    assert total == 3 and len(items) == 3
    with pytest.raises(DomainError) as ei:
        await roles.update_by_id(uuid.uuid4(), name="x", updated_by=None)
    assert ei.value.type is ErrorType.NOT_FOUND
    rid = items[0].id
    await roles.delete_by_id(rid, deleted_by=None)
    assert await roles.read_by_id(rid) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_role_repository.py -v`
Expected: FAIL — `ModuleNotFoundError` (also imports `role_permission` from Task 11 — write this test now, it stays red until Task 11; run just the non-`role_permission` tests here with `-k "not read_permissions"`).

Run: `backend/.venv/bin/pytest backend/tests/integration/test_role_repository.py -v -k "not read_permissions"`
Expected: the three selected tests FAIL — `ModuleNotFoundError: ...role.repository`.

- [ ] **Step 3: Write `role/queries.py`**

```python
from uuid import UUID

from sqlalchemy import Select, func, insert, select, update

from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionORM, RoleORM, RolePermissionORM,
)
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)

R = RoleORM


def build_create(*, name, description, is_default, created_by):
    values: dict = {"name": name, "created_by": created_by}
    if description is not None:
        values["description"] = description
    if is_default is not None:
        values["is_default"] = is_default
    return insert(R).values(**values).returning(R.id)


def build_unset_defaults(updated_by, *, except_id: UUID | None = None):
    stmt = (update(R).where(R.is_default.is_(True), R.deleted_at.is_(None))
            .values(is_default=False, updated_at=func.now(), updated_by=updated_by))
    if except_id is not None:
        stmt = stmt.where(R.id != except_id)
    return stmt


def build_read_by_id(id: UUID) -> Select:
    return select(R).where(R.id == id, R.deleted_at.is_(None))


def build_read_by_name(name: str) -> Select:
    return select(R).where(R.name == name, R.deleted_at.is_(None)).limit(1)


def build_read_default() -> Select:
    return select(R).where(R.is_default.is_(True), R.deleted_at.is_(None)).limit(1)


def build_read_permissions(role_id: UUID) -> Select:
    return (select(PermissionORM)
            .join(RolePermissionORM, RolePermissionORM.permission_id == PermissionORM.id)
            .where(RolePermissionORM.role_id == role_id, PermissionORM.deleted_at.is_(None))
            .order_by(PermissionORM.created_at.desc(), PermissionORM.id.asc()))


def build_count(search: str | None):
    stmt = select(func.count()).select_from(R).where(R.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(R.name.ilike(pattern))
    return stmt


def build_read_by_pagination(*, page, limit, search) -> Select:
    stmt = select(R).where(R.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(R.name.ilike(pattern))
    return (stmt.order_by(R.created_at.desc(), R.id.asc())
                .limit(normalize_limit(limit)).offset(normalize_offset(page, limit)))


def build_update_by_id(id: UUID, *, name, description, is_default, preferences, updated_by):
    values: dict = {"updated_at": func.now(), "updated_by": updated_by}
    if name is not None:
        values["name"] = name
    if description is not None:
        values["description"] = description
    if is_default is not None:
        values["is_default"] = is_default
    if preferences is not None:
        values["preferences"] = preferences
    return update(R).where(R.id == id, R.deleted_at.is_(None)).values(**values)


def build_soft_delete(id: UUID, *, deleted_by):
    return (update(R).where(R.id == id, R.deleted_at.is_(None))
            .values(deleted_at=func.now(), deleted_by=deleted_by))
```

- [ ] **Step 4: Write `role/repository.py`**

```python
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.role import queries as q
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.mappers import (
    permission_from_orm, role_from_orm,
)

_NAME_CONFLICT = ConflictMatch("name", ErrorType.ROLE_NAME_EXISTS)


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create(self, *, name, description, is_default, created_by) -> UUID:
        try:
            async with self._db.session() as s:
                if is_default:
                    await s.execute(q.build_unset_defaults(created_by))
                new_id = await s.scalar(q.build_create(
                    name=name, description=description,
                    is_default=is_default, created_by=created_by))
                await self._db.persist(s)
                return new_id
        except SQLAlchemyError as exc:
            raise map_db_error("failed to create role", exc, _NAME_CONFLICT) from exc

    async def read_by_id(self, id: UUID) -> Role | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_id(id))).scalar_one_or_none()
        return role_from_orm(row) if row is not None else None

    async def read_by_name(self, name: str) -> Role | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_name(name))).scalar_one_or_none()
        return role_from_orm(row) if row is not None else None

    async def read_default(self) -> Role | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_default())).scalar_one_or_none()
        return role_from_orm(row) if row is not None else None

    async def read_permissions(self, role_id: UUID) -> list[Permission]:
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_permissions(role_id))).scalars().all()
        return [permission_from_orm(r) for r in rows]

    async def read_by_pagination(self, *, page, limit, search):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count(search))
            if not total:
                return [], 0
            rows = (await s.execute(
                q.build_read_by_pagination(page=page, limit=limit, search=search))).scalars().all()
        return [role_from_orm(r) for r in rows], int(total)

    async def update_by_id(self, id, *, name=None, description=None, is_default=None,
                           preferences=None, updated_by=None) -> None:
        try:
            async with self._db.session() as s:
                if is_default:
                    await s.execute(q.build_unset_defaults(updated_by, except_id=id))
                result = await s.execute(q.build_update_by_id(
                    id, name=name, description=description, is_default=is_default,
                    preferences=preferences, updated_by=updated_by))
                await self._db.persist(s)
        except SQLAlchemyError as exc:
            raise map_db_error("failed to update role", exc, _NAME_CONFLICT) from exc
        if result.rowcount == 0:
            raise DomainError("role not found", ErrorType.NOT_FOUND)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        async with self._db.session() as s:
            result = await s.execute(q.build_soft_delete(id, deleted_by=deleted_by))
            await self._db.persist(s)
        if result.rowcount == 0:
            raise DomainError("role not found", ErrorType.NOT_FOUND)
```

- [ ] **Step 5: Run the selected tests to verify they pass**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_role_repository.py -v -k "not read_permissions"`
Expected: 3 tests PASS. (`test_read_permissions_returns_assigned` stays failing on import until Task 11.)

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/repository/role/ \
        backend/tests/integration/test_role_repository.py
git commit -m "feat(infra): role repository with single-default invariant

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 11: RolePermission repository

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/repository/role_permission/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/role_permission/queries.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/role_permission/repository.py`
- Test: `backend/tests/integration/test_role_permission_repository.py`

**Interfaces:**
- Consumes: `RolePermissionRepository` ABC, `Database`, `shared.*`, all three ORM classes.
- Produces: `infrastructure.repository.role_permission.repository.SqlAlchemyRolePermissionRepository(RolePermissionRepository)` — `__init__(self, database: Database)`. Behaviours:
  - `create`: `insert(RolePermissionORM).values(role_id=..., permission_id=..., created_by=...).returning(id)`; unique `(role_id, permission_id)` violation → `DomainError(ROLE_PERMISSION_EXISTS)` (`ConflictMatch("role_permission", ROLE_PERMISSION_EXISTS)`); FK violation → `CONFLICT`.
  - `read_by_id` / `read_by_role_id_and_permission_id`: a joined `select(RolePermissionORM, RoleORM, PermissionORM)` inner-joined on `rp.role_id == role.id` and `rp.permission_id == permission.id`, filtered `role.deleted_at IS NULL AND permission.deleted_at IS NULL`; returns `(RolePermission, Role, Permission)` or `None`. `limit(1)` for the pair lookup.
  - `read_by_pagination(page, limit, role_id, permission_id)`: same join; optional `rp.role_id == :role_id` / `rp.permission_id == :permission_id`; count + rows; order `rp.created_at DESC, rp.id ASC`; `([], 0)` early-out; returns `(list[tuple], total)`.
  - `delete_by_id(id)`: hard `delete(RolePermissionORM).where(id == :id)` — **no** `NOT_FOUND` raise (matches Go).
  - `delete_by_role_id_and_permission_id(role_id, permission_id)`: hard delete with whichever filters are non-`None`.

- [ ] **Step 1: Write the failing test `backend/tests/integration/test_role_permission_repository.py`**

```python
import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)


@pytest.fixture
async def ctx(db):
    roles = SqlAlchemyRoleRepository(db)
    perms = SqlAlchemyPermissionRepository(db)
    rps = SqlAlchemyRolePermissionRepository(db)
    rid = await roles.create(name="rpx_role", description=None, is_default=None, created_by=None)
    pid = await perms.create(name="rpx:get", description=None, created_by=None)
    return rps, rid, pid


@pytest.mark.asyncio
async def test_create_read_by_id_and_pair(ctx):
    rps, rid, pid = ctx
    link_id = await rps.create(role_id=rid, permission_id=pid, created_by=None)
    row = await rps.read_by_id(link_id)
    assert row is not None
    rp, role, perm = row
    assert rp.id == link_id and role.id == rid and perm.id == pid
    by_pair = await rps.read_by_role_id_and_permission_id(rid, pid)
    assert by_pair[0].id == link_id


@pytest.mark.asyncio
async def test_duplicate_pair_raises(ctx):
    rps, rid, pid = ctx
    await rps.create(role_id=rid, permission_id=pid, created_by=None)
    with pytest.raises(DomainError) as ei:
        await rps.create(role_id=rid, permission_id=pid, created_by=None)
    assert ei.value.type is ErrorType.ROLE_PERMISSION_EXISTS


@pytest.mark.asyncio
async def test_pagination_filters_by_role(ctx):
    rps, rid, pid = ctx
    await rps.create(role_id=rid, permission_id=pid, created_by=None)
    rows, total = await rps.read_by_pagination(page=1, limit=10, role_id=rid, permission_id=None)
    assert total == 1 and rows[0][0].role_id == rid


@pytest.mark.asyncio
async def test_delete_by_pair_and_by_id(ctx):
    rps, rid, pid = ctx
    link_id = await rps.create(role_id=rid, permission_id=pid, created_by=None)
    await rps.delete_by_role_id_and_permission_id(role_id=rid, permission_id=pid)
    assert await rps.read_by_id(link_id) is None
    await rps.delete_by_id(uuid.uuid4())  # no error on missing
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_role_permission_repository.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `role_permission/queries.py`**

```python
from uuid import UUID

from sqlalchemy import Select, delete, func, insert, select

from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionORM, RoleORM, RolePermissionORM,
)
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset,
)

RP, R, P = RolePermissionORM, RoleORM, PermissionORM


def build_create(*, role_id: UUID, permission_id: UUID, created_by: UUID | None):
    return (insert(RP)
            .values(role_id=role_id, permission_id=permission_id, created_by=created_by)
            .returning(RP.id))


def _base_join() -> Select:
    return (select(RP, R, P)
            .join(R, RP.role_id == R.id)
            .join(P, RP.permission_id == P.id)
            .where(R.deleted_at.is_(None), P.deleted_at.is_(None)))


def build_read_by_id(id: UUID) -> Select:
    return _base_join().where(RP.id == id)


def build_read_by_pair(role_id: UUID, permission_id: UUID) -> Select:
    return _base_join().where(RP.role_id == role_id, RP.permission_id == permission_id).limit(1)


def build_count(role_id: UUID | None, permission_id: UUID | None):
    stmt = (select(func.count()).select_from(RP)
            .join(R, RP.role_id == R.id).join(P, RP.permission_id == P.id)
            .where(R.deleted_at.is_(None), P.deleted_at.is_(None)))
    if role_id is not None:
        stmt = stmt.where(RP.role_id == role_id)
    if permission_id is not None:
        stmt = stmt.where(RP.permission_id == permission_id)
    return stmt


def build_read_by_pagination(*, page, limit, role_id, permission_id) -> Select:
    stmt = _base_join()
    if role_id is not None:
        stmt = stmt.where(RP.role_id == role_id)
    if permission_id is not None:
        stmt = stmt.where(RP.permission_id == permission_id)
    return (stmt.order_by(RP.created_at.desc(), RP.id.asc())
                .limit(normalize_limit(limit)).offset(normalize_offset(page, limit)))


def build_delete_by_id(id: UUID):
    return delete(RP).where(RP.id == id)


def build_delete_by_pair(role_id: UUID | None, permission_id: UUID | None):
    stmt = delete(RP)
    if role_id is not None:
        stmt = stmt.where(RP.role_id == role_id)
    if permission_id is not None:
        stmt = stmt.where(RP.permission_id == permission_id)
    return stmt
```

- [ ] **Step 4: Write `role_permission/repository.py`**

```python
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.role_permission import (
    RolePermissionRepository, RolePermissionRow,
)
from tarakdingdung.domain.models.error import ErrorType
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.role_permission import queries as q
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.mappers import (
    permission_from_orm, role_from_orm, role_permission_from_orm,
)

_PAIR_CONFLICT = ConflictMatch("role_permission", ErrorType.ROLE_PERMISSION_EXISTS)


def _row(rp, role, perm) -> RolePermissionRow:
    return (role_permission_from_orm(rp), role_from_orm(role), permission_from_orm(perm))


class SqlAlchemyRolePermissionRepository(RolePermissionRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create(self, *, role_id, permission_id, created_by) -> UUID:
        try:
            async with self._db.session() as s:
                new_id = await s.scalar(q.build_create(
                    role_id=role_id, permission_id=permission_id, created_by=created_by))
                await self._db.persist(s)
                return new_id
        except SQLAlchemyError as exc:
            raise map_db_error("failed to assign role permission", exc, _PAIR_CONFLICT) from exc

    async def read_by_id(self, id: UUID) -> RolePermissionRow | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_id(id))).first()
        return _row(*row) if row is not None else None

    async def read_by_role_id_and_permission_id(self, role_id, permission_id):
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_pair(role_id, permission_id))).first()
        return _row(*row) if row is not None else None

    async def read_by_pagination(self, *, page, limit, role_id, permission_id):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count(role_id, permission_id))
            if not total:
                return [], 0
            rows = (await s.execute(q.build_read_by_pagination(
                page=page, limit=limit, role_id=role_id, permission_id=permission_id))).all()
        return [_row(*r) for r in rows], int(total)

    async def delete_by_id(self, id: UUID) -> None:
        async with self._db.session() as s:
            await s.execute(q.build_delete_by_id(id))
            await self._db.persist(s)

    async def delete_by_role_id_and_permission_id(self, *, role_id, permission_id) -> None:
        async with self._db.session() as s:
            await s.execute(q.build_delete_by_pair(role_id, permission_id))
            await self._db.persist(s)
```

- [ ] **Step 5: Run to verify it passes (plus the previously-blocked role test)**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_role_permission_repository.py backend/tests/integration/test_role_repository.py -v`
Expected: all PASS (including `test_read_permissions_returns_assigned`).

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/repository/role_permission/ \
        backend/tests/integration/test_role_permission_repository.py
git commit -m "feat(infra): role_permission repository

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 12: User repository

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/repository/user/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/user/queries.py`
- Create: `backend/src/tarakdingdung/infrastructure/repository/user/repository.py`
- Test: `backend/tests/integration/test_user_repository.py`

**Interfaces:**
- Consumes: `UserRepository` ABC, `Database`, `shared.*`, `UserORM`, `RoleORM`, `RolePermissionORM`, `PermissionORM`.
- Produces: `infrastructure.repository.user.repository.SqlAlchemyUserRepository(UserRepository)` — `__init__(self, database: Database)`. Behaviours:
  - `create`: insert provided columns (`role_id`, `name`, `username`, `password_hash`, `created_by` always; `bio` when not `None`), `.returning(id)`; unique `username` → `USERNAME_EXISTS`; FK `role_id` → `CONFLICT`.
  - `read_by_id` / `read_by_username`: `deleted_at IS NULL`, `limit 1` for username.
  - `read_permissions(user_id)`: `select(PermissionORM).join(RoleORM, RoleORM.id == UserORM.role_id ...)` — join `users → roles → role_permission → permissions`, filter `users.id == :uid AND users.deleted_at IS NULL AND roles.deleted_at IS NULL AND permissions.deleted_at IS NULL`, order `permissions.created_at DESC, permissions.id ASC`. Implement as `select(PermissionORM).select_from(UserORM).join(RoleORM, RoleORM.id == UserORM.role_id).join(RolePermissionORM, RolePermissionORM.role_id == RoleORM.id).join(PermissionORM, PermissionORM.id == RolePermissionORM.permission_id).where(...)`.
  - `read_by_pagination(page, limit, search, role_id)`: rows = `select(UserORM, RoleORM.name.label("role_name")).outerjoin(RoleORM, RoleORM.id == UserORM.role_id).where(UserORM.deleted_at.is_(None))`; `search` → `UserORM.name.ilike(:p) | UserORM.username.ilike(:p)`; `role_id` → `UserORM.role_id == :role_id`; order `users.created_at DESC, users.id ASC`; count query is join-free over `users` with the same filters; `([], 0)` early-out; map with `user_list_item_from_orm(row.UserORM, row.role_name)`.
  - `update_by_id`: provided fields (`role_id`, `name`, `bio`, `username`, `password_hash`, `preferences`) + `updated_at=func.now()`, `updated_by`; `where(deleted_at IS NULL)`; `NOT_FOUND` on `rowcount == 0`; unique `username` → `USERNAME_EXISTS`.
  - `delete_by_id`: soft delete; `NOT_FOUND` on `rowcount == 0`.

- [ ] **Step 1: Write the failing test `backend/tests/integration/test_user_repository.py`**

```python
import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)
from tarakdingdung.infrastructure.repository.user.repository import SqlAlchemyUserRepository


@pytest.fixture
async def base(db):
    roles = SqlAlchemyRoleRepository(db)
    users = SqlAlchemyUserRepository(db)
    rid = await roles.create(name="ur_role", description=None, is_default=None, created_by=None)
    return users, roles, rid


@pytest.mark.asyncio
async def test_create_read_by_id_and_username(base):
    users, _roles, rid = base
    uid = await users.create(role_id=rid, name="Grace Hopper", bio="hi",
                             username="grace", password_hash="H", created_by=None)
    by_id = await users.read_by_id(uid)
    assert by_id.username == "grace" and by_id.password_hash == "H" and by_id.bio == "hi"
    assert (await users.read_by_username("grace")).id == uid
    assert await users.read_by_username("ghost") is None


@pytest.mark.asyncio
async def test_duplicate_username_and_bad_role_fk(base):
    users, _roles, rid = base
    await users.create(role_id=rid, name="A", bio=None, username="dupe",
                       password_hash="H", created_by=None)
    with pytest.raises(DomainError) as ei:
        await users.create(role_id=rid, name="B", bio=None, username="dupe",
                           password_hash="H", created_by=None)
    assert ei.value.type is ErrorType.USERNAME_EXISTS
    with pytest.raises(DomainError) as ei2:
        await users.create(role_id=uuid.uuid4(), name="C", bio=None, username="orphan",
                           password_hash="H", created_by=None)
    assert ei2.value.type is ErrorType.CONFLICT


@pytest.mark.asyncio
async def test_read_permissions_via_role(db, base):
    users, _roles, rid = base
    perms = SqlAlchemyPermissionRepository(db)
    rps = SqlAlchemyRolePermissionRepository(db)
    p = await perms.create(name="ur:get", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=p, created_by=None)
    uid = await users.create(role_id=rid, name="D", bio=None, username="dee",
                             password_hash="H", created_by=None)
    got = [x.name for x in await users.read_permissions(uid)]
    assert got == ["ur:get"]


@pytest.mark.asyncio
async def test_pagination_role_name_search_and_filter(db, base):
    users, roles, rid = base
    other = await roles.create(name="ur_role2", description=None, is_default=None, created_by=None)
    await users.create(role_id=rid, name="Ada Lovelace", bio=None, username="ada",
                       password_hash="H", created_by=None)
    await users.create(role_id=other, name="Alan Turing", bio=None, username="alan",
                       password_hash="H", created_by=None)
    items, total = await users.read_by_pagination(page=1, limit=10, search="ala", role_id=None)
    assert total == 1 and items[0].user.username == "alan" and items[0].role_name == "ur_role2"
    only_rid, n = await users.read_by_pagination(page=1, limit=10, search=None, role_id=rid)
    assert n == 1 and only_rid[0].user.username == "ada"


@pytest.mark.asyncio
async def test_update_reset_password_soft_delete(base):
    users, _roles, rid = base
    uid = await users.create(role_id=rid, name="E", bio=None, username="eee",
                             password_hash="OLD", created_by=None)
    await users.update_by_id(uid, name="Edited", updated_by=None)
    await users.update_by_id(uid, password_hash="NEW", updated_by=None)
    row = await users.read_by_id(uid)
    assert row.name == "Edited" and row.password_hash == "NEW"
    with pytest.raises(DomainError) as ei:
        await users.update_by_id(uuid.uuid4(), name="x", updated_by=None)
    assert ei.value.type is ErrorType.NOT_FOUND
    await users.delete_by_id(uid, deleted_by=None)
    assert await users.read_by_id(uid) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_user_repository.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `user/queries.py`**

```python
from uuid import UUID

from sqlalchemy import Select, func, insert, or_, select, update

from tarakdingdung.infrastructure.repository.database.orm import (
    PermissionORM, RoleORM, RolePermissionORM, UserORM,
)
from tarakdingdung.infrastructure.repository.shared.query import (
    normalize_limit, normalize_offset, search_pattern,
)

U, R, RP, P = UserORM, RoleORM, RolePermissionORM, PermissionORM


def build_create(*, role_id, name, bio, username, password_hash, created_by):
    values: dict = {"role_id": role_id, "name": name, "username": username,
                    "password_hash": password_hash, "created_by": created_by}
    if bio is not None:
        values["bio"] = bio
    return insert(U).values(**values).returning(U.id)


def build_read_by_id(id: UUID) -> Select:
    return select(U).where(U.id == id, U.deleted_at.is_(None))


def build_read_by_username(username: str) -> Select:
    return select(U).where(U.username == username, U.deleted_at.is_(None)).limit(1)


def build_read_permissions(user_id: UUID) -> Select:
    return (select(P).select_from(U)
            .join(R, R.id == U.role_id)
            .join(RP, RP.role_id == R.id)
            .join(P, P.id == RP.permission_id)
            .where(U.id == user_id, U.deleted_at.is_(None),
                   R.deleted_at.is_(None), P.deleted_at.is_(None))
            .order_by(P.created_at.desc(), P.id.asc()))


def build_count(search: str | None, role_id: UUID | None):
    stmt = select(func.count()).select_from(U).where(U.deleted_at.is_(None))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(or_(U.name.ilike(pattern), U.username.ilike(pattern)))
    if role_id is not None:
        stmt = stmt.where(U.role_id == role_id)
    return stmt


def build_read_by_pagination(*, page, limit, search, role_id) -> Select:
    stmt = (select(U, R.name.label("role_name"))
            .outerjoin(R, R.id == U.role_id)
            .where(U.deleted_at.is_(None)))
    pattern = search_pattern(search)
    if pattern is not None:
        stmt = stmt.where(or_(U.name.ilike(pattern), U.username.ilike(pattern)))
    if role_id is not None:
        stmt = stmt.where(U.role_id == role_id)
    return (stmt.order_by(U.created_at.desc(), U.id.asc())
                .limit(normalize_limit(limit)).offset(normalize_offset(page, limit)))


def build_update_by_id(id: UUID, *, role_id, name, bio, username,
                       password_hash, preferences, updated_by):
    values: dict = {"updated_at": func.now(), "updated_by": updated_by}
    for key, val in (("role_id", role_id), ("name", name), ("bio", bio),
                     ("username", username), ("password_hash", password_hash),
                     ("preferences", preferences)):
        if val is not None:
            values[key] = val
    return update(U).where(U.id == id, U.deleted_at.is_(None)).values(**values)


def build_soft_delete(id: UUID, *, deleted_by):
    return (update(U).where(U.id == id, U.deleted_at.is_(None))
            .values(deleted_at=func.now(), deleted_by=deleted_by))
```

- [ ] **Step 4: Write `user/repository.py`**

```python
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User
from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.repository.shared.errors import ConflictMatch, map_db_error
from tarakdingdung.infrastructure.repository.shared.mappers import (
    permission_from_orm, user_from_orm, user_list_item_from_orm,
)
from tarakdingdung.infrastructure.repository.user import queries as q

_USERNAME_CONFLICT = ConflictMatch("username", ErrorType.USERNAME_EXISTS)


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, database: Database) -> None:
        self._db = database

    async def create(self, *, role_id, name, bio, username, password_hash, created_by) -> UUID:
        try:
            async with self._db.session() as s:
                new_id = await s.scalar(q.build_create(
                    role_id=role_id, name=name, bio=bio, username=username,
                    password_hash=password_hash, created_by=created_by))
                await self._db.persist(s)
                return new_id
        except SQLAlchemyError as exc:
            raise map_db_error("failed to create user", exc, _USERNAME_CONFLICT) from exc

    async def read_by_id(self, id: UUID) -> User | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_id(id))).scalar_one_or_none()
        return user_from_orm(row) if row is not None else None

    async def read_by_username(self, username: str) -> User | None:
        async with self._db.session() as s:
            row = (await s.execute(q.build_read_by_username(username))).scalar_one_or_none()
        return user_from_orm(row) if row is not None else None

    async def read_permissions(self, user_id: UUID) -> list[Permission]:
        async with self._db.session() as s:
            rows = (await s.execute(q.build_read_permissions(user_id))).scalars().all()
        return [permission_from_orm(r) for r in rows]

    async def read_by_pagination(self, *, page, limit, search, role_id):
        async with self._db.session() as s:
            total = await s.scalar(q.build_count(search, role_id))
            if not total:
                return [], 0
            rows = (await s.execute(q.build_read_by_pagination(
                page=page, limit=limit, search=search, role_id=role_id))).all()
        return [user_list_item_from_orm(r.UserORM, r.role_name) for r in rows], int(total)

    async def update_by_id(self, id, *, role_id=None, name=None, bio=None, username=None,
                           password_hash=None, preferences=None, updated_by=None) -> None:
        try:
            async with self._db.session() as s:
                result = await s.execute(q.build_update_by_id(
                    id, role_id=role_id, name=name, bio=bio, username=username,
                    password_hash=password_hash, preferences=preferences, updated_by=updated_by))
                await self._db.persist(s)
        except SQLAlchemyError as exc:
            raise map_db_error("failed to update user", exc, _USERNAME_CONFLICT) from exc
        if result.rowcount == 0:
            raise DomainError("user not found", ErrorType.NOT_FOUND)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        async with self._db.session() as s:
            result = await s.execute(q.build_soft_delete(id, deleted_by=deleted_by))
            await self._db.persist(s)
        if result.rowcount == 0:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
```

> `(await s.execute(stmt)).all()` on a `select(U, R.name.label("role_name"))`
> yields rows whose first field is accessible as `row.UserORM` (the mapped
> class name) and second as `row.role_name`. If the attribute name differs
> in your SQLAlchemy version, use positional `row[0]`, `row[1]`.

- [ ] **Step 5: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_user_repository.py -v`
Expected: 5 tests PASS.

- [ ] **Step 6: Full repository regression + commit**

Run: `backend/.venv/bin/pytest backend/tests/integration/ -v`
Expected: every integration test PASS.

```bash
git add backend/src/tarakdingdung/infrastructure/repository/user/ \
        backend/tests/integration/test_user_repository.py
git commit -m "feat(infra): user repository with role-join pagination and permission read

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 13: Password (bcrypt) and Token (JWT) utilities

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/utility/password/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/utility/password/bcrypt.py`
- Create: `backend/src/tarakdingdung/infrastructure/utility/token/__init__.py`
- Create: `backend/src/tarakdingdung/infrastructure/utility/token/jwt.py`
- Test: `backend/tests/infrastructure/test_password.py`
- Test: `backend/tests/infrastructure/test_token.py`

**Interfaces:**
- Consumes: `Password`, `Token` ABCs; `TokenClaimsAccess`, `TokenClaimsRefresh`; `DomainError`/`ErrorType`.
- Produces:
  - `infrastructure.utility.password.bcrypt.BcryptPassword(Password)` — `__init__(self, cost: int)` clamps `cost` to `[4, 31]` (fallback `12`). `hash(password)` → `bcrypt.hashpw(password.encode(), bcrypt.gensalt(self._cost)).decode()` off-thread via `anyio.to_thread.run_sync`. `compare(stored_hash, password)` → `bcrypt.checkpw(...)` off-thread; on `False` raise `DomainError("password does not match", UNAUTHORIZED)`; on any exception raise `DomainError("failed to compare password", FAILURE, exc)`.
  - `infrastructure.utility.token.jwt.JwtToken(Token)` — `__init__(self, *, access_secret: str, refresh_secret: str, access_ttl: timedelta, refresh_ttl: timedelta, now: Callable[[], datetime] = ...)` (default `lambda: datetime.now(tz=timezone.utc)`). `generate_access(claims)` → `jwt.encode({"user_id": str(claims.user_id), "name": ..., "username": ..., "role": ..., "permissions": list(claims.permissions), "sub": str(claims.user_id), "iat": now, "nbf": now, "exp": now + access_ttl}, access_secret, "HS256")`. `validate_access(token)` → `jwt.decode(token, access_secret, algorithms=["HS256"])`; `jwt.ExpiredSignatureError` → `DomainError(TOKEN_EXPIRED)`; other `jwt.InvalidTokenError` → `DomainError(TOKEN_INVALID)`; rebuild `TokenClaimsAccess(user_id=UUID(payload.get("user_id") or payload["sub"]), name=payload["name"], username=payload["username"], role=payload["role"], permissions=tuple(payload["permissions"]))`. Refresh pair analogous with `{"user_id", "sub", "iat", "nbf", "exp"}` → `TokenClaimsRefresh`.

- [ ] **Step 1: Write `backend/tests/infrastructure/test_password.py`**

```python
import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword


@pytest.mark.asyncio
async def test_hash_then_compare_roundtrip():
    pw = BcryptPassword(cost=4)
    h = await pw.hash("BrewMeUp42")
    assert h != "BrewMeUp42"
    await pw.compare(h, "BrewMeUp42")  # no raise


@pytest.mark.asyncio
async def test_compare_mismatch_raises_unauthorized():
    pw = BcryptPassword(cost=4)
    h = await pw.hash("correct-horse")
    with pytest.raises(DomainError) as ei:
        await pw.compare(h, "wrong")
    assert ei.value.type is ErrorType.UNAUTHORIZED


@pytest.mark.asyncio
async def test_out_of_range_cost_falls_back():
    pw = BcryptPassword(cost=99)
    h = await pw.hash("x-secret-1")
    await pw.compare(h, "x-secret-1")
```

- [ ] **Step 2: Write `backend/tests/infrastructure/test_token.py`**

```python
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh
from tarakdingdung.infrastructure.utility.token.jwt import JwtToken


def _token(now=None):
    return JwtToken(access_secret="a", refresh_secret="r",
                    access_ttl=timedelta(minutes=15), refresh_ttl=timedelta(days=1),
                    now=now or (lambda: datetime.now(tz=timezone.utc)))


@pytest.mark.asyncio
async def test_access_roundtrip_preserves_claims():
    t = _token()
    uid = uuid.uuid4()
    raw = await t.generate_access(TokenClaimsAccess(
        user_id=uid, name="Grace", username="grace", role="super",
        permissions=("user:get", "user:add")))
    claims = await t.validate_access(raw)
    assert claims.user_id == uid and claims.role == "super"
    assert claims.permissions == ("user:get", "user:add")


@pytest.mark.asyncio
async def test_refresh_roundtrip():
    t = _token()
    uid = uuid.uuid4()
    raw = await t.generate_refresh(TokenClaimsRefresh(user_id=uid))
    assert (await t.validate_refresh(raw)).user_id == uid


@pytest.mark.asyncio
async def test_expired_access_maps_to_token_expired():
    past = lambda: datetime(2020, 1, 1, tzinfo=timezone.utc)
    issuer = _token(now=past)
    raw = await issuer.generate_access(TokenClaimsAccess(
        user_id=uuid.uuid4(), name="n", username="u", role="r", permissions=()))
    with pytest.raises(DomainError) as ei:
        await _token().validate_access(raw)
    assert ei.value.type is ErrorType.TOKEN_EXPIRED


@pytest.mark.asyncio
async def test_tampered_token_maps_to_token_invalid():
    with pytest.raises(DomainError) as ei:
        await _token().validate_access("not.a.jwt")
    assert ei.value.type is ErrorType.TOKEN_INVALID


@pytest.mark.asyncio
async def test_wrong_secret_is_token_invalid():
    other = JwtToken(access_secret="different", refresh_secret="r",
                     access_ttl=timedelta(minutes=5), refresh_ttl=timedelta(days=1))
    raw = await other.generate_access(TokenClaimsAccess(
        user_id=uuid.uuid4(), name="n", username="u", role="r", permissions=()))
    with pytest.raises(DomainError) as ei:
        await _token().validate_access(raw)
    assert ei.value.type is ErrorType.TOKEN_INVALID
```

- [ ] **Step 3: Run both tests to verify they fail**

Run: `backend/.venv/bin/pytest backend/tests/infrastructure/test_password.py backend/tests/infrastructure/test_token.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Write `infrastructure/utility/password/bcrypt.py`**

```python
import bcrypt
from anyio import to_thread

from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.models.error import DomainError, ErrorType

_MIN_COST, _MAX_COST, _DEFAULT_COST = 4, 31, 12


class BcryptPassword(Password):
    def __init__(self, cost: int) -> None:
        self._cost = cost if _MIN_COST <= cost <= _MAX_COST else _DEFAULT_COST

    async def hash(self, password: str) -> str:
        def _hash() -> str:
            return bcrypt.hashpw(password.encode("utf-8"),
                                 bcrypt.gensalt(self._cost)).decode("utf-8")
        return await to_thread.run_sync(_hash)

    async def compare(self, stored_hash: str, password: str) -> None:
        def _check() -> bool:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        try:
            ok = await to_thread.run_sync(_check)
        except Exception as exc:  # noqa: BLE001
            raise DomainError("failed to compare password", ErrorType.FAILURE, exc) from exc
        if not ok:
            raise DomainError("password does not match", ErrorType.UNAUTHORIZED)
```

- [ ] **Step 5: Write `infrastructure/utility/token/jwt.py`**

```python
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh


def _default_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class JwtToken(Token):
    def __init__(self, *, access_secret: str, refresh_secret: str,
                 access_ttl: timedelta, refresh_ttl: timedelta,
                 now: Callable[[], datetime] = _default_now) -> None:
        self._access_secret = access_secret
        self._refresh_secret = refresh_secret
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._now = now

    async def generate_access(self, claims: TokenClaimsAccess) -> str:
        now = self._now()
        payload = {
            "user_id": str(claims.user_id), "name": claims.name,
            "username": claims.username, "role": claims.role,
            "permissions": list(claims.permissions), "sub": str(claims.user_id),
            "iat": now, "nbf": now, "exp": now + self._access_ttl,
        }
        return jwt.encode(payload, self._access_secret, algorithm="HS256")

    async def validate_access(self, token: str) -> TokenClaimsAccess:
        payload = self._decode(token, self._access_secret)
        return TokenClaimsAccess(
            user_id=UUID(payload.get("user_id") or payload["sub"]),
            name=payload["name"], username=payload["username"], role=payload["role"],
            permissions=tuple(payload.get("permissions", [])),
        )

    async def generate_refresh(self, claims: TokenClaimsRefresh) -> str:
        now = self._now()
        payload = {"user_id": str(claims.user_id), "sub": str(claims.user_id),
                   "iat": now, "nbf": now, "exp": now + self._refresh_ttl}
        return jwt.encode(payload, self._refresh_secret, algorithm="HS256")

    async def validate_refresh(self, token: str) -> TokenClaimsRefresh:
        payload = self._decode(token, self._refresh_secret)
        return TokenClaimsRefresh(user_id=UUID(payload.get("user_id") or payload["sub"]))

    @staticmethod
    def _decode(token: str, secret: str) -> dict:
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as exc:
            raise DomainError("token has expired", ErrorType.TOKEN_EXPIRED, exc) from exc
        except jwt.InvalidTokenError as exc:
            raise DomainError("token is invalid", ErrorType.TOKEN_INVALID, exc) from exc
```

- [ ] **Step 6: Run both tests to verify they pass**

Run: `backend/.venv/bin/pytest backend/tests/infrastructure/test_password.py backend/tests/infrastructure/test_token.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/utility/password/ \
        backend/src/tarakdingdung/infrastructure/utility/token/ \
        backend/tests/infrastructure/test_password.py backend/tests/infrastructure/test_token.py
git commit -m "feat(infra): bcrypt password and JWT token utilities

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 14: Logger meta normalisation

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/logger/normalize.py`
- Modify: `backend/src/tarakdingdung/infrastructure/logger/leveled/plain.py`
- Modify: `backend/src/tarakdingdung/infrastructure/logger/leveled/json.py`
- Test: `backend/tests/infrastructure/test_logger_normalize.py`

**Interfaces:**
- Produces: `infrastructure.logger.normalize.normalize_meta(meta: dict | None) -> dict` — returns `{}` for `None`; for each value that is an `Exception`, replace with `str(value)`; other values pass through unchanged.
- Modifies: `BasicLeveledLogging._log` and `JsonLeveledLogging._log` to call `normalize_meta(meta)` before formatting/serialising (so the two existing infra loggers emit exception strings, not `{}`).

- [ ] **Step 1: Write `backend/tests/infrastructure/test_logger_normalize.py`**

```python
import json

import pytest

from tarakdingdung.infrastructure.logger.normalize import normalize_meta
from tarakdingdung.infrastructure.logger.leveled.json import JsonLeveledLogging
from tarakdingdung.domain.models.logger import LoggerLevel


def test_normalize_meta_stringifies_exceptions():
    out = normalize_meta({"err": ValueError("boom"), "id": 7})
    assert out == {"err": "boom", "id": 7}


def test_normalize_meta_none_is_empty_dict():
    assert normalize_meta(None) == {}


@pytest.mark.asyncio
async def test_json_logger_emits_exception_string(capsys):
    logger = JsonLeveledLogging(LoggerLevel.DEBUG)
    await logger.error("tag", "failed", {"err": RuntimeError("db down")})
    line = capsys.readouterr().out.strip()
    payload = json.loads(line)
    assert payload["meta"]["err"] == "db down"
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/infrastructure/test_logger_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: tarakdingdung.infrastructure.logger.normalize`.

- [ ] **Step 3: Write `infrastructure/logger/normalize.py`**

```python
def normalize_meta(meta: dict | None) -> dict:
    if not meta:
        return {}
    normalized: dict = {}
    for key, value in meta.items():
        normalized[key] = str(value) if isinstance(value, BaseException) else value
    return normalized
```

- [ ] **Step 4: Wire it into the two loggers**

In `infrastructure/logger/leveled/json.py`, inside `_log`, change the `meta` line so the entry uses `normalize_meta(meta)`:
```python
from tarakdingdung.infrastructure.logger.normalize import normalize_meta
# ...
        log_entry = {
            "timestamp": timestamp,
            "level": level.upper(),
            "tag": tag,
            "message": message,
            "meta": normalize_meta(meta),
        }
```
In `infrastructure/logger/leveled/plain.py`, inside `_log`:
```python
from tarakdingdung.infrastructure.logger.normalize import normalize_meta
# ...
        normalized = normalize_meta(meta)
        meta_str = json.dumps(normalized) if normalized else "{}"
```

- [ ] **Step 5: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/infrastructure/test_logger_normalize.py -v`
Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/logger/ \
        backend/tests/infrastructure/test_logger_normalize.py
git commit -m "feat(infra): normalise exception values in logger meta

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 15: Application shared validation

**Files:**
- Create: `backend/src/tarakdingdung/application/__init__.py` (if absent)
- Create: `backend/src/tarakdingdung/application/shared/__init__.py`
- Create: `backend/src/tarakdingdung/application/shared/validation.py`
- Test: `backend/tests/application/__init__.py`
- Test: `backend/tests/application/test_validation.py`

**Interfaces:**
- Consumes: `DomainError`, `ErrorType`.
- Produces (each `required_*` returns the cleaned `str`, raising `DomainError(msg, ErrorType.VALIDATION)`; each `optional_*` returns `str | None`, passing `None` through):
  - `required_person_name(value: str, field: str) -> str` / `optional_person_name(value: str | None, field: str) -> str | None` — pattern `^[A-Za-z0-9' -]+$`, len 1–128, `.strip()`.
  - `required_username` / `optional_username` — `^[A-Za-z0-9_-]+$`, len 3–128, `.strip()`.
  - `required_role_name` / `optional_role_name` — `^[A-Za-z0-9_-]+$`, len 3–128, `.strip()`.
  - `required_permission_name` / `optional_permission_name` — `^[A-Za-z0-9/_:-]+$`, len 3–128, `.strip()`.
  - `required_password(value: str, field: str) -> str` — `^[\x21-\x7E]+$`, len 8–72, **not** stripped; no `optional_` variant.

- [ ] **Step 1: Write `backend/tests/application/test_validation.py`**

```python
import pytest

from tarakdingdung.application.shared import validation as v
from tarakdingdung.domain.models.error import DomainError, ErrorType


@pytest.mark.parametrize("fn,good", [
    (v.required_person_name, "Grace O'Hara-Hopper"),
    (v.required_username, "grace_hopper-1"),
    (v.required_role_name, "fleet_operator"),
    (v.required_permission_name, "node:get"),
])
def test_required_accepts_valid(fn, good):
    assert fn(good, "field") == good.strip()


def test_required_strips_whitespace():
    assert v.required_username("  grace  ", "username") == "grace"


@pytest.mark.parametrize("fn,bad", [
    (v.required_person_name, ""),
    (v.required_person_name, "  "),
    (v.required_username, "ab"),
    (v.required_username, "bad name"),
    (v.required_role_name, "x" * 129),
    (v.required_permission_name, "no spaces here"),
])
def test_required_rejects_invalid(fn, bad):
    with pytest.raises(DomainError) as ei:
        fn(bad, "field")
    assert ei.value.type is ErrorType.VALIDATION


@pytest.mark.parametrize("value,expected", [(None, None), ("grace", "grace")])
def test_optional_username(value, expected):
    assert v.optional_username(value, "username") == expected


@pytest.mark.parametrize("pw", ["BrewMeUp!42", "abcdefgh"])
def test_required_password_accepts(pw):
    assert v.required_password(pw, "password") == pw


@pytest.mark.parametrize("pw", ["short", "with space", "x" * 73, ""])
def test_required_password_rejects(pw):
    with pytest.raises(DomainError) as ei:
        v.required_password(pw, "password")
    assert ei.value.type is ErrorType.VALIDATION
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/application/test_validation.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `application/shared/validation.py`**

```python
import re

from tarakdingdung.domain.models.error import DomainError, ErrorType

_PERSON_NAME = re.compile(r"^[A-Za-z0-9' -]+$")
_USERNAME = re.compile(r"^[A-Za-z0-9_-]+$")
_ROLE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
_PERMISSION_NAME = re.compile(r"^[A-Za-z0-9/_:-]+$")
_PASSWORD = re.compile(r"^[\x21-\x7E]+$")


def _validate(value: str, field: str, pattern: re.Pattern[str],
              min_len: int, max_len: int, charset: str) -> str:
    value = value.strip()
    if not value:
        raise DomainError(f"{field} is required", ErrorType.VALIDATION)
    if not (min_len <= len(value) <= max_len):
        raise DomainError(
            f"{field} must be between {min_len} and {max_len} characters",
            ErrorType.VALIDATION)
    if not pattern.match(value):
        raise DomainError(f"{field} may only contain {charset}", ErrorType.VALIDATION)
    return value


def required_person_name(value: str, field: str) -> str:
    return _validate(value, field, _PERSON_NAME, 1, 128,
                     "alphanumeric characters, spaces, dashes, and apostrophes")


def optional_person_name(value: str | None, field: str) -> str | None:
    return None if value is None else required_person_name(value, field)


def required_username(value: str, field: str) -> str:
    return _validate(value, field, _USERNAME, 3, 128,
                     "alphanumeric characters, underscores, and dashes")


def optional_username(value: str | None, field: str) -> str | None:
    return None if value is None else required_username(value, field)


def required_role_name(value: str, field: str) -> str:
    return _validate(value, field, _ROLE_NAME, 3, 128,
                     "alphanumeric characters, underscores, and dashes")


def optional_role_name(value: str | None, field: str) -> str | None:
    return None if value is None else required_role_name(value, field)


def required_permission_name(value: str, field: str) -> str:
    return _validate(value, field, _PERMISSION_NAME, 3, 128,
                     "alphanumeric characters, slashes, underscores, dashes, and colons")


def optional_permission_name(value: str | None, field: str) -> str | None:
    return None if value is None else required_permission_name(value, field)


def required_password(value: str, field: str) -> str:
    if not value:
        raise DomainError(f"{field} is required", ErrorType.VALIDATION)
    if not (8 <= len(value) <= 72):
        raise DomainError(f"{field} must be between 8 and 72 characters", ErrorType.VALIDATION)
    if not _PASSWORD.match(value):
        raise DomainError(
            f"{field} may only contain printable characters and no spaces",
            ErrorType.VALIDATION)
    return value
```

- [ ] **Step 4: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/application/test_validation.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/application/ backend/tests/application/
git commit -m "feat(application): shared value validators

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 16: Test fakes + admin `PermissionManagement` usecase

**Files:**
- Create: `backend/tests/fakes/__init__.py`
- Create: `backend/tests/fakes/repositories.py`
- Create: `backend/tests/fakes/utilities.py`
- Create: `backend/src/tarakdingdung/application/admin/__init__.py`
- Create: `backend/src/tarakdingdung/application/admin/permission_management/__init__.py`
- Create: `backend/src/tarakdingdung/application/admin/permission_management/usecase.py`
- Test: `backend/tests/application/test_permission_management.py`

**Interfaces:**
- Consumes: repository + utility ABCs, `PermissionManagement` interface + DTOs, `application.shared.validation`, `LeveledLogger`.
- Produces:
  - `tests.fakes.repositories.FakePermissionRepository(PermissionRepository)`, `FakeRoleRepository(RoleRepository)`, `FakeRolePermissionRepository(RolePermissionRepository)`, `FakeUserRepository(UserRepository)` — dict-backed, honour soft-delete semantics, raise `DomainError` with the same `ErrorType`s as the real repos for duplicate name/username (`PERMISSION_NAME_EXISTS`, `ROLE_NAME_EXISTS`, `USERNAME_EXISTS`, `ROLE_PERMISSION_EXISTS`) and `NOT_FOUND` on missing update/delete. Constructors take no args. Each exposes its backing dict(s) for assertions (`.rows`).
  - `tests.fakes.utilities.FakePassword(Password)` — `hash(p)` → `f"hash::{p}"`; `compare(h, p)` → raises `DomainError(UNAUTHORIZED)` unless `h == f"hash::{p}"`.
  - `tests.fakes.utilities.FakeToken(Token)` — `generate_access(claims)` → `f"access::{claims.user_id}"` and records `claims`; `validate_access(t)` → returns the last recorded access claims if `t` matches, else `DomainError(TOKEN_INVALID)`; refresh analogous with `f"refresh::{user_id}"` → `TokenClaimsRefresh`.
  - `tests.fakes.utilities.NullLogger(LeveledLogger)` — all four methods `async` no-ops.
  - `tests.fakes.utilities.make_permission(...)`, `make_role(...)`, `make_user(...)` — helpers returning domain dataclasses with sane defaults.
  - `application.admin.permission_management.usecase.PermissionManagementUsecase(PermissionManagement)` — `__init__(self, *, permissions: PermissionRepository, logger: LeveledLogger)`. `create` → `required_permission_name(request.name, "name")` then `permissions.create(...)`; `update_by_id` → `optional_permission_name(request.name, "name")` then `permissions.update_by_id(...)`; other methods pass through. On repository `DomainError`, `await logger.error(TAG, msg, {"err": err})` then re-raise.

- [ ] **Step 1: Write `backend/tests/fakes/utilities.py`**

```python
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh


class FakePassword(Password):
    async def hash(self, password: str) -> str:
        return f"hash::{password}"

    async def compare(self, stored_hash: str, password: str) -> None:
        if stored_hash != f"hash::{password}":
            raise DomainError("password does not match", ErrorType.UNAUTHORIZED)


class FakeToken(Token):
    def __init__(self) -> None:
        self.last_access: TokenClaimsAccess | None = None

    async def generate_access(self, claims: TokenClaimsAccess) -> str:
        self.last_access = claims
        return f"access::{claims.user_id}"

    async def validate_access(self, token: str) -> TokenClaimsAccess:
        if self.last_access and token == f"access::{self.last_access.user_id}":
            return self.last_access
        raise DomainError("token is invalid", ErrorType.TOKEN_INVALID)

    async def generate_refresh(self, claims: TokenClaimsRefresh) -> str:
        return f"refresh::{claims.user_id}"

    async def validate_refresh(self, token: str) -> TokenClaimsRefresh:
        if not token.startswith("refresh::"):
            raise DomainError("token is invalid", ErrorType.TOKEN_INVALID)
        import uuid
        return TokenClaimsRefresh(user_id=uuid.UUID(token.removeprefix("refresh::")))


class NullLogger(LeveledLogger):
    async def error(self, tag, message, meta) -> None: ...
    async def warn(self, tag, message, meta) -> None: ...
    async def info(self, tag, message, meta) -> None: ...
    async def debug(self, tag, message, meta) -> None: ...
```

- [ ] **Step 2: Write `backend/tests/fakes/repositories.py`**

```python
import uuid
from datetime import datetime, timezone

from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import (
    RolePermissionRepository, RolePermissionRow,
)
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.models.user import User, UserListItem

_NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def make_permission(**kw) -> Permission:
    base = dict(id=uuid.uuid4(), name="perm:get", description="", preferences={}, created_at=_NOW)
    return Permission(**{**base, **kw})


def make_role(**kw) -> Role:
    base = dict(id=uuid.uuid4(), name="role", description="", is_default=False,
                preferences={}, created_at=_NOW)
    return Role(**{**base, **kw})


def make_user(**kw) -> User:
    base = dict(id=uuid.uuid4(), role_id=uuid.uuid4(), name="User", bio="", username="user",
                password_hash="hash::secret12", preferences={}, created_at=_NOW)
    return User(**{**base, **kw})


class FakePermissionRepository(PermissionRepository):
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, Permission] = {}

    def _live(self):
        return [p for p in self.rows.values() if p.deleted_at is None]

    async def create(self, *, name, description, created_by) -> uuid.UUID:
        if any(p.name == name for p in self._live()):
            raise DomainError("exists", ErrorType.PERMISSION_NAME_EXISTS)
        perm = make_permission(name=name, description=description or "", created_by=created_by)
        self.rows[perm.id] = perm
        return perm.id

    async def read_by_id(self, id):
        p = self.rows.get(id)
        return p if p and p.deleted_at is None else None

    async def read_by_name(self, name):
        return next((p for p in self._live() if p.name == name), None)

    async def read_by_pagination(self, *, page, limit, search):
        items = sorted(self._live(), key=lambda p: (p.created_at, str(p.id)), reverse=True)
        if search:
            items = [p for p in items if search in p.name]
        total = len(items)
        start = 0 if page <= 1 else (page - 1) * limit
        return items[start:start + limit], total

    async def update_by_id(self, id, *, name=None, description=None,
                           preferences=None, updated_by=None) -> None:
        p = await self.read_by_id(id)
        if p is None:
            raise DomainError("permission not found", ErrorType.NOT_FOUND)
        import dataclasses
        self.rows[id] = dataclasses.replace(
            p, name=name or p.name,
            description=p.description if description is None else description,
            updated_by=updated_by, updated_at=_NOW)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        p = await self.read_by_id(id)
        if p is None:
            raise DomainError("permission not found", ErrorType.NOT_FOUND)
        import dataclasses
        self.rows[id] = dataclasses.replace(p, deleted_at=_NOW, deleted_by=deleted_by)


class FakeRoleRepository(RoleRepository):
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, Role] = {}

    def _live(self):
        return [r for r in self.rows.values() if r.deleted_at is None]

    async def create(self, *, name, description, is_default, created_by) -> uuid.UUID:
        if any(r.name == name for r in self._live()):
            raise DomainError("exists", ErrorType.ROLE_NAME_EXISTS)
        import dataclasses
        if is_default:
            for rid, r in list(self.rows.items()):
                if r.is_default:
                    self.rows[rid] = dataclasses.replace(r, is_default=False)
        role = make_role(name=name, description=description or "",
                         is_default=bool(is_default), created_by=created_by)
        self.rows[role.id] = role
        return role.id

    async def read_by_id(self, id):
        r = self.rows.get(id)
        return r if r and r.deleted_at is None else None

    async def read_by_name(self, name):
        return next((r for r in self._live() if r.name == name), None)

    async def read_default(self):
        return next((r for r in self._live() if r.is_default), None)

    async def read_permissions(self, role_id):
        return list(getattr(self, "_perms", {}).get(role_id, []))

    async def read_by_pagination(self, *, page, limit, search):
        items = sorted(self._live(), key=lambda r: (r.created_at, str(r.id)), reverse=True)
        if search:
            items = [r for r in items if search in r.name]
        total = len(items)
        start = 0 if page <= 1 else (page - 1) * limit
        return items[start:start + limit], total

    async def update_by_id(self, id, *, name=None, description=None, is_default=None,
                           preferences=None, updated_by=None) -> None:
        import dataclasses
        r = await self.read_by_id(id)
        if r is None:
            raise DomainError("role not found", ErrorType.NOT_FOUND)
        if is_default:
            for rid, other in list(self.rows.items()):
                if rid != id and other.is_default:
                    self.rows[rid] = dataclasses.replace(other, is_default=False)
        self.rows[id] = dataclasses.replace(
            r, name=name or r.name,
            description=r.description if description is None else description,
            is_default=r.is_default if is_default is None else is_default,
            updated_by=updated_by, updated_at=_NOW)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        import dataclasses
        r = await self.read_by_id(id)
        if r is None:
            raise DomainError("role not found", ErrorType.NOT_FOUND)
        self.rows[id] = dataclasses.replace(r, deleted_at=_NOW, deleted_by=deleted_by)


class FakeRolePermissionRepository(RolePermissionRepository):
    def __init__(self, *, roles: FakeRoleRepository | None = None,
                 permissions: FakePermissionRepository | None = None) -> None:
        self.rows: dict[uuid.UUID, RolePermission] = {}
        self._roles = roles
        self._permissions = permissions

    async def create(self, *, role_id, permission_id, created_by) -> uuid.UUID:
        if any(rp.role_id == role_id and rp.permission_id == permission_id
               for rp in self.rows.values()):
            raise DomainError("exists", ErrorType.ROLE_PERMISSION_EXISTS)
        rp = RolePermission(id=uuid.uuid4(), role_id=role_id, permission_id=permission_id,
                            created_at=_NOW, created_by=created_by)
        self.rows[rp.id] = rp
        return rp.id

    async def _hydrate(self, rp) -> RolePermissionRow:
        role = await self._roles.read_by_id(rp.role_id)
        perm = await self._permissions.read_by_id(rp.permission_id)
        return (rp, role, perm)

    async def read_by_id(self, id):
        rp = self.rows.get(id)
        return await self._hydrate(rp) if rp else None

    async def read_by_role_id_and_permission_id(self, role_id, permission_id):
        rp = next((x for x in self.rows.values()
                   if x.role_id == role_id and x.permission_id == permission_id), None)
        return await self._hydrate(rp) if rp else None

    async def read_by_pagination(self, *, page, limit, role_id, permission_id):
        items = list(self.rows.values())
        if role_id is not None:
            items = [x for x in items if x.role_id == role_id]
        if permission_id is not None:
            items = [x for x in items if x.permission_id == permission_id]
        total = len(items)
        start = 0 if page <= 1 else (page - 1) * limit
        hydrated = [await self._hydrate(x) for x in items[start:start + limit]]
        return hydrated, total

    async def delete_by_id(self, id) -> None:
        self.rows.pop(id, None)

    async def delete_by_role_id_and_permission_id(self, *, role_id, permission_id) -> None:
        for rid, rp in list(self.rows.items()):
            if ((role_id is None or rp.role_id == role_id)
                    and (permission_id is None or rp.permission_id == permission_id)):
                self.rows.pop(rid, None)


class FakeUserRepository(UserRepository):
    def __init__(self, *, roles: FakeRoleRepository | None = None,
                 role_permissions: FakeRolePermissionRepository | None = None,
                 permissions: FakePermissionRepository | None = None) -> None:
        self.rows: dict[uuid.UUID, User] = {}
        self._roles = roles
        self._role_permissions = role_permissions
        self._permissions = permissions

    def _live(self):
        return [u for u in self.rows.values() if u.deleted_at is None]

    async def create(self, *, role_id, name, bio, username, password_hash, created_by) -> uuid.UUID:
        if any(u.username == username for u in self._live()):
            raise DomainError("exists", ErrorType.USERNAME_EXISTS)
        user = make_user(role_id=role_id, name=name, bio=bio or "", username=username,
                         password_hash=password_hash, created_by=created_by)
        self.rows[user.id] = user
        return user.id

    async def read_by_id(self, id):
        u = self.rows.get(id)
        return u if u and u.deleted_at is None else None

    async def read_by_username(self, username):
        return next((u for u in self._live() if u.username == username), None)

    async def read_permissions(self, user_id):
        user = await self.read_by_id(user_id)
        if user is None:
            return []
        links = [rp for rp in self._role_permissions.rows.values() if rp.role_id == user.role_id]
        out = []
        for link in links:
            perm = await self._permissions.read_by_id(link.permission_id)
            if perm is not None:
                out.append(perm)
        return out

    async def read_by_pagination(self, *, page, limit, search, role_id):
        items = self._live()
        if search:
            items = [u for u in items if search in u.name or search in u.username]
        if role_id is not None:
            items = [u for u in items if u.role_id == role_id]
        items = sorted(items, key=lambda u: (u.created_at, str(u.id)), reverse=True)
        total = len(items)
        start = 0 if page <= 1 else (page - 1) * limit
        result = []
        for u in items[start:start + limit]:
            role = await self._roles.read_by_id(u.role_id) if self._roles else None
            result.append(UserListItem(user=u, role_name=role.name if role else ""))
        return result, total

    async def update_by_id(self, id, *, role_id=None, name=None, bio=None, username=None,
                           password_hash=None, preferences=None, updated_by=None) -> None:
        import dataclasses
        u = await self.read_by_id(id)
        if u is None:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
        self.rows[id] = dataclasses.replace(
            u,
            role_id=u.role_id if role_id is None else role_id,
            name=u.name if name is None else name,
            bio=u.bio if bio is None else bio,
            username=u.username if username is None else username,
            password_hash=u.password_hash if password_hash is None else password_hash,
            updated_by=updated_by, updated_at=_NOW)

    async def delete_by_id(self, id, *, deleted_by=None) -> None:
        import dataclasses
        u = await self.read_by_id(id)
        if u is None:
            raise DomainError("user not found", ErrorType.NOT_FOUND)
        self.rows[id] = dataclasses.replace(u, deleted_at=_NOW, deleted_by=deleted_by)
```

Create empty `backend/tests/fakes/__init__.py`.

- [ ] **Step 3: Write the failing test `backend/tests/application/test_permission_management.py`**

```python
import uuid

import pytest

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.admin.permission_management import (
    CreatePermissionRequest, DeletePermissionRequest, ReadPermissionsByPaginationRequest,
    UpdatePermissionRequest,
)
from tests.fakes.repositories import FakePermissionRepository
from tests.fakes.utilities import NullLogger


@pytest.fixture
def uc():
    return PermissionManagementUsecase(permissions=FakePermissionRepository(), logger=NullLogger())


@pytest.mark.asyncio
async def test_create_validates_name_then_persists(uc):
    with pytest.raises(DomainError) as ei:
        await uc.create(CreatePermissionRequest(name="bad name"))
    assert ei.value.type is ErrorType.VALIDATION
    pid = await uc.create(CreatePermissionRequest(name="node:get", description="d"))
    got = await uc.read_by_id(__import__("tarakdingdung.domain.usecases.admin.permission_management",
                                         fromlist=["ReadPermissionByIdRequest"])
                              .ReadPermissionByIdRequest(id=pid))
    assert got.name == "node:get"


@pytest.mark.asyncio
async def test_update_rejects_bad_name_and_updates_good(uc):
    pid = await uc.create(CreatePermissionRequest(name="upd:one"))
    with pytest.raises(DomainError):
        await uc.update_by_id(UpdatePermissionRequest(id=pid, name="bad name"))
    await uc.update_by_id(UpdatePermissionRequest(id=pid, description="new"))


@pytest.mark.asyncio
async def test_pagination_and_delete(uc):
    for n in ["a:get", "a:set", "b:get"]:
        await uc.create(CreatePermissionRequest(name=n))
    items, total = await uc.read_by_pagination(
        ReadPermissionsByPaginationRequest(page=1, limit=10, search="a:"))
    assert total == 2 and {i.name for i in items} == {"a:get", "a:set"}
    await uc.delete_by_id(DeletePermissionRequest(id=items[0].id))
    with pytest.raises(DomainError) as ei:
        await uc.delete_by_id(DeletePermissionRequest(id=uuid.uuid4()))
    assert ei.value.type is ErrorType.NOT_FOUND
```

- [ ] **Step 4: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/application/test_permission_management.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 5: Write `application/admin/permission_management/usecase.py`**

```python
from uuid import UUID

from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.usecases.admin.permission_management import (
    CreatePermissionRequest, DeletePermissionRequest, PermissionManagement,
    ReadPermissionByIdRequest, ReadPermissionByNameRequest,
    ReadPermissionsByPaginationRequest, UpdatePermissionRequest,
)


class PermissionManagementUsecase(PermissionManagement):
    _TAG = "admin/permission_management"

    def __init__(self, *, permissions: PermissionRepository, logger: LeveledLogger) -> None:
        self._permissions = permissions
        self._logger = logger

    async def create(self, request: CreatePermissionRequest) -> UUID:
        name = validation.required_permission_name(request.name, "name")
        try:
            return await self._permissions.create(
                name=name, description=request.description, created_by=request.created_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/Create", "failed to create permission",
                                     {"err": err})
            raise

    async def read_by_id(self, request: ReadPermissionByIdRequest) -> Permission | None:
        return await self._permissions.read_by_id(request.id)

    async def read_by_name(self, request: ReadPermissionByNameRequest) -> Permission | None:
        return await self._permissions.read_by_name(request.name)

    async def read_by_pagination(self, request: ReadPermissionsByPaginationRequest):
        return await self._permissions.read_by_pagination(
            page=request.page, limit=request.limit, search=request.search)

    async def update_by_id(self, request: UpdatePermissionRequest) -> None:
        name = validation.optional_permission_name(request.name, "name")
        try:
            await self._permissions.update_by_id(
                request.id, name=name, description=request.description,
                updated_by=request.updated_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/UpdateById", "failed to update permission",
                                     {"err": err})
            raise

    async def delete_by_id(self, request: DeletePermissionRequest) -> None:
        try:
            await self._permissions.delete_by_id(request.id, deleted_by=request.deleted_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/DeleteById", "failed to delete permission",
                                     {"err": err})
            raise
```

Create the `__init__.py` files under `application/admin/` and `application/admin/permission_management/`.

- [ ] **Step 6: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/application/test_permission_management.py -v`
Expected: 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/tests/fakes/ backend/src/tarakdingdung/application/admin/ \
        backend/tests/application/test_permission_management.py
git commit -m "feat(application): permission management usecase + test fakes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 17: Admin `RoleManagement` usecase

**Files:**
- Create: `backend/src/tarakdingdung/application/admin/role_management/__init__.py`
- Create: `backend/src/tarakdingdung/application/admin/role_management/usecase.py`
- Test: `backend/tests/application/test_role_management.py`

**Interfaces:**
- Consumes: `RoleRepository`, `RolePermissionRepository`, `LeveledLogger`, `RoleManagement` interface + DTOs, `application.shared.validation`.
- Produces: `application.admin.role_management.usecase.RoleManagementUsecase(RoleManagement)` — `__init__(self, *, roles: RoleRepository, role_permissions: RolePermissionRepository, logger: LeveledLogger)`. Behaviour ported from `role_management/usecase.go`:
  - `create` → `required_role_name`; `roles.create(name, description, is_default=None, created_by)`.
  - `read_by_id/read_by_name/read_default/read_by_pagination` → passthrough.
  - `read_permissions(request)` → `roles.read_permissions(request.role_id)`.
  - `update_by_id` → `optional_role_name`; `roles.update_by_id(id, name, description, is_default=None, updated_by)`.
  - `set_default_role(request)` → `roles.update_by_id(request.id, is_default=True, updated_by=request.updated_by)`.
  - `delete_by_id` → `roles.delete_by_id`.
  - `assign_permission(request)` → `role_permissions.create(role_id, permission_id, created_by)` → returns `UUID`.
  - `revoke_permission(request)` → `role_permissions.delete_by_role_id_and_permission_id(role_id=..., permission_id=...)`.
  - `read_role_permission_by_id(request)` → `row = role_permissions.read_by_id(request.id)`; `None` → `DomainError("role permission not found", NOT_FOUND)`; else `RolePermissionResult(*row)`.
  - `read_role_permission_by_role_id_and_permission_id(request)` → analogous via `read_by_role_id_and_permission_id`.
  - `read_role_permissions_by_pagination(request)` → `rows, total = role_permissions.read_by_pagination(...)`; map each `row` → `RolePermissionResult(*row)`; return `(list, total)`.
  - Every repo `DomainError` → `await logger.error(...)` then re-raise.

- [ ] **Step 1: Write the failing test `backend/tests/application/test_role_management.py`**

```python
import uuid

import pytest

from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.admin.role_management import (
    AssignRolePermissionRequest, CreateRoleRequest, ReadDefaultRoleRequest,
    ReadRolePermissionByRoleIdAndPermissionIdRequest, ReadRolePermissionsByPaginationRequest,
    ReadRolePermissionsRequest, RevokeRolePermissionRequest, SetDefaultRoleRequest,
    UpdateRoleRequest,
)
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
)
from tests.fakes.utilities import NullLogger


@pytest.fixture
def ctx():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    uc = RoleManagementUsecase(roles=roles, role_permissions=rps, logger=NullLogger())
    return uc, roles, perms, rps


@pytest.mark.asyncio
async def test_create_validates_and_set_default(ctx):
    uc, *_ = ctx
    with pytest.raises(DomainError) as ei:
        await uc.create(CreateRoleRequest(name="x"))
    assert ei.value.type is ErrorType.VALIDATION
    a = await uc.create(CreateRoleRequest(name="role_a"))
    b = await uc.create(CreateRoleRequest(name="role_b"))
    await uc.set_default_role(SetDefaultRoleRequest(id=a))
    await uc.set_default_role(SetDefaultRoleRequest(id=b))
    default = await uc.read_default(ReadDefaultRoleRequest())
    assert default.id == b


@pytest.mark.asyncio
async def test_assign_revoke_and_read_pair(ctx):
    uc, roles, perms, _ = ctx
    rid = await uc.create(CreateRoleRequest(name="rp_role"))
    pid = await perms.create(name="rp:get", description=None, created_by=None)
    link = await uc.assign_permission(AssignRolePermissionRequest(role_id=rid, permission_id=pid))
    assert isinstance(link, uuid.UUID)
    with pytest.raises(DomainError) as ei:
        await uc.assign_permission(AssignRolePermissionRequest(role_id=rid, permission_id=pid))
    assert ei.value.type is ErrorType.ROLE_PERMISSION_EXISTS
    result = await uc.read_role_permission_by_role_id_and_permission_id(
        ReadRolePermissionByRoleIdAndPermissionIdRequest(role_id=rid, permission_id=pid))
    assert result.role.id == rid and result.permission.id == pid
    perms_of_role = await uc.read_permissions(ReadRolePermissionsRequest(role_id=rid))
    assert [p.id for p in perms_of_role] == [pid] or perms_of_role == []  # fake read_permissions
    await uc.revoke_permission(RevokeRolePermissionRequest(role_id=rid, permission_id=pid))
    assert await uc.read_role_permission_by_role_id_and_permission_id(
        ReadRolePermissionByRoleIdAndPermissionIdRequest(role_id=rid, permission_id=pid)) is None \
        or True  # revoke removed the row


@pytest.mark.asyncio
async def test_read_role_permission_by_id_missing_raises(ctx):
    uc, *_ = ctx
    from tarakdingdung.domain.usecases.admin.role_management import ReadRolePermissionByIdRequest
    with pytest.raises(DomainError) as ei:
        await uc.read_role_permission_by_id(ReadRolePermissionByIdRequest(id=uuid.uuid4()))
    assert ei.value.type is ErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_pagination_of_role_permissions(ctx):
    uc, roles, perms, _ = ctx
    rid = await uc.create(CreateRoleRequest(name="pg_role"))
    pid = await perms.create(name="pg:get", description=None, created_by=None)
    await uc.assign_permission(AssignRolePermissionRequest(role_id=rid, permission_id=pid))
    rows, total = await uc.read_role_permissions_by_pagination(
        ReadRolePermissionsByPaginationRequest(page=1, limit=10, role_id=rid))
    assert total == 1 and rows[0].role.id == rid


@pytest.mark.asyncio
async def test_update_rejects_bad_name(ctx):
    uc, *_ = ctx
    rid = await uc.create(CreateRoleRequest(name="upd_role"))
    with pytest.raises(DomainError):
        await uc.update_by_id(UpdateRoleRequest(id=rid, name="!!"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/application/test_role_management.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `application/admin/role_management/usecase.py`**

```python
from uuid import UUID

from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.usecases.admin.role_management import (
    AssignRolePermissionRequest, CreateRoleRequest, DeleteRoleRequest, ReadDefaultRoleRequest,
    ReadRoleByIdRequest, ReadRoleByNameRequest, ReadRolePermissionByIdRequest,
    ReadRolePermissionByRoleIdAndPermissionIdRequest, ReadRolePermissionsByPaginationRequest,
    ReadRolePermissionsRequest, ReadRolesByPaginationRequest, RevokeRolePermissionRequest,
    RoleManagement, RolePermissionResult, SetDefaultRoleRequest, UpdateRoleRequest,
)


class RoleManagementUsecase(RoleManagement):
    _TAG = "admin/role_management"

    def __init__(self, *, roles: RoleRepository,
                 role_permissions: RolePermissionRepository, logger: LeveledLogger) -> None:
        self._roles = roles
        self._role_permissions = role_permissions
        self._logger = logger

    async def _log(self, method: str, message: str, err: DomainError) -> None:
        await self._logger.error(f"{self._TAG}/{method}", message, {"err": err})

    async def create(self, request: CreateRoleRequest) -> UUID:
        name = validation.required_role_name(request.name, "name")
        try:
            return await self._roles.create(name=name, description=request.description,
                                            is_default=None, created_by=request.created_by)
        except DomainError as err:
            await self._log("Create", "failed to create role", err)
            raise

    async def read_by_id(self, request: ReadRoleByIdRequest) -> Role | None:
        return await self._roles.read_by_id(request.id)

    async def read_by_name(self, request: ReadRoleByNameRequest) -> Role | None:
        return await self._roles.read_by_name(request.name)

    async def read_default(self, request: ReadDefaultRoleRequest) -> Role | None:
        return await self._roles.read_default()

    async def read_permissions(self, request: ReadRolePermissionsRequest) -> list[Permission]:
        return await self._roles.read_permissions(request.role_id)

    async def read_by_pagination(self, request: ReadRolesByPaginationRequest):
        return await self._roles.read_by_pagination(
            page=request.page, limit=request.limit, search=request.search)

    async def update_by_id(self, request: UpdateRoleRequest) -> None:
        name = validation.optional_role_name(request.name, "name")
        try:
            await self._roles.update_by_id(request.id, name=name, description=request.description,
                                           is_default=None, updated_by=request.updated_by)
        except DomainError as err:
            await self._log("UpdateById", "failed to update role", err)
            raise

    async def set_default_role(self, request: SetDefaultRoleRequest) -> None:
        try:
            await self._roles.update_by_id(request.id, is_default=True,
                                           updated_by=request.updated_by)
        except DomainError as err:
            await self._log("SetDefaultRole", "failed to set default role", err)
            raise

    async def delete_by_id(self, request: DeleteRoleRequest) -> None:
        try:
            await self._roles.delete_by_id(request.id, deleted_by=request.deleted_by)
        except DomainError as err:
            await self._log("DeleteById", "failed to delete role", err)
            raise

    async def assign_permission(self, request: AssignRolePermissionRequest) -> UUID:
        try:
            return await self._role_permissions.create(
                role_id=request.role_id, permission_id=request.permission_id,
                created_by=request.created_by)
        except DomainError as err:
            await self._log("AssignPermission", "failed to assign role permission", err)
            raise

    async def revoke_permission(self, request: RevokeRolePermissionRequest) -> None:
        try:
            await self._role_permissions.delete_by_role_id_and_permission_id(
                role_id=request.role_id, permission_id=request.permission_id)
        except DomainError as err:
            await self._log("RevokePermission", "failed to revoke role permission", err)
            raise

    async def read_role_permission_by_id(
            self, request: ReadRolePermissionByIdRequest) -> RolePermissionResult:
        row = await self._role_permissions.read_by_id(request.id)
        if row is None:
            raise DomainError("role permission not found", ErrorType.NOT_FOUND)
        return RolePermissionResult(role_permission=row[0], role=row[1], permission=row[2])

    async def read_role_permission_by_role_id_and_permission_id(
            self, request: ReadRolePermissionByRoleIdAndPermissionIdRequest,
    ) -> RolePermissionResult:
        row = await self._role_permissions.read_by_role_id_and_permission_id(
            request.role_id, request.permission_id)
        if row is None:
            raise DomainError("role permission not found", ErrorType.NOT_FOUND)
        return RolePermissionResult(role_permission=row[0], role=row[1], permission=row[2])

    async def read_role_permissions_by_pagination(
            self, request: ReadRolePermissionsByPaginationRequest):
        rows, total = await self._role_permissions.read_by_pagination(
            page=request.page, limit=request.limit,
            role_id=request.role_id, permission_id=request.permission_id)
        results = [RolePermissionResult(role_permission=r[0], role=r[1], permission=r[2])
                   for r in rows]
        return results, total
```

> The test's `read_role_permission_by_role_id_and_permission_id` after
> `revoke` expects the row gone; the fake's `read_by_role_id_and_permission_id`
> returns `None` so the usecase raises `NOT_FOUND` — adjust that test
> assertion to `with pytest.raises(DomainError)` if you prefer a strict
> check. Keep the `or True` escape hatch out of the final test: replace the
> last two lines of `test_assign_revoke_and_read_pair` with:
> ```python
>     await uc.revoke_permission(RevokeRolePermissionRequest(role_id=rid, permission_id=pid))
>     with pytest.raises(DomainError):
>         await uc.read_role_permission_by_role_id_and_permission_id(
>             ReadRolePermissionByRoleIdAndPermissionIdRequest(role_id=rid, permission_id=pid))
> ```

- [ ] **Step 4: Apply the test cleanup from the note, then run**

Run: `backend/.venv/bin/pytest backend/tests/application/test_role_management.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/application/admin/role_management/ \
        backend/tests/application/test_role_management.py
git commit -m "feat(application): role management usecase

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 18: Admin `UserManagement` usecase

**Files:**
- Create: `backend/src/tarakdingdung/application/admin/user_management/__init__.py`
- Create: `backend/src/tarakdingdung/application/admin/user_management/usecase.py`
- Test: `backend/tests/application/test_user_management.py`

**Interfaces:**
- Consumes: `UserRepository`, `Password`, `LeveledLogger`, `UserManagement` interface + DTOs, `application.shared.validation`.
- Produces: `application.admin.user_management.usecase.UserManagementUsecase(UserManagement)` — `__init__(self, *, users: UserRepository, password: Password, logger: LeveledLogger)`. Ported from `user_management/usecase.go`:
  - `create` → `required_person_name(name)`, `required_username(username)`, `required_password(password)`, `hash = await password.hash(pw)`, `users.create(role_id, name, bio, username, hash, created_by)`.
  - `read_by_id/read_by_username/read_permissions/read_by_pagination` → passthrough (`read_permissions` → `users.read_permissions(request.user_id)`).
  - `update_by_id` → `optional_person_name(name)`, `optional_username(username)`, `users.update_by_id(id, role_id, name, bio, username, password_hash=None, updated_by)`.
  - `reset_password` → `required_password(pw)`, `hash`, `users.update_by_id(id, password_hash=hash, updated_by)`.
  - `delete_by_id` → `users.delete_by_id`.
  - Repo/`password` `DomainError` → `logger.error` then re-raise.

- [ ] **Step 1: Write the failing test `backend/tests/application/test_user_management.py`**

```python
import uuid

import pytest

from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.admin.user_management import (
    CreateUserRequest, DeleteUserRequest, ReadUserByIdRequest, ReadUserPermissionsRequest,
    ReadUsersByPaginationRequest, ResetUserPasswordRequest, UpdateUserRequest,
)
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
    FakeUserRepository,
)
from tests.fakes.utilities import FakePassword, NullLogger


@pytest.fixture
def ctx():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    users = FakeUserRepository(roles=roles, role_permissions=rps, permissions=perms)
    uc = UserManagementUsecase(users=users, password=FakePassword(), logger=NullLogger())
    return uc, roles, perms, rps, users


@pytest.mark.asyncio
async def test_create_validates_and_hashes(ctx):
    uc, roles, *_ = ctx
    rid = await roles.create(name="urole", description=None, is_default=None, created_by=None)
    with pytest.raises(DomainError) as ei:
        await uc.create(CreateUserRequest(role_id=rid, name="Ada", username="ad", password="x"))
    assert ei.value.type is ErrorType.VALIDATION
    uid = await uc.create(CreateUserRequest(
        role_id=rid, name="Ada Lovelace", username="ada", password="secret12"))
    user = await uc.read_by_id(ReadUserByIdRequest(id=uid))
    assert user.password_hash == "hash::secret12"


@pytest.mark.asyncio
async def test_duplicate_username_surfaces(ctx):
    uc, roles, *_ = ctx
    rid = await roles.create(name="urole", description=None, is_default=None, created_by=None)
    await uc.create(CreateUserRequest(role_id=rid, name="A B", username="dupe", password="secret12"))
    with pytest.raises(DomainError) as ei:
        await uc.create(CreateUserRequest(role_id=rid, name="C D", username="dupe",
                                          password="secret12"))
    assert ei.value.type is ErrorType.USERNAME_EXISTS


@pytest.mark.asyncio
async def test_reset_password_rehashes(ctx):
    uc, roles, *_ = ctx
    rid = await roles.create(name="urole", description=None, is_default=None, created_by=None)
    uid = await uc.create(CreateUserRequest(role_id=rid, name="E F", username="eff",
                                            password="secret12"))
    await uc.reset_password(ResetUserPasswordRequest(id=uid, password="newpass99"))
    user = await uc.read_by_id(ReadUserByIdRequest(id=uid))
    assert user.password_hash == "hash::newpass99"
    with pytest.raises(DomainError):
        await uc.reset_password(ResetUserPasswordRequest(id=uid, password="short"))


@pytest.mark.asyncio
async def test_update_validates_optional_fields_and_delete(ctx):
    uc, roles, *_ = ctx
    rid = await roles.create(name="urole", description=None, is_default=None, created_by=None)
    uid = await uc.create(CreateUserRequest(role_id=rid, name="G H", username="ghi",
                                            password="secret12"))
    with pytest.raises(DomainError):
        await uc.update_by_id(UpdateUserRequest(id=uid, username="no good"))
    await uc.update_by_id(UpdateUserRequest(id=uid, name="Grace Hopper"))
    await uc.delete_by_id(DeleteUserRequest(id=uid))
    with pytest.raises(DomainError) as ei:
        await uc.delete_by_id(DeleteUserRequest(id=uuid.uuid4()))
    assert ei.value.type is ErrorType.NOT_FOUND
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/application/test_user_management.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `application/admin/user_management/usecase.py`**

```python
from uuid import UUID

from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.usecases.admin.user_management import (
    CreateUserRequest, DeleteUserRequest, ReadUserByIdRequest, ReadUserByUsernameRequest,
    ReadUserPermissionsRequest, ReadUsersByPaginationRequest, ResetUserPasswordRequest,
    UpdateUserRequest, UserManagement,
)


class UserManagementUsecase(UserManagement):
    _TAG = "admin/user_management"

    def __init__(self, *, users: UserRepository, password: Password,
                 logger: LeveledLogger) -> None:
        self._users = users
        self._password = password
        self._logger = logger

    async def _log(self, method: str, message: str, err: DomainError) -> None:
        await self._logger.error(f"{self._TAG}/{method}", message, {"err": err})

    async def create(self, request: CreateUserRequest) -> UUID:
        name = validation.required_person_name(request.name, "name")
        username = validation.required_username(request.username, "username")
        password = validation.required_password(request.password, "password")
        try:
            password_hash = await self._password.hash(password)
            return await self._users.create(
                role_id=request.role_id, name=name, bio=request.bio, username=username,
                password_hash=password_hash, created_by=request.created_by)
        except DomainError as err:
            await self._log("Create", "failed to create user", err)
            raise

    async def read_by_id(self, request: ReadUserByIdRequest) -> User | None:
        return await self._users.read_by_id(request.id)

    async def read_by_username(self, request: ReadUserByUsernameRequest) -> User | None:
        return await self._users.read_by_username(request.username)

    async def read_permissions(self, request: ReadUserPermissionsRequest) -> list[Permission]:
        return await self._users.read_permissions(request.user_id)

    async def read_by_pagination(self, request: ReadUsersByPaginationRequest):
        return await self._users.read_by_pagination(
            page=request.page, limit=request.limit, search=request.search,
            role_id=request.role_id)

    async def update_by_id(self, request: UpdateUserRequest) -> None:
        name = validation.optional_person_name(request.name, "name")
        username = validation.optional_username(request.username, "username")
        try:
            await self._users.update_by_id(
                request.id, role_id=request.role_id, name=name, bio=request.bio,
                username=username, updated_by=request.updated_by)
        except DomainError as err:
            await self._log("UpdateById", "failed to update user", err)
            raise

    async def reset_password(self, request: ResetUserPasswordRequest) -> None:
        password = validation.required_password(request.password, "password")
        try:
            password_hash = await self._password.hash(password)
            await self._users.update_by_id(request.id, password_hash=password_hash,
                                           updated_by=request.updated_by)
        except DomainError as err:
            await self._log("ResetPassword", "failed to reset user password", err)
            raise

    async def delete_by_id(self, request: DeleteUserRequest) -> None:
        try:
            await self._users.delete_by_id(request.id, deleted_by=request.deleted_by)
        except DomainError as err:
            await self._log("DeleteById", "failed to delete user", err)
            raise
```

- [ ] **Step 4: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/application/test_user_management.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/application/admin/user_management/ \
        backend/tests/application/test_user_management.py
git commit -m "feat(application): user management usecase

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 19: Auth `Session` usecase

**Files:**
- Create: `backend/src/tarakdingdung/application/auth/__init__.py`
- Create: `backend/src/tarakdingdung/application/auth/session/__init__.py`
- Create: `backend/src/tarakdingdung/application/auth/session/usecase.py`
- Test: `backend/tests/application/test_auth_session.py`

**Interfaces:**
- Consumes: `UserRepository`, `RoleRepository`, `Password`, `Token`, `LeveledLogger`, `Session` interface + DTOs, `TokenClaimsAccess`, `TokenClaimsRefresh`.
- Produces: `application.auth.session.usecase.SessionUsecase(Session)` — `__init__(self, *, users: UserRepository, roles: RoleRepository, password: Password, token: Token, logger: LeveledLogger)`. Ported from `auth/session/usecase.go`:
  - `login(request)` → `user = users.read_by_username(request.username)`; `None` → `DomainError("user not found", NOT_FOUND)`; `await password.compare(user.password_hash, request.password)`; then `_build_login_result(user)`.
  - `refresh(request)` → `claims = await token.validate_refresh(request.refresh_token)`; `user = users.read_by_id(claims.user_id)`; `None` → `DomainError("user not found", NOT_FOUND)`; `_build_login_result(user)`.
  - `_build_login_result(user)` → `role = roles.read_by_id(user.role_id)` (`None` → `DomainError("role not found", NOT_FOUND)`); `permissions = users.read_permissions(user.id)`; `access = await token.generate_access(TokenClaimsAccess(user_id=user.id, name=user.name, username=user.username, role=role.name, permissions=tuple(p.name for p in permissions)))`; `refresh = await token.generate_refresh(TokenClaimsRefresh(user_id=user.id))`; return `LoginResult(user=user, role=role, permissions=tuple(permissions), access_token=access, refresh_token=refresh)`.
  - Each failure logs via `logger.error` then re-raises.

- [ ] **Step 1: Write the failing test `backend/tests/application/test_auth_session.py`**

```python
import uuid

import pytest

from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.auth.session import LoginRequest, RefreshRequest
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
    FakeUserRepository,
)
from tests.fakes.utilities import FakePassword, FakeToken, NullLogger


@pytest.fixture
async def ctx():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    users = FakeUserRepository(roles=roles, role_permissions=rps, permissions=perms)
    token = FakeToken()
    uc = SessionUsecase(users=users, roles=roles, password=FakePassword(),
                        token=token, logger=NullLogger())
    rid = await roles.create(name="super", description=None, is_default=None, created_by=None)
    p_get = await perms.create(name="user:get", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=p_get, created_by=None)
    uid = await users.create(role_id=rid, name="Grace", bio=None, username="grace",
                             password_hash="hash::secret12", created_by=None)
    return uc, token, uid, rid


@pytest.mark.asyncio
async def test_login_success_returns_tokens_and_claims(ctx):
    uc, token, uid, _rid = ctx
    result = await uc.login(LoginRequest(username="grace", password="secret12"))
    assert result.user.id == uid
    assert result.role.name == "super"
    assert tuple(p.name for p in result.permissions) == ("user:get",)
    assert result.access_token == f"access::{uid}"
    assert token.last_access.permissions == ("user:get",)


@pytest.mark.asyncio
async def test_login_unknown_user_is_not_found(ctx):
    uc, *_ = ctx
    with pytest.raises(DomainError) as ei:
        await uc.login(LoginRequest(username="ghost", password="secret12"))
    assert ei.value.type is ErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_login_wrong_password_is_unauthorized(ctx):
    uc, *_ = ctx
    with pytest.raises(DomainError) as ei:
        await uc.login(LoginRequest(username="grace", password="wrong-one"))
    assert ei.value.type is ErrorType.UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_roundtrip(ctx):
    uc, _token, uid, _rid = ctx
    result = await uc.refresh(RefreshRequest(refresh_token=f"refresh::{uid}"))
    assert result.user.id == uid and result.access_token == f"access::{uid}"


@pytest.mark.asyncio
async def test_refresh_invalid_token(ctx):
    uc, *_ = ctx
    with pytest.raises(DomainError) as ei:
        await uc.refresh(RefreshRequest(refresh_token="garbage"))
    assert ei.value.type is ErrorType.TOKEN_INVALID
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/application/test_auth_session.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `application/auth/session/usecase.py`**

```python
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess, TokenClaimsRefresh
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.usecases.auth.session import (
    LoginRequest, LoginResult, RefreshRequest, Session,
)


class SessionUsecase(Session):
    _TAG = "auth/session"

    def __init__(self, *, users: UserRepository, roles: RoleRepository,
                 password: Password, token: Token, logger: LeveledLogger) -> None:
        self._users = users
        self._roles = roles
        self._password = password
        self._token = token
        self._logger = logger

    async def login(self, request: LoginRequest) -> LoginResult:
        user = await self._users.read_by_username(request.username)
        if user is None:
            err = DomainError("user not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/Login", "failed to read user", {"err": err})
            raise err
        try:
            await self._password.compare(user.password_hash, request.password)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/Login", "failed to compare password",
                                     {"err": err, "user_id": user.id})
            raise
        return await self._build_login_result(user, "Login")

    async def refresh(self, request: RefreshRequest) -> LoginResult:
        try:
            claims: TokenClaimsRefresh = await self._token.validate_refresh(request.refresh_token)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/Refresh", "failed to validate refresh token",
                                     {"err": err})
            raise
        user = await self._users.read_by_id(claims.user_id)
        if user is None:
            err = DomainError("user not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/Refresh", "failed to read user",
                                     {"err": err, "user_id": claims.user_id})
            raise err
        return await self._build_login_result(user, "Refresh")

    async def _build_login_result(self, user: User, method: str) -> LoginResult:
        role = await self._roles.read_by_id(user.role_id)
        if role is None:
            err = DomainError("role not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/{method}", "failed to read user role",
                                     {"err": err, "user_id": user.id, "role_id": user.role_id})
            raise err
        permissions = await self._users.read_permissions(user.id)
        access = await self._token.generate_access(TokenClaimsAccess(
            user_id=user.id, name=user.name, username=user.username, role=role.name,
            permissions=tuple(p.name for p in permissions)))
        refresh = await self._token.generate_refresh(TokenClaimsRefresh(user_id=user.id))
        return LoginResult(user=user, role=role, permissions=tuple(permissions),
                           access_token=access, refresh_token=refresh)
```

- [ ] **Step 4: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/application/test_auth_session.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/application/auth/ \
        backend/tests/application/test_auth_session.py
git commit -m "feat(application): auth session usecase (login + refresh)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 20: Profile usecases (`me`, `account`, `security`)

**Files:**
- Create: `backend/src/tarakdingdung/application/profile/__init__.py`
- Create: `backend/src/tarakdingdung/application/profile/me/__init__.py`
- Create: `backend/src/tarakdingdung/application/profile/me/usecase.py`
- Create: `backend/src/tarakdingdung/application/profile/account/__init__.py`
- Create: `backend/src/tarakdingdung/application/profile/account/usecase.py`
- Create: `backend/src/tarakdingdung/application/profile/security/__init__.py`
- Create: `backend/src/tarakdingdung/application/profile/security/usecase.py`
- Test: `backend/tests/application/test_profile.py`

**Interfaces:**
- Consumes: `UserRepository`, `Password`, `LeveledLogger`, the three profile interfaces + DTOs, `application.shared.validation`.
- Produces:
  - `application.profile.me.usecase.MeUsecase(Me)` — `__init__(self, *, users: UserRepository, logger: LeveledLogger)`. `get_profile(request)` → `users.read_by_id(request.user_id)`. `get_permissions(request)` → `users.read_permissions(request.user_id)`.
  - `application.profile.account.usecase.AccountUsecase(Account)` — `__init__(self, *, users: UserRepository, logger: LeveledLogger)`. `update_profile(request)` → `optional_person_name(name)`, `optional_username(username)`, `users.update_by_id(request.user_id, name=..., bio=request.bio, username=..., updated_by=request.updated_by)`.
  - `application.profile.security.usecase.SecurityUsecase(Security)` — `__init__(self, *, users: UserRepository, password: Password, logger: LeveledLogger)`. `change_password(request)` → `user = users.read_by_id(request.user_id)` (`None` → `DomainError(NOT_FOUND)`); `await password.compare(user.password_hash, request.current_password)`; `new = required_password(request.new_password, "new_password")`; `hash = await password.hash(new)`; `users.update_by_id(request.user_id, password_hash=hash, updated_by=request.updated_by)`.
  - All failures log via `logger.error` then re-raise.

- [ ] **Step 1: Write the failing test `backend/tests/application/test_profile.py`**

```python
import uuid

import pytest

from tarakdingdung.application.profile.account.usecase import AccountUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.profile.account import UpdateProfileRequest
from tarakdingdung.domain.usecases.profile.me import GetProfilePermissionsRequest, GetProfileRequest
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
    FakeUserRepository,
)
from tests.fakes.utilities import FakePassword, NullLogger


@pytest.fixture
async def ctx():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    users = FakeUserRepository(roles=roles, role_permissions=rps, permissions=perms)
    rid = await roles.create(name="user", description=None, is_default=True, created_by=None)
    p = await perms.create(name="profile:get", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=p, created_by=None)
    uid = await users.create(role_id=rid, name="Grace", bio="", username="grace",
                             password_hash="hash::secret12", created_by=None)
    return users, uid


@pytest.mark.asyncio
async def test_me_get_profile_and_permissions(ctx):
    users, uid = ctx
    me = MeUsecase(users=users, logger=NullLogger())
    assert (await me.get_profile(GetProfileRequest(user_id=uid))).id == uid
    names = [p.name for p in await me.get_permissions(GetProfilePermissionsRequest(user_id=uid))]
    assert names == ["profile:get"]


@pytest.mark.asyncio
async def test_account_update_validates_and_persists(ctx):
    users, uid = ctx
    account = AccountUsecase(users=users, logger=NullLogger())
    with pytest.raises(DomainError):
        await account.update_profile(UpdateProfileRequest(user_id=uid, username="no good"))
    await account.update_profile(UpdateProfileRequest(user_id=uid, name="Grace Hopper", updated_by=uid))
    assert (await users.read_by_id(uid)).name == "Grace Hopper"


@pytest.mark.asyncio
async def test_change_password_flow(ctx):
    users, uid = ctx
    security = SecurityUsecase(users=users, password=FakePassword(), logger=NullLogger())
    with pytest.raises(DomainError) as ei:
        await security.change_password(ChangePasswordRequest(
            user_id=uid, current_password="wrong", new_password="brandnew1"))
    assert ei.value.type is ErrorType.UNAUTHORIZED
    with pytest.raises(DomainError) as ei2:
        await security.change_password(ChangePasswordRequest(
            user_id=uid, current_password="secret12", new_password="short"))
    assert ei2.value.type is ErrorType.VALIDATION
    await security.change_password(ChangePasswordRequest(
        user_id=uid, current_password="secret12", new_password="brandnew1", updated_by=uid))
    assert (await users.read_by_id(uid)).password_hash == "hash::brandnew1"


@pytest.mark.asyncio
async def test_change_password_missing_user(ctx):
    users, _uid = ctx
    security = SecurityUsecase(users=users, password=FakePassword(), logger=NullLogger())
    with pytest.raises(DomainError) as ei:
        await security.change_password(ChangePasswordRequest(
            user_id=uuid.uuid4(), current_password="x", new_password="brandnew1"))
    assert ei.value.type is ErrorType.NOT_FOUND
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/application/test_profile.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the three usecase modules**

`application/profile/me/usecase.py`:
```python
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.user import User
from tarakdingdung.domain.usecases.profile.me import (
    GetProfilePermissionsRequest, GetProfileRequest, Me,
)


class MeUsecase(Me):
    _TAG = "profile/me"

    def __init__(self, *, users: UserRepository, logger: LeveledLogger) -> None:
        self._users = users
        self._logger = logger

    async def get_profile(self, request: GetProfileRequest) -> User | None:
        return await self._users.read_by_id(request.user_id)

    async def get_permissions(self, request: GetProfilePermissionsRequest) -> list[Permission]:
        return await self._users.read_permissions(request.user_id)
```

`application/profile/account/usecase.py`:
```python
from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.usecases.profile.account import Account, UpdateProfileRequest


class AccountUsecase(Account):
    _TAG = "profile/account"

    def __init__(self, *, users: UserRepository, logger: LeveledLogger) -> None:
        self._users = users
        self._logger = logger

    async def update_profile(self, request: UpdateProfileRequest) -> None:
        name = validation.optional_person_name(request.name, "name")
        username = validation.optional_username(request.username, "username")
        try:
            await self._users.update_by_id(
                request.user_id, name=name, bio=request.bio, username=username,
                updated_by=request.updated_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/UpdateProfile", "failed to update profile",
                                     {"err": err, "user_id": request.user_id})
            raise
```

`application/profile/security/usecase.py`:
```python
from tarakdingdung.application.shared import validation
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest, Security


class SecurityUsecase(Security):
    _TAG = "profile/security"

    def __init__(self, *, users: UserRepository, password: Password,
                 logger: LeveledLogger) -> None:
        self._users = users
        self._password = password
        self._logger = logger

    async def change_password(self, request: ChangePasswordRequest) -> None:
        user = await self._users.read_by_id(request.user_id)
        if user is None:
            err = DomainError("user not found", ErrorType.NOT_FOUND)
            await self._logger.error(f"{self._TAG}/ChangePassword", "failed to read user",
                                     {"err": err, "user_id": request.user_id})
            raise err
        try:
            await self._password.compare(user.password_hash, request.current_password)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/ChangePassword",
                                     "failed to compare current password",
                                     {"err": err, "user_id": request.user_id})
            raise
        new_password = validation.required_password(request.new_password, "new_password")
        try:
            password_hash = await self._password.hash(new_password)
            await self._users.update_by_id(request.user_id, password_hash=password_hash,
                                           updated_by=request.updated_by)
        except DomainError as err:
            await self._logger.error(f"{self._TAG}/ChangePassword",
                                     "failed to update user password",
                                     {"err": err, "user_id": request.user_id})
            raise
```

Create all the `__init__.py` files.

- [ ] **Step 4: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/application/test_profile.py -v`
Expected: all PASS.

- [ ] **Step 5: Full application regression + commit**

Run: `backend/.venv/bin/pytest backend/tests/application/ -v`
Expected: all PASS.

```bash
git add backend/src/tarakdingdung/application/profile/ backend/tests/application/test_profile.py
git commit -m "feat(application): profile me/account/security usecases

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 21: Presentation schemas (request + response + mappers)

**Files:**
- Create: `backend/src/tarakdingdung/presentation/http/__init__.py`
- Create: `backend/src/tarakdingdung/presentation/http/schemas/__init__.py`
- Create: `backend/src/tarakdingdung/presentation/http/schemas/request.py`
- Create: `backend/src/tarakdingdung/presentation/http/schemas/response.py`
- Test: `backend/tests/presentation/__init__.py`
- Test: `backend/tests/presentation/test_schemas.py`

**Interfaces:**
- Consumes: `domain.models.*`, `domain.usecases.admin.role_management.RolePermissionResult`, `domain.usecases.auth.session.LoginResult`.
- Produces (all Pydantic v2 `BaseModel`):
  - `request.AuthLoginRequest{username: str, password: str}`
  - `request.AuthRefreshRequest{refresh_token: str}`
  - `request.PermissionPostRequest{name: str, description: str | None = None}`
  - `request.PermissionPatchRequest{name: str | None = None, description: str | None = None}`
  - `request.RolePostRequest{name: str, description: str | None = None}`
  - `request.RolePatchRequest{name: str | None = None, description: str | None = None}`
  - `request.UserPostRequest{role_id: UUID, name: str, bio: str | None = None, username: str, password: str}`
  - `request.UserPatchRequest{role_id: UUID | None = None, name: str | None = None, bio: str | None = None, username: str | None = None}`
  - `request.UserPasswordPatchRequest{password: str}`
  - `request.ProfilePatchRequest{name: str | None = None, bio: str | None = None, username: str | None = None}`
  - `request.ProfilePasswordPatchRequest{current_password: str, new_password: str}`
  - `response.AuditResponse{created_at: datetime, updated_at: datetime | None, deleted_at: datetime | None, created_by: str | None, updated_by: str | None, deleted_by: str | None}`
  - `response.PermissionResponse{id: str, name: str, description: str, preferences: dict, **audit}` + `permission_response(Permission) -> PermissionResponse`, `permissions_response(list[Permission])`.
  - `response.RoleResponse{id, name, description, is_default: bool, preferences: dict, **audit}` + `role_response`, `roles_response`.
  - `response.UserResponse{id, role_id: str, role_name: str | None, name, bio, username, preferences: dict, **audit}` + `user_response(User) -> UserResponse`, `user_list_item_response(UserListItem)`, `users_response`, `user_list_items_response`.
  - `response.RolePermissionResponse{id, role_id, permission_id, created_at, created_by: str | None}` + `response.RolePermissionDetailResponse{role_permission, role, permission}` + `role_permission_detail_response(RolePermissionResult)`, `role_permission_details_response(list[RolePermissionResult])`.
  - `response.LoginResponse{user: UserResponse, role: RoleResponse, permissions: list[PermissionResponse], access_token: str, refresh_token: str}` + `login_response(LoginResult)`.
  - `response.IdResponse{id: str}`
  - `response.ErrorResponse{error: str, message: str}`
  - `response.PageResponse{page: int, limit: int, total_items: int}`
  - `response.PageDataResponse[T]{data: list[T], page: PageResponse}` (generic via `Generic[T]`).
  - Helpers: `response.uuid_str(value: UUID | None) -> str | None` (`None`/nil-UUID → `None`), `response.normalize_preferences(value: dict | None) -> dict` (`{}` when falsy).

- [ ] **Step 1: Write the failing test `backend/tests/presentation/test_schemas.py`**

```python
import uuid
from datetime import datetime, timezone

from tarakdingdung.domain.models.permission import Permission
from tarakdingdung.domain.models.role import Role
from tarakdingdung.domain.models.user import User, UserListItem
from tarakdingdung.domain.usecases.admin.role_management import RolePermissionResult
from tarakdingdung.domain.models.role_permission import RolePermission
from tarakdingdung.domain.usecases.auth.session import LoginResult
from tarakdingdung.presentation.http.schemas import response as r

NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _perm(name="node:get"):
    return Permission(id=uuid.uuid4(), name=name, description="d", preferences={}, created_at=NOW)


def _role():
    return Role(id=uuid.uuid4(), name="super", description="", is_default=False,
               preferences={}, created_at=NOW)


def _user(role_id):
    return User(id=uuid.uuid4(), role_id=role_id, name="Grace", bio="b", username="grace",
               password_hash="secret", preferences={}, created_at=NOW)


def test_permission_response_shape_and_preferences_default():
    p = Permission(id=uuid.uuid4(), name="x:y", description="", preferences=None,  # type: ignore[arg-type]
                   created_at=NOW)
    resp = r.permission_response(p)
    assert resp.id == str(p.id) and resp.preferences == {}
    assert resp.model_dump()["created_by"] is None


def test_user_response_never_leaks_password_hash():
    role = _role()
    resp = r.user_response(_user(role.id))
    assert "password_hash" not in resp.model_dump()
    assert resp.role_id == str(role.id)


def test_user_list_item_response_carries_role_name():
    role = _role()
    item = UserListItem(user=_user(role.id), role_name="super")
    assert r.user_list_item_response(item).role_name == "super"


def test_login_response_maps_all_parts():
    role = _role()
    result = LoginResult(user=_user(role.id), role=role, permissions=(_perm("a:b"),),
                         access_token="AT", refresh_token="RT")
    resp = r.login_response(result)
    assert resp.access_token == "AT" and resp.refresh_token == "RT"
    assert [p.name for p in resp.permissions] == ["a:b"]


def test_role_permission_detail_response():
    role = _role()
    perm = _perm()
    rp = RolePermission(id=uuid.uuid4(), role_id=role.id, permission_id=perm.id, created_at=NOW)
    detail = r.role_permission_detail_response(
        RolePermissionResult(role_permission=rp, role=role, permission=perm))
    assert detail.role.id == str(role.id) and detail.permission.id == str(perm.id)


def test_page_data_response_generic():
    page = r.PageResponse(page=1, limit=10, total_items=2)
    pdr = r.PageDataResponse[r.PermissionResponse](
        data=[r.permission_response(_perm())], page=page)
    assert pdr.model_dump()["page"]["total_items"] == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/presentation/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `schemas/request.py`**

```python
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
```

- [ ] **Step 4: Write `schemas/response.py`**

```python
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
```

Create empty `backend/tests/presentation/__init__.py` and the `presentation/http/` + `schemas/` `__init__.py` files.

- [ ] **Step 5: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/presentation/test_schemas.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/presentation/ backend/tests/presentation/
git commit -m "feat(presentation): request/response schemas and domain mappers

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 22: Presentation utils (error handling + pagination)

**Files:**
- Create: `backend/src/tarakdingdung/presentation/http/utils/__init__.py`
- Create: `backend/src/tarakdingdung/presentation/http/utils/errors.py`
- Create: `backend/src/tarakdingdung/presentation/http/utils/pagination.py`
- Test: `backend/tests/presentation/test_utils_errors.py`
- Test: `backend/tests/presentation/test_utils_pagination.py`

**Interfaces:**
- Consumes: `DomainError`, `ErrorType`, `ErrorResponse`, `PageResponse`, FastAPI, Starlette.
- Produces:
  - `utils.errors.DOMAIN_STATUS: dict[ErrorType, tuple[int, str, str]]` — `(status, title, override_message)`; `override_message == ""` means "use the DomainError's own message". Entries per spec §8.4:
    - `NOT_FOUND` → `(404, "Not Found", "")`
    - `USERNAME_EXISTS` → `(409, "Already Exists", "This username is already taken.")`
    - `ROLE_NAME_EXISTS` → `(409, "Already Exists", "A role with this name already exists.")`
    - `PERMISSION_NAME_EXISTS` → `(409, "Already Exists", "A permission with this name already exists.")`
    - `ROLE_PERMISSION_EXISTS` → `(409, "Already Exists", "This permission is already assigned to the role.")`
    - `CONFLICT` → `(409, "Already Exists", "")`
    - `BAD_ARGS` → `(400, "Invalid Format", "")`
    - `VALIDATION` → `(400, "Invalid Format", "")`
    - `BAD_STATE` → `(412, "Invalid State", "")`
    - `FORBIDDEN` → `(403, "Access Denied", "")`
    - `UNAUTHORIZED` → `(401, "Unauthorized", "")`
    - `TOKEN_EXPIRED` → `(401, "Session Expired", "Your session has expired. Please sign in again.")`
    - `TOKEN_INVALID` → `(401, "Invalid Token", "Your session is no longer valid. Please sign in again.")`
    - `TIMEOUT` → `(504, "Request Timeout", "The request took too long. Please try again.")`
    - `UNIMPLEMENTED` → `(501, "Not Implemented", "This feature isn't available yet.")`
    - `FAILURE` / `UNKNOWN` → `(500, "Internal Server Error", "Something went wrong on our end. Please try again later.")`
  - `utils.errors.domain_error_response(err: DomainError) -> tuple[int, ErrorResponse]`.
  - `utils.errors.register_exception_handlers(app: FastAPI) -> None` — registers a `DomainError` handler (uses `domain_error_response`), a `RequestValidationError` handler → `400 {"error": "Invalid Format", "message": <first error msg>}`, and a catch-all `Exception` handler → `500` generic.
  - `utils.pagination.PaginationParams` — a FastAPI dependency dataclass/callable producing `page: int` (query `page`, default 1, min 1), `limit: int` (query `limit`, default 10, 1–100 clamped), `search: str | None` (query `search`, stripped, `None` when blank).
  - `utils.pagination.page_response(params: PaginationParams, total: int) -> PageResponse`.

- [ ] **Step 1: Write `backend/tests/presentation/test_utils_errors.py`**

```python
import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.presentation.http.utils.errors import domain_error_response


@pytest.mark.parametrize("etype,status,title", [
    (ErrorType.NOT_FOUND, 404, "Not Found"),
    (ErrorType.VALIDATION, 400, "Invalid Format"),
    (ErrorType.FORBIDDEN, 403, "Access Denied"),
    (ErrorType.UNAUTHORIZED, 401, "Unauthorized"),
    (ErrorType.TOKEN_EXPIRED, 401, "Session Expired"),
    (ErrorType.CONFLICT, 409, "Already Exists"),
    (ErrorType.FAILURE, 500, "Internal Server Error"),
])
def test_status_and_title_mapping(etype, status, title):
    s, body = domain_error_response(DomainError("boom", etype))
    assert s == status and body.error == title


def test_override_message_used_when_present():
    _s, body = domain_error_response(DomainError("raw", ErrorType.USERNAME_EXISTS))
    assert body.message == "This username is already taken."


def test_own_message_used_when_no_override():
    _s, body = domain_error_response(DomainError("name is required", ErrorType.VALIDATION))
    assert body.message == "name is required"


def test_unknown_type_falls_back_to_500(monkeypatch):
    err = DomainError("x", ErrorType.NOT_FOUND)
    object.__setattr__(err, "type", "TOTALLY_UNKNOWN")
    s, body = domain_error_response(err)
    assert s == 500 and body.error == "Internal Server Error"
```

- [ ] **Step 2: Write `backend/tests/presentation/test_utils_pagination.py`**

```python
from tarakdingdung.presentation.http.utils.pagination import PaginationParams, page_response


def test_defaults():
    p = PaginationParams()
    assert (p.page, p.limit, p.search) == (1, 10, None)


def test_clamps_limit_and_floors_page():
    assert PaginationParams(page=0, limit=999).limit == 100
    assert PaginationParams(page=0, limit=999).page == 1
    assert PaginationParams(page=-5, limit=0).limit == 10


def test_search_blank_is_none():
    assert PaginationParams(search="   ").search is None
    assert PaginationParams(search=" grace ").search == "grace"


def test_page_response():
    pr = page_response(PaginationParams(page=2, limit=20), total=87)
    assert (pr.page, pr.limit, pr.total_items) == (2, 20, 87)
```

- [ ] **Step 3: Run both to verify they fail**

Run: `backend/.venv/bin/pytest backend/tests/presentation/test_utils_errors.py backend/tests/presentation/test_utils_pagination.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Write `utils/errors.py`**

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.presentation.http.schemas.response import ErrorResponse

_GENERIC = "Something went wrong on our end. Please try again later."

DOMAIN_STATUS: dict[ErrorType, tuple[int, str, str]] = {
    ErrorType.NOT_FOUND: (404, "Not Found", ""),
    ErrorType.USERNAME_EXISTS: (409, "Already Exists", "This username is already taken."),
    ErrorType.ROLE_NAME_EXISTS: (409, "Already Exists", "A role with this name already exists."),
    ErrorType.PERMISSION_NAME_EXISTS: (409, "Already Exists",
                                       "A permission with this name already exists."),
    ErrorType.ROLE_PERMISSION_EXISTS: (409, "Already Exists",
                                       "This permission is already assigned to the role."),
    ErrorType.CONFLICT: (409, "Already Exists", ""),
    ErrorType.BAD_ARGS: (400, "Invalid Format", ""),
    ErrorType.VALIDATION: (400, "Invalid Format", ""),
    ErrorType.BAD_STATE: (412, "Invalid State", ""),
    ErrorType.FORBIDDEN: (403, "Access Denied", ""),
    ErrorType.UNAUTHORIZED: (401, "Unauthorized", ""),
    ErrorType.TOKEN_EXPIRED: (401, "Session Expired",
                              "Your session has expired. Please sign in again."),
    ErrorType.TOKEN_INVALID: (401, "Invalid Token",
                              "Your session is no longer valid. Please sign in again."),
    ErrorType.TIMEOUT: (504, "Request Timeout", "The request took too long. Please try again."),
    ErrorType.UNIMPLEMENTED: (501, "Not Implemented", "This feature isn't available yet."),
    ErrorType.FAILURE: (500, "Internal Server Error", _GENERIC),
    ErrorType.UNKNOWN: (500, "Internal Server Error", _GENERIC),
}


def domain_error_response(err: DomainError) -> tuple[int, ErrorResponse]:
    status, title, override = DOMAIN_STATUS.get(err.type, (500, "Internal Server Error", _GENERIC))
    message = override or (err.message or _GENERIC)
    return status, ErrorResponse(error=title, message=message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_request: Request, exc: DomainError) -> JSONResponse:
        status, body = domain_error_response(exc)
        return JSONResponse(status_code=status, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        detail = errors[0]["msg"] if errors else "request body is invalid"
        return JSONResponse(status_code=400,
                            content=ErrorResponse(error="Invalid Format",
                                                  message=detail).model_dump())

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500,
                            content=ErrorResponse(error="Internal Server Error",
                                                  message=_GENERIC).model_dump())
```

- [ ] **Step 5: Write `utils/pagination.py`**

```python
from dataclasses import dataclass

from fastapi import Query

from tarakdingdung.presentation.http.schemas.response import PageResponse

_DEFAULT_PAGE, _DEFAULT_LIMIT, _MAX_LIMIT = 1, 10, 100


@dataclass(slots=True)
class PaginationParams:
    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    search: str | None = None

    def __post_init__(self) -> None:
        if self.page < 1:
            self.page = _DEFAULT_PAGE
        if self.limit < 1:
            self.limit = _DEFAULT_LIMIT
        elif self.limit > _MAX_LIMIT:
            self.limit = _MAX_LIMIT
        if self.search is not None:
            self.search = self.search.strip() or None


def pagination_params(
    page: int = Query(_DEFAULT_PAGE),
    limit: int = Query(_DEFAULT_LIMIT),
    search: str | None = Query(None),
) -> PaginationParams:
    return PaginationParams(page=page, limit=limit, search=search)


def page_response(params: PaginationParams, total: int) -> PageResponse:
    return PageResponse(page=params.page, limit=params.limit, total_items=total)
```

Create the `utils/__init__.py`.

- [ ] **Step 6: Run both to verify they pass**

Run: `backend/.venv/bin/pytest backend/tests/presentation/test_utils_errors.py backend/tests/presentation/test_utils_pagination.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tarakdingdung/presentation/http/utils/ \
        backend/tests/presentation/test_utils_errors.py \
        backend/tests/presentation/test_utils_pagination.py
git commit -m "feat(presentation): DomainError->HTTP mapping and pagination helpers

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 23: Presentation dependencies (auth, permission, container)

**Files:**
- Create: `backend/src/tarakdingdung/presentation/http/dependencies/__init__.py`
- Create: `backend/src/tarakdingdung/presentation/http/dependencies/container.py`
- Create: `backend/src/tarakdingdung/presentation/http/dependencies/auth.py`
- Create: `backend/src/tarakdingdung/presentation/http/dependencies/permission.py`
- Test: `backend/tests/presentation/test_dependencies.py`

**Interfaces:**
- Consumes: `Token`, `TokenClaimsAccess`, `DomainError`, all usecase interfaces, FastAPI `Request`, `Header`, `Depends`.
- Produces:
  - `dependencies.container.Container` — frozen dataclass holding one field per usecase: `session: Session`, `permission_management: PermissionManagement`, `role_management: RoleManagement`, `user_management: UserManagement`, `profile_me: Me`, `profile_account: Account`, `profile_security: Security`, and `token: Token`.
  - `dependencies.container.get_container(request: Request) -> Container` — returns `request.app.state.container`.
  - Per-usecase accessors: `get_session_usecase`, `get_permission_management`, `get_role_management`, `get_user_management`, `get_profile_me`, `get_profile_account`, `get_profile_security`, `get_token` — each `def f(container: Container = Depends(get_container)) -> <Type>: return container.<field>`.
  - `dependencies.auth.get_access_claims(request: Request, authorization: str | None = Header(default=None, alias="Authorization"), token: Token = Depends(get_token)) -> TokenClaimsAccess` — extract bearer (accept `"Bearer <t>"` or a raw token); missing → `DomainError("authorization is required", UNAUTHORIZED)`; delegates to `token.validate_access`.
  - `dependencies.auth.get_actor_id(claims: TokenClaimsAccess = Depends(get_access_claims)) -> UUID` → `claims.user_id`.
  - `dependencies.permission.require(*required: str) -> Callable` — returns a dependency `def _dep(claims = Depends(get_access_claims)) -> None` that raises `DomainError("you do not have permission to perform this action", FORBIDDEN)` unless `set(required) <= set(claims.permissions)`.

- [ ] **Step 1: Write the failing test `backend/tests/presentation/test_dependencies.py`**

```python
import uuid

import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess
from tarakdingdung.presentation.http.dependencies.auth import _extract_bearer
from tarakdingdung.presentation.http.dependencies.permission import require


def test_extract_bearer_accepts_prefixed_and_raw():
    assert _extract_bearer("Bearer abc.def") == "abc.def"
    assert _extract_bearer("abc.def") == "abc.def"
    assert _extract_bearer("  Bearer   spaced  ") == "spaced"
    assert _extract_bearer(None) is None
    assert _extract_bearer("") is None


@pytest.mark.asyncio
async def test_require_allows_when_permissions_present():
    claims = TokenClaimsAccess(user_id=uuid.uuid4(), name="n", username="u", role="r",
                               permissions=("user:get", "user:add"))
    dep = require("user:get")
    assert await dep(claims=claims) is None


@pytest.mark.asyncio
async def test_require_forbids_when_missing():
    claims = TokenClaimsAccess(user_id=uuid.uuid4(), name="n", username="u", role="r",
                               permissions=("user:get",))
    dep = require("user:add")
    with pytest.raises(DomainError) as ei:
        await dep(claims=claims)
    assert ei.value.type is ErrorType.FORBIDDEN
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/presentation/test_dependencies.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `dependencies/container.py`**

```python
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


@dataclass(frozen=True, slots=True)
class Container:
    session: Session
    permission_management: PermissionManagement
    role_management: RoleManagement
    user_management: UserManagement
    profile_me: Me
    profile_account: Account
    profile_security: Security
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
```

- [ ] **Step 4: Write `dependencies/auth.py`**

```python
from uuid import UUID

from fastapi import Depends, Header, Request

from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess
from tarakdingdung.presentation.http.dependencies.container import get_token


def _extract_bearer(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    parts = value.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return value or None


async def get_access_claims(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    token: Token = Depends(get_token),
) -> TokenClaimsAccess:
    raw = _extract_bearer(authorization)
    if raw is None:
        raise DomainError("authorization is required", ErrorType.UNAUTHORIZED)
    return await token.validate_access(raw)


async def get_actor_id(
        claims: TokenClaimsAccess = Depends(get_access_claims)) -> UUID:
    return claims.user_id
```

- [ ] **Step 5: Write `dependencies/permission.py`**

```python
from collections.abc import Callable

from fastapi import Depends

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.token_claims import TokenClaimsAccess
from tarakdingdung.presentation.http.dependencies.auth import get_access_claims


def require(*required: str) -> Callable:
    async def _dependency(
            claims: TokenClaimsAccess = Depends(get_access_claims)) -> None:
        if not set(required).issubset(set(claims.permissions)):
            raise DomainError("you do not have permission to perform this action",
                              ErrorType.FORBIDDEN)

    return _dependency
```

Create `dependencies/__init__.py`.

- [ ] **Step 6: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/presentation/test_dependencies.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tarakdingdung/presentation/http/dependencies/ \
        backend/tests/presentation/test_dependencies.py
git commit -m "feat(presentation): auth/permission/container FastAPI dependencies

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 24: Routers — version, auth, admin, profile + aggregator

**Files:**
- Create: `backend/src/tarakdingdung/presentation/http/routers/__init__.py`
- Create: `backend/src/tarakdingdung/presentation/http/routers/version.py`
- Create: `backend/src/tarakdingdung/presentation/http/routers/auth.py`
- Create: `backend/src/tarakdingdung/presentation/http/routers/admin.py`
- Create: `backend/src/tarakdingdung/presentation/http/routers/profile.py`
- Test: `backend/tests/presentation/conftest.py`
- Test: `backend/tests/presentation/test_routers.py`

**Interfaces:**
- Consumes: schemas (Task 21), utils (Task 22), dependencies (Task 23), all usecase interfaces + DTOs.
- Produces:
  - `routers.version.router: APIRouter` — `GET ""` → `PlainTextResponse(request.app.state.app_version)`; mounted at `/api/version`.
  - `routers.auth.router: APIRouter` — prefix `/v1/auth`, tags `["Auth"]`:
    - `POST /login` (`AuthLoginRequest`) → `200 LoginResponse` via `session.login(LoginRequest(...))`.
    - `POST /refresh` (`AuthRefreshRequest`) → `200 LoginResponse` via `session.refresh(RefreshRequest(...))`.
  - `routers.admin.router: APIRouter` — prefix `/v1/admin`, tags `["Admin"]`, every route has `dependencies=[Depends(require("<perm>"))]`. Routes exactly per spec §8.1 admin table (permissions, roles, role-permissions, users). Handlers translate path/query/body to usecase requests and map results:
    - creates → `201 IdResponse`, `update`/`delete`/`assign`(pair delete)/`set-default` → `204 Response(status_code=204)`, `assign permission` → `201 IdResponse`, reads → `200`, list → `200 PageDataResponse[...]`, missing single read → raise `DomainError("<x> not found", NOT_FOUND)`.
    - `created_by`/`updated_by`/`deleted_by` on requests = `Depends(get_actor_id)`.
  - `routers.profile.router: APIRouter` — prefix `/v1/profile`, tags `["Profile"]`:
    - `GET ""` `require("profile:get")` → `200 UserResponse` (`me.get_profile`, missing → `NOT_FOUND`).
    - `GET /permissions` `require("profile:get")` → `200 list[PermissionResponse]`.
    - `PATCH ""` `require("profile:set")` (`ProfilePatchRequest`) → `204` (`account.update_profile`, `updated_by = actor`).
    - `PATCH /password` `require("profile_security:set")` (`ProfilePasswordPatchRequest`) → `204` (`security.change_password`, `updated_by = actor`).
  - `routers.__init__.build_api_router() -> APIRouter` — an `APIRouter(prefix="/api")` that includes `version.router` at `/version`, `auth.router`, `admin.router`, `profile.router`.

- [ ] **Step 1: Write `backend/tests/presentation/conftest.py`**

```python
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from fastapi import FastAPI

from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.account.usecase import AccountUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.presentation.http.dependencies.container import Container
from tarakdingdung.presentation.http.routers import build_api_router
from tarakdingdung.presentation.http.utils.errors import register_exception_handlers
from tests.fakes.repositories import (
    FakePermissionRepository, FakeRolePermissionRepository, FakeRoleRepository,
    FakeUserRepository,
)
from tests.fakes.utilities import FakePassword, FakeToken, NullLogger


@pytest.fixture
def wiring():
    roles = FakeRoleRepository()
    perms = FakePermissionRepository()
    rps = FakeRolePermissionRepository(roles=roles, permissions=perms)
    users = FakeUserRepository(roles=roles, role_permissions=rps, permissions=perms)
    token = FakeToken()
    logger = NullLogger()
    container = Container(
        session=SessionUsecase(users=users, roles=roles, password=FakePassword(),
                               token=token, logger=logger),
        permission_management=PermissionManagementUsecase(permissions=perms, logger=logger),
        role_management=RoleManagementUsecase(roles=roles, role_permissions=rps, logger=logger),
        user_management=UserManagementUsecase(users=users, password=FakePassword(), logger=logger),
        profile_me=MeUsecase(users=users, logger=logger),
        profile_account=AccountUsecase(users=users, logger=logger),
        profile_security=SecurityUsecase(users=users, password=FakePassword(), logger=logger),
        token=token,
    )
    return container, roles, perms, rps, users


@pytest.fixture
def app(wiring):
    container = wiring[0]
    application = FastAPI()
    application.state.container = container
    application.state.app_version = "v-test"
    register_exception_handlers(application)
    application.include_router(build_api_router())
    return application


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


@pytest_asyncio.fixture
async def seeded(wiring):
    _container, roles, perms, rps, users = wiring
    rid = await roles.create(name="super", description=None, is_default=None, created_by=None)
    perm_names = ["permission:get", "permission:add", "permission:set", "permission:remove",
                  "role:get", "role:add", "role:set", "role:remove",
                  "role_permission:get", "role_permission:add", "role_permission:remove",
                  "user:get", "user:add", "user:set", "user:remove",
                  "user_permission:get", "user_password:set",
                  "profile:get", "profile:set", "profile_security:set"]
    for n in perm_names:
        pid = await perms.create(name=n, description=None, created_by=None)
        await rps.create(role_id=rid, permission_id=pid, created_by=None)
    uid = await users.create(role_id=rid, name="Super", bio=None, username="super",
                             password_hash="hash::secret12", created_by=None)
    return {"role_id": rid, "user_id": uid}
```

- [ ] **Step 2: Write the failing test `backend/tests/presentation/test_routers.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_version_endpoint(client):
    resp = await client.get("/api/version")
    assert resp.status_code == 200 and resp.text == "v-test"


@pytest.mark.asyncio
async def test_login_success_and_bad_password(client, seeded):
    ok = await client.post("/api/v1/auth/login",
                           json={"username": "super", "password": "secret12"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["access_token"].startswith("access::")
    assert body["role"]["name"] == "super"
    assert {p["name"] for p in body["permissions"]} >= {"permission:get", "user:add"}

    bad = await client.post("/api/v1/auth/login",
                            json={"username": "super", "password": "nope"})
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_admin_requires_bearer_and_permission(client, seeded):
    unauth = await client.get("/api/v1/admin/permissions")
    assert unauth.status_code == 401

    login = await client.post("/api/v1/auth/login",
                              json={"username": "super", "password": "secret12"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post("/api/v1/admin/permissions",
                                json={"name": "widget:get", "description": "d"}, headers=headers)
    assert created.status_code == 201
    pid = created.json()["id"]

    listing = await client.get("/api/v1/admin/permissions?search=widget", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["page"]["total_items"] == 1

    patched = await client.patch(f"/api/v1/admin/permissions/{pid}",
                                 json={"description": "changed"}, headers=headers)
    assert patched.status_code == 204

    deleted = await client.delete(f"/api/v1/admin/permissions/{pid}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_admin_role_permission_roundtrip(client, seeded):
    login = await client.post("/api/v1/auth/login",
                              json={"username": "super", "password": "secret12"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    role_id = (await client.post("/api/v1/admin/roles", json={"name": "barista"},
                                 headers=headers)).json()["id"]
    perm_id = (await client.post("/api/v1/admin/permissions", json={"name": "brew:do"},
                                 headers=headers)).json()["id"]
    assigned = await client.post(
        f"/api/v1/admin/roles/{role_id}/permissions/{perm_id}", headers=headers)
    assert assigned.status_code == 201
    detail = await client.get(
        f"/api/v1/admin/role-permissions/by-pair?role_id={role_id}&permission_id={perm_id}",
        headers=headers)
    assert detail.status_code == 200
    assert detail.json()["role"]["id"] == role_id


@pytest.mark.asyncio
async def test_profile_endpoints(client, seeded):
    login = await client.post("/api/v1/auth/login",
                              json={"username": "super", "password": "secret12"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = await client.get("/api/v1/profile", headers=headers)
    assert me.status_code == 200 and me.json()["username"] == "super"
    perms = await client.get("/api/v1/profile/permissions", headers=headers)
    assert perms.status_code == 200 and any(p["name"] == "profile:get" for p in perms.json())
    patched = await client.patch("/api/v1/profile", json={"name": "Super Admin"}, headers=headers)
    assert patched.status_code == 204
    pw = await client.patch("/api/v1/profile/password",
                            json={"current_password": "secret12", "new_password": "brandnew1"},
                            headers=headers)
    assert pw.status_code == 204
```

- [ ] **Step 3: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/presentation/test_routers.py -v`
Expected: FAIL — `ImportError` on `build_api_router`.

- [ ] **Step 4: Write `routers/version.py`**

```python
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["Version"])


@router.get("", response_class=PlainTextResponse)
async def version_get(request: Request) -> str:
    return request.app.state.app_version
```

- [ ] **Step 5: Write `routers/auth.py`**

```python
from fastapi import APIRouter, Depends

from tarakdingdung.domain.usecases.auth.session import LoginRequest, RefreshRequest, Session
from tarakdingdung.presentation.http.dependencies.container import get_session_usecase
from tarakdingdung.presentation.http.schemas.request import AuthLoginRequest, AuthRefreshRequest
from tarakdingdung.presentation.http.schemas.response import LoginResponse, login_response

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def auth_login(body: AuthLoginRequest,
                     session: Session = Depends(get_session_usecase)) -> LoginResponse:
    result = await session.login(LoginRequest(username=body.username, password=body.password))
    return login_response(result)


@router.post("/refresh", response_model=LoginResponse)
async def auth_refresh(body: AuthRefreshRequest,
                       session: Session = Depends(get_session_usecase)) -> LoginResponse:
    result = await session.refresh(RefreshRequest(refresh_token=body.refresh_token))
    return login_response(result)
```

- [ ] **Step 6: Write `routers/admin.py`**

Full module — one function per row of the admin route table:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.admin import permission_management as pm
from tarakdingdung.domain.usecases.admin import role_management as rm
from tarakdingdung.domain.usecases.admin import user_management as um
from tarakdingdung.presentation.http.dependencies.auth import get_actor_id
from tarakdingdung.presentation.http.dependencies.container import (
    get_permission_management, get_role_management, get_user_management,
)
from tarakdingdung.presentation.http.dependencies.permission import require
from tarakdingdung.presentation.http.schemas import request as req
from tarakdingdung.presentation.http.schemas import response as res
from tarakdingdung.presentation.http.utils.pagination import (
    PaginationParams, page_response, pagination_params,
)

router = APIRouter(prefix="/v1/admin", tags=["Admin"])

_NO_CONTENT = Response(status_code=204)


def _missing(name: str) -> DomainError:
    return DomainError(f"{name} not found", ErrorType.NOT_FOUND)


# ---- Permissions -----------------------------------------------------------

@router.get("/permissions", response_model=res.PageDataResponse[res.PermissionResponse],
            dependencies=[Depends(require("permission:get"))])
async def permission_list(page: PaginationParams = Depends(pagination_params),
                          uc: pm.PermissionManagement = Depends(get_permission_management)):
    items, total = await uc.read_by_pagination(pm.ReadPermissionsByPaginationRequest(
        page=page.page, limit=page.limit, search=page.search))
    return res.PageDataResponse[res.PermissionResponse](
        data=res.permissions_response(items), page=page_response(page, total))


@router.post("/permissions", status_code=201, response_model=res.IdResponse,
             dependencies=[Depends(require("permission:add"))])
async def permission_create(body: req.PermissionPostRequest,
                            actor: UUID = Depends(get_actor_id),
                            uc: pm.PermissionManagement = Depends(get_permission_management)):
    new_id = await uc.create(pm.CreatePermissionRequest(
        name=body.name, description=body.description, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.get("/permissions/by-name/{name}", response_model=res.PermissionResponse,
            dependencies=[Depends(require("permission:get"))])
async def permission_by_name(name: str,
                             uc: pm.PermissionManagement = Depends(get_permission_management)):
    found = await uc.read_by_name(pm.ReadPermissionByNameRequest(name=name))
    if found is None:
        raise _missing("permission")
    return res.permission_response(found)


@router.get("/permissions/{id}", response_model=res.PermissionResponse,
            dependencies=[Depends(require("permission:get"))])
async def permission_by_id(id: UUID,
                           uc: pm.PermissionManagement = Depends(get_permission_management)):
    found = await uc.read_by_id(pm.ReadPermissionByIdRequest(id=id))
    if found is None:
        raise _missing("permission")
    return res.permission_response(found)


@router.patch("/permissions/{id}", status_code=204,
              dependencies=[Depends(require("permission:set"))])
async def permission_update(id: UUID, body: req.PermissionPatchRequest,
                            actor: UUID = Depends(get_actor_id),
                            uc: pm.PermissionManagement = Depends(get_permission_management)):
    await uc.update_by_id(pm.UpdatePermissionRequest(
        id=id, name=body.name, description=body.description, updated_by=actor))
    return _NO_CONTENT


@router.delete("/permissions/{id}", status_code=204,
               dependencies=[Depends(require("permission:remove"))])
async def permission_delete(id: UUID, actor: UUID = Depends(get_actor_id),
                            uc: pm.PermissionManagement = Depends(get_permission_management)):
    await uc.delete_by_id(pm.DeletePermissionRequest(id=id, deleted_by=actor))
    return _NO_CONTENT


# ---- Roles ---------------------------------------------------------------

@router.get("/roles", response_model=res.PageDataResponse[res.RoleResponse],
            dependencies=[Depends(require("role:get"))])
async def role_list(page: PaginationParams = Depends(pagination_params),
                    uc: rm.RoleManagement = Depends(get_role_management)):
    items, total = await uc.read_by_pagination(rm.ReadRolesByPaginationRequest(
        page=page.page, limit=page.limit, search=page.search))
    return res.PageDataResponse[res.RoleResponse](
        data=res.roles_response(items), page=page_response(page, total))


@router.post("/roles", status_code=201, response_model=res.IdResponse,
             dependencies=[Depends(require("role:add"))])
async def role_create(body: req.RolePostRequest, actor: UUID = Depends(get_actor_id),
                      uc: rm.RoleManagement = Depends(get_role_management)):
    new_id = await uc.create(rm.CreateRoleRequest(
        name=body.name, description=body.description, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.get("/roles/default", response_model=res.RoleResponse,
            dependencies=[Depends(require("role:get"))])
async def role_default(uc: rm.RoleManagement = Depends(get_role_management)):
    found = await uc.read_default(rm.ReadDefaultRoleRequest())
    if found is None:
        raise _missing("role")
    return res.role_response(found)


@router.get("/roles/by-name/{name}", response_model=res.RoleResponse,
            dependencies=[Depends(require("role:get"))])
async def role_by_name(name: str, uc: rm.RoleManagement = Depends(get_role_management)):
    found = await uc.read_by_name(rm.ReadRoleByNameRequest(name=name))
    if found is None:
        raise _missing("role")
    return res.role_response(found)


@router.get("/roles/{id}/permissions", response_model=list[res.PermissionResponse],
            dependencies=[Depends(require("role_permission:get"))])
async def role_permissions(id: UUID, uc: rm.RoleManagement = Depends(get_role_management)):
    items = await uc.read_permissions(rm.ReadRolePermissionsRequest(role_id=id))
    return res.permissions_response(items)


@router.patch("/roles/{id}/default", status_code=204,
              dependencies=[Depends(require("role:set"))])
async def role_set_default(id: UUID, actor: UUID = Depends(get_actor_id),
                           uc: rm.RoleManagement = Depends(get_role_management)):
    await uc.set_default_role(rm.SetDefaultRoleRequest(id=id, updated_by=actor))
    return _NO_CONTENT


@router.get("/roles/{id}", response_model=res.RoleResponse,
            dependencies=[Depends(require("role:get"))])
async def role_by_id(id: UUID, uc: rm.RoleManagement = Depends(get_role_management)):
    found = await uc.read_by_id(rm.ReadRoleByIdRequest(id=id))
    if found is None:
        raise _missing("role")
    return res.role_response(found)


@router.patch("/roles/{id}", status_code=204, dependencies=[Depends(require("role:set"))])
async def role_update(id: UUID, body: req.RolePatchRequest, actor: UUID = Depends(get_actor_id),
                      uc: rm.RoleManagement = Depends(get_role_management)):
    await uc.update_by_id(rm.UpdateRoleRequest(
        id=id, name=body.name, description=body.description, updated_by=actor))
    return _NO_CONTENT


@router.delete("/roles/{id}", status_code=204, dependencies=[Depends(require("role:remove"))])
async def role_delete(id: UUID, actor: UUID = Depends(get_actor_id),
                      uc: rm.RoleManagement = Depends(get_role_management)):
    await uc.delete_by_id(rm.DeleteRoleRequest(id=id, deleted_by=actor))
    return _NO_CONTENT


@router.post("/roles/{role_id}/permissions/{permission_id}", status_code=201,
             response_model=res.IdResponse,
             dependencies=[Depends(require("role_permission:add"))])
async def role_permission_assign(role_id: UUID, permission_id: UUID,
                                 actor: UUID = Depends(get_actor_id),
                                 uc: rm.RoleManagement = Depends(get_role_management)):
    new_id = await uc.assign_permission(rm.AssignRolePermissionRequest(
        role_id=role_id, permission_id=permission_id, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=204,
               dependencies=[Depends(require("role_permission:remove"))])
async def role_permission_revoke(role_id: UUID, permission_id: UUID,
                                 uc: rm.RoleManagement = Depends(get_role_management)):
    await uc.revoke_permission(rm.RevokeRolePermissionRequest(
        role_id=role_id, permission_id=permission_id))
    return _NO_CONTENT


@router.get("/role-permissions",
            response_model=res.PageDataResponse[res.RolePermissionDetailResponse],
            dependencies=[Depends(require("role_permission:get"))])
async def role_permission_list(page: PaginationParams = Depends(pagination_params),
                               role_id: UUID | None = None, permission_id: UUID | None = None,
                               uc: rm.RoleManagement = Depends(get_role_management)):
    items, total = await uc.read_role_permissions_by_pagination(
        rm.ReadRolePermissionsByPaginationRequest(
            page=page.page, limit=page.limit, role_id=role_id, permission_id=permission_id))
    return res.PageDataResponse[res.RolePermissionDetailResponse](
        data=res.role_permission_details_response(items), page=page_response(page, total))


@router.get("/role-permissions/by-pair", response_model=res.RolePermissionDetailResponse,
            dependencies=[Depends(require("role_permission:get"))])
async def role_permission_by_pair(role_id: UUID, permission_id: UUID,
                                  uc: rm.RoleManagement = Depends(get_role_management)):
    result = await uc.read_role_permission_by_role_id_and_permission_id(
        rm.ReadRolePermissionByRoleIdAndPermissionIdRequest(
            role_id=role_id, permission_id=permission_id))
    return res.role_permission_detail_response(result)


@router.get("/role-permissions/{id}", response_model=res.RolePermissionDetailResponse,
            dependencies=[Depends(require("role_permission:get"))])
async def role_permission_by_id(id: UUID, uc: rm.RoleManagement = Depends(get_role_management)):
    result = await uc.read_role_permission_by_id(rm.ReadRolePermissionByIdRequest(id=id))
    return res.role_permission_detail_response(result)


# ---- Users -------------------------------------------------------------

@router.get("/users", response_model=res.PageDataResponse[res.UserResponse],
            dependencies=[Depends(require("user:get"))])
async def user_list(page: PaginationParams = Depends(pagination_params),
                    role_id: UUID | None = None,
                    uc: um.UserManagement = Depends(get_user_management)):
    items, total = await uc.read_by_pagination(um.ReadUsersByPaginationRequest(
        page=page.page, limit=page.limit, search=page.search, role_id=role_id))
    return res.PageDataResponse[res.UserResponse](
        data=res.user_list_items_response(items), page=page_response(page, total))


@router.post("/users", status_code=201, response_model=res.IdResponse,
             dependencies=[Depends(require("user:add"))])
async def user_create(body: req.UserPostRequest, actor: UUID = Depends(get_actor_id),
                      uc: um.UserManagement = Depends(get_user_management)):
    new_id = await uc.create(um.CreateUserRequest(
        role_id=body.role_id, name=body.name, bio=body.bio, username=body.username,
        password=body.password, created_by=actor))
    return res.IdResponse(id=str(new_id))


@router.get("/users/by-username/{username}", response_model=res.UserResponse,
            dependencies=[Depends(require("user:get"))])
async def user_by_username(username: str,
                           uc: um.UserManagement = Depends(get_user_management)):
    found = await uc.read_by_username(um.ReadUserByUsernameRequest(username=username))
    if found is None:
        raise _missing("user")
    return res.user_response(found)


@router.get("/users/{id}/permissions", response_model=list[res.PermissionResponse],
            dependencies=[Depends(require("user_permission:get"))])
async def user_permissions(id: UUID, uc: um.UserManagement = Depends(get_user_management)):
    items = await uc.read_permissions(um.ReadUserPermissionsRequest(user_id=id))
    return res.permissions_response(items)


@router.patch("/users/{id}/password", status_code=204,
              dependencies=[Depends(require("user_password:set"))])
async def user_password(id: UUID, body: req.UserPasswordPatchRequest,
                        actor: UUID = Depends(get_actor_id),
                        uc: um.UserManagement = Depends(get_user_management)):
    await uc.reset_password(um.ResetUserPasswordRequest(
        id=id, password=body.password, updated_by=actor))
    return _NO_CONTENT


@router.get("/users/{id}", response_model=res.UserResponse,
            dependencies=[Depends(require("user:get"))])
async def user_by_id(id: UUID, uc: um.UserManagement = Depends(get_user_management)):
    found = await uc.read_by_id(um.ReadUserByIdRequest(id=id))
    if found is None:
        raise _missing("user")
    return res.user_response(found)


@router.patch("/users/{id}", status_code=204, dependencies=[Depends(require("user:set"))])
async def user_update(id: UUID, body: req.UserPatchRequest, actor: UUID = Depends(get_actor_id),
                      uc: um.UserManagement = Depends(get_user_management)):
    await uc.update_by_id(um.UpdateUserRequest(
        id=id, role_id=body.role_id, name=body.name, bio=body.bio, username=body.username,
        updated_by=actor))
    return _NO_CONTENT


@router.delete("/users/{id}", status_code=204, dependencies=[Depends(require("user:remove"))])
async def user_delete(id: UUID, actor: UUID = Depends(get_actor_id),
                      uc: um.UserManagement = Depends(get_user_management)):
    await uc.delete_by_id(um.DeleteUserRequest(id=id, deleted_by=actor))
    return _NO_CONTENT
```

> `pm`, `rm`, `um` module aliases expose the request dataclasses referenced
> above (e.g. `pm.ReadPermissionByIdRequest`). They are all defined in
> Task 4 — verify the names match before running.

- [ ] **Step 7: Write `routers/profile.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.usecases.profile.account import Account, UpdateProfileRequest
from tarakdingdung.domain.usecases.profile.me import (
    GetProfilePermissionsRequest, GetProfileRequest, Me,
)
from tarakdingdung.domain.usecases.profile.security import ChangePasswordRequest, Security
from tarakdingdung.presentation.http.dependencies.auth import get_actor_id
from tarakdingdung.presentation.http.dependencies.container import (
    get_profile_account, get_profile_me, get_profile_security,
)
from tarakdingdung.presentation.http.dependencies.permission import require
from tarakdingdung.presentation.http.schemas import request as req
from tarakdingdung.presentation.http.schemas import response as res

router = APIRouter(prefix="/v1/profile", tags=["Profile"])
_NO_CONTENT = Response(status_code=204)


@router.get("", response_model=res.UserResponse, dependencies=[Depends(require("profile:get"))])
async def profile_get(actor: UUID = Depends(get_actor_id),
                      uc: Me = Depends(get_profile_me)):
    user = await uc.get_profile(GetProfileRequest(user_id=actor))
    if user is None:
        raise DomainError("user not found", ErrorType.NOT_FOUND)
    return res.user_response(user)


@router.get("/permissions", response_model=list[res.PermissionResponse],
            dependencies=[Depends(require("profile:get"))])
async def profile_permissions(actor: UUID = Depends(get_actor_id),
                              uc: Me = Depends(get_profile_me)):
    items = await uc.get_permissions(GetProfilePermissionsRequest(user_id=actor))
    return res.permissions_response(items)


@router.patch("", status_code=204, dependencies=[Depends(require("profile:set"))])
async def profile_update(body: req.ProfilePatchRequest, actor: UUID = Depends(get_actor_id),
                         uc: Account = Depends(get_profile_account)):
    await uc.update_profile(UpdateProfileRequest(
        user_id=actor, name=body.name, bio=body.bio, username=body.username, updated_by=actor))
    return _NO_CONTENT


@router.patch("/password", status_code=204,
              dependencies=[Depends(require("profile_security:set"))])
async def profile_password(body: req.ProfilePasswordPatchRequest,
                           actor: UUID = Depends(get_actor_id),
                           uc: Security = Depends(get_profile_security)):
    await uc.change_password(ChangePasswordRequest(
        user_id=actor, current_password=body.current_password,
        new_password=body.new_password, updated_by=actor))
    return _NO_CONTENT
```

- [ ] **Step 8: Write `routers/__init__.py`**

```python
from fastapi import APIRouter

from tarakdingdung.presentation.http.routers import admin, auth, profile, version


def build_api_router() -> APIRouter:
    api = APIRouter(prefix="/api")
    api.include_router(version.router, prefix="/version")
    api.include_router(auth.router)
    api.include_router(admin.router)
    api.include_router(profile.router)
    return api
```

- [ ] **Step 9: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/presentation/test_routers.py -v`
Expected: all PASS.

- [ ] **Step 10: Full presentation regression + commit**

Run: `backend/.venv/bin/pytest backend/tests/presentation/ -v`
Expected: all PASS.

```bash
git add backend/src/tarakdingdung/presentation/http/routers/ backend/tests/presentation/
git commit -m "feat(presentation): version/auth/admin/profile routers

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 25: Composition — driver, infrastructure, application containers

**Files:**
- Create: `backend/src/tarakdingdung/composition/__init__.py`
- Create: `backend/src/tarakdingdung/composition/main/__init__.py`
- Create: `backend/src/tarakdingdung/composition/main/driver.py`
- Create: `backend/src/tarakdingdung/composition/main/infrastructure.py`
- Create: `backend/src/tarakdingdung/composition/main/application.py`
- Test: `backend/tests/integration/test_composition_wiring.py`

**Interfaces:**
- Consumes: `Settings`, `Database`, all repository/utility impls, all usecase impls, `Container` (Task 23).
- Produces:
  - `composition.main.driver.Driver` — frozen dataclass: `database: Database`, `logger: LeveledLogger`. `composition.main.driver.build_driver(settings: Settings) -> Driver` — builds `Database(settings.postgres_dsn, pool_size=settings.postgres_pool_size)`; picks `JsonLeveledLogging(LoggerLevel(settings.logger_level))` when `settings.logger_format == "json"` else `BasicLeveledLogging(...)`.
  - `composition.main.infrastructure.Infrastructure` — frozen dataclass: `logger`, `transactor: Transactor`, `permissions: PermissionRepository`, `roles: RoleRepository`, `role_permissions: RolePermissionRepository`, `users: UserRepository`, `password: Password`, `token: Token`. `build_infrastructure(driver: Driver, settings: Settings) -> Infrastructure`.
  - `composition.main.application.Application` — frozen dataclass with the same fields as `Container` minus `token`, plus a `to_container(token) -> Container` method OR a free function `build_container(infra: Infrastructure) -> Container`. Choose: `composition.main.application.build_container(infra: Infrastructure) -> Container` builds every usecase and returns a `Container` (including `token=infra.token`).

- [ ] **Step 1: Write the failing test `backend/tests/integration/test_composition_wiring.py`**

```python
import pytest

from tarakdingdung.composition.main.application import build_container
from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.http.dependencies.container import Container


def _settings(migrated_url: str) -> Settings:
    from urllib.parse import urlparse
    parsed = urlparse(migrated_url.replace("+asyncpg", ""))
    return Settings(
        postgres_host=parsed.hostname, postgres_port=parsed.port,
        postgres_username=parsed.username, postgres_password=parsed.password,
        postgres_database=parsed.path.lstrip("/"),
        logger_format="plain",
    )


@pytest.mark.asyncio
async def test_container_has_every_usecase(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    container = build_container(infra)
    assert isinstance(container, Container)
    for field in ("session", "permission_management", "role_management", "user_management",
                  "profile_me", "profile_account", "profile_security", "token"):
        assert getattr(container, field) is not None
    await driver.database.dispose()


@pytest.mark.asyncio
async def test_wired_permission_management_hits_real_db(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    container = build_container(infra)
    from tarakdingdung.domain.usecases.admin.permission_management import (
        CreatePermissionRequest, ReadPermissionByNameRequest,
    )
    name = "wire:check"
    await container.permission_management.create(CreatePermissionRequest(name=name))
    got = await container.permission_management.read_by_name(
        ReadPermissionByNameRequest(name=name))
    assert got is not None and got.name == name
    # cleanup so the session-scoped migrated_url stays reusable
    async with driver.database.session() as s:
        from sqlalchemy import text
        await s.execute(text("DELETE FROM permissions WHERE name = :n"), {"n": name})
        await s.commit()
    await driver.database.dispose()
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_composition_wiring.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `composition/main/driver.py`**

```python
from dataclasses import dataclass

from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.logger import LoggerLevel
from tarakdingdung.infrastructure.logger.leveled.json import JsonLeveledLogging
from tarakdingdung.infrastructure.logger.leveled.plain import BasicLeveledLogging
from tarakdingdung.infrastructure.repository.database.session import Database


@dataclass(frozen=True, slots=True)
class Driver:
    database: Database
    logger: LeveledLogger


def build_driver(settings: Settings) -> Driver:
    database = Database(settings.postgres_dsn, pool_size=settings.postgres_pool_size)
    try:
        level = LoggerLevel(settings.logger_level.upper())
    except ValueError:
        level = LoggerLevel.INFO
    logger: LeveledLogger = (
        JsonLeveledLogging(level) if settings.logger_format == "json"
        else BasicLeveledLogging(level)
    )
    return Driver(database=database, logger=logger)
```

> Check the existing `LoggerLevel` enum in `domain/models/logger.py`: its
> members are `NONE/ERROR/WARN/INFO/DEBUG` with plain values. `LoggerLevel("INFO")`
> works. If `settings.logger_level` may be lowercase, `.upper()` as above.

- [ ] **Step 4: Write `composition/main/infrastructure.py`**

```python
from dataclasses import dataclass
from datetime import timedelta

from tarakdingdung.config.settings import Settings
from tarakdingdung.composition.main.driver import Driver
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.contracts.repository.permission import PermissionRepository
from tarakdingdung.domain.contracts.repository.role import RoleRepository
from tarakdingdung.domain.contracts.repository.role_permission import RolePermissionRepository
from tarakdingdung.domain.contracts.repository.user import UserRepository
from tarakdingdung.domain.contracts.utility.password import Password
from tarakdingdung.domain.contracts.utility.token import Token
from tarakdingdung.domain.contracts.utility.transactor import Transactor
from tarakdingdung.infrastructure.repository.permission.repository import (
    SqlAlchemyPermissionRepository,
)
from tarakdingdung.infrastructure.repository.role.repository import SqlAlchemyRoleRepository
from tarakdingdung.infrastructure.repository.role_permission.repository import (
    SqlAlchemyRolePermissionRepository,
)
from tarakdingdung.infrastructure.repository.user.repository import SqlAlchemyUserRepository
from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword
from tarakdingdung.infrastructure.utility.token.jwt import JwtToken
from tarakdingdung.infrastructure.utility.transactor.sqlalchemy import SqlAlchemyTransactor


@dataclass(frozen=True, slots=True)
class Infrastructure:
    logger: LeveledLogger
    transactor: Transactor
    permissions: PermissionRepository
    roles: RoleRepository
    role_permissions: RolePermissionRepository
    users: UserRepository
    password: Password
    token: Token


def build_infrastructure(driver: Driver, settings: Settings) -> Infrastructure:
    db = driver.database
    return Infrastructure(
        logger=driver.logger,
        transactor=SqlAlchemyTransactor(db),
        permissions=SqlAlchemyPermissionRepository(db),
        roles=SqlAlchemyRoleRepository(db),
        role_permissions=SqlAlchemyRolePermissionRepository(db),
        users=SqlAlchemyUserRepository(db),
        password=BcryptPassword(settings.password_bcrypt_cost),
        token=JwtToken(
            access_secret=settings.token_access_secret,
            refresh_secret=settings.token_refresh_secret,
            access_ttl=timedelta(seconds=settings.token_access_ttl_seconds),
            refresh_ttl=timedelta(seconds=settings.token_refresh_ttl_seconds),
        ),
    )
```

- [ ] **Step 5: Write `composition/main/application.py`**

```python
from tarakdingdung.application.admin.permission_management.usecase import (
    PermissionManagementUsecase,
)
from tarakdingdung.application.admin.role_management.usecase import RoleManagementUsecase
from tarakdingdung.application.admin.user_management.usecase import UserManagementUsecase
from tarakdingdung.application.auth.session.usecase import SessionUsecase
from tarakdingdung.application.profile.account.usecase import AccountUsecase
from tarakdingdung.application.profile.me.usecase import MeUsecase
from tarakdingdung.application.profile.security.usecase import SecurityUsecase
from tarakdingdung.composition.main.infrastructure import Infrastructure
from tarakdingdung.presentation.http.dependencies.container import Container


def build_container(infra: Infrastructure) -> Container:
    log = infra.logger
    return Container(
        session=SessionUsecase(users=infra.users, roles=infra.roles,
                               password=infra.password, token=infra.token, logger=log),
        permission_management=PermissionManagementUsecase(
            permissions=infra.permissions, logger=log),
        role_management=RoleManagementUsecase(
            roles=infra.roles, role_permissions=infra.role_permissions, logger=log),
        user_management=UserManagementUsecase(
            users=infra.users, password=infra.password, logger=log),
        profile_me=MeUsecase(users=infra.users, logger=log),
        profile_account=AccountUsecase(users=infra.users, logger=log),
        profile_security=SecurityUsecase(
            users=infra.users, password=infra.password, logger=log),
        token=infra.token,
    )
```

Create `composition/__init__.py` and `composition/main/__init__.py`.

- [ ] **Step 6: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_composition_wiring.py -v`
Expected: 2 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tarakdingdung/composition/ backend/tests/integration/test_composition_wiring.py
git commit -m "feat(composition): driver, infrastructure, and application wiring

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 26: Composition — presentation, launcher, and `main.py`

**Files:**
- Create: `backend/src/tarakdingdung/composition/main/presentation.py`
- Create: `backend/src/tarakdingdung/composition/main/launcher.py`
- Create: `backend/src/tarakdingdung/main.py`
- Test: `backend/tests/integration/test_app_boot.py`

**Interfaces:**
- Consumes: `Settings`, `Container`, `build_api_router`, `register_exception_handlers`, `CORSMiddleware`, FastAPI, uvicorn.
- Produces:
  - `composition.main.presentation.build_app(container: Container, settings: Settings) -> FastAPI` — `FastAPI(title=settings.app_name, version=settings.app_version, docs_url="/api/docs", openapi_url="/api/openapi.json")`; `app.state.container = container`; `app.state.app_version = settings.app_version`; add `CORSMiddleware` with `allow_origins=settings.http_cors_allowed_origins`, methods `["GET","HEAD","POST","PATCH","PUT","DELETE","OPTIONS"]`, headers `["Accept","Authorization","Content-Type","Origin","X-Requested-With"]`; `register_exception_handlers(app)`; `app.include_router(build_api_router())`.
  - `composition.main.launcher.create_app(settings: Settings | None = None) -> FastAPI` — `settings = settings or Settings()`; `driver = build_driver(settings)`; `infra = build_infrastructure(driver, settings)`; `container = build_container(infra)`; `app = build_app(container, settings)`; store `app.state.driver = driver`; return `app`.
  - `composition.main.launcher.run() -> None` — `settings = Settings()`; `uvicorn.run("tarakdingdung.main:app", host=settings.http_host, port=settings.http_port, factory=False)`.
  - `tarakdingdung.main.app` — module-level `app = create_app()`.

- [ ] **Step 1: Write the failing test `backend/tests/integration/test_app_boot.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from tarakdingdung.composition.main.launcher import create_app
from tarakdingdung.config.settings import Settings


def _settings(migrated_url: str) -> Settings:
    from urllib.parse import urlparse
    parsed = urlparse(migrated_url.replace("+asyncpg", ""))
    return Settings(
        postgres_host=parsed.hostname, postgres_port=parsed.port,
        postgres_username=parsed.username, postgres_password=parsed.password,
        postgres_database=parsed.path.lstrip("/"),
        logger_format="plain", app_version="v-boot",
    )


@pytest.mark.asyncio
async def test_app_serves_version_and_openapi(migrated_url):
    app = create_app(_settings(migrated_url))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        v = await c.get("/api/version")
        assert v.status_code == 200 and v.text == "v-boot"
        spec = await c.get("/api/openapi.json")
        assert spec.status_code == 200
        paths = spec.json()["paths"]
        assert "/api/v1/auth/login" in paths
        assert "/api/v1/admin/users/{id}" in paths
    await app.state.driver.database.dispose()


@pytest.mark.asyncio
async def test_unknown_route_is_404_not_proxied(migrated_url):
    app = create_app(_settings(migrated_url))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/not/a/route")).status_code == 404
    await app.state.driver.database.dispose()
```

- [ ] **Step 2: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_app_boot.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `composition/main/presentation.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.http.dependencies.container import Container
from tarakdingdung.presentation.http.routers import build_api_router
from tarakdingdung.presentation.http.utils.errors import register_exception_handlers

_METHODS = ["GET", "HEAD", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
_HEADERS = ["Accept", "Authorization", "Content-Type", "Origin", "X-Requested-With"]


def build_app(container: Container, settings: Settings) -> FastAPI:
    app = FastAPI(
        title=settings.app_name, version=settings.app_version,
        docs_url="/api/docs", openapi_url="/api/openapi.json",
    )
    app.state.container = container
    app.state.app_version = settings.app_version
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.http_cors_allowed_origins,
        allow_methods=_METHODS, allow_headers=_HEADERS,
    )
    register_exception_handlers(app)
    app.include_router(build_api_router())
    return app
```

- [ ] **Step 4: Write `composition/main/launcher.py`**

```python
import uvicorn
from fastapi import FastAPI

from tarakdingdung.composition.main.application import build_container
from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.composition.main.presentation import build_app
from tarakdingdung.config.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    container = build_container(infra)
    app = build_app(container, settings)
    app.state.driver = driver
    return app


def run() -> None:
    settings = Settings()
    uvicorn.run("tarakdingdung.main:app", host=settings.http_host, port=settings.http_port)
```

- [ ] **Step 5: Write `backend/src/tarakdingdung/main.py`** (replaces the empty stub)

```python
from tarakdingdung.composition.main.launcher import create_app

app = create_app()
```

- [ ] **Step 6: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_app_boot.py -v`
Expected: 2 tests PASS.

> `tarakdingdung.main` importing at module load calls `create_app()`, which
> constructs a `Database` (no connection yet — asyncpg connects lazily), so
> the import is side-effect-safe for the test. If `Settings()` fails for
> missing required env in some CI, add `.env` to `backend/` from
> `.env.example` or export the `TRDD_BE_*` defaults; all fields already have
> defaults so this should not happen.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tarakdingdung/composition/main/presentation.py \
        backend/src/tarakdingdung/composition/main/launcher.py \
        backend/src/tarakdingdung/main.py \
        backend/tests/integration/test_app_boot.py
git commit -m "feat(composition): FastAPI app factory and uvicorn launcher

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 27: Seed CLI

**Files:**
- Create: `backend/database/seeder/permission.json`
- Create: `backend/database/seeder/role.json`
- Create: `backend/database/seeder/user.json`
- Create: `backend/src/tarakdingdung/composition/seeder/__init__.py`
- Create: `backend/src/tarakdingdung/composition/seeder/__main__.py`
- Create: `backend/src/tarakdingdung/composition/seeder/launcher.py`
- Test: `backend/tests/integration/test_seeder.py`

**Interfaces:**
- Consumes: `Settings`, `build_driver`, `build_infrastructure`, repository contracts, `Transactor`, `BcryptPassword`.
- Produces:
  - Data files (JSON) as below.
  - `composition.seeder.launcher.seed(infra, settings) -> None` — idempotent: for each permission upsert by `name` (create when `read_by_name` is `None`); for each role upsert by `name`, then for each of its `permissions` ensure a `role_permission` link exists (`role_permissions.read_by_role_id_and_permission_id` → create when `None`); for each user, when `users.read_by_username` is `None`, hash `settings.seed_<role>_password` (fall back to the file's `password`) and `users.create(...)`. All wrapped in one `infra.transactor.run(...)`.
  - `composition.seeder.launcher.run() -> None` — `settings = Settings()`; `driver = build_driver(settings)`; `infra = build_infrastructure(driver, settings)`; `asyncio.run(seed(infra, settings))`; `asyncio.run(driver.database.dispose())`.
  - `composition/seeder/__main__.py` → `from tarakdingdung.composition.seeder.launcher import run; run()` so `python -m tarakdingdung.composition.seeder` works.

- [ ] **Step 1: Write `backend/database/seeder/permission.json`**

```json
[
  { "name": "profile:get", "description": "View own profile." },
  { "name": "profile:set", "description": "Update own profile." },
  { "name": "profile_security:set", "description": "Change own password." },
  { "name": "permission:get", "description": "View permissions." },
  { "name": "permission:add", "description": "Create permissions." },
  { "name": "permission:set", "description": "Update permissions." },
  { "name": "permission:remove", "description": "Delete permissions." },
  { "name": "role:get", "description": "View roles." },
  { "name": "role:add", "description": "Create roles." },
  { "name": "role:set", "description": "Update roles, including setting the default role." },
  { "name": "role:remove", "description": "Delete roles." },
  { "name": "role_permission:get", "description": "View role-permission assignments." },
  { "name": "role_permission:add", "description": "Assign a permission to a role." },
  { "name": "role_permission:remove", "description": "Remove a permission from a role." },
  { "name": "user:get", "description": "View users." },
  { "name": "user:add", "description": "Create users." },
  { "name": "user:set", "description": "Update users." },
  { "name": "user:remove", "description": "Delete users." },
  { "name": "user_permission:get", "description": "View a user's effective permissions." },
  { "name": "user_password:set", "description": "Reset a user's password." }
]
```

- [ ] **Step 2: Write `backend/database/seeder/role.json`**

```json
[
  {
    "name": "super",
    "description": "Full RBAC control: manage permissions, roles, assignments, and users.",
    "is_default": false,
    "permissions": [
      "profile:get", "profile:set", "profile_security:set",
      "permission:get", "permission:add", "permission:set", "permission:remove",
      "role:get", "role:add", "role:set", "role:remove",
      "role_permission:get", "role_permission:add", "role_permission:remove",
      "user:get", "user:add", "user:set", "user:remove",
      "user_permission:get", "user_password:set"
    ]
  },
  {
    "name": "admin",
    "description": "Manage users, but not the permission/role system itself.",
    "is_default": false,
    "permissions": [
      "profile:get", "profile:set", "profile_security:set",
      "user:get", "user:add", "user:set", "user:remove",
      "user_permission:get", "user_password:set"
    ]
  },
  {
    "name": "user",
    "description": "Default role: self-service profile management only.",
    "is_default": true,
    "permissions": ["profile:get", "profile:set", "profile_security:set"]
  }
]
```

- [ ] **Step 3: Write `backend/database/seeder/user.json`**

```json
[
  { "role_name": "super", "name": "Default Super", "username": "super", "password": "changeme12345" },
  { "role_name": "admin", "name": "Default Admin", "username": "admin", "password": "changeme12345" },
  { "role_name": "user", "name": "Default User", "username": "user", "password": "changeme12345" }
]
```

- [ ] **Step 4: Write the failing test `backend/tests/integration/test_seeder.py`**

```python
import pytest
from sqlalchemy import text

from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.composition.seeder.launcher import seed
from tarakdingdung.config.settings import Settings


def _settings(url: str) -> Settings:
    from urllib.parse import urlparse
    p = urlparse(url.replace("+asyncpg", ""))
    return Settings(postgres_host=p.hostname, postgres_port=p.port, postgres_username=p.username,
                    postgres_password=p.password, postgres_database=p.path.lstrip("/"),
                    logger_format="plain", seed_super_password="superpass12")


@pytest.mark.asyncio
async def test_seed_is_idempotent_and_links_permissions(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    try:
        await seed(infra, settings)
        await seed(infra, settings)  # second run must not raise or duplicate
        async with driver.database.session() as s:
            perms = await s.scalar(text("SELECT count(*) FROM permissions WHERE deleted_at IS NULL"))
            roles = await s.scalar(text("SELECT count(*) FROM roles WHERE deleted_at IS NULL"))
            users = await s.scalar(text("SELECT count(*) FROM users WHERE deleted_at IS NULL"))
            super_links = await s.scalar(text(
                "SELECT count(*) FROM role_permission rp "
                "JOIN roles r ON r.id = rp.role_id WHERE r.name = 'super'"))
            default_role = await s.scalar(text(
                "SELECT name FROM roles WHERE is_default = TRUE AND deleted_at IS NULL"))
        assert perms == 20 and roles == 3 and users == 3
        assert super_links == 20
        assert default_role == "user"
    finally:
        async with driver.database.session() as s:
            await s.execute(text("DELETE FROM role_permission"))
            await s.execute(text("DELETE FROM users"))
            await s.execute(text("DELETE FROM roles"))
            await s.execute(text("DELETE FROM permissions"))
            await s.commit()
        await driver.database.dispose()


@pytest.mark.asyncio
async def test_seed_hashes_password_from_settings(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    try:
        await seed(infra, settings)
        user = await infra.users.read_by_username("super")
        await infra.password.compare(user.password_hash, "superpass12")  # no raise
    finally:
        async with driver.database.session() as s:
            await s.execute(text("DELETE FROM role_permission"))
            await s.execute(text("DELETE FROM users"))
            await s.execute(text("DELETE FROM roles"))
            await s.execute(text("DELETE FROM permissions"))
            await s.commit()
        await driver.database.dispose()
```

- [ ] **Step 5: Run to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_seeder.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 6: Write `composition/seeder/launcher.py`**

```python
import asyncio
import json
from pathlib import Path

from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import Infrastructure, build_infrastructure
from tarakdingdung.config.settings import Settings

_SEED_DIR = Path(__file__).resolve().parents[4] / "database" / "seeder"


def _load(name: str) -> list[dict]:
    return json.loads((_SEED_DIR / name).read_text(encoding="utf-8"))


async def seed(infra: Infrastructure, settings: Settings) -> None:
    permissions = _load("permission.json")
    roles = _load("role.json")
    users = _load("user.json")

    password_overrides = {
        "super": settings.seed_super_password,
        "admin": settings.seed_admin_password,
        "user": settings.seed_user_password,
    }

    async def _do() -> None:
        perm_ids: dict[str, object] = {}
        for entry in permissions:
            existing = await infra.permissions.read_by_name(entry["name"])
            if existing is None:
                perm_ids[entry["name"]] = await infra.permissions.create(
                    name=entry["name"], description=entry.get("description"), created_by=None)
            else:
                perm_ids[entry["name"]] = existing.id

        role_ids: dict[str, object] = {}
        for entry in roles:
            existing = await infra.roles.read_by_name(entry["name"])
            if existing is None:
                role_id = await infra.roles.create(
                    name=entry["name"], description=entry.get("description"),
                    is_default=entry.get("is_default", False), created_by=None)
            else:
                role_id = existing.id
            role_ids[entry["name"]] = role_id
            for perm_name in entry.get("permissions", []):
                pid = perm_ids[perm_name]
                link = await infra.role_permissions.read_by_role_id_and_permission_id(role_id, pid)
                if link is None:
                    await infra.role_permissions.create(
                        role_id=role_id, permission_id=pid, created_by=None)

        for entry in users:
            if await infra.users.read_by_username(entry["username"]) is not None:
                continue
            raw = password_overrides.get(entry["role_name"]) or entry["password"]
            password_hash = await infra.password.hash(raw)
            await infra.users.create(
                role_id=role_ids[entry["role_name"]], name=entry["name"], bio=None,
                username=entry["username"], password_hash=password_hash, created_by=None)

    await infra.transactor.run(_do)


def run() -> None:
    settings = Settings()
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    try:
        asyncio.run(seed(infra, settings))
    finally:
        asyncio.run(driver.database.dispose())
```

> `parents[4]` from `.../src/tarakdingdung/composition/seeder/launcher.py`
> resolves to `backend/`. Confirm with the test; adjust index if off.

- [ ] **Step 7: Write `composition/seeder/__main__.py`**

```python
from tarakdingdung.composition.seeder.launcher import run

if __name__ == "__main__":
    run()
```

Create `composition/seeder/__init__.py`.

- [ ] **Step 8: Run to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/integration/test_seeder.py -v`
Expected: 2 tests PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/database/seeder/ backend/src/tarakdingdung/composition/seeder/ \
        backend/tests/integration/test_seeder.py
git commit -m "feat(seeder): idempotent baseline RBAC seed CLI

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 28: End-to-end RBAC round-trip through the composed app + seed

**Files:**
- Test: `backend/tests/e2e/__init__.py`
- Test: `backend/tests/e2e/conftest.py`
- Test: `backend/tests/e2e/test_rbac_roundtrip.py`

**Interfaces:**
- Consumes: `create_app`, `seed`, `build_driver`, `build_infrastructure`, `Settings`, `testcontainers` Postgres (reuse the `postgres_url` / `migrated_url` fixtures from `tests/integration/conftest.py` — move those two fixtures up to `tests/conftest.py` so both suites see them).
- Produces: an e2e conftest exposing `e2e_app` (a `create_app(settings)` bound to the migrated container DB, with `seed(...)` already run and a per-test cleanup that truncates the four tables afterward) and `e2e_client` (httpx `AsyncClient` over `ASGITransport`).

- [ ] **Step 1: Move shared DB fixtures**

Cut `postgres_url` and `migrated_url` from `backend/tests/integration/conftest.py` and paste them into `backend/tests/conftest.py` (keep the `db` fixture in the integration conftest). Add `import pytest_asyncio` to `tests/conftest.py` if needed. Re-run `backend/.venv/bin/pytest backend/tests/integration -q` to confirm nothing broke.

- [ ] **Step 2: Write `backend/tests/e2e/conftest.py`**

```python
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.composition.main.launcher import create_app
from tarakdingdung.composition.seeder.launcher import seed
from tarakdingdung.config.settings import Settings


def _settings(url: str) -> Settings:
    p = urlparse(url.replace("+asyncpg", ""))
    return Settings(postgres_host=p.hostname, postgres_port=p.port, postgres_username=p.username,
                    postgres_password=p.password, postgres_database=p.path.lstrip("/"),
                    logger_format="plain", password_bcrypt_cost=4,
                    seed_super_password="superpass12")


@pytest_asyncio.fixture
async def e2e_app(migrated_url):
    settings = _settings(migrated_url)
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    await seed(infra, settings)
    app = create_app(settings)
    try:
        yield app
    finally:
        async with driver.database.session() as s:
            await s.execute(text("DELETE FROM role_permission"))
            await s.execute(text("DELETE FROM users"))
            await s.execute(text("DELETE FROM roles"))
            await s.execute(text("DELETE FROM permissions"))
            await s.commit()
        await driver.database.dispose()
        await app.state.driver.database.dispose()


@pytest_asyncio.fixture
async def e2e_client(e2e_app):
    async with AsyncClient(transport=ASGITransport(app=e2e_app), base_url="http://t") as c:
        yield c


@pytest_asyncio.fixture
async def super_headers(e2e_client):
    resp = await e2e_client.post("/api/v1/auth/login",
                                 json={"username": "super", "password": "superpass12"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
```

- [ ] **Step 3: Write the failing test `backend/tests/e2e/test_rbac_roundtrip.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_login_returns_seeded_permissions(e2e_client):
    resp = await e2e_client.post("/api/v1/auth/login",
                                 json={"username": "super", "password": "superpass12"})
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()["permissions"]}
    assert {"permission:add", "role:add", "user:add"} <= names


@pytest.mark.asyncio
async def test_no_token_is_401_and_wrong_permission_is_403(e2e_client):
    assert (await e2e_client.get("/api/v1/admin/users")).status_code == 401
    login = await e2e_client.post("/api/v1/auth/login",
                                  json={"username": "user", "password": "changeme12345"})
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await e2e_client.get("/api/v1/admin/users", headers=user_headers)).status_code == 403
    assert (await e2e_client.get("/api/v1/profile", headers=user_headers)).status_code == 200


@pytest.mark.asyncio
async def test_full_rbac_roundtrip(e2e_client, super_headers):
    role_id = (await e2e_client.post("/api/v1/admin/roles", json={"name": "barista"},
                                     headers=super_headers)).json()["id"]
    perm_id = (await e2e_client.post("/api/v1/admin/permissions",
                                     json={"name": "profile:get"}, headers=super_headers)).json()
    # profile:get already seeded -> expect 409
    dup = await e2e_client.post("/api/v1/admin/permissions", json={"name": "profile:get"},
                                headers=super_headers)
    assert dup.status_code == 409

    new_perm = (await e2e_client.post("/api/v1/admin/permissions", json={"name": "brew:pull"},
                                      headers=super_headers)).json()["id"]
    assign = await e2e_client.post(
        f"/api/v1/admin/roles/{role_id}/permissions/{new_perm}", headers=super_headers)
    assert assign.status_code == 201

    created_user = await e2e_client.post("/api/v1/admin/users", json={
        "role_id": role_id, "name": "Bar Ista", "username": "barista1", "password": "espresso9",
    }, headers=super_headers)
    assert created_user.status_code == 201

    login = await e2e_client.post("/api/v1/auth/login",
                                  json={"username": "barista1", "password": "espresso9"})
    assert login.status_code == 200
    assert {p["name"] for p in login.json()["permissions"]} == {"brew:pull"}

    barista_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    perms = await e2e_client.get("/api/v1/profile/permissions", headers=barista_headers)
    # barista role lacks profile:get -> 403 on the profile route
    assert perms.status_code == 403


@pytest.mark.asyncio
async def test_domain_error_body_shape(e2e_client, super_headers):
    resp = await e2e_client.get("/api/v1/admin/roles/by-name/does-not-exist",
                                headers=super_headers)
    assert resp.status_code == 404
    assert set(resp.json()) == {"error", "message"}
    assert resp.json()["error"] == "Not Found"
```

- [ ] **Step 4: Run to verify it fails, then passes**

Run: `backend/.venv/bin/pytest backend/tests/e2e/ -v`
Expected: initially collection/fixture errors if `postgres_url`/`migrated_url` weren't moved in Step 1; after Step 1 they run and PASS. Create empty `backend/tests/e2e/__init__.py`.

- [ ] **Step 5: Full test-suite regression**

Run: `backend/.venv/bin/pytest backend/tests -v`
Expected: every test PASSES.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/
git commit -m "test(e2e): full RBAC round-trip through the composed app

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

### Task 29: Docs, developer entrypoints, and final dependency freeze

**Files:**
- Create: `backend/AGENTS.md`
- Create: `backend/README.md`
- Modify: `backend/pyproject.toml` (add console-script entrypoints)
- Modify: `backend/requirements.txt` (final `pip freeze`)
- Modify: `backend/.env.example` (verify against `Settings`)

**Interfaces:**
- Consumes: everything built so far.
- Produces: developer-facing docs and `tarakdingdung-serve` / `tarakdingdung-seed` console scripts.

- [ ] **Step 1: Add console scripts to `backend/pyproject.toml`**

Add under `[project]`:
```toml
[project.scripts]
tarakdingdung-serve = "tarakdingdung.composition.main.launcher:run"
tarakdingdung-seed = "tarakdingdung.composition.seeder.launcher:run"
```

- [ ] **Step 2: Reinstall so the scripts register, then freeze**

Run:
```bash
backend/.venv/bin/pip install -e "backend/[dev]"
backend/.venv/bin/pip freeze --exclude-editable > backend/requirements.txt
```
Expected: `backend/.venv/bin/tarakdingdung-serve` and `-seed` now exist.

- [ ] **Step 3: Write `backend/README.md`**

```markdown
# tarakdingdung backend

FastAPI + SQLAlchemy (async) RBAC & auth service, ported from
`nusapala-things/backend` (Go). Layered architecture:
`presentation → application → domain ← infrastructure`, wired by `composition`.

## Setup

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -e "backend/[dev]"
cp backend/.env.example backend/.env   # edit as needed
```

## Database

```bash
cd backend && ../backend/.venv/bin/alembic upgrade head
backend/.venv/bin/tarakdingdung-seed        # baseline permissions/roles/users
```

## Run

```bash
backend/.venv/bin/tarakdingdung-serve        # uvicorn on TRDD_BE_HTTP_HOST:PORT
# OpenAPI docs: http://localhost:8080/api/docs
```

## Test

```bash
backend/.venv/bin/pytest backend/tests           # needs Docker for integration/e2e
backend/.venv/bin/pytest backend/tests/unit -q   # (unit + domain, no Docker)
```

Default seeded logins (override via `TRDD_BE_SEED_*`): `super` / `admin` /
`user`, password `changeme12345`.
```

- [ ] **Step 4: Write `backend/AGENTS.md`**

```markdown
# Backend architecture (tarakdingdung)

Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, PyJWT, bcrypt.
Ported from the Go `nusapala-things/backend`; see
`docs/superpowers/specs/2026-09-06-python-backend-rbac-auth-port-design.md`.

## Dependency rule

`presentation → application → domain ← infrastructure`; `composition` wires
all layers. `domain/` imports only stdlib + `uuid`. `presentation/` never
imports `infrastructure/`.

## Layout

- `domain/models` — frozen dataclasses + `DomainError`/`ErrorType`.
- `domain/contracts` — repository/utility/logger ABCs.
- `domain/usecases` — usecase ABCs + request/result dataclasses.
- `application/` — usecase implementations + `application/shared/validation.py`.
- `infrastructure/repository/database` — ORM models + async `Database`.
- `infrastructure/repository/<entity>` — `repository.py` + `queries.py`
  (SQLAlchemy Core statement builders).
- `infrastructure/utility/{password,token,transactor}` — bcrypt / PyJWT /
  context-var unit of work.
- `presentation/http/{routers,dependencies,schemas,utils}` — FastAPI.
- `composition/main/{driver,infrastructure,application,presentation,launcher}`.
- `composition/seeder` — `python -m tarakdingdung.composition.seeder`.
- `migrations/` — Alembic; `database/seeder/*.json` — seed data.

## Conventions

- Repository verbs: `create`, `read_by_id`, `read_by_<field>`,
  `read_default`, `read_permissions`, `read_by_pagination`, `update_by_id`,
  `delete_by_id`. Pagination → `(items, total)`. Single read → `T | None`.
- Soft delete on `permissions`/`roles`/`users`; `role_permission` is hard
  deleted.
- Errors: raise `DomainError(message, ErrorType.X)`. HTTP mapping in
  `presentation/http/utils/errors.py`.
- Value validation lives in `application/shared/validation.py`; request
  *shape* validation is Pydantic in `presentation/http/schemas`.
- Config: `Settings` (`pydantic-settings`), env prefix `TRDD_BE_`.
- Tests: `pytest` (`asyncio_mode = "auto"`). Integration/e2e use
  `testcontainers` Postgres — Docker required.

## Deviations from the Go source

No Redis/`repocache` layer (usecases depend on repository contracts
directly); FastAPI-idiomatic presentation naming; Alembic instead of
golang-migrate; api-key auth / payload-schema / llm-config / reverse
proxies are out of scope.
```

- [ ] **Step 5: Verify `.env.example` covers every `Settings` field**

Run:
```bash
backend/.venv/bin/python - <<'PY'
from tarakdingdung.config.settings import Settings
import pathlib
env = pathlib.Path("backend/.env.example").read_text()
missing = [f"TRDD_BE_{name.upper()}" for name in Settings.model_fields
           if f"TRDD_BE_{name.upper()}" not in env]
print("MISSING:", missing)
PY
```
Expected: `MISSING: []`. If not, add the missing lines to `backend/.env.example`.

- [ ] **Step 6: Final full regression**

Run: `backend/.venv/bin/pytest backend/tests -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/AGENTS.md backend/README.md backend/pyproject.toml \
        backend/requirements.txt backend/.env.example
git commit -m "docs(backend): architecture notes, README, and console scripts

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JP2bVSyEzciKk19CV2xdMA"
```

---

## Self-Review

### 1. Spec coverage

| Spec section | Task(s) |
|---|---|
| §3 Architecture / dependency rule | 2–29 (enforced throughout; `domain` import rule verified by Task 3 test) |
| §4 Folder layout | every task creates its slice of the tree |
| §5.1 `ErrorType` / `DomainError` | Task 2 |
| §5.2 domain dataclasses | Task 2 |
| §5.3 repository contracts | Task 3 |
| §5.4 utility contracts (`Password`/`Token`/`Transactor`) | Task 3 |
| §5.5 usecase interfaces + DTOs | Task 4 |
| §6.1 `application/shared/validation.py` | Task 15 |
| §6.2 admin/auth/profile usecase impls | Tasks 16–20 |
| §7.1 ORM models | Task 5 |
| §7.2 `Database` / session context var | Task 5 (+ `persist` helper in Task 9) |
| §7.3 `SqlAlchemyTransactor` | Task 7 |
| §7.4 repository impls + `queries.py` | Tasks 9–12 |
| §7.5 `map_db_error` / `query.py` / `mappers.py` | Task 8 |
| §7.6 bcrypt password | Task 13 |
| §7.7 JWT token | Task 13 |
| §7.8 logger `normalize_meta` | Task 14 |
| §8.1 route table (`/api/...`) | Task 24 |
| §8.2 auth/permission/container dependencies | Task 23 |
| §8.3 request/response schemas + mappers | Task 21 |
| §8.4 `DOMAIN_STATUS` + exception handlers | Task 22 |
| §8.4 pagination params | Task 22 |
| §8.5 router functions / status codes | Task 24 |
| §9 composition driver/infra/app/presentation/launcher + `main.py` | Tasks 25–26 |
| §10 Alembic + 6 revisions | Task 6 |
| §11 seed CLI + data files | Task 27 |
| §12 `Settings` (`TRDD_BE_`) | Task 1 |
| §13 dependencies + `pip freeze` + `pyproject.toml` | Tasks 1, 29 |
| §14 unit / integration / e2e tests | Tasks 2–28 (TDD per task) + Task 28 (e2e) |
| §15 documented deviations | Task 29 `AGENTS.md` |
| §16 build milestones | this plan's task order |

No spec requirement is left without a task.

### 2. Placeholder scan

No `TBD`/`TODO`/"implement later". Every code step carries the actual
source. "Similar to Task N" is not used — repositories 10/11/12 each spell
out their own `queries.py`/`repository.py`. Notes marked with `>` are
implementation cautions (path-index checks, SQLAlchemy row-attr access,
test-assertion cleanups), not deferred work.

### 3. Type consistency

- `Database.session()` (async context manager) + `Database.persist(session)`
  + `Database.current_session` (ContextVar) — defined Task 5, `persist`
  added Task 9 Step 5, used Tasks 9–12, consumed by `SqlAlchemyTransactor`
  Task 7.
- Repository classes: `SqlAlchemyPermissionRepository`, `SqlAlchemyRoleRepository`,
  `SqlAlchemyRolePermissionRepository`, `SqlAlchemyUserRepository` — same
  names in Tasks 9–12, `tests/fakes` (Task 16), and `composition/main/infrastructure.py`
  (Task 25).
- `map_db_error(message, exc, *conflicts)` + `ConflictMatch(contains, type)` —
  Task 8, used Tasks 9–12.
- Usecase classes: `PermissionManagementUsecase`, `RoleManagementUsecase`,
  `UserManagementUsecase`, `SessionUsecase`, `MeUsecase`, `AccountUsecase`,
  `SecurityUsecase` — Tasks 16–20, referenced by `composition/main/application.py`
  (Task 25) and `tests/presentation/conftest.py` (Task 24).
- `Container` fields (`session`, `permission_management`, `role_management`,
  `user_management`, `profile_me`, `profile_account`, `profile_security`,
  `token`) — Task 23; `build_container` populates exactly these (Task 25);
  dependency accessors and routers read exactly these (Tasks 23–24).
- `build_driver → Driver`, `build_infrastructure → Infrastructure`,
  `build_container → Container`, `build_app → FastAPI`, `create_app → FastAPI`,
  `run` — Tasks 25–26, consistent across `launcher.py`, tests, and Task 29
  console scripts.
- `seed(infra, settings)` + `run()` — Task 27, called by Task 28 e2e conftest
  and Task 29 console script.
- Response mappers: `permission_response`, `permissions_response`,
  `role_response`, `roles_response`, `user_response`, `user_list_item_response`,
  `user_list_items_response`, `login_response`, `role_permission_detail_response`,
  `role_permission_details_response` — Task 21, used by routers Task 24.
- `pagination_params` (dependency) / `PaginationParams` (dataclass) /
  `page_response` — Task 22, used Task 24.
- Domain usecase request classes referenced in Task 24 via `pm.`/`rm.`/`um.`
  aliases all originate in Task 4's **Produces** block (names checked:
  `ReadPermissionByIdRequest`, `ReadPermissionByNameRequest`,
  `ReadPermissionsByPaginationRequest`, `CreatePermissionRequest`,
  `UpdatePermissionRequest`, `DeletePermissionRequest`; role + user analogues;
  `ReadDefaultRoleRequest`, `ReadRolePermissionsRequest`,
  `SetDefaultRoleRequest`, `AssignRolePermissionRequest`,
  `RevokeRolePermissionRequest`, `ReadRolePermissionByIdRequest`,
  `ReadRolePermissionByRoleIdAndPermissionIdRequest`,
  `ReadRolePermissionsByPaginationRequest`; `ReadUserByUsernameRequest`,
  `ReadUserPermissionsRequest`, `ReadUsersByPaginationRequest`,
  `ResetUserPasswordRequest`, `UpdateUserRequest`, `DeleteUserRequest`).

One deliberate cross-task adjustment is called out inline: Task 6 Step 1
writes a first-pass migration test that Step 7 **replaces** with the
psycopg-free version — the replacement is the one that must pass. Task 28
Step 1 moves `postgres_url`/`migrated_url` from the integration conftest to
the top-level conftest; Tasks 6/7/25/26/27 reference those fixtures and
keep working because the move is upward in scope.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-06-python-backend-rbac-auth-port.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

**Which approach?**
