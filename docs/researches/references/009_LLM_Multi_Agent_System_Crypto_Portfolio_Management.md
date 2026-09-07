# LLM-Powered Multi-Agent System for Automated Crypto Portfolio Management

- **Source URL:** https://arxiv.org/abs/2501.00826 (HTML: https://arxiv.org/html/2501.00826v3)
- **Author / Publisher:** Yichen Luo, Yebo Feng, Jiahua Xu, Paolo Tasca, Yang Liu (UCL / NTU et al.); arXiv preprint
- **Published:** 2025-01-01 (v3 revised 2026, backtests the full 2025 calendar year)
- **Retrieved:** 2026-09-07
- **Retrieved by:** Claude Sonnet 5, conducting-research session
- **Type:** paper (preprint, with open-source code)
- **Topic tags:** llm-agents, multi-agent, portfolio-management, crypto, backtesting, reinforcement-of-prompts, sentiment

---

## Raw content

### System architecture

Three modality-specialised agents:

1. **Crypto Agent** — analyses 30-day market statistics (price, volume, market cap)
   from CoinGecko per asset. Outputs a directional signal in [-1, 1] with a
   confidence score [0, 1] and a rationale.
2. **News Agent** — processes weekly Cointelegraph articles → market-wide
   sentiment [-1, 1] plus per-coin signals for mentioned assets.
3. **Trading Agent** — integrates Crypto + News outputs with current portfolio
   state (cash, holdings, unrealised P&L) → final action per asset in [-1, 1]
   (positive = buy allocation fraction, negative = sell fraction).

**Communication architectures (inter-agent coordination):**

- **Hierarchical** — Crypto and News agents run independently; Trading Agent is
  supervisor, reconciles conflicts.
- **Collaborative** — iterative refinement, R = 1 round; agents revise signals
  after seeing each other's output, then Trading Agent decides.
- **Debate** — structured adversarial argumentation, R = 2 rounds; each agent
  challenges the other citing evidence; Trading Agent weighs the full dialectic.

**Capability configurations (applied per agent):**

- **Zero-Shot (ZS)** — direct input→output mapping from pretrained knowledge.
- **Chain-of-Thought (CoT)** — step-by-step reasoning in `<reasoning>` tags
  before structured JSON output.
- **Retrieval-Augmented Generation (RAG)** — Crypto Agent queries a vector store
  of historical market analogues via an 11-dim scale-invariant feature vector
  (6 price-return periods, 3 volume periods, 2 market-cap periods); retrieves
  top-K = 3 past weeks with realised next-week returns as calibration.
- **Skill-Augmented** — Crypto Agent is fed 4 pre-computed technical indicators:
  SMA7, SLMA (golden cross), MACD histogram, Bollinger oversold. Composite
  bullish count ∈ {0,1,2,3,4} maps to signal strength.

**Memory:** all agents keep a rolling K = 4 week memory, serialised at week end,
restored next week, prepended in reverse-chronological order. Only final-round
output commits to memory during collaborative/debate rounds.

### Dataset and universe

- **Universe:** top 15 L1-blockchain native cryptos by market cap as of Jan 2025,
  held constant: BTC, ETH, BNB, XRP, SOL, TRX, ADA, BCH, HYPE, XMR, ZEC, LTC,
  SUI, AVAX, HBAR.
- **Data:** daily OHLCV from CoinGecko; news from Cointelegraph; risk-free rate
  from Fama-French 1-month US T-bills.
- **Backtest period:** calendar year 2025, ISO weeks 1–52 (T = 52). Chosen so all
  model training cutoffs precede the window (GPT-4o Oct 2023, GPT-5 Sep 2024,
  Claude Sonnet 4.5 Jan 2025).
- **Regimes:** Bull = weeks where the mcap-weighted basket is ≥ +20% off its
  running trough (N = 27); Bear = ≤ -20% off running peak (N = 15).

### Backtest methodology

- Initial capital $100,000; weekly rebalancing (ISO week close).
- Transaction cost **0.1% per trade side** (0.2% round-trip); slippage / price
  impact **omitted** (justified by top-15 liquidity).
- Execution: all sells first, then cash redistributed across buys simultaneously
  with proportional scaling if buy fractions sum > 1.0.
- Objective: maximise terminal value V_T = V_0 · ∏(1 + r_t).
- All agents run at **temperature 0.0** (deterministic).

### Quantitative results — full period, GPT-4o backbone

| Strategy | Cum% | Avg%/wk | Vol% (ann.) | Sharpe | MaxDD% | Win% |
|---|---|---|---|---|---|---|
| Hierarchical (Skill) | +133.52 | +2.12 | 73.40 | +1.502 | -39.33 | 59.6 |
| Debate (Skill) | +110.00 | +2.00 | 79.26 | +1.310 | -44.60 | 59.6 |
| Collaborative (Skill) | +57.12 | +1.28 | 67.41 | +0.990 | -38.35 | 57.7 |
| TimesNet (DL baseline) | +83.40 | +1.55 | 66.72 | +1.212 | -32.09 | 55.8 |
| Informer (DL baseline) | +74.89 | +1.40 | 58.77 | +1.236 | -26.37 | 53.8 |
| PatchTST (DL baseline) | +28.35 | +0.81 | 59.43 | +0.710 | -35.68 | 50.0 |
| LSTM (DL baseline) | +13.82 | +0.67 | 66.37 | +0.522 | -44.01 | 48.1 |
| Autoformer (DL baseline) | +8.72 | +0.48 | 58.31 | +0.428 | -35.22 | 46.2 |
| Single-agent (CoT) | -8.81 | +0.01 | 44.54 | +0.013 | -34.48 | 46.2 |
| Single-agent (ZS) | -26.00 | -0.31 | 52.68 | -0.309 | -39.29 | 50.0 |
| Single-agent (Skill) | -28.34 | -0.33 | 56.81 | -0.302 | -42.55 | 48.1 |
| Single-agent (RAG) | -28.90 | -0.39 | 52.69 | -0.386 | -40.62 | 44.2 |
| BTC hold | -3.36 | +0.06 | 37.09 | +0.091 | -29.73 | 46.2 |
| Mcap-weighted hold | -4.54 | +0.08 | 41.65 | +0.095 | -31.31 | 50.0 |

Full 4×3 architecture×capability grid (GPT-4o), cumulative return / Sharpe:

- Hierarchical: ZS +52.19% / +1.022 · CoT -12.99% / -0.122 · RAG -11.25% / -0.056 · Skill +133.52% / +1.502
- Collaborative: ZS +31.91% / +0.785 · CoT -21.94% / -0.220 · RAG -8.03% / -0.006 · Skill +57.12% / +0.990
- Debate: ZS +1.94% / +0.320 · CoT +52.76% / +1.026 · RAG -12.71% / -0.085 · Skill +110.00% / +1.310

### Bull market (27 weeks)

| Strategy | Cum% | Sharpe | MaxDD% |
|---|---|---|---|
| Debate (Skill) | +290.96 | +3.475 | -14.51 |
| Hierarchical (Skill) | +277.08 | +3.541 | -12.00 |
| Collaborative (Skill) | +187.14 | +3.112 | -11.75 |
| TimesNet | +164.04 | +2.799 | -15.53 |
| Mcap hold | +21.13 | +1.100 | -16.67 |

### Bear market (15 weeks)

| Strategy | Cum% | Sharpe | MaxDD% |
|---|---|---|---|
| Hierarchical (CoT) | -15.51 | -1.709 | -4.42 |
| BTC hold | -21.24 | -1.719 | -8.83 |
| Collaborative (Skill) | -43.87 | -3.080 | -38.35 |
| Debate (Skill) | -47.30 | -2.745 | -44.60 |

### Cross-model comparison (mean over all 16 arch×capability combos)

- Claude Sonnet 4.5: +33.0% cumulative, 54.1% vol
- GPT-4o: +17.5% cumulative, 54.5% vol
- GPT-5: +6.9% cumulative, 45.8% vol

Best config per model: GPT-4o Hier.(Skill) +133.5%; Claude Debate(Skill) +121.3%;
GPT-5 Hier.(CoT) +39.7% (GPT-5 prefers CoT, underperforms with Skill).

Multi-agent vs single-agent (mean over backbones): GPT-4o +31.0% vs -23.0%;
GPT-5 +12.2% vs -9.0%; Claude +43.9% vs +0.1%.

### Ablation (Hierarchical ZS reference, GPT-4o)

| Ablation | Cum% | Δ vs full |
|---|---|---|
| Full (Hier. ZS) | +52.19 | — |
| − News Agent | +51.31 | -0.88 |
| − Crypto Agent | +9.62 | -42.57 |
| − Memory | +40.72 | -11.47 |

Crypto Agent removal = largest hit; News Agent acts as a volatility/risk dampener;
memory provides cross-week continuity.

### Capability trade-offs stated

- **Skill augmentation** maximises bull returns (+290.96% Debate) but amplifies
  bear losses (-47.30% same config): momentum signals lack downside protection.
- **CoT** minimises bear drawdown (Hier. CoT MaxDD -4.42%) and cuts volatility.
- **RAG** systematically lowers volatility but caps upside; no RAG variant is
  top-3 for return in any period.
- **Hierarchical** = best risk-adjusted overall (Sharpe +1.502).
- **Debate** = highest raw bull return but amplified reversals.

### Limitations / caveats stated by authors

1. Stochasticity not quantified — temperature 0.0 used; full multi-seed sweep
   "cost-prohibitive under commercial API pricing," left to future work.
2. No slippage / price impact modelled (justified only for top-15 assets at
   $100k; may not hold at larger capital).
3. Universe fixed at Jan 2025 — misses dynamic rebalancing opportunities.
4. Single contiguous 52-week evaluation window; no cross-validation or multiple
   hold-outs to test robustness.
5. Training-data leakage minimised (dates after cutoffs) but not proven absent.
6. Crypto-specific domain knowledge underrepresented in LLM pretraining corpora —
   a caveat for all LLM approaches, and the reason single-agent variants lose money.

### Real-world feasibility notes

- Transaction cost model 0.1%/side; execution venue availability, congestion,
  time-of-execution not modelled.
- Full implementation open-sourced "to support reproducibility and practical
  adoption"; every decision traceable to explicit agent reasoning chains.
- Commercial API per-token cost not disclosed; weekly (not intraday) rebalancing
  keeps friction low.

---

## Capture notes

Extracted via WebFetch against the arXiv HTML (v3). Tables transcribed from the
model's structured extraction; a few rows of the 12-cell grid and the bull/bear
tables were abridged to the highest- and lowest-ranked entries plus benchmarks.
Numbers are as reported by the paper's HTML; not independently verified.
