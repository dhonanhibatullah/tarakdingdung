from tarakdingdung.composition.main.driver import build_app
from tarakdingdung.config.settings import Settings


def test_build_app_registers_routes():
    app = build_app(Settings(_env_file=None))
    paths = set(app.openapi()["paths"].keys())
    for expected in (
        "/api/version",
        "/api/auth/login",
        "/api/profile/me",
        "/api/admin/permissions",
    ):
        assert expected in paths


def test_app_container_is_wired():
    app = build_app(Settings(_env_file=None))
    assert app.state.container.session is not None
    assert app.state.container.token is not None
