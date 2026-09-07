# Trading Usecases — Implementation Plan

- **Date:** 2026-09-07
- **Design:** `docs/superpowers/specs/2026-09-07-trading-usecases-design.md`

## Ordering

Models before contracts before implementations, and within that, the pure work
before anything async. Each step below leaves the suite green, so the sequence
can be stopped at any point without a half-wired layer.

Steps 1–3 are worth landing as their own commit: they complete the algorithm
layer and are the only part with no external dependencies.

### Step 1 — models

`domain/models/strategy.py` (`TradingMode`, `StrategyConfig`),
`backtest.py` (`TimeRange`, `BacktestRun`, `ValidationRun`),
`execution.py` (`OrderAck`, `OrderRejection`, `ExecutionResult`,
`Discrepancy`, `CollectionFailure`).

Same rules as the existing models: frozen slots dataclasses, stdlib only,
`Decimal` for anything reaching an exchange or a balance, `int` epoch
milliseconds for time. Per-cycle objects validate in `__post_init__`;
`TimeRange` validates that start precedes end, since a reversed window would
otherwise silently select nothing.

### Step 2 — `CyclePlanner` contract and implementation

`domain/contracts/algorithm/cycle.py`, then
`infrastructure/algorithm/cycle/standard.py`.

Synchronous and pure, like every other algorithm block. The implementation
composes `Strategy` → `RiskRule` → `Rebalancer` → `OrderPlanner` and returns
the `OrderPlan` plus which rule halted, if any. Client order IDs are assigned
here, deterministically from strategy id, cycle timestamp, symbol and side, so
that the same plan computed twice is byte-identical — which is what makes
retry-by-client-order-id safe.

### Step 3 — `CyclePlanner` tests

Unit tests plus a conformance suite in
`tests/infrastructure/algorithm/conformance.py`, parametrised in
`test_conformance.py` alongside the existing four. Invariants: a halted risk
state yields an empty plan and names the rule; identical inputs yield identical
plans including client order IDs; every intent appears once across `orders` and
`rejected`.

### Step 4 — repository and utility contracts

`contracts/repository/{market_data,strategy,backtest,portfolio}.py`,
`contracts/execution/executor.py`, `contracts/utility/clock.py`.

`async` ABCs in the existing style, one-line abstract methods. Repository verb
names follow the current fixed set — `create`, `read_by_id`,
`read_by_pagination`, `update_by_id`, `delete_by_id` — extended only where the
domain genuinely differs (`read_range`, `read_coverage`, `append_fills`,
`acquire_cycle_lock`).

### Step 5 — usecase contracts

`domain/usecases/trading/{collection,history,strategy,backtest,validation,portfolio,engine}.py`.

Each file holds its request and result dataclasses beside the ABC, matching
`domain/usecases/auth/session.py`. `CycleDecision` lives in `engine.py`.

### Step 6 — fakes

`tests/fakes/` gains in-memory implementations of the four new repositories
plus `FakeExecutor`, `FakeClock` and `make_*` builders for the new models. The
fake executor records submissions so the write-ahead ordering can be asserted,
and can be told to fail on submit or on cancel.

### Step 7 — usecase implementations

`application/trading/<name>/usecase.py`, one at a time, in dependency order:
`history` and `collection` first (they depend only on repositories and the API
clients), then `strategy`, then `portfolio`, then `backtest`, then
`validation`, and `engine` last since it uses the most.

Each follows the house pattern: `_TAG`, keyword-only dependencies, log before
re-raising, `DomainError` with the right `ErrorType`.

### Step 8 — usecase tests

One file per usecase under `tests/application/`. Every safety property listed
in the design's testing section gets a named test; the engine's tests are the
substantial ones and cover write-ahead ordering, no-retry on transport failure,
reconciliation by client order ID, the halt and failed-cancel paths, the
single-flight lock, and staleness.

### Step 9 — presentation

`presentation/cron/` with `tasks/`, `schedule.py` and `dependencies/`, then
`presentation/http/routers/trading.py` with its schemas and new permission
entries in the seeder's `permission.json`. No route reaches live execution.

### Step 10 — wiring

`composition/main/infrastructure.py`, `application.py`, `launcher.py`, and a
`StrategyFactory` that turns a stored `StrategyConfig` into a `Strategy` and
its overlay.

### Step 11 — verify

Full suite, plus a check that `domain/` still imports nothing outside the
standard library.

## Blocked

**Steps 4 and 7 need the storage engine decision** that summary 004 left open —
the same Postgres as everything else, or a time-series store for candles and
books. The contracts can be written against either, but the SQLAlchemy
implementations and their migrations cannot start until it is settled. Raise
this before step 4 rather than guessing.

## Not in this work

Real strategy configurations beyond the controls, the collector's scheduling
policy tuning, and any live-capital operation.
