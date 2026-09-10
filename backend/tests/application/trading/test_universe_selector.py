from decimal import Decimal

from tarakdingdung.application.trading.universe.selector import select_universe


def _pair(symbol, traded, ticker_id, vol="0", maintenance=0, suspended=0):
    return {
        "id": symbol.lower(),
        "symbol": symbol,
        "base_currency": "idr",
        "traded_currency": traded,
        "traded_currency_unit": traded.upper(),
        "ticker_id": ticker_id,
        "is_maintenance": maintenance,
        "is_market_suspended": suspended,
    }


def _summaries(volumes):
    return {"tickers": {k: {"vol_idr": str(v)} for k, v in volumes.items()}}


def test_selects_top_n_by_volume():
    pairs = [
        _pair("BTCIDR", "btc", "btc_idr"),
        _pair("ETHIDR", "eth", "eth_idr"),
        _pair("SOLIDR", "sol", "sol_idr"),
    ]
    summaries = _summaries({"btc_idr": 100, "eth_idr": 300, "sol_idr": 200})
    result = select_universe(pairs, summaries, top_n=2)
    assert [r["external"] for r in result] == ["ETHIDR", "SOLIDR"]


def test_excludes_stablecoins():
    pairs = [
        _pair("BTCIDR", "btc", "btc_idr"),
        _pair("USDTIDR", "usdt", "usdt_idr"),
        _pair("USDCIDR", "usdc", "usdc_idr"),
    ]
    summaries = _summaries({"btc_idr": 100, "usdt_idr": 9999, "usdc_idr": 8888})
    result = select_universe(pairs, summaries, top_n=10)
    assert [r["external"] for r in result] == ["BTCIDR"]


def test_excludes_maintenance_and_suspended():
    pairs = [
        _pair("BTCIDR", "btc", "btc_idr"),
        _pair("ETHIDR", "eth", "eth_idr", maintenance=1),
        _pair("SOLIDR", "sol", "sol_idr", suspended=1),
    ]
    summaries = _summaries({"btc_idr": 100, "eth_idr": 300, "sol_idr": 200})
    result = select_universe(pairs, summaries, top_n=10)
    assert [r["external"] for r in result] == ["BTCIDR"]


def test_base_quote_mapping():
    pairs = [_pair("BTCIDR", "btc", "btc_idr")]
    result = select_universe(pairs, _summaries({"btc_idr": 100}), top_n=1)
    assert result[0]["base"] == "BTC"
    assert result[0]["quote"] == "IDR"
    assert result[0]["external"] == "BTCIDR"
