import hashlib
from uuid import UUID

from tarakdingdung.domain.models.algorithm import Side
from tarakdingdung.domain.models.market import Symbol

_PREFIX = "tdd"
_DIGEST_CHARS = 16


def client_order_id(*, strategy_id: UUID, timestamp: int, symbol: Symbol,
                    side: Side) -> str:
    """A deterministic, venue-safe id for one order in one cycle.

    Deterministic so that recomputing a cycle after a crash produces the same
    ids: the venue then rejects the duplicate instead of opening a second
    position. That is the whole safety mechanism behind never retrying an
    ambiguous submission.

    Kept short and alphanumeric because both venues bound the field — Binance
    style on Tokocrypto, ``client_order_id`` on Indodax.
    """
    material = f"{strategy_id}:{timestamp}:{symbol.venue}:{symbol.base}:{symbol.quote}:{side}"
    digest = hashlib.sha256(material.encode()).hexdigest()
    return f"{_PREFIX}{digest[:_DIGEST_CHARS]}"
