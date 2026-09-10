import asyncio

from tarakdingdung.presentation.cron.tasks import collect, engine, snapshot, summarize


async def run_once(container) -> None:
    await collect.run(container)
    await summarize.run(container)
    await engine.run(container)
    await snapshot.run(container)


async def run_scheduler(container, settings, stop_event: asyncio.Event) -> None:
    if not settings.cron_enabled:
        return
    interval = settings.engine_interval_seconds
    while not stop_event.is_set():
        await run_once(container)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
