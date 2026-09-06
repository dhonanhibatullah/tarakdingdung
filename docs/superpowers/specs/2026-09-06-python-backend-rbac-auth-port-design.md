# Design: Python/FastAPI backend — RBAC + Auth port from `nusapala-things`

Date: 2026-09-06
Status: Approved for planning

## 1. Context

`nusapala-things/backend/` is a Go service built on a strict layered/clean
architecture. This project (`tarakdingdung`) has an empty Python backend
skeleton under `backend/src/tarakdingdung/` that already contains the
`domain/models/logger.py`, `domain/contracts/logger/leveled.py`, and
`infrastructure/logger/leveled/{plain,json}.py` files, plus empty package
directories mirroring the Go layout.

The goal is to port the **RBAC + authentication slice** of the Go backend
to Python/FastAPI, faithfully preserving the architecture, folder
structure, naming conventions, error-handling model, repository verb set,
and validation rules — up to and including a runnable `composition/main`
entrypoint.

### Reference source (Go) — files this design is derived from

- `internal/domain/models/{user,role,permission,role_permission,error,token_claims,logger}.go`
- `internal/domain/contracts/repository/{user,role,permission,role_permission}.go`
- `internal/domain/contracts/utility/{password,token,transactor}.go`
- `internal/domain/contracts/logger/leveled.go`
- `internal/domain/usecases/admin/{user,role,permission}_management.go`
- `internal/domain/usecases/auth/session.go`
- `internal/domain/usecases/profile/{me,account,security}.go`
- `internal/application/admin/*/usecase.go`, `internal/application/auth/session/usecase.go`,
  `internal/application/profile/*/usecase.go`, `internal/application/shared/validation.go`
- `internal/infrastructure/repository/{shared,role,permission,role_permission,user}/*.go`
- `internal/infrastructure/utility/{password/bcrypt,token/jwt,transactor/pgxdt}.go`
- `internal/infrastructure/logger/leveled/{slog,normalize}.go`
- `internal/presentation/http/{handler/{auth,admin,profile,version},middleware/{auth,permission},request,response,route,utils}/*.go`
- `internal/composition/main/{driver,infrastructure,application,presentation,launcher}.go`
- `internal/config/{app,env}.go`
- `database/migrations/2026072012*_{create_extensions,create_permissions,create_roles,create_role_permission,create_users}.{up,down}.sql`
- `database/migrations/20260727080000_soft_delete_partial_unique_indexes.{up,down}.sql`
- `database/seeder/{permission,role,user}.json`

## 2. Scope

### In scope

| Area | Detail |
|---|---|
| Entities | `permission`, `role`, `role_permission`, `user` |
| Admin usecases | `PermissionManagement`, `RoleManagement` (incl. role↔permission assignment + set-default), `UserManagement` (incl. password reset) |
| Auth | `auth/session`: `login` (username/password → access+refresh JWT), `refresh` |
| Profile | `profile/me` (get profile + permissions), `profile/account` (self update), `profile/security` (change own password) |
| Utilities | `Password` (bcrypt), `Token` (JWT HS256), `Transactor` (SQLAlchemy) |
| Logger | Reuse existing `Leveled` contract + `plain`/`json` infra impls unchanged; add `normalize_meta` |
| Persistence | SQLAlchemy 2.0 async ORM + Core, `asyncpg`, Postgres |
| Migrations | Alembic, 6 hand-written revisions mirroring the Go SQL |
| Seeder | Standalone CLI: baseline permissions/roles/role_permission + default users |
| Presentation | FastAPI, routes under `/api`, CORS, `DomainError`→HTTP mapping |
| Composition | `composition/main` app factory (`create_app()`), served by `uvicorn` |
| Config | `pydantic-settings` `BaseSettings`, env prefix `TRDD_BE_` |
| Tests | pytest; unit (fakes), integration (`testcontainers` Postgres), e2e (httpx ASGI) |

### Out of scope (present in `nusapala-things`, deliberately excluded)

- Redis cache / `repocache` decorator layer — usecases depend on repository
  contracts **directly**.
- `api_key` authentication and admin API-key management.
- `payload_schema`, `llm_config`, nodes, firmware, telemetry, derived
  records, node logs, infrared, MQTT, MinIO.
- `preferences` update usecase (the `preferences` JSONB column is still
  created, modelled, and returned in responses — just not mutated by any
  in-scope usecase).
- Reverse proxies (Next.js frontend, MinIO, Node-RED), Swagger generation
  tooling (FastAPI serves its own OpenAPI at `/api/docs`).
- `timescaledb` extension (only needed by telemetry).

## 3. Architecture

One-directional dependency rule, identical to the Go service:

```
presentation → application → domain ← infrastructure
                                ↑
                          composition (wires everything together)
```

- `domain` imports only stdlib + `uuid`. No SQLAlchemy, FastAPI, Pydantic.
- `application` imports `domain` only.
- `infrastructure` imports `domain` only (plus its own drivers). May import
  sibling `infrastructure` modules.
- `presentation` imports `application` usecase interfaces + `domain`
  models/errors. Never imports `infrastructure`.
- `composition` is the only layer importing concrete types from everywhere.

### Language/style conventions

- Domain models: `@dataclass(frozen=True, slots=True)` — the "plain struct"
  analogue. Optional fields typed `T | None`, defaulted `None`.
- Contracts and usecase interfaces: `abc.ABC` + `@abstractmethod`
  (per requirement [3]).
- All repository / usecase / logger methods are `async`.
- Repository verb set is fixed: `create`, `read_by_id`, `read_by_<field>`,
  `read_default`, `read_permissions`, `read_by_pagination`, `update_by_id`,
  `delete_by_id`. No `get`/`list`/`find`.
- Pagination methods return `tuple[list[T], int]` (items, total).
- Single-item reads return `T | None`.
- snake_case module/dir names; module contents in `snake_case`;
  classes `PascalCase`.

## 4. Folder layout

Under `backend/src/tarakdingdung/`:

```
config/
  settings.py                     # pydantic-settings BaseSettings, env prefix TRDD_BE_

domain/
  models/
    logger.py                     # EXISTS — unchanged
    error.py                      # ErrorType (StrEnum), DomainError (Exception)
    permission.py                 # Permission
    role.py                       # Role
    role_permission.py            # RolePermission
    user.py                       # User, UserListItem
    token_claims.py               # TokenClaimsAccess, TokenClaimsRefresh
  contracts/
    logger/leveled.py             # EXISTS — unchanged
    repository/
      permission.py               # PermissionRepository(ABC)
      role.py                     # RoleRepository(ABC)
      role_permission.py          # RolePermissionRepository(ABC)
      user.py                     # UserRepository(ABC)
    utility/
      password.py                 # Password(ABC)
      token.py                    # Token(ABC)
      transactor.py               # Transactor(ABC)
  usecases/
    admin/
      permission_management.py    # PermissionManagement(ABC) + request dataclasses
      role_management.py          # RoleManagement(ABC) + request/result dataclasses
      user_management.py          # UserManagement(ABC) + request dataclasses
    auth/
      session.py                  # Session(ABC) + LoginRequest/RefreshRequest/LoginResult
    profile/
      me.py                       # Me(ABC) + request dataclasses
      account.py                  # Account(ABC) + request dataclasses
      security.py                 # Security(ABC) + request dataclasses

application/
  shared/
    validation.py                 # required_*/optional_* value validators
  admin/
    permission_management/usecase.py
    role_management/usecase.py
    user_management/usecase.py
  auth/
    session/usecase.py
  profile/
    me/usecase.py
    account/usecase.py
    security/usecase.py

infrastructure/
  logger/
    leveled/plain.py              # EXISTS — call normalize_meta
    leveled/json.py               # EXISTS — call normalize_meta
    normalize.py                  # normalize_meta(meta) -> dict
  repository/
    database/
      orm.py                      # DeclarativeBase + *ORM table models
      session.py                  # engine, async_sessionmaker, current-session ContextVar, get_session()
    shared/
      errors.py                   # map_db_error(...)
      query.py                    # normalize_limit / normalize_offset / search_pattern
      mappers.py                  # *_orm -> domain dataclass
    permission/{repository.py,queries.py}
    role/{repository.py,queries.py}
    role_permission/{repository.py,queries.py}
    user/{repository.py,queries.py}
  utility/
    password/bcrypt.py            # BcryptPassword(Password)
    token/jwt.py                  # JwtToken(Token)
    transactor/sqlalchemy.py      # SqlAlchemyTransactor(Transactor)

presentation/
  http/
    routers/
      __init__.py                 # api_router(container) -> APIRouter  (route.go analogue)
      auth.py
      admin.py
      profile.py
      version.py
    dependencies/
      auth.py                     # get_access_claims, get_actor_id
      permission.py               # require(*perms)
      container.py                # usecase accessors bound to app.state
    schemas/
      request.py                  # Pydantic request models
      response.py                 # Pydantic response models + mappers
    utils/
      errors.py                   # DOMAIN_STATUS table + exception handler
      pagination.py               # page/limit/search parsing, page_response

composition/
  main/
    driver.py                     # engine + sessionmaker + logger backend
    infrastructure.py             # build repositories/utilities -> Infrastructure container
    application.py                # build usecases -> Application container
    presentation.py               # build FastAPI app: CORS, error handler, include routers
    launcher.py                   # create_app() -> FastAPI ; run() (uvicorn + signals)
  seeder/
    launcher.py                   # run() — idempotent baseline seed

main.py                           # app = create_app()
```

Repo-root / `backend/` additions:

```
backend/pyproject.toml            # project metadata, src layout, pytest config
backend/requirements.txt          # full `pip freeze` of the .venv
backend/.env.example              # documents every TRDD_BE_* var
backend/alembic.ini
backend/migrations/env.py
backend/migrations/versions/00{01..06}_*.py
backend/database/seeder/{permission,role,user}.json
backend/tests/{unit,integration,e2e}/...
backend/tests/conftest.py
backend/AGENTS.md                 # ported architecture notes
backend/README.md
```

## 5. Domain layer

### 5.1 `domain/models/error.py`

```python
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
    def __init__(self, message: str, type: ErrorType, source: Exception | None = None): ...
    # __str__ -> "[TYPE] message: source" | "[TYPE] message"
```

All application/infrastructure failures raise `DomainError`. No other
custom exception types are introduced.

### 5.2 `domain/models` dataclasses

Mirror the Go structs one-to-one (`db`/`json` tags become field names):

- `Permission(id: UUID, name: str, description: str, preferences: dict,
  created_at: datetime, updated_at: datetime | None,
  deleted_at: datetime | None, created_by: UUID | None,
  updated_by: UUID | None, deleted_by: UUID | None)`
- `Role(... same audit fields ..., is_default: bool)`
- `RolePermission(id: UUID, role_id: UUID, permission_id: UUID,
  created_at: datetime, created_by: UUID | None)`
- `User(id, role_id, name, bio, username, password_hash, preferences,
  + audit fields)`
- `UserListItem(user: User, role_name: str)`
- `TokenClaimsAccess(user_id: UUID, name: str, username: str, role: str,
  permissions: list[str])`
- `TokenClaimsRefresh(user_id: UUID)`

### 5.3 `domain/contracts/repository/*` (ABC)

Method signatures port the Go interfaces verbatim. Representative:

```python
class UserRepository(ABC):
    @abstractmethod
    async def create(self, *, role_id: UUID, name: str, bio: str | None,
                     username: str, password_hash: str,
                     created_by: UUID | None) -> UUID: ...
    @abstractmethod
    async def read_by_id(self, id: UUID) -> User | None: ...
    @abstractmethod
    async def read_by_username(self, username: str) -> User | None: ...
    @abstractmethod
    async def read_permissions(self, user_id: UUID) -> list[Permission]: ...
    @abstractmethod
    async def read_by_pagination(self, *, page: int, limit: int,
                                 search: str | None,
                                 role_id: UUID | None
                                 ) -> tuple[list[UserListItem], int]: ...
    @abstractmethod
    async def update_by_id(self, id: UUID, *, role_id: UUID | None = None,
                           name: str | None = None, bio: str | None = None,
                           username: str | None = None,
                           password_hash: str | None = None,
                           preferences: dict | None = None,
                           updated_by: UUID | None = None) -> None: ...
    @abstractmethod
    async def delete_by_id(self, id: UUID, *,
                           deleted_by: UUID | None = None) -> None: ...
```

`RoleRepository`: `create`, `read_by_id`, `read_by_name`, `read_default`,
`read_permissions`, `read_by_pagination(page, limit, search)`,
`update_by_id(name, description, is_default, preferences, updated_by)`,
`delete_by_id`.

`PermissionRepository`: `create`, `read_by_id`, `read_by_name`,
`read_by_pagination(page, limit, search)`,
`update_by_id(name, description, preferences, updated_by)`, `delete_by_id`.

`RolePermissionRepository`: `create(role_id, permission_id, created_by) -> UUID`,
`read_by_id -> (RolePermission, Role, Permission) | None`,
`read_by_role_id_and_permission_id -> (RolePermission, Role, Permission) | None`,
`read_by_pagination(page, limit, role_id, permission_id) ->
tuple[list[tuple[RolePermission, Role, Permission]], int]`,
`delete_by_id`, `delete_by_role_id_and_permission_id(role_id, permission_id)`.

### 5.4 `domain/contracts/utility/*` (ABC)

```python
class Password(ABC):
    @abstractmethod
    async def hash(self, password: str) -> str: ...
    @abstractmethod
    async def compare(self, stored_hash: str, password: str) -> None: ...   # raises DomainError

class Token(ABC):
    @abstractmethod
    async def generate_access(self, claims: TokenClaimsAccess) -> str: ...
    @abstractmethod
    async def validate_access(self, token: str) -> TokenClaimsAccess: ...
    @abstractmethod
    async def generate_refresh(self, claims: TokenClaimsRefresh) -> str: ...
    @abstractmethod
    async def validate_refresh(self, token: str) -> TokenClaimsRefresh: ...

class Transactor(ABC):
    @abstractmethod
    async def run(self, fn: Callable[[], Awaitable[T]]) -> T: ...
```

`Password.hash`/`compare` are `async` only for interface uniformity (bcrypt
work is offloaded with `anyio.to_thread.run_sync`). `Token` methods are
`async` for the same reason; JWT work is synchronous under the hood.

### 5.5 `domain/usecases/*` (ABC + request/result dataclasses)

Port the Go `domainusecases*` files. Request/result types are
`@dataclass(frozen=True, slots=True)`. Examples:

```python
# auth/session.py
@dataclass(frozen=True, slots=True)
class LoginRequest:  username: str; password: str
@dataclass(frozen=True, slots=True)
class RefreshRequest: refresh_token: str
@dataclass(frozen=True, slots=True)
class LoginResult:
    user: User; role: Role; permissions: list[Permission]
    access_token: str; refresh_token: str

class Session(ABC):
    @abstractmethod
    async def login(self, request: LoginRequest) -> LoginResult: ...
    @abstractmethod
    async def refresh(self, request: RefreshRequest) -> LoginResult: ...
```

`admin/role_management.py` additionally declares `AssignRolePermissionRequest`,
`RevokeRolePermissionRequest`, `ReadRolePermissionByIdRequest`,
`ReadRolePermissionByRoleIdAndPermissionIdRequest`,
`ReadRolePermissionsByPaginationRequest`, `RolePermissionResult`,
`SetDefaultRoleRequest`, mirroring the Go file. `admin/user_management.py`
declares `ResetUserPasswordRequest`. Every request that carries an actor
carries `created_by`/`updated_by`/`deleted_by: UUID | None`.

## 6. Application layer

### 6.1 `application/shared/validation.py`

Direct port of `internal/application/shared/validation.go` (only the
in-scope validators). Each raises `DomainError(msg, ErrorType.VALIDATION)`.

| Function | Pattern | Min | Max |
|---|---|---|---|
| `required_person_name` / `optional_person_name` | `^[A-Za-z0-9' -]+$` | 1 | 128 |
| `required_username` / `optional_username` | `^[A-Za-z0-9_-]+$` | 3 | 128 |
| `required_role_name` / `optional_role_name` | `^[A-Za-z0-9_-]+$` | 3 | 128 |
| `required_permission_name` / `optional_permission_name` | `^[A-Za-z0-9/_:-]+$` | 3 | 128 |
| `required_password` | `^[\x21-\x7E]+$` | 8 | 72 |

Values are `.strip()`ed before validation (except password). `optional_*`
returns `None` when the input is `None`.

### 6.2 Usecase implementations

One class per module, constructor-injected with the **repository contract
interfaces directly** (no `repocache`), plus `Password`/`Token`/`Leveled`
as needed. Behaviour is a line-for-line port of the corresponding
`internal/application/**/usecase.go`. Each method has a `TAG` constant
(`"admin/user_management/Create"` etc.) used in `await logger.error(...)`.

- `admin/permission_management` — deps: `PermissionRepository`, `Leveled`.
  `create` validates name; `update_by_id` validates optional name;
  read/delete pass through.
- `admin/role_management` — deps: `RoleRepository`, `RolePermissionRepository`,
  `Leveled`. `create`/`update_by_id` validate role name; `set_default_role`
  calls `role.update_by_id(is_default=True)`; `assign_permission` →
  `role_permission.create`; `revoke_permission` →
  `role_permission.delete_by_role_id_and_permission_id`; the
  `read_role_permission_*` methods wrap the repo tuples into
  `RolePermissionResult`.
- `admin/user_management` — deps: `UserRepository`, `Password`, `Leveled`.
  `create` validates name+username+password, hashes, inserts;
  `update_by_id` validates optional name+username; `reset_password`
  validates + hashes + `update_by_id(password_hash=...)`.
- `auth/session` — deps: `UserRepository`, `RoleRepository`, `Password`,
  `Token`, `Leveled`. `login`: `read_by_username` → `password.compare`
  → `_build_login_result`. `refresh`: `token.validate_refresh` →
  `read_by_id` → `_build_login_result`. `_build_login_result`:
  `role.read_by_id`, `user.read_permissions`, build
  `TokenClaimsAccess(permissions=[p.name ...])`, `generate_access` +
  `generate_refresh`.
- `profile/me` — deps: `UserRepository`, `Leveled`. `get_profile` →
  `read_by_id`; `get_permissions` → `read_permissions`.
- `profile/account` — deps: `UserRepository`, `Leveled`. `update_profile`
  validates optional name+username, `update_by_id(name, bio, username,
  updated_by)`.
- `profile/security` — deps: `UserRepository`, `Password`, `Leveled`.
  `change_password`: `read_by_id` → `password.compare(current)` →
  `required_password(new)` → `hash` → `update_by_id(password_hash=...)`.

## 7. Infrastructure layer

### 7.1 `repository/database/orm.py`

`class Base(DeclarativeBase)`. Table models `PermissionORM` (`permissions`),
`RoleORM` (`roles`), `RolePermissionORM` (`role_permission`), `UserORM`
(`users`). Column mapping:

- `id: Mapped[uuid.UUID]` — `PG_UUID(as_uuid=True)`, `primary_key=True`,
  `server_default=text("gen_random_uuid()")`.
- `preferences: Mapped[dict]` — `JSONB`, `server_default=text("'{}'::jsonb")`.
- `created_at: Mapped[datetime]` — `TIMESTAMP(timezone=True)`,
  `server_default=func.now()`.
- `updated_at/deleted_at: Mapped[datetime | None]`.
- `created_by/updated_by/deleted_by: Mapped[uuid.UUID | None]`.
- `users.role_id` → `ForeignKey("roles.id")`.
- `role_permission.role_id/permission_id` →
  `ForeignKey(..., ondelete="CASCADE")`.

These ORM classes stay inside `infrastructure`. Repositories translate them
to/from `domain.models` dataclasses (`repository/shared/mappers.py`).
Requirement [4] is satisfied by this hard separation: `domain` never
imports `orm.py`.

### 7.2 `repository/database/session.py`

```python
_engine: AsyncEngine = create_async_engine(settings.postgres_dsn,
                                           pool_size=settings.postgres_pool_size,
                                           pool_pre_ping=True)
_sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
_current_session: ContextVar[AsyncSession | None] = ContextVar("current_session", default=None)

@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    existing = _current_session.get()
    if existing is not None:
        yield existing                     # enlisted in an active Transactor.run scope
        return
    async with _sessionmaker() as session: # standalone: one session per call
        yield session
```

`driver.py` owns creation of the engine/sessionmaker (passed in), so the
module exposes factory functions rather than import-time globals — the
above is illustrative.

### 7.3 `utility/transactor/sqlalchemy.py`

```python
class SqlAlchemyTransactor(Transactor):
    def __init__(self, sessionmaker, current_session_var): ...
    async def run(self, fn):
        async with self._sessionmaker() as session:
            token = self._var.set(session)
            try:
                async with session.begin():
                    return await fn()
            finally:
                self._var.reset(token)
```

Repositories call `get_session()`; when a `run(...)` scope is active they
receive that transaction's session and their writes commit/rollback with
it. Used by `RoleManagement.set_default_role` semantics if a
"unset other defaults then set this one" transaction is required, and by
the seeder.

> Note: the Go `roles` schema has a partial unique index
> `uq_roles_is_default_true WHERE is_default = TRUE`, so setting a new
> default must clear the previous one in the same transaction. The
> `RoleRepository.update_by_id` implementation performs the
> `UPDATE roles SET is_default = false WHERE is_default AND id <> :id`
> then the target update, wrapped in `get_session()`'s transaction (or the
> ambient `Transactor` scope). This mirrors `role/postgres.go`.

### 7.4 `repository/{entity}/{repository.py,queries.py}`

`queries.py` builds statements with SQLAlchemy Core against the ORM tables
(`select()`, `insert().returning()`, `update()`), the squirrel analogue:

- `build_create(...)` — insert only the non-None columns, `.returning(id)`.
- `build_read_by_id(id)` / `build_read_by_name(name)` /
  `build_read_default()` — `where(deleted_at.is_(None))`.
- `build_read_by_pagination(page, limit, search, ...)` — returns
  `(count_stmt, rows_stmt)`; `rows_stmt` adds
  `order_by(created_at.desc(), id.asc())`, `limit`, `offset`.
- `build_update_by_id(id, **fields)` — `.values(**provided)` +
  `updated_at=func.now()`, `updated_by=...`, `where(deleted_at.is_(None))`.
- `build_delete_by_id(id, deleted_by)` — soft delete:
  `update().values(deleted_at=func.now(), deleted_by=...)`.

`user/queries.py` adds `build_read_permissions(user_id)` — join
`users → roles → role_permission → permissions`, all `deleted_at IS NULL`,
`order_by(permissions.created_at.desc(), permissions.id.asc())`. Its
`build_read_by_pagination` LEFT JOINs `roles` for `role_name`, and searches
`users.name ILIKE :p OR users.username ILIKE :p`.

`role_permission/queries.py` has a `base_read()` joined select returning
rp + role + permission columns; delete-by-pair and delete-by-id are hard
`DELETE` (no `deleted_at` column on this table — matches Go).

`repository.py` executes via `get_session()`, maps rows with
`shared/mappers.py`, and wraps DB exceptions with
`shared/errors.map_db_error(...)`.

### 7.5 `repository/shared/errors.py`

```python
@dataclass(frozen=True)
class ConflictMatch: contains: str; type: ErrorType

def map_db_error(message: str, exc: Exception, *conflicts: ConflictMatch) -> DomainError:
    # NoResultFound / DoesNotExist    -> NOT_FOUND
    # IntegrityError w/ asyncpg cause:
    #   UniqueViolationError (23505)  -> first ConflictMatch whose `contains`
    #                                    is in constraint_name, else CONFLICT
    #   ForeignKeyViolationError (23503) -> CONFLICT
    #   NotNullViolation / DataError / InvalidTextRepresentation
    #     (23502 / 22001 / 22P02)     -> VALIDATION
    # else                            -> UNKNOWN
```

Call sites pass the specific conflict targets, e.g. user create passes
`ConflictMatch("username", ErrorType.USERNAME_EXISTS)`; role create passes
`ConflictMatch("name", ErrorType.ROLE_NAME_EXISTS)`; role_permission create
passes `ConflictMatch("role_permission", ErrorType.ROLE_PERMISSION_EXISTS)`.

`query.py`: `normalize_limit(limit) -> int` (0 if negative),
`normalize_offset(page, limit) -> int` (0 if page ≤ 1 or limit ≤ 0),
`search_pattern(search) -> str | None` (`f"%{search}%"` or `None`).

### 7.6 `utility/password/bcrypt.py`

`BcryptPassword(Password)` — `bcrypt` package. Cost from settings, clamped
to `[4, 31]` (fallback `12`). `hash` → `bcrypt.hashpw` under
`anyio.to_thread.run_sync`; `compare` → `bcrypt.checkpw`, raising
`DomainError("password does not match", UNAUTHORIZED)` on mismatch,
`DomainError(..., FAILURE)` on any other error. Passwords are pre-validated
≤ 72 bytes by `application/shared`.

### 7.7 `utility/token/jwt.py`

`JwtToken(Token)` — `PyJWT`, `HS256`. Constructor: `access_secret`,
`refresh_secret`, `access_ttl: timedelta`, `refresh_ttl: timedelta`,
`now: Callable[[], datetime] = lambda: datetime.now(tz=UTC)`.

- `generate_access`: payload = `{user_id, name, username, role,
  permissions, sub: str(user_id), iat, nbf, exp}` (uuid serialised as str).
- `validate_access`: `jwt.decode(..., algorithms=["HS256"])`;
  `ExpiredSignatureError` → `DomainError(TOKEN_EXPIRED)`; any other
  `InvalidTokenError` → `DomainError(TOKEN_INVALID)`; rebuild
  `TokenClaimsAccess`, parsing `user_id` from the claim or `sub`.
- refresh pair analogous with `{user_id, sub, iat, nbf, exp}`.

### 7.8 `logger/leveled/normalize.py`

`normalize_meta(meta: dict) -> dict` — replace any `Exception` value with
`str(value)` (port of `normalize.go`; avoids `{}` in JSON logs). `plain.py`
and `json.py` call it in `_log(...)` before formatting. No other change to
the existing files.

## 8. Presentation layer (FastAPI)

### 8.1 `routers/__init__.py`

`api_router(container) -> APIRouter` builds the tree under prefix `/api`
(mirrors `route.go`):

- `GET /api/version` → `version.router`
- `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh` — **public**
- `/api/v1/admin/...` and `/api/v1/profile/...` — every route carries
  `dependencies=[Depends(get_access_claims), Depends(require("resource:action"))]`

Route table (method, path, permission) — ported from `routeAdmin` /
`routeProfile` / `routeAuthPublic`:

```
POST   /api/v1/auth/login                                        (public)
POST   /api/v1/auth/refresh                                      (public)

GET    /api/v1/profile                        profile:get
GET    /api/v1/profile/permissions            profile:get
PATCH  /api/v1/profile                        profile:set
PATCH  /api/v1/profile/password               profile_security:set

GET    /api/v1/admin/permissions              permission:get
POST   /api/v1/admin/permissions              permission:add
GET    /api/v1/admin/permissions/by-name/{name}   permission:get
GET    /api/v1/admin/permissions/{id}         permission:get
PATCH  /api/v1/admin/permissions/{id}         permission:set
DELETE /api/v1/admin/permissions/{id}         permission:remove

GET    /api/v1/admin/roles                    role:get
POST   /api/v1/admin/roles                    role:add
GET    /api/v1/admin/roles/default            role:get
GET    /api/v1/admin/roles/by-name/{name}     role:get
GET    /api/v1/admin/roles/{id}/permissions   role_permission:get
PATCH  /api/v1/admin/roles/{id}/default       role:set
GET    /api/v1/admin/roles/{id}               role:get
PATCH  /api/v1/admin/roles/{id}               role:set
DELETE /api/v1/admin/roles/{id}               role:remove
POST   /api/v1/admin/roles/{role_id}/permissions/{permission_id}    role_permission:add
DELETE /api/v1/admin/roles/{role_id}/permissions/{permission_id}    role_permission:remove
GET    /api/v1/admin/role-permissions         role_permission:get
GET    /api/v1/admin/role-permissions/by-pair role_permission:get
GET    /api/v1/admin/role-permissions/{id}    role_permission:get

GET    /api/v1/admin/users                    user:get
POST   /api/v1/admin/users                    user:add
GET    /api/v1/admin/users/by-username/{username}   user:get
GET    /api/v1/admin/users/{id}/permissions   user_permission:get
PATCH  /api/v1/admin/users/{id}/password      user_password:set
GET    /api/v1/admin/users/{id}               user:get
PATCH  /api/v1/admin/users/{id}               user:set
DELETE /api/v1/admin/users/{id}               user:remove
```

Static segments (`/default`, `/by-name/...`, `/by-pair`, `/{id}/permissions`,
`/{id}/password`, `/{id}/default`) are registered before the bare
`/{id}` routes, matching the Go ordering.

### 8.2 `dependencies/`

- `auth.get_access_claims(authorization: str | None = Header(None),
  token: Token = Depends(get_token)) -> TokenClaimsAccess` — extract the
  Bearer value (accepts raw token or `Bearer <token>`), `validate_access`;
  raise `DomainError("authorization is required", UNAUTHORIZED)` if absent.
- `auth.get_actor_id(claims = Depends(get_access_claims)) -> UUID` —
  `claims.user_id`.
- `permission.require(*required: str)` — returns a dependency that reads
  `Depends(get_access_claims)` and raises
  `DomainError("you do not have permission to perform this action",
  FORBIDDEN)` unless `set(required) <= set(claims.permissions)`.
- `container.py` — `get_<usecase>(request: Request)` accessors reading
  `request.app.state.application`, one per usecase, used as `Depends`.

### 8.3 `schemas/`

- `request.py` — Pydantic v2 models: `AuthLoginRequest{username,password}`,
  `AuthRefreshRequest{refresh_token}`, `PermissionPostRequest{name,
  description?}`, `PermissionPatchRequest{name?,description?}`,
  `RolePostRequest`, `RolePatchRequest`, `UserPostRequest{role_id,name,
  bio?,username,password}`, `UserPatchRequest{role_id?,name?,bio?,
  username?}`, `UserPasswordPatchRequest{password}`,
  `ProfilePatchRequest{name?,bio?,username?}`,
  `ProfilePasswordPatchRequest{current_password,new_password}`.
- `response.py` — `AuditResponse`, `PermissionResponse`, `RoleResponse`,
  `UserResponse` (+ optional `role_name`), `RolePermissionResponse`,
  `RolePermissionDetailResponse`, `LoginResponse{user,role,permissions,
  access_token,refresh_token}`, `IdResponse{id}`, `ErrorResponse{error,
  message}`, `PageResponse{page,limit,total_items}`,
  `PageDataResponse[T]{data,page}`. Plus mapper functions
  `permission_response(Permission) -> PermissionResponse`, etc.
  `preferences` empty → `{}` (port of `NormalizeJSON`). UUIDs serialised as
  strings; `nil`/`None` UUIDs omitted.

### 8.4 `utils/`

- `errors.py` — `DOMAIN_STATUS: dict[ErrorType, tuple[int, str, str]]`
  (status, title, override-message) ported from `error.go`
  (`NOT_FOUND`→404 "Not Found"; `USERNAME_EXISTS`→409 "Already Exists"
  "This username is already taken."; `ROLE_NAME_EXISTS`/`PERMISSION_NAME_EXISTS`/
  `ROLE_PERMISSION_EXISTS`/`CONFLICT`→409; `VALIDATION`/`BAD_ARGS`→400
  "Invalid Format"; `BAD_STATE`→412; `FORBIDDEN`→403; `UNAUTHORIZED`→401;
  `TOKEN_EXPIRED`/`TOKEN_INVALID`→401 with friendly copy; `TIMEOUT`→504;
  `UNIMPLEMENTED`→501; `FAILURE`/`UNKNOWN`→500 generic). A registered
  `@app.exception_handler(DomainError)` returns
  `ErrorResponse(error=title, message=override or err.message)`. A
  catch-all `Exception` handler → 500 generic. FastAPI
  `RequestValidationError` → 400 "Invalid Format".
- `pagination.py` — `PaginationParams` dependency: `page` (default 1, ≥1),
  `limit` (default 10, 1–100), `search: str | None`. `page_response(params,
  total) -> PageResponse`.

### 8.5 Router functions

Thin: parse path/query/body (Pydantic + typed path params give UUID/int
parsing for free), call the injected usecase, map the result. Status codes
match Go: create → `201` + `IdResponse`; update/delete/assign-less →
`204`; reads → `200`. Missing single-item read (`None`) → raise
`DomainError("<x> not found", NOT_FOUND)`.

## 9. Composition & entrypoint

- `composition/main/driver.py` — `build_driver(settings) -> Driver`:
  create `AsyncEngine` + `async_sessionmaker` + the `current_session`
  `ContextVar`; select logger backend (`BasicLeveledLogging` /
  `JsonLeveledLogging`) from `settings.logger_format` + `logger_level`.
- `composition/main/infrastructure.py` — `build_infrastructure(driver,
  settings) -> Infrastructure` (frozen dataclass of contract-typed fields):
  the four repositories, `SqlAlchemyTransactor`, `BcryptPassword`,
  `JwtToken`, `logger`.
- `composition/main/application.py` — `build_application(infra) ->
  Application`: the eight usecase instances.
- `composition/main/presentation.py` — `build_app(application, infra,
  settings) -> FastAPI`: instantiate `FastAPI(title=..., docs_url="/api/docs",
  openapi_url="/api/openapi.json")`; add `CORSMiddleware`
  (`allow_origins=settings.http_cors_allowed_origins`, methods
  `GET/HEAD/POST/PATCH/PUT/DELETE/OPTIONS`, headers `Accept, Authorization,
  Content-Type, Origin, X-Requested-With`); register the `DomainError` /
  `Exception` / `RequestValidationError` handlers; `app.state.application =
  application`; `app.include_router(api_router(application))`.
- `composition/main/launcher.py` — `create_app() -> FastAPI` runs
  `Settings()` → driver → infra → app → presentation and returns the app.
  `run()` calls `uvicorn.run("tarakdingdung.main:app", host, port)` (or
  programmatic `Server` with SIGINT/SIGTERM handling).
- `src/tarakdingdung/main.py` — `from tarakdingdung.composition.main.launcher
  import create_app; app = create_app()`.

Run: `uvicorn tarakdingdung.main:app --host 0.0.0.0 --port 8080`.

## 10. Migrations (Alembic)

`backend/alembic.ini` + `backend/migrations/env.py` (async: builds an
`AsyncEngine` from `Settings().postgres_dsn`, `run_sync` for the migration
context, `target_metadata = Base.metadata`). Revisions are **hand-written**
(no `--autogenerate`) so Postgres-specific DDL is exact. `op.execute(...)`
for index/extension SQL Alembic ops can't express.

| # | id | up | down |
|---|---|---|---|
| 1 | `0001_extensions` | `CREATE EXTENSION IF NOT EXISTS pgcrypto`; `... pg_trgm` | `DROP EXTENSION IF EXISTS pg_trgm`; `... pgcrypto` |
| 2 | `0002_permissions` | `permissions` table; `CREATE INDEX idx_permissions_name_trgm ... USING GIN (name gin_trgm_ops)`; `idx_permissions_deleted_at` | drop table |
| 3 | `0003_roles` | `roles` table; trigram GIN on `name`; `CREATE UNIQUE INDEX uq_roles_is_default_true ON roles (is_default) WHERE is_default = TRUE`; `idx_roles_deleted_at` | drop table |
| 4 | `0004_role_permission` | `role_permission` table; FKs `ON DELETE CASCADE`; `CONSTRAINT uq_role_permission_role_id_permission_id UNIQUE (role_id, permission_id)`; `idx_role_permission_role_id`, `idx_role_permission_permission_id` | drop table |
| 5 | `0005_users` | `users` table; FK `role_id → roles(id)`; `idx_users_role_id`; trigram GIN on `name` and `username`; `idx_users_deleted_at` | drop table |
| 6 | `0006_soft_delete_partial_unique` | drop plain `UNIQUE` on `permissions.name`, `roles.name`, `users.username`; `CREATE UNIQUE INDEX uq_<t>_<col> ON <t> (<col>) WHERE deleted_at IS NULL` | reverse |

Column definitions replicate the Go DDL exactly (`preferences JSONB NOT
NULL DEFAULT '{}'::jsonb`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`,
`id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `bio TEXT NOT NULL DEFAULT
''`, etc.).

Integration test: `alembic upgrade head` then `alembic downgrade base` on a
`testcontainers` Postgres, asserting a clean round-trip.

## 11. Seeder

`composition/seeder/launcher.py` — `run()` (invoked by `python -m
tarakdingdung.composition.seeder`). Reads `backend/database/seeder/{permission,
role,user}.json`. All work wrapped in one `Transactor.run(...)`. Idempotent:
upsert permissions by `name`, roles by `name`, `role_permission` by
`(role_id, permission_id)`, users by `username` (skip if present).

`permission.json` — in-scope permissions only:

```
profile:get, profile:set, profile_security:set,
permission:get, permission:add, permission:set, permission:remove,
role:get, role:add, role:set, role:remove,
role_permission:get, role_permission:add, role_permission:remove,
user:get, user:add, user:set, user:remove, user_permission:get, user_password:set
```

`role.json`:

- `super` — all of the above; `is_default = false`.
- `admin` — `profile:*`, `user:*`, `user_permission:get`,
  `user_password:set`; `is_default = false`.
- `user` — `profile:get`, `profile:set`, `profile_security:set`;
  `is_default = true`.

`user.json` — `super` / `admin` / `user`, each `password` defaulting to a
dev value, overridable via `TRDD_BE_SEED_SUPER_PASSWORD` etc. Passwords
bcrypt-hashed via the same `BcryptPassword` used by the app.

## 12. Config (`config/settings.py`)

`class Settings(BaseSettings)` with
`model_config = SettingsConfigDict(env_prefix="TRDD_BE_", env_file=".env",
extra="ignore")`:

| Field | Env | Default |
|---|---|---|
| `app_name` | `TRDD_BE_APP_NAME` | `tarakdingdung` |
| `app_version` | `TRDD_BE_APP_VERSION` | `v0.1.0-dev.1` |
| `logger_format` | `TRDD_BE_LOGGER_FORMAT` | `json` |
| `logger_level` | `TRDD_BE_LOGGER_LEVEL` | `INFO` |
| `postgres_host` | `TRDD_BE_POSTGRES_HOST` | `127.0.0.1` |
| `postgres_port` | `TRDD_BE_POSTGRES_PORT` | `5432` |
| `postgres_username` | `TRDD_BE_POSTGRES_USERNAME` | `postgres` |
| `postgres_password` | `TRDD_BE_POSTGRES_PASSWORD` | `postgres` |
| `postgres_database` | `TRDD_BE_POSTGRES_DATABASE` | `tarakdingdung` |
| `postgres_ssl_mode` | `TRDD_BE_POSTGRES_SSL_MODE` | `disable` |
| `postgres_pool_size` | `TRDD_BE_POSTGRES_POOL_SIZE` | `20` |
| `http_host` | `TRDD_BE_HTTP_HOST` | `0.0.0.0` |
| `http_port` | `TRDD_BE_HTTP_PORT` | `8080` |
| `http_cors_allowed_origins` | `TRDD_BE_HTTP_CORS_ALLOWED_ORIGINS` | `["*"]` |
| `token_access_secret` | `TRDD_BE_TOKEN_ACCESS_SECRET` | `tarakdingdung-access-secret` |
| `token_refresh_secret` | `TRDD_BE_TOKEN_REFRESH_SECRET` | `tarakdingdung-refresh-secret` |
| `token_access_ttl_seconds` | `TRDD_BE_TOKEN_ACCESS_TTL_SECONDS` | `900` |
| `token_refresh_ttl_seconds` | `TRDD_BE_TOKEN_REFRESH_TTL_SECONDS` | `86400` |
| `password_bcrypt_cost` | `TRDD_BE_PASSWORD_BCRYPT_COST` | `12` |
| `seed_super_password` / `seed_admin_password` / `seed_user_password` | `TRDD_BE_SEED_*` | `changeme12345` |

`postgres_dsn` is a computed property:
`postgresql+asyncpg://user:pass@host:port/db`. `http_cors_allowed_origins`
parsed from comma-separated string or JSON list. `.env.example` lists every
var with its default.

## 13. Dependencies

Installed into the existing `backend/.venv`, then
`backend/.venv/bin/pip freeze > backend/requirements.txt`. `pyproject.toml`
uses the src layout (`[tool.setuptools.packages.find] where = ["src"]`) so
`pip install -e backend/` makes `tarakdingdung` importable for tests.

- Runtime: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`,
  `asyncpg`, `alembic`, `pydantic`, `pydantic-settings`, `pyjwt`, `bcrypt`.
- Dev/test: `pytest`, `pytest-asyncio`, `httpx`, `testcontainers[postgres]`.

`requirements.txt` is the full freeze (runtime + dev, single venv, as
instructed). `pyproject.toml` records the direct deps under `[project]`
and `[project.optional-dependencies].dev`.

## 14. Testing (TDD)

`pyproject.toml` → `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`,
`testpaths = ["backend/tests"]`.

### `tests/unit/` — fakes, no DB

In-memory fakes implement the repository ABCs (dict-backed). Cover:

- `application/shared/validation` — every `required_*`/`optional_*` accept
  and reject case (patterns, length bounds, strip, `None` passthrough).
- `auth/session.login` — unknown username → `NOT_FOUND`; wrong password →
  `UNAUTHORIZED`; success → `LoginResult` with role, permission list, and
  `TokenClaimsAccess.permissions == [names]`; tokens validate back.
- `auth/session.refresh` — invalid/expired token → `TOKEN_*`; success
  re-mints.
- `admin/user_management` — create hashes + inserts; duplicate username
  surfaced as `USERNAME_EXISTS`; `reset_password` re-hashes.
- `admin/role_management` — `assign_permission` duplicate →
  `ROLE_PERMISSION_EXISTS`; `set_default_role` calls `update_by_id(
  is_default=True)`; `read_role_permission_*` wrap into
  `RolePermissionResult`.
- `profile/security.change_password` — wrong current password →
  `UNAUTHORIZED`; weak new password → `VALIDATION`; success re-hashes.
- `utility/bcrypt` + `utility/jwt` — round-trip, tamper, expiry (inject
  `now`).

### `tests/integration/` — `testcontainers` Postgres

Session-scoped `PostgresContainer`; `alembic upgrade head` once; each test
runs in a transaction rolled back at teardown. Cover, per repository:
create → read-by-id/name → paginate (with/without search, ordering) →
update (partial) → soft-delete → name reuse after delete → conflict
mapping (unique, FK, not-null). Plus: `user.read_permissions` join
correctness; `role.update_by_id(is_default=True)` clears the prior default
in one transaction; `SqlAlchemyTransactor.run` commits on success and rolls
back on exception; Alembic `upgrade head` → `downgrade base` round-trip.

### `tests/e2e/` — `httpx.AsyncClient(transport=ASGITransport(app))`

Composed app against a `testcontainers` DB with the seeder run first.
Cover: `POST /api/v1/auth/login` (bad creds → 401, ok → tokens);
missing / invalid bearer → 401; `super` token reaches every admin route;
`user` token → 403 on admin routes, 200 on `/api/v1/profile`; full RBAC
round-trip (super creates role + permission, assigns, creates a user with
that role; the new user logs in and its `/api/v1/profile/permissions`
reflects the assignment); pagination envelope shape; `DomainError` → the
mapped `{error, message}` body and status.

## 15. Deviations from `nusapala-things` (intentional)

1. **No `repocache`/`cache` layer.** Redis is out of scope; usecases depend
   on `domain/contracts/repository/*` directly. The Go `domainusecasesrepocache.*`
   pass-through interfaces are not ported.
2. **Presentation uses FastAPI-idiomatic names** (`routers/`,
   `dependencies/`, `schemas/`, `utils/`) instead of `handler/`,
   `middleware/`, `request/`, `response/`, `route/`. FastAPI has no
   per-route middleware; `route.go`'s handler-interface indirection is
   replaced by `Depends`-injected router functions.
3. **`database/` lives under `infrastructure/repository/database/`** and the
   **transactor under `infrastructure/utility/transactor/`** (next to
   `password/` and `token/`) for layout consistency — rather than the Go
   `pkg/pgxdt` standalone package and `infrastructure/utility/transactor`.
4. **Alembic** replaces `golang-migrate`; **FastAPI OpenAPI** replaces
   `swaggo`; **`uvicorn`** replaces the Echo server; **`testcontainers`**
   replaces the Go test harness.
5. **`timescaledb`** extension dropped (telemetry out of scope).
6. Logger contract kept exactly as the existing Python skeleton defines it
   (`async`, `(tag, message, meta)`), which differs from the Go signature
   (`ctx, tag, message, meta`). Per requirement [6].

## 16. Build milestones

1. **Scaffolding** — `backend/pyproject.toml`, `config/settings.py`,
   `.env.example`; install deps into `.venv`; `pip freeze >
   backend/requirements.txt`; pytest config; `tests/conftest.py` skeleton.
2. **Domain** — `models/{error,permission,role,role_permission,user,token_claims}.py`;
   `contracts/repository/*`; `contracts/utility/*`; `usecases/{admin,auth,profile}/*`.
3. **Infra / database** — `repository/database/{orm,session}.py`;
   `utility/transactor/sqlalchemy.py`; Alembic init + 6 revisions;
   integration test: migrate up/down.
4. **Infra / repositories** — `shared/{errors,query,mappers}.py`; then
   `permission/`, `role/`, `role_permission/`, `user/` (`queries.py` +
   `repository.py`), each integration-tested (TDD).
5. **Infra / utilities** — `password/bcrypt.py`, `token/jwt.py`,
   `logger/normalize.py` (+ wire into `plain.py`/`json.py`); unit-tested.
6. **Application / shared** — `validation.py` (TDD).
7. **Application / admin** — `permission_management`, `role_management`,
   `user_management` usecases (TDD with fakes).
8. **Application / auth** — `session` usecase (TDD).
9. **Application / profile** — `me`, `account`, `security` usecases (TDD).
10. **Presentation / plumbing** — `schemas/{request,response}.py`;
    `utils/{errors,pagination}.py`; `dependencies/{auth,permission,container}.py`.
11. **Presentation / routers** — `version`, `auth`, `admin`, `profile`;
    `routers/__init__.py` aggregator.
12. **Composition** — `main/{driver,infrastructure,application,presentation,launcher}.py`;
    `src/tarakdingdung/main.py`.
13. **Seeder** — `database/seeder/*.json`; `composition/seeder/launcher.py`.
14. **E2E** — full-stack tests through `create_app()` + seeded DB.
15. **Docs & finalise** — `backend/AGENTS.md`, `backend/README.md`; final
    `pip freeze`; `.env.example` review.
