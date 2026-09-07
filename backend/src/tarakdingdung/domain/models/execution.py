from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from tarakdingdung.domain.models.algorithm import PlannedOrder
from tarakdingdung.domain.models.market import Symbol, Venue
from tarakdingdung.domain.models.performance import Fill


class OrderState(StrEnum):
    """What we know about an order, which is not always what is true.

    ``UNCONFIRMED`` is the important one: the submission failed in transport,
    so the order may or may not exist at the venue. It is neither accepted nor
    rejected, and it must be reconciled by client order id rather than retried.
    """

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    UNCONFIRMED = "UNCONFIRMED"


@dataclass(frozen=True, slots=True)
class OrderAck:
    order: PlannedOrder
    client_order_id: str
    venue_order_id: str


@dataclass(frozen=True, slots=True)
class OrderRejection:
    order: PlannedOrder
    client_order_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class UnconfirmedOrder:
    order: PlannedOrder
    client_order_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """The outcome of one submission batch.

    Every submitted order appears exactly once across the three tuples. An
    order that vanished from the result would be one nothing will ever
    reconcile.
    """

    accepted: tuple[OrderAck, ...]
    rejected: tuple[OrderRejection, ...]
    unconfirmed: tuple[UnconfirmedOrder, ...]
    fills: tuple[Fill, ...]

    @property
    def is_complete(self) -> bool:
        return not self.unconfirmed


@dataclass(frozen=True, slots=True)
class Discrepancy:
    """A gap between what the venue holds and what we recorded.

    The most important thing a reconciliation can report, so it is returned as
    data rather than raised: a cron that swallowed it into a log line would
    leave the engine sizing against a portfolio that does not exist.
    """

    symbol: Symbol
    expected: Decimal
    actual: Decimal

    @property
    def difference(self) -> Decimal:
        return self.actual - self.expected


@dataclass(frozen=True, slots=True)
class CollectionFailure:
    """One symbol that could not be collected this pass.

    Returned rather than raised so that one venue being down shrinks a poll
    instead of aborting it — otherwise an outage on one exchange permanently
    gaps the other's history.
    """

    venue: Venue
    symbol: Symbol | None
    reason: str
