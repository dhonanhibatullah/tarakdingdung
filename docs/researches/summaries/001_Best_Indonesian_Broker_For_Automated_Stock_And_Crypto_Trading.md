# Best Indonesian Broker for Automated Stock & Crypto Trading (API-focused)

- **Question:** Which Indonesia-accessible broker(s) should tarakdingdung use to
  study and execute automated trading — most trustworthy, best API experience —
  covering (a) IDX / local stocks and (b) crypto? Separate providers are fine.
- **Last updated:** 2026-09-06
- **Status:** draft
- **Topic tags:** broker-selection, api, crypto, idx, equities, indonesia, indodax, tokocrypto, alpaca, regulation, security

---

## TL;DR

- **Crypto — use Tokocrypto as the primary execution venue, keep Indodax as
  secondary / data.** Tokocrypto is OJK-licensed (PAKD), 100% Binance-owned, and
  its API is a **Binance-cloud clone** (`X-MBX-APIKEY`, HMAC SHA256, weight-based
  rate limits, OCO, `executionReport` user stream) — so mature open-source
  tooling (`ccxt`, Binance-style clients) works with minimal adaptation
  (ref 002). Indodax is the oldest/largest and has a fully **official** REST +
  WebSocket + Trade API 2.0 with clear auth and rate limits and the deepest IDR
  liquidity (ref 001, ref 003), but it suffered a **~US$22–25M hot-wallet /
  withdrawal-system breach in Sep 2024** (users reimbursed) — so treat it as a
  trading venue with elevated custody risk: keep minimal balances, `view`+`trade`
  API keys only, never `withdraw` (ref 005).
- **IDX / local stocks — there is no trustworthy official execution API.** No
  Indonesian retail stock broker (Stockbit/Sinarmas, Ajaib, IPOT/Indo Premier,
  Mirae HOTS, Phillip/POEMS-ID) publishes an order-execution API. The only way
  to automate IDX orders today is **reverse-engineered Stockbit app endpoints**
  via community MCP servers — against ToS, with account-suspension risk
  (ref 006). Official/third-party IDX APIs (IDX Data Services, Sectors.app,
  Invezgo, GOAPI, OHLC.dev) are **data only** (ref 008).
- **If you want a proper equities API, go offshore, not IDX.** BrokerChooser
  rates **Alpaca** the best API broker accessible from Indonesia (REST/streaming,
  US-regulated) — but that is **US-listed** stocks/ETFs, not IDX (ref 007).
  **Interactive Brokers** covers more global markets (REST/FIX) but still no IDX
  cash equities (ref 007).
- **Recommended build order:** (1) build and validate the engine against
  **Tokocrypto** (best API ergonomics, Binance-compatible, so also easy to
  paper-test against Binance testnet); (2) add **Indodax** as a second crypto
  adapter for redundancy and IDR depth; (3) for stocks, start **research/backtest
  only** on IDX via a data vendor, and if live equities execution is required,
  use **Alpaca on US markets** rather than automating an Indonesian stock broker.

## Detail

### Regulatory / trust backdrop

Crypto oversight moved from **Bappebti to OJK on 10 January 2025**; licensed
venues are now "Digital Financial Asset Traders" (**PAKD**) that clear through
the state-backed **CFX** national crypto exchange, and OJK published an official
whitelist (March 2026) (ref 003, ref 004). Being CFX-connected also means
**automatic tax handling**: ~**0.21% final income tax (PPh)** withheld per
eligible trade, versus a self-reported ~**1%** bracket for offshore venues
(ref 004). Both **Indodax** and **Tokocrypto** are on the licensed list, so from
a compliance standpoint either is defensible; the differentiators are **API
quality** and **custody/security track record**.

Equities are OJK/IDX-regulated and traded through licensed local brokers, but
that regulatory maturity has **not** produced a retail execution API (ref 006,
ref 008).

### Crypto option A — Tokocrypto (recommended primary)

- **API (ref 002):** spot REST at `https://www.tokocrypto.com` with Binance-style
  auth — API key in `X-MBX-APIKEY`, SIGNED endpoints use **HMAC SHA256** over
  `totalParams`, `timestamp` + optional `recvWindow`. Order endpoints
  `POST /open/v1/orders` (LIMIT, MARKET, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT,
  TAKE_PROFIT_LIMIT, LIMIT_MAKER), `POST /open/v1/orders/oco`,
  `POST /open/v1/orders/cancel`, `GET /open/v1/orders/detail`. `timeInForce`
  GTC/IOC/FOK/GTX; self-trade-prevention modes; iceberg orders.
- **Streaming (ref 002):** market streams (`aggTrade`, `trade`, `kline`,
  `miniTicker`, `depth`) and user streams (`outboundAccountPosition`,
  `executionReport`) via a `listenToken` (24 h).
- **Rate limits (ref 002):** IP weight system with `X-MBX-USED-WEIGHT` /
  `X-MBX-ORDER-COUNT` headers, HTTP 429 / 418 semantics — identical model to
  Binance, so existing backoff logic ports over.
- **Why primary:** the Binance-compatibility means `ccxt` and the large body of
  Binance example code, backtesting adapters, and rate-limit handling apply
  directly; you can prototype/paper-trade against Binance Spot **testnet** and
  switch base URL + path prefix for live. Ownership by Binance and ISO 27001 /
  27017 certification (per general coverage) give it a stronger security posture
  than Indodax's recent history.
- **Caveats:** watch the changelog — the user-data-stream endpoint was
  **decommissioned 2026-04-30** in favour of `POST /open/v1/user-listen-token`
  (ref 002); "Nextme"/Type-3 symbols run on separate infra from Binance-standard
  Type-1 symbols, so pin your symbol universe. Confirm current API-key
  self-service signup and whether market-maker/volume tiers are needed.

### Crypto option B — Indodax (recommended secondary / IDR depth)

- **API (ref 001):** genuinely **official and documented** — Public REST
  (`/api/*`, 180 req/min, no auth), Private "tapi" (`POST https://indodax.com/tapi`,
  **HMAC SHA512**, `Key`/`Sign` headers, per-key `view`/`trade`/`withdraw`
  permissions), Market Data + Private WebSocket, and a **Deadman Switch**
  (auto-cancel on disconnect — useful for a bot losing connectivity).
- **Order model (ref 001):** `trade` method with `limit` / `market` / `stoplimit`;
  `GTC`/`MOC` TIF; client order IDs (dedupe); self-trade prevention. Cancel by
  order ID or client ID. Rate limits: 20 req/s per account+pair (5 s block on
  breach), 30 req/s for cancels.
- **Strengths:** deepest IDR order books and pair count among local exchanges
  (ref 003); the Deadman Switch is a real operational safety feature; fully
  sanctioned API means no ToS risk.
- **Deal-breaker-level caveat (ref 005):** the **Sep 2024 breach** (~US$22–25M,
  reportedly a withdrawal-system compromise, Lazarus-attributed). Indodax paused,
  contained, and **reimbursed users**, which is the good outcome — but it raises
  the bar for how much capital you park there. Mitigate: keep only working
  balance on-exchange, sweep profits out on a schedule, issue API keys with
  **no withdraw permission**, IP-allowlist, and rotate keys.
- **Migration note (ref 001):** `tradeHistory` / `orderHistory` "tapi" methods
  were deprecated 2026-04-07 → use `GET /api/v2/myTrades` and
  `GET /api/v2/order/histories`.

### IDX / local stocks — the gap

- **No official retail execution API** from any Indonesian stock broker
  (ref 006). Phillip Securities exposes a POEMS API gateway but only for its
  **Singapore** entity, not POEMS-ID.
- Community **Stockbit MCP servers** talk to "the same JSON backends used by
  Stockbit's official apps" and can place orders / subscribe to IPOs, but these
  are **unofficial, undocumented, reverse-engineered**, guarded behind
  "confirm + off by default" for good reason — using them for an always-on bot
  risks breaking on any app update and violates Stockbit/Sinarmas Sekuritas
  terms (ref 006).
- The healthy part of the IDX ecosystem is **data**: IDX Data Services
  (institutional feed), and REST APIs/SDKs from **Sectors.app, Invezgo
  (Python/Go/JS/Rust/PHP SDKs, incl. broker-summary & foreign-flow), GOAPI.io,
  OHLC.dev**, plus GitHub scrapers (ref 008). These are enough to **research,
  build signals, and backtest** an IDX strategy — just not to execute it
  programmatically.
- **PT Valbury Asia Futures** now fronts **Alpaca** for **US** stock trading
  from Indonesia (Jan 2026) — evidence the local market solves "API equities" by
  routing to offshore infrastructure, not by opening IDX (ref 006, ref 007).

### Offshore equities APIs (if live stock execution is required)

- **Alpaca** — BrokerChooser's #1 "API broker in Indonesia": developer-friendly
  REST + streaming, low fees, smooth onboarding, US-regulated; universe is
  **US-listed** stocks/ETFs (+ crypto) (ref 007).
- **Interactive Brokers** — broadest global market access, REST + FIX, but
  heavier onboarding and **still no IDX cash equities** (ref 007).
- Both are offshore for an Indonesian resident: account-opening, funding, FX and
  tax-reporting friction apply, and neither gives IDX exposure.

### Recommendation for tarakdingdung

1. **Crypto engine first, on Tokocrypto.** Best API ergonomics, Binance-tooling
   reuse, licensed + tax-integrated, better security posture. Build the exchange
   adapter against the Binance-compatible surface so it doubles as a Binance
   adapter later.
2. **Add Indodax as a second crypto adapter.** Official API, IDR depth, Deadman
   Switch; run it with hard custody limits and withdraw-disabled keys.
3. **IDX stocks: research/backtest only** via Invezgo or Sectors.app. Do **not**
   build production execution on reverse-engineered Stockbit endpoints.
4. **If live equity execution becomes a requirement, use Alpaca (US markets)** —
   accept that this changes the tradable universe from IDX to US-listed names.

## Open questions / gaps

- **Tokocrypto API-key self-service:** confirm a retail user can generate
  `trade`-scoped keys without a business/market-maker agreement, and current
  maker/taker fees and volume tiers. (Not settled by ref 002.)
- **Indodax post-hack hardening:** what concretely changed in the withdrawal
  system after Sep 2024, and any proof-of-reserves. (ref 005 is contemporaneous
  news only.)
- **ccxt coverage:** verify current `ccxt` support status/quality for both
  `indodax` and `tokocrypto` unified methods (fetchOHLCV, createOrder, watchers).
- **Latency / colocation:** typical REST + WebSocket round-trip from an
  Indonesian/SEA VPS to each venue — matters if the strategy is intraday.
- **IDX execution, future:** whether any local broker (or a fintech like Ajaib/
  Bibit) has an official API on a roadmap; whether IBKR or Saxo offer any IDX
  access at all.
- **Reku / Pintu / Pluang APIs:** no public trading API found (ref 003, ref 004);
  confirm none exists before ruling them out permanently.
- **Regulatory:** does OJK impose any rule on automated/algorithmic retail
  trading or bot API use on PAKD venues?

---

## References used

- `references/001_Indodax_Official_API_Documentation.md`
- `references/002_Tokocrypto_API_Documentation.md`
- `references/003_Fintech_News_Indonesia_Top_Licensed_Crypto_Exchanges_2026.md`
- `references/004_Liminal_Custody_Indonesia_Crypto_Regulation_Tax_Guide_2026.md`
- `references/005_Indodax_2024_Hot_Wallet_Hack.md`
- `references/006_Stockbit_Community_MCP_And_Unofficial_IDX_API_Access.md`
- `references/007_BrokerChooser_Best_Brokers_Algo_Trading_Indonesia_2026.md`
- `references/008_IDX_Third_Party_Market_Data_APIs.md`
