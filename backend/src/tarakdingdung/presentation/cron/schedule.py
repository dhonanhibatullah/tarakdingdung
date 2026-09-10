import asyncio

from tarakdingdung.presentation.cron.tasks import collect, engine, snapshot


async def run_once(container) -> None:
    await collect.run(container)
    await snapshot.run(container)
    await engine.run(container)


async def run_scheduler(container, settings) -> None:
    if not settings.cron_enabled:
        return
    interval = settings.engine_interval_seconds
    while True:
        await run_once(container)
        await asyncio.sleep(interval)
