# TODOs — Contents Overview

Index of every file in `todos/`. One problem per file. Keep this table in sync
on every add, resolve, or retire. Numbers are never reused.

**Status legend:** `open` — confirmed, not yet fixed · `in progress` — being
worked · `done` — fixed and verified · `wontfix` — deliberately not addressed
(reason in the file).

| #   | File | Problem | Severity | Status |
|-----|------|---------|----------|--------|
| 001 | `001_Backtest_Replay_Non_Functional.md` | Backtest (and walk-forward validation) replayed 0 cycles / 0 trades against real collected data and returned an all-zero report with no error. The collector never stores the historical price & order-book *series* the replay needs. | blocker | **done** |
| 002 | `002_Docker_Compose_Port_Mismatch_Unhealthy.md` | `docker compose up` produced a permanently-unhealthy container and an unreachable host port whenever `TRDD_BE_HTTP_PORT` was set (the project's own `.env.example` sets it). | high | **done** |
| 003 | `003_Tokocrypto_Signed_API_Forbidden_2015.md` | Every signed Tokocrypto `/api/v3` call returns `-2015` (invalid key / IP / permission). Tokocrypto balance sync and order placement are unavailable; the live order path is still completely unexercised. | high | open |
| 004 | `004_Paper_Trading_Via_Engine_Not_Simulated.md` | A PAPER strategy stepped by the cron engine writes orphaned fills; the portfolio is rebuilt from real venue balances, so paper positions never materialise. `fills` cannot distinguish paper from live. | medium | open |
| 005 | `005_Prices_And_Order_Books_Grow_Unbounded.md` | The collector `INSERT`s (not upserts) a `prices` and `order_books` row every run with no retention — unbounded growth, duplicate rows. | low | open |
| 006 | `006_Coverage_Completeness_Below_One_With_No_Gaps.md` | `GET /trading/coverage` reports `completeness < 1.0` with an empty `gaps` list when the window extends past the newest stored candle — misleading for the "check before trusting a backtest" use case. | low | open |
| 007 | `007_Backtest_Persists_Empty_Report_When_Zero_Cycles.md` | When a backtest materialises 0 usable snapshots it still returns HTTP 201 and persists an all-zero report instead of raising, the way the coverage gate does. | low | open |

## Verification context

All findings below were observed on 2026-09-07 running the backend in Docker
against the real Postgres at `192.168.18.18:15432` and the live Indodax /
Tokocrypto APIs. Auth, RBAC/admin, profile, and strategy-management HTTP
surfaces were exercised end-to-end and behaved correctly (38 checks; the only
"failures" were wrong expectations in the test script — `PATCH` returns `204`,
`VALIDATION`/`BAD_ARGS` map to `400`). Market-data collection from Indodax
(candles), portfolio sync from Indodax balances, and a single live engine
cycle in PAPER mode all worked. The problems are concentrated in the
**backtest / validation replay path** and **Docker packaging**.
