# 001 — Backtest replay is non-functional and fails silently

- **Severity:** blocker
- **Status:** done (fixed 2026-09-07)
- **Detected:** 2026-09-07, Docker run against real DB + live Indodax data
- **Area:** `application/trading/backtest/`, `infrastructure/repository/market_data/`, `application/trading/collection/`
- **Also breaks:** walk-forward validation (`POST /api/v1/trading/validations`), which replays through the same engine, and therefore PBO / overfitting scoring.

## Resolution

The replay now builds its snapshot from the **candle series alone** — it no
longer touches the live `prices` / `order_books` tables, which only ever hold a
"latest" row.

- **New `MarketDataRepository.read_replay_snapshot`** (`domain/contracts/repository/market_data.py`,
  impl in `infrastructure/repository/market_data/repository.py`): reads only
  *closed* candles (`open_time` **strictly** before `as_of` — a new
  `inclusive=False` path on `build_read_candles_before`, so the bar opening at
  a step boundary, which has not closed, is never seen). `last_prices` is the
  close of the newest closed candle; `books` is left empty. A symbol whose
  newest closed candle is older than `max_age` is omitted, so a mid-window gap
  is skipped rather than sized against a stale bar. The live `read_snapshot` is
  untouched.
- **New `application/trading/backtest/replay.py`** — `synthetic_book(candle,
  …)` expands a bar into a `levels`-deep ladder each side of the close
  (`half_spread` at level 0, `+ level_step` per rung), each rung holding
  `volume / levels`. A small order pays the spread only; a larger one walks the
  ladder and accrues slippage via `DepthWalkCostModel`; an order bigger than
  the bar's volume is `fillable=False` → rejected, not filled at an invented
  price. A zero-volume bar yields zero-size rungs → every order rejected
  (visible in the rejected count). `replay_snapshot(base, …)` fills the book
  gap for any symbol that lacks one.
- **`simulation.py`** — a fill now crosses the spread: `_fill_price` takes the
  near touch of the book (`asks[0]` for a buy, `bids[0]` for a sell) instead of
  the strategy's own limit, so the spread is paid and the cost model's slippage
  is only the extra from walking deeper.
- **`BacktestingUsecase`** — steps via `read_replay_snapshot` + `replay_snapshot`;
  synthetic-book shape is constructor-configurable
  (`replay_half_spread` 5bps, `replay_book_levels` 5, `replay_level_step` 5bps).
  It now **raises** `VALIDATION` when the window yields 0 evaluable cycles
  instead of persisting an all-zero report (also closes `007`).

**Verified in Docker** against real Indodax candles: a `pipeline` / momentum
strategy backtest over an 8-day window returned `trade_count: 70`,
`total_return: -4.6%`, `sharpe: -3.9`, `turnover: 16.8`, `cost_drag: 3.4%`
(the momentum baseline loses after costs — an honest result). Walk-forward
validation produced a real PBO verdict (`probability 0.17`, `passed: false`)
instead of erroring.

Tests: `tests/application/trading/test_backtest_replay.py` (new),
`tests/application/trading/test_backtest_and_validation.py` (extended). Full
suite 734 passing.

---

## Original analysis

## Symptom

`POST /api/v1/trading/backtests` over a window that is fully covered by stored
candles returns **HTTP 201** with an all-zero report:

```json
{"report":{"total_return":0.0,"sharpe":0.0,"sortino":0.0,"max_drawdown":0.0,
           "turnover":0.0,"gross_return":0.0,"net_return":0.0,"cost_drag":0.0,
           "trade_count":0}}
```

There is no error. A user reads this as "my strategy chose not to trade" when
in fact **the backtest never ran a single decision that could fill**.

## Root cause — the collector stores point-in-time snapshots, the replay needs series

`MarketDataCollectionUsecase._collect_symbol` writes, per run:

- a full **candle series** (`write_candles`) — ✅ stored as history
- **one** `prices` row, stamped at `candles[-1].open_time` (the *newest* bar)
- **one** `order_books` row, stamped "now"

So `prices` and `order_books` only ever hold the *latest* observation. Verified
in the running DB: after two collect runs, `prices` had 4 rows for 2 symbols,
all with `captured_at = 1788786000000` (the newest candle time).

The replay needs both as a historical series:

### Bug A — `read_snapshot` gates the entire snapshot on a `prices` row ≤ as_of

`SqlAlchemyMarketDataRepository.read_snapshot` (`infrastructure/repository/market_data/repository.py`):

```python
prices = await self.read_prices(symbols=symbols, as_of=as_of, max_age=max_age)
...
for symbol in prices:          # <-- only symbols with a fresh price row
    candles[symbol] = await self._lookback(...)
```

`read_prices` is bounded by `captured_at <= as_of` **and** `>= as_of - max_age`
(`max_age = interval_ms * 2` = 2h in the backtest). For any historical `as_of`
the only price rows are stamped *after* it, so `read_prices` returns `{}`, the
loop body never runs, and `read_snapshot` returns an empty `MarketSnapshot`.
The backtest loop then hits `if not snapshot.last_prices: continue` on **every
iteration** → `cycles = 0` → empty report.

*Evidence:* with real data, `BacktestingUsecase.run` over `1788100000000..1788780000000`
returned `cycles: 0`. Injecting a synthetic `prices` row per candle
(`captured_at = open_time`) raised it to `cycles: 189`.

### Bug B — `simulate()` requires a historical order book, which is never stored

Even with prices fixed, `application/trading/backtest/simulation.py::simulate`:

```python
book = snapshot.books.get(order.symbol)
price = _price(order, snapshot)
if book is None or price is None:
    unfilled += 1
    continue
```

`read_snapshot` fills `books` from `read_book(symbol, as_of)`, which reads the
`order_books` table — one "latest" row. For a historical `as_of`, `read_book`
returns `None`, so **every planned order is `unfilled`**.

*Evidence (instrumented replay, synthetic prices in place):*
`TOTAL planned orders across window: 134`, `cycles where an order had a book present: 0`,
`trade_count: 0`. The strategy *does* produce orders
(`weights: {BTC/IDR: 0.25}`, `orders: [(BTC, BUY, 0.00182...)]`) — they just
never fill.

## Why the live engine looks fine

`TradingEngineUsecase` and the `dry-run` route call the **same**
`read_snapshot`, but with `as_of = now`. The single "latest" `prices` /
`order_books` rows are within `max_age` of `now`, so the live snapshot is
populated and a cycle can plan and (paper-)fill. The divergence is entirely
about **historical** `as_of`.

## Suggested direction

The replay must not depend on a dense historical order-book series — a REST
poller can never produce one. Options, roughly in order of preference:

1. **Derive the reference price and a synthetic book from the candle bar.**
   In the backtest path, price = bar close (or open of the next bar to avoid
   look-ahead); model fills against a synthetic book built from the bar
   (e.g. close ± a spread/impact parameter) and keep charging the cost model.
   Removes the `prices` and `order_books` dependency from replay entirely.
2. Alternatively, in `read_snapshot`, when no `prices` row ≤ `as_of` exists,
   fall back to the close of the newest candle ≤ `as_of` for `last_prices`,
   and have `simulate` synthesise a book from that candle when
   `snapshot.books` is empty.
3. Least good: have the collector persist a price/book row per candle. Heavy,
   makes `prices` a candle duplicate, still no real historical book depth.

Whichever path: a backtest that materialises **0 usable snapshots** should
`raise` (see `007`), not persist a zero report.

## Repro

```bash
# with the stack up and Indodax candles collected for an enabled strategy
curl -s -XPOST localhost:<port>/api/v1/trading/backtests \
  -H "authorization: Bearer $TOK" -H 'content-type: application/json' \
  -d '{"strategy_id":"<id>","window_start":1788400000000,"window_end":1788780000000,
       "initial_equity":"10000000","interval":"1h","min_completeness":0.5}'
# -> 201, report all zeros, trade_count 0, despite full candle coverage
```
