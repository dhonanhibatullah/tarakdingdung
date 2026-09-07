# Tokocrypto API Documentation

- **Source URL:** https://www.tokocrypto.com/apidocs/
- **Author / Publisher:** PT Aset Kripto Internasional (Tokocrypto; 100% Binance-owned)
- **Published:** living doc; recent changelog entries dated April–June 2026
- **Retrieved:** 2026-09-06
- **Retrieved by:** conducting-research skill, research/base-trading-algo session
- **Type:** docs (official API reference)
- **Topic tags:** crypto, tokocrypto, binance, exchange-api, rest-api, websocket, order-execution, indonesia, broker-selection

---

## Raw content

### API surface

Spot trading exposed through two symbol families:
- **Type 1 (Main / MBX)** — standard **Binance-compatible** symbols and schema.
- **Type 3 (Nextme)** — next-gen symbols on separate infrastructure.

### Base URLs

- REST: `https://www.tokocrypto.com` and `https://www.tokocrypto.site`
- WebSocket streams: `wss://stream-cloud.tokocrypto.site/stream` (Type 1),
  `wss://stream-toko.2meta.app` (Type 3)
- WebSocket API: `wss://ws-api.tokocrypto.site:443/ws-api/v3`

### Authentication

- API-key header: `X-MBX-APIKEY`
- SIGNED endpoints: additional `signature` param, "HMAC SHA256 signatures using
  your secretKey as the key and totalParams as the value"; plus `timestamp`
  (and optional `recvWindow`).
- Data returned in ascending order (oldest first). All times in milliseconds.

### Rate limits

- IP-based request limits with a weight system; per-account order-rate limits.
- Response headers `X-MBX-USED-WEIGHT` and `X-MBX-ORDER-COUNT`.
- HTTP 429 on violation; HTTP 418 for IP bans (escalating 2 minutes → 3 days).

### Order endpoints

- `POST /open/v1/orders` — create order (LIMIT, MARKET, STOP variants)
- `GET  /open/v1/orders/detail` — query order status
- `POST /open/v1/orders/cancel` — cancel by `orderId` or `clientId`
- `GET  /open/v1/orders` — list all orders
- `POST /open/v1/orders/oco` — One-Cancels-Other

**Order types:** LIMIT, MARKET, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT,
TAKE_PROFIT_LIMIT, LIMIT_MAKER.
**Key params:** `timeInForce` (GTC / IOC / FOK / GTX),
`selfTradePreventionMode` (EXPIRE_MAKER / EXPIRE_TAKER / EXPIRE_BOTH /
DECREMENT / TRANSFER), `icebergQty`.

### WebSocket

- Market-data streams: `aggTrade`, `trade`, `kline`, `miniTicker`, `depth`
  (partial / diff).
- User-data streams: `outboundAccountPosition`, `executionReport`, via
  `listenToken` (24-hour validity).

### Status (as of 2026)

- REST endpoints and WebSocket streams operational.
- Deprecated: `POST/PUT/DELETE /open/v1/user-data-stream` → migrate to
  `POST /open/v1/user-listen-token`; old path decommissioned **2026-04-30**.
- Recent changes: STP modes added June 2026; Price-Range execution rules
  April 2026.

---

## Capture notes

Captured via WebFetch of `https://www.tokocrypto.com/apidocs/` (model-condensed
extraction) plus corroborating WebSearch snippets. The doc is explicitly a
Binance-cloud derivative: request signing, header names, weight system, order
types, STP modes and stream names mirror Binance Spot, so Binance-oriented
tooling (e.g. `ccxt`, `python-binance`-style clients) maps onto it with the
`/open/v1/*` path prefix. Not byte-exact; re-fetch the live page for exact
parameter tables.
