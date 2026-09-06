import pytest

from tarakdingdung.config.settings import Settings


def test_defaults_match_spec():
    s = Settings()
    assert s.app_name == "tarakdingdung"
    assert s.token_access_ttl_seconds == 900
    assert s.password_bcrypt_cost == 12
    assert s.http_cors_allowed_origins == ["*"]


def test_env_prefix_is_trdd_be(monkeypatch):
    monkeypatch.setenv("TRDD_BE_POSTGRES_DATABASE", "custom_db")
    monkeypatch.setenv("TRDD_BE_TOKEN_ACCESS_TTL_SECONDS", "60")
    s = Settings()
    assert s.postgres_database == "custom_db"
    assert s.token_access_ttl_seconds == 60


def test_postgres_dsn_is_asyncpg():
    s = Settings(postgres_username="u", postgres_password="p",
                 postgres_host="h", postgres_port=1234, postgres_database="d")
    assert s.postgres_dsn == "postgresql+asyncpg://u:p@h:1234/d"


@pytest.mark.parametrize("raw,expected", [
    ("a.com,b.com", ["a.com", "b.com"]),
    ("  x.com , y.com ", ["x.com", "y.com"]),
])
def test_cors_origins_parsed_from_csv(monkeypatch, raw, expected):
    monkeypatch.setenv("TRDD_BE_HTTP_CORS_ALLOWED_ORIGINS", raw)
    assert Settings().http_cors_allowed_origins == expected
