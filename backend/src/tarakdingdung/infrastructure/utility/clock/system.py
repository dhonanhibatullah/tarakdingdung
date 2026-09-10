import time

from tarakdingdung.domain.contracts.utility.clock import Clock


class SystemClock(Clock):
    def now_ms(self) -> int:
        return int(time.time() * 1000)
