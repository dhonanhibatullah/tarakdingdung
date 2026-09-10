# Production Readiness — Data, Backtests, Paper Trading

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the backend to a deployable state: fix real-API integration bugs, seed a wide liquid universe, generate backtesting confidence (baseline + LLM-on-history), and stand up daily paper trading against live Indodax market data + DeepSeek.

**Architecture:** No new subsystems — this hardens the existing clean-architecture backend and adds one new concept: a *weight function* (deterministic baseline or LLM) driven by a *historical backtest driver* that builds `RebalanceEvent`s for the existing `FillSimulator`. Cron is wired as a FastAPI lifespan background task.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, httpx, DeepSeek (`deepseek-chat`), Indodax public + v2 API, Docker.

**Spec:** `backend/DESIGN.md` + `backend/AGENTS.md`. Decisions locked in with the user: (1) backtest = **both baseline + LLM-on-history**; (2) universe = **top ~25 liquid IDR pairs, excluding stablecoins/maintenance/suspended**; (3) paper cadence = **daily**.

## Discovery findings (verified live 2026-09-10)

- Indodax `/api/pairs` → 506 IDR pairs; `/api/summaries` → `{tickers: {btc_idr: {last, vol_idr, ...}}}`.
- Indodax `/tradingview/history_v2` returns a **list** of `{Time,Open,High,Low,Close,Volume}` (Time in **seconds**, OHLC ints, Volume string) — current parser is wrong.
- Indodax `/api/ticker/{pair}` `server_time` is **seconds**.
- Indodax v2 private key is **valid** but the machine IP is not allowlisted → `-2015 Unauthorized IP address` (blocks LIVE only; paper unaffected).
- DeepSeek key `TRDD_DEEPSEEK_SECRET_KEY` valid; real model is `deepseek-chat` (resolves to `deepseek-flash`); `response_format=json_object` works and returns valid decisions.
- CoinDesk feed 308-redirects `/arc/outboundfeeds/rss/` → `/arc/outboundfeeds/rss`; `httpx.AsyncClient()` defaults to `follow_redirects=False`.
- `.env` uses stale key names (`TRDD_BE_INDODAX_V2_*`, `TRDD_DEEPSEEK_SECRET_KEY`) that don't match `Settings`.
- Cron `run_scheduler` is defined but **never invoked** — no background loop starts it.

## Global Constraints

- `domain/` imports only stdlib; `domain/contracts/algorithm/*` stays **sync and pure**; everything else async.
- Money = `Decimal` (`NUMERIC(38,18)`); parse venue payloads via `str`, never `Decimal(float)`. Time = epoch **ms** UTC.
- Deterministic client order ids; risk overlay idempotent; write-ahead persistence; no HTTP route runs a live cycle.
- Repository verbs/naming as in `AGENTS.md`; env prefix `TRDD_BE_`.
- Tests: `pytest -q` (must stay green); integration requires Docker (already available).

---

## Phase 0 — Real-API bug fixes

### Task 1: Fix Indodax public client (candles + ticker)

**Files:**
- Modify: `src/tarakdingdung/infrastructure/scrapper/indodax/public.py`
- Test: `tests/infrastructure/scrapper/test_indodax_public.py`

- [ ] **Step 1: Rewrite `fetch_candles` to parse the list-of-objects shape** (Time seconds → ms, `Decimal(str(...))` for OHLC/Volume) and `fetch_ticker` `server_time * 1000`.

- [ ] **Step 2: Update the two mock tests** to return the real shape:
  - candles mock: `[{"Time":1000,"Open":1371027000,"High":1374765000,"Low":1368572000,"Close":1374765000,"Volume":"0.54342495"}]` → assert `open_time_ms == 1_000_000`, `volume == Decimal("0.54342495")`.
  - ticker mock `server_time: 1789015293` → assert `timestamp_ms == 1789015293000`.

- [ ] **Step 3: Run** `pytest tests/infrastructure/scrapper/test_indodax_public.py -q` → PASS.

- [ ] **Step 4: Commit** `fix: parse Indodax candle/ticker response shapes`.

### Task 2: Follow redirects in all httpx clients

**Files:**
- Modify: `src/tarakdingdung/composition/main/infrastructure.py` (the four `httpx.AsyncClient()` sites)

- [ ] **Step 1: Add `follow_redirects=True`** to `build_completion`, `build_market_source`, `build_news_sources` (`client = httpx.AsyncClient(follow_redirects=True)`), and `build_exchange` live branch.

- [ ] **Step 2: Add a regression test** in `tests/infrastructure/scrapper/test_news_rss.py` asserting `HttpNewsSource` follows a 308 (MockTransport returning 308 with `location` then 200 XML).

- [ ] **Step 3: Run** `pytest tests/infrastructure/scrapper/test_news_rss.py -q` → PASS.

- [ ] **Step 4: Commit** `fix: follow redirects in httpx clients`.

### Task 3: DeepSeek defaults

**Files:**
- Modify: `src/tarakdingdung/config/settings.py`
- Test: `tests/test_settings.py`

- [ ] **Step 1: Change `llm_model` default to `"deepseek-chat"` and `llm_base_url` default to `"https://api.deepseek.com"`.**

- [ ] **Step 2: Add test** asserting `Settings(_env_file=None).llm_model == "deepseek-chat"` and `llm_base_url == "https://api.deepseek.com"`.

- [ ] **Step 3: Run + commit** `fix: deepseek-chat model + base url defaults`.

---

## Phase 1 — Environment alignment

### Task 4: Rewrite `.env` to current `Settings` naming

**Files:**
- Modify: `backend/.env` (values preserved; do not print secrets)

- [ ] **Step 1:** Map values: `TRDD_BE_INDODAX_V2_API_KEY→TRDD_BE_INDODAX_API_KEY`, `TRDD_BE_INDODAX_V2_SECRET_KEY→TRDD_BE_INDODAX_SECRET_KEY`, `TRDD_DEEPSEEK_SECRET_KEY→TRDD_BE_LLM_API_KEY`; add `TRDD_BE_LLM_BASE_URL=https://api.deepseek.com`, `TRDD_BE_LLM_MODEL=deepseek-chat`, `TRDD_BE_ENGINE_ENABLED=true`, `TRDD_BE_ENGINE_MODE=paper`, `TRDD_BE_UNIVERSE_ID=default`; drop dead `TRDD_BE_INDODAX_V1_*`, `TRDD_BE_TOKOCRYPTO_*`.

- [ ] **Step 2: Verify** `Settings().indodax_api_key` and `Settings().llm_api_key` are non-empty; `Settings().llm_model == "deepseek-chat"`.

- [ ] **Step 3: Commit** `chore: align .env with Settings naming`.

---

## Phase 2 — Universe expansion

### Task 5: Universe selector (top ~25 liquid, no stablecoins)

**Files:**
- Create: `src/tarakdingdung/application/trading/universe/selector.py` (pure helper)
- Test: `tests/application/trading/test_universe_selector.py`

**Interfaces:**
- Produces `select_universe(pairs: list[dict], summaries: dict, top_n: int, stablecoins: set[str]) -> list[dict]` returning `{"venue","base","quote","external","volume"}` rows, filtered on `is_maintenance != 1`, `is_market_suspended != 1`, `traded_currency` not in stablecoins, sorted by `vol_idr` desc, top N.

- [ ] **Step 1: Write failing test** (a canned `pairs`/`summaries` blob; assert stablecoins excluded, maintenance excluded, top-N returned).
- [ ] **Step 2-4: Implement + pass.**
- [ ] **Step 5: Commit** `feat: universe selector`.

### Task 6: Seed the wide universe

**Files:**
- Modify: `backend/database/seeder/universe.json` (25 rows)
- Modify: `src/tarakdingdung/composition/seeder/launcher.py` (accept `base`/`quote` case; already generic)

- [ ] **Step 1: Run the selector against live Indodax** to produce the top-25 list (stablecoin set: `{usdt, usdc, dai, busd, tusd, usdp, usdd, frax, usd}`); write the 25 rows into `universe.json`.

- [ ] **Step 2: Re-run migrations are not needed; run seeder** against the live DB and verify `universe_memberships` grows to ~25 APPROVED.

- [ ] **Step 3: Update** `tests/integration/test_seeder.py` assertion to expect the new count (≥ 20).

- [ ] **Step 4: Commit** `feat: seed wide liquid universe`.

---

## Phase 3 — Historical candle backfill

### Task 7: Backfill candles for the universe

**Files:**
- Create: `src/tarakdingdung/application/trading/backtest/backfill.py` (one-shot async routine using `MarketSource` + `MarketDataRepository`)
- Test: `tests/application/trading/test_backfill.py` (fake source/repo)

**Interfaces:**
- Produces `async backfill(market_source, market_data, symbols, interval, from_ms, to_ms) -> int` (candles stored), paginating the venue `from/to` window in chunks of ≤ ~2000 candles to respect the API limit.

- [ ] **Step 1: TDD the pagination** (fake source yields candles per chunk; assert chunking + append called).
- [ ] **Step 2-4: Implement + pass.**
- [ ] **Step 5: Commit** `feat: candle backfill`.

---

## Phase 4 — Backtesting

### Task 8: Baseline weight functions (pure, sync)

**Files:**
- Create: `src/tarakdingdung/infrastructure/algorithm/backtest/weights.py`
- Test: `tests/infrastructure/algorithm/test_weights.py`

**Interfaces:**
- `equal_weight(symbol_ids: list[str]) -> list[Weight]`
- `momentum_top_k(candles: dict[str, list[Candle]], top_k: int, lookback: int) -> list[Weight]` (rank by `close[-1]/close[-lookback] - 1`, equal-weight the top K)

- [ ] **Step 1: TDD both** (equal weights sum to 1; momentum selects the top K symbols).
- [ ] **Step 2-4: Implement + pass.**
- [ ] **Step 5: Commit** `feat: baseline weight functions`.

### Task 9: Historical backtest driver

**Files:**
- Create: `src/tarakdingdung/application/trading/backtest/historical.py`
- Test: `tests/application/trading/test_historical_backtest.py`

**Interfaces:**
- `WeightFn = Callable[[dict[str, list[Candle]], int], Awaitable[list[Weight]]]`
- `async run(rebalancer, simulator, cost_model, initial_equity, symbols, candles_by_symbol, timestamps, weight_fn) -> FillSimResult` — builds `RebalanceEvent(timestamp, target, prices-at-ts)` per timestamp and calls `simulator.simulate`.

- [ ] **Step 1: TDD with a fixed `weight_fn`** (assert equity curve/fills produced, prices snap to the candle at each timestamp).
- [ ] **Step 2-4: Implement + pass.**
- [ ] **Step 5: Commit** `feat: historical backtest driver`.

### Task 10: LLM-on-history weight function

**Files:**
- Create: `src/tarakdingdung/application/trading/backtest/llm_weight_fn.py`
- Test: `tests/application/trading/test_llm_weight_fn.py` (fake decision maker)

**Interfaces:**
- `make_llm_weight_fn(decision_maker, symbol_ids) -> WeightFn` — builds a `DecisionContext` (candles-as-text, empty news, "cash" portfolio) at each timestamp, calls `decision_maker.decide`, returns `decision.weights` or `[]` on hold.

- [ ] **Step 1: TDD with a fake decision maker** (returns fixed weights; held → `[]`).
- [ ] **Step 2-4: Implement + pass.**
- [ ] **Step 5: Commit** `feat: LLM-on-history weight function`.

### Task 11: Run backtests (operational)

- [ ] **Step 1: Backfill** ~90 days of daily candles (`tf="1D"`) for the ~25 universe symbols.
- [ ] **Step 2: Run baselines** — equal-weight + momentum over 90d, and over 30d/60d sub-windows; record Sharpe/maxDD/turnover.
- [ ] **Step 3: Run LLM-on-history** over the 90d window (one decision/day) and record the same metrics.
- [ ] **Step 4: Write `docs/superpowers/plans/2026-09-10-backtest-results.md`** with a results table + a one-paragraph conclusion on deploy-readiness.
- [ ] **Step 5: Commit** the results doc.

---

## Phase 5 — Paper trading setup

### Task 12: Wire cron scheduler into the app lifespan

**Files:**
- Modify: `src/tarakdingdung/composition/main/driver.py` (add `lifespan`), `src/tarakdingdung/presentation/cron/schedule.py` (expose a stoppable task)
- Test: `tests/presentation/cron/test_schedule.py` (lifespan starts/does-not-start)

- [ ] **Step 1: Add a FastAPI `lifespan`** that, when `settings.cron_enabled`, launches `run_scheduler(container, settings)` as a background `asyncio.Task` and cancels it on shutdown.

- [ ] **Step 2: Test** `cron_enabled=False` → no task started; `True` → task scheduled (use `TestClient` context or a direct lifespan call with a `stop_event`).

- [ ] **Step 3: Run + commit** `feat: start cron scheduler via app lifespan`.

### Task 13: Paper-exchange state reconstruction

**Files:**
- Modify: `src/tarakdingdung/composition/main/infrastructure.py` + `driver.py` (paper exchange seeding from last snapshot)

- [ ] **Step 1: Seed `PaperExchange` from the latest persisted snapshot** — on paper boot, read `portfolio.read_latest(venue)` + balances; if present, construct `PaperExchange({asset: free+locked})`; else the configured initial IDR. (Do this in an async startup step inside the lifespan, before the scheduler runs.)

- [ ] **Step 2: Test** that a second boot resumes from the previous balances.

- [ ] **Step 3: Run + commit** `feat: resume paper state from last snapshot`.

### Task 14: Full paper cycle end-to-end (operational)

- [ ] **Step 1:** With `TRDD_BE_ENGINE_ENABLED=true`, `TRDD_BE_ENGINE_MODE=paper`, `TRDD_BE_CRON_ENABLED=true`, run the app (docker compose) and confirm a complete cycle: collect candles → snapshot → LLM decision → paper fill → persisted decision + order.

- [ ] **Step 2:** Inspect `decisions`, `orders`, `fills`, `portfolio_snapshots` rows to confirm the paper book advances.

- [ ] **Step 3: Commit** any fixes found.

---

## Phase 6 — Hardening + verification

### Task 15: Docker + full verification

- [ ] **Step 1: `docker compose up -d --build`** then `docker compose run --rm seeder`; confirm healthcheck `/api/version` passes and cron logs a first cycle.
- [ ] **Step 2: Run `pytest -q`** → green.
- [ ] **Step 3: Confirm** `alembic upgrade head` idempotent against live DB.
- [ ] **Step 4: Write the come-back guidance** (below) into the final report.

**Come-back guidance (daily cadence):** check at **7 days** (7 decisions — pipeline sanity), meaningful signal at **~14 days** (enough decisions for a replay-backtest + basic stats), full picture at **~30 days**.

---

## Self-review

- Bugs D1–D5 (candles, ticker, redirects, model, config) → Tasks 1–4.
- Universe (top 25, no stablecoins) → Tasks 5–6.
- Backtests (baseline + LLM-on-history) → Tasks 8–11; backfill → Task 7.
- Paper (daily, live market data + DeepSeek) → Tasks 12–14.
- Production hardening + duration → Tasks 15.
- All decisions from the clarifying questions are reflected; type names (`Weight`, `RebalanceEvent`, `FillSimResult`, `WeightFn`) reused from the existing algorithm layer.
