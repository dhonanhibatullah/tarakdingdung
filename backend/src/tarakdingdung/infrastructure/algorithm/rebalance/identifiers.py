import hashlib


def client_order_id(
    universe_id: str, timestamp_ms: int, symbol_id: str, side: str
) -> str:
    raw = f"{universe_id}:{timestamp_ms}:{symbol_id}:{side}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
