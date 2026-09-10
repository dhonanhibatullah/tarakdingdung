from tarakdingdung.domain.usecases.trading.collection import CollectResult
from tarakdingdung.domain.usecases.trading.engine import CycleResult, CycleStatus
from tarakdingdung.presentation.cron.tasks import collect, engine, snapshot


class FakeLogger:
    def __init__(self) -> None:
        self.messages = []

    def info(self, message, **fields):
        self.messages.append((message, fields))

    def debug(self, message, **fields):
        pass

    def warning(self, message, **fields):
        pass

    def error(self, message, **fields):
        pass


class FakeCollection:
    def __init__(self) -> None:
        self.called = False

    async def collect(self):
        self.called = True
        return CollectResult(failed=[])


class FakeSnapshot:
    def __init__(self) -> None:
        self.called = False

    async def take(self):
        self.called = True
        return type("S", (), {"equity": "1000"})()


class FakeEngine:
    def __init__(self) -> None:
        self.called = False

    async def run_cycle(self):
        self.called = True
        return CycleResult(CycleStatus.EXECUTED)


class FakeContainer:
    def __init__(self) -> None:
        self.collection = FakeCollection()
        self.snapshot = FakeSnapshot()
        self.engine = FakeEngine()
        self.logger = FakeLogger()


async def test_collect_task():
    container = FakeContainer()
    await collect.run(container)
    assert container.collection.called


async def test_snapshot_task():
    container = FakeContainer()
    await snapshot.run(container)
    assert container.snapshot.called


async def test_engine_task():
    container = FakeContainer()
    await engine.run(container)
    assert container.engine.called
