# Tokocrypto API Documentation

- **Source URL:** https://www.tokocrypto.com/apidocs/
- **Author / Publisher:** PT Aset Kripto Internasional (Tokocrypto; 100% Binance-owned)
- **Published:** living doc; recent changelog entries dated April–June 2026
- **Retrieved:** 2026-09-06; full v1 endpoint inventory added 2026-09-07
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

### Full REST endpoint inventory — v1 (`/open/v1/*`), added 2026-09-07

Base `https://www.tokocrypto.com` for both public and signed calls (confirmed
against `ccxt`'s `tokocrypto.py`, which maps exactly these paths). Signed calls:
`X-MBX-APIKEY` header + `&signature=<HMAC-SHA256(query_or_body, secret)>`
appended; `timestamp` (ms) required, `recvWindow` optional (≤ 60000).
Tokocrypto wraps responses as `{"code": <int>, "msg": <str>, "data": <...>}`;
`code == 0` is success. `side`: `0`=BUY `1`=SELL. `type`: `1`=LIMIT `2`=MARKET
`3`=STOP_LOSS `4`=STOP_LOSS_LIMIT `5`=TAKE_PROFIT `6`=TAKE_PROFIT_LIMIT
`7`=LIMIT_MAKER. `timeInForce`: `1`=GTC `2`=IOC `3`=FOK `4`=GTX.

| Method | Path | Security | Key params |
|---|---|---|---|
| GET | `/open/v1/common/time` | NONE | — |
| GET | `/open/v1/common/symbols` | NONE | — |
| GET | `/open/v1/market/depth` | NONE | `symbol`*, `limit` (≤ 5000) |
| GET | `/open/v1/market/trades` | NONE | `symbol`*, `fromId`, `limit` (≤ 1000) |
| GET | `/open/v1/market/agg-trades` | NONE | `symbol`*, `fromId`, `startTime`, `endTime`, `limit` |
| GET | `/open/v1/market/klines` | NONE | `symbol`*, `interval`* (1m…1M), `startTime`, `endTime`, `limit` |
| POST | `/open/v1/orders` | SIGNED | `symbol`*, `side`*, `type`*, `quantity`, `quoteOrderQty`, `price`, `stopPrice`, `icebergQty`, `clientId`, `timeInForce`, `selfTradePreventionMode`, `recvWindow`, `timestamp`* |
| GET | `/open/v1/orders/detail` | SIGNED | `orderId`* (or `clientId`), `recvWindow`, `timestamp`* |
| POST | `/open/v1/orders/cancel` | SIGNED | `orderId` or `clientId`, `recvWindow`, `timestamp`* |
| GET | `/open/v1/orders` | SIGNED | `symbol`*, `type` (`1`=open `2`=history `-1`=all), `side`, `startTime`, `endTime`, `fromId`, `direct` (`prev`/`next`), `limit`, `recvWindow`, `timestamp`* |
| POST | `/open/v1/orders/oco` | SIGNED | `symbol`*, `side`*, `quantity`*, `price`*, `stopPrice`*, `stopLimitPrice`*, `listClientId`, `limitClientId`, `stopClientId`, `recvWindow`, `timestamp`* |
| GET | `/open/v1/orders/trades` | SIGNED | `symbol`*, `orderId`, `startTime`, `endTime`, `fromId`, `direct`, `limit`, `recvWindow`, `timestamp`* |
| GET | `/open/v1/account/spot` | SIGNED | `recvWindow`, `timestamp`* |
| GET | `/open/v1/account/spot/asset` | SIGNED | `asset`*, `recvWindow`, `timestamp`* |
| POST | `/open/v1/withdraws` | SIGNED | `asset`*, `address`*, `amount`*, `network`, `addressTag`, `clientId`, `recvWindow`, `timestamp`* |
| GET | `/open/v1/withdraws` | SIGNED | `asset`, `status`, `fromId`, `startTime`, `endTime`, `recvWindow`, `timestamp`* |
| GET | `/open/v1/deposits` | SIGNED | `asset`, `status` (`0`=pending `1`=success), `fromId`, `startTime`, `endTime`, `recvWindow`, `timestamp`* |
| GET | `/open/v1/deposits/address` | SIGNED | `asset`*, `network`*, `recvWindow`, `timestamp`* |
| POST | `/open/v1/user-listen-token` | SIGNED | `validity` (ms, ≤ 24 h), `recvWindow`, `timestamp`* |

(* = mandatory.) Deprecated: `POST/PUT/DELETE /open/v1/user-data-stream`
(API_KEY security) — replaced by `user-listen-token`; legacy path decommissioned
2026-04-30. Market-data endpoints for Type-3 / "Nextme" symbols route to
`https://cloudme-toko.2meta.app/api/v1/*` instead, and Binance-standard Type-1
symbols may alternatively be served from `https://www.tokocrypto.site/api/v3/*`.

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

**2026-09-07 addition:** the "Full REST endpoint inventory — v1" table was
cross-checked against `ccxt`'s `python/ccxt/tokocrypto.py` (paths, base URL
`https://www.tokocrypto.com`, `X-MBX-APIKEY` + `&signature=` HMAC-SHA256 in
`sign()`), which lists the identical `/open/v1/*` set. Enum integer codes for
`side`/`type`/`timeInForce` are from the apidocs WebFetch and should be
re-verified against the live parameter tables before order code goes to
production.
