# Backend architecture (tarakdingdung)

Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, PyJWT, bcrypt,
httpx, websockets. Two subsystems share one clean-architecture codebase:

- **RBAC/auth** — users, roles, permissions, JWT sessions. Ported from the Go
  `nusapala-things/backend`.
- **Automated crypto trading** — market-data collection, a pure algorithm
  layer, backtesting with an overfitting gate, and a live cycle against
  Indodax and Tokocrypto.

Design records, worth reading before changing the shape of anything:

| Topic | Document |
|---|---|
| RBAC port | `docs/superpowers/specs/2026-09-06-python-backend-rbac-auth-port-design.md` |
| Algorithm layer | `docs/superpowers/specs/2026-09-07-algorithm-layer-design.md` |
| Trading usecases | `docs/superpowers/specs/2026-09-07-trading-usecases-design.md` |
| Why this strategy, in what order | `docs/researches/summaries/004_Automated_Trading_Engine_Implementation_Plan.md` |
| Exchange API inventory | `docs/researches/summaries/003_Exchange_REST_API_Endpoint_Inventory.md` |

## Dependency rule

`presentation → application → domain ← infrastructure`; `composition` wires
all layers. `domain/` imports only the standard library — no SQLAlchemy, no
httpx, no numeric libraries. `presentation/` never imports `infrastructure/`.

## Sync versus async

The split is deliberate and load-bearing:

- **`domain/contracts/algorithm/*` is synchronous.** These blocks are pure
  computation — no clock, no I/O, no network. The signature says so, which is
  what makes them backtestable and what lets a backtester call them millions of
  times without event-loop overhead.
- **Everything else is `async`** because it genuinely performs I/O.

A coroutine appearing in the algorithm layer means something has acquired the
ability to reach outside its arguments; a test asserts it has not.

## Layout

### Domain

- `domain/models/` — frozen slots dataclasses plus `DomainError`/`ErrorType`.
  RBAC: `permission`, `role`, `role_permission`, `user`, `token_claims`.
  Trading: `market`, `portfolio`, `algorithm`, `performance`, `strategy`,
  `backtest`, `execution`.
- `domain/contracts/` — ABCs:
  - `repository/` — permission, role, role_permission, user, market_data,
    strategy, backtest, portfolio, order_journal.
  - `algorithm/` — the twelve pure blocks (below).
  - `api/` — exchange REST/WS clients, plus `market_source` and
    `account_source` (venue payloads → domain models).
  - `execution/executor.py` — order submission.
  - `utility/` — password, token, transactor, clock, single_flight.
  - `logger/leveled.py`.
- `domain/usecases/` — usecase ABCs with their request/result dataclasses:
  `admin/`, `auth/`, `profile/`, `trading/`.

### Application

- `application/<area>/<name>/usecase.py` — one implementation per usecase.
- `application/shared/` — `validation.py` (value rules), `intervals.py`
  (candle interval → milliseconds).
- `application/trading/backtest/simulation.py` — fill simulation for replays.

### Infrastructure

- `repository/database/` — `orm.py` (16 tables), `session.py`, `migrations.py`.
- `repository/<entity>/` — `repository.py` + `queries.py` (Core statement
  builders). `repository/shared/` — errors, mappers, query helpers, `results.py`,
  `trading.py` (domain ↔ stored representation).
- `algorithm/<block>/` — one package per contract, one implementation per file,
  plus `shared/` (numeric, statistics, ordering, weights).
- `api/{indodax,tokocrypto}/` — REST and WebSocket clients; `api/shared/`
  (rest, signing, websocket).
- `venue/{indodax,tokocrypto}/` — market and account adapters; `symbols.py`
  holds every wire-format conversion.
- `execution/paper/`, `execution/live/` — paper and per-venue live executors
  plus `router.py`.
- `utility/{password,token,transactor,clock,single_flight}/`.
- `logger/leveled/`.

### Presentation

- `http/{routers,dependencies,schemas,utils}` — FastAPI.
- `cron/{schedule.py,tasks/}` — a delivery adapter beside `http/`. Tasks
  resolve a usecase, call its single step, and log.

### Composition

- `main/{driver,infrastructure,exchanges,application,strategies,cron,presentation,launcher}.py`
- `seeder/` — `python -m tarakdingdung.composition.seeder`.
- `database/migrations/` — Alembic, hand-written, 7 revisions.
  `database/seeder/*.json` — seed data.

## The algorithm layer

Twelve pure, synchronous contracts. The live chain, each block's output being
the next one's input:

```
universe → feature → signal → allocation → risk → rebalance → order
```

Plus evaluators (`cost`, `metric`, `validation`), the `strategy` composition
seam, and `cycle` — a `CyclePlanner` that runs the whole chain.

**`CyclePlanner` exists so the backtester and the live engine cannot diverge.**
Both call it and act on the same result; written as two loops they would drift,
and a backtest that disagrees with live is worse than no backtest.

Non-obvious rules, each of which has a test:

- **`RiskRule` must be idempotent** — applying twice equals applying once — or
  a composed chain compounds its reductions.
- **The risk overlay sits outside `Strategy`**, between strategy and executor,
  because it needs a `RiskState` that `decide()` does not receive.
- **`StandardCyclePlanner` holds risk rules as a sequence, not a composite**, so
  a plan can name *which* rule halted it.
- **A halt liquidates rather than freezing**: empty weights mean hold nothing,
  so the rebalancer sells what is held.
- **Missing data is normal**, not an error — a symbol with too little history is
  omitted and the absence propagates harmlessly.
- **`OrderPlanner` returns an `OrderPlan` carrying rejections**, so an intent
  dropped for min-notional is diagnosable rather than vanished.
- **Client order ids are deterministic** — `hash(strategy_id, timestamp, symbol,
  side)` — so replaying a cycle after a crash produces ids the venue rejects as
  duplicates instead of opening a second position.

## The trading cycle

`TradingEngine.run_cycle` is one step; cadence belongs to cron. Its ordering is
the safety design, not an implementation detail:

1. load config → missing raises, disabled returns `DISABLED`
2. single-flight lock → already running returns `SKIPPED`
3. **reconcile unconfirmed orders from previous cycles, before planning**
4. read snapshot and portfolio → absent or stale returns `NO_DATA`
5. `CyclePlanner.plan(...)` — pure
6. halt → `cancel_all`, then `HALTED`
7. dry run → return without persisting
8. **persist planned orders *before* submitting**
9. submit
10. persist execution, fills, equity

**Step 8 precedes step 9** so a crash mid-submit leaves a reconcilable record
rather than orders at the venue nothing knows about. **A transport failure is
recorded `UNCONFIRMED` and never retried** — the order may already exist. **A
failed `cancel_all` during a halt escalates**: the flag persists and later
cycles re-attempt it, so the failure gets louder rather than quieter.

## Conventions

- **Repository verbs:** `create`, `read_by_id`, `read_by_<field>`,
  `read_default`, `read_permissions`, `read_by_pagination`, `update_by_id`,
  `delete_by_id`. Pagination → `(items, total)`. Single read → `T | None`.
  Trading repositories extend this only where the domain differs
  (`read_range`, `read_coverage`, `append_fills`, `read_unreconciled`).
- **Naming:** infrastructure classes carry their mechanism —
  `SqlAlchemy*Repository`, `Http*Api`, `Ws*WebSocket`, `Jwt*`, `Bcrypt*`,
  `Postgres*`.
- **`Decimal` versus `float`:** `Decimal` for anything that becomes an exchange
  field or a ledger entry — prices, quantities, fees, cash, equity. `float` for
  dimensionless statistics — features, signals, weights, Sharpe. They meet only
  in `Rebalancer`. In storage, money is `NUMERIC(38,18)` and Decimals cross into
  JSONB as **strings**; parse venue payloads through `str`, never
  `Decimal(float)`.
- **Time** is `int` epoch milliseconds, UTC, everywhere in trading — it is what
  both venues speak, and it makes a timezone bug structurally impossible.
- **`Symbol` carries its venue.** The same pair on two exchanges is two symbols;
  the price difference is the entire cross-exchange trade.
- **Validation:** per-cycle objects validate in `__post_init__`; per-row market
  data (`Candle`, `BookLevel`) does not, because it is constructed in the
  millions during a replay.
- **Errors:** raise `DomainError(message, ErrorType.X)`. HTTP mapping in
  `presentation/http/utils/errors.py` — note `VALIDATION` and `BAD_ARGS` both
  map to **400**, not 422.
- **Partial failure is returned as data**, not raised: `CollectResult.failed`,
  `SyncResult.discrepancies`, `OrderPlan.rejected`, `ExecutionResult.unconfirmed`.
  One venue being down must shrink a poll, not abort it.
- **Soft delete** on `permissions`/`roles`/`users`/`strategies`;
  `role_permission` is hard deleted.
- **Config:** `Settings` (`pydantic-settings`), env prefix `TRDD_BE_`.

## Security

- **No HTTP route executes a live cycle** — only `dry_run`. The engine is
  reachable solely from cron, and a test asserts that absence so it stays true.
- **Cron is disabled by default** (`TRDD_BE_CRON_ENABLED`). A process should not
  start trading because it booted.
- Trading permissions: `strategy:{get,add,set,remove}`, `market_data:get`,
  `backtest:{get,add}`, `portfolio:get`, `engine:run`. Admin observes and
  evaluates but cannot change what trades.
- API keys are trade-only, never withdraw, and IP-allowlisted.
- `.env` is gitignored and holds real secrets; only `.env.example` is tracked.
  `.dockerignore` keeps it out of images — compose supplies it via `env_file`.

## Testing

`pytest` with `asyncio_mode = "auto"`. **685 tests.**

- **Algorithm blocks** — no mocks, no event loop: construct, call, assert.
- **Conformance suites** (`tests/infrastructure/algorithm/conformance.py`) hold
  the invariants that belong to a *contract* rather than an implementation, and
  are parametrised over every implementation. Adding a `RiskRule`, `CostModel`,
  `Allocator`, `OrderPlanner` or `CyclePlanner` costs one line there and cannot
  regress the guarantees.
- **Usecases** — hand-written fakes in `tests/fakes/`, no mocking library. The
  fakes store real state, which is what lets the engine's write-ahead ordering
  be asserted rather than approximated.
- **Integration** — `testcontainers` Postgres, so migrations, upserts,
  `DISTINCT ON` freshness, coverage-gap detection, `NUMERIC` round-trips and
  advisory locks run against a real database. **Docker required.**

## Running

```sh
# Local
pip install -e ".[dev]" && pytest
alembic upgrade head
python -m tarakdingdung.composition.seeder
uvicorn tarakdingdung.main:app --reload

# Container — the database is external, configured through .env
docker compose up -d --build
docker compose run --rm seeder
docker compose run --rm backend pytest   # any unrecognised argv runs verbatim
```

The image installs the package **editable on purpose**: the Alembic runner and
the seeder locate their data by walking up from the package file, so
`alembic.ini` and `database/` must sit above `src/tarakdingdung`. A normal
site-packages install severs that and both fail at runtime. The entrypoint
migrates before serving, so a failed migration stops the deploy rather than
leaving a server answering against a half-applied schema.

## Status and known gaps

Built: RBAC/auth, the full exchange API surface, the algorithm layer, the seven
trading usecases, Postgres persistence, cron, HTTP, and Docker.

- **No venue adapter has run against a live exchange.** Response-shape
  assumptions in `venue/` come from the reference docs, not production traffic.
  Verifying them against the real APIs is the next thing worth doing.
- **Volatility targeting is inexpressible.** `Allocator.allocate(signals,
  portfolio)` does not receive the `FeatureSet`, so sizing by realised
  volatility needs a signature change. Deferred until a backtest shows equal
  weighting is the binding constraint.
- **Long-only is a convention, not an invariant.** `TargetWeights` permits
  negative weights so an offshore perp venue would not require reshaping the
  layer, but neither current venue supports shorting.
- **Neither venue offers a futures/perp API**, so funding-rate arbitrage and
  cash-and-carry are impossible here; v1 is spot-only.
- Storage is plain Postgres. Interfaces hide the choice, so TimescaleDB is an
  extension rather than a rewrite if volume ever justifies it.

## Deviations from the Go source

No Redis/`repocache` layer (usecases depend on repository contracts directly);
FastAPI-idiomatic presentation naming; Alembic instead of golang-migrate;
api-key auth / payload-schema / llm-config / reverse proxies are out of scope.
TLS/SSL DSN options (a `sslmode`/`ssl` parameter on the Postgres connection)
remain out of scope.
