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
