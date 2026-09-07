# Algorithm Layer — Implementation Plan

- **Date:** 2026-09-07
- **Design:** `docs/superpowers/specs/2026-09-07-algorithm-layer-design.md`
- **Scope:** contracts and models only

## Order of work

The models come first because every contract signature references them, and
`market.py` comes first among the models because the other three import
`Symbol`. Tests follow the models, since the models are the only executable
code in this change.

### Step 1 — `domain/models/market.py`

`Venue`, `Symbol`, `Candle`, `BookLevel`, `OrderBook`, `SymbolRules`,
`MarketSnapshot`. No validation anywhere in this file: `Candle` and `BookLevel`
are the per-row types constructed in the millions during a replay, and
`MarketSnapshot`'s guarantees are owed by its constructor, not checkable
cheaply. `MarketSnapshot`'s docstring states those obligations explicitly.

### Step 2 — `domain/models/portfolio.py`

`Position`, `Portfolio`, `RiskState`. Imports `Symbol` and `Venue`.

### Step 3 — `domain/models/algorithm.py`

The enums, then `FeatureSet`, `Signals`, `TargetWeights`, `TradeIntent`,
`PlannedOrder`, `RejectedIntent`, `OrderPlan`, `CostEstimate`.

Private helpers at the top of the file — `_invalid`, `_check_finite`,
`_check_positive` — keep the `__post_init__` bodies to one line each. Decimal
comparisons guard `is_finite()` first, because comparing `Decimal("NaN")` raises
`InvalidOperation` rather than returning false.

Gross exposure is checked against `1.0 + 1e-9`; a tolerance is required because
weights that sum to one in exact arithmetic often do not in binary floating
point.

### Step 4 — `domain/models/performance.py`

`Fill`, `EquityPoint`, `PerformanceReport`, `TrialResult`, `OverfittingReport`.
Only `OverfittingReport` validates, bounding `probability` to `[0, 1]`.

### Step 5 — `domain/contracts/algorithm/*.py`

Eleven files, one contract each, in the order they run: `universe`, `feature`,
`signal`, `allocation`, `risk`, `rebalance`, `order`, then the evaluators
`cost`, `metric`, `validation`, then `strategy`. Each is an `ABC` with a class
docstring recording *why the seam is there*, and one-line `@abstractmethod`
bodies matching the style of `domain/contracts/utility/token.py`. All methods
synchronous.

`risk.py` and `order.py` state their invariants — idempotence, and every intent
appearing exactly once across the returned plan — in the docstring, since those
are obligations on implementers that the type system cannot express.

### Step 6 — `tests/domain/test_algorithm_models.py`

Table-driven, no fixtures. Covers, for each validating model, an accepted case
at the boundary and each rejection path: weights over one rejected and weights
at exactly one accepted; NaN and infinity rejected in features, signals and
weights; signals at exactly ±1 accepted and beyond rejected; non-positive
quantity and reference price rejected; a market order carrying a price and a
limit order missing one both rejected; negative fee and slippage rejected;
`OverfittingReport` probability outside `[0, 1]` rejected. Each rejection
asserts `ErrorType.VALIDATION`, not merely that something raised.

Also asserts the per-row types stay unvalidated — a `Candle` with absurd values
constructs fine — so the performance decision is pinned by a test rather than a
comment.

### Step 7 — `tests/domain/test_algorithm_contracts.py`

Every contract is an ABC that cannot be instantiated, and each declares exactly
the expected public method set. Mirrors `tests/domain/test_contracts.py`.

### Step 8 — Verify

Run the full suite. Confirm no import of anything outside the standard library
appears in the new `domain/` files.

## Deliberately not in this change

Implementations, the conformance suites (Phase 3, alongside the first
implementation), Hypothesis, and any change to `ErrorType`.
