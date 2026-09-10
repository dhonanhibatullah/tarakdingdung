# LLM-Driven Trading Backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the tarakdingdung backend greenfield as an LLM-decision trading system with deterministic safety rails, against Indodax V2.

**Architecture:** Clean architecture (`presentation → application → domain ← infrastructure`, `composition` wires). The LLM decides universe + target weights + reasoning; deterministic code validates, applies a risk overlay, rebalances to orders, and executes (paper/live). Every decision is persisted in full for replay-backtesting.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, PyJWT, bcrypt, httpx, pydantic-settings, pytest + pytest-asyncio, testcontainers[postgres].

**Spec:** `backend/DESIGN.md` (normative decisions D1–D9) and `backend/AGENTS.md` (layout + conventions). The plan argues from those two files; executors read all three.

## Global Constraints

- Package: `tarakdingdung` under `src/`; entry points `tarakdingdung.composition.main.launcher:run` (serve) and `tarakdingdung.composition.seeder.launcher:run` (seed) — these exact paths are referenced by `pyproject.toml`, `Dockerfile`, `docker/entrypoint.sh`.
- `domain/` imports only the standard library. `presentation/` never imports `infrastructure/`.
- `domain/contracts/algorithm/*` is **synchronous and pure** (no I/O, no clock, no LLM). Everything else is `async`.
- Money = `Decimal` (`NUMERIC(38,18)` in Postgres); statistics = `float`. Decimals cross JSONB as strings; parse venue payloads via `str`, never `Decimal(float)`.
- Time = `int` epoch milliseconds, UTC, everywhere in trading.
- Errors: `DomainError(message, ErrorType.X)`. `VALIDATION` and `BAD_ARGS` both map to HTTP 400.
- Partial failure is returned as data, not raised.
- `Settings` via pydantic-settings, env prefix `TRDD_BE_`. Secrets in `.env` (gitignored).
- Soft delete on `permissions`/`roles`/`users`; `role_permission` hard deleted.
- Repository verbs: `create`, `read_by_id`, `read_by_<field>`, `read_default`, `read_permissions`, `read_by_pagination`, `update_by_id`, `delete_by_id`. Trading adds `read_range`, `read_coverage`, `append_fills`, `read_unreconciled`, `read_latest_decision`.
- Infrastructure classes carry their mechanism: `SqlAlchemy*Repository`, `Http*`, `Jwt*`, `Bcrypt*`, `Postgres*`.
- Tests: `pytest -q`, `asyncio_mode=auto`, `testpaths=["tests"]`, `pythonpath=["src"]`.

---

## Phase 0 — Foundation

### Task 1: Config, error, logger, clock

**Files:**
- Create: `src/tarakdingdung/__init__.py`
- Create: `src/tarakdingdung/config/__init__.py`, `src/tarakdingdung/config/settings.py`
- Create: `src/tarakdingdung/domain/models/__init__.py`, `src/tarakdingdung/domain/models/error.py`, `src/tarakdingdung/domain/models/logger.py`
- Create: `src/tarakdingdung/domain/contracts/__init__.py`, `src/tarakdingdung/domain/contracts/logger/__init__.py`, `src/tarakdingdung/domain/contracts/logger/leveled.py`
- Create: `src/tarakdingdung/domain/contracts/utility/__init__.py`, `src/tarakdingdung/domain/contracts/utility/clock.py`
- Create: `src/tarakdingdung/infrastructure/__init__.py`, `src/tarakdingdung/infrastructure/logger/__init__.py`, `src/tarakdingdung/infrastructure/logger/leveled/__init__.py`, `src/tarakdingdung/infrastructure/logger/leveled/json.py`, `src/tarakdingdung/infrastructure/logger/leveled/plain.py`
- Create: `src/tarakdingdung/infrastructure/utility/__init__.py`, `src/tarakdingdung/infrastructure/utility/clock/__init__.py`, `src/tarakdingdung/infrastructure/utility/clock/system.py`
- Test: `tests/test_settings.py`, `tests/domain/test_error.py`, `tests/infrastructure/test_logger.py`, `tests/infrastructure/test_clock.py`

**Interfaces:**
- Produces: `DomainError(message: str, error_type: ErrorType)` where `ErrorType` is a `str`-enum (`VALIDATION`, `BAD_ARGS`, `NOT_FOUND`, `UNAUTHORIZED`, `FORBIDDEN`, `CONFLICT`, `INTERNAL`). `LeveledLogger` ABC: `debug/info/warning/error(level, message, **fields)` — exact names chosen in this task. `Clock` ABC with `now_ms() -> int`.
- Produces: `Settings` with at least `postgres_dsn` (property), `logger_format`, `logger_level`, `http_host`, `http_port`, `cors_allowed_origins`, `token_access_secret`, `token_refresh_secret`, `token_access_ttl_seconds`, `token_refresh_ttl_seconds`, `password_bcrypt_cost`, `cron_enabled`, `engine_interval_seconds`, `llm_base_url`, `llm_api_key`, `llm_model`, `news_sources` (list[str]).

- [ ] **Step 1: Write failing tests** — settings loads from `TRDD_BE_` env; `DomainError` carries type; logger formats json/plain; `SystemClock.now_ms()` returns an int.

- [ ] **Step 2: Run** `pytest -q tests/test_settings.py tests/domain/test_error.py tests/infrastructure/test_logger.py tests/infrastructure/test_clock.py` → FAIL (no module).

- [ ] **Step 3: Implement** minimal versions.

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit** `feat: foundation — settings, error, logger, clock`.

### Task 2: Utility contracts + implementations (password, token, transactor, single_flight)

**Files:**
- Create: `src/tarakdingdung/domain/contracts/utility/password.py`, `token.py`, `transactor.py`, `single_flight.py`
- Create: `src/tarakdingdung/infrastructure/utility/password/__init__.py`, `bcrypt.py`; `token/__init__.py`, `jwt.py`; `transactor/__init__.py`, `sqlalchemy.py`; `single_flight/__init__.py`, `postgres.py`
- Test: `tests/infrastructure/test_password.py`, `test_token.py`, `tests/domain/test_contracts.py` (utility ABCs)

**Interfaces:**
- `Password` ABC: `hash(plain) -> str`, `verify(plain, hashed) -> bool`.
- `Token` ABC: `encode_access(claims) -> str`, `encode_refresh(claims) -> str`, `decode(token) -> TokenClaims`.
- `Transactor` ABC: `async __call__(fn: Callable[[], Awaitable[T]]) -> T` (wraps fn in a transaction).
- `SingleFlight` ABC: `async acquire(key: str) -> bool` (true if acquired; false if already running).

- [ ] **Step 1: TDD each** (hash/verify round-trip; token encode/decode round-trip; transactor commits on success and rolls back on exception using a fake session; single_flight returns true once then false).

- [ ] **Step 2–4:** red/green each.

- [ ] **Step 5: Commit** `feat: utility contracts + bcrypt/jwt/transactor/single_flight`.

---

## Phase 1 — RBAC / auth

### Task 3: RBAC domain models + repository contracts

**Files:**
- Create: `src/tarakdingdung/domain/models/permission.py`, `role.py`, `role_permission.py`, `user.py`, `token_claims.py`
- Create: `src/tarakdingdung/domain/contracts/repository/__init__.py`, `permission.py`, `role.py`, `role_permission.py`, `user.py`
- Test: `tests/domain/test_models.py` (frozen, validate), `tests/domain/test_contracts.py`

**Interfaces:**
- Models (frozen slots): `Permission(id, name, description)`, `Role(id, name, description)`, `RolePermission(role_id, permission_id)`, `User(id, username, email, password_hash, is_active, is_deleted, created_at, updated_at)`, `TokenClaims(sub, username, roles: list[str], permissions: list[str], exp: int, type: str)`.
- Repository ABCs with verbs from Global Constraints; `read_permissions(role_id) -> list[Permission]`; `read_default() -> Role | None` for roles.

- [ ] **Step 1–4:** TDD the frozen/validation behavior and ABC surface (abstract methods only).

- [ ] **Step 5: Commit** `feat: rbac domain models + repository contracts`.

### Task 4: RBAC usecases (admin + auth + profile)

**Files:**
- Create: `src/tarakdingdung/domain/usecases/__init__.py`, `admin/__init__.py`, `admin/permission_management.py`, `admin/role_management.py`, `admin/user_management.py`, `auth/__init__.py`, `auth/session.py`, `profile/__init__.py`, `profile/me.py`, `profile/account.py`, `profile/security.py`
- Create: `src/tarakdingdung/application/admin/...` (one impl per usecase), `src/tarakdingdung/application/auth/session/usecase.py`, `src/tarakdingdung/application/profile/...`
- Test: `tests/application/test_permission_management.py`, `test_role_management.py`, `test_user_management.py`, `test_auth_session.py`, `test_profile.py`

**Interfaces:** usecase ABCs with request/result dataclasses. Implementations depend only on repository + utility contracts (injected). Fakes (Task 5) satisfy the repository contracts.

- [ ] **Step 1–4:** TDD with hand-written fakes in `tests/fakes/repositories.py`.

- [ ] **Step 5: Commit** `feat: rbac + auth + profile usecases`.

### Task 5: SQLAlchemy repositories + ORM + migrations

**Files:**
- Create: `src/tarakdingdung/infrastructure/repository/database/__init__.py`, `orm.py`, `session.py`, `migrations.py`
- Create: `src/tarakdingdung/infrastructure/repository/shared/__init__.py`, `errors.py`, `mappers.py`, `query.py`, `results.py`
- Create: `src/tarakdingdung/infrastructure/repository/{permission,role,role_permission,user}/__init__.py`, `queries.py`, `repository.py`
- Create: `database/migrations/__init__.py` (non-empty), `env.py`, `script.py.mako`, `versions/0001_rbac.py`
- Modify: `alembic.ini` already points at `database/migrations`.
- Test: `tests/integration/test_migrations.py`, `test_permission_repository.py`, `test_role_repository.py`, `test_role_permission_repository.py`, `test_user_repository.py`

**Interfaces:** `upgrade_to_head(dsn: str) -> None` (used by entrypoint). `Session` async sessionmaker. Each `SqlAlchemy*Repository` implements its domain contract.

- [ ] **Step 1–4:** TDD against testcontainers Postgres (Docker required); assert soft-delete behavior and pagination `(items, total)`.

- [ ] **Step 5: Commit** `feat: sqlalchemy repositories + alembic migration`.

### Task 6: HTTP presentation for RBAC + composition wiring + seeder

**Files:**
- Create: `src/tarakdingdung/presentation/http/...` (`routers/auth.py`, `routers/admin.py`, `routers/profile.py`, `dependencies/auth.py`, `dependencies/container.py`, `dependencies/permission.py`, `schemas/request.py`, `schemas/response.py`, `utils/errors.py`, `utils/pagination.py`)
- Create: `src/tarakdingdung/composition/main/{__init__,driver,infrastructure,application,presentation,launcher}.py`
- Create: `src/tarakdingdung/composition/seeder/{__init__,launcher,__main__}.py`
- Create: `src/tarakdingdung/main.py` (exports `app`)
- Create: `database/seeder/{permission,role,user}.json`
- Test: `tests/presentation/test_routers.py`, `tests/integration/test_composition_wiring.py`, `tests/integration/test_seeder.py`

**Interfaces:** `app` (FastAPI instance). `launcher.run()` starts uvicorn. Seeder `run()` idempotent (create-if-missing keyed by name). HTTP error mapping: `VALIDATION`/`BAD_ARGS` → 400.

- [ ] **Step 1–4:** TDD route behavior via FastAPI TestClient with fakes; wiring test asserts app boots; seeder test idempotency.

- [ ] **Step 5: Commit** `feat: http presentation + composition + seeder`.

---

## Phase 2 — Trading domain models

### Task 7: Trading domain models + repository contracts

**Files:**
- Create: `src/tarakdingdung/domain/models/symbol.py`, `universe.py`, `candle.py`, `market.py`, `portfolio.py` (snapshot + balance), `news.py` (article + analysis), `decision.py` (weight + decision), `backtest.py`, `order.py` (order/execution/fill)
- Create: `src/tarakdingdung/domain/contracts/repository/{symbol,market_data,news,decision,backtest,portfolio,order_journal}.py`
- Test: `tests/domain/test_trading_models.py`, `tests/domain/test_trading_contracts.py`

**Interfaces:**
- `Symbol(id, venue, base, quote, external)` — carries venue.
- `Universe(id, name)`, `UniverseMembership(symbol_id, state, rationale)` with `state ∈ {PROPOSED, APPROVED, REJECTED, REMOVED}`.
- `Candle(symbol_id, open_time_ms, open, high, low, close, volume)` (Decimals; no `__post_init__` validation — constructed in the millions).
- `PortfolioSnapshot(id, venue, as_of_ms, equity)`, `Balance(snapshot_id, asset, free, locked)`.
- `NewsArticle(id, source, url, title, published_ms, raw_text)`, `NewsAnalysis(id, article_id, summary, sentiment)`.
- `Weight(symbol_id, weight: float)`, `Decision(universe_id, as_of_ms, weights: list[Weight], reasoning: str, confidence: float, traces: dict, prompt: str, raw_response: str, status: str)` — validates: weights non-negative, sum ≤ 1.0.
- `Order(...)`, `Execution(...)`, `Fill(...)` with statuses including `UNCONFIRMED`.
- Repository ABCs: market_data `read_range(symbol_id, from_ms, to_ms)`, `read_coverage(...)`; decision `read_latest_decision(universe_id)`; order_journal `append_fills(...)`, `read_unreconciled(...)`.

- [ ] **Step 1–4:** TDD model validation (decision weight constraints) and ABC surface.

- [ ] **Step 5: Commit** `feat: trading domain models + repository contracts`.

---

## Phase 3 — Algorithm (pure, synchronous)

### Task 8: Risk overlay

**Files:**
- Create: `src/tarakdingdung/domain/contracts/algorithm/__init__.py`, `risk.py`
- Create: `src/tarakdingdung/infrastructure/algorithm/__init__.py`, `risk/__init__.py`, `risk/per_position_cap.py`, `risk/per_venue_cap.py`, `risk/daily_loss_halt.py`, `risk/volatility_kill_switch.py`, `risk/overlay.py`
- Test: `tests/infrastructure/algorithm/test_risk.py`, `tests/infrastructure/algorithm/conformance.py`

**Interfaces:**
- `RiskRule` ABC: `apply(weights: list[Weight], state: RiskState) -> RiskResult` (sync). `RiskResult(weights | None, halted: bool, rule: str, reason: str)`.
- `RiskState(equity, daily_pnl, volatility, venue_exposures)`.
- `RiskOverlay` ABC: `apply(weights, state) -> RiskResult`; implementations hold rules as a **sequence**, return which rule halted.

**Conformance invariants** (in `conformance.py`, parametrised): idempotence — `apply(apply(w)) == apply(w)`; halt → empty weights (liquidate).

- [ ] **Step 1–4:** TDD each rule + conformance.

- [ ] **Step 5: Commit** `feat: risk overlay (pure)`.

### Task 9: Rebalancer + cost model

**Files:**
- Create: `src/tarakdingdung/domain/contracts/algorithm/rebalance.py`, `cost.py`
- Create: `src/tarakdingdung/infrastructure/algorithm/rebalance/no_trade_band.py`, `cost/flat_fee.py`, `cost/__init__.py`
- Test: `tests/infrastructure/algorithm/test_rebalance.py`, `test_cost.py`

**Interfaces:**
- `Rebalancer` ABC: `rebalance(current: dict[str, Decimal], target: list[Weight], prices: dict[str, Decimal], equity: Decimal) -> OrderPlan` (sync). `OrderPlan(orders: list[PlannedOrder], rejected: list[Rejection])`.
- `CostModel` ABC: `fee(notional) -> Decimal`.
- `PlannedOrder(symbol_id, side, quantity, notional)`; `Rejection(symbol_id, reason)`.
- Deterministic `client_order_id = hash((universe_id, timestamp_ms, symbol_id, side))`.

- [ ] **Step 1–4:** TDD diff logic, no-trade band, min-notional rejections, deterministic ids.

- [ ] **Step 5: Commit** `feat: rebalancer + cost model (pure)`.

### Task 10: Metrics + fill simulation

**Files:**
- Create: `src/tarakdingdung/domain/contracts/algorithm/metric.py`, `backtest.py`
- Create: `src/tarakdingdung/infrastructure/algorithm/metric/standard.py`, `backtest/fill_sim.py`
- Test: `tests/infrastructure/algorithm/test_metric.py`, `test_backtest.py`

**Interfaces:**
- `Metric` ABC: `sharpe(returns) -> float`, `max_drawdown(equity) -> float`, `turnover(...) -> float`.
- `FillSimulator` ABC: `simulate(orders, candles, cost_model, initial_equity) -> FillSimResult(equity_curve, fills, metrics)` (sync).

- [ ] **Step 1–4:** TDD metrics on known series; fill sim reproduces a buy-and-hold equity curve within tolerance.

- [ ] **Step 5: Commit** `feat: metrics + fill simulation (pure)`.

---

## Phase 4 — Scraper

### Task 11: Scrapper contracts + Indodax public client

**Files:**
- Create: `src/tarakdingdung/domain/contracts/scrapper/__init__.py`, `market_source.py`, `news_source.py`
- Create: `src/tarakdingdung/infrastructure/scrapper/__init__.py`, `indodax/__init__.py`, `indodax/public.py`
- Test: `tests/infrastructure/scrapper/test_indodax_public.py` (httpx mock transport)

**Interfaces:**
- `MarketSource` ABC: `async fetch_candles(symbol, interval, from_ms, to_ms) -> list[Candle]`, `async fetch_ticker(symbol) -> Ticker`.
- `NewsSource` ABC: `async fetch() -> list[NewsArticle]`.
- `HttpIndodaxPublicApi` implements `MarketSource` against `https://indodax.com/api/*` and `/tradingview/history_v2`.

- [ ] **Step 1–4:** TDD with a canned httpx response (pairs, ticker, candles), parsing via `str` for Decimals.

- [ ] **Step 5: Commit** `feat: scrapper contracts + indodax public client`.

### Task 12: News source + collection usecase

**Files:**
- Create: `src/tarakdingdung/infrastructure/scrapper/news/rss.py`
- Create: `src/tarakdingdung/domain/usecases/trading/collection.py`
- Create: `src/tarakdingdung/application/trading/collection/usecase.py`
- Create: `src/tarakdingdung/infrastructure/repository/market_data/...`, `news/...`
- Create: `database/migrations/versions/0002_trading.py`
- Test: `tests/application/trading/test_collection.py`, `tests/integration/test_trading_repositories.py`

**Interfaces:** `CollectResult(failed: list[str])` — partial failure is data. Collection writes candles + news via repositories.

- [ ] **Step 1–4:** TDD collection tolerates one source failing; repositories round-trip candles/news.

- [ ] **Step 5: Commit** `feat: news source + collection usecase + trading repositories`.

---

## Phase 5 — LLM

### Task 13: LLM completion contract + OpenAI-compatible client

**Files:**
- Create: `src/tarakdingdung/domain/contracts/llm/__init__.py`, `completion.py`
- Create: `src/tarakdingdung/infrastructure/llm/__init__.py`, `openai_compatible.py`
- Test: `tests/infrastructure/llm/test_completion.py` (httpx mock)

**Interfaces:**
- `Completion` ABC: `async complete(messages: list[Message], *, json_schema: str | None = None) -> str`.
- `Message(role: str, content: str)`.
- `HttpOpenAiCompatibleCompletion` posts to `{base_url}/chat/completions` with `response_format={"type":"json_object"}` when a schema is requested.

- [ ] **Step 1–4:** TDD request shape + response parse against a canned httpx response.

- [ ] **Step 5: Commit** `feat: llm completion contract + openai-compatible client`.

### Task 14: Agent pipeline + schema validation

**Files:**
- Create: `src/tarakdingdung/domain/contracts/llm/agent.py`, `pipeline.py`, `validation.py`
- Create: `src/tarakdingdung/infrastructure/llm/agents/market.py`, `news.py`, `coordinator.py`
- Create: `src/tarakdingdung/infrastructure/llm/pipeline.py`, `validation.py`
- Test: `tests/infrastructure/llm/test_pipeline.py`, `test_validation.py`

**Interfaces:**
- `Agent` ABC: `async analyze(context: str) -> str`.
- `DecisionMaker` ABC: `async decide(context: DecisionContext) -> DecisionResult`.
- `DecisionContext(candles: str, news_summaries: str, portfolio: str, universe: str)`.
- `DecisionResult(decision: Decision | None, held: bool, traces: dict)`.
- `DecisionValidator` ABC: `validate(raw: str) -> Decision` (raises on schema violation). Retry 2×, then `held=True`.

**Validation tests:** fuzz malformed JSON, negative weights, sum > 1.0 → assert hold-on-fail. Fake `Completion` returns canned valid/invalid responses; no network.

- [ ] **Step 1–4:** TDD pipeline produces a `Decision` from fake completion; malformed → held.

- [ ] **Step 5: Commit** `feat: agent pipeline + schema validation`.

---

## Phase 6 — Trade

### Task 15: Indodax V2 trade client + executor contract

**Files:**
- Create: `src/tarakdingdung/domain/contracts/trade/__init__.py`, `exchange.py`, `executor.py`, `reconciler.py`
- Create: `src/tarakdingdung/infrastructure/trade/__init__.py`, `indodax/__init__.py`, `indodax/v2.py`
- Create: `src/tarakdingdung/infrastructure/trade/execution/__init__.py`, `paper/executor.py`, `live/executor.py`, `reconciler.py`
- Test: `tests/infrastructure/trade/test_indodax_v2.py`, `test_executors.py`

**Interfaces:**
- `Exchange` ABC: `async account() -> Account`, `async place_order(order) -> OrderResult`, `async cancel_order(...)`, `async open_orders(...)`.
- `Executor` ABC: `async submit(orders) -> ExecutionResult` (`ExecutionResult(unconfirmed: list[...])`).
- `Reconciler` ABC: `async reconcile(unconfirmed) -> ReconcileResult`.

**Safety:** transport failure → `UNCONFIRMED`, never retried; client order ids deterministic (from Task 9).

- [ ] **Step 1–4:** TDD paper executor simulates fills; live executor maps transport errors to `UNCONFIRMED`; signing via `HMAC-SHA256` over query string + body (per `docs/researches/summaries/003`).

- [ ] **Step 5: Commit** `feat: indodax v2 client + executors + reconciler`.

---

## Phase 7 — Trading usecases

### Task 16: Engine (decision cycle) + portfolio + universe + backtest usecases

**Files:**
- Create: `src/tarakdingdung/domain/usecases/trading/{engine,portfolio,universe,backtest,orders}.py`
- Create: `src/tarakdingdung/application/trading/{engine,portfolio,universe,backtest,orders}/usecase.py`
- Test: `tests/application/trading/test_engine.py`, `test_portfolio.py`, `test_universe.py`, `test_backtest_replay.py`

**Interfaces:**
- `TradingEngine` ABC: `async run_cycle() -> CycleResult`, `async dry_run() -> CycleResult`.
- `CycleResult(status, ...)` with `status ∈ {DISABLED, SKIPPED, NO_DATA, HELD, HALTED, EXECUTED}`.
- `Universe` usecase: `propose(symbol)`, `approve(symbol)`, `list()`, `remove(symbol)` — LLM proposes, code approves.
- `Backtest` usecase: `replay(universe_id, from_ms, to_ms) -> BacktestResult`.

**Engine ordering test (write-ahead):** fake repositories assert that planned orders + `LlmDecision` are persisted before the executor's `submit` is called; a `UNCONFIRMED` order is reconciled next cycle.

- [ ] **Step 1–4:** TDD the 12-step cycle with fakes (fake LLM pipeline, fake executor, fake repos).

- [ ] **Step 5: Commit** `feat: trading usecases (engine, portfolio, universe, backtest)`.

---

## Phase 8 — Presentation + composition

### Task 17: Trading HTTP routes + cron tasks

**Files:**
- Create: `src/tarakdingdung/presentation/http/routers/trading.py`
- Create: `src/tarakdingdung/presentation/cron/{__init__,schedule.py,tasks/{__init__,collect.py,engine.py,portfolio.py}}`
- Test: `tests/presentation/test_trading_routes.py`, `tests/presentation/cron/test_schedule.py`, `tests/presentation/cron/test_tasks.py`

**Interfaces:** routes expose `universe`, `portfolio`, `backtest`, `decision`, `engine:dry_run` (no live route — a test asserts the live engine usecase is NOT imported by any router). Cron tasks resolve usecases and call a single step.

- [ ] **Step 1–4:** TDD route handlers + the "no live cycle over HTTP" guard; cron schedule with `TRDD_BE_CRON_ENABLED=false` default.

- [ ] **Step 5: Commit** `feat: trading routes + cron`.

### Task 18: Composition wiring, seeder universe, env, Docker alignment

**Files:**
- Modify: `src/tarakdingdung/composition/main/*.py` (add `llm`, `scrapper`, `trade` wiring)
- Modify: `src/tarakdingdung/composition/seeder/launcher.py` + `database/seeder/universe.json`
- Modify: `.env.example` (add `TRDD_BE_LLM_BASE_URL`, `TRDD_BE_LLM_API_KEY`, `TRDD_BE_LLM_MODEL`, `TRDD_BE_ENGINE_INTERVAL_SECONDS`, `TRDD_BE_NEWS_SOURCES`; drop Tokocrypto keys)
- Test: `tests/integration/test_app_boot.py`, `tests/integration/test_seeder.py`

- [ ] **Step 1–4:** TDD full app boot + seeder idempotency incl. universe seed.

- [ ] **Step 5: Commit** `feat: composition wiring + seeder universe + env`.

### Task 19: Full test pass + verification

- [ ] **Step 1:** Run `pip install -e ".[dev]"` and `pytest -q`.
- [ ] **Step 2:** Fix any failures; run `alembic upgrade head` against a throwaway Postgres.
- [ ] **Step 3:** Confirm `python -m tarakdingdung.composition.seeder` and app import (`uvicorn tarakdingdung.main:app`) succeed.
- [ ] **Step 4: Commit** any fixes as `test: full suite green`.

---

## Self-review notes

- Spec coverage: D1 (boundary) → Tasks 8,9,13,14,15; D2 (multi-agent) → 14; D3/D4 (weights + hold-on-fail) → 7,14; D5 (text+numeric) → 11,12,14; D6 (replay) → 10,16; D7 (universe gate) → 16; D8 (scrape→summarize→decide) → 11,12,14,16; D9 (greenfield safety) → 8,9,15.
- The 12-step cycle → Task 16; no-live-over-HTTP + cron-default-off → Task 17.
- Type consistency: `Decision`/`Weight`/`DecisionResult`/`RiskResult`/`OrderPlan`/`PlannedOrder`/`FillSimResult`/`CycleResult` defined once in Tasks 7–10 and reused verbatim downstream.
