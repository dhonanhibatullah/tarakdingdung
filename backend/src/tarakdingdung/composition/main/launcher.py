import uvicorn

from tarakdingdung.composition.main.driver import build_app
from tarakdingdung.config.settings import Settings


def run() -> None:
    settings = Settings()
    app = build_app(settings)
    uvicorn.run(app, host=settings.http_host, port=settings.http_port)
