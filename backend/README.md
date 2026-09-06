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
# apply migrations (reads TRDD_BE_POSTGRES_* from backend/.env)
backend/.venv/bin/python -c "from tarakdingdung.infrastructure.repository.database.migrations import upgrade_to_head; from tarakdingdung.config.settings import Settings; upgrade_to_head(Settings().postgres_dsn)"

backend/.venv/bin/tarakdingdung-seed        # baseline permissions/roles/users
```

## Run

```bash
backend/.venv/bin/tarakdingdung-serve        # uvicorn on TRDD_BE_HTTP_HOST:PORT
# OpenAPI docs: http://localhost:8080/api/docs
```

## Test

```bash
backend/.venv/bin/pytest backend/tests           # full suite; needs Docker for integration/e2e

# no-Docker subset (domain, application, presentation, infrastructure, settings):
backend/.venv/bin/pytest backend/tests/domain backend/tests/application \
    backend/tests/presentation backend/tests/infrastructure \
    backend/tests/test_settings.py -q
```

Default seeded logins (override via `TRDD_BE_SEED_*`): `super` / `admin` /
`user`, password `changeme12345`.
