# Automated Trading Engine — Implementation Plan (v1)

- **Question:** Concretely, how does tarakdingdung build its first automated
  crypto trading engine — what strategy, what pipeline, in what order, with what
  safeguards, and how does it map onto the codebase?
- **Last updated:** 2026-09-07
- **Status:** draft
- **Topic tags:** implementation-plan, architecture, strategy, backtesting,
  overfitting, risk-management, tokocrypto, indodax, spot, roadmap

---

## TL;DR

- **Start boring, prove the pipeline, then get clever.** The cutting-edge
  methods (deep RL, LLM multi-agent) mostly fail to beat buy-and-hold or a
  moving-average rule once fees are counted and testing is honest (summary 002).
  v1 is a simple, cost-aware, risk-capped spot strategy; the pipeline around it
  matters more than the algorithm.
- **Funding-rate arbitrage is off the table for v1.** It needs perpetual
  futures, and **neither Tokocrypto nor Indodax exposes a futures/perp API** —
  both are spot-only (ref 018). So v1 is a **spot** strategy: cross-exchange
  arbitrage, cross-sectional momentum / trend, or spot mean-reversion.
- **Build order:** (0) API clients — done; (1) market-data collector + storage;
  (2) realistic backtester (fees, slippage, funding, borrow); (3) one strategy
  as a pure `data -> target positions` function, plus MA-crossover and
  buy-and-hold as controls; (4) walk-forward validation + a Probability-of-
  Backtest-Overfitting (PBO) gate — reject if p ≥ ~10% (ref 010); (5) paper
  trading against live data; (6) tiny real capital with all safeguards armed;
  (7) iterate — only now do DRL / LLM methods enter, held to the same bar.
- **Always-on risk overlay:** per-trade + per-coin + per-venue (≤ 30%) caps,
  volatility kill-switch, scheduled profit sweeps, trade-only/no-withdraw
  API keys, Indodax dead-man switch (refs 001, 005, 014).
- **Realistic expectations:** Sharpe ~0.5–1.5 for a spot directional/arb
  strategy; a backtest Sharpe > 3 is a bug, not a win (ref 015). Max drawdown
  budget fixed in advance (e.g. 15–20%).

## Detail

### 1. What the research rules in and out

| Approach | Verdict for v1 | Why |
|---|---|---|
| Deep RL (PPO ensembles) | research track, not v1 | beats buy-and-hold only in multi-year up-trends, 40–70% drawdowns, costs often unmodelled (refs 010, 011 via summary 002) |
| LLM multi-agent | research track, not v1 | strong single-window results, no cross-validation; single-agent variants lose money; an independent build (CryptoTrade) couldn't beat a moving average (summary 002) |
| Transformer price prediction | not a priority | a plain LSTM beat it, and better forecasts didn't yield more profit (ref 017) |
| Funding-rate arbitrage | **impossible on our venues** | needs a perp API; Tokocrypto + Indodax are spot-only (ref 018) |
| Cash-and-carry basis | **impossible on our venues** | same reason (ref 018) |
| Market making | not for our size | needs $5–50M+, colocation, rebate tiers (ref 014) |
| **Spot cross-exchange arbitrage** | **v1 candidate** | market-neutral-ish, needs only spot books on both venues, which we have |
| **Spot cross-sectional momentum / trend** | **v1 candidate (fallback)** | simple, well-understood; realistic Sharpe 0.5–1.0 (ref 015); needs strict risk control (ref 014) |
| **Spot mean-reversion / pairs** | v1 candidate | realistic Sharpe ~1–2 (ref 015); watch regime shifts (ref 014) |

The transferable technique from the whole literature is not an algorithm — it is
**overfitting control**: combinatorial cross-validation + a PBO hypothesis test,
rejecting any parameter set with overfitting probability ≥ ~10% (ref 010).

### 2. The strategy interface

Every strategy in the codebase is a **pure function**:

```
decide(snapshot) -> {asset: target_weight}     # weights sum to <= 1; cash is the remainder
```

- No API calls, no order logic, no clock inside it → trivially unit-testable and
  backtestable with the exact same code path as live.
- `snapshot` = whatever the collector has stored up to time *t* (candles, order
  books, recent trades, cross-venue prices) — **never** future data.
- The engine diffs current holdings vs. target weights and asks the executor to
  close the gap.

### 3. Phased build

**Phase 0 — Foundations (done).**
Exchange API access, credentials in config (trade-only, no withdraw), and typed
REST clients for Indodax v1/v2 + Tokocrypto v1 covering the **full** documented
surface (market data, orders, account, wallet, listen-token). See summary 003.

**Phase 1 — Market-data collector + storage.**
A long-running task that polls (and later WebSocket-subscribes to) candles,
order-book snapshots, recent trades, and per-venue last prices for a pinned
symbol universe, and writes them to storage. Rationale: no vendor sells clean
history for these venues, and **nothing downstream can be built or tested
without accumulated data**. Decide: same Postgres vs. a time-series store.

**Phase 2 — Backtester.**
Replays stored data through `decide()` and simulates fills. **Must** model:
maker/taker fees, slippage (sized to each venue's real book depth — thin IDR
books are a known risk, summary 002 §"Open questions"), and borrow/interest.
**Must** support walk-forward: tune on window A, evaluate untouched on window B.
Outputs: equity curve, Sharpe, max drawdown, turnover, gross-vs-net (cost drag).

**Phase 3 — First strategy + controls.**
Implement one strategy (§1 candidates) behind the `decide()` interface, plus two
always-present controls: a moving-average crossover and buy-and-hold. If the
strategy can't beat both **after costs**, it isn't real.

**Phase 4 — Validation gate.**
Walk-forward across multiple regimes (calm, crash, sideways). Run the **PBO
test**; discard if p ≥ ~10% (ref 010). Sanity-check the numbers are *plausible*,
not spectacular: Sharpe ~0.5–2, drawdown within the pre-set budget, costs not
eating most of the gross return. A Sharpe > 3 for a non-latency strategy is a
methodology error (ref 015).

**Phase 5 — Paper trading.**
Run `decide()` on live data through the real clients, but **simulate fills**
instead of sending orders. Prototype first against the Binance Spot **testnet**
(Tokocrypto is a Binance clone, so code ports over — summary 001). Track
live-vs-backtest decay; a large gap means the backtest lied — stop.

**Phase 6 — Tiny real capital.**
Go live with a small, losable amount. Keys trade-only + IP-locked to
`118.99.94.221`. All Phase-8 safeguards armed. Watch daily for weeks.

**Phase 7 — Iterate.**
Add a second strategy; run several as an ensemble. **Now** DRL / LLM-agent
methods become experiments — each must clear the same backtest + PBO + paper bar
(summary 002). Prefer PPO ensembles with checkpoint selection for allocation;
for LLM agents, the evidence says multi-agent + debate + explicit indicator
"skills" + memory + a reflection step + a risk agent is the configuration that
works, and single-shot prompting is not (ref via summary 002).

### 4. Always-on risk overlay (from Phase 5 onward)

- Per-trade notional cap; per-coin exposure cap.
- **Per-venue cap ≤ 30%** of total capital — if an exchange fails, the rest of
  the book survives (ref 014).
- **Volatility kill-switch:** above a fear-index threshold, stop opening and
  de-risk (ref 010's crash overlay).
- **Scheduled profit sweep** off-exchange (Indodax had a ~US$22–25M breach in
  2024 — refs 001, 005).
- **No withdraw permission** on any API key, ever.
- **Indodax dead-man switch:** auto-cancel resting orders if the bot loses
  connectivity (ref 001).
- Global daily-loss limit → flatten and halt for the day.

### 5. Codebase mapping

| Concern | Location | Status |
|---|---|---|
| Exchange REST clients | `domain/contracts/api/**`, `infrastructure/api/**` | done (summary 003) |
| Exchange WebSocket clients | `domain/contracts/api/**` (`*_ws.py`), `infrastructure/api/**` | contracts + baseline infra |
| Market-data collector | `infrastructure/…/collector` + a `composition` task | Phase 1 |
| Market-data storage/repo | `domain/contracts/repository/marketdata.py` + infra | Phase 1 |
| `Strategy` contract | `domain/contracts/strategy/…` (`decide(snapshot) -> weights`) | Phase 3 |
| Concrete strategies | `infrastructure/strategy/…` or `domain/usecases/…` | Phase 3 |
| Backtester | own module (`backtest/…`) reusing `Strategy` + stored data | Phase 2 |
| Validation / PBO | `backtest/validation.py` | Phase 4 |
| Executor (weights → orders) | `domain/contracts/execution/…` + infra over the API clients | Phase 3 |
| Risk manager | `domain/contracts/risk/…` + infra; sits between strategy and executor | Phase 5 |
| Engine loop / scheduler | `composition/…` (collect → decide → risk-check → execute) | Phase 3+ |

Contracts stay dependency-light ABCs (like `Token`, `LeveledLogger`); infra
implementations get the `Http*` / tech-prefixed naming already used.

### 6. Immediate next actions

1. Pin the v1 symbol universe (a handful of liquid IDR + USDT pairs common to
   both venues).
2. Decide storage (Postgres table vs. time-series DB) and stand up the Phase-1
   collector.
3. Choose the v1 strategy: **spot cross-exchange arbitrage** (most
   market-neutral, needs a latency/fee study first) vs. **spot cross-sectional
   momentum** (simplest, robust, lower Sharpe). Recommendation: prototype the
   momentum baseline first because it doubles as the Phase-3 control, then
   evaluate cross-exchange arb once the backtester and cost model exist.
4. Build the backtester with a real fee + slippage model before writing more
   strategy code.

## Open questions / gaps

- **Storage engine** for tick/candle/order-book history — not decided.
- **Slippage model:** need measured book depth for the target IDR/USDT pairs on
  both venues before the backtester's cost model is trustworthy (carried from
  summary 003).
- **Cross-exchange arb viability:** real round-trip latency Indodax⇄Tokocrypto
  from a SEA VPS, withdrawal/transfer times between venues (you can't
  instantly move coins to rebalance), and whether fee tiers leave an edge.
- **Trade cadence:** daily vs. hourly. Slower = less cost drag and fewer failure
  modes; the best LLM result in the literature rebalanced weekly (summary 002).
- **Offshore perp option:** if delta-neutral strategies become a requirement,
  scope Binance USDⓈ-M (KYC/funding/tax cost) rather than waiting on a local
  perp API (ref 018).
- **PBO cost** when each backtest "trial" is expensive — cheaper robustness
  proxy? (carried from summary 002).
- **Regulatory:** does OJK restrict automated/algorithmic retail trading on PAKD
  venues? (carried from summary 001).

---

## References used

- `references/001_Indodax_Official_API_Documentation.md`
- `references/002_Tokocrypto_API_Documentation.md`
- `references/005_Indodax_2024_Hot_Wallet_Hack.md`
- `references/010_DRL_Crypto_Trading_Backtest_Overfitting_FinRL_Crypto.md`
- `references/011_Ensemble_Deep_Reinforcement_Learning_Automated_Crypto_Trading.md`
- `references/014_Quantt_Crypto_Quant_Strategies_2026_What_Actually_Works.md`
- `references/015_Quantt_Quant_Trading_Strategies_Guide_Realistic_Sharpe_By_Strategy.md`
- `references/016_1Token_Crypto_Quant_Strategy_Index_VIII_Nov_2025.md`
- `references/017_Review_Deep_Learning_Models_Crypto_Price_Prediction.md`
- `references/018_Indodax_Tokocrypto_No_Futures_Perp_API.md`
