from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class Symbol:
    id: str
    venue: str
    base: str
    quote: str
    external: str


class MembershipState(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    REMOVED = "removed"


@dataclass(frozen=True, slots=True)
class Universe:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class UniverseMembership:
    universe_id: str
    symbol_id: str
    state: MembershipState
    rationale: str = ""
