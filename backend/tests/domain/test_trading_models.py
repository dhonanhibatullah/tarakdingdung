from decimal import Decimal

import pytest

from tarakdingdung.domain.models.decision import Decision, Weight
from tarakdingdung.domain.models.error import DomainError
from tarakdingdung.domain.models.market import Candle
from tarakdingdung.domain.models.symbol import (
    MembershipState,
    Symbol,
    Universe,
    UniverseMembership,
)


def test_symbol_carries_venue():
    s = Symbol(id="1", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")
    assert s.venue == "indodax"
    assert s.external == "BTCIDR"


def test_membership_states():
    assert MembershipState.PROPOSED.value == "proposed"
    assert MembershipState.APPROVED.value == "approved"
    assert MembershipState.REJECTED.value == "rejected"
    assert MembershipState.REMOVED.value == "removed"


def test_universe_membership_default_rationale():
    m = UniverseMembership(
        universe_id="u1", symbol_id="s1", state=MembershipState.PROPOSED
    )
    assert m.rationale == ""


def test_candle_has_no_validation():
    c = Candle(
        symbol_id="s1",
        open_time_ms=1,
        open=Decimal("0"),
        high=Decimal("-1"),
        low=Decimal("0"),
        close=Decimal("0"),
        volume=Decimal("0"),
    )
    assert c.high == Decimal("-1")


def test_decision_rejects_negative_weights():
    with pytest.raises(DomainError):
        Decision(
            id="d1",
            universe_id="u1",
            as_of_ms=1,
            weights=[Weight(symbol_id="s1", weight=-0.1)],
            reasoning="",
            confidence=0.5,
            traces={},
            prompt="",
            raw_response="",
            status="valid",
        )


def test_decision_rejects_over_one_sum():
    with pytest.raises(DomainError):
        Decision(
            id="d1",
            universe_id="u1",
            as_of_ms=1,
            weights=[Weight(symbol_id="s1", weight=0.7), Weight(symbol_id="s2", weight=0.5)],
            reasoning="",
            confidence=0.5,
            traces={},
            prompt="",
            raw_response="",
            status="valid",
        )


def test_decision_accepts_valid_weights():
    d = Decision(
        id="d1",
        universe_id="u1",
        as_of_ms=1,
        weights=[Weight(symbol_id="s1", weight=0.7)],
        reasoning="r",
        confidence=0.5,
        traces={},
        prompt="p",
        raw_response="j",
        status="valid",
    )
    assert d.status == "valid"


def test_universe_model():
    u = Universe(id="u1", name="default")
    assert u.name == "default"
