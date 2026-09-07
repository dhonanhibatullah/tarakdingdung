"""Cadences and the loop that honours them.

Scheduling lives here rather than in a usecase so the usecases stay ignorant of
time: each exposes a single step, and a test drives it directly with no clock.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from tarakdingdung.domain.contracts.logger.leveled import LeveledLogger

TAG = "cron/schedule"


@dataclass(frozen=True, slots=True)
class Task:
    name: str
    interval_seconds: int
    run: Callable[[], Awaitable[None]]


async def run_task(task: Task, *, logger: LeveledLogger) -> None:
    """Run one task forever at its cadence.

    Every failure is caught and the loop continues. A scheduler that died on an
    exception would stop collecting data — and a gap in history is permanent in
    a way a failed pass is not.

    The sleep follows the work rather than running alongside it, so a slow pass
    delays the next one instead of overlapping with it. The engine additionally
    holds a database lock, so even a badly misconfigured cadence cannot produce
    two concurrent cycles for one strategy.
    """
    while True:
        try:
            await task.run()
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - a task must never kill the loop
            await logger.error(TAG, f"task {task.name} raised",
                               {"err": str(err), "task": task.name})
        await asyncio.sleep(task.interval_seconds)


def start(tasks: tuple[Task, ...], *, logger: LeveledLogger) -> list[asyncio.Task]:
    return [asyncio.create_task(run_task(task, logger=logger), name=f"cron:{task.name}")
            for task in tasks]


async def stop(running: list[asyncio.Task]) -> None:
    for task in running:
        task.cancel()
    await asyncio.gather(*running, return_exceptions=True)
