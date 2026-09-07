# Indodax & Tokocrypto Have No Futures / Perpetual Trading API (2026-09)

- **Source URL:**
  - https://www.tokocrypto.com/apidocs/ (section list)
  - https://github.com/ccxt/ccxt/blob/master/python/ccxt/tokocrypto.py
  - https://github.com/ccxt/ccxt/blob/master/python/ccxt/indodax.py
  - https://github.com/btcid/indodax-official-api-docs (repo-wide search)
  - https://help.indodax.com/hc/en-us/articles/38662836912153-What-is-Perpetual-Trading
  - https://help.indodax.com/hc/en-us/articles/38312003924505-What-are-Crypto-Futures
- **Author / Publisher:** Tokocrypto (PT Aset Kripto Internasional); Indodax (PT Indodax Nasional Indonesia); ccxt project
- **Published:** docs/libraries current as of retrieval
- **Retrieved:** 2026-09-07
- **Retrieved by:** conducting-research skill, research/base-trading-algo session
- **Type:** docs + library source + support articles
- **Topic tags:** futures, perpetual, derivatives, api-capability, indodax, tokocrypto, funding-rate, spot-only

---

## Raw content

### Question

Does Tokocrypto or Indodax expose a **perpetual-futures / derivatives API**
(needed for delta-neutral funding-rate arbitrage — see summary 002)?

### Tokocrypto — NO derivatives API (spot only)

- `https://www.tokocrypto.com/apidocs/` top-level sections: **Rest API**
  (General / Market Data / Account / Wallet), **WebSocket Streams**,
  **User Data Streams**, **FAQs** (Price-Range Execution, STP). WebFetch
  verdict: *"contains NO futures, perpetual, derivatives, or margin trading
  endpoints. The API is spot-trading only."* The only account endpoint is
  `GET /open/v1/account/spot`; symbol config shows `"marginTradingEnable": 0`.
- `ccxt/python/ccxt/tokocrypto.py` `has` block:
  `'spot': True, 'margin': True (conditional on marginTradingEnable), 'swap': False,
  'future': False, 'option': False, 'fetchFundingRate': False,
  'fetchFundingRateHistory': False`. The `fapi`/`dapi` strings in that file are
  inherited from the Binance base class ccxt's Tokocrypto class extends — they
  are **not** Tokocrypto endpoints.
- Trade-press: Tokocrypto "has announced a derivatives launch that is **pending
  regulatory approval**" — not live, no API.

### Indodax — NO derivatives API (spot only)

- `ccxt/python/ccxt/indodax.py` `has` block:
  `'spot': True, 'margin': False, 'swap': False, 'future': False,
  'option': False`, and every funding-rate / leverage / position method is
  `False`.
- Repo-wide `grep` of `btcid/indodax-official-api-docs` (`README`, `CHANGELOG`,
  `INDODAX-TradeAPI-2.md`, `Public-RestAPI.md`, `Private-RestAPI.md`, both
  WebSocket docs) for `future|perp|perpetual|derivativ|leverage|margin|contract|
  funding` → **no product endpoints**; the only "future" hit is the sentence
  about the legacy `/tapi` endpoint being decommissioned "in a future release".
- Indodax **does** publish consumer help articles "What is Perpetual Trading?"
  and "What are Crypto Futures?" (generic education / in-app product framing),
  and is registered with **CFX** (the national *Crypto Futures Exchange*
  clearing house). Neither implies a public API. The "Perpetual Trading" article
  describes the product concept (no expiry, periodic funding fees) but contains
  **no API/REST/WebSocket reference**; access appears to be app/web UI only.
  (The article page itself returned HTTP 403 to automated fetch; conclusion
  rests on the ccxt + official-docs evidence, which is unambiguous.)

### Consequence for tarakdingdung

- **Delta-neutral funding-rate arbitrage and cash-and-carry basis trades are not
  executable** on either venue via API — both legs would need a perp/future
  order book that neither API offers.
- A v1 automated strategy on these venues must be **spot-only**: spot trend /
  cross-sectional momentum, spot cross-exchange arbitrage (Tokocrypto vs
  Indodax), spot triangular arbitrage, or a spot market-making / mean-reversion
  rule.
- If perp execution becomes a hard requirement, it means an **offshore venue**
  (e.g. Binance USDⓈ-M — Tokocrypto's own parent, so tooling ports over) with
  the attendant KYC / funding / tax friction (parallels the equities finding in
  summary 001).

---

## Capture notes

Evidence is from library source (`ccxt`, authoritative on what is
API-reachable) and the exchanges' own docs. The Indodax consumer help article
could not be fetched (403) but is not load-bearing — ccxt `indodax.py` and the
official `btcid` repo are conclusive that no derivatives API exists. Re-check if
either exchange announces an API-accessible futures product.
