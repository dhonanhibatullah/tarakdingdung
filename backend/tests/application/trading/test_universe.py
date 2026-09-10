from tarakdingdung.application.trading.universe.usecase import UniverseUsecase
from tarakdingdung.domain.models.symbol import MembershipState, Symbol
from tests.fakes.trading import InMemorySymbolRepository, InMemoryUniverseRepository


async def test_propose_creates_symbol_and_membership():
    symbols = InMemorySymbolRepository()
    universes = InMemoryUniverseRepository()
    uc = UniverseUsecase(universes, symbols)

    membership = await uc.propose(
        "u1", Symbol(id="", venue="indodax", base="BTC", quote="IDR", external="BTCIDR"), "liquid"
    )

    assert membership.state is MembershipState.PROPOSED
    assert len(symbols.created) == 1
    assert len(universes.memberships) == 1


async def test_propose_reuses_existing_symbol():
    symbols = InMemorySymbolRepository()
    existing = await symbols.create(
        Symbol(id="", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")
    )
    universes = InMemoryUniverseRepository()
    uc = UniverseUsecase(universes, symbols)

    membership = await uc.propose(
        "u1", Symbol(id="", venue="indodax", base="BTC", quote="IDR", external="BTCIDR")
    )

    assert membership.symbol_id == existing.id
    assert len(symbols.created) == 1


async def test_approve_and_reject():
    universes = InMemoryUniverseRepository()
    uc = UniverseUsecase(universes, InMemorySymbolRepository())

    approved = await uc.approve("u1", "s1", "liquid")
    rejected = await uc.reject("u1", "s2", "illiquid")

    assert approved.state is MembershipState.APPROVED
    assert rejected.state is MembershipState.REJECTED
