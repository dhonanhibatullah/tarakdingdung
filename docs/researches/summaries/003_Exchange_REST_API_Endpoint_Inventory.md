# Exchange REST API Endpoint Inventory — Indodax v1, Indodax v2, Tokocrypto v1

- **Question:** What is the complete set of REST endpoints tarakdingdung's
  exchange adapters must cover for Indodax (Trade API v1 "tapi" + Trade API v2)
  and Tokocrypto (v1 `/open/v1/*`), with their auth model, request shape and
  response envelope?
- **Last updated:** 2026-09-07
- **Status:** draft
- **Topic tags:** indodax, tokocrypto, exchange-api, rest, endpoint-inventory,
  auth, hmac, order-execution, market-data, wallet

---

## TL;DR

- **Three surfaces, three auth schemes.** Indodax v1 "tapi": one POST endpoint,
  `method=` dispatch, `Key` + `Sign` (**HMAC-SHA512** over body), envelope
  `{"success":0|1,...}`. Indodax v2: RESTful `/api/v2/*`, `X-APIKEY` + `Sign`
  (**HMAC-SHA256** over query string, `+body` on POST), errors as
  `{"code":-N,"msg":...}`. Tokocrypto v1: Binance-cloned `/open/v1/*`,
  `X-MBX-APIKEY` + `&signature=` (**HMAC-SHA256**), envelope
  `{"code":0,"msg":..,"data":..}` (`code==0` = success) (refs 001, 002).
- **Indodax public market data** (`https://indodax.com/api/*`, no auth) is
  shared and unversioned — 9 endpoints: server_time, pairs, price_increments,
  summaries, ticker, ticker_all, trades, depth, and OHLC (`/tradingview/history_v2`).
- **Indodax v1 private** = 15 methods: getInfo, transHistory, trade,
  tradeHistory, openOrders, orderHistory, getOrder, getOrderByClientOrderId,
  cancelOrder, cancelByClientOrderId, withdrawFee, withdrawCoin, listDownline,
  checkDownline, createVoucher (partner-only). `tradeHistory`/`orderHistory`
  are decommissioned 2026-04-07 → use the v2 equivalents.
- **Indodax v2** = 13 endpoints: order create/cancel/query, openOrders, account,
  order/histories, myTrades, capital withdraw+deposit history, deposit address
  list, fiat orders, coin withdraw apply, fiat withdraw.
- **Tokocrypto v1** = 20 REST endpoints: common time+symbols; market
  depth/trades/agg-trades/klines + `executionRules` (on `.site/api/v3`); orders
  create/detail/cancel/list, OCO, orders/trades; account spot + spot/asset;
  withdraws (POST+GET), deposits (GET), deposits/address; user-listen-token.
- **WebSocket** (see §E): Indodax market + private streams, Tokocrypto market +
  user-data streams — contracts and a reconnecting baseline client are wired
  alongside the REST surface.
- **Recommended coverage order** (from summary 001): Tokocrypto v1 first,
  Indodax v2 second, Indodax v1 only as fallback. Contracts + infra clients for
  all three live under `backend/src/tarakdingdung/{domain/contracts,infrastructure}/api/`.

## Detail

### A. Indodax — Public REST API (ref 001)

Base `https://indodax.com`. GET, no auth. 180 req/min. Times in ms.

| # | Endpoint | Purpose |
|---|---|---|
| 1 | `GET /api/server_time` | Server timezone + epoch (ms) |
| 2 | `GET /api/pairs` | All pairs with precision/min-order metadata |
| 3 | `GET /api/price_increments` | Tick size per pair |
| 4 | `GET /api/summaries` | 24h/7d snapshot for all pairs |
| 5 | `GET /api/ticker/{pair_id}` | Single-pair ticker (default `btcidr`) |
| 6 | `GET /api/ticker_all` | All tickers |
| 7 | `GET /api/trades/{pair_id}` | Recent public trades |
| 8 | `GET /api/depth/{pair_id}` | Order-book depth (`buy`/`sell` arrays) |
| 9 | `GET /tradingview/history_v2` | OHLC candles — params `from`, `to`, `tf` (`1`,`15`,`30`,`60`,`240`,`1D`,`3D`,`1W`), `symbol` (e.g. `BTCIDR`) |

### B. Indodax — Trade API v1 / legacy "tapi" (ref 001)

`POST https://indodax.com/tapi`, `application/x-www-form-urlencoded`. Headers
`Key`, `Sign` = HMAC-SHA512(secret, request-body). Body always carries `method`
+ (`timestamp` ms **or** `nonce`) + optional `recvWindow` (default 5000).
Response `{"success":1,"return":{...}}` or `{"success":0,"error":...,"error_code":...}`.
Permissions: **view** {getInfo, transHistory, tradeHistory, openOrders,
orderHistory, getOrder, getOrderByClientOrderId}, **trade** {trade, cancelOrder,
cancelByClientOrderId}, **withdraw** {withdrawFee, withdrawCoin}.

| # | `method` | Key params | Notes |
|---|---|---|---|
| 1 | `getInfo` | — | balances, balance_hold, addresses, networks, withdraw_status |
| 2 | `transHistory` | `start`, `end` (Y-m-d) | deposits+withdrawals; max 7-day window, ≤ 500 rows |
| 3 | `trade` | `pair`*, `type`* (buy/sell), `price` (limit), `idr` **or** `btc`(coin amt), `order_type` (limit/market), `client_order_id`, `time_in_force` (GTC/MOC), `smp_cancel` (MAKER/TAKER/BOTH) | 20 req/s per account+pair; market BUY = `idr` only |
| 4 | `tradeHistory` | `pair`*, `count`, `from_id`, `end_id`, `order`, `since`, `end`, `order_id` | **decommissioned 2026-04-07** → v2 `myTrades` |
| 5 | `openOrders` | `pair` | omit `pair` → grouped by pair |
| 6 | `orderHistory` | `pair`*, `count`, `from` | **decommissioned 2026-04-07** → v2 `order/histories` |
| 7 | `getOrder` | `pair`*, `order_id`* | single order detail |
| 8 | `getOrderByClientOrderId` | `client_order_id`* | as above by client id |
| 9 | `cancelOrder` | `pair`*, `order_id`*, `type`* (buy/sell), `order_type` (limit/stoplimit) | 30 req/s |
| 10 | `cancelByClientOrderId` | `client_order_id`* | 30 req/s |
| 11 | `withdrawFee` | `currency`*, `network` | needs withdraw perm |
| 12 | `withdrawCoin` | `currency`*, `network`*, `withdraw_address`*, `withdraw_amount`*, `withdraw_memo`, `request_id`*; or by username: `withdraw_input_method`=`username`, `withdraw_username` | needs withdraw perm + callback URL |
| 13 | `listDownline` | `page`*, `limit`* | affiliate downline list |
| 14 | `checkDownline` | `email`* | 1/0 membership check |
| 15 | `createVoucher` | `amount`*, `to_email`* | **partner-only** (signed agreement) |

### C. Indodax — Trade API v2 (ref 001)

Base `https://api.indodax.com`. Headers `Accept: application/json`, `X-APIKEY`,
`Sign` = HMAC-SHA256(secret, query-string `+` body-on-POST); `Content-Type:
application/x-www-form-urlencoded` on POST. `timestamp` (ms) or `nonce`
required; `recvWindow` default 5000. Errors `{"code":-N,"msg":...}`
(`-1002` bad creds, `-1021` timestamp, `-1022` sign/nonce, `-2014` missing key,
`-2015` access denied / wrong key version, `-1003` rate limit, `-1121` symbol).
**IP allowlist mandatory** for trade & withdraw scopes. Rate limits 300 req/min
(order/account/history), 50 req/min (capital), plus 20 req/s per user per pair
on order create/cancel.

| # | Method + path | Key params |
|---|---|---|
| 1 | `POST /api/v2/order` | `symbol`*, `side`* (BUY/SELL), `type`* (LIMIT/MARKET), `price` (LIMIT), `quantity` (all except MARKET BUY), `quoteOrderQty` (MARKET BUY, IDR), `newClientOrderId`, `timeInForce` (GTC/MOC), `selfTradePreventionMode` (EXPIRE_TAKER/EXPIRE_MAKER/EXPIRE_BOTH) |
| 2 | `DELETE /api/v2/order` | order id / client id + `symbol` |
| 3 | `GET /api/v2/openOrders` | `symbol` |
| 4 | `GET /api/v2/order` | order id / client id + `symbol` |
| 5 | `GET /api/v2/account` | `omitZeroBalances` — returns `canTrade`, `canWithdraw`, `accountType`, `balances[]{asset,free,locked}`, `uid` |
| 6 | `GET /api/v2/order/histories` | pagination / time range |
| 7 | `GET /api/v2/myTrades` | `symbol`*, `limit`, time range |
| 8 | `GET /api/v2/capital/withdraw/history` | `coin`, `startTime`, `endTime`, `limit` (10–1000), `WithdrawStatus`; ≤ 90-day range |
| 9 | `GET /api/v2/capital/deposit/hisrec` | coin + time range |
| 10 | `GET /api/v2/capital/deposit/address/list` | — |
| 11 | `GET /api/v2/fiat/orders` | fiat deposit+withdrawal history |
| 12 | `POST /api/v2/capital/withdraw/apply` | `asset`, `address`/`username` (whitelisted), `amount`, `network` |
| 13 | `POST /api/v2/fiat/withdraw` | IDR withdrawal to KYC-matched bank |

### D. Tokocrypto — v1 (`/open/v1/*`) (ref 002)

Base `https://www.tokocrypto.com`. Header `X-MBX-APIKEY`; SIGNED endpoints
append `&signature=<HMAC-SHA256(query-or-body, secret)>`; `timestamp` (ms)
required, `recvWindow` ≤ 60000. Envelope `{"code":0,"msg":"","data":...}`,
`code==0` = success. Weight-based IP limits (`X-MBX-USED-WEIGHT-*`), 429/418 on
breach. Enum ints: `side` 0=BUY 1=SELL; `type` 1=LIMIT 2=MARKET 3=STOP_LOSS
4=STOP_LOSS_LIMIT 5=TAKE_PROFIT 6=TAKE_PROFIT_LIMIT 7=LIMIT_MAKER;
`timeInForce` 1=GTC 2=IOC 3=FOK 4=GTX.

| # | Method + path | Security | Key params |
|---|---|---|---|
| 1 | `GET /open/v1/common/time` | NONE | — |
| 2 | `GET /open/v1/common/symbols` | NONE | — |
| 3 | `GET /open/v1/market/depth` | NONE | `symbol`*, `limit` (≤ 5000) |
| 4 | `GET /open/v1/market/trades` | NONE | `symbol`*, `fromId`, `limit` (≤ 1000) |
| 5 | `GET /open/v1/market/agg-trades` | NONE | `symbol`*, `fromId`, `startTime`, `endTime`, `limit` |
| 6 | `GET /open/v1/market/klines` | NONE | `symbol`*, `interval`* (1m…1M), `startTime`, `endTime`, `limit` |
| 6b | `GET /api/v3/executionRules` (on `www.tokocrypto.site`) | NONE | `symbol` / `symbols` / `symbolStatus` — price-range + STP rules; Binance-standard host, so symbol is `BTCUSDT` not `BTC_USDT` |
| 7 | `POST /open/v1/orders` | SIGNED | `symbol`*, `side`*, `type`*, `quantity`, `quoteOrderQty`, `price`, `stopPrice`, `icebergQty`, `clientId`, `timeInForce`, `selfTradePreventionMode` |
| 8 | `GET /open/v1/orders/detail` | SIGNED | `orderId`* / `clientId` |
| 9 | `POST /open/v1/orders/cancel` | SIGNED | `orderId` / `clientId` |
| 10 | `GET /open/v1/orders` | SIGNED | `symbol`*, `type` (1/2/-1), `side`, `startTime`, `endTime`, `fromId`, `direct`, `limit` |
| 11 | `POST /open/v1/orders/oco` | SIGNED | `symbol`*, `side`*, `quantity`*, `price`*, `stopPrice`*, `stopLimitPrice`*, `*ClientId` |
| 12 | `GET /open/v1/orders/trades` | SIGNED | `symbol`*, `orderId`, `startTime`, `endTime`, `fromId`, `direct`, `limit` |
| 13 | `GET /open/v1/account/spot` | SIGNED | — |
| 14 | `GET /open/v1/account/spot/asset` | SIGNED | `asset`* |
| 15 | `POST /open/v1/withdraws` | SIGNED | `asset`*, `address`*, `amount`*, `network`, `addressTag`, `clientId` |
| 16 | `GET /open/v1/withdraws` | SIGNED | `asset`, `status`, `fromId`, `startTime`, `endTime` |
| 17 | `GET /open/v1/deposits` | SIGNED | `asset`, `status` (0/1), `fromId`, `startTime`, `endTime` |
| 18 | `GET /open/v1/deposits/address` | SIGNED | `asset`*, `network`* |
| 19 | `POST /open/v1/user-listen-token` | SIGNED | `validity` (ms, ≤ 24 h) |

Deprecated: `POST/PUT/DELETE /open/v1/user-data-stream` (decommissioned
2026-04-30).

### E. WebSocket surfaces (contracts + baseline infra added 2026-09-07)

REST is the primary surface; these WS streams are also wired as
`contracts/api/**/*_ws.py` + `infrastructure/api/**` with a shared
reconnecting client (`shared/websocket.py`).

| Surface | URL | Auth | Channels / streams |
|---|---|---|---|
| Indodax market | `wss://ws3.indodax.com/ws/` | static public token; Centrifugo (`method` 1=subscribe, 7=ping) | `chart:tick-<pair>`, `market:summary-24h`, `market:trade-activity-<pair>`, `market:order-book-<pair>` |
| Indodax private | `wss://pws.indodax.com/ws/` | `POST /api/private_ws/v1/generate_token` (HMAC-SHA512) → `{connToken, channel}`, then `connect`+`subscribe` | account order-update events |
| Tokocrypto market | `wss://stream-cloud.tokocrypto.site/stream` | none; Binance-style `{"method":"SUBSCRIBE","params":[…]}` | `<sym>@aggTrade`, `@trade`, `@kline_<iv>`, `@miniTicker`, `@depth`, `@depth<levels>` |
| Tokocrypto user | `wss://stream-cloud.tokocrypto.site/stream?streams=<token>` | listen token from `POST /open/v1/user-listen-token` | `outboundAccountPosition`, `executionReport` |

All four verified to connect + hand-shake against production on 2026-09-07
(Tokocrypto aggTrade messages received live; Indodax auth+subscribe acks
received).

### F. Mapping to code

`backend/src/tarakdingdung/domain/contracts/api/` — one ABC per surface/concern:

- `indodax/v1/public.py` → `IndodaxV1PublicApi` (§A)
- `indodax/v1/private.py` → `IndodaxV1PrivateApi` (§B)
- `indodax/v2/trade.py` → `IndodaxV2TradeApi` (§C)
- `tokocrypto/v1/market.py` → `TokocryptoV1MarketApi` (§D 1–6, 6b)
- `tokocrypto/v1/trade.py` → `TokocryptoV1TradeApi` (§D 7–14)
- `tokocrypto/v1/wallet.py` → `TokocryptoV1WalletApi` (§D 15–18)
- `tokocrypto/v1/stream.py` → `TokocryptoV1StreamApi` (§D 19, listen-token REST)
- `indodax/v1/market_ws.py` → `IndodaxMarketWebSocket` (§E)
- `indodax/v1/private_ws.py` → `IndodaxPrivateWebSocket` (§E)
- `tokocrypto/v1/market_ws.py` → `TokocryptoMarketWebSocket` (§E)
- `tokocrypto/v1/user_ws.py` → `TokocryptoUserWebSocket` (§E)

`backend/src/tarakdingdung/infrastructure/api/` — `httpx.AsyncClient`-backed
REST impls (`Http*` prefix) and `websockets`-backed WS impls (`Ws*` prefix),
with `shared/signing.py` (HMAC helpers), `shared/rest.py` (request +
JSON-decode + `DomainError` mapping) and `shared/websocket.py`
(`ReconnectingWebSocket`: capped-backoff reconnect + re-handshake). Each REST
impl unwraps its success envelope (`return` / `data`) and raises `DomainError`
on the exchange's error shape.

## Open questions / gaps

- **Tokocrypto enum encoding:** the apidocs WebFetch reports `side`/`type`/
  `timeInForce` as **integers**; some community clients send the string names.
  Verify against the live parameter tables (and a testnet order) before trusting
  the int codes.
- **Tokocrypto market-data base:** `/open/v1/market/*` vs the newer
  `www.tokocrypto.site/api/v3/*` (Type-1) / `cloudme-toko.2meta.app/api/v1/*`
  (Type-3). `ccxt` still calls `/open/v1/market/*`; confirm it is not
  soft-deprecated.
- **Indodax v2 request signing** — **confirmed** 2026-09-07: signing the exact
  urlencoded param string (`timestamp=…&recvWindow=…&…`) as the GET query, with
  `Sign` header + `X-APIKEY`, authenticates (`GET /api/v2/account` →
  `canTrade=true, canWithdraw=false`). POST body signing still unverified (no
  order placed).
- **Tokocrypto `/open/v1/common/time`** — **confirmed** 2026-09-07: returns
  `{"code":0,"msg":"Success","data":null,"timestamp":<ms>}` — the epoch is the
  top-level `timestamp`, not inside `data`; the client returns this envelope
  unwrapped. Other market endpoints (`depth` → `{lastUpdateId,bids,asks}`) do
  carry their payload in `data`.
- **Clock skew:** Indodax v2 rejected one request with `-1021` ("timestamp
  outside recvWindow") on a residential NTP clock, then succeeded on retry. A
  production client should sync a server-time offset rather than trust the local
  clock; the current `Http*` clients accept an injectable `now_ms` but do not
  auto-sync yet.
- **Indodax v2 remaining response schemas:** only `GET /api/v2/account` and
  `POST /api/v2/order` sample bodies were captured; the history/capital
  endpoints' exact field names still need a full capture from
  `INDODAX-TradeAPI-2.md`.
- **WebSocket surfaces** (Indodax market + private WS, Tokocrypto streams) are
  out of scope here — REST only.
- **Rate-limit / weight handling** and retry/backoff policy for each venue is
  not settled (feeds into the adapter's `shared/rest.py`).

---

## References used

- `references/001_Indodax_Official_API_Documentation.md`
- `references/002_Tokocrypto_API_Documentation.md`
