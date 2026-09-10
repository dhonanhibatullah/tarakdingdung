from tarakdingdung.config.settings import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("TRDD_BE_POSTGRES_DATABASE", "testdb")
    monkeypatch.setenv("TRDD_BE_LLM_MODEL", "deepseek-v4-pro")
    s = Settings()
    assert s.postgres_database == "testdb"
    assert s.llm_model == "deepseek-v4-pro"


def test_postgres_dsn():
    s = Settings(
        postgres_username="u",
        postgres_password="p",
        postgres_host="h",
        postgres_port=5432,
        postgres_database="d",
    )
    assert s.postgres_dsn == "postgresql+asyncpg://u:p@h:5432/d"


def test_news_sources_list():
    s = Settings(news_sources="https://a.com, https://b.com")
    assert s.news_sources_list == ["https://a.com", "https://b.com"]


def test_news_sources_list_empty():
    assert Settings(news_sources="").news_sources_list == []


def test_defaults():
    s = Settings(_env_file=None)
    assert s.cron_enabled is False
    assert s.engine_interval_seconds == 86400
