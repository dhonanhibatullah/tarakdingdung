# Indodax Official API Documentation

- **Source URL:** https://github.com/btcid/indodax-official-api-docs (and sub-files `README.md`, `Public-RestAPI.md`, `Private-RestAPI.md`, `INDODAX-TradeAPI-2.md`, `Marketdata-websocket.md`, `Private-websocket.md`)
- **Author / Publisher:** PT Indodax Nasional Indonesia (GitHub org `btcid`)
- **Published:** repo ongoing; sub-docs updated through 2026 (deprecation notices dated April 2026)
- **Retrieved:** 2026-09-06; TAPI v2 section added 2026-09-07
- **Retrieved by:** conducting-research skill, research/base-trading-algo session
- **Type:** docs (official API reference repository)
- **Topic tags:** crypto, indodax, exchange-api, rest-api, websocket, order-execution, indonesia, broker-selection

---

## Raw content

### Repository scope (README)

The repository documents the following **official and supported** APIs:

1. **Public REST API** — public market-data endpoints
2. **Private REST API** — authenticated account/trading endpoints (PHP example v2.0.1 available)
3. **Market Data WebSocket** — real-time market-data streaming
4. **Private WebSocket** — authenticated streaming
5. **INDODAX Trade API 2.0** — official trade API (version 2.0)
6. **Deadman Switch** — risk-management feature (auto-cancel orders if connection lost)

README disclaimer, verbatim sense:
> "Streams, endpoints, parameters, payloads, etc. described in the documents in
> this repository are considered **official** and **supported**. The use of any
> other streams, endpoints, parameters, or payloads, etc. is **not supported**."

### Public REST API

- **Base URL:** `https://indodax.com`
- **Rate limit:** "Public API rate limited to 180 request/minute."
- **Auth:** none for public endpoints. GET requests. JSON responses. Timestamps in milliseconds. Default pair `btcidr` when `pair_id` omitted.

| Endpoint | Purpose |
|----------|---------|
| `/api/server_time` | Server timezone + current timestamp (ms) |
| `/api/pairs` | All trading pairs with metadata |
| `/api/price_increments` | Minimum price increment per pair |
| `/api/summaries` | Aggregate market data across all pairs |
| `/api/ticker/$pair_id` | Single-pair ticker (OHLC + volume) |
| `/api/ticker_all` | All tickers |
| `/api/trades/$pair_id` | Recent trades for a pair |
| `/api/depth/$pair_id` | Order-book depth (bid/ask volumes) |
| `/tradingview/history_v2` | OHLC charting data, custom timeframes |

### Private REST API — legacy "tapi" / Trade API v1 (`Private-RestAPI.md`)

> **Version note (added 2026-09-07):** the endpoint below is now the **legacy /
> v1** trade surface. It requires a **v1 API key**. A key created as **TAPI v2**
> returns HTTP 403 `code -2015` ("invalid TAPI version key") here. See the
> separate "Trade API v2" section further down. The repo states the legacy
> endpoint "will be deprecated and decommissioned in a future release (a
> decommission date will be announced in advance)" and "all users are strongly
> encouraged to migrate" to v2.

- **Base URL:** `https://indodax.com/tapi`
- **All requests:** `POST`, with params `method`, `timestamp` or `nonce`, optional `recvWindow` (default 5000 ms).
- **Auth:** API key + secret, both case-sensitive. Key passed in `Key` header; signature in `Sign` header. Signature = **HMAC SHA512** of the concatenated query string + request body, using the secret key. Signature value itself is not case-sensitive.
  - Example: `echo -n 'method=getInfo&timestamp=1578304294000&recvWindow=1578303937000' | openssl dgst -sha512 -hmac 'secretkey'`
- **API-key permission levels:** `view`, `trade`, `withdraw` (independently grantable).

**Rate limits / reliability:**
- Trade API: "20 requests per second per account and pair" → exceeding triggers a 5-second block.
- Cancel order: 30 requests/second.
- Over limit → HTTP 429, `error_code: too_many_requests`.
- Transaction history: max 7-day lookback window; 500 records per request (per coin/direction).

**Key methods:**

| Method | Purpose | Permission |
|--------|---------|------------|
| `getInfo` | Account balances + deposit addresses | view |
| `trade` | Create buy/sell order | trade |
| `tradeHistory` | Transaction history (**deprecated 2026-04-07** → `GET /api/v2/myTrades`) | view |
| `openOrders` | Active orders | view |
| `orderHistory` | Closed orders (**deprecated 2026-04-07** → `GET /api/v2/order/histories`) | view |
| `cancelOrder` | Cancel by order ID | trade |
| `cancelByClientOrderId` | Cancel by custom client ID | trade |
| `withdrawCoin` | Crypto withdrawal | withdraw |

**Order types:** `limit` (default), `market`, `stoplimit`.
- Buy orders specified via `idr` amount or coin amount.
- Market buy supports only the `idr` parameter.
- `limit` buy with `idr` + `order_type: limit` is rejected.

**Time-in-force (limit only):** `GTC` (default), `MOC` (maker-only-cancel).
**Self-trade prevention:** `smp_cancel` = `MAKER` | `TAKER` | `BOTH`.
**Client order IDs:** optional, max 36 chars alphanumeric + `_`/`-`; prevents duplicate submissions.
**Memo support:** for assets needing destination tags (XRP), messages (NXT), memos (BitShares).
**Zero-fee internal transfers:** `withdrawCoin` to another Indodax username.

**Sample pairs:** `btc_idr`, `ltc_btc`, `doge_btc` (400+ pairs total per market coverage).

### Trade API v2 — "TAPI v2" (`INDODAX-TradeAPI-2.md`, captured 2026-09-07)

A **separate API surface**, not just a new key on the old endpoint. Binance-style
REST. Legacy `/tapi` integrations "must be migrated" to these endpoints.

- **Base URL:** `https://api.indodax.com` (all endpoints return JSON; timestamps
  in ms; results sorted newest-first).
- **Dedicated key required:** "TAPIv2 can only be accessed with a dedicated
  TAPIv2 API key." Existing v1 keys cannot be reused. Generate at
  `https://indodax.com/trade_api`. After regenerating a key, API coin
  withdrawals are blocked for 24 h (website/app still work).
- **Request headers:**
  - `Accept: application/json` (mandatory)
  - `X-APIKEY: <api key>` (mandatory; case-sensitive)
  - `Content-Type: application/x-www-form-urlencoded` (POST only)
  - `Sign: <signature>` — **HMAC-SHA256** of the query string (for GET/DELETE)
    or query string concatenated with request body (for POST), hex digest, using
    the secret key. Signature is case-insensitive. May alternatively be sent as
    a `signature` query param or body field.
- **Timing:** each request needs `timestamp` (ms) or `nonce` (incrementing int);
  if both sent, `timestamp` wins. Optional `recvWindow` (default 5000 ms).
  Reject if `timestamp >= serverTime + 1000` or `serverTime - timestamp > recvWindow`.
- **Permission scope (all require the matching whitelist to be populated):**
  - Reading / View Only — IP permission optional
  - Spot Trading (create & cancel orders) — **IP whitelist required**
  - IDR & Crypto Withdrawal — **IP whitelist required** + address or username whitelist
- **Rate limits (per IP):** 300 req/min for order/account/history endpoints;
  50 req/min for capital (withdraw/deposit) endpoints. Order create & cancel
  additionally capped at **20 req/s per user per trading pair** (applies even to
  whitelisted IPs).

**Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v2/order` | POST | Create order (`LIMIT` / `MARKET`) |
| `/api/v2/order` | DELETE | Cancel order |
| `/api/v2/openOrders` | GET | Pending orders |
| `/api/v2/order` | GET | Order detail |
| `/api/v2/account` | GET | Account info + balances |
| `/api/v2/capital/withdraw/history` | GET | Crypto withdrawal history |
| `/api/v2/capital/deposit/hisrec` | GET | Crypto deposit history |
| `/api/v2/fiat/orders` | GET | Fiat deposit/withdrawal history |
| `/api/v2/capital/withdraw/apply` | POST | Submit crypto withdrawal |
| `/api/v2/capital/deposit/address/list` | GET | Deposit addresses |
| `/api/v2/fiat/withdraw` | POST | Submit IDR withdrawal |
| `/api/v2/order/histories` | GET | Order history |
| `/api/v2/myTrades` | GET | Trade history |

**Create Order params:** `symbol` (e.g. `BTCIDR`), `side` (`BUY`/`SELL`),
`type` (`LIMIT`/`MARKET`), `price` (LIMIT), `quantity` (all except MARKET BUY),
`quoteOrderQty` (MARKET BUY only, IDR), `newClientOrderId` (≤36 chars,
alnum + `_` `-`), `timeInForce` (`GTC` default / `MOC`),
`selfTradePreventionMode` (`EXPIRE_TAKER` / `EXPIRE_MAKER` (default) / `EXPIRE_BOTH`).

**`GET /api/v2/account`** — optional `omitZeroBalances` (bool, default false).
Response:

```json
{
  "canTrade": true,
  "canWithdraw": true,
  "accountType": "Regular",
  "balances": [ { "asset": "BTC", "free": "…", "locked": "0.00000000" } ],
  "uid": 1776329213
}
```

**Signed GET example (from docs):**

```
queryString: symbol=btcidr&limit=100&timestamp=1578304294000&recvWindow=1578303937000
Sign: echo -n "<queryString>" | openssl dgst -sha256 -hmac "<secretKey>"
curl -H "X-APIKEY: <key>" -H "Sign: <sig>" -X GET \
  'https://api.indodax.com/api/v2/myTrades?symbol=btcidr&limit=100&timestamp=…&recvWindow=…'
```

**Error codes (subset):** `-1002` invalid credentials / key not found (HTTP 401);
`-1021` timestamp outside recvWindow; `-1022` invalid nonce/signature or `Sign`
header missing; `-2014` API key not found in header; `-2015` (HTTP 403) access
denied — "Trade API is disabled, account is locked/disabled, no permission,
unauthorized IP address, or **invalid TAPI version key**"; `-1003` too many
requests; `-1121` invalid symbol.

**Connectivity test (2026-09-07, this project's v2 key):**
`GET https://api.indodax.com/api/v2/account` → HTTP 200,
`canTrade=true`, `canWithdraw=false`, `accountType=individual`, balances
returned. Same credentials against the legacy `https://indodax.com/tapi`
previously returned `-2015` / `invalid_version_key` — confirming the two
surfaces are distinct and the key is bound to v2.

### WebSocket

- **Market Data WebSocket:** real-time trades / trading activity; channel format `market:trade-activity-<pair>`.
- **Private WebSocket:** authenticated account/order stream.
- **Deadman Switch:** documented as a distinct safety endpoint.

---

## Capture notes

Captured via WebFetch of the GitHub `README.md`, `Public-RestAPI.md`, and
`Private-RestAPI.md` (rendered pages) plus a corroborating WebSearch result set.
WebFetch returned model-condensed extractions rather than byte-exact markdown;
the endpoint tables, rate-limit numbers, auth mechanism (HMAC SHA512), order
types and the April 2026 deprecation notices are reproduced from those
extractions. A direct fetch of `Trade-API-class.md` 404'd (file renamed/moved);
`Private-RestAPI.md` is the current v1 trade reference.

**2026-09-07 addition:** the "Trade API v2" section was captured from the raw
`INDODAX-TradeAPI-2.md` (via `curl` on `raw.githubusercontent.com`), so its
headers/params/endpoints/error-codes are byte-accurate to that file. The
connectivity-test line reflects a live call made from this project's machine
(egress IP 118.99.94.221, which is on the key's IP allowlist) using the
`TRDD_BE_INDODAX_V2_*` credentials in `backend/.env`. Earlier notes in this repo
that treated `invalid_version_key` as unexplained are superseded: it simply means
a v2 key was used against the v1 `/tapi` endpoint (or vice-versa).
