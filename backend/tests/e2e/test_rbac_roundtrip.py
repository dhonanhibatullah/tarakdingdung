import pytest


@pytest.mark.asyncio
async def test_login_returns_seeded_permissions(e2e_client):
    resp = await e2e_client.post("/api/v1/auth/login",
                                 json={"username": "super", "password": "superpass12"})
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()["permissions"]}
    assert {"permission:add", "role:add", "user:add"} <= names


@pytest.mark.asyncio
async def test_no_token_is_401_and_wrong_permission_is_403(e2e_client):
    assert (await e2e_client.get("/api/v1/admin/users")).status_code == 401
    login = await e2e_client.post("/api/v1/auth/login",
                                  json={"username": "user", "password": "changeme12345"})
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await e2e_client.get("/api/v1/admin/users", headers=user_headers)).status_code == 403
    assert (await e2e_client.get("/api/v1/profile", headers=user_headers)).status_code == 200


@pytest.mark.asyncio
async def test_full_rbac_roundtrip(e2e_client, super_headers):
    role_id = (await e2e_client.post("/api/v1/admin/roles", json={"name": "barista"},
                                     headers=super_headers)).json()["id"]
    # profile:get already seeded -> expect 409
    dup = await e2e_client.post("/api/v1/admin/permissions", json={"name": "profile:get"},
                                headers=super_headers)
    assert dup.status_code == 409

    new_perm = (await e2e_client.post("/api/v1/admin/permissions", json={"name": "brew:pull"},
                                      headers=super_headers)).json()["id"]
    assign = await e2e_client.post(
        f"/api/v1/admin/roles/{role_id}/permissions/{new_perm}", headers=super_headers)
    assert assign.status_code == 201

    created_user = await e2e_client.post("/api/v1/admin/users", json={
        "role_id": role_id, "name": "Bar Ista", "username": "barista1", "password": "espresso9",
    }, headers=super_headers)
    assert created_user.status_code == 201

    login = await e2e_client.post("/api/v1/auth/login",
                                  json={"username": "barista1", "password": "espresso9"})
    assert login.status_code == 200
    assert {p["name"] for p in login.json()["permissions"]} == {"brew:pull"}

    barista_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    perms = await e2e_client.get("/api/v1/profile/permissions", headers=barista_headers)
    # barista role lacks profile:get -> 403 on the profile route
    assert perms.status_code == 403


@pytest.mark.asyncio
async def test_login_wrong_password_is_401(e2e_client):
    resp = await e2e_client.post("/api/v1/auth/login",
                                 json={"username": "user", "password": "wrong-password"})
    assert resp.status_code == 401
    assert set(resp.json()) == {"error", "message"}


@pytest.mark.asyncio
async def test_change_password_wrong_current_is_401(e2e_client):
    login = await e2e_client.post("/api/v1/auth/login",
                                  json={"username": "user", "password": "changeme12345"})
    assert login.status_code == 200
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await e2e_client.patch("/api/v1/profile/password", headers=user_headers, json={
        "current_password": "not-the-current-one", "new_password": "brandnew12345",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_domain_error_body_shape(e2e_client, super_headers):
    resp = await e2e_client.get("/api/v1/admin/roles/by-name/does-not-exist",
                                headers=super_headers)
    assert resp.status_code == 404
    assert set(resp.json()) == {"error", "message"}
    assert resp.json()["error"] == "Not Found"
