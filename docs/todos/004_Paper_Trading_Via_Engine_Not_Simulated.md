# 004 — PAPER trading through the cron engine is not a real simulation

- **Severity:** medium
- **Status:** open
- **Detected:** 2026-09-07, one live engine cycle on a PAPER strategy
- **Area:** `application/trading/engine/`, `application/trading/portfolio/`, `fills` schema

## Symptom

Running a `mode = PAPER` strategy through `run_cycles` (the engine task, not
`dry-run`) with real Indodax data produced `decision = TRADED, orders = 1`.
Inspecting the DB afterwards:

- `planned_orders`: 1 row, `state = ACCEPTED`, `venue_order_id = paper-...`
- `fills`: 1 row — `ETH/IDR BUY 0.00567 @ 43,997,000, fee 499`
- `portfolio_snapshots`: 1 row — `positions: []`, `equity: 998000`
- `equity_points`: 1 row — `equity: 998000`

The fill exists, but the portfolio shows **no ETH position** and equity
**unchanged** at the real Indodax cash balance.

## Root cause

`TradingEngineUsecase._submit` calls `_portfolios.append_fills(execution.fills)`
after a paper fill, but the **portfolio itself is rebuilt from real venue
balances** by `PortfolioSyncUsecase.sync` (which polls `AccountSource`). A
paper order is never really placed, so the next sync sees no ETH and the
paper position vanishes. The paper fill is left orphaned in `fills`.

Compounding:

- The `fills` table has **no `strategy_id` and no `mode` column**
  (`id, venue, base, quote, side, quantity, price, fee, filled_at`). Paper
  fills and (future) live fills land in the same table with no way to tell
  them apart, and the equity curve / any fills-based reporting would commingle
  simulated and real trades.
- The only place a paper portfolio is actually modelled coherently is the
  backtest `simulate()` path — and that path is currently broken (see `001`).

## Effect

"Run a strategy in paper mode on the live schedule to see how it would do" is
not currently a working workflow. It records disconnected fills and leaves the
portfolio equal to the real account balance.

## Suggested direction

Decide what PAPER-on-the-engine is supposed to mean and make it consistent:

- **If paper should simulate a portfolio:** give PAPER strategies their own
  portfolio state, seeded from a configured notional, advanced by paper fills
  only — never overwritten by the real-balance sync. Add `strategy_id` (and/or
  `mode`) to `fills` and to the portfolio/equity tables, or key them by
  strategy.
- **If paper-on-the-engine is only meant to validate the plumbing (not the
  P&L):** skip `append_fills` / portfolio writes for PAPER mode entirely, and
  document that paper P&L comes only from the backtest.

Either way, `fills` needs to distinguish paper from live before any live
strategy runs, or real and simulated trades will be indistinguishable in
storage.
