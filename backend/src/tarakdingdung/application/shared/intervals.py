from tarakdingdung.domain.models.error import DomainError, ErrorType

_UNIT_MS = {"m": 60_000, "h": 3_600_000, "d": 86_400_000, "w": 604_800_000}


def interval_ms(interval: str) -> int:
    """Milliseconds in a candle interval such as ``15m``, ``1h`` or ``1d``.

    Raises rather than defaulting: an unrecognised interval silently treated as
    an hour would step a backtest at the wrong cadence and produce a report
    that looks fine.
    """
    if len(interval) < 2 or not interval[:-1].isdigit():
        raise DomainError(f"unrecognised interval {interval!r}", ErrorType.BAD_ARGS)
    unit = _UNIT_MS.get(interval[-1])
    if unit is None:
        raise DomainError(f"unrecognised interval unit in {interval!r}", ErrorType.BAD_ARGS)
    return int(interval[:-1]) * unit
