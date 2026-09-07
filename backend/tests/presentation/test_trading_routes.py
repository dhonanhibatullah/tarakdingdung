import pytest


async def _headers(client) -> dict:
    login = await client.post("/api/v1/auth/login",
                              json={"username": "super", "password": "secret12"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _strategy_body(**kw) -> dict:
    base = {"name": "momentum", "kind": "pipeline", "mode": "PAPER",
            "universe": [{"venue": "INDODAX", "base": "BTC", "quote": "IDR"}]}
    return {**base, **kw}


# --- the security property --------------------------------------------------

@pytest.mark.asyncio
async def test_no_route_executes_a_live_cycle(app):
    """The engine is reachable only from cron.

    An HTTP endpoint that places real orders would be an attack surface with
    no compensating benefit, so this asserts the absence rather than trusting
    that nobody adds one.
    """
    engine_paths = {path for path in app.openapi()["paths"] if "/engine" in path}
    assert engine_paths == {"/api/v1/trading/engine/{strategy_id}/dry-run"}


@pytest.mark.asyncio
async def test_a_dry_run_plans_without_submitting(client, seeded):
    headers = await _headers(client)
    created = await client.post("/api/v1/trading/strategies",
                                json=_strategy_body(), headers=headers)
    strategy_id = created.json()["id"]
    resp = await client.post(
        f"/api/v1/trading/engine/{strategy_id}/dry-run", headers=headers)
    assert resp.status_code == 200
    # No stored portfolio or market data in this harness, so the honest answer
    # is that it had nothing to decide on.
    assert resp.json()["decision"] in {"DRY_RUN", "NO_DATA"}


# --- authorisation ----------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("get", "/api/v1/trading/strategies"),
    ("post", "/api/v1/trading/strategies"),
    ("get", "/api/v1/trading/backtests"),
    ("get", "/api/v1/trading/portfolio"),
    ("post", "/api/v1/trading/engine/00000000-0000-0000-0000-000000000000/dry-run"),
])
async def test_every_trading_route_requires_a_bearer(client, method, path):
    resp = await getattr(client, method)(path)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_a_missing_permission_is_forbidden(client, wiring):
    _container, roles, perms, rps, users = wiring
    # A user with only profile access must not reach the trading surface.
    rid = await roles.create(name="plain", description=None, is_default=None,
                             created_by=None)
    pid = await perms.create(name="profile:get", description=None, created_by=None)
    await rps.create(role_id=rid, permission_id=pid, created_by=None)
    await users.create(role_id=rid, name="Plain", bio=None, username="plain",
                       password_hash="hash::secret12", created_by=None)

    login = await client.post("/api/v1/auth/login",
                              json={"username": "plain", "password": "secret12"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.get("/api/v1/trading/strategies",
                             headers=headers)).status_code == 403


# --- strategies -------------------------------------------------------------

@pytest.mark.asyncio
async def test_strategy_crud_round_trip(client, seeded):
    headers = await _headers(client)

    created = await client.post("/api/v1/trading/strategies",
                                json=_strategy_body(), headers=headers)
    assert created.status_code == 201
    strategy_id = created.json()["id"]

    detail = await client.get(f"/api/v1/trading/strategies/{strategy_id}",
                              headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["mode"] == "PAPER"
    assert body["universe"] == [{"venue": "INDODAX", "base": "BTC", "quote": "IDR"}]

    patched = await client.patch(f"/api/v1/trading/strategies/{strategy_id}",
                                 json={"is_enabled": True}, headers=headers)
    assert patched.status_code == 204

    listing = await client.get("/api/v1/trading/strategies", headers=headers)
    assert listing.json()["page"]["total_items"] == 1

    deleted = await client.delete(f"/api/v1/trading/strategies/{strategy_id}",
                                  headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_an_empty_universe_is_rejected(client, seeded):
    headers = await _headers(client)
    resp = await client.post("/api/v1/trading/strategies",
                             json=_strategy_body(universe=[]), headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_an_unknown_venue_is_a_bad_request(client, seeded):
    headers = await _headers(client)
    resp = await client.post(
        "/api/v1/trading/strategies",
        json=_strategy_body(universe=[{"venue": "BINANCE", "base": "BTC",
                                       "quote": "USDT"}]),
        headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_an_unknown_mode_is_a_bad_request(client, seeded):
    headers = await _headers(client)
    resp = await client.post("/api/v1/trading/strategies",
                             json=_strategy_body(mode="YOLO"), headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_a_missing_strategy_is_not_found(client, seeded):
    headers = await _headers(client)
    resp = await client.get(
        "/api/v1/trading/strategies/00000000-0000-0000-0000-000000000000",
        headers=headers)
    assert resp.status_code == 404


# --- market data ------------------------------------------------------------

@pytest.mark.asyncio
async def test_coverage_reports_completeness(client, seeded):
    headers = await _headers(client)
    resp = await client.get(
        "/api/v1/trading/coverage?venue=INDODAX&base=BTC&quote=IDR"
        "&window_start=1000&window_end=2000", headers=headers)
    assert resp.status_code == 200
    assert "completeness" in resp.json()


@pytest.mark.asyncio
async def test_a_reversed_window_is_rejected(client, seeded):
    # TimeRange validates that a window advances; a reversed one would
    # otherwise select nothing and read as an empty success.
    headers = await _headers(client)
    resp = await client.get(
        "/api/v1/trading/coverage?venue=INDODAX&base=BTC&quote=IDR"
        "&window_start=2000&window_end=1000", headers=headers)
    assert resp.status_code == 400


# --- portfolio --------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_is_not_found_before_the_first_sync(client, seeded):
    headers = await _headers(client)
    resp = await client.get("/api/v1/trading/portfolio", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_the_equity_curve_starts_empty(client, seeded):
    headers = await _headers(client)
    resp = await client.get(
        "/api/v1/trading/portfolio/equity?window_start=1000&window_end=2000",
        headers=headers)
    assert resp.status_code == 200
    assert resp.json()["points"] == []


# --- backtests --------------------------------------------------------------

@pytest.mark.asyncio
async def test_backtests_start_empty(client, seeded):
    headers = await _headers(client)
    resp = await client.get("/api/v1/trading/backtests", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["page"]["total_items"] == 0
