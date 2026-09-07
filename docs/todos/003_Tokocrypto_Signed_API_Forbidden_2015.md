# 003 — Tokocrypto signed `/api/v3` calls rejected with `-2015`

- **Severity:** high
- **Status:** open
- **Detected:** 2026-09-07, signed probe from the dev host + in-container portfolio sync
- **Area:** operational / credentials, not a code bug in the v3 client itself

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
(a bad signature is `-1022`, a missing/late timestamp is `-1021`). Reaching
`-2015` means the request was well-formed and signed; the rejection is about
the **key, its IP allowlist, or its permissions**. So this is not a signing
bug in `TokocryptoV3Transport`.

Most likely causes, in order:

1. **IP allowlist.** The keys are pinned to a deploy host; the probe ran from
   a different machine. Re-run from the allowlisted host.
2. **Key not enabled for the Binance-standard `.site` surface.** The existing
   key was issued for `/open/v1` on `www.tokocrypto.com`. The v3 client talks
   to `www.tokocrypto.site` (`/api/v3/*`), which on some Tokocrypto accounts
   needs a separately-issued "Type-1" key. Confirm the key type in the
   Tokocrypto dashboard; re-issue with `/api/v3` (spot) access if needed.
3. Key lacks the "read" / "spot trade" permission scope.

## Next steps

- [ ] Re-run the signed probe (`GET /api/v3/account`) from the allowlisted
      deploy host. If it succeeds, this is purely an environment issue —
      close it and note the deploy constraint in the runbook.
- [ ] If it still returns `-2015` from the deploy host: re-issue the
      Tokocrypto API key with `/api/v3` spot access and update `.env`
      (`TRDD_BE_TOKOCRYPTO_API_KEY` / `_SECRET_KEY`).
- [ ] Once signed reads work: place one supervised, minimum-size live order to
      finally exercise `TokocryptoLiveExecutor.submit` / `cancel_all` /
      `read_by_client_order_id` against the real API.

## Note

Public Tokocrypto market data (`/api/v3/klines`, `/depth`, `/ticker/price`,
`/exchangeInfo`) works unauthenticated — verified earlier. Only the signed
surface is blocked, so market-data collection for Tokocrypto symbols is not
affected by this item.
