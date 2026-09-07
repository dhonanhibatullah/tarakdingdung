from tarakdingdung.domain.models.error import ErrorType

# Errors the venue decided about: the order definitely did not open, so it is
# settled. Anything else — a timeout, a 5xx, a dropped connection — leaves the
# outcome unknown, and treating it as a rejection would let the engine forget
# an order that may be working.
DECIDED = frozenset({ErrorType.BAD_ARGS, ErrorType.VALIDATION, ErrorType.CONFLICT,
                     ErrorType.NOT_FOUND, ErrorType.FORBIDDEN,
                     ErrorType.UNAUTHORIZED})


def is_settled(error_type: ErrorType) -> bool:
    return error_type in DECIDED
