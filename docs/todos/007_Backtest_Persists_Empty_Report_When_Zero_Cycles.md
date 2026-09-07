# 007 — Backtest persists an all-zero report when it ran 0 cycles

- **Severity:** low (becomes moot once `001` is fixed, but worth a guard regardless)
- **Status:** open
- **Detected:** 2026-09-07
- **Area:** `application/trading/backtest/usecase.py`

## Symptom

When `BacktestingUsecase.run` iterates its timeline and **every** iteration
hits `if not snapshot.last_prices: continue` (see `001`), it falls through
with `cycles = 0`, an untouched equity curve, no fills — and still:

- builds a `PerformanceReport` of all zeros,
- returns `RunBacktestResult` normally (HTTP `201`),
- **persists** the run via `_persist` when `request.persist` is set.

The stored/returned run is indistinguishable from "a strategy that genuinely
never traded over a fully-covered window".

## Contrast

The class docstring says *"Refuses rather than approximates"*, and
`_require_coverage` does exactly that — it `raise`s `VALIDATION` when
`completeness < min_completeness`. But that gate is satisfiable while the
replay still produces nothing (e.g. the window has candles but the
`prices`/`order_books` series needed to step it does not — `001`).

## Suggested direction

After the loop, if `cycles == 0` (no snapshot ever materialised), `raise
DomainError(..., ErrorType.VALIDATION)` with a message that distinguishes it
from the coverage failure — e.g. *"backtest produced no evaluable cycles over
the window; candle coverage passed but no usable snapshot could be built"*.
Do not persist.

Optionally also refuse (or clearly flag) when `cycles > 0` but far below the
expected number of steps, so a mostly-empty replay can't masquerade as a real
result.
