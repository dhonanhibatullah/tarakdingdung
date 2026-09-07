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
| 003 | `003_Tokocrypto_Signed_API_Forbidden_2015.md` | Signed Tokocrypto `/api/v3` calls return `-2015`. **Root cause confirmed:** the key is valid + trade-enabled but only on the **legacy `/open/v1`** host — not the Binance-standard `.site` host the v3 migration targeted. IP and permissions ruled out. Fix is Path A (get a standard-API key) or Path B (scoped partial revert: market data on `/api/v3`, signed trading back on `/open/v1`). Key also has withdraw enabled — regenerate withdraw-disabled. | high | **open — awaiting operator decision (A or B)** |
| 004 | `004_Paper_Trading_Via_Engine_Not_Simulated.md` | A PAPER strategy stepped by the cron engine wrote orphaned fills; the portfolio is rebuilt from real venue balances, so paper positions never materialised. | medium | **done** |
| 005 | `005_Prices_And_Order_Books_Grow_Unbounded.md` | The collector `INSERT`ed (not upserted) a `prices` and `order_books` row every run with no retention — unbounded growth, duplicate rows. | low | **done** |
| 006 | `006_Coverage_Completeness_Below_One_With_No_Gaps.md` | `GET /trading/coverage` reported `completeness < 1.0` with an empty `gaps` list when the window extends past the newest stored candle — misleading for the "check before trusting a backtest" use case. | low | **done** |
| 007 | `007_Backtest_Persists_Empty_Report_When_Zero_Cycles.md` | When a backtest materialised 0 usable snapshots it still returned HTTP 201 and persisted an all-zero report instead of raising, the way the coverage gate does. | low | **done** (with 001) |
| 008 | `008_Compose_Builds_A_Separate_Image_Per_Service.md` | `backend` and `seeder` built two separate images from an identical build config, so `docker compose build backend` left the seeder on stale code — an app/schema skew. Surfaced while verifying `005`'s migration. | medium | **done** |

## Verification context

All findings were observed on 2026-09-07 running the backend in Docker against
the real Postgres at `192.168.18.18:15432` and the live Indodax / Tokocrypto
APIs. Auth, RBAC/admin, profile, and strategy-management HTTP surfaces were
exercised end-to-end and behaved correctly (38 checks; the only "failures"
were wrong expectations in the test script — `PATCH` returns `204`,
`VALIDATION`/`BAD_ARGS` map to `400`). Market-data collection from Indodax
(candles), portfolio sync from Indodax balances, and a live engine cycle in
PAPER mode all worked. The problems were concentrated in the **backtest /
validation replay path** and **Docker packaging**.

## Status

**001, 002, 004, 005, 006, 007, 008 are fixed** (full test suite 741 passing;
each re-verified in Docker against the real DB + live Indodax data). **003
remains open** — it is a credentials / IP-allowlist issue that no code change
resolves; see the file for the operator steps.
