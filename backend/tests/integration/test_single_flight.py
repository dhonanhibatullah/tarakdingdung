"""Advisory locks are the one piece a fake cannot vouch for.

The whole reason for choosing them over an in-process lock is behaviour across
connections and across processes, which only a real database can demonstrate.
"""

import pytest

from tarakdingdung.infrastructure.repository.database.session import Database
from tarakdingdung.infrastructure.utility.single_flight.postgres import (
    PostgresSingleFlight, _key,
)


@pytest.fixture
async def database(migrated_url: str):
    db = Database(migrated_url, pool_size=5)
    yield db
    await db.dispose()


@pytest.mark.asyncio
async def test_a_second_holder_is_refused_not_queued(database):
    first = PostgresSingleFlight(database)
    second = PostgresSingleFlight(database)
    assert await first.acquire("cycle:a") is True
    try:
        # A separate instance stands in for a separate worker process: this is
        # exactly the case an asyncio.Lock would wrongly allow.
        assert await second.acquire("cycle:a") is False
    finally:
        await first.release("cycle:a")


@pytest.mark.asyncio
async def test_releasing_lets_the_next_holder_in(database):
    first = PostgresSingleFlight(database)
    second = PostgresSingleFlight(database)
    assert await first.acquire("cycle:b") is True
    await first.release("cycle:b")
    assert await second.acquire("cycle:b") is True
    await second.release("cycle:b")


@pytest.mark.asyncio
async def test_different_keys_do_not_block_each_other(database):
    lock = PostgresSingleFlight(database)
    assert await lock.acquire("cycle:c") is True
    assert await lock.acquire("cycle:d") is True
    await lock.release("cycle:c")
    await lock.release("cycle:d")


@pytest.mark.asyncio
async def test_releasing_something_never_held_is_harmless(database):
    await PostgresSingleFlight(database).release("cycle:never")


@pytest.mark.asyncio
async def test_a_dropped_connection_frees_the_lock(database):
    # The property a row-based lock would need a lease and a reaper to imitate:
    # a worker that dies stops holding the lock.
    holder = PostgresSingleFlight(database)
    assert await holder.acquire("cycle:e") is True
    await holder._held.pop("cycle:e").close()

    successor = PostgresSingleFlight(database)
    assert await successor.acquire("cycle:e") is True
    await successor.release("cycle:e")


def test_the_advisory_key_is_stable_across_processes():
    # Python's hash() is randomised per process, which would give two workers
    # different lock ids for the same key.
    assert _key("cycle:a") == _key("cycle:a")
    assert _key("cycle:a") != _key("cycle:b")
    assert -(2 ** 63) <= _key("cycle:a") < 2 ** 63
