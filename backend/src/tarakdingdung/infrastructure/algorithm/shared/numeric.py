from decimal import Decimal


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Largest multiple of ``step`` not exceeding ``value``.

    A zero or non-finite step means the venue imposes no granularity, so the
    value passes through untouched.
    """
    if not step.is_finite() or step <= 0:
        return value
    return (value // step) * step


def ceil_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Smallest multiple of ``step`` not below ``value``."""
    if not step.is_finite() or step <= 0:
        return value
    floored = (value // step) * step
    return floored if floored == value else floored + step
