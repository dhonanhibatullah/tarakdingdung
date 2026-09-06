import pytest


@pytest.mark.asyncio
async def test_version_endpoint(client):
    resp = await client.get("/api/version")
    assert resp.status_code == 200 and resp.text == "v-test"


@pytest.mark.asyncio
async def test_login_success_and_bad_password(client, seeded):
    ok = await client.post("/api/v1/auth/login",
                           json={"username": "super", "password": "secret12"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["access_token"].startswith("access::")
    assert body["role"]["name"] == "super"
    assert {p["name"] for p in body["permissions"]} >= {"permission:get", "user:add"}

    bad = await client.post("/api/v1/auth/login",
                            json={"username": "super", "password": "nope"})
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_admin_requires_bearer_and_permission(client, seeded):
    unauth = await client.get("/api/v1/admin/permissions")
    assert unauth.status_code == 401

    login = await client.post("/api/v1/auth/login",
                              json={"username": "super", "password": "secret12"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post("/api/v1/admin/permissions",
                                json={"name": "widget:get", "description": "d"}, headers=headers)
    assert created.status_code == 201
    pid = created.json()["id"]

    listing = await client.get("/api/v1/admin/permissions?search=widget", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["page"]["total_items"] == 1

    patched = await client.patch(f"/api/v1/admin/permissions/{pid}",
                                 json={"description": "changed"}, headers=headers)
    assert patched.status_code == 204

    deleted = await client.delete(f"/api/v1/admin/permissions/{pid}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_admin_role_permission_roundtrip(client, seeded):
    login = await client.post("/api/v1/auth/login",
                              json={"username": "super", "password": "secret12"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    role_id = (await client.post("/api/v1/admin/roles", json={"name": "barista"},
                                 headers=headers)).json()["id"]
    perm_id = (await client.post("/api/v1/admin/permissions", json={"name": "brew:do"},
                                 headers=headers)).json()["id"]
    assigned = await client.post(
        f"/api/v1/admin/roles/{role_id}/permissions/{perm_id}", headers=headers)
    assert assigned.status_code == 201
    detail = await client.get(
        f"/api/v1/admin/role-permissions/by-pair?role_id={role_id}&permission_id={perm_id}",
        headers=headers)
    assert detail.status_code == 200
    assert detail.json()["role"]["id"] == role_id


@pytest.mark.asyncio
async def test_profile_endpoints(client, seeded):
    login = await client.post("/api/v1/auth/login",
                              json={"username": "super", "password": "secret12"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = await client.get("/api/v1/profile", headers=headers)
    assert me.status_code == 200 and me.json()["username"] == "super"
    perms = await client.get("/api/v1/profile/permissions", headers=headers)
    assert perms.status_code == 200 and any(p["name"] == "profile:get" for p in perms.json())
    patched = await client.patch("/api/v1/profile", json={"name": "Super Admin"}, headers=headers)
    assert patched.status_code == 204
    pw = await client.patch("/api/v1/profile/password",
                            json={"current_password": "secret12", "new_password": "brandnew1"},
                            headers=headers)
    assert pw.status_code == 204
