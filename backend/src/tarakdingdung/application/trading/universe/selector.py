from decimal import Decimal

STABLECOINS = {
    "usdt",
    "usdc",
    "dai",
    "busd",
    "tusd",
    "usdp",
    "usdd",
    "frax",
    "usd",
    "fdusd",
    "gusd",
    "usdk",
}


def select_universe(
    pairs: list[dict],
    summaries: dict,
    top_n: int,
    stablecoins: set[str] | None = None,
) -> list[dict]:
    stablecoins = stablecoins if stablecoins is not None else STABLECOINS
    tickers = summaries.get("tickers", {})

    rows: list[dict] = []
    for pair in pairs:
        if pair.get("is_maintenance") == 1 or pair.get("is_market_suspended") == 1:
            continue

        traded = str(pair.get("traded_currency", "")).lower()
        if traded in stablecoins:
            continue

        ticker = tickers.get(pair.get("ticker_id", ""), {})
        try:
            volume = Decimal(str(ticker.get("vol_idr", "0")))
        except Exception:
            volume = Decimal("0")

        rows.append(
            {
                "venue": "indodax",
                "base": pair.get("traded_currency_unit") or traded.upper(),
                "quote": str(pair.get("base_currency", "idr")).upper(),
                "external": pair.get("symbol") or str(pair.get("id", "")).upper(),
                "volume": volume,
            }
        )

    rows.sort(key=lambda r: r["volume"], reverse=True)
    return rows[:top_n]
