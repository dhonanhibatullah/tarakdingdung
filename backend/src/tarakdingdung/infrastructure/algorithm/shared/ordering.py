from tarakdingdung.domain.models.market import Symbol


def symbol_key(symbol: Symbol) -> tuple[str, str, str]:
    """Total order over symbols.

    Blocks that rank or truncate break ties by position, so an unstable
    ordering would make an otherwise deterministic backtest irreproducible.
    """
    return (symbol.venue, symbol.base, symbol.quote)
