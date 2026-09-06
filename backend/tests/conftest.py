import pytest

from tarakdingdung.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings()
