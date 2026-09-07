# 005 — `prices` and `order_books` grow unbounded (INSERT, not upsert; no retention)

- **Severity:** low
- **Status:** open
- **Detected:** 2026-09-07
- **Area:** `application/trading/collection/`, `infrastructure/repository/market_data/queries.py`

## Symptom

Every `collect` run appends one `prices` row and one `order_books` row per
symbol via a plain `INSERT` (`build_insert_price`, `build_insert_book`).
`write_candles` upserts; these two do not.

After two collect runs for two symbols the DB held **4** `prices` rows and
**4** `order_books` rows, all with the same `captured_at` (the newest candle
time). At the default 5-minute collect cadence this is ~576 rows/symbol/day
with no dedup and no pruning.

`order_books` rows also store full bid/ask arrays as JSON, so the table grows
faster than a row count suggests.

## Why it matters

- Unbounded growth on tables that only ever need "the latest" (for the live
  engine) plus, at most, a short retention window.
- Duplicate rows with identical `captured_at` are pure noise —
  `read_prices` / `read_book` only ever want the most recent ≤ `as_of`.

## Suggested direction

- Upsert on `(venue, base, quote)` for `prices` and `order_books`, keeping only
  the latest — **or** keep the append model but add a retention sweep (e.g.
  delete rows older than N days) and a `captured_at` index.
- If a historical price/book series is ever wanted (e.g. for `001`), design
  that table deliberately with an interval and a retention policy rather than
  letting the current one accrete.
