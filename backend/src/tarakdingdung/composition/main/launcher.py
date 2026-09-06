import uvicorn
from fastapi import FastAPI

from tarakdingdung.composition.main.application import build_container
from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.composition.main.presentation import build_app
from tarakdingdung.config.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    container = build_container(infra)
    app = build_app(container, settings)
    app.state.driver = driver
    return app


def run() -> None:
    settings = Settings()
    uvicorn.run("tarakdingdung.main:app", host=settings.http_host, port=settings.http_port)
