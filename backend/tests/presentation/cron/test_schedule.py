from tarakdingdung.presentation.cron.schedule import run_once, run_scheduler


class FakeSettings:
    def __init__(self, cron_enabled, interval=86400) -> None:
        self.cron_enabled = cron_enabled
        self.engine_interval_seconds = interval


class FakeContainer:
    def __init__(self) -> None:
        self.ran = []


async def test_run_once_calls_all_tasks(monkeypatch):
    calls = []

    async def fake_collect(container):
        calls.append("collect")

    async def fake_snapshot(container):
        calls.append("snapshot")

    async def fake_engine(container):
        calls.append("engine")

    monkeypatch.setattr("tarakdingdung.presentation.cron.schedule.collect.run", fake_collect)
    monkeypatch.setattr("tarakdingdung.presentation.cron.schedule.snapshot.run", fake_snapshot)
    monkeypatch.setattr("tarakdingdung.presentation.cron.schedule.engine.run", fake_engine)

    await run_once(FakeContainer())
    assert calls == ["collect", "snapshot", "engine"]


async def test_scheduler_disabled_returns_immediately(monkeypatch):
    calls = []

    async def fake_once(container):
        calls.append("once")

    monkeypatch.setattr("tarakdingdung.presentation.cron.schedule.run_once", fake_once)

    await run_scheduler(FakeContainer(), FakeSettings(cron_enabled=False))
    assert calls == []
