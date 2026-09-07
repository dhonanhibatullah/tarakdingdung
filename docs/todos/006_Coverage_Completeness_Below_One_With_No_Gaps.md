# 006 — `GET /trading/coverage` reports `completeness < 1.0` with an empty `gaps` list

- **Severity:** low
- **Status:** done (fixed 2026-09-07 — commit `<pending>`)
- **Detected:** 2026-09-07
- **Area:** `infrastructure/repository/market_data/repository.py` (`read_coverage`, `_gaps`, `_step`)

## Resolution — `_gaps` now reports the edges too

`SqlAlchemyMarketDataRepository._gaps` takes the `window` and synthesises:

- a **leading** gap `TimeRange(window.start, first_stamp)` when the window
  starts a step or more before the first stored candle,
- a **trailing** gap `TimeRange(last_stamp + step, window.end)` when the window
  ends a step or more after the last stored candle,

alongside the interior holes it already found. An empty stamp list now yields
one gap covering the whole window. So `completeness < 1` always has a
corresponding, inspectable gap — no more silent shortfall.

**Verified in Docker:** a window ending ~10h past the newest candle returned
`completeness: 0.61` **with** `gaps: [{start: <newest+1h>, end: <window end>}]`
(previously: `0.72`, `gaps: []`).

Tests: `test_a_window_reaching_past_the_last_candle_reports_a_trailing_gap`,
`test_a_window_starting_before_the_first_candle_reports_a_leading_gap`
(`test_trading_repositories.py`); the existing interior-hole and
complete-coverage tests are unchanged and still pass.

---

## Original analysis

## Symptom

```
GET /api/v1/trading/coverage?venue=indodax&base=BTC&quote=IDR
   &window_start=1788000000000&window_end=1788999999000&interval=1h
->
{"expected":277,"present":201,"completeness":0.7256,"gaps":[]}
```

76 hours are "missing" (`expected - present`) but `gaps` is empty, so the
response gives no indication of *where* or *why* history is incomplete.

## Root cause

`_gaps` only reports **interior** holes — ranges *between two consecutive
stored stamps* that are wider than the inferred step. A window whose end is
past the newest stored candle (here `window_end` is in the future relative to
the last collected bar) inflates `expected` — `window.duration // step` —
without ever producing a gap entry, because there is no "later stamp" to
bracket the shortfall against.

A leading shortfall (window starts before the oldest stored candle) has the
same blind spot.

## Why it matters

The endpoint's stated purpose is *"the check to run before trusting a backtest
over a window"*. `72% complete, no gaps` is exactly the kind of answer that
looks fine at a glance and isn't. Combined with `001` (backtest silently
returns zeros), a user has no clear signal that a window is unbacktestable.

## Suggested direction

- Report the covered span explicitly: add `first_present` / `last_present`
  stamps to the response, or synthesise leading/trailing gap `TimeRange`s from
  `window.start → first_stamp` and `last_stamp → window.end` when those spans
  exceed one step.
- Consider clamping `expected` to `min(window.end, last_collected) - window.start`
  so `completeness` reflects "of the window that *could* be covered", with the
  trailing shortfall surfaced separately.
