from decimal import Decimal, InvalidOperation

from tarakdingdung.domain.models.error import DomainError, ErrorType


def to_decimal(value, label: str, *, venue: str,
               default: Decimal | None = None) -> Decimal:
    """Parse a venue field into a Decimal, via ``str``.

    Going through ``str`` matters: a venue that sends a JSON number arrives as
    a float, and ``Decimal(float)`` would carry the binary approximation into a
    quantity that becomes an exchange order field.
    """
    if value is None or value == "":
        if default is not None:
            return default
        raise DomainError(f"missing {label} in {venue} response", ErrorType.UPSTREAM)
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise DomainError(f"unreadable {label} in {venue} response",
                          ErrorType.UPSTREAM, exc) from exc
