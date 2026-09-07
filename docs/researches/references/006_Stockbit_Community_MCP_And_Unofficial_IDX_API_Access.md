# Stockbit Community MCP Servers & Unofficial IDX Trading-API Access

- **Source URL:**
  - https://mcpmarket.com/server/stockbit
  - https://www.pulsemcp.com/servers/mrofisr-stockbit
  - https://github.com/topics/stockbit
  - https://github.com/SorataBaka/New-Composite-API
- **Author / Publisher:** independent developers (mcpmarket listing; `mrofisr`; `SorataBaka`); not Stockbit / Sinarmas Sekuritas
- **Published:** 2025–2026
- **Retrieved:** 2026-09-06
- **Retrieved by:** conducting-research skill, research/base-trading-algo session
- **Type:** tool listings / repos
- **Topic tags:** idx, stockbit, unofficial-api, reverse-engineered, mcp, order-execution, terms-of-service-risk, indonesia, broker-selection

---

## Raw content

### mcpmarket "Stockbit MCP" listing (as summarised in search results)

- Provides an MCP server for the Indonesian / IDX market that "directly
  interacts with the **same JSON backends used by Stockbit's official apps**."
- Read capabilities: broker summaries (bandarmology), real-time quotes, top
  movers, order-book data, fundamental analysis, sentiment, personal portfolio
  details, chart manipulation.
- Write capabilities: **order placement, IPO subscriptions**, chart drawing,
  watchlist management — "all behind explicit confirmation and off by default."
- Presented as an unofficial/community project; not an official Stockbit
  release. (An official trading-automation MCP announcement in April 2026 was
  from **Bybit**, not Stockbit.)

### PulseMCP "Stockbit Automation MCP Server" (`mrofisr`)

- Description: "UI automation and technical analysis for the Stockbit **desktop
  trading application**."
- Community-maintained (not official); server.json temporarily hosted by
  PulseMCP pending registry publication.
- Works by driving the desktop app UI rather than a documented API.
- No ToS / account-risk disclaimer shown on the listing page.

### Other community projects

- `SorataBaka/New-Composite-API` and similar repos **scrape** IDX equity/index
  information via the Stockbit API endpoints.
- Multiple GitHub projects under the `stockbit` topic pull data using
  undocumented Stockbit / yfinance endpoints.

### Context: no official local IDX execution API

- Search across IDX broker names (Stockbit/Sinarmas, Ajaib, IPOT/Indo Premier,
  Mirae Asset HOTS, Phillip/POEMS Indonesia) surfaced **no official retail
  order-execution API**. Phillip has a POEMS API gateway documented only for the
  **Singapore** entity (`poems.com.sg/docs/poemsapi/`), not Indonesia.
- Available IDX programmatic offerings are **market-data only**, from third
  parties: Sectors.app, Invezgo, GOAPI.io, OHLC.dev, plus GitHub scrapers.
- For automated equities execution accessible from Indonesia, brokers reviewed
  externally point to **offshore** API brokers (see ref 07); PT Valbury Asia
  Futures launched US-stock trading "powered by **Alpaca**" (Jan 2026), i.e.
  US-listed stocks, not IDX.

---

## Capture notes

Assembled from WebSearch snippets; `mcpmarket.com/server/stockbit` returned
HTTP 429 on direct fetch so its capability list is second-hand via search
excerpts (consistent across two separate queries). PulseMCP page fetched
directly. Key takeaway for the summary: IDX execution automation today means
**reverse-engineered Stockbit endpoints**, which run against Stockbit/Sinarmas
Sekuritas terms of service and carry account-suspension risk.
