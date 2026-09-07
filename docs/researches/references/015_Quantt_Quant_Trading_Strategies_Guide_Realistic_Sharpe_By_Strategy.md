# Quantt — Quant Trading Strategies Guide (Realistic Sharpe by Strategy Type)

- **Source URL:** https://www.quantt.co.uk/resources/quant-trading-strategies-guide
- **Author / Publisher:** Quantt
- **Published:** dated 2026 (undated within page)
- **Retrieved:** 2026-09-07
- **Retrieved by:** Claude Sonnet 5, conducting-research session
- **Type:** article (practitioner / educational)
- **Topic tags:** sharpe-ratio, statistical-arbitrage, market-making, momentum, machine-learning, HFT, overfitting, reality-check

---

## Raw content

### "Realistic Sharpe" estimates by strategy type (2026)

| Strategy | Sharpe range |
|---|---|
| Statistical arbitrage | 1.0 – 2.0 |
| Pairs trading | 0.8 – 1.5 |
| Market making | 3.0 – 8.0+ |
| Momentum / trend following | 0.5 – 1.0 |
| Mean reversion (cross-sectional equity) | 0.6 – 1.2 |
| Machine learning | 0.5 – 1.5 |
| Options volatility / vol-arb | 0.8 – 2.0 |
| High-frequency trading | 5.0 – 20.0+ |
| Crypto quant strategies | 1.0 – 3.0+ |

### Caveat (verbatim)

"A 'realistic Sharpe' above 3 in any strategy at 2026 should make you suspicious"
— of look-ahead bias, survivorship bias, or other methodology errors. (Market
making and HFT are the exceptions: their high Sharpe comes from very high trade
counts and short holding periods, not from a large per-trade edge, and requires
co-location / low-latency infrastructure.)

All figures are "forward-looking estimates for 2026 or illustrative ranges
without historical verification."

---

## Capture notes

Fetched via WebFetch. Values are the site's own estimates, not audited fund
data. Useful mainly as a sanity band: a pure directional / ML strategy that
isn't a latency play should be expected to live around Sharpe 0.5–1.5, and any
backtest showing >3 for such a strategy is a red flag. Contrast with the
research-paper backtests (refs 009, 011) that report Sharpe 1.0–1.5 full-period
and 3+ in cherry-picked bull sub-windows.
