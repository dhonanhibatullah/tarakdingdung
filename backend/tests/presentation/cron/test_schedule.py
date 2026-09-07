import asyncio

import pytest

from tarakdingdung.presentation.cron.schedule import Task, run_task, start, stop
from tests.fakes.utilities import NullLogger


class RecordingLogger(NullLogger):
    def __init__(self) -> None:
        self.errors: list[str] = []

    async def error(self, tag, message, meta) -> None:
        self.errors.append(message)


async def test_a_failing_task_does_not_kill_the_loop():
    # A scheduler that died on an exception would stop collecting data, and a
    # gap in history is permanent in a way a failed pass is not.
    calls = []
    logger = RecordingLogger()

    async def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("venue down")

    task = asyncio.create_task(run_task(
        Task(name="flaky", interval_seconds=0, run=flaky), logger=logger))
    await asyncio.sleep(0.01)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert len(calls) > 1, "the loop stopped after the first failure"
    assert logger.errors


async def test_cancellation_propagates_rather_than_being_swallowed():
    async def forever():
        await asyncio.sleep(10)

    task = asyncio.create_task(run_task(
        Task(name="slow", interval_seconds=0, run=forever), logger=NullLogger()))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_start_and_stop_manage_every_task():
    ran = []

    async def work():
        ran.append(1)

    running = start((Task(name="a", interval_seconds=0, run=work),
                     Task(name="b", interval_seconds=0, run=work)),
                    logger=NullLogger())
    await asyncio.sleep(0.01)
    await stop(running)

    assert ran
    assert all(task.done() for task in running)


async def test_the_sleep_follows_the_work():
    # Sleeping after rather than alongside means a slow pass delays the next
    # one instead of overlapping with it.
    order = []

    async def slow():
        order.append("start")
        await asyncio.sleep(0.005)
        order.append("end")

    task = asyncio.create_task(run_task(
        Task(name="slow", interval_seconds=0, run=slow), logger=NullLogger()))
    await asyncio.sleep(0.02)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    assert order[:2] == ["start", "end"]
