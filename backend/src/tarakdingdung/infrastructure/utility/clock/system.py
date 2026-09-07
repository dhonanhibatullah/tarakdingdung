import time

from tarakdingdung.domain.contracts.utility.clock import Clock


class SystemClock(Clock):
    """Wall-clock milliseconds from the host.

    Note both venues reject a request whose timestamp drifts outside their
    receive window, so the host's own clock discipline is a production
    dependency, not an implementation detail. This is the seam where a
    server-time offset would be applied if drift becomes a problem.
    """

    async def now_ms(self) -> int:
        return int(time.time() * 1000)
