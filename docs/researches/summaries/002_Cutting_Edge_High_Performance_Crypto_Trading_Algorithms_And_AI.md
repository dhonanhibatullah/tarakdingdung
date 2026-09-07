# Cutting-Edge / High-Performance Crypto Trading Algorithms and AI (2024–2026)

- **Question:** What are the most cutting-edge and high-performance crypto
  trading algorithms / AI approaches currently documented on the web, what do
  they actually achieve, and what should tarakdingdung take from them for a v1
  automated crypto engine?
- **Last updated:** 2026-09-07
- **Status:** draft
- **Topic tags:** crypto, deep-reinforcement-learning, llm-agents, multi-agent,
  transformers, statistical-arbitrage, market-making, funding-arbitrage,
  backtest-overfitting, risk-management

---

## TL;DR

- The **research frontier** is in two families: (1) **deep reinforcement
  learning (DRL)** for position/portfolio allocation — PPO-based, ensembled,
  with explicit anti-overfitting model selection (refs 010, 011); (2)
  **LLM multi-agent systems** that fuse price, news/sentiment and technical
  "skills" through hierarchical / debate structures (refs 009, 012, 013).
- The **best published crypto results** are eye-catching but fragile: an
  LLM 3-agent system reports **+133.5% / Sharpe 1.50** over full-year-2025
  weekly rebalancing on the top-15 L1s, beating deep-learning time-series
  baselines (+83%) and passive holding (≈ -4%) (ref 009); a PPO ensemble reports
  **+694% / Sharpe 1.07** over 4 years but with a **69.5% drawdown** and **no
  transaction costs** (ref 011).
- **Reality checks are strong and consistent.** The same LLM agent literature
  shows single-agent LLMs *lose money* (ref 009), and a reflective on-chain LLM
  agent (CryptoTrade) **fails to beat buy-and-hold or a simple moving-average
  rule** and is net-negative outside bull markets (ref 013). A DL reproduction
  study finds a plain bidirectional LSTM beats a Transformer and never links
  forecast accuracy to profit (ref 017). Practitioner guidance says any
  non-latency strategy backtesting above **Sharpe 3 is a red flag** (ref 015).
- **What professionals actually run at scale** is not AI price prediction — it is
  **delta-neutral funding-rate arbitrage** and **market-neutral long-short**,
  plus **cash-and-carry basis** and **market making**. An $4B-AUM cohort's
  funding-arb returns are smooth enough that Sharpe is "uninformatively high";
  basis trades ~8–15% annualised now; market making needs $5–50M+ and
  low-latency infra and is structurally hostile to small players (refs 014, 016).
- **The single most important technique in the cutting-edge DRL work is not the
  algorithm — it is overfitting control**: formulating backtest overfitting as a
  hypothesis test, estimating the Probability of Backtest Overfitting (PBO) via
  combinatorial cross-validation, and **rejecting** any agent with p ≥ 10%
  (ref 010). This is the transferable idea for tarakdingdung regardless of
  strategy family.
- **Recommended posture for v1:** build the engine around a **market-neutral,
  cost-aware, risk-capped** strategy (funding-rate / basis capture is the
  highest Sharpe-per-unit-effort and matches the Tokocrypto/Indodax venue set),
  with a **classical signal baseline** (moving-average / cross-sectional
  momentum) as the control. Treat DRL and LLM-agent methods as **research
  tracks** layered on top of a working backtester with realistic fees and
  slippage and a PBO gate — not as the v1 execution brain.

## Detail

### 1. The two frontier families

**Deep reinforcement learning (DRL).** The active line of work (FinRL /
FinRL-Crypto ecosystem) uses actor-critic algorithms — **PPO, A2C, TD3, SAC,
DDPG** — to learn a policy that maps market state → target positions, trained on
minute-to-hourly bars. Two 2023 papers define the current practice:

- *Ensemble PPO* (ref 011): instead of one final policy, keep **K checkpoints**
  from a single PPO run, selected on validation performance across multiple
  periods, and combine them with an equal-weighted "mixture distribution
  policy." On 5 coins (BTC, ETH, BCH, XRP, LTC), hourly 2018–2022, 4-year
  out-of-sample: **annualised return 0.93, cumulative 7.94× (vs 2.61× buy-and-
  hold), Sharpe 1.07 (vs 0.81), max drawdown 69.5%.** Authors concede it "excels
  at exploiting the upward trend" but offers "limited protection during market
  crashes," models **no transaction costs**, and is long-only.
- *Backtest-overfitting control* (ref 010, AAAI-23): the headline contribution is
  methodological. Detect overfitting as a hypothesis test — H0: PBO p < α (not
  overfit); reject the agent if p ≥ α = 10%. p is estimated by combinatorial
  cross-validation (N = 5 groups, k = 2 validation, J = 10 splits) over H = 50
  hyperparameter trials, ranking in-sample vs out-of-sample and integrating the
  logit distribution below zero. On 10 coins at 5-min bars into the May–Jun 2022
  crash: the **accepted PPO agent lost 34.96%** vs -47.78% equal-weight,
  -50.78% S&P DBM, -55.5% for the K-fold-selected PPO, and -59% for TD3/SAC
  (both of which the test *rejected* as overfit, p = 9.6% accepted for TD3,
  21.3% rejected for SAC). Claimed ~46% reduction in overfitting vs conventional
  train/val selection. A CVIX > 90.1 overlay forces de-risking.

Takeaway: DRL can beat passive holding on multi-year windows, but (a) the
reported edge is concentrated in bull trends, (b) drawdowns are brutal, (c)
results collapse toward benchmarks once you evaluate honestly, and (d) the
literature's own remedy is aggressive model rejection, not a better network.

**LLM multi-agent systems.** The 2024–2026 frontier. Architecture pattern:
specialised agents (a market/price agent, a news/sentiment agent, sometimes a
technical-"skill" agent) whose outputs are combined by a **coordination
structure** — hierarchical (a supervisor reconciles), collaborative (iterative
refinement), or **debate** (bull vs bear adversarial argument) — feeding a
trading agent, often with a **risk-management agent** and a **reflection** step
that reviews past decisions.

- *3-agent crypto portfolio system* (ref 009): Crypto Agent (30-day stats) +
  News Agent (weekly Cointelegraph) + Trading Agent, with ZS / CoT / RAG /
  Skill capability variants and a 4-week rolling memory. Full-year-2025 weekly
  rebalancing, top-15 L1s, 0.1%/side fees, slippage ignored. **Best config
  (Hierarchical + Skill, GPT-4o): +133.5% cumulative, Sharpe 1.50, MaxDD
  -39%**, vs +83% for the best DL baseline (TimesNet), vs ≈ -4% for BTC/mcap
  holding in a roughly flat 2025. Debate + Skill hit +291% in the 27 bull weeks
  (Sharpe 3.5) but **-47% in the 15 bear weeks**. **Single-agent LLM variants
  all lost money (-9% to -29%)** — the multi-agent structure is doing the work.
  Ablations: removing the price agent costs 43 points of return; removing the
  news agent mainly raises volatility (it acts as a risk damper); removing
  memory costs 11 points. Claude Sonnet 4.5 was the strongest backbone on
  average (+33% mean over all configs) vs GPT-4o (+17.5%) vs GPT-5 (+6.9%).
- *TradingAgents* (ref 012): the most-cited design — analyst team + bull/bear
  researcher debate + trader + risk team. Equities only (AAPL/GOOGL/AMZN, 3
  months of 2024), reporting **Sharpe 5–8**. That number over a single short,
  favorable window is a **methodology red flag**, not evidence of edge; the
  value here is the architecture, which has been ported to crypto.
- *CryptoTrade* (ref 013): reflective 4-agent system on **on-chain + off-chain**
  data, BTC/ETH/SOL across bull/sideways/bear windows. Result: it **beats naive
  deep-learning forecasters but not simple technical rules or buy-and-hold**
  (BTC bull: 26–28% vs 39.7% buy-and-hold; SOL bull: 100–115% vs 177%
  buy-and-hold / 170% SLMA) and is net-negative in sideways and bear markets.
  Honest, and sobering.

Takeaway: multi-agent + debate + explicit "skills" + memory + reflection is the
real frontier and clearly beats single-shot LLM prompting, but (a) the strong
numbers come from a single 2025 window with no cross-validation, no slippage,
and no seed-variance quantification (ref 009's own stated limitations), (b)
skill/momentum signals win in bull runs and get punished in drawdowns, and (c)
an independent design (ref 013) can't beat a moving average.

### 2. Transformers / time-series deep learning

Present but not dominant. In ref 009's own baselines, **TimesNet** and
**Informer** (+83% / +75%) beat **PatchTST**, **LSTM** and **Autoformer**
(+28% / +14% / +9%). A 2024 reproduction review (ref 017) across
BTC/ETH/DOGE/LTC finds a **bidirectional LSTM beats the Transformer**
(BTC test RMSE 0.0327 vs 0.0494), univariate beats multivariate, and — crucially
— reports **RMSE only, with no demonstration that better forecasts make money**.
The prediction-accuracy-to-P&L gap is the recurring theme.

### 3. What actually generates high, stable Sharpe (practitioner reality)

The professional crypto quant world (refs 014, 016) is not running AI price
prediction as its core. The load-bearing strategies:

| Strategy | What it is | Reported economics | Feasibility for a small operator |
|---|---|---|---|
| **Funding-rate arbitrage** (delta-neutral) | Long spot, short perp of equal notional; harvest funding | Returns "so stable Sharpe is uninformatively high" across $4B AUM cohort (ref 016); dollar-neutral cohort ~31% in 2025, top venue ~67% / Sharpe 2.39 (ref 014, vendor-reported, unverified) | **Best fit.** Works from ~$2–5k; main risks are exchange counterparty and funding sign-flips |
| **Cash-and-carry basis** | Long spot, short dated future; capture basis to expiry | 8–15% annualised now (was 30–50% in 2020–21); historical Sharpe ~4.84 claimed (ref 014, unverified) | Good fit; needs both legs and fee coverage (~$5k+) |
| **Statistical arbitrage** | Cross-sectional momentum/reversion; pairs | Realistic Sharpe 1.0–2.0; BTC-ETH pair ~2.23 claimed (refs 014, 015); "naive cointegration" fails due to regime shifts | Feasible; needs clean multi-asset data + careful cost modelling |
| **Market making** | Quote both sides, earn spread | Realistic Sharpe 3–8+ (ref 015) but BTC-USDT spreads are 1–2 bps now | **Poor fit.** Needs $5–50M+, colocation, rebate tiers; small players structurally disadvantaged (ref 014) |
| **Trend / momentum** | Directional, multi-timeframe | Realistic Sharpe 0.5–1.0 (ref 015); "whipsaw risk is severe" in crypto (ref 014) | Feasible as a baseline; must have strict risk management |
| **HFT / MEV** | Latency / mempool games | Sharpe 5–20+ (ref 015); MEV needs $10M+ and a team (ref 014) | Out of scope |

Cross-cutting practitioner rules (ref 014): never keep >30% of capital on one
exchange; exchange counterparty risk dominates ("if Binance fails, your hedge
doesn't help"); on-chain signals only work at 1–7 day horizons.

### 4. Synthesis for tarakdingdung

1. **v1 execution brain = a classical, market-neutral, cost-aware strategy.**
   Funding-rate / basis capture has the best Sharpe-per-unit-effort, is the
   strategy professionals actually scale (ref 016), needs little capital, and
   maps directly onto the Tokocrypto (Binance-style perps/spot) + Indodax venue
   set from summary 001. Pair it with a **moving-average / cross-sectional
   momentum baseline** as an experimental control.
2. **Build the backtester first, with realistic frictions.** Every cutting-edge
   result above that looks spectacular either omits transaction costs (ref 011),
   omits slippage (ref 009), or uses a single short window (refs 009, 012). A
   v1 backtester must model **maker/taker fees, funding, slippage, and
   borrow/interest**, and support walk-forward evaluation.
3. **Adopt the overfitting gate (ref 010) as a first-class component**, whatever
   the strategy family: combinatorial cross-validation + a PBO hypothesis test,
   and refuse to deploy any parameter set / model with p ≥ ~10%. This is the
   most transferable idea in the entire frontier literature.
4. **Hard risk overlay, always on.** A volatility-index / regime kill-switch
   (ref 010's CVIX cutoff), per-position and per-venue caps (ref 014's 30%
   rule), and profit-sweeping. The frontier methods' worst failures are
   40–70% drawdowns in bear regimes (refs 009, 011).
5. **Treat DRL and LLM-agent methods as research tracks, not v1.** When pursued:
   prefer **PPO ensembles with checkpoint selection** (ref 011) for allocation;
   for LLM agents, the evidence says **multi-agent + debate + explicit technical
   "skills" + memory + a reflection step + a dedicated risk agent** is the
   configuration that works (ref 009), single-agent prompting is not, and the
   whole approach must still clear the same cost-aware, cross-validated bar —
   because an independent build (ref 013) couldn't beat a moving average.
6. **Don't chase architectures.** Transformer > LSTM is not established for
   crypto (ref 017), and forecast accuracy has not been shown to equal profit.

## Open questions / gaps

- **Funding-arb mechanics on Tokocrypto/Indodax specifically:** perp
  availability, funding intervals, borrow costs, and whether delta-neutral is
  cleanly executable on these venues (Indodax has limited perps). Needs a
  venue-capability reference feeding back into summary 001.
- **Realistic slippage model for IDR pairs and mid-cap alts** — the frontier
  papers all assume top-15 liquidity; tarakdingdung may trade thinner books.
- **PBO / combinatorial-CV implementation cost** for an LLM-agent strategy where
  each "trial" is an expensive API rollout (ref 009 explicitly punted on
  seed-variance for this reason). Is there a cheaper robustness proxy?
- **Live-vs-backtest decay:** none of refs 009–013 report forward/live results;
  need a source (or our own paper-trading log) quantifying the drop.
- **ccxt / library support** for funding-rate and basis data collection on the
  two target exchanges (open question also flagged in summary 001).
- **Transaction-cost-inclusive DRL:** is there newer (2025–2026) work that adds
  realistic fees/slippage to the FinRL-Crypto setup and still shows an edge?
- **Regulatory:** does OJK restrict automated/algorithmic retail trading on PAKD
  venues (carried over from summary 001)?

---

## References used

- `references/009_LLM_Multi_Agent_System_Crypto_Portfolio_Management.md`
- `references/010_DRL_Crypto_Trading_Backtest_Overfitting_FinRL_Crypto.md`
- `references/011_Ensemble_Deep_Reinforcement_Learning_Automated_Crypto_Trading.md`
- `references/012_TradingAgents_Multi_Agent_LLM_Financial_Trading_Framework.md`
- `references/013_CryptoTrade_Reflective_LLM_Agent_Zero_Shot_Crypto_Trading.md`
- `references/014_Quantt_Crypto_Quant_Strategies_2026_What_Actually_Works.md`
- `references/015_Quantt_Quant_Trading_Strategies_Guide_Realistic_Sharpe_By_Strategy.md`
- `references/016_1Token_Crypto_Quant_Strategy_Index_VIII_Nov_2025.md`
- `references/017_Review_Deep_Learning_Models_Crypto_Price_Prediction.md`
