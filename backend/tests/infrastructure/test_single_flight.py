from tarakdingdung.infrastructure.utility.single_flight.memory import InMemorySingleFlight


async def test_acquire_once_then_false():
    sf = InMemorySingleFlight()
    assert await sf.acquire("cycle") is True
    assert await sf.acquire("cycle") is False


async def test_release_allows_reacquire():
    sf = InMemorySingleFlight()
    assert await sf.acquire("cycle") is True
    await sf.release("cycle")
    assert await sf.acquire("cycle") is True


async def test_distinct_keys_are_independent():
    sf = InMemorySingleFlight()
    assert await sf.acquire("a") is True
    assert await sf.acquire("b") is True
