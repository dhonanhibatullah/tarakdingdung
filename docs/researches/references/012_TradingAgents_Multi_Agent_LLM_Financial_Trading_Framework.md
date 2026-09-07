# TradingAgents: Multi-Agents LLM Financial Trading Framework

- **Source URL:** https://arxiv.org/abs/2412.20138 (project: https://tradingagents-ai.github.io/ ; alphaXiv: https://www.alphaxiv.org/abs/2412.20138)
- **Author / Publisher:** Yijia Xiao, Edward Sun, Di Luo, Wei Wang (UCLA / MIT); presented in the ICLR 2025 workshop track / arXiv
- **Published:** 2024-12-28 (backtests early 2024)
- **Retrieved:** 2026-09-07
- **Retrieved by:** Claude Sonnet 5, conducting-research session
- **Type:** paper (with open-source framework, github.com/TauricResearch/TradingAgents)
- **Topic tags:** llm-agents, multi-agent, equities, debate, backtesting, sentiment, risk-management

---

## Raw content

### Agent architecture

Simulates a trading firm with specialised LLM agents:

- **Analyst team:** fundamental analyst, sentiment analyst, news analyst,
  technical analyst.
- **Researcher team:** Bull researcher vs Bear researcher engage in a structured
  **debate** over the analysts' reports.
- **Trader agent:** composes the trade decision from the debate outcome.
- **Risk management team:** evaluates the proposed trade against risk parameters;
  a portfolio/fund manager agent gives final approval.
- Agents communicate via structured natural-language reports and a debate
  protocol rather than only passing numeric signals.

### Data inputs

Historical OHLCV; 60 technical indicators per asset; news articles; social-media
sentiment; insider transactions; financial statements. Strict temporal
constraints to prevent look-ahead.

### LLMs used

GPT-4o-mini and GPT-4o for routine tasks; o1-preview for reasoning-intensive
steps.

### Backtest

- **Tickers:** AAPL, GOOGL, AMZN, NVDA, META, MSFT (major tech names).
- **Period:** 2024-01-01 to 2024-03-29 (~3 months).
- Baselines: Buy-and-Hold, MACD, KDJ+RSI, ZMR (zero-mean reversion), SMA.

### Quantitative results (TradingAgents)

| Ticker | Cumulative return | Sharpe ratio | Max drawdown |
|---|---|---|---|
| AAPL | 26.62% | 8.21 | 0.91% |
| GOOGL | 24.36% | 6.39 | 1.69% |
| AMZN | 23.21% | 5.60 | 2.11% |

Paper states TradingAgents "consistently exceeded all baseline strategies, often
by margins exceeding 20%" in cumulative return, with higher Sharpe and lower max
drawdown. Full per-ticker baseline comparison tables were not extractable from
the sources retrieved.

### Stated limitations

- Hallucination mitigation in LLM outputs.
- Factor-extraction accuracy for profitable signals.
- Real-world implementation vs backtesting gap.

---

## Capture notes

arXiv PDF did not text-extract cleanly; numbers above are from the alphaXiv
rendering and search summaries. **Reader caution (capture-level, not authored
analysis):** Sharpe ratios of 5–8 over a single 3-month window on 6 mega-cap
tech stocks are extreme and typical of short, favorable evaluation windows;
treat as illustrative, not as evidence of a deployable edge. Framework is for
equities, not crypto, but is the most-cited multi-agent LLM trading design and
has been forked for crypto.
