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
- **Permissions.** The account owner confirms the key has **read and trade**
  enabled.

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

## Next steps (for the operator)

1. **Prove the key is alive on the legacy host.** Run a signed
   `GET /open/v1/account/spot` against `www.tokocrypto.com` with the same
   `.env` credentials (the repo still has `HttpTokocryptoV1TradeApi`, unwired).
   - **Balances come back** → the key is valid but scoped to `/open/v1` only.
     The account is not on the Binance-standard signed API. Go to step 2a.
   - **Also `-2015` / an auth error** → the key/secret pair itself is
     wrong (revoked, typo, or the *secret* was mangled when pasted into
     `.env` — a wrong secret usually gives `-1022`, a wrong key `-2015`).
     Regenerate the key in the Tokocrypto dashboard, re-paste both halves
     with no surrounding whitespace, retry.
2. Depending on step 1:
   - **2a — key works only on `/open/v1`:** check the Tokocrypto API
     management page for a separate "Binance API" / "Standard API" key
     section. If one exists, generate a key there and use it for the v3
     client. If it does **not** exist, this account cannot use the
     Binance-standard signed API at all → the pragmatic fix is a **scoped
     partial revert**: keep Tokocrypto *market data* on `.site/api/v3` (works
     unauthenticated) but move Tokocrypto *account + trading* back onto the
     signed `/open/v1` client. ~1 file of composition rewiring; the
     `/open/v1` clients were deliberately kept in the tree for this.
   - **2b — a Binance-standard key is obtained:** put it in `.env`
     (`TRDD_BE_TOKOCRYPTO_API_KEY` / `_SECRET_KEY`), re-run the probe.
3. Once signed reads work on whichever host: place one supervised,
   minimum-size live order to finally exercise `TokocryptoLiveExecutor`
   against the real API.

### Clock drift (cheap to rule out while you're here)

`-2015` is not the drift code, but if step 1 is inconclusive, compare the
container clock to the venue: `GET /api/v3/time` vs `date +%s%3N`. A skew
beyond `recvWindow` (5000 ms) would normally surface as `-1021`, not `-2015`.

## Note

Public Tokocrypto market data (`/api/v3/klines`, `/depth`, `/ticker/price`,
`/exchangeInfo`) works unauthenticated — verified earlier. Only the signed
surface is blocked, so market-data collection for Tokocrypto symbols is not
affected by this item.
