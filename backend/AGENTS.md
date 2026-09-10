# Backend architecture (tarakdingdung)

Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, PyJWT, bcrypt,
httpx, websockets. Two subsystems share one clean-architecture codebase:

- **RBAC/auth** — users, roles, permissions, JWT sessions. Ported from the Go
  `nusapala-things/backend`.
- **LLM-driven crypto trading** — a scraper feeding a multi-agent LLM decision
  pipeline, a deterministic safety layer, and a live cycle against Indodax V2.

The design source of truth is `backend/DESIGN.md`. Read it first. Its decision
table (D1–D9) is normative: this file documents *how* those decisions are
implemented, not new decisions.

## Dependency rule

`presentation → application → domain ← infrastructure`; `composition` wires
all layers. `domain/` imports only the standard library — no SQLAlchemy, no
httpx, no numeric libraries. `presentation/` never imports `infrastructure/`.

## Sync versus async

The split is deliberate and load-bearing:

- **`domain/contracts/algorithm/*` is synchronous.** These blocks are pure
  computation — no clock, no I/O, no network, no LLM. The signature says so,
  which is what makes them backtestable and replayable millions of times
  without event-loop overhead.
- **Everything else is `async`**, including LLM calls, scraping, and trade
  execution — they genuinely perform I/O.

A coroutine appearing in the algorithm layer means something has acquired the
ability to reach outside its arguments; a test asserts it has not.

## The decision boundary (D1)

The LLM decides **what to hold** (universe membership + target weights + written
reasoning). It never touches the order path. Deterministic code owns everything
after the decision:

```
scrape → summarize → decide (LLM) → validate → risk overlay → rebalance → order
```

- **`llm/`** — prompts, the agent pipeline, schema validation.
- **`algorithm/`** — risk overlay, rebalancer (weights → orders), cost model,
  metrics, backtest fill simulation. Pure and synchronous.
- **`trade/`** — order construction, execution (paper/live), reconciliation.

There is **no `api/` contract** for specific REST calls. Exchange calls are
encapsulated inside `scrapper/` (market data) or `trade/` (trading ops) — strict
layer abstraction.

## Layout

### Domain

- `domain/models/` — frozen slots dataclasses plus `DomainError`/`ErrorType`.
  RBAC: `permission`, `role`, `role_permission`, `user`, `token_claims`.
  Trading: `symbol`, `universe`, `candle`, `market`, `portfolio_snapshot`,
  `news_article`, `news_analysis`, `news_feed`, `llm_decision`,
  `backtest_result`, `order`, `execution`, `fill`, `decision` (target weights).
- `domain/contracts/` — ABCs:
  - `repository/` — permission, role, role_permission, user, user_role, symbol,
    universe, market_data, news, news_feed, decision, backtest, portfolio,
    order_journal.
  - `llm/` — `completion.py` (provider), `agent.py` (specialist),
    `pipeline.py` (decision maker), `validation.py` (schema validator).
  - `algorithm/` — `risk.py`, `rebalance.py`, `cost.py`, `metric.py`,
    `backtest.py` (fill simulation).
  - `trade/` — `executor.py` (order submission), `exchange.py` (Indodax V2
    client), `reconciler.py`.
  - `scrapper/` — `news_source.py`, `market_source.py`.
  - `utility/` — password, token, transactor, clock, single_flight.
  - `logger/leveled.py`.
- `domain/usecases/` — usecase ABCs with request/result dataclasses: `admin/`,
  `auth/`, `profile/`, `portfolio/`, `trading/`.

### Application

- `application/<area>/<name>/usecase.py` — one implementation per usecase.
- `application/shared/` — `validation.py` (value rules), `intervals.py`
  (candle interval → milliseconds).
- `application/trading/` — `engine.py` (the decision cycle), `universe.py`,
  `backtest.py` (replay), plus per-use-case orchestrations.

### Infrastructure

- `repository/database/` — `orm.py`, `session.py`, `migrations.py`.
- `repository/<entity>/` — `repository.py` + `queries.py` (Core statement
  builders). `repository/shared/` — errors, mappers, query helpers, `results.py`.
- `llm/<provider>/` — OpenAI-compatible client (`Http*Completion`), prompt
  assembly, agent implementations, schema validation.
- `algorithm/<block>/` — one package per contract, one implementation per file,
  plus `shared/` (numeric, statistics, weights).
- `trade/indodax/` — V2 REST client; `trade/execution/paper/`, `trade/execution/live/`.
- `scrapper/indodax/` — public market-data client; `scrapper/news/` — HTTP/RSS
  fetchers.
- `utility/{password,token,transactor,clock,single_flight}/`.
- `logger/leveled/`.

### Presentation

- `http/{routers,dependencies,schemas,utils}` — FastAPI.
- `cron/{schedule.py,tasks/}` — a delivery adapter beside `http/`. Tasks resolve
  a usecase, call its single step, and log.

### Composition

- `main/{driver,infrastructure,application,strategies,cron,presentation,launcher}.py`
- `seeder/` — `python -m tarakdingdung.composition.seeder`. Idempotent
  (create-if-missing, keyed by name): RBAC from `permission/role/user.json`, plus
  a seeded universe so the engine can run paper cycles with no funds at risk.
  Promotion to LIVE is a deliberate `PATCH`, never a seed.
- `database/migrations/` — Alembic, hand-written (never autogenerated).
  `database/seeder/*.json` — seed data.

## The LLM decision pipeline (D2, D5)

Two mandatory specialists plus a coordinator:

```
market/technicals agent ─┐
news/sentiment agent   ─┼─► coordinator/trader agent ─► target weights + reasoning
risk agent (optional)  ─┘
```

Each specialist emits structured analysis (Pydantic-validated); the coordinator
emits the final decision. Input is **text + numeric only** (D5): compiled news
summaries and candle/indicator tables, never raw article firehose (D8) and never
images. Deepseek v4 pro is the default backbone, swappable via config (the
`llm/completion` contract hides the provider).

The optional risk agent produces a qualitative regime read that may *inform* the
coordinator. It is distinct from — and subordinate to — the deterministic risk
overlay, which is the hard, non-negotiable gate.

## The decision output contract (D3, D4)

The coordinator must return JSON conforming to a Pydantic `Decision` schema:
`weights` (list of `{symbol, weight}`, non-negative, sum ≤ 1.0, remainder is
cash), `reasoning` (text), `confidence` (float), plus per-agent traces.
Validation retries N times, then **holds the previous weights** (no new orders).
A decision is only actionable after it passes the schema and the risk overlay.

## The deterministic safety layer

Greenfield re-implementation of the safety principles, not the old code:

- **Risk rules are idempotent** — applying twice equals applying once, or a
  composed chain compounds its reductions.
- **The risk overlay sits between the LLM decision and the executor**, because
  it needs risk state (current drawdown, daily P&L) that the coordinator does
  not receive.
- **Risk rules are held as a sequence, not a composite**, so a plan can name
  *which* rule halted it.
- **A halt liquidates rather than freezing**: empty weights mean hold nothing,
  so the rebalancer sells what is held.
- **The rebalancer diffs current holdings vs target weights** and emits orders;
  a no-trade band suppresses noise churn.
- **Client order ids are deterministic** — `hash(universe_id, timestamp, symbol,
  side)` — so replaying a cycle after a crash produces ids the venue rejects as
  duplicates instead of opening a second position.
- **Universe expansion is LLM-proposed, code-approved (D7)**: a symbol enters the
  universe only after passing hard filters (venue lists it, liquidity floor,
  known price increment, not already rejected). Rejections are logged with
  reasons.

## The decision cycle

`TradingEngine.run_cycle` is one step; cadence belongs to cron (default daily,
configurable). Its ordering is the safety design, not an implementation detail:

1. load config → missing raises, disabled returns `DISABLED`
2. single-flight lock → already running returns `SKIPPED`
3. **reconcile unconfirmed orders from previous cycles, before planning**
4. read snapshot + portfolio → absent or stale returns `NO_DATA`
5. scrape/summarize (refresh news + candles) — partial failure is data, not an abort
6. compile context snapshot
7. run multi-agent LLM pipeline → target weights + reasoning
8. schema-validate → on failure, **hold previous weights** (no new orders)
9. deterministic risk overlay (caps, kill-switch, daily-loss halt) → may halt/liquidate
10. diff current vs target → orders (deterministic)
11. **persist `LlmDecision` + planned orders *before* submitting**
12. submit, persist execution/fills/equity

**Step 11 precedes step 12** so a crash mid-submit leaves a reconcilable record
rather than orders at the venue nothing knows about. **A transport failure is
recorded `UNCONFIRMED` and never retried** — the order may already exist. **A
failed `cancel_all` during a halt escalates**: the flag persists and later cycles
re-attempt it, so the failure gets louder rather than quieter.

## Backtesting (D6)

Backtests **replay recorded decisions** through the deterministic fill simulator
— the exact `LlmDecision` rows (context + prompt + response) are re-driven
against stored candle history with fees and slippage. There is no "re-run the
LLM on history" path; that would be non-deterministic and leak-lookahead-prone.
The backtester and the live engine share the same deterministic rebalancer and
fill model, so replay cannot disagree with what live actually did.

## Conventions

- **Repository verbs:** `create`, `read_by_id`, `read_by_<field>`,
  `read_default`, `read_permissions`, `read_by_pagination`, `update_by_id`,
  `delete_by_id`. Pagination → `(items, total)`. Single read → `T | None`.
  Trading repositories extend this only where the domain differs
  (`read_range`, `read_coverage`, `append_fills`, `read_unreconciled`,
  `read_latest_decision`).
- **Naming:** infrastructure classes carry their mechanism —
  `SqlAlchemy*Repository`, `Http*Completion`, `Http*Api`, `Ws*WebSocket`,
  `Jwt*`, `Bcrypt*`, `Postgres*`.
- **`Decimal` versus `float`:** `Decimal` for anything that becomes an exchange
  field or a ledger entry — prices, quantities, fees, cash, equity. `float` for
  dimensionless statistics — weights, confidence, Sharpe. They meet only in
  the rebalancer. In storage, money is `NUMERIC(38,18)` and Decimals cross into
  JSONB as **strings**; parse venue payloads through `str`, never
  `Decimal(float)`.
- **Time** is `int` epoch milliseconds, UTC, everywhere in trading — it makes a
  timezone bug structurally impossible.
- **`Symbol` carries its venue.** The same pair on two exchanges is two symbols.
- **Validation:** per-cycle objects validate in `__post_init__`; per-row market
  data (`Candle`) does not, because it is constructed in the millions during a
  replay.
- **Errors:** raise `DomainError(message, ErrorType.X)`. HTTP mapping in
  `presentation/http/utils/errors.py` — `VALIDATION` and `BAD_ARGS` both map to
  **400**, not 422.
- **Partial failure is returned as data**, not raised: `CollectResult.failed`,
  `DecisionResult.hold`, `OrderPlan.rejected`, `ExecutionResult.unconfirmed`.
  One source being down must shrink a scrape, not abort it.
- **Soft delete** on `permissions`/`roles`/`users`; `role_permission` is hard
  deleted.
- **Config:** `Settings` (`pydantic-settings`), env prefix `TRDD_BE_`.

## Security

- **No HTTP route executes a live cycle** — only `dry_run`. The engine is
  reachable solely from cron, and a test asserts that absence so it stays true.
- **Cron is disabled by default** (`TRDD_BE_CRON_ENABLED`). A process should not
  start trading because it booted.
- Trading permissions: `universe:{get,add,set,remove}`, `market_data:get`,
  `backtest:{get,add}`, `portfolio:get`, `decision:get`, `engine:run`. Admin
  observes and evaluates but cannot change what trades.
- API keys are trade-only, never withdraw, and IP-allowlisted.
- LLM API key and exchange keys live in `.env`; `.env` is gitignored, only
  `.env.example` is tracked.
- Deterministic validation + risk overlay are the final gates before any order;
  LLM output is never trusted raw.

## Testing

`pytest` with `asyncio_mode = "auto"`. Run `pytest -q` for the current count.

- **Algorithm blocks** — no mocks, no event loop: construct, call, assert.
- **Conformance suites** (`tests/infrastructure/algorithm/conformance.py`) hold
  the invariants that belong to a *contract* rather than an implementation, and
  are parametrised over every implementation. Adding a `RiskRule`, `CostModel`
  or `Rebalancer` costs one line there and cannot regress the guarantees.
- **Schema validation** — fuzz malformed LLM outputs; assert hold-on-fail.
- **Usecases** — hand-written fakes in `tests/fakes/`, no mocking library. The
  fakes store real state, which is what lets the engine's write-ahead ordering
  be asserted rather than approximated.
- **LLM pipeline** — a fake completion provider (deterministic canned responses)
  drives the agents; no network in unit tests.
- **Replay backtest** — recorded decisions replay through the fill sim.
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

## Status and known gaps

Built: design fixated; this document. The codebase is being rebuilt greenfield
from this spec.

- **No venue adapter has run against a live exchange.** Response-shape
  assumptions in `trade/indodax/` come from the reference docs, not production
  traffic. Verifying them against the real API is the next thing worth doing.
- **Long-only is a convention, not an invariant.** `Decision.weights` permits
  zero-or-positive weights only; a short-capable venue would extend the schema,
  not reshape the layer.
- **Cadence default is daily**, configurable; the research says weekly rebalancing
  was the best LLM result — revisit once the pipeline is live.
- **Token/latency budget** per decision is configurable and sized once the
  provider is fixed.
- **News source allowlist** is seeded in the `news_feeds` table from
  `database/seeder/news_sources.json` (verified RSS feeds; enable/disable per row).
- Storage is plain Postgres. Interfaces hide the choice, so TimescaleDB is an
  extension rather than a rewrite if volume ever justifies it.

## Deviations from the Go source

No Redis/`repocache` layer (usecases depend on repository contracts directly);
FastAPI-idiomatic presentation naming; Alembic instead of golang-migrate;
api-key auth / payload-schema / reverse proxies are out of scope.
TLS/SSL DSN options (a `sslmode`/`ssl` parameter on the Postgres connection)
remain out of scope.
