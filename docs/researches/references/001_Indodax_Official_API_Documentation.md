# Indodax Official API Documentation

- **Source URL:** https://github.com/btcid/indodax-official-api-docs (and sub-files `README.md`, `Public-RestAPI.md`, `Private-RestAPI.md`, `Marketdata-websocket.md`, `Private-websocket.md`)
- **Author / Publisher:** PT Indodax Nasional Indonesia (GitHub org `btcid`)
- **Published:** repo ongoing; sub-docs updated through 2026 (deprecation notices dated April 2026)
- **Retrieved:** 2026-09-06
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

### Private REST API ("tapi" / Trade API)

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
`Private-RestAPI.md` is the current trade reference. Re-capture from the raw
`.md` files if byte-exact wording is needed.
