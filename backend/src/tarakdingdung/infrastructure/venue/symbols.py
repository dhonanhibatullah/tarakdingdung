"""Symbol translation between the domain and each venue's wire format.

Each venue names the same pair differently — Indodax public uses ``btcidr`` and
its OHLC endpoint ``BTCIDR``, the v2 trade API uses ``BTC_IDR``, Tokocrypto's
``/open/v1`` uses ``BTC_USDT`` while its Binance-standard host uses
``BTCUSDT``. Keeping every one of those conversions here means an adapter never
builds a symbol string inline, and a venue renaming its convention is a change
in one file.
"""

from tarakdingdung.domain.models.market import Symbol


def joined_lower(symbol: Symbol) -> str:
    """``btcidr`` — Indodax public REST ``pair_id``."""
    return f"{symbol.base}{symbol.quote}".lower()


def joined_upper(symbol: Symbol) -> str:
    """``BTCIDR`` — Indodax OHLC, and Tokocrypto's Binance-standard host."""
    return f"{symbol.base}{symbol.quote}".upper()


def underscored(symbol: Symbol) -> str:
    """``BTC_IDR`` — Indodax v2 trade API and Tokocrypto ``/open/v1``."""
    return f"{symbol.base}_{symbol.quote}".upper()
