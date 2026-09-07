# Tokocrypto v3 API Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Tokocrypto market data, trading and account access onto the Binance-standard `/api/v3/*` API on `https://www.tokocrypto.site`, fixing the dead klines feed, reporting fills from order responses, and keeping the reconcile path working.

**Architecture:** A new `tokocrypto/v3` contract + infrastructure layer sits beside the existing `tokocrypto/v1`, not replacing it. `v3` speaks raw JSON with string enums and a `{"code","msg"}` error body; a small `error_mapper` hook on the shared `RestClient` lets it read that body. The three Tokocrypto venue adapters (`market`, `account`, executor) are repointed at `v3`. `Executor.read_by_client_order_id` gains an optional `symbol` because Binance order lookup requires one.

**Tech Stack:** Python 3.12, `httpx.AsyncClient` (+ `httpx.MockTransport` in tests), `pytest` with `asyncio_mode = "auto"`, HMAC-SHA256 signing (`infrastructure/api/shared/signing.py`).

**Spec:** `docs/superpowers/specs/2026-09-07-tokocrypto-v3-api-migration-design.md`

## Global Constraints

- `domain/` imports stdlib only — no `httpx`, no SQLAlchemy. The new `domain/contracts/api/tokocrypto/v3/` files are pure ABCs.
- Everything here is `async`. Tests are bare `async def test_…` (no `@pytest.mark.asyncio` needed; a few existing files still add it — either is fine).
- Exchange field values (prices, quantities, fees) are parsed with `to_decimal(value, label, venue="tokocrypto", default=…)` from `infrastructure/venue/shared.py`, which routes through `str` so a JSON float never reaches a `Decimal`.
- Money is `Decimal`; dimensionless stats are `float`. In this change every numeric touched is `Decimal`.
- Domain models are `@dataclass(frozen=True, slots=True)`. `Fill` lives in `tarakdingdung.domain.models.performance` (re-exported from `…models.execution`).
- `DomainError(message: str, type: ErrorType, source=None)`; read back as `err.type` and `err.message`.
- Symbol wire form for `v3` is joined-upper (`BTCIDR`, `BTCUSDT`) via `infrastructure/venue/symbols.py::joined_upper`. The `/open/v1` `underscored` form is not used by any `v3` call.
- Match surrounding style: ~92-column wrap, module docstring on new files explaining *why* the file exists.
- Run tests from `backend/`: `.venv/bin/python -m pytest <path> -q`.
- One commit per task, message prefix `feat(tokocrypto-v3):` or `refactor(tokocrypto-v3):` / `test(tokocrypto-v3):` as fits.
- The `/open/v1` Tokocrypto market/trade code is **left in the tree**, only unwired. Do not delete it.
- Indodax is out of scope. Do not change any `indodax` file except where a shared signature forces a one-line edit (Task 6).

---

### Task 1: `RestClient` gains an optional `error_mapper`

Binance returns the real failure reason as a JSON body (`{"code":-1121,"msg":"Invalid symbol."}`) *with* a 4xx status. `RestClient.request` currently raises on the status before the caller can read that body. Add an opt-in hook; default behaviour is byte-identical.

**Files:**
- Modify: `backend/src/tarakdingdung/infrastructure/api/shared/rest.py`
- Test: `backend/tests/infrastructure/api/test_shared.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `RestClient(client, *, base_url, tag, error_mapper: Callable[[int, str], DomainError] | None = None)`. When `error_mapper` is set and a response has `status_code >= 400`, `request` raises `error_mapper(status_code, response.text)` instead of its built-in status-map `DomainError`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/infrastructure/api/test_shared.py`:

```python
async def test_rest_client_uses_the_error_mapper_when_given_one():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(418, text='{"code":-1121,"msg":"Invalid symbol."}')

    def mapper(status: int, body: str) -> DomainError:
        assert status == 418 and "Invalid symbol." in body
        return DomainError("mapped it", ErrorType.BAD_ARGS)

    rest = RestClient(_client(handler), base_url="https://x.test", tag="t",
                      error_mapper=mapper)
    with pytest.raises(DomainError) as ei:
        await rest.request("GET", "/ping")
    assert ei.value.type is ErrorType.BAD_ARGS
    assert ei.value.message == "mapped it"


async def test_rest_client_without_a_mapper_is_unchanged():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="plain")

    rest = RestClient(_client(handler), base_url="https://x.test", tag="t")
    with pytest.raises(DomainError) as ei:
        await rest.request("GET", "/ping")
    assert ei.value.type is ErrorType.BAD_ARGS  # from _STATUS_ERROR[400]
```

- [ ] **Step 2: Run the tests, verify they fail**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_shared.py -q`
Expected: `test_rest_client_uses_the_error_mapper_when_given_one` FAILS with `TypeError: __init__() got an unexpected keyword argument 'error_mapper'`.

- [ ] **Step 3: Add the parameter and the branch**

In `rest.py`, add the import (top, with the others):

```python
from collections.abc import Callable
```

Change `__init__`:

```python
    def __init__(self, client: httpx.AsyncClient, *, base_url: str, tag: str,
                 error_mapper: Callable[[int, str], DomainError] | None = None) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._tag = tag
        self._error_mapper = error_mapper
```

In `request`, replace the `if response.status_code >= 400:` block with:

```python
        if response.status_code >= 400:
            if self._error_mapper is not None:
                raise self._error_mapper(response.status_code, response.text)
            kind = _STATUS_ERROR.get(response.status_code, ErrorType.UPSTREAM)
            raise DomainError(
                f"{self._tag} responded HTTP {response.status_code}: {response.text[:200]}",
                kind,
            )
```

- [ ] **Step 4: Run the tests, verify they pass**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_shared.py -q`
Expected: PASS. Then run the sibling suite to catch regressions:
`.venv/bin/python -m pytest tests/infrastructure/api/ -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/api/shared/rest.py backend/tests/infrastructure/api/test_shared.py
git commit -m "feat(tokocrypto-v3): optional error_mapper hook on RestClient"
```

---

### Task 2: v3 error mapper

Turn a Binance `{"code","msg"}` body into a `DomainError` with the right `ErrorType`. Reuse the code table that already exists in `tokocrypto/errors.py` — but rename it from private `_ERROR_CODE` to public `ERROR_CODE` first so a sibling module can import it without reaching into a private.

**Files:**
- Modify: `backend/src/tarakdingdung/infrastructure/api/tokocrypto/errors.py` (rename `_ERROR_CODE` → `ERROR_CODE`; it is referenced only inside `unwrap` in that same file)
- Create: `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/__init__.py` (empty)
- Create: `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/errors.py`
- Create: `backend/tests/infrastructure/api/test_tokocrypto_v3.py`

**Interfaces:**
- Consumes: `ERROR_CODE: dict[int, ErrorType]` from `tokocrypto/errors.py`.
- Produces: `map_v3_error(status: int, body: str) -> DomainError` in `infrastructure/api/tokocrypto/v3/errors.py`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/infrastructure/api/test_tokocrypto_v3.py`:

```python
import httpx
import pytest

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.tokocrypto.v3.errors import map_v3_error


def test_map_v3_error_reads_the_binance_code():
    err = map_v3_error(400, '{"code":-1121,"msg":"Invalid symbol."}')
    assert err.type is ErrorType.BAD_ARGS
    assert "Invalid symbol." in err.message


def test_map_v3_error_maps_a_state_code():
    err = map_v3_error(400, '{"code":-2010,"msg":"Account has insufficient balance."}')
    assert err.type is ErrorType.BAD_STATE


def test_map_v3_error_falls_back_to_status_when_body_is_opaque():
    assert map_v3_error(401, "not json").type is ErrorType.UNAUTHORIZED
    assert map_v3_error(500, "boom").type is ErrorType.UPSTREAM


def test_map_v3_error_unknown_code_is_upstream():
    assert map_v3_error(400, '{"code":-9999,"msg":"nope"}').type is ErrorType.UPSTREAM
```

- [ ] **Step 2: Run, verify it fails**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_tokocrypto_v3.py -q`
Expected: `ModuleNotFoundError: tarakdingdung.infrastructure.api.tokocrypto.v3.errors`.

- [ ] **Step 3: Rename the shared table**

In `backend/src/tarakdingdung/infrastructure/api/tokocrypto/errors.py`, rename `_ERROR_CODE` to `ERROR_CODE` (the dict literal and its one use inside `unwrap`: `kind = ERROR_CODE.get(...)`).

- [ ] **Step 4: Create the package and mapper**

Create `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/__init__.py` (empty).

Create `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/errors.py`:

```python
"""Turn a Binance-standard error response into a DomainError.

The `/api/v3/*` endpoints put the real reason in a `{"code","msg"}` JSON body
alongside a 4xx status, unlike `/open/v1` which wraps success and failure in
one 200 envelope. The numeric codes are the same Binance set, so the table in
`tokocrypto/errors.py` is reused rather than duplicated.
"""

import json

from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.infrastructure.api.tokocrypto.errors import ERROR_CODE

_STATUS_FALLBACK: dict[int, ErrorType] = {
    401: ErrorType.UNAUTHORIZED,
    403: ErrorType.UNAUTHORIZED,
    404: ErrorType.NOT_FOUND,
    408: ErrorType.TIMEOUT,
    429: ErrorType.RATE_LIMITED,
}


def map_v3_error(status: int, body: str) -> DomainError:
    code: object = None
    message = body[:200]
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict) and "code" in parsed:
        code = parsed.get("code")
        message = parsed.get("msg") or message

    kind = ERROR_CODE.get(code) if isinstance(code, int) else None
    if kind is None:
        kind = _STATUS_FALLBACK.get(status, ErrorType.UPSTREAM)

    label = f"[{code}]" if isinstance(code, int) else f"HTTP {status}"
    return DomainError(f"tokocrypto.v3 {label}: {message}", kind)
```

- [ ] **Step 5: Run, verify pass**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_tokocrypto_v3.py tests/infrastructure/api/test_clients.py -q`
Expected: PASS (the second file exercises the renamed `ERROR_CODE` through `unwrap`).

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/api/tokocrypto/errors.py \
        backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/ \
        backend/tests/infrastructure/api/test_tokocrypto_v3.py
git commit -m "feat(tokocrypto-v3): Binance error-body mapper"
```

---

### Task 3: v3 transport

Shared request/sign plumbing for `/api/v3/*`. Public calls send only `X-MBX-APIKEY`; signed calls append `&signature=<HMAC-SHA256>` over the encoded query and send it as the query string for every verb. No envelope unwrap.

**Files:**
- Create: `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/transport.py`
- Test: `backend/tests/infrastructure/api/test_tokocrypto_v3.py`

**Interfaces:**
- Consumes: `RestClient` (with `error_mapper` from Task 1), `map_v3_error` (Task 2), `hmac_sha256`, `encode_params`.
- Produces:
  - `V3_BASE_URL = "https://www.tokocrypto.site"`
  - `default_now_ms() -> int`
  - `TokocryptoV3Transport(client, *, api_key="", secret_key="", base_url=V3_BASE_URL, recv_window: int | None = None, now_ms=default_now_ms)`
  - `await transport.public_get(path, **params) -> Any` — returns `response.json()` verbatim
  - `await transport.signed_request(method, path, **params) -> Any`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/infrastructure/api/test_tokocrypto_v3.py`:

```python
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha256
from tarakdingdung.infrastructure.api.tokocrypto.v3.transport import TokocryptoV3Transport

_FIXED_NOW = lambda: 1_700_000_000_000


class _Capture:
    request: httpx.Request | None = None

    def client(self, response: httpx.Response) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            self.request = request
            return response
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_v3_public_get_sends_key_header_and_returns_raw_json():
    cap = _Capture()
    t = TokocryptoV3Transport(cap.client(httpx.Response(200, json={"serverTime": 1})),
                              api_key="mbx")
    assert await t.public_get("/api/v3/time") == {"serverTime": 1}
    assert cap.request.method == "GET"
    assert cap.request.url.path == "/api/v3/time"
    assert cap.request.headers["X-MBX-APIKEY"] == "mbx"


async def test_v3_public_get_omits_none_params_and_the_header_without_a_key():
    cap = _Capture()
    t = TokocryptoV3Transport(cap.client(httpx.Response(200, json=[])))
    await t.public_get("/api/v3/klines", symbol="BTCIDR", interval="1h", limit=None)
    assert cap.request.url.query.decode() == "symbol=BTCIDR&interval=1h"
    assert "X-MBX-APIKEY" not in cap.request.headers


async def test_v3_signed_request_appends_the_signature_over_the_encoded_query():
    cap = _Capture()
    t = TokocryptoV3Transport(cap.client(httpx.Response(200, json={"ok": 1})),
                              api_key="mbx", secret_key="sec", recv_window=5000,
                              now_ms=_FIXED_NOW)
    await t.signed_request("POST", "/api/v3/order", symbol="BTCIDR", side="BUY")
    unsigned = "timestamp=1700000000000&recvWindow=5000&symbol=BTCIDR&side=BUY"
    assert cap.request.url.query.decode() == (
        f"{unsigned}&signature={hmac_sha256('sec', unsigned)}")
    assert cap.request.headers["X-MBX-APIKEY"] == "mbx"


async def test_v3_transport_maps_a_binance_error_body():
    cap = _Capture()
    t = TokocryptoV3Transport(
        cap.client(httpx.Response(400, text='{"code":-1121,"msg":"Invalid symbol."}')))
    with pytest.raises(DomainError) as ei:
        await t.public_get("/api/v3/depth", symbol="NOPE")
    assert ei.value.type is ErrorType.BAD_ARGS
```

- [ ] **Step 2: Run, verify it fails**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_tokocrypto_v3.py -q`
Expected: `ImportError` for `TokocryptoV3Transport`.

- [ ] **Step 3: Write the transport**

Create `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/transport.py`:

```python
import time
from collections.abc import Callable
from typing import Any

import httpx

from tarakdingdung.infrastructure.api.shared.rest import RestClient, encode_params
from tarakdingdung.infrastructure.api.shared.signing import hmac_sha256
from tarakdingdung.infrastructure.api.tokocrypto.v3.errors import map_v3_error

V3_BASE_URL = "https://www.tokocrypto.site"


def default_now_ms() -> int:
    return int(time.time() * 1000)


class TokocryptoV3Transport:
    """Binance-standard `/api/v3/*` plumbing on the `.site` host.

    Responses are raw JSON — there is no `{code,msg,data}` envelope to unwrap.
    Failures arrive as a `{"code","msg"}` body with a 4xx status, so the
    RestClient is handed `map_v3_error` to read that body. Signed calls put the
    whole signed parameter string in the query for every verb; Binance accepts
    POST and DELETE parameters there.
    """

    def __init__(self, client: httpx.AsyncClient, *, api_key: str = "",
                 secret_key: str = "", base_url: str = V3_BASE_URL,
                 recv_window: int | None = None,
                 now_ms: Callable[[], int] = default_now_ms) -> None:
        self._rest = RestClient(client, base_url=base_url, tag="tokocrypto.v3",
                                error_mapper=map_v3_error)
        self._api_key = api_key
        self._secret_key = secret_key
        self._recv_window = recv_window
        self._now_ms = now_ms

    def _key_header(self) -> dict[str, str]:
        return {"X-MBX-APIKEY": self._api_key} if self._api_key else {}

    async def public_get(self, path: str, **params: Any) -> Any:
        return await self._rest.request(
            "GET", path, query=encode_params(params) or None,
            headers=self._key_header())

    async def signed_request(self, method: str, path: str, **params: Any) -> Any:
        base: dict[str, Any] = {"timestamp": self._now_ms()}
        if self._recv_window is not None:
            base["recvWindow"] = self._recv_window
        encoded = encode_params({**base, **params})
        signed = f"{encoded}&signature={hmac_sha256(self._secret_key, encoded)}"
        return await self._rest.request(method, path, query=signed,
                                       headers=self._key_header())
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_tokocrypto_v3.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/transport.py \
        backend/tests/infrastructure/api/test_tokocrypto_v3.py
git commit -m "feat(tokocrypto-v3): signed/public transport for /api/v3"
```

---

### Task 4: v3 market API (contract + client)

**Files:**
- Create: `backend/src/tarakdingdung/domain/contracts/api/tokocrypto/v3/__init__.py` (empty)
- Create: `backend/src/tarakdingdung/domain/contracts/api/tokocrypto/v3/market.py`
- Create: `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/market.py`
- Test: `backend/tests/infrastructure/api/test_tokocrypto_v3.py`

**Interfaces:**
- Consumes: `TokocryptoV3Transport`, `V3_BASE_URL`.
- Produces:
  - ABC `TokocryptoV3MarketApi` with `server_time()`, `exchange_info(*, symbol=None, symbols=None)`, `klines(*, symbol, interval, start_time=None, end_time=None, limit=None) -> list`, `depth(*, symbol, limit=None) -> dict`, `ticker_price(*, symbol) -> dict`.
  - `HttpTokocryptoV3MarketApi(client, *, api_key="", base_url=V3_BASE_URL)` implementing it.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/infrastructure/api/test_tokocrypto_v3.py`:

```python
from tarakdingdung.infrastructure.api.tokocrypto.v3.market import HttpTokocryptoV3MarketApi


async def test_v3_market_klines_passes_params_and_returns_the_array():
    cap = _Capture()
    api = HttpTokocryptoV3MarketApi(
        cap.client(httpx.Response(200, json=[[1, "1", "2", "0.5", "1.5", "10"]])))
    rows = await api.klines(symbol="BTCIDR", interval="1h", limit=2)
    assert rows == [[1, "1", "2", "0.5", "1.5", "10"]]
    assert cap.request.url.path == "/api/v3/klines"
    assert cap.request.url.params["symbol"] == "BTCIDR"
    assert cap.request.url.params["interval"] == "1h"
    assert cap.request.url.params["limit"] == "2"


async def test_v3_market_ticker_price_returns_the_object():
    cap = _Capture()
    api = HttpTokocryptoV3MarketApi(
        cap.client(httpx.Response(200, json={"symbol": "BTCIDR", "price": "1397.00"})))
    assert await api.ticker_price(symbol="BTCIDR") == {"symbol": "BTCIDR", "price": "1397.00"}
    assert cap.request.url.path == "/api/v3/ticker/price"


async def test_v3_market_depth_and_exchange_info_hit_their_paths():
    cap = _Capture()
    api = HttpTokocryptoV3MarketApi(cap.client(httpx.Response(200, json={"bids": [], "asks": []})))
    await api.depth(symbol="BTCIDR", limit=5)
    assert cap.request.url.path == "/api/v3/depth"
    api2 = HttpTokocryptoV3MarketApi(cap.client(httpx.Response(200, json={"symbols": []})))
    await api2.exchange_info()
    assert cap.request.url.path == "/api/v3/exchangeInfo"
```

- [ ] **Step 2: Run, verify it fails**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_tokocrypto_v3.py -q`
Expected: `ImportError` for `HttpTokocryptoV3MarketApi`.

- [ ] **Step 3: Write the contract**

Create `backend/src/tarakdingdung/domain/contracts/api/tokocrypto/v3/__init__.py` (empty) and `…/v3/market.py`:

```python
from abc import ABC, abstractmethod


class TokocryptoV3MarketApi(ABC):
    """Binance-standard public market data (`/api/v3/*` on the `.site` host).

    No authentication, no response envelope. `symbol` is the joined-upper form
    (`BTCIDR`). `interval` uses the Binance vocabulary (`1m`, `1h`, `1d`, …) —
    the same set the engine's `cron_interval` already uses, so it passes
    straight through with no mapping.
    """

    @abstractmethod
    async def server_time(self) -> dict: ...

    @abstractmethod
    async def exchange_info(self, *, symbol: str | None = None,
                            symbols: str | None = None) -> dict: ...

    @abstractmethod
    async def klines(self, *, symbol: str, interval: str, start_time: int | None = None,
                     end_time: int | None = None, limit: int | None = None) -> list: ...

    @abstractmethod
    async def depth(self, *, symbol: str, limit: int | None = None) -> dict: ...

    @abstractmethod
    async def ticker_price(self, *, symbol: str) -> dict: ...
```

- [ ] **Step 4: Write the client**

Create `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/market.py`:

```python
import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v3.market import TokocryptoV3MarketApi
from tarakdingdung.infrastructure.api.tokocrypto.v3.transport import (
    V3_BASE_URL,
    TokocryptoV3Transport,
)


class HttpTokocryptoV3MarketApi(TokocryptoV3MarketApi):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str = "",
                 base_url: str = V3_BASE_URL) -> None:
        self._t = TokocryptoV3Transport(client, api_key=api_key, base_url=base_url)

    async def server_time(self) -> dict:
        return await self._t.public_get("/api/v3/time")

    async def exchange_info(self, *, symbol: str | None = None,
                            symbols: str | None = None) -> dict:
        return await self._t.public_get("/api/v3/exchangeInfo", symbol=symbol,
                                        symbols=symbols)

    async def klines(self, *, symbol: str, interval: str, start_time: int | None = None,
                     end_time: int | None = None, limit: int | None = None) -> list:
        return await self._t.public_get("/api/v3/klines", symbol=symbol,
                                        interval=interval, startTime=start_time,
                                        endTime=end_time, limit=limit)

    async def depth(self, *, symbol: str, limit: int | None = None) -> dict:
        return await self._t.public_get("/api/v3/depth", symbol=symbol, limit=limit)

    async def ticker_price(self, *, symbol: str) -> dict:
        return await self._t.public_get("/api/v3/ticker/price", symbol=symbol)
```

- [ ] **Step 5: Run, verify pass**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_tokocrypto_v3.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/domain/contracts/api/tokocrypto/v3/ \
        backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/market.py \
        backend/tests/infrastructure/api/test_tokocrypto_v3.py
git commit -m "feat(tokocrypto-v3): market-data contract and client"
```

---

### Task 5: v3 trade API (contract + client)

**Files:**
- Create: `backend/src/tarakdingdung/domain/contracts/api/tokocrypto/v3/trade.py`
- Create: `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/trade.py`
- Test: `backend/tests/infrastructure/api/test_tokocrypto_v3.py`

**Interfaces:**
- Consumes: `TokocryptoV3Transport`, `V3_BASE_URL`, `default_now_ms`.
- Produces:
  - ABC `TokocryptoV3TradeApi`: `create_order(*, symbol, side, type, quantity=None, quote_order_qty=None, price=None, time_in_force=None, new_client_order_id=None, new_order_resp_type="FULL") -> dict`; `query_order(*, symbol, order_id=None, orig_client_order_id=None) -> dict`; `cancel_order(*, symbol, order_id=None, orig_client_order_id=None) -> dict`; `open_orders(*, symbol=None) -> list`; `my_trades(*, symbol, order_id=None, start_time=None, end_time=None, from_id=None, limit=None) -> list`; `account() -> dict`.
  - `HttpTokocryptoV3TradeApi(client, *, api_key, secret_key, base_url=V3_BASE_URL, recv_window=5000, now_ms=default_now_ms)`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/infrastructure/api/test_tokocrypto_v3.py`:

```python
from tarakdingdung.infrastructure.api.tokocrypto.v3.trade import HttpTokocryptoV3TradeApi


async def test_v3_trade_create_order_maps_snake_to_camel_and_defaults_full_resp():
    cap = _Capture()
    api = HttpTokocryptoV3TradeApi(
        cap.client(httpx.Response(200, json={"orderId": 7, "fills": []})),
        api_key="mbx", secret_key="sec", now_ms=_FIXED_NOW)
    out = await api.create_order(symbol="BTCIDR", side="BUY", type="LIMIT",
                                 quantity="1", price="1000",
                                 time_in_force="GTC", new_client_order_id="tdd1")
    assert out == {"orderId": 7, "fills": []}
    q = cap.request.url.query.decode()
    assert cap.request.method == "POST"
    assert cap.request.url.path == "/api/v3/order"
    assert "symbol=BTCIDR" in q and "side=BUY" in q and "type=LIMIT" in q
    assert "newClientOrderId=tdd1" in q and "newOrderRespType=FULL" in q
    assert "timeInForce=GTC" in q
    assert "&signature=" in q


async def test_v3_trade_account_is_signed():
    cap = _Capture()
    api = HttpTokocryptoV3TradeApi(
        cap.client(httpx.Response(200, json={"balances": []})),
        api_key="mbx", secret_key="sec", now_ms=_FIXED_NOW)
    assert await api.account() == {"balances": []}
    assert cap.request.url.path == "/api/v3/account"
    assert cap.request.headers["X-MBX-APIKEY"] == "mbx"
    assert "&signature=" in cap.request.url.query.decode()


async def test_v3_trade_query_order_uses_orig_client_order_id():
    cap = _Capture()
    api = HttpTokocryptoV3TradeApi(
        cap.client(httpx.Response(200, json={"status": "FILLED"})),
        api_key="mbx", secret_key="sec", now_ms=_FIXED_NOW)
    await api.query_order(symbol="BTCIDR", orig_client_order_id="tdd1")
    assert cap.request.method == "GET"
    assert "origClientOrderId=tdd1" in cap.request.url.query.decode()
```

- [ ] **Step 2: Run, verify it fails**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_tokocrypto_v3.py -q`
Expected: `ImportError` for `HttpTokocryptoV3TradeApi`.

- [ ] **Step 3: Write the contract**

Create `backend/src/tarakdingdung/domain/contracts/api/tokocrypto/v3/trade.py`:

```python
from abc import ABC, abstractmethod


class TokocryptoV3TradeApi(ABC):
    """Binance-standard signed spot trading + account (`/api/v3/*`).

    HMAC-SHA256 over the urlencoded query string, `X-MBX-APIKEY` header. Enum
    fields are the exchange's string values (`"BUY"`, `"LIMIT"`, `"GTC"`).
    Client orders are `newClientOrderId` on create and `origClientOrderId` on
    query/cancel; both of those also require `symbol`.
    """

    @abstractmethod
    async def create_order(self, *, symbol: str, side: str, type: str,
                           quantity: str | None = None,
                           quote_order_qty: str | None = None,
                           price: str | None = None,
                           time_in_force: str | None = None,
                           new_client_order_id: str | None = None,
                           new_order_resp_type: str = "FULL") -> dict: ...

    @abstractmethod
    async def query_order(self, *, symbol: str, order_id: int | None = None,
                          orig_client_order_id: str | None = None) -> dict: ...

    @abstractmethod
    async def cancel_order(self, *, symbol: str, order_id: int | None = None,
                           orig_client_order_id: str | None = None) -> dict: ...

    @abstractmethod
    async def open_orders(self, *, symbol: str | None = None) -> list: ...

    @abstractmethod
    async def my_trades(self, *, symbol: str, order_id: int | None = None,
                        start_time: int | None = None, end_time: int | None = None,
                        from_id: int | None = None, limit: int | None = None) -> list: ...

    @abstractmethod
    async def account(self) -> dict: ...
```

- [ ] **Step 4: Write the client**

Create `backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/trade.py`:

```python
from collections.abc import Callable

import httpx

from tarakdingdung.domain.contracts.api.tokocrypto.v3.trade import TokocryptoV3TradeApi
from tarakdingdung.infrastructure.api.tokocrypto.v3.transport import (
    V3_BASE_URL,
    TokocryptoV3Transport,
    default_now_ms,
)

_DEFAULT_RECV_WINDOW = 5000


class HttpTokocryptoV3TradeApi(TokocryptoV3TradeApi):
    def __init__(self, client: httpx.AsyncClient, *, api_key: str, secret_key: str,
                 base_url: str = V3_BASE_URL, recv_window: int = _DEFAULT_RECV_WINDOW,
                 now_ms: Callable[[], int] = default_now_ms) -> None:
        self._t = TokocryptoV3Transport(client, api_key=api_key, secret_key=secret_key,
                                        base_url=base_url, recv_window=recv_window,
                                        now_ms=now_ms)

    async def create_order(self, *, symbol: str, side: str, type: str,
                           quantity: str | None = None,
                           quote_order_qty: str | None = None,
                           price: str | None = None,
                           time_in_force: str | None = None,
                           new_client_order_id: str | None = None,
                           new_order_resp_type: str = "FULL") -> dict:
        return await self._t.signed_request(
            "POST", "/api/v3/order", symbol=symbol, side=side, type=type,
            quantity=quantity, quoteOrderQty=quote_order_qty, price=price,
            timeInForce=time_in_force, newClientOrderId=new_client_order_id,
            newOrderRespType=new_order_resp_type)

    async def query_order(self, *, symbol: str, order_id: int | None = None,
                          orig_client_order_id: str | None = None) -> dict:
        return await self._t.signed_request(
            "GET", "/api/v3/order", symbol=symbol, orderId=order_id,
            origClientOrderId=orig_client_order_id)

    async def cancel_order(self, *, symbol: str, order_id: int | None = None,
                           orig_client_order_id: str | None = None) -> dict:
        return await self._t.signed_request(
            "DELETE", "/api/v3/order", symbol=symbol, orderId=order_id,
            origClientOrderId=orig_client_order_id)

    async def open_orders(self, *, symbol: str | None = None) -> list:
        return await self._t.signed_request("GET", "/api/v3/openOrders", symbol=symbol)

    async def my_trades(self, *, symbol: str, order_id: int | None = None,
                        start_time: int | None = None, end_time: int | None = None,
                        from_id: int | None = None, limit: int | None = None) -> list:
        return await self._t.signed_request(
            "GET", "/api/v3/myTrades", symbol=symbol, orderId=order_id,
            startTime=start_time, endTime=end_time, fromId=from_id, limit=limit)

    async def account(self) -> dict:
        return await self._t.signed_request("GET", "/api/v3/account")
```

- [ ] **Step 5: Run, verify pass**

Run: `.venv/bin/python -m pytest tests/infrastructure/api/test_tokocrypto_v3.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/domain/contracts/api/tokocrypto/v3/trade.py \
        backend/src/tarakdingdung/infrastructure/api/tokocrypto/v3/trade.py \
        backend/tests/infrastructure/api/test_tokocrypto_v3.py
git commit -m "feat(tokocrypto-v3): signed trade + account contract and client"
```

---

### Task 6: widen `Executor.read_by_client_order_id` with an optional `symbol`

Binance `GET /api/v3/order` needs a symbol. The engine's reconcile loop holds the `PlannedOrder` for each unreconciled entry, so it can supply one. This task threads the parameter through the contract and every implementation without changing any behaviour yet — the Tokocrypto body still calls its `v1` client until Task 8.

**Files:**
- Modify: `backend/src/tarakdingdung/domain/contracts/execution/executor.py`
- Modify: `backend/src/tarakdingdung/infrastructure/execution/paper/executor.py`
- Modify: `backend/src/tarakdingdung/infrastructure/execution/live/router.py`
- Modify: `backend/src/tarakdingdung/infrastructure/execution/live/indodax.py`
- Modify: `backend/src/tarakdingdung/infrastructure/execution/live/tokocrypto.py` (signature only)
- Modify: `backend/src/tarakdingdung/application/trading/engine/usecase.py` (line ~166, the `_reconcile` call)
- Modify: `backend/tests/fakes/trading.py` (`FakeExecutor`)
- Test: `backend/tests/application/trading/test_engine.py`, `backend/tests/infrastructure/execution/test_executors.py`

**Interfaces:**
- Produces: `Executor.read_by_client_order_id(self, client_order_id: str, *, symbol: Symbol | None = None) -> ExecutionResult` across all implementations. `FakeExecutor` records calls in `self.looked_up: list[tuple[str, Symbol | None]]`.

- [ ] **Step 1: Update the failing tests**

In `backend/tests/application/trading/test_engine.py`:

- The `Failing(FakeExecutor)` subclass inside `test_a_failed_reconciliation_does_not_stop_the_cycle` currently declares `async def read_by_client_order_id(self, client_order_id):`. Change it to:

```python
        async def read_by_client_order_id(self, client_order_id, *, symbol=None):
            raise DomainError("venue down", ErrorType.UPSTREAM)
```

- Add a new test:

```python
async def test_reconcile_passes_the_symbol_to_the_executor():
    # Binance order lookup needs a symbol; the journal entry carries it.
    ctx = Ctx(cycle_plan=plan(orders=()))
    ctx.journal.unreconciled = [order()]
    await ctx.run()
    assert ctx.executor.looked_up == [("tdd0000000000001", BTC)]
```

(`conftest.order()` defaults to `client_order_id="tdd0000000000001"` and `symbol=BTC`, so those are the expected values.)

In `backend/tests/infrastructure/execution/test_executors.py`, update `test_indodax_lookup_is_refused_rather_than_guessed` to also prove a symbol does not change Indodax's answer:

```python
async def test_indodax_lookup_is_refused_rather_than_guessed():
    executor, _ = live()
    with pytest.raises(DomainError) as e:
        await executor.read_by_client_order_id("tdd1")
    assert e.value.type is ErrorType.UNIMPLEMENTED
    with pytest.raises(DomainError):
        await executor.read_by_client_order_id("tdd1", symbol=IDX)
```

- [ ] **Step 2: Run, verify failures**

Run: `.venv/bin/python -m pytest tests/application/trading/test_engine.py tests/infrastructure/execution/test_executors.py -q`
Expected: `test_reconcile_passes_the_symbol_to_the_executor` FAILS (`AttributeError: 'FakeExecutor' object has no attribute 'looked_up'`); the Indodax test FAILS on the second call (`TypeError: unexpected keyword argument 'symbol'`).

- [ ] **Step 3: Widen the contract**

`backend/src/tarakdingdung/domain/contracts/execution/executor.py` — `Symbol` is already imported. Change the abstract method:

```python
    @abstractmethod
    async def read_by_client_order_id(
        self, client_order_id: str, *, symbol: Symbol | None = None
    ) -> ExecutionResult:
        """Reconciliation path for an unconfirmed submission.

        ``symbol`` is optional because not every venue needs it: Indodax and
        Tokocrypto v3 look an order up by market, while the paper executor
        ignores it. The engine always passes the symbol from the journal.
        """
        ...
```

- [ ] **Step 4: Update every implementation**

`paper/executor.py`:

```python
    async def read_by_client_order_id(self, client_order_id: str, *,
                                      symbol: Symbol | None = None) -> ExecutionResult:
        return ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=())
```

`live/router.py` (body unchanged — routing a lookup with no order in hand is still refused):

```python
    async def read_by_client_order_id(self, client_order_id: str, *,
                                      symbol: Symbol | None = None) -> ExecutionResult:
        raise DomainError("reconcile through the venue executor that placed the order",
                          ErrorType.UNIMPLEMENTED)
```

`live/indodax.py` (body unchanged):

```python
    async def read_by_client_order_id(self, client_order_id: str, *,
                                      symbol: Symbol | None = None) -> ExecutionResult:
        raise DomainError(
            "indodax order lookup requires a symbol; reconcile through the "
            "journal, which records it alongside the client order id",
            ErrorType.UNIMPLEMENTED)
```

`live/tokocrypto.py` — signature only, body still the existing `v1` call for now:

```python
    async def read_by_client_order_id(self, client_order_id: str, *,
                                      symbol: Symbol | None = None) -> ExecutionResult:
        try:
            payload = await self._trade.query_order(client_id=client_order_id)
        except DomainError as err:
            if err.type is ErrorType.NOT_FOUND:
                return ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=())
            raise
        return ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=())
```

- [ ] **Step 5: Update the engine call site**

`backend/src/tarakdingdung/application/trading/engine/usecase.py`, in `_reconcile`, change:

```python
                found = await executor.read_by_client_order_id(order.client_order_id)
```

to:

```python
                found = await executor.read_by_client_order_id(
                    order.client_order_id, symbol=order.symbol)
```

- [ ] **Step 6: Update `FakeExecutor`**

`backend/tests/fakes/trading.py`, in `FakeExecutor.__init__` add `self.looked_up: list[tuple[str, object]] = []` (near `self.cancelled`), and change the method:

```python
    async def read_by_client_order_id(self, client_order_id, *, symbol=None) -> ExecutionResult:
        if self._journal is not None:
            self._journal.events.append("reconcile")
        self.looked_up.append((client_order_id, symbol))
        return self.known.get(
            client_order_id,
            ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=()))
```

- [ ] **Step 7: Run, verify pass**

Run: `.venv/bin/python -m pytest tests/application/trading/ tests/infrastructure/execution/ tests/domain/ -q`
Expected: PASS. Then the full suite once: `.venv/bin/python -m pytest -q` → PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/tarakdingdung/domain/contracts/execution/executor.py \
        backend/src/tarakdingdung/infrastructure/execution/ \
        backend/src/tarakdingdung/application/trading/engine/usecase.py \
        backend/tests/fakes/trading.py backend/tests/application/trading/test_engine.py \
        backend/tests/infrastructure/execution/test_executors.py
git commit -m "refactor(tokocrypto-v3): thread optional symbol through Executor.read_by_client_order_id"
```

---

### Task 7: repoint the market + account adapters at v3

**Files:**
- Modify: `backend/src/tarakdingdung/infrastructure/venue/tokocrypto/market.py`
- Modify: `backend/src/tarakdingdung/infrastructure/venue/tokocrypto/account.py`
- Test: `backend/tests/infrastructure/venue/test_adapters.py`

**Interfaces:**
- Consumes: `TokocryptoV3MarketApi`, `TokocryptoV3TradeApi`, `joined_upper`.
- Produces: `TokocryptoMarketDataSource(*, market: TokocryptoV3MarketApi, clock)` and `TokocryptoAccountSource(*, trade: TokocryptoV3TradeApi)` — same method surface (`fetch_candles`, `fetch_book`, `fetch_price`, `fetch_rules`; `fetch_balances`), now speaking `v3`.

- [ ] **Step 1: Rewrite the Tokocrypto section of `test_adapters.py`**

Replace `class StubTokocryptoMarket` and the `tokocrypto(...)` helper with:

```python
class StubTokocryptoV3Market:
    def __init__(self, **payloads) -> None:
        self.payloads = payloads
        self.calls: dict[str, object] = {}

    async def klines(self, *, symbol, interval, start_time=None, end_time=None, limit=None):
        self.calls["klines"] = (symbol, interval, limit)
        return self.payloads.get("klines", [])

    async def depth(self, *, symbol, limit=None):
        self.calls["depth"] = symbol
        return self.payloads.get("depth", {})

    async def ticker_price(self, *, symbol):
        self.calls["ticker_price"] = symbol
        return self.payloads.get("ticker_price", {})

    async def exchange_info(self, *, symbol=None, symbols=None):
        return self.payloads.get("exchange_info", {"symbols": []})

    async def server_time(self): ...


def tokocrypto(**payloads):
    stub = StubTokocryptoV3Market(**payloads)
    return TokocryptoMarketDataSource(market=stub, clock=FakeClock()), stub
```

Then replace the Tokocrypto tests with:

```python
async def test_tokocrypto_parses_binance_kline_arrays():
    source, stub = tokocrypto(klines=[[1_757_000_000_000, "1", "2", "0.5", "1.5", "10"]])
    candles = await source.fetch_candles(symbol=TKO, interval="1h", limit=1)
    assert candles[0].open_time == 1_757_000_000_000
    assert candles[0].high == Decimal("2")
    assert stub.calls["klines"][0] == "BTCUSDT"


async def test_tokocrypto_book_maps_bids_and_asks():
    source, stub = tokocrypto(depth={"bids": [["100", "1"]], "asks": [["101", "2"]]})
    book = await source.fetch_book(symbol=TKO, limit=10)
    assert book.bids[0].price == Decimal("100")
    assert book.asks[0].quantity == Decimal("2")
    assert stub.calls["depth"] == "BTCUSDT"


async def test_tokocrypto_price_reads_the_ticker():
    source, stub = tokocrypto(ticker_price={"symbol": "BTCUSDT", "price": "9.75"})
    assert await source.fetch_price(symbol=TKO) == Decimal("9.75")
    assert stub.calls["ticker_price"] == "BTCUSDT"


async def test_tokocrypto_price_raises_when_the_ticker_has_no_price():
    source, _ = tokocrypto(ticker_price={"symbol": "BTCUSDT"})
    with pytest.raises(DomainError) as e:
        await source.fetch_price(symbol=TKO)
    assert e.value.type is ErrorType.UPSTREAM


async def test_tokocrypto_rules_read_the_binance_filters():
    source, _ = tokocrypto(exchange_info={"symbols": [{
        "baseAsset": "BTC", "quoteAsset": "USDT",
        "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                    {"filterType": "LOT_SIZE", "stepSize": "0.0001"},
                    {"filterType": "NOTIONAL", "minNotional": "10"}]}]})
    rules = await source.fetch_rules()
    assert rules[TKO].tick_size == Decimal("0.01")
    assert rules[TKO].step_size == Decimal("0.0001")
    assert rules[TKO].min_notional == Decimal("10")


async def test_tokocrypto_rules_accept_the_legacy_min_notional_filter():
    source, _ = tokocrypto(exchange_info={"symbols": [{
        "baseAsset": "BTC", "quoteAsset": "USDT",
        "filters": [{"filterType": "MIN_NOTIONAL", "minNotional": "5"}]}]})
    rules = await source.fetch_rules()
    assert rules[TKO].min_notional == Decimal("5")


async def test_tokocrypto_rules_survive_a_missing_filter():
    source, _ = tokocrypto(exchange_info={"symbols": [
        {"baseAsset": "BTC", "quoteAsset": "USDT", "filters": []}]})
    rules = await source.fetch_rules()
    assert rules[TKO].tick_size == Decimal(0)


async def test_tokocrypto_balances_drop_zeroes():
    class StubTrade:
        async def account(self):
            return {"balances": [{"asset": "BTC", "free": "2", "locked": "0"},
                                 {"asset": "ETH", "free": "0", "locked": "0"}]}

    balances = await TokocryptoAccountSource(trade=StubTrade()).fetch_balances()
    assert balances == {"BTC": Decimal("2")}
```

- [ ] **Step 2: Run, verify failures**

Run: `.venv/bin/python -m pytest tests/infrastructure/venue/test_adapters.py -q`
Expected: the Tokocrypto tests FAIL (`fetch_price` still calls `klines`; `fetch_rules` still calls `symbols()`; `stub.calls["klines"][0]` is `"BTC_USDT"` not `"BTCUSDT"`).

- [ ] **Step 3: Rewrite `venue/tokocrypto/market.py`**

```python
from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.api.market_source import MarketDataSource
from tarakdingdung.domain.contracts.api.tokocrypto.v3.market import TokocryptoV3MarketApi
from tarakdingdung.domain.contracts.utility.clock import Clock
from tarakdingdung.domain.models.market import (
    BookLevel, Candle, OrderBook, Symbol, SymbolRules, Venue,
)
from tarakdingdung.infrastructure.venue.shared import to_decimal
from tarakdingdung.infrastructure.venue.symbols import joined_upper

_VENUE = "tokocrypto"

# Binance-standard fee schedule; `/api/v3` exposes no per-account tier, so this
# stays configuration rather than discovery.
_MAKER_FEE = Decimal("0.0010")
_TAKER_FEE = Decimal("0.0010")


class TokocryptoMarketDataSource(MarketDataSource):
    """Tokocrypto market data via the Binance-standard `/api/v3` API."""

    def __init__(self, *, market: TokocryptoV3MarketApi, clock: Clock) -> None:
        self._market = market
        self._clock = clock

    async def fetch_candles(self, *, symbol: Symbol, interval: str,
                            limit: int) -> tuple[Candle, ...]:
        rows = await self._market.klines(symbol=joined_upper(symbol),
                                         interval=interval, limit=limit)
        return tuple(_candle(row) for row in rows)

    async def fetch_book(self, *, symbol: Symbol, limit: int) -> OrderBook:
        payload = await self._market.depth(symbol=joined_upper(symbol), limit=limit)
        body = payload if isinstance(payload, dict) else {}
        return OrderBook(symbol=symbol, timestamp=await self._clock.now_ms(),
                         bids=_levels(body.get("bids")),
                         asks=_levels(body.get("asks")))

    async def fetch_price(self, *, symbol: Symbol) -> Decimal:
        payload = await self._market.ticker_price(symbol=joined_upper(symbol))
        body = payload if isinstance(payload, dict) else {}
        return to_decimal(body.get("price"), f"ticker for {symbol.base}", venue=_VENUE)

    async def fetch_rules(self) -> Mapping[Symbol, SymbolRules]:
        payload = await self._market.exchange_info()
        body = payload if isinstance(payload, dict) else {}
        rules: dict[Symbol, SymbolRules] = {}
        for entry in body.get("symbols") or []:
            symbol = _symbol(entry)
            if symbol is None:
                continue
            filters = entry.get("filters")
            rules[symbol] = SymbolRules(
                symbol=symbol,
                tick_size=_filter(filters, "PRICE_FILTER", "tickSize"),
                step_size=_filter(filters, "LOT_SIZE", "stepSize"),
                min_notional=_min_notional(filters),
                maker_fee=_MAKER_FEE, taker_fee=_TAKER_FEE)
        return rules


def _symbol(entry: dict) -> Symbol | None:
    base, quote = entry.get("baseAsset"), entry.get("quoteAsset")
    if not base or not quote:
        return None
    return Symbol(venue=Venue.TOKOCRYPTO, base=base.upper(), quote=quote.upper())


def _filter(filters, filter_type: str, field: str) -> Decimal:
    for entry in filters or []:
        if entry.get("filterType") == filter_type:
            return to_decimal(entry.get(field), field, venue=_VENUE, default=Decimal(0))
    return Decimal(0)


def _min_notional(filters) -> Decimal:
    # Binance renamed MIN_NOTIONAL to NOTIONAL; the field name stayed
    # `minNotional`. Accept either so an older symbol table still parses.
    for filter_type in ("NOTIONAL", "MIN_NOTIONAL"):
        value = _filter(filters, filter_type, "minNotional")
        if value != 0:
            return value
    return Decimal(0)


def _candle(row) -> Candle:
    # Binance kline arrays: [openTime, open, high, low, close, volume, ...]
    return Candle(open_time=int(row[0]),
                  open=to_decimal(row[1], "open", venue=_VENUE),
                  high=to_decimal(row[2], "high", venue=_VENUE),
                  low=to_decimal(row[3], "low", venue=_VENUE),
                  close=to_decimal(row[4], "close", venue=_VENUE),
                  volume=to_decimal(row[5], "volume", venue=_VENUE))


def _levels(raw) -> tuple[BookLevel, ...]:
    if not raw:
        return ()
    return tuple(BookLevel(price=to_decimal(price, "price", venue=_VENUE),
                           quantity=to_decimal(quantity, "quantity", venue=_VENUE))
                 for price, quantity in raw)
```

- [ ] **Step 4: Update `venue/tokocrypto/account.py`**

Only the import and the constructor type change; the body already accepts a `balances` list.

```python
from collections.abc import Mapping
from decimal import Decimal

from tarakdingdung.domain.contracts.api.account_source import AccountSource
from tarakdingdung.domain.contracts.api.tokocrypto.v3.trade import TokocryptoV3TradeApi
from tarakdingdung.infrastructure.venue.shared import to_decimal


class TokocryptoAccountSource(AccountSource):
    """Free balances per asset from the Binance-standard `/api/v3/account`."""

    _VENUE = "tokocrypto"

    def __init__(self, *, trade: TokocryptoV3TradeApi) -> None:
        self._trade = trade

    async def fetch_balances(self) -> Mapping[str, Decimal]:
        payload = await self._trade.account()
        balances: dict[str, Decimal] = {}
        for entry in payload.get("balances") or payload.get("accountAssets") or []:
            asset = (entry.get("asset") or "").upper()
            if not asset:
                continue
            free = to_decimal(entry.get("free"), f"free balance for {asset}",
                              venue=self._VENUE, default=Decimal(0))
            if free > 0:
                balances[asset] = free
        return balances
```

- [ ] **Step 5: Run, verify pass**

Run: `.venv/bin/python -m pytest tests/infrastructure/venue/test_adapters.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/venue/tokocrypto/ \
        backend/tests/infrastructure/venue/test_adapters.py
git commit -m "refactor(tokocrypto-v3): market + account adapters onto /api/v3"
```

---

### Task 8: rewrite `TokocryptoLiveExecutor` on v3 (string enums, fills, symbol-aware lookup)

**Files:**
- Modify: `backend/src/tarakdingdung/infrastructure/execution/live/tokocrypto.py`
- Test: `backend/tests/infrastructure/execution/test_executors.py`

**Interfaces:**
- Consumes: `TokocryptoV3TradeApi`, `joined_upper`, `Fill` (`tarakdingdung.domain.models.performance`), `to_decimal`.
- Produces: `TokocryptoLiveExecutor(*, trade: TokocryptoV3TradeApi, logger)` — `submit` returns `ExecutionResult` whose `fills` tuple is populated from `payload["fills"]`; `read_by_client_order_id(coid, *, symbol=None)` raises `UNIMPLEMENTED` without a symbol and returns an empty `ExecutionResult` with one.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/infrastructure/execution/test_executors.py`, add a Tokocrypto section (after the Indodax one):

```python
# --- tokocrypto live ------------------------------------------------------

from tarakdingdung.infrastructure.execution.live.tokocrypto import TokocryptoLiveExecutor


class StubTokocryptoV3Trade:
    def __init__(self, *, create=None, error=None, query_error=None, resting=()):
        self.create = create or {"orderId": 99, "transactTime": 1_757_000_000_000,
                                 "fills": []}
        self.error = error
        self.query_error = query_error
        self.resting = list(resting)
        self.created: list[dict] = []
        self.cancelled: list[dict] = []

    async def create_order(self, **kw):
        if self.error is not None:
            raise self.error
        self.created.append(kw)
        return self.create

    async def open_orders(self, *, symbol=None):
        return self.resting

    async def cancel_order(self, **kw):
        self.cancelled.append(kw)
        return {}

    async def query_order(self, **kw):
        if self.query_error is not None:
            raise self.query_error
        return {"status": "FILLED"}


def tko_live(**kw):
    stub = StubTokocryptoV3Trade(**kw)
    return TokocryptoLiveExecutor(trade=stub, logger=NullLogger()), stub


async def test_tko_submit_records_venue_id_and_string_enums():
    executor, stub = tko_live()
    result = await executor.submit((order(TKO),))
    assert result.accepted[0].venue_order_id == "99"
    assert stub.created[0]["symbol"] == "BTCUSDT"
    assert stub.created[0]["side"] == "BUY"
    assert stub.created[0]["type"] == "LIMIT"
    assert stub.created[0]["new_order_resp_type"] == "FULL"


async def test_tko_submit_maps_fills_from_a_full_response():
    executor, stub = tko_live(create={
        "orderId": 5, "transactTime": 1_757_000_000_123,
        "fills": [{"price": "100.0", "qty": "0.4", "commission": "0.04",
                   "commissionAsset": "USDT"},
                  {"price": "101.0", "qty": "0.6", "commission": "0.06",
                   "commissionAsset": "USDT"}]})
    result = await executor.submit((order(TKO),))
    assert [str(f.price) for f in result.fills] == ["100.0", "101.0"]
    assert [str(f.quantity) for f in result.fills] == ["0.4", "0.6"]
    assert result.fills[0].fee == Decimal("0.04")
    assert result.fills[0].timestamp == 1_757_000_000_123


async def test_tko_fee_in_a_foreign_asset_is_recorded_as_zero():
    recorded: list[str] = []

    class Rec(NullLogger):
        async def warn(self, tag, message, meta):
            recorded.append(message)

    stub = StubTokocryptoV3Trade(create={
        "orderId": 7, "transactTime": 1,
        "fills": [{"price": "100", "qty": "1", "commission": "0.001",
                   "commissionAsset": "BNB"}]})
    executor = TokocryptoLiveExecutor(trade=stub, logger=Rec())
    result = await executor.submit((order(TKO),))
    assert result.fills[0].fee == Decimal(0)
    assert recorded and "foreign asset" in recorded[0]


async def test_tko_resting_limit_has_no_fills_but_is_accepted():
    executor, _ = tko_live(create={"orderId": 8, "transactTime": 1, "fills": []})
    result = await executor.submit((order(TKO),))
    assert len(result.accepted) == 1
    assert result.fills == ()


async def test_tko_a_venue_verdict_becomes_a_rejection():
    executor, _ = tko_live(error=DomainError("bad price", ErrorType.BAD_ARGS))
    result = await executor.submit((order(TKO),))
    assert len(result.rejected) == 1 and result.is_complete


async def test_tko_a_timeout_is_unconfirmed():
    executor, _ = tko_live(error=DomainError("timed out", ErrorType.TIMEOUT))
    result = await executor.submit((order(TKO),))
    assert len(result.unconfirmed) == 1 and result.is_complete is False


async def test_tko_cancel_all_pulls_resting_orders_by_client_id():
    executor, stub = tko_live(resting=[{"clientOrderId": "a"}, {"clientOrderId": "b"}])
    await executor.cancel_all((TKO,))
    assert [c["orig_client_order_id"] for c in stub.cancelled] == ["a", "b"]
    assert stub.cancelled[0]["symbol"] == "BTCUSDT"


async def test_tko_lookup_needs_a_symbol():
    executor, _ = tko_live()
    with pytest.raises(DomainError) as e:
        await executor.read_by_client_order_id("tdd1")
    assert e.value.type is ErrorType.UNIMPLEMENTED


async def test_tko_lookup_treats_not_found_as_a_failed_submission():
    executor, _ = tko_live(query_error=DomainError("no", ErrorType.NOT_FOUND))
    result = await executor.read_by_client_order_id("tdd1", symbol=TKO)
    assert result == ExecutionResult((), (), (), ())
```

- [ ] **Step 2: Run, verify failures**

Run: `.venv/bin/python -m pytest tests/infrastructure/execution/test_executors.py -q`
Expected: the new `test_tko_*` tests FAIL (executor still constructs against the `v1` client shape; `fills` not mapped; `cancel_order` called with `client_id` not `orig_client_order_id`).

- [ ] **Step 3: Rewrite the executor**

```python
from decimal import Decimal

from tarakdingdung.domain.contracts.api.tokocrypto.v3.trade import TokocryptoV3TradeApi
from tarakdingdung.domain.contracts.execution.executor import Executor
from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger
from tarakdingdung.domain.models.algorithm import (
    OrderType, PlannedOrder, Side, TimeInForce,
)
from tarakdingdung.domain.models.error import DomainError, ErrorType
from tarakdingdung.domain.models.execution import (
    ExecutionResult, OrderAck, OrderRejection, UnconfirmedOrder,
)
from tarakdingdung.domain.models.market import Symbol
from tarakdingdung.domain.models.performance import Fill
from tarakdingdung.infrastructure.execution.live.classify import is_settled
from tarakdingdung.infrastructure.venue.shared import to_decimal
from tarakdingdung.infrastructure.venue.symbols import joined_upper

_VENUE = "tokocrypto"
_SIDES = {Side.BUY: "BUY", Side.SELL: "SELL"}
_TYPES = {OrderType.LIMIT: "LIMIT", OrderType.MARKET: "MARKET",
          OrderType.LIMIT_MAKER: "LIMIT_MAKER"}
_TIME_IN_FORCE = {TimeInForce.GTC: "GTC", TimeInForce.IOC: "IOC", TimeInForce.FOK: "FOK"}

_EMPTY = ExecutionResult(accepted=(), rejected=(), unconfirmed=(), fills=())


class TokocryptoLiveExecutor(Executor):
    """Sends real orders to Tokocrypto via the Binance-standard `/api/v3` API.

    `create_order` is sent with `newOrderRespType=FULL`, so a crossing order
    comes back with a `fills` array this maps straight to `Fill`s. A fill whose
    commission was charged in an asset other than the quote currency records a
    zero fee and a warning: a BNB-denominated number must not enter a
    quote-denominated ledger.
    """

    _TAG = "execution/tokocrypto"

    def __init__(self, *, trade: TokocryptoV3TradeApi, logger: LeveledLogger) -> None:
        self._trade = trade
        self._logger = logger

    async def submit(self, orders: tuple[PlannedOrder, ...]) -> ExecutionResult:
        accepted: list[OrderAck] = []
        rejected: list[OrderRejection] = []
        unconfirmed: list[UnconfirmedOrder] = []
        fills: list[Fill] = []

        for order in orders:
            client_order_id = order.client_order_id or ""
            try:
                payload = await self._create(order, client_order_id)
            except DomainError as err:
                await self._logger.error(f"{self._TAG}/Submit", "order failed",
                                         {"err": err, "client_order_id": client_order_id})
                if is_settled(err.type):
                    rejected.append(OrderRejection(
                        order=order, client_order_id=client_order_id, reason=err.message))
                else:
                    unconfirmed.append(UnconfirmedOrder(
                        order=order, client_order_id=client_order_id, reason=err.message))
                continue
            accepted.append(OrderAck(order=order, client_order_id=client_order_id,
                                     venue_order_id=str(payload.get("orderId", ""))))
            fills.extend(await self._fills(order, payload))

        return ExecutionResult(accepted=tuple(accepted), rejected=tuple(rejected),
                               unconfirmed=tuple(unconfirmed), fills=tuple(fills))

    async def cancel_all(self, symbols: tuple[Symbol, ...]) -> None:
        for symbol in symbols:
            resting = await self._trade.open_orders(symbol=joined_upper(symbol))
            for entry in resting or []:
                await self._trade.cancel_order(
                    symbol=joined_upper(symbol),
                    orig_client_order_id=entry.get("clientOrderId"))

    async def read_by_client_order_id(self, client_order_id: str, *,
                                      symbol: Symbol | None = None) -> ExecutionResult:
        if symbol is None:
            raise DomainError("tokocrypto v3 order lookup needs a symbol",
                              ErrorType.UNIMPLEMENTED)
        try:
            await self._trade.query_order(symbol=joined_upper(symbol),
                                          orig_client_order_id=client_order_id)
        except DomainError as err:
            if err.type is ErrorType.NOT_FOUND:
                return _EMPTY
            raise
        # The venue knows the order. Back-filling its state and fills from the
        # payload / my_trades is a known gap; the portfolio sync reconciles
        # holdings against the venue in the meantime.
        return _EMPTY

    async def _create(self, order: PlannedOrder, client_order_id: str) -> dict:
        return await self._trade.create_order(
            symbol=joined_upper(order.symbol), side=_SIDES[order.side],
            type=_TYPES[order.type], quantity=str(order.quantity),
            price=str(order.price) if order.price is not None else None,
            time_in_force=_TIME_IN_FORCE.get(order.time_in_force),
            new_client_order_id=client_order_id, new_order_resp_type="FULL")

    async def _fills(self, order: PlannedOrder, payload: dict) -> list[Fill]:
        timestamp = int(payload.get("transactTime") or 0)
        quote = order.symbol.quote.upper()
        out: list[Fill] = []
        for entry in payload.get("fills") or []:
            asset = (entry.get("commissionAsset") or "").upper()
            if asset and asset != quote:
                await self._logger.warn(
                    f"{self._TAG}/Submit", "fee charged in a foreign asset",
                    {"client_order_id": order.client_order_id,
                     "commission_asset": asset, "quote": quote})
            fee = (to_decimal(entry.get("commission"), "commission", venue=_VENUE,
                              default=Decimal(0))
                   if asset == quote else Decimal(0))
            out.append(Fill(
                symbol=order.symbol, side=order.side,
                quantity=to_decimal(entry.get("qty"), "fill qty", venue=_VENUE),
                price=to_decimal(entry.get("price"), "fill price", venue=_VENUE),
                fee=fee, timestamp=timestamp))
        return out
```

- [ ] **Step 4: Run, verify pass**

Run: `.venv/bin/python -m pytest tests/infrastructure/execution/test_executors.py -q`
Expected: PASS. Then `.venv/bin/python -m pytest tests/infrastructure/ tests/application/ -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/tarakdingdung/infrastructure/execution/live/tokocrypto.py \
        backend/tests/infrastructure/execution/test_executors.py
git commit -m "feat(tokocrypto-v3): executor on /api/v3 with fills from FULL responses"
```

---

### Task 9: composition + settings

**Files:**
- Modify: `backend/src/tarakdingdung/config/settings.py`
- Modify: `backend/src/tarakdingdung/composition/main/exchanges.py`
- Modify: `backend/.env.example`
- Create: `backend/tests/composition/test_exchanges.py`

**Interfaces:**
- Consumes: `HttpTokocryptoV3MarketApi`, `HttpTokocryptoV3TradeApi`.
- Produces: `Settings.tokocrypto_v3_base_url` (`TRDD_BE_TOKOCRYPTO_V3_BASE_URL`, default `https://www.tokocrypto.site`). `build_exchanges` wires the three Tokocrypto adapters onto `v3` clients.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/composition/test_exchanges.py`:

```python
import httpx

from tarakdingdung.composition.main.exchanges import build_exchanges
from tarakdingdung.config.settings import Settings
from tarakdingdung.domain.models.market import Venue
from tarakdingdung.infrastructure.api.tokocrypto.v3.market import HttpTokocryptoV3MarketApi
from tarakdingdung.infrastructure.api.tokocrypto.v3.trade import HttpTokocryptoV3TradeApi
from tests.fakes.trading import FakeClock
from tests.fakes.utilities import NullLogger


def test_build_exchanges_wires_tokocrypto_onto_v3():
    ex = build_exchanges(httpx.AsyncClient(), Settings(),
                         clock=FakeClock(), logger=NullLogger())
    assert isinstance(ex.markets[Venue.TOKOCRYPTO]._market, HttpTokocryptoV3MarketApi)
    assert isinstance(ex.accounts[Venue.TOKOCRYPTO]._trade, HttpTokocryptoV3TradeApi)
    assert isinstance(ex.executors[Venue.TOKOCRYPTO]._trade, HttpTokocryptoV3TradeApi)


def test_settings_expose_a_v3_base_url_default():
    assert Settings().tokocrypto_v3_base_url == "https://www.tokocrypto.site"
```

- [ ] **Step 2: Run, verify it fails**

Run: `.venv/bin/python -m pytest tests/composition/test_exchanges.py -q`
Expected: `AttributeError: 'Settings' object has no attribute 'tokocrypto_v3_base_url'` / the wiring assertions fail (still `HttpTokocryptoV1MarketApi`).

- [ ] **Step 3: Add the setting**

`backend/src/tarakdingdung/config/settings.py`, immediately after `tokocrypto_secret_key`:

```python
    tokocrypto_secret_key: str = "changemetokocryptosecretkey"
    tokocrypto_v3_base_url: str = "https://www.tokocrypto.site"
```

- [ ] **Step 4: Rewire `exchanges.py`**

Replace the two `v1` imports (lines 21-22):

```python
from tarakdingdung.infrastructure.api.tokocrypto.v3.market import HttpTokocryptoV3MarketApi
from tarakdingdung.infrastructure.api.tokocrypto.v3.trade import HttpTokocryptoV3TradeApi
```

In `build_exchanges`, replace the two `tokocrypto_*` constructions:

```python
    tokocrypto_market = HttpTokocryptoV3MarketApi(
        http, base_url=settings.tokocrypto_v3_base_url)
    tokocrypto_trade = HttpTokocryptoV3TradeApi(
        http, api_key=settings.tokocrypto_api_key,
        secret_key=settings.tokocrypto_secret_key,
        base_url=settings.tokocrypto_v3_base_url)
```

The three adapter constructions (`TokocryptoMarketDataSource(market=…)`,
`TokocryptoAccountSource(trade=…)`, `TokocryptoLiveExecutor(trade=…)`) are
unchanged — they now receive `v3` clients.

- [ ] **Step 5: Document the env var**

`backend/.env.example` — add near the other Tokocrypto lines:

```
TRDD_BE_TOKOCRYPTO_V3_BASE_URL=https://www.tokocrypto.site
```

- [ ] **Step 6: Run, verify pass**

Run: `.venv/bin/python -m pytest tests/composition/ -q`
Expected: PASS. Then the full suite: `.venv/bin/python -m pytest -q` → PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/tarakdingdung/config/settings.py \
        backend/src/tarakdingdung/composition/main/exchanges.py \
        backend/.env.example backend/tests/composition/test_exchanges.py
git commit -m "feat(tokocrypto-v3): wire venue adapters onto v3, add base-url setting"
```

---

### Task 10: live authentication probe (issue #2)

Not committed. This proves the real credentials + signing work end to end against the live API before any order is placed. It does **not** place an order.

**Files:**
- Create: `<scratchpad>/v3_auth_probe.py` (scratchpad dir, throwaway — never `git add`)

**Interfaces:**
- Consumes: `Settings()` (reads `backend/.env`), `HttpTokocryptoV3TradeApi`.
- Produces: a console line `auth OK — N non-zero balances` or a masked failure. No key material, no amounts.

- [ ] **Step 1: Write the probe**

Create `<scratchpad>/v3_auth_probe.py`:

```python
"""Throwaway: prove the Tokocrypto v3 keys authenticate. Places no orders.

Run from backend/:  .venv/bin/python <path>/v3_auth_probe.py
"""

import asyncio

import httpx

from tarakdingdung.config.settings import Settings
from tarakdingdung.infrastructure.api.tokocrypto.v3.trade import HttpTokocryptoV3TradeApi


async def main() -> None:
    s = Settings()
    async with httpx.AsyncClient(timeout=s.exchange_timeout_seconds) as http:
        api = HttpTokocryptoV3TradeApi(
            http, api_key=s.tokocrypto_api_key, secret_key=s.tokocrypto_secret_key,
            base_url=s.tokocrypto_v3_base_url)
        try:
            account = await api.account()
        except Exception as exc:  # noqa: BLE001 - probe reports every failure
            print(f"auth FAILED: {type(exc).__name__}: {str(exc)[:160]}")
            return
        balances = [b for b in account.get("balances", [])
                    if b.get("free", "0") not in ("0", "0.00000000", "")]
        print(f"auth OK — {len(balances)} non-zero balances")
        print(f"canTrade={account.get('canTrade')} canWithdraw={account.get('canWithdraw')}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python <scratchpad>/v3_auth_probe.py`
Expected: `auth OK — N non-zero balances` and `canTrade=True canWithdraw=False`.
If it prints `auth FAILED: ... -2014` or `-1022`, the key or signature is wrong — stop and report; do not proceed to live trading.

- [ ] **Step 3: Report, do not commit**

Summarise the probe result to the user (masking any figure). Leave the file in the scratchpad. There is no commit for this task.

---

## Self-Review

**1. Spec coverage**

| Spec section | Task |
|---|---|
| `RestClient` `error_mapper` change | Task 1 |
| `errors.py` / `map_v3_error`, reuse Binance code table | Task 2 |
| `transport.py` `TokocryptoV3Transport` | Task 3 |
| New contract `TokocryptoV3MarketApi` + `Http…` | Task 4 |
| New contract `TokocryptoV3TradeApi` + `Http…` | Task 5 |
| `Executor.read_by_client_order_id` gains `symbol`; call sites | Task 6 |
| `TokocryptoMarketDataSource` → v3 (ticker, exchangeInfo, joined_upper) | Task 7 |
| `TokocryptoAccountSource` → v3 | Task 7 |
| `TokocryptoLiveExecutor` → v3, string enums, fills, fee-asset rule | Task 8 |
| `read_by_client_order_id` symbol/NOT_FOUND handling | Task 8 |
| `Settings.tokocrypto_v3_base_url`; `exchanges.py` rewiring; `/open/v1` left unwired | Task 9 |
| Issue #2 auth probe (throwaway) | Task 10 |
| Unit tests per `Http…` class against captured shapes | Tasks 2-5 |
| Adapter tests (filters, ticker, fee-asset, empty fills) | Tasks 7-8 |
| `Executor` conformance covers the `symbol` keyword | Task 6 (fakes + tests) |
| Out of scope: WS, deleting v1, OCO, Indodax lookup, fee-tier discovery | not implemented — correct |

**2. Placeholder scan:** none — every code step carries the full source.

**3. Type consistency:**
- `map_v3_error(status: int, body: str) -> DomainError` — defined Task 2, consumed Task 3. ✓
- `TokocryptoV3Transport(... recv_window: int | None = None ...)` — Task 3; the trade client passes `recv_window=5000`, the market client omits it. ✓
- `public_get` / `signed_request` names — Task 3, used Tasks 4-5. ✓
- `TokocryptoV3MarketApi.klines(...) -> list` returns a bare array; `TokocryptoMarketDataSource.fetch_candles` iterates it directly (no `_rows`). ✓
- `TokocryptoV3TradeApi.create_order(... new_order_resp_type="FULL")` — Task 5; executor passes `new_order_resp_type="FULL"` and reads `payload["fills"]`, `payload["orderId"]`, `payload["transactTime"]`. ✓
- `cancel_order(*, symbol, orig_client_order_id=…)` — Task 5; executor `cancel_all` calls it with `orig_client_order_id=entry.get("clientOrderId")`. ✓
- `read_by_client_order_id(self, client_order_id, *, symbol=None)` — identical signature in the contract (Task 6) and all five implementations (Tasks 6, 8). Engine passes `symbol=order.symbol` (Task 6). `FakeExecutor.looked_up` recorded (Task 6) and asserted (Task 6 test). ✓
- `Fill(symbol, side, quantity, price, fee, timestamp)` — matches `domain/models/performance.py`. ✓
- `_filter` / `_min_notional` helpers — defined and used within `venue/tokocrypto/market.py` (Task 7). ✓
