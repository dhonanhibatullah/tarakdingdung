# Tokocrypto v3 API Migration — Design

- **Date:** 2026-09-07
- **Status:** approved
- **Scope:** a new `tokocrypto/v3` (Binance-standard) API contract + infrastructure
  layer, the rewiring of the three Tokocrypto venue adapters onto it, and a
  widening of the `Executor` reconcile signature that the rewiring forces
- **Sources:** live probing of `https://www.tokocrypto.site` on 2026-09-07;
  `docs/superpowers/specs/2026-09-07-trading-usecases-design.md`

## Problem

Three defects were found by probing the Tokocrypto market path against the real
exchange:

1. **Candles are permanently empty.** `TokocryptoMarketDataSource.fetch_candles` calls
   `/open/v1/market/klines`, which returns `{"data":{"list":[]}}` for every
   symbol and every parameter set — the endpoint is dead. No candles means the
   feature extractor produces nothing, the strategy targets nothing, and
   Tokocrypto cannot trade at all. `fetch_price` is collateral damage: it is
   implemented as "last 1m kline close".
2. **The live order path has never run against the real API.** The signing,
   the integer enum encoding and the ack parsing in `TokocryptoLiveExecutor`
   and `HttpTokocryptoV1TradeApi` come from documentation, not traffic.
3. **Fills are never reported.** `TokocryptoLiveExecutor.submit` always returns
   `fills=()`; position tracking depends entirely on the 5-minute portfolio
   sync polling balances.

The `/open/v1` REST surface is the wrong foundation to fix these on. The
endpoints that actually work are the Binance-standard `/api/v3/*` routes on the
`.site` host — already used by the existing `execution_rules` method. That host
also solves defect 3 for free: `POST /api/v3/order` with
`newOrderRespType=FULL` returns a `fills[]` array.

## Decisions

**A dedicated `v3` API layer, parallel to `v1`, not a patch of `v1`.** The two
speak different dialects: `v1` unwraps a `{code,msg,data}` envelope and uses
integer enum codes; `v3` returns raw JSON, uses string enums (`"BUY"`,
`"LIMIT"`, `"GTC"`), and puts errors in a `{"code":-1121,"msg":...}` body
alongside a 4xx status. Mixing both into one client would make every method
branch on which dialect it is speaking. A separate contract keeps each one
coherent.

**Scope is market + trade + account. WebSockets stay on `v1`.** The three REST
adapters (`market`, `account`, executor) move to `v3`. The market and user
WebSocket clients are not wired into the engine today, so migrating them is
speculative work; they keep their `/open/v1` transport untouched.

**The old `/open/v1` market/trade code stays in the tree, unwired.** The
`stream`, `wallet` and `*_ws` contracts still reference that transport, and a
dead endpoint today may be revived. Composition simply stops constructing the
`v1` market/trade clients. Deleting them is a separate later decision.

**`Executor.read_by_client_order_id` gains an optional `symbol`.** The `v1`
executor could reconcile from a client id alone
(`/open/v1/orders/detail?clientId=`). Binance `GET /api/v3/order` requires a
symbol. Rather than let the Tokocrypto reconcile path regress to the Indodax
"raise `UNIMPLEMENTED`" level, the contract widens to
`read_by_client_order_id(client_order_id, *, symbol: Symbol | None = None)`.
`TradingEngineUsecase._reconcile` already holds the `PlannedOrder` for each
unreconciled entry, so it passes `order.symbol` through. Paper ignores it;
Indodax can now use it too, though wiring Indodax's is out of scope here.

**A fill whose commission is not in the quote currency records zero fee.**
Binance `fills[].commission` may be charged in a third asset (BNB, a native
token). `Fill.fee` is a single unlabelled `Decimal` that flows into a
quote-denominated ledger. Putting a BNB number there is a silent accounting
error. When `commissionAsset != symbol.quote`, `fee` is `Decimal(0)` and the
executor logs a warning. Recording fees in a foreign commission asset
accurately is a known gap, noted below.

## New contracts — `domain/contracts/api/tokocrypto/v3/`

### `market.py` — `TokocryptoV3MarketApi` (unauthenticated)

| Method | Endpoint | Returns |
|---|---|---|
| `server_time()` | `GET /api/v3/time` | `{"serverTime": int}` |
| `exchange_info(*, symbol=None, symbols=None)` | `GET /api/v3/exchangeInfo` | `{"symbols": [...]}` |
| `klines(*, symbol, interval, start_time=None, end_time=None, limit=None)` | `GET /api/v3/klines` | `list[list]` (Binance kline arrays) |
| `depth(*, symbol, limit=None)` | `GET /api/v3/depth` | `{"bids": [[p,q]], "asks": [[p,q]]}` |
| `ticker_price(*, symbol)` | `GET /api/v3/ticker/price` | `{"symbol": str, "price": str}` |

`symbol` is the joined-upper form (`BTCIDR`), via `venue.symbols.joined_upper`.

### `trade.py` — `TokocryptoV3TradeApi` (signed)

| Method | Endpoint |
|---|---|
| `create_order(*, symbol, side, type, quantity=None, quote_order_qty=None, price=None, time_in_force=None, new_client_order_id=None, new_order_resp_type="FULL")` | `POST /api/v3/order` |
| `query_order(*, symbol, order_id=None, orig_client_order_id=None)` | `GET /api/v3/order` |
| `cancel_order(*, symbol, order_id=None, orig_client_order_id=None)` | `DELETE /api/v3/order` |
| `open_orders(*, symbol=None)` | `GET /api/v3/openOrders` |
| `my_trades(*, symbol, order_id=None, start_time=None, end_time=None, from_id=None, limit=None)` | `GET /api/v3/myTrades` |
| `account()` | `GET /api/v3/account` |

`side`, `type`, `time_in_force` are the exchange's **string** values. Client
orders are identified by `newClientOrderId` on create and `origClientOrderId`
on query/cancel.

## New infrastructure — `infrastructure/api/tokocrypto/v3/`

### `transport.py` — `TokocryptoV3Transport`

- `V3_BASE_URL = "https://www.tokocrypto.site"`, constructor-overridable.
- `public_get(path, **params)` — drops `None`s via `clean_params`, sends
  `X-MBX-APIKEY` when a key is configured, returns `response.json()` verbatim.
  No unwrap.
- `signed_request(method, path, **params)` — prepends `timestamp` and
  `recvWindow`, signs the URL-encoded query string with
  `hmac_sha256(secret, query)`, appends `&signature=<hex>`, sends the whole
  thing as the query string for every verb (Binance accepts POST parameters in
  the query), with the `X-MBX-APIKEY` header.
- Reuses `hmac_sha256` from `infrastructure/api/shared/signing.py`.

### `RestClient` change — `infrastructure/api/shared/rest.py`

`RestClient.request` currently raises on any `status >= 400` using
`response.text[:200]`, before the caller can read the JSON error body. Add an
optional `error_mapper: Callable[[int, str], DomainError] | None` parameter
(constructor-level). When set and the response is a 4xx/5xx, the mapper is
called with `(status_code, response.text)` and its `DomainError` is raised.
Default `None` preserves today's behaviour exactly — Indodax and `v1` are
untouched.

### `errors.py` — `map_v3_error(status: int, body: str) -> DomainError`

Parses `body` as `{"code": int, "msg": str}`. Reuses the Binance error-code
table already present in `infrastructure/api/tokocrypto/errors.py` (`-1021`,
`-1121`, `-2010`, `-2011`, `-2013`, `-2014`, `-2015`, …), mapping to
`ErrorType`. An unparseable body or unknown code falls back to the HTTP-status
mapping (`401/403 → UNAUTHORIZED`, `429 → RATE_LIMITED`, else `UPSTREAM`).

### `market.py` / `trade.py`

`HttpTokocryptoV3MarketApi` and `HttpTokocryptoV3TradeApi` — one thin method
per contract method, delegating to the transport.

## Venue adapter rewiring

### `infrastructure/venue/tokocrypto/market.py`

- Constructor takes `TokocryptoV3MarketApi`.
- `fetch_candles` → `market.klines(symbol=joined_upper(symbol), interval=…,
  limit=…)`; existing `_candle` array parser unchanged.
- `fetch_book` → `market.depth(symbol=joined_upper(symbol), limit=…)`;
  existing `_levels` parser unchanged.
- `fetch_price` → `market.ticker_price(symbol=joined_upper(symbol))` →
  `to_decimal(payload["price"])`. The "last 1m kline" workaround is deleted.
- `fetch_rules` → `market.exchange_info()`; for each `symbols[]` entry walk
  `filters` for `PRICE_FILTER.tickSize`, `LOT_SIZE.stepSize`, and
  `NOTIONAL.minNotional` — accepting the legacy `MIN_NOTIONAL.minNotional`
  spelling as a fallback. `_MAKER_FEE` / `_TAKER_FEE` stay hard-coded at
  `0.0010`; `v3` exposes no per-account fee tier either.
- Symbol form throughout the file changes from `underscored` to `joined_upper`.

### `infrastructure/venue/tokocrypto/account.py`

- Constructor takes `TokocryptoV3TradeApi`.
- `fetch_balances` → `trade.account()` → iterate `balances[]`
  (`{asset, free, locked}`), keep `Decimal(free) > 0`.

### `infrastructure/execution/live/tokocrypto.py`

- Constructor takes `TokocryptoV3TradeApi`.
- Enum maps become string-valued: `Side.BUY → "BUY"`, `OrderType.LIMIT →
  "LIMIT"`, `OrderType.MARKET → "MARKET"`, `OrderType.LIMIT_MAKER →
  "LIMIT_MAKER"`, `TimeInForce.GTC → "GTC"` etc.
- `_create` → `trade.create_order(symbol=joined_upper(order.symbol),
  side=…, type=…, quantity=str(order.quantity),
  price=str(order.price) if order.price is not None else None,
  time_in_force=…, new_client_order_id=client_order_id,
  new_order_resp_type="FULL")`.
- Ack: `venue_order_id = str(payload["orderId"])`.
- **Fills:** for each entry in `payload.get("fills", [])`, build
  `Fill(symbol=order.symbol, side=order.side, quantity=to_decimal(qty),
  price=to_decimal(price), fee=_fee(commission, commission_asset,
  order.symbol.quote), timestamp=payload["transactTime"])`. `_fee` returns
  `to_decimal(commission)` when `commission_asset == symbol.quote`, else
  `Decimal(0)` with a warn log. An empty or absent `fills` array yields no
  `Fill`s and the order still lands in `accepted` (a resting limit order that
  did not cross) — the portfolio sync reconciles it later.
- `cancel_all` → `trade.open_orders(symbol=joined_upper(symbol))`; for each
  resting entry, `trade.cancel_order(symbol=…,
  orig_client_order_id=entry["clientOrderId"])`.
- `read_by_client_order_id(client_order_id, *, symbol=None)` → when `symbol`
  is `None`, raise `DomainError(UNIMPLEMENTED)` (the engine always passes one);
  otherwise `trade.query_order(symbol=joined_upper(symbol),
  orig_client_order_id=client_order_id)`. A `NOT_FOUND` means the venue never
  saw the order — return an empty `ExecutionResult`. A terminal status maps to
  `accepted`/`rejected` with any `fills` from a follow-up `my_trades` call kept
  out of scope for v1 (documented gap).

## Contract change — `Executor.read_by_client_order_id`

```python
async def read_by_client_order_id(
    self, client_order_id: str, *, symbol: Symbol | None = None
) -> ExecutionResult: ...
```

Call sites to update:

- `application/trading/engine/usecase.py::_reconcile` — pass
  `symbol=order.symbol` (the `PlannedOrder` from `read_unreconciled`).
- `infrastructure/execution/paper/executor.py` — accept and ignore `symbol`.
- `infrastructure/execution/live/router.py::RoutingExecutor` — still raises
  (its job is to route a submission, not a lookup); signature updated.
- `infrastructure/execution/live/indodax.py` — signature updated; body still
  raises `UNIMPLEMENTED` (Indodax reconciles through the journal). Wiring
  Indodax's symbol-based lookup is explicitly out of scope.

## Composition + configuration

### `config/settings.py`

Add `tokocrypto_v3_base_url: str = "https://www.tokocrypto.site"`
(`TRDD_BE_TOKOCRYPTO_V3_BASE_URL`), so a different host or a future testnet is
an env change.

### `composition/main/exchanges.py`

```python
tokocrypto_v3_market = HttpTokocryptoV3MarketApi(
    http, base_url=settings.tokocrypto_v3_base_url)
tokocrypto_v3_trade = HttpTokocryptoV3TradeApi(
    http, api_key=settings.tokocrypto_api_key,
    secret_key=settings.tokocrypto_secret_key,
    base_url=settings.tokocrypto_v3_base_url)
```

Pass `tokocrypto_v3_market` to `TokocryptoMarketDataSource`,
`tokocrypto_v3_trade` to `TokocryptoAccountSource` and
`TokocryptoLiveExecutor`. The `HttpTokocryptoV1MarketApi` /
`HttpTokocryptoV1TradeApi` constructions are removed from this file. The `v1`
`execution_rules` method and its `.site` sub-transport become dead with the
`v1` market client; they are left in the file per the "stays unwired" decision.

## Testing

- **`infrastructure/api/tokocrypto/v3/` unit tests** — a stub `httpx`
  transport returns the real bodies captured on 2026-09-07: a klines array, a
  depth object, an `exchangeInfo` with `PRICE_FILTER`/`LOT_SIZE`/`NOTIONAL`
  filters, an order `FULL` response carrying `fills`, and a
  `{"code":-1121,"msg":"..."}` error body. Assert the transport signs the
  query, sends `X-MBX-APIKEY`, and that `map_v3_error` turns `-1121` into
  `BAD_ARGS` and `-2010` into `BAD_STATE`.
- **`RestClient` test** — with an `error_mapper` set, a 400 carrying a JSON
  body raises the mapper's `DomainError`; with no mapper, behaviour is
  byte-identical to today.
- **Adapter tests** — `fetch_rules` parses Binance filters into `SymbolRules`;
  `fetch_price` reads `ticker_price`; the executor maps a `FULL` response to
  `Fill`s; a `commissionAsset` that is not the quote currency yields
  `fee == Decimal(0)` and a warn log; an empty `fills` array yields an
  `accepted` order with no fills.
- **`Executor` conformance suite** — extended so the `symbol` keyword is
  exercised across paper and both live executors; the "every order appears
  exactly once" invariant is unchanged.
- **Issue #2 auth probe** — a throwaway script in the scratchpad (not
  committed) performs a signed `GET /api/v3/account` with the real keys and
  prints only `"auth OK — N non-zero balances"`. No amounts, no key material.
  It proves credentials + signing end-to-end. The first real order is placed
  by the operator, supervised, at minimum size.

## Out of scope

- WebSocket stream migration (`market_ws`, `user_ws`, `stream` stay on `v1`).
- Deleting the `/open/v1` market/trade code.
- OCO orders on `v3`.
- Indodax changes of any kind, including its symbol-based reconcile lookup.
- Recording fees denominated in a non-quote commission asset.
- Per-account fee-tier discovery.
- A Tokocrypto testnet integration.

## Known gaps after this change

- **Foreign-asset commissions are dropped to zero.** Acceptable only while the
  account holds no fee-discount token balance; revisit if BNB-paid fees start
  appearing in `my_trades`.
- **`read_by_client_order_id` terminal-status fills.** The v3 executor's
  reconcile path returns state without back-filling fills from `my_trades`; the
  portfolio sync remains the backstop.
- **The live order path is still unproven against real traffic.** The auth
  probe covers signing and credentials, not order semantics.
