def _login(client):
    resp = client.post("/api/auth/login", json={"username": "super", "password": "pw"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_and_me(client):
    token = _login(client)
    resp = client.get("/api/profile/me", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "super"
    assert "admin" in body["permissions"]


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "super", "password": "bad"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/profile/me")
    assert resp.status_code == 401


def test_admin_permission_endpoint_authorized(client):
    token = _login(client)
    resp = client.post(
        "/api/admin/permissions",
        json={"name": "trade:get"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "trade:get"


def test_version_endpoint(client):
    resp = client.get("/api/version")
    assert resp.status_code == 200
    assert resp.json()["name"] == "tarakdingdung"
