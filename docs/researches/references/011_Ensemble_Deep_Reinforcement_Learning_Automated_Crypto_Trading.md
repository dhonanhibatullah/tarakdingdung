# An Ensemble Method of Deep Reinforcement Learning for Automated Cryptocurrency Trading

- **Source URL:** https://arxiv.org/abs/2309.00626 (HTML: https://ar5iv.labs.arxiv.org/abs/2309.00626)
- **Author / Publisher:** (arXiv preprint, q-fin.TR) — authors per arXiv listing
- **Published:** 2023-09-01
- **Retrieved:** 2026-09-07
- **Retrieved by:** Claude Sonnet 5, conducting-research session
- **Type:** paper
- **Topic tags:** deep-reinforcement-learning, ensemble, PPO, portfolio-allocation, crypto, backtesting, FinRL

---

## Raw content

### Method

- **Base algorithm:** Proximal Policy Optimization (PPO) only — *not* a
  multi-algorithm ensemble.
- **Ensembling:** from a single PPO training run, select K models by validation
  performance across multiple periods, then combine them via a "novel mixture
  distribution policy" with equal weighting across the selected models.

### Universe and data

- 5 cryptocurrencies + USD: BTC, ETH, BCH, XRP, LTC.
- Hourly OHLCV from Kraken, 2018-01-01 to 2022-06-30.

### Splits

- Training: 6-month rolling window.
- Validation: 9 randomly selected weekly periods inside each training window.
- Testing: 48 monthly periods over 4 years (208 weekly test periods total),
  out-of-sample.

### Results (4-year out-of-sample)

| Metric | Ensemble policy | FinRL (single) | Buy-and-Hold |
|---|---|---|---|
| Annualized return | 0.9319 | 0.6320 | 0.7571 |
| Cumulative return | 7.9361 | 4.8851 | 2.6088 |
| Sharpe ratio | 1.0724 | 1.0401 | 0.8119 |
| Sortino ratio | 1.6218 | 1.3762 | 1.2560 |
| Max drawdown | 0.6953 | 0.4818 | 0.7430 |
| Volatility | 0.8690 | 0.6076 | 0.9325 |

Ensemble beat buy-and-hold on cumulative return (7.94× vs 2.61×) and Sharpe
(1.07 vs 0.81) over 4 years, but with a **69.5% max drawdown**.

### Limitations stated by authors

- "Excels at exploiting the upward trend" but "shows limited protection during
  market crashes."
- No learned covariance structure.
- **Transaction costs not modelled.**
- Long-only (no shorts).
- Assumes markets "liquid enough" with negligible spreads.

---

## Capture notes

arXiv PDF did not text-extract; content from the ar5iv HTML mirror via WebFetch.
Metrics are ratios/multiples as reported (e.g. cumulative return 7.9361 = +694%).
Drawdown reported as a fraction (0.6953 = 69.5%). Not independently verified.
