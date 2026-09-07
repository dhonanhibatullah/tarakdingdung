from decimal import Decimal

from tarakdingdung.infrastructure.algorithm.universe.liquidity import LiquidityUniverseSelector
from tarakdingdung.infrastructure.algorithm.universe.static import StaticUniverseSelector
from tests.infrastructure.algorithm.conformance import BTC_IDX, ETH_IDX, ETH_TKO, book
from tests.infrastructure.algorithm.fixtures import level, order_book, snapshot


def test_static_universe_drops_symbols_absent_from_the_snapshot():
    selector = StaticUniverseSelector((BTC_IDX, ETH_IDX))
    assert selector.select(snapshot(prices={BTC_IDX: Decimal("100")})) == (BTC_IDX,)


def test_static_universe_is_deterministically_ordered():
    selector = StaticUniverseSelector((ETH_TKO, BTC_IDX, ETH_IDX))
    prices = {s: Decimal("100") for s in (ETH_TKO, BTC_IDX, ETH_IDX)}
    assert selector.select(snapshot(prices=prices)) == (BTC_IDX, ETH_IDX, ETH_TKO)


def test_liquidity_universe_excludes_thin_books():
    selector = LiquidityUniverseSelector(min_book_notional=Decimal("1000"))
    selected = selector.select(snapshot(
        books={BTC_IDX: book(BTC_IDX, levels=5, size="10"),
               ETH_IDX: book(ETH_IDX, levels=1, size="0.001")},
        prices={BTC_IDX: Decimal("100"), ETH_IDX: Decimal("100")}))
    assert selected == (BTC_IDX,)


def test_liquidity_universe_judges_the_thinner_side():
    # Deep bids do not help if we cannot buy back out of the position.
    lopsided = order_book(BTC_IDX, bids=[level("100", "1000")],
                          asks=[level("101", "0.001")])
    selector = LiquidityUniverseSelector(min_book_notional=Decimal("1000"))
    assert selector.select(snapshot(books={BTC_IDX: lopsided},
                                    prices={BTC_IDX: Decimal("100")})) == ()


def test_liquidity_universe_ignores_depth_beyond_the_level_limit():
    shallow = order_book(BTC_IDX,
                         bids=[level("100", "1"), level("99", "1000")],
                         asks=[level("101", "1"), level("102", "1000")])
    selector = LiquidityUniverseSelector(min_book_notional=Decimal("1000"),
                                         depth_levels=1)
    assert selector.select(snapshot(books={BTC_IDX: shallow},
                                    prices={BTC_IDX: Decimal("100")})) == ()
