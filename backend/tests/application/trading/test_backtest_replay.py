from decimal import Decimal

from tarakdingdung.application.trading.backtest.replay import (
    replay_snapshot, synthetic_book,
)
from tarakdingdung.domain.models.algorithm import (
    OrderType, PlannedOrder, Side, TimeInForce,
)
from tarakdingdung.domain.models.market import (
    Candle, MarketSnapshot, Symbol, Venue,
)
from tarakdingdung.infrastructure.algorithm.cost.depth_walk import DepthWalkCostModel

BTC = Symbol(venue=Venue.INDODAX, base="BTC", quote="IDR")


def candle(*, close="100", volume="10", open_time=1_000) -> Candle:
    c = Decimal(close)
    return Candle(open_time=open_time, open=c, high=c, low=c, close=c,
                  volume=Decimal(volume))


def buy(qty="1") -> PlannedOrder:
    return PlannedOrder(symbol=BTC, side=Side.BUY, type=OrderType.LIMIT,
                        quantity=Decimal(qty), price=Decimal("100"),
                        time_in_force=TimeInForce.GTC, client_order_id="tdd1")


# --- synthetic_book -------------------------------------------------------


def test_ladder_straddles_the_close_with_the_bid_below_and_ask_above():
    book = synthetic_book(candle(close="100"), BTC, half_spread=Decimal("0.001"),
                          levels=3, level_step=Decimal("0.001"))
    assert len(book.asks) == 3 and len(book.bids) == 3
    # level 0 sits at the half-spread, each further level one step out
    assert book.asks[0].price == Decimal("100") * Decimal("1.001")
    assert book.asks[1].price == Decimal("100") * Decimal("1.002")
    assert book.bids[0].price == Decimal("100") * Decimal("0.999")
    assert book.asks[0].price > Decimal("100") > book.bids[0].price
    # ask ladder climbs, bid ladder falls
    assert [lv.price for lv in book.asks] == sorted(lv.price for lv in book.asks)
    assert [lv.price for lv in book.bids] == sorted(
        (lv.price for lv in book.bids), reverse=True)


def test_each_level_holds_an_equal_slice_of_bar_volume():
    book = synthetic_book(candle(volume="12"), BTC, levels=4)
    assert [lv.quantity for lv in book.asks] == [Decimal("3")] * 4
    assert sum(lv.quantity for lv in book.bids) == Decimal("12")


def test_a_bar_with_no_volume_makes_every_order_unfillable():
    book = synthetic_book(candle(volume="0"), BTC)
    est = DepthWalkCostModel(fee_rate=Decimal("0.001")).estimate(buy("1"), book)
    assert est.fillable is False


def test_an_order_larger_than_the_bar_traded_is_not_fillable():
    book = synthetic_book(candle(volume="5"), BTC, levels=5)  # total depth 5
    model = DepthWalkCostModel(fee_rate=Decimal("0.001"))
    assert model.estimate(buy("4"), book).fillable is True
    assert model.estimate(buy("6"), book).fillable is False


def test_walking_deeper_levels_accrues_slippage():
    book = synthetic_book(candle(close="100", volume="10"), BTC, levels=5,
                          half_spread=Decimal("0.001"), level_step=Decimal("0.001"))
    model = DepthWalkCostModel(fee_rate=Decimal("0"))
    shallow = model.estimate(buy("1"), book).slippage    # fills at level 0 only
    deep = model.estimate(buy("6"), book).slippage        # walks four levels
    assert shallow == Decimal("0")
    assert deep > Decimal("0")


def test_levels_below_one_collapse_to_a_single_rung():
    book = synthetic_book(candle(volume="10"), BTC, levels=0)
    assert len(book.asks) == 1 and book.asks[0].quantity == Decimal("10")


# --- replay_snapshot ----------------------------------------------------


def _base(**books) -> MarketSnapshot:
    return MarketSnapshot(
        timestamp=2_000,
        candles={BTC: (candle(close="100", volume="8", open_time=1_000),)},
        books=dict(books), last_prices={BTC: Decimal("100")})


def test_fills_the_book_gap_from_the_newest_candle():
    out = replay_snapshot(_base(), levels=4)
    assert BTC in out.books
    assert sum(lv.quantity for lv in out.books[BTC].asks) == Decimal("8")
    # candles and prices pass straight through
    assert out.candles == _base().candles
    assert out.last_prices == {BTC: Decimal("100")}
    assert out.timestamp == 2_000


def test_a_symbol_that_already_has_a_book_keeps_it():
    from tarakdingdung.domain.models.market import BookLevel, OrderBook
    real = OrderBook(symbol=BTC, timestamp=1_000,
                     bids=(BookLevel(price=Decimal("99"), quantity=Decimal("1")),),
                     asks=(BookLevel(price=Decimal("101"), quantity=Decimal("1")),))
    base = MarketSnapshot(timestamp=2_000, candles=_base().candles,
                          books={BTC: real}, last_prices={BTC: Decimal("100")})
    assert replay_snapshot(base).books[BTC] is real


def test_a_symbol_without_candles_gets_no_book():
    base = MarketSnapshot(timestamp=2_000, candles={BTC: ()}, books={},
                          last_prices={})
    assert replay_snapshot(base).books == {}
