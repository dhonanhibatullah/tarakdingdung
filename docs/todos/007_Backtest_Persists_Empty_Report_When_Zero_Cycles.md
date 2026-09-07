# 007 — Backtest persists an all-zero report when it ran 0 cycles

- **Severity:** low (becomes moot once `001` is fixed, but worth a guard regardless)
- **Status:** done (fixed 2026-09-07, with `001` — commit `4caf67c`)
- **Detected:** 2026-09-07
- **Area:** `application/trading/backtest/usecase.py`

## Resolution

`BacktestingUsecase.run` now raises after the loop when `cycles == 0`:

```python
if cycles == 0:
    err = DomainError(
        "backtest produced no evaluable cycles: candle coverage passed "
        "the gate but no usable snapshot could be built over the window",
        ErrorType.VALIDATION)
    ...
    raise err
```

Nothing is persisted. The message is distinct from the `_require_coverage`
gate's, so the two failure modes are told apart. Covered by
`test_raises_when_the_window_yields_no_evaluable_cycle`.

The optional "far below expected step count" flag was **not** added — after
`001` a covered window replays fully, and a partial replay from a genuine
mid-window gap is already surfaced by `min_completeness` and (now) by the
trailing gaps from `006`.

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
