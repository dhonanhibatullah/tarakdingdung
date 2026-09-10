from tarakdingdung.infrastructure.utility.clock.system import SystemClock


def test_system_clock_returns_int_ms():
    c = SystemClock()
    v = c.now_ms()
    assert isinstance(v, int)
    assert v > 0
