# 003 — Tokocrypto signed `/api/v3` calls rejected with `-2015`

- **Severity:** high
- **Status:** open
- **Detected:** 2026-09-07, signed probe + in-container portfolio sync
- **Area:** operational / credentials, not a code bug in the v3 client itself
- **Narrowed 2026-09-07:** IP allowlist and key permissions both ruled out
  (see below) — the key is almost certainly not valid for the Binance-standard
  `.site` host.

## Symptom

Every **signed** Tokocrypto v3 request fails:

```
GET /api/v3/account
-> DomainError [FORBIDDEN] tokocrypto.v3 [-2015]:
   "Invalid API-key, IP, or permissions for action."
```

Consequences observed in the running system:

- **Portfolio sync** logs `WARN trading/portfolio/Sync "failed to read balances"`
  for `TOKOCRYPTO` and marks the venue `unreachable`. It degrades gracefully —
  the portfolio is still built from Indodax — but any Tokocrypto holdings are
  invisible.
- Any strategy with a Tokocrypto symbol in its universe cannot sync balances,
  and (once wired for live) could not place or reconcile orders.
- The Tokocrypto **live order path remains completely unexercised** against
  real order traffic — the v3 migration's own known gap.

## What it is / isn't

`-2015` is returned by Binance-family APIs **before** signature verification
(a bad signature is `-1022`, a missing/late timestamp is `-1021`, a badly
*formatted* key is `-2014`). Reaching `-2015` means the request was well-formed
and signed; the rejection is that this **API-key string is not one the host
will act on** — because of the key itself, its IP allowlist, or its
permissions. So this is not a signing bug in `TokocryptoV3Transport`.

### Ruled out (2026-09-07)

- **IP allowlist.** The keys are allowlisted to `118.99.94.221`, and the
  machine that ran the probe *is* on `118.99.94.221` (confirmed via
  `api.ipify.org` / `ifconfig.me` / `icanhazip.com`, all agreeing). Not an IP
  problem.
- **Permissions.** Confirmed: `canTrade=1`, `canWithdraw=1`, `canDeposit=1`.
- **Clock drift.** Container-vs-venue skew measured at **10 ms** (`recvWindow`
  is 5000 ms). Not a drift problem.

### Confirmed root cause (2026-09-07)

A signed `GET /open/v1/account/spot` against **`www.tokocrypto.com`** with the
same `.env` credentials **succeeds**: `auth OK`, 653 assets (1 non-zero),
`makerCommission`/`takerCommission` `0.00150000`, `canTrade=1`.

So the key is **fully valid and trade-enabled — but only on Tokocrypto's
legacy `/open/v1` system**. It is not recognised on the Binance-standard
`www.tokocrypto.site` `/api/v3` host, which is what this session's migration
pointed the signed client at. Diagnosis 2a is confirmed; the v3 migration's
"trade + account on `/api/v3`" scope was wrong for this account.

> **Security note:** this key has **withdraw enabled** (`canWithdraw=1`). The
> intended scope was view + trade only. Regenerate it withdraw-disabled
> regardless of which path below is taken.

### Therefore

With IP and permissions eliminated, `-2015` on a well-formed signed request
points at the **key not being valid for this host / API system**. Tokocrypto
runs two signed API systems:

| System | Host | Endpoints | Key |
|---|---|---|---|
| Legacy "TokoCrypto" | `www.tokocrypto.com` | `/open/v1/*` | the key we have was issued here |
| Binance-standard | `www.tokocrypto.site` | `/api/v3/*` | provisioned separately on Binance-powered accounts |

The v3 client (this session's migration) talks to `www.tokocrypto.site`
`/api/v3/*`. If the account's key only exists in the legacy system, every
signed `/api/v3` call is `-2015` even with a perfect IP and permissions —
which is exactly the symptom.

## What to do

**Step 1 done** — the legacy-host probe confirmed the key works on
`/open/v1`. Two viable paths from here; pick one.

### Path A — get a Binance-standard API key (best if the account supports it)

In the Tokocrypto app / website API management page, look for a **separate
"Binance API" / "Standard API"** key section (distinct from the one the
current key came from).

- **If it exists:** generate a key there (read + spot trade, IP `118.99.94.221`,
  **no withdraw**), put it in `.env` as `TRDD_BE_TOKOCRYPTO_API_KEY` /
  `_SECRET_KEY`, re-run the `/api/v3/account` probe. The v3 code is already
  done — nothing else to change.
- **If it does not exist:** this account is legacy-only for signed calls →
  take Path B.

### Path B — scoped partial revert (works with the key you already have)

Split the Tokocrypto wiring by what each host actually serves:

| Concern | Host | Client |
|---|---|---|
| Market data (candles / depth / rules) | `www.tokocrypto.site` `/api/v3/*` | `HttpTokocryptoV3MarketApi` — **keep** (this is what fixed the dead-klines bug) |
| Account balances + signed trading | `www.tokocrypto.com` `/open/v1/*` | `HttpTokocryptoV1TradeApi` — **restore** |

Work involved (all `/open/v1` clients were deliberately kept in the tree):

- restore `venue/tokocrypto/account.py` and `execution/live/tokocrypto.py` to
  their `/open/v1` forms (git: state at `d18ca62`, before commits `acf5813` /
  `462d09f`) — int enums, `{code,msg,data}` envelope, `BTC_USDT` symbols;
- rewire `composition/main/exchanges.py`: `TokocryptoAccountSource` and
  `TokocryptoLiveExecutor` take `HttpTokocryptoV1TradeApi`,
  `TokocryptoMarketDataSource` keeps `HttpTokocryptoV3MarketApi`;
- the v3 `tokocrypto/v3/trade.py` contract + client stay in the tree, unused
  (same as `/open/v1` is today).

~3 files. This is the fix if Path A has no key to offer.

### Then (either path)

Regenerate the API key **withdraw-disabled**, then place one supervised,
minimum-size live order to finally exercise the signed trading path against
the real API.

## Note

Public Tokocrypto market data (`/api/v3/klines`, `/depth`, `/ticker/price`,
`/exchangeInfo`) works unauthenticated — verified earlier. Only the signed
surface is blocked, so market-data collection for Tokocrypto symbols is not
affected by this item.
