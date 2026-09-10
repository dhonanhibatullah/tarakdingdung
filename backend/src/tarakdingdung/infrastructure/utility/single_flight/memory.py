from tarakdingdung.domain.contracts.utility.single_flight import SingleFlight


class InMemorySingleFlight(SingleFlight):
    def __init__(self) -> None:
        self._keys: set[str] = set()

    async def acquire(self, key: str) -> bool:
        if key in self._keys:
            return False
        self._keys.add(key)
        return True

    async def release(self, key: str) -> None:
        self._keys.discard(key)
