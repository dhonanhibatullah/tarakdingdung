# Trading Usecases — Design

- **Date:** 2026-09-07
- **Status:** approved
- **Scope:** the `trading/` usecase area, the contracts it needs, and the
  presentation adapters that drive it
- **Sources:** `docs/researches/summaries/004_Automated_Trading_Engine_Implementation_Plan.md`,
  `docs/superpowers/specs/2026-09-07-algorithm-layer-design.md`

## Problem

The algorithm layer is pure and synchronous by design: it cannot fetch a
candle, place an order or know what time it is. Something has to stand between
those blocks and the world — read stored history, reconcile a portfolio across
two exchanges, submit orders, persist what happened, and do all of it without
letting a partial failure become either a silent gap or a doubled position.
That is the usecase layer.

It also has to guarantee one property the whole project rests on: that a
backtest and a live cycle make decisions the same way. If they are two
implementations, they drift, and a drifting backtest is worse than no backtest.

## Decisions

**Both a backtest and a live cycle call one pure planner.** The shared part —
snapshot plus portfolio plus risk state plus venue rules producing an
`OrderPlan` — contains no I/O. It is a composition of `Strategy`, `RiskRule`,
`Rebalancer` and `OrderPlanner`, so it belongs in the algorithm layer, not in a
usecase:

```
CyclePlanner.plan(snapshot, portfolio, state, rules) -> OrderPlan
```

`TradingEngine.run_cycle` fetches, calls `plan`, executes and persists.
`Backtesting.run` replays stored snapshots, calls the same `plan`, simulates
fills and persists. Neither usecase depends on the other, both provably share
the decision logic, and the shared part stays testable without mocks.

The alternatives were rejected: having the backtester drive
`TradingEngine.run_cycle` forces a usecase to depend on another usecase and
parameterises the live path for a caller it should not know about; two
independent loops kept in sync by discipline is exactly the divergence the
research warns about.

This adds a twelfth contract to the algorithm layer, which the earlier spec
described as complete. That claim was wrong — the need only surfaced when
designing what a backtest and a live cycle actually share.

**Paper versus live is injected, never a request flag.** `StrategyConfig`
carries a `mode`, and `TradingEngine` holds `executors: Mapping[TradingMode,
Executor]`. One engine can run one strategy on paper and another live
simultaneously, which is what promoting a single strategy from Phase 5 to
Phase 6 requires. A boolean on the request would let a caller send a paper
strategy's orders to a real exchange.

**Scheduling lives in `presentation/cron/`, never in a usecase.** Cron is a
delivery adapter, a sibling of `http/`, driving usecases exactly as routers do.
Each usecase exposes a single step and stays ignorant of time; cadence, retry
policy and overlap handling belong to the adapter.

**Partial failure is returned as data.** Collection, portfolio sync and the
cycle can all half-succeed, and each reports what failed rather than raising.
One venue being down must shrink a poll, not abort it — otherwise an outage on
one exchange stops collecting the other's data and the gap is permanent.

## Usecases

New area `trading/`, mirroring `auth/`, `admin/` and `profile/`. Contracts and
their request/result dataclasses in `domain/usecases/trading/`, implementations
in `application/trading/<name>/usecase.py`.

| File | Contract | Methods | Driven by |
|---|---|---|---|
| `collection.py` | `MarketDataCollection` | `collect` | cron |
| `history.py` | `MarketDataHistory` | `read_candles`, `read_snapshot`, `read_coverage` | HTTP + engine |
| `strategy.py` | `StrategyManagement` | `create`, `read_by_id`, `read_by_pagination`, `update_by_id`, `delete_by_id` | HTTP |
| `backtest.py` | `Backtesting` | `run`, `read_by_id`, `read_by_pagination` | HTTP + cron |
| `validation.py` | `StrategyValidation` | `run_walk_forward`, `read_by_id` | HTTP |
| `portfolio.py` | `PortfolioSync` | `sync`, `read_current`, `read_equity_curve` | cron + HTTP |
| `engine.py` | `TradingEngine` | `run_cycle` | cron |

Why these seams:

- **`collection` is split from `history`** because they have opposite failure
  modes and opposite drivers. Collection is a write path on a cron that must
  tolerate a venue being down and is judged on coverage; history is a read path
  serving both HTTP and the engine that must never invent data. One usecase
  doing both would force every caller to reason about both.
- **`StrategyManagement` is CRUD in the existing house style.** Without it,
  what the engine runs lives in a config file that nothing audits, and
  `run_cycle` has nothing to look up.
- **`PortfolioSync` exists because a `Portfolio` is not free.** It is
  reconciled from both venues' account endpoints, and `RiskState` is derived
  from stored history. That reconciliation is where "the exchange says we hold
  something we did not order" surfaces, so it gets its own usecase instead of
  hiding inside a cycle.
- **`Backtesting` and `StrategyValidation` are separate** because a backtest is
  one run over one parameter set while validation is many runs plus the PBO
  gate over their results. Merging them would make the gate an optional flag,
  and an optional gate is not a gate.

## Requests and results

Ordinary shapes are omitted; these four carry the design.

### Partial failure

```
CollectResult(timestamp, collected: tuple[Symbol, ...],
              failed: tuple[CollectionFailure, ...])
SyncResult(portfolio, discrepancies: tuple[Discrepancy, ...])
RunCycleResult(..., plan: OrderPlan, execution: ExecutionResult | None)
```

`SyncResult.discrepancies` is the most important thing a reconciliation can
report and must not be an exception a cron swallows into a log line. This is
`OrderPlan.rejected` applied consistently.

### The cycle explains itself

```
RunCycleResult(timestamp, strategy_id, decision: CycleDecision,
               weights: TargetWeights, plan: OrderPlan,
               execution: ExecutionResult | None, halted_by: str | None)

CycleDecision(StrEnum): TRADED | NO_DRIFT | HALTED | NO_DATA
                      | DISABLED | SKIPPED | DRY_RUN
```

"The bot did nothing" is the most common operational question and the hardest
to answer after the fact. A halt records which rule halted it; no drift is
distinct from no data. Without this the only diagnosis available is re-reading
logs and guessing.

### Coverage is a first-class query

```
CoverageResult(first_timestamp, last_timestamp, expected, present,
               gaps: tuple[TimeRange, ...])
```

A backtest over history with holes invents flat periods and reports a Sharpe
for a strategy that never traded. Nothing sells clean history for these venues
and we are accumulating our own, so gaps are likely rather than hypothetical.
`Backtesting.run` checks coverage first and refuses a window whose gaps exceed
tolerance.

## New contracts

| Path | Contract | Purpose |
|---|---|---|
| `contracts/algorithm/cycle.py` | `CyclePlanner` | the pure shared decision step |
| `contracts/execution/executor.py` | `Executor` | `submit(orders)`, `cancel_all(symbols)` |
| `contracts/repository/market_data.py` | `MarketDataRepository` | candles, books, prices, range reads, coverage |
| `contracts/repository/strategy.py` | `StrategyRepository` | strategy configs |
| `contracts/repository/backtest.py` | `BacktestRepository` | runs, reports, validation results |
| `contracts/repository/portfolio.py` | `PortfolioRepository` | position snapshots, equity curve, fills, risk state |
| `contracts/utility/clock.py` | `Clock` | `now_ms()`, injected for reproducibility |

`Executor.cancel_all` exists for the Indodax dead-man switch and the halt path:
when a risk rule trips, resting orders must be pulled, not merely left
unplaced.

## New models

- `domain/models/strategy.py` — `StrategyConfig` (persisted entity with `UUID`,
  timestamps and `preferences`, matching `Role` and `User`), `TradingMode`.
- `domain/models/backtest.py` — `BacktestRun`, `ValidationRun`, `TimeRange`.
- `domain/models/execution.py` — `OrderAck`, `OrderRejection`,
  `ExecutionResult`, `Discrepancy`, `CollectionFailure`.

## The cycle

```
1. load StrategyConfig          → missing: raise NOT_FOUND; disabled: DISABLED
2. acquire single-flight lock   → already running: SKIPPED
3. read snapshot as of clock    → absent or stale: NO_DATA
4. read portfolio + risk state
5. CyclePlanner.plan(...)         ← pure, no I/O
6. if halted → cancel_all, persist, return HALTED
7. if dry_run → persist nothing, return DRY_RUN
8. persist planned orders         ← write-ahead, before submitting
9. Executor.submit
10. persist execution, fills, equity point
11. return TRADED | NO_DRIFT
```

**Step 8 precedes step 9 deliberately.** A process that dies between submitting
and recording leaves orders at the exchange with no local record — the worst
state available. Writing intent first leaves a persisted order with no
confirmation, which the next cycle can reconcile. The reverse ordering leaves
nothing to reconcile from.

**Steps 3–5 read, step 9 writes, and nothing reads after the write,** so no
mid-cycle price move can produce a decision based on two views of the market.

### Idempotency

Every `PlannedOrder` carries `client_order_id = hash(strategy_id,
cycle_timestamp, symbol, side)`. Both venues support client order IDs — Indodax
has `get_order_by_client_order_id` and `cancel_by_client_order_id`, Tokocrypto
is Binance-style — so a retried submission is rejected by the exchange as a
duplicate rather than doubling the position.

This makes the dangerous case survivable: **a transport failure on submit is
never blindly retried.** The order may or may not have landed. The cycle
records the attempt as unconfirmed and returns; the next cycle queries by
client order ID and reconciles. Automatic retry on timeout is how one intended
position becomes two.

### Failure taxonomy

| Situation | Behaviour |
|---|---|
| Strategy missing | raise `NOT_FOUND` — caller error |
| Strategy disabled | return `DISABLED` |
| Snapshot absent or older than `max_age` | return `NO_DATA` |
| Risk rule trips | `cancel_all`, then return `HALTED` with `halted_by` |
| Order rejected by venue rules | already in `OrderPlan.rejected`, not an error |
| Executor transport failure | persist unconfirmed, return, reconcile next cycle |
| `cancel_all` fails during a halt | escalate: log error, persist the halt flag |

The last row is deliberate. A halt whose cancellation failed has left live
orders in the market with no supervision, so the halt flag persists, every
subsequent cycle re-attempts the cancel, and nothing new is opened. The failure
gets louder rather than quieter.

Staleness matters more than absence: a snapshot four hours old will size a real
order at a dead price. `max_age` is checked explicitly by the engine rather
than trusted to the collector.

### Concurrency

The single-flight lock is **database-level, keyed by strategy id**, not an
in-process `asyncio.Lock`. Two overlapping cycles would each size against a
portfolio the other is about to change, and an in-process lock silently stops
working the moment a second worker process exists while still appearing
correct.

### Determinism

The engine takes `Clock`; the backtester never does. A backtest's time comes
from the replayed snapshots, so a run is reproducible from stored data alone.
With `CyclePlanner` pure, a backtest result is a function of data and strategy
config and nothing else — which is what makes the PBO gate meaningful rather
than a measurement of scheduling noise.

### Backtest guards

`Backtesting.run` refuses rather than approximates. Coverage gaps beyond
tolerance raise `VALIDATION`, and so does a window shorter than the strategy's
longest feature lookback. Both would otherwise produce a plausible report from
data that cannot support it, and a plausible wrong number is more dangerous
than an error.

## Testing

`CyclePlanner` is pure, so it joins the algorithm blocks — no mocks, construct
and assert — and gets a conformance suite: a halted risk state yields an empty
plan, dry-run and live planning produce identical plans for identical inputs,
every intent is accounted for.

The usecases are async with injected dependencies, so they follow
`tests/fakes/`: hand-written in-memory repositories plus a `FakeExecutor` and
`FakeClock`, with `make_*` builders beside the existing ones. No mocking
library; the existing tests use none and these need none.

**`Executor` gets a conformance suite**, and it matters most: paper and live
must agree on the contract, because promoting a strategy from paper to live
rests on that. Invariants — submitting one client order ID twice produces one
order; `cancel_all` is safe when nothing rests; every submitted order appears
exactly once in `accepted` or `rejected`.

Each safety property from the cycle gets a named test, because their absence is
invisible until it costs money:

- planned orders are persisted before `submit` is called
- a transport failure produces an unconfirmed record and no retry
- the next cycle reconciles by client order ID rather than re-submitting
- a tripped risk rule calls `cancel_all` before returning `HALTED`
- a failed `cancel_all` persists the halt flag and the next cycle retries it
- a second concurrent cycle returns `SKIPPED`
- a stale snapshot returns `NO_DATA`
- collection with one venue failing still persists the other's data
- a backtest over a gapped window raises

## Presentation

**`presentation/cron/`**, a new sibling of `http/`, structured the same way:
`tasks/` as the analogue of `routers/`, `schedule.py` naming cadences, and its
own `dependencies/` resolving from the same `Container`. Three tasks — collect
market data, sync portfolio, run the engine cycle. Each is thin: resolve the
usecase, call its single step, log the result.

**`presentation/http/`** gains `routers/trading.py` and matching schemas. The
surface is read-heavy — strategies CRUD, backtest and validation runs,
portfolio and equity curve, cycle history — plus two deliberate writes: run a
backtest, and `run_cycle` with `dry_run=true` so an operator can ask what the
engine would do without touching the market.

New permissions are seeded through the existing `permission.json`. **Live cycle
execution gets no route**: it is reachable only from cron. An HTTP endpoint
that places real orders is an attack surface with no compensating benefit,
since the engine runs on a schedule anyway.

## Wiring

`composition/main/infrastructure.py` gains the repositories, both executors,
the clock and the concrete algorithm blocks; `application.py` constructs the
seven usecases into `Container`; `launcher.py` starts cron alongside the HTTP
app. `Container` grows but keeps its shape.

**Strategy blocks are built per `StrategyConfig`, not once at startup.** A
`StrategyFactory` in composition turns a stored config into a `Strategy` and
its risk overlay. Otherwise the engine can only run the pipeline wired at boot
and `StrategyManagement` is decorative.

## Out of scope

- Storage engine choice for market data — still open from summary 004.
- The migration and ORM work for the new repositories.
- Any real strategy configuration; the seeded strategies are the controls.
