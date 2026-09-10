# Project Big Goal
Using an LLM API to make profitable crypto trading decisions, wrapped in hard
deterministic safety rails.

# Core idea
A **multi-agent LLM pipeline** periodically decides the whole portfolio's target
weights (which coins, how much) and writes down its reasoning. **No LLM output
ever touches the order path directly.** A greenfield deterministic layer
validates the output, applies a risk overlay, diffs weights into orders, and
executes against **Indodax V2** (paper or live). Every decision is fully
recorded (context + prompt + response) so the past can be replayed and audited.

# Design decisions
The load-bearing choices, agreed before code was written.

| # | Decision | Choice |
|---|---|---|
| D1 | LLM vs deterministic boundary | LLM decides (universe + weights + reasoning); deterministic code owns validation, risk overlay, sizing, execution |
| D2 | Agent topology | Multi-agent pipeline (specialists → coordinator) |
| D3 | Output + cadence | Target weights + written reasoning, slow rebalance (configurable cron cadence) |
| D4 | Structured output | Pydantic-schema JSON; retry N then **hold previous weights** on failure |
| D5 | Input modalities | Text (news summaries) + numeric (candles/indicators as tables). No images |
| D6 | Backtesting | Replay recorded decisions through deterministic fill simulation |
| D7 | Universe expansion | LLM proposes symbols; deterministic code approves via hard filters |
| D8 | Data pipeline | Scrape → summarize (LLM) → decide (LLM); decisions read stored summaries, never raw firehose |
| D9 | Code reuse | Greenfield rewrite; old algorithm blocks not reused, but their safety principles are re-encoded |

# Models/Entities in this project
* `Permission`, `Role`, `RolePermission`, `User`, `Error`, `TokenClaims` are defaults
* `PortfolioSnapshot` — per-venue balances and equity, taken each cycle
* `CoinSymbol`, `Universe` — symbol identity plus membership state
  (`PROPOSED` / `APPROVED` / `REJECTED` / `REMOVED`) with approval rationale
* `Candle`, `Market` — market data
* `NewsArticle` (raw) and `NewsAnalysis` (LLM summary of one or more articles)
* `LlmDecision` — the full audit record: compiled context snapshot, exact
  prompt(s), raw response(s), parsed weights, validation result, agent traces
* `BacktestResult` — replay outcome (equity curve, Sharpe, drawdown, turnover)
* `Order`, `Execution`, `Fill` — order journal

# Domain Contracts
* `logger/` and `utility/` (password, token, transactor, websocket, clock,
  single_flight) follow almost the same as the previous codebase
* `repository/` follows the new models above
* `scrapper/` obtains news and candles, market data, and any useful data for
  analysis, either from the internet or from Indodax itself
* `llm/` — provider abstraction, prompt assembly, the agent pipeline, schema
  validation
* `trade/` — order construction, execution (paper/live), reconciliation
* `algorithm/` — greenfield pure blocks: risk overlay, rebalancer
  (weights → orders), cost model, metrics, backtest fill simulation
* There is no `api/` contract for specific API calls anymore — REST calls are
  encapsulated inside `scrapper/` or `trade/` (strict layer abstraction)

# Domain Usecases
* `admin/`, `auth/`, and `profile/` are default
* `portfolio/` (snapshots, equity), `trading/` (decision cycle, universe,
  backtest, orders)

# The decision cycle
`TradingEngine.run_cycle` is one step; cadence belongs to cron.

1. trigger (cron only) → missing config raises; disabled returns `DISABLED`
2. single-flight lock → already running returns `SKIPPED`
3. reconcile unconfirmed orders from prior cycles
4. read snapshot + portfolio → absent or stale returns `NO_DATA`
5. scrape/summarize (refresh news + candles) — partial failure is data, not an abort
6. compile context snapshot
7. run multi-agent LLM pipeline → target weights + reasoning
8. schema-validate → on failure, **hold previous weights** (no new orders)
9. deterministic risk overlay (caps, kill-switch, daily-loss halt) → may halt/liquidate
10. diff current vs target → orders (deterministic)
11. **persist `LlmDecision` + planned orders before submitting**
12. submit, persist execution/fills/equity

Step 11 precedes step 12 (write-ahead): a crash mid-submit leaves a reconcilable
record rather than orders at the venue nothing knows about.

# The multi-agent pipeline
```
market/technicals agent ─┐
news/sentiment agent   ─┼─► coordinator/trader agent ─► target weights + reasoning
risk agent (optional)  ─┘
```
Each specialist emits structured analysis; the coordinator emits the final
schema-validated decision. Deepseek v4 pro is the default backbone, swappable
via config (the `llm/` contract hides the provider).

# Safety & security
* No HTTP route runs a live cycle — `dry_run` only; the engine is reachable
  solely from cron
* Cron disabled by default (`TRDD_BE_CRON_ENABLED`)
* LLM API key and exchange keys in `.env`; trade-only, no-withdraw,
  IP-allowlisted
* Deterministic validation is the final gate before any order; LLM output is
  never trusted raw
* Risk overlay is idempotent; hold-on-fail; write-ahead persistence
* Universe expansion is always gated by code

# Conventions
* `Decimal` for money, `float` for statistics
* Time as `int` epoch milliseconds, UTC
* `Symbol` carries its venue
* `DomainError(message, ErrorType.X)`
* Partial failure is returned as data, not raised
* Soft-delete on config entities
* `Settings` (pydantic-settings), env prefix `TRDD_BE_`

# Testing
* Risk overlay + rebalancer + fill sim: pure, no event loop, conformance-suite
  invariants
* Schema validation: fuzz malformed LLM outputs, assert hold-on-fail
* Replay backtest: recorded decisions replay through fill sim
* Integration: testcontainers Postgres for the new repositories

# Open questions
* Exact cadence default (daily vs weekly) — configurable until settled
* Token/latency budget per decision — sized once the provider is fixed
* News source allowlist for the scraper
