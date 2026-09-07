import uvicorn
from fastapi import FastAPI

from tarakdingdung.composition.main.application import build_container
from tarakdingdung.composition.main.cron import build_tasks
from tarakdingdung.composition.main.driver import build_driver
from tarakdingdung.composition.main.infrastructure import build_infrastructure
from tarakdingdung.composition.main.presentation import build_app
from tarakdingdung.config.settings import Settings
from tarakdingdung.presentation.cron import schedule


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    driver = build_driver(settings)
    infra = build_infrastructure(driver, settings)
    container = build_container(infra, settings)
    app = build_app(container, settings)
    app.state.driver = driver
    app.state.on_startup = _start_cron(container, infra, settings)
    return app


def _start_cron(container, infra, settings: Settings):
    """Return a startup hook that runs the cron, and a matching shutdown.

    Disabled by default: a process that starts trading merely because it booted
    is not something anyone should be able to do by accident.
    """
    async def start():
        if not settings.cron_enabled:
            return None
        running = schedule.start(build_tasks(container, infra, settings),
                                 logger=infra.logger)

        async def stop():
            # Cancelled and awaited, so a cycle in flight unwinds rather than
            # being dropped mid-submission.
            await schedule.stop(running)

        return stop
    return start


def run() -> None:
    settings = Settings()
    uvicorn.run("tarakdingdung.main:app", host=settings.http_host, port=settings.http_port)
