# IDX Market-Data APIs — Third-Party Providers (Data Only, No Execution)

- **Source URL:**
  - https://sectors.app/
  - https://invezgo.com/data-api-saham-indonesia and https://invezgo.com/sdk-saham-indonesia
  - https://goapi.io/api-data-saham-indonesia/
  - https://ohlc.dev/indonesia-stock-exchange-idx-api
  - https://www.idx.co.id/en/products/idx-data-services/
  - https://github.com/NeaByteLab/IDX-API
- **Author / Publisher:** Sectors.app; Invezgo; GOAPI.io; OHLC.dev; PT Bursa Efek Indonesia (IDX); NeaByteLab (GitHub)
- **Published:** current as of 2026
- **Retrieved:** 2026-09-06
- **Retrieved by:** conducting-research skill, research/base-trading-algo session
- **Type:** vendor pages / docs / repo
- **Topic tags:** idx, market-data, rest-api, sdk, backtesting, indonesia, data-vendor, broker-selection

---

## Raw content

- **IDX Data Services (official, idx.co.id):** system-to-system data feed —
  real-time, delayed, end-of-day, and log data for stocks, bonds, derivatives.
  Subscription / licensee model aimed at institutions and redistributors; not a
  retail self-serve trading API.
- **Sectors.app:** "API-first financial data for Indonesia stock market" —
  stocks, sectors, indices; updated daily; ~99% coverage of IDX-listed stocks.
- **Invezgo:** real-time IDX data via REST API — stock prices, volume, financial
  reports, **broker data, foreign flow**, technical indicators; "production-ready
  REST API"; official SDKs for Rust, JS, Python, Go, PHP, marketed for
  connecting trading bots and quant analysis.
- **GOAPI.io:** "fast, stable, and accurate access to Indonesian capital-market
  data" for developers.
- **OHLC.dev:** IDX API covering equities, bonds, derivatives, structured
  warrants, exchange activity; Redis-cached for performance; real-time +
  historical.
- **GitHub `NeaByteLab/IDX-API`, `SorataBaka/New-Composite-API`:** open-source
  wrappers/pipelines (Deno/Drizzle etc.) scraping IDX + Stockbit data for
  company info, indices, trading data.

All of the above are **market data / research** feeds. **None place orders** —
there is no execution or account-management capability in this tier.

---

## Capture notes

Compiled from WebSearch result summaries across two queries; individual vendor
pages not deep-fetched. Sufficient to establish the point used in the summary:
IDX has a healthy *data* API ecosystem but a missing *execution* API layer for
retail/automated traders.
