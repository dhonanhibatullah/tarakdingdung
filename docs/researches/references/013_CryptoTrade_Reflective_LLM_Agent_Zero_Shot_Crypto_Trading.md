# CryptoTrade: A Reflective LLM-based Agent to Guide Zero-shot Cryptocurrency Trading

- **Source URL:** https://arxiv.org/abs/2407.09546 (HTML: https://ar5iv.labs.arxiv.org/abs/2407.09546 ; ACL: https://aclanthology.org/2024.emnlp-main.63/)
- **Author / Publisher:** Yuan Li, Bingqiao Luo, Qian Wang, Nuo Chen, Xu Liu, Bingsheng He (NUS Xtra-Computing)
- **Published:** EMNLP 2024 (Main). arXiv 2024-07-01. Code: github.com/Xtra-Computing/CryptoTrade
- **Retrieved:** 2026-09-07
- **Retrieved by:** Claude Sonnet 5, conducting-research session
- **Type:** paper
- **Topic tags:** llm-agents, reflection, on-chain-data, zero-shot, crypto, backtesting, technical-analysis-baselines

---

## Raw content

### Abstract (paraphrased from page — see capture notes)

LLMs in financial trading have been concentrated on equities; crypto is
underexplored. CryptoTrade combines **on-chain and off-chain** data with a
**reflective mechanism** that refines daily trading decisions by analysing the
outcomes of prior decisions. In experiments it beats time-series baselines and is
comparable to (but does **not** consistently beat) traditional technical-analysis
signals, across several coins and market conditions.

### Agent design (4 agents)

1. **Market Analyst** — on-chain trading signals: MA, MACD, Bollinger Bands.
2. **News Analyst** — market sentiment from news summaries.
3. **Trading Agent** — daily buy/sell/hold with allocation %.
4. **Reflection Agent** — weekly review of performance to refine future strategy.

### Data

- **On-chain** (CoinMarketCap + Dune): daily price, volume, market cap;
  transaction counts, active wallets, total value transferred, gas prices, gas
  consumed.
- **Off-chain** (Gnews API): articles filtered from Bloomberg, Yahoo Finance,
  crypto.news.

### Assets and windows

- BTC, ETH, SOL.
- Bull: 2023-10-01 to 2023-12-01. Sideways: mid-2023 periods. Bear: 2023-04 to
  2023-06.

### LLMs

GPT-3.5-turbo (data analysis); GPT-4 and GPT-4o (trading decisions).

### Results — return % (Sharpe)

**BTC**

| Strategy | Bull ret | Sideways ret | Bear ret | Bull SR | Sideways SR | Bear SR |
|---|---|---|---|---|---|---|
| Buy & Hold | 39.66% | -0.83% | -15.61% | 0.25 | 0.00 | -0.11 |
| MACD | 13.57% | -6.71% | -9.51% | 0.15 | -0.09 | -0.09 |
| SLMA | 38.53% | -3.14% | -7.68% | 0.25 | -0.05 | -0.09 |
| CryptoTrade (GPT-4) | 26.35% | -4.07% | -11.72% | 0.23 | -0.04 | -0.11 |
| CryptoTrade (GPT-4o) | 28.47% | -5.08% | -13.71% | 0.23 | -0.06 | -0.12 |

**ETH**

| Strategy | Bull ret | Sideways ret | Bear ret | Bull SR | Sideways SR | Bear SR |
|---|---|---|---|---|---|---|
| Buy & Hold | 22.59% | -1.91% | -12.24% | 0.14 | -0.00 | -0.07 |
| MACD | 7.72% | 0.77% | -12.15% | 0.10 | 0.01 | -0.12 |
| SLMA | 5.20% | -2.62% | -15.90% | 0.05 | -0.03 | -0.13 |
| CryptoTrade (GPT-4) | 25.72% | 0.72% | -13.72% | 0.17 | 0.02 | -0.10 |
| CryptoTrade (GPT-4o) | 25.47% | -6.59% | -15.35% | 0.18 | -0.04 | -0.11 |

**SOL**

| Strategy | Bull ret | Sideways ret | Bear ret | Bull SR | Sideways SR | Bear SR |
|---|---|---|---|---|---|---|
| Buy & Hold | 176.72% | -3.23% | -36.08% | 0.30 | 0.00 | -0.18 |
| MACD | 23.25% | -9.78% | -21.07% | 0.20 | -0.07 | -0.13 |
| SLMA | 169.98% | 6.22% | -8.11% | 0.30 | 0.05 | -0.06 |
| CryptoTrade (GPT-4) | 99.84% | -2.16% | -19.55% | 0.27 | 0.00 | -0.13 |
| CryptoTrade (GPT-4o) | 115.18% | 3.09% | -16.32% | 0.28 | 0.03 | -0.10 |

### Where CryptoTrade won / lost

- **Won:** ETH bull (~3% over buy-and-hold); consistently beat time-series
  models (Informer, PatchTST); roughly matched traditional signals.
- **Lost:** BTC bull (26–28% vs 39.66% buy-and-hold); SOL bull (100–115% vs
  176.72% buy-and-hold and 170% SLMA); bear and sideways — negative returns
  across essentially all assets and all strategies (it lost less than buy-and-hold
  in some bear cases but was rarely positive).

---

## Capture notes

Extracted from the ar5iv HTML mirror. Abstract wording is a close paraphrase, not
a verbatim quote (quote limit). The headline takeaway — an LLM agent that beats
naive DL forecasters but **not** simple moving-average / buy-and-hold rules, and
loses money outside bull markets — is the paper's own reported result.
