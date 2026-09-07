# Algorithm Layer — Design

- **Date:** 2026-09-07
- **Status:** approved
- **Scope:** contracts and models; Phase 3 implementations added 2026-09-07
- **Source:** `docs/researches/summaries/004_Automated_Trading_Engine_Implementation_Plan.md`

## Problem

Summary 004 specifies a single strategy seam — `decide(snapshot) -> weights` —
but says nothing about the internals. Written as one function, a strategy would
tangle universe selection, indicator maths, sizing, risk caps and venue rounding
into a body that cannot be tested in pieces and cannot be varied one part at a
time. The layer needs seams.

## Decisions

Four decisions constrain every signature in the package. They were settled
before the block inventory because each one changes all of it.

**Domain dataclasses, stdlib only.** Blocks exchange frozen slots dataclasses
defined in `domain/models/`. `domain/` imports nothing outside the standard
library. Numeric libraries, if any are wanted, live inside infrastructure
implementations and convert at their own boundary. This keeps the domain
swappable and keeps every field name visible to the type checker, at the cost of
hand-written indicator maths.

**Synchronous, pure blocks.** No `async`, no I/O, no clock, no network. The rest
of `domain/contracts/` is uniformly `async` because it genuinely performs I/O;
these blocks do not, and the signature should say so. Purity is the property
that makes a block backtestable, and a backtester calling these millions of
times pays no event-loop overhead.

**Typed stages plus an explicit composition seam.** Each block has its own
contract with distinct input and output types, so pipeline order is enforced by
the type checker. Above them sits one `Strategy` contract, which is all the
backtester, paper trader and live engine ever see. Blocks where multiplicity is
natural — feature extractors, risk rules — compose within their own type: a
composite risk rule is itself a `RiskRule`. Flexibility is confined to the
places that need it, rather than achieved by making every block accept a
bag-of-anything context object.

**Full contract surface up front.** Every block the plan implies is defined now,
including the evaluators the backtester will need, so later phases add
implementations rather than reshaping interfaces.

## Blocks

All in `domain/contracts/algorithm/`.

### The live chain

Each block's output type is the next block's input type.

| File | Contract | Signature |
|---|---|---|
| `universe.py` | `UniverseSelector` | `select(snapshot) -> tuple[Symbol, ...]` |
| `feature.py` | `FeatureExtractor` | `compute(snapshot) -> FeatureSet` |
| `signal.py` | `SignalGenerator` | `generate(features) -> Signals` |
| `allocation.py` | `Allocator` | `allocate(signals, portfolio) -> TargetWeights` |
| `risk.py` | `RiskRule` | `apply(weights, portfolio, state) -> TargetWeights` |
| `rebalance.py` | `Rebalancer` | `plan(target, portfolio, prices) -> tuple[TradeIntent, ...]` |
| `order.py` | `OrderPlanner` | `plan(intents, rules) -> OrderPlan` |

Why the seams fall here:

- **`UniverseSelector` is its own block** because "which symbols may I hold" is
  a liquidity and listing question, unrelated to conviction. Pinning the v1
  symbol universe becomes an implementation of this rather than a constant
  buried in a strategy.
- **`Allocator` is split from `SignalGenerator`** because *how strongly do I
  believe* and *how much do I bet* have different failure modes. The same
  momentum signal with volatility-targeted sizing instead of equal weight is a
  different risk profile with no change to the signal code.
- **`RiskRule` is post-allocation and idempotent** — `TargetWeights ->
  TargetWeights`. That is what allows a chain: per-coin cap, per-venue cap,
  volatility kill-switch and daily-loss halt are four independent rules.
  Idempotence is required so composing them cannot compound their reductions.
  Adding a control is adding a file, never editing the pipeline.
- **`Rebalancer` is split from `OrderPlanner`** because they answer to different
  masters. The rebalancer applies our policy — no-trade bands, turnover caps —
  deciding what is worth trading. The order planner applies the venue's rules —
  tick size, step size, min notional — and is where an intent is rejected for
  being too small to place. Merging them produces backtests that trade
  quantities the exchange refuses.

### Evaluators

Used by the backtester and reporting, not in the live chain.

| File | Contract | Signature |
|---|---|---|
| `cost.py` | `CostModel` | `estimate(order, book) -> CostEstimate` |
| `metric.py` | `PerformanceEvaluator` | `evaluate(curve, fills) -> PerformanceReport` |
| `validation.py` | `OverfittingTest` | `evaluate(trials) -> OverfittingReport` |

`CostModel` is a contract rather than a function because at least three are
needed: a flat taker fee for smoke tests, a depth-walking model for honest
backtests, and a deliberately pessimistic one for stress runs. `OverfittingTest`
is the PBO gate from reference 010, kept as an interface so a cheaper robustness
proxy can stand beside it.

### Composition seam

| File | Contract | Signature |
|---|---|---|
| `strategy.py` | `Strategy` | `decide(snapshot, portfolio) -> TargetWeights` |

Exactly the boundary summary 004 §2 specifies. A `PipelineStrategy` in
infrastructure chains universe → feature → signal → allocation; a later trained
policy is a different `Strategy` that skips the chain entirely. Neither is
visible to callers.

**The risk overlay sits outside the strategy, not at the end of the pipeline.**
An earlier draft of this section put `risk` at the tail of the chain, which
cannot work: `RiskRule` needs a `RiskState` — peak equity, daily P&L, trailing
volatility — that `Strategy.decide` does not receive and should not, because
that state is history the engine owns rather than a fact about the market.
Summary 004 §5 already places the risk manager between strategy and executor,
and keeping it there is better anyway: the overlay then applies to *every*
strategy, including ones that never use this pipeline. The engine's cycle is
`decide → risk → rebalance → plan orders → execute`.

Not in this package: clocks, repositories, exchange clients, order submission.
Sending a `PlannedOrder` belongs to `domain/contracts/execution/`, as summary
004 §5 maps it.

## Models

Four files in `domain/models/`, matching the existing flat layout.

**`Decimal` versus `float` splits by role.** `Decimal` for anything that becomes
an exchange field or a ledger entry: prices, quantities, fees, cash, equity.
`float` for dimensionless statistics: feature values, signal scores, weights,
Sharpe. The two meet at exactly one place — the `Rebalancer`, which takes float
weights and a Decimal portfolio and emits Decimal quantities. One auditable
conversion point beats conversions scattered through the layer.

**Time is `int` epoch milliseconds, UTC.** Both exchanges speak milliseconds on
the wire, so this needs no translation, sorts trivially, and makes a timezone
bug structurally impossible.

**Symbols carry their venue.** Cross-exchange arbitrage is a v1 candidate, so
the same pair on two exchanges must be distinguishable — the price difference is
the entire trade. `Symbol(venue, base, quote)` is hashable and usable as a dict
key; wire formats stay an infrastructure concern. Risk rules aggregate over
`.venue` for the per-venue cap and `.base` for the per-coin cap, both free from
the key.

### `market.py`

```
Venue(StrEnum): INDODAX | TOKOCRYPTO
Symbol(venue, base, quote)
Candle(open_time, open, high, low, close, volume)
BookLevel(price, quantity)
OrderBook(symbol, timestamp, bids, asks)
SymbolRules(symbol, tick_size, step_size, min_notional, maker_fee, taker_fee)
MarketSnapshot(timestamp, candles, books, last_prices)
```

`MarketSnapshot` is the lookahead-bias boundary and the most important object in
the design. Its contract, owed by whoever constructs it — the collector, the
backtester — and stated in its docstring:

- every datum it holds has a timestamp at or before `snapshot.timestamp`, and
  `candles` holds closed candles only, ordered oldest to newest;
- stale data is omitted rather than carried, because a four-hour-old price looks
  valid and will size a real order.

Because `Strategy.decide` takes nothing else, a strategy cannot see the future.
This is what lets the backtest and the live engine run the same code path
honestly.

`SymbolRules` carries fees alongside tick, step and min-notional so the cost
model and order planner read venue economics from one place.

### `portfolio.py`

```
Position(symbol, quantity, average_price)
Portfolio(timestamp, cash, positions, equity)     # cash: Mapping[Venue, Decimal]
RiskState(timestamp, equity_peak, daily_pnl, realized_volatility, halted)
```

Cash is per venue because it genuinely is: IDR on Indodax cannot buy anything on
Tokocrypto, and transfers take real time. A single cash balance would let the
backtester execute trades the live engine cannot.

`RiskState` is separate from `Portfolio` because it is history-derived — peak
equity, today's P&L, trailing volatility — while `Portfolio` is a point-in-time
fact. Keeping them apart lets the drawdown and volatility rules stay pure.

### `algorithm.py`

```
FeatureSet(timestamp, values)          # Mapping[Symbol, Mapping[str, float]]
Signals(timestamp, scores)             # Mapping[Symbol, float] in [-1, 1]
TargetWeights(timestamp, weights)      # Mapping[Symbol, float], sum(abs) <= 1
Side, OrderType, TimeInForce (StrEnum)
TradeIntent(symbol, side, quantity, reference_price)
PlannedOrder(symbol, side, type, quantity, price, time_in_force, client_order_id)
RejectionReason(StrEnum), RejectedIntent(intent, reason)
OrderPlan(orders, rejected)
CostEstimate(fee, slippage, total, fillable)
```

`CostEstimate.fillable` exists because thin IDR books are a named risk in
summary 002. The honest answer to "what does this order cost" is sometimes "the
book cannot absorb it", and a model that returns a number anyway flatters every
backtest.

### `performance.py`

```
Fill(symbol, side, quantity, price, fee, timestamp)
EquityPoint(timestamp, equity)
PerformanceReport(total_return, sharpe, sortino, max_drawdown,
                  turnover, gross_return, net_return, cost_drag, trade_count)
TrialResult(label, parameters, returns)
OverfittingReport(probability, threshold, passed)
```

`PerformanceReport` carries gross and net side by side with an explicit
`cost_drag` because summary 004 Phase 2 requires it. A strategy that looks good
gross and dies net is the most common outcome, and it should be impossible to
read the report without seeing that.

Frozen dataclasses holding a `Mapping` are not deeply immutable. Annotating
`Mapping` rather than `dict` means consumers cannot mutate through the declared
type, which the type checker enforces. Runtime immutability via
`MappingProxyType` at every construction site was considered and rejected as
ceremony out of proportion to the risk.

## Errors and edge cases

A block that raises mid-backtest kills a multi-year run. These blocks are total
functions where the situation is normal and raise only where it is a bug.

**Missing or insufficient data is not an error.** A 200-period average on a
symbol with 40 candles has no answer, so `FeatureExtractor` omits that symbol.
An absent key propagates harmlessly: no feature, no signal, no weight, no
position. This is the normal state at the start of every backtest and for weeks
after any new listing, so every block iterates what it was given and never
assumes a key exists.

**Contract violations raise `DomainError(..., ErrorType.VALIDATION)`.** Weights
summing above one, negative quantities, a signal outside `[-1, 1]`, NaN or
infinity anywhere. These are programming errors and must fail at the moment of
creation, because a silently clamped NaN produces a backtest that looks fine and
means nothing. No new `ErrorType` members are needed.

Where the check lives is a performance decision: **per-cycle objects validate in
`__post_init__`; per-row market data does not validate at all.** `FeatureSet`,
`Signals`, `TargetWeights`, `TradeIntent`, `PlannedOrder`, `CostEstimate` and
`OverfittingReport` are built a handful of times per cycle, so checking them is
free. `Candle` and `BookLevel` are built in the millions when replaying history;
they carry no validation and are trusted to the collector that wrote them.

**Risk trips are decisions, not exceptions.** When the volatility kill-switch
fires or the daily-loss limit hits, `RiskRule` returns reduced or empty weights.
A halt must appear in the equity curve as a flat period, not in a stack trace.

**Venue rejections are returned as data.** `OrderPlanner` returns an `OrderPlan`
carrying both placeable orders and rejected intents with reasons, rather than a
bare tuple of orders. An intent that silently vanishes below min-notional is the
most common source of unexplained live-versus-backtest divergence, and a
signature that discards the reason guarantees the question cannot be answered.
Every input intent appears exactly once across `orders` and `rejected`.

**Determinism.** No block reads a wall clock or a global RNG. Time comes only
from `snapshot.timestamp`; any block wanting randomness takes an explicit seed.
Without this a failed backtest cannot be reproduced and the PBO gate measures
noise.

**Staleness beats absence.** A four-hour-old price is more dangerous than a
missing one because it looks valid. Snapshots omit stale data rather than carry
it — an obligation on the collector and backtester, not on the blocks.

## Testing

Synchronous and pure means tests need no event loop, fixtures, mocks, clock
patching or database: construct inputs, call, assert on the return value.

Contracts-only scope means this change ships few tests, because ABCs have no
behaviour. The executable code here is the `__post_init__` invariant checking,
so that is what is tested now — boundaries and accepted values, not only
failures — plus the standard check that each ABC cannot be instantiated,
matching `tests/domain/test_contracts.py`.

**Conformance suites are specified now and written in Phase 3.** Because
`RiskRule`, `CostModel`, `Allocator` and `OrderPlanner` will each have several
implementations, their invariants belong to the contract rather than to any one
implementation, and each gets a parametrized suite every implementation must
pass:

- `RiskRule` — idempotent; never increases gross exposure; output satisfies the
  `TargetWeights` invariant; a halted `RiskState` produces empty weights.
- `Allocator` — gross exposure at most one; emits only symbols present in the
  input signals; zero signals produce zero weights.
- `CostModel` — cost non-negative; non-decreasing in order size; `fillable` is
  false whenever requested size exceeds book depth.
- `OrderPlanner` — every input intent appears exactly once across `orders` and
  `rejected`.

A new risk rule then costs one file and one line registering it with the suite,
and cannot regress the invariants.

Property-based testing with Hypothesis is the natural fit for those invariants
and was deliberately deferred: it is a new dev dependency, and adding it in a
change that ships no implementations buys nothing. Revisit in Phase 3.

Not tested: the ABCs themselves, and anything requiring a live exchange. The
seam between this layer and reality is `MarketSnapshot`, fed by fixtures.

## Known gaps

**Volatility targeting cannot be expressed.** `Allocator.allocate(signals,
portfolio)` does not receive the `FeatureSet`, so an allocator cannot size
positions by realised volatility — the standard way to equalise risk across
assets. `EqualWeightAllocator` and `ConvictionWeightedAllocator` work within the
signature; a volatility-targeting one would need features threaded through,
either by widening the signature or by having the signal generator fold
volatility into the score. Deferred rather than patched: the right fix depends
on whether Phase 3 backtests show equal weighting is actually the binding
constraint, and widening the signature now would be guessing.

**Spot-only is a convention, not an invariant.** `TargetWeights` permits
negative weights, but neither venue supports shorting, so every v1
implementation is long-only by default. The models allow shorts so that an
offshore perp venue would not require reshaping the layer; nothing yet stops a
strategy from emitting a weight it cannot hold.

## Out of scope

- The backtester, the collector, the executor and the engine loop.
- Persistence of any model in this layer.
