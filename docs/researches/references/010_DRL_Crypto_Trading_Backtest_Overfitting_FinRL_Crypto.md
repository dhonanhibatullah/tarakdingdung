# Deep Reinforcement Learning for Cryptocurrency Trading: Practical Approach to Address Backtest Overfitting (FinRL-Crypto)

- **Source URL:** https://arxiv.org/abs/2209.05559 (HTML: https://ar5iv.labs.arxiv.org/abs/2209.05559)
- **Author / Publisher:** Berend Jelmer Dirk Gort, Xiao-Yang Liu, Xinghang Sun, Jiechao Gao, Shuaiyu Chen, Christina Dan Wang (Columbia University et al.)
- **Published:** 2022-09-12; last revised 2023-01-31. Presented at AAAI-23 Bridge on AI for Financial Services. Code: github.com/berendgort/FinRL_Crypto
- **Retrieved:** 2026-09-07
- **Retrieved by:** Claude Sonnet 5, conducting-research session
- **Type:** paper
- **Topic tags:** deep-reinforcement-learning, backtest-overfitting, PBO, cross-validation, crypto, risk-management, FinRL

---

## Raw content

### Abstract (verbatim)

"Designing profitable and reliable trading strategies is challenging in the
highly volatile cryptocurrency market. Existing works applied deep reinforcement
learning methods and optimistically reported increased profits in backtesting,
which may suffer from the false positive issue due to overfitting. In this paper,
we propose a practical approach to address backtest overfitting for
cryptocurrency trading using deep reinforcement learning. First, we formulate the
detection of backtest overfitting as a hypothesis test. Then, we train the DRL
agents, estimate the probability of overfitting, and reject the overfitted
agents, increasing the chance of good trading performance. Finally, on 10
cryptocurrencies over a testing period from 05/01/2022 to 06/27/2022 (during
which the crypto market crashed two times), we show that the less overfitted deep
reinforcement learning agents have a higher return than that of more overfitted
agents, an equal weight strategy, and the S&P DBM Index (market benchmark),
offering confidence in possible deployment to a real market."

### Backtest-overfitting detection as a hypothesis test

- **H0:** p < α → NOT overfitted. **H1:** p ≥ α → overfitted. Significance
  α = 10%. p = estimated probability of backtest overfitting (PBO).
- PBO computation:
  1. For each hyperparameter trial, average returns across validation sets →
     R_avg.
  2. Stack H trial vectors into matrix M ∈ ℝ^(T'×H).
  3. Split M into IS (in-sample) and OOS (out-of-sample); rank the performance
     metric within each; relative rank ω^c = r̄^c[ε]/(H+1); logit
     λ^c = ln(ω^c/(1-ω^c)); integrate p = ∫_{-∞}^{0} f(λ) dλ.
  - Negative logit ⇒ the best in-sample strategy underperforms out-of-sample ⇒
    overfitting.

### Setup

- **Cryptocurrencies (10):** AAVE, AVAX, BTC, NEAR, LINK, ETH, LTC, MATIC, UNI,
  SOL.
- **Data:** 5-minute bars. Training 02/02/2022–04/30/2022 (25,055 points);
  Testing 05/01/2022–06/27/2022 (16,704 points; two market crashes).
- **Combinatorial cross-validation (CPCV):** N = 5 groups, k = 2 validation
  groups, J = 10 total splits.
- **Hyperparameter trials:** H = 50, drawn from a space of 2,700 combinations
  across 6 parameters:
  - learning rate ∈ [3e-2, 2.3e-2, 1.5e-2, 7.5e-3, 5e-6]
  - batch size ∈ [512, 1280, 2048, 3080]
  - γ ∈ [0.95, 0.96, 0.97, 0.98, 0.99]
  - net dimension ∈ [2^9, 2^10, 2^11]
  - target step ∈ [2.5e3, 3.75e3, 5e3]
  - break step ∈ [3e4, 4.5e4, 6e4]

### DRL algorithms

PPO, TD3, SAC. Compared against two conventional model-selection protocols:
Walk-Forward (WF) and K-fold CV (KCV).

### Results

Probability of overfitting p:

| Method | p | Verdict |
|---|---|---|
| PPO Walk-Forward | 17.5% | rejected (p > α) |
| PPO K-fold CV | 7.9% | accepted |
| PPO (proposed CPCV) | 8.0% | accepted |
| TD3 (proposed) | 9.6% | accepted |
| SAC (proposed) | 21.3% | rejected (p > α) |

Backtest performance over the test period (market fell heavily):

| Metric | S&P BDM | Equal-Weight | PPO WF | PPO KCV | PPO (proposed) | TD3 | SAC |
|---|---|---|---|---|---|---|---|
| Cumulative return | -50.78% | -47.78% | -49.39% | -55.54% | **-34.96%** | -59.08% | -59.48% |
| Volatility | 5.81e-2 | 4.19e-3 | 2.79e-3 | 3.49e-3 | **2.01e-3** | 3.51e-3 | 3.78e-3 |

The accepted PPO agent beat conventional selection methods by >15% return, beat
TD3/SAC by >24%, and beat both benchmarks — but still lost ~35% in absolute terms
during the crash window (all strategies were long-biased into a falling market).

### Risk management overlay

CVIX (Crypto Volatility Index) threshold 90.1: above it, stop buying and
liquidate; resume when CVIX normalises.

### Key recommendation

Before deployment, apply the overfitting hypothesis test across multiple market
situations and **reject any agent with p ≥ α**. Reported to cut overfitting ~46%
vs. conventional train/validation selection.

---

## Capture notes

arXiv PDF would not text-extract; content taken from the ar5iv HTML mirror plus
the arXiv abstract page. Result tables as reported by the paper; the test window
is a single 8-week crash period, so absolute returns are all negative — the
paper's claim is relative (less-overfit > more-overfit), not that DRL was
profitable here.
