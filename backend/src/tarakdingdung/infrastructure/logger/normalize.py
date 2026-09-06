def normalize_meta(meta: dict | None) -> dict:
    if not meta:
        return {}
    normalized: dict = {}
    for key, value in meta.items():
        normalized[key] = str(value) if isinstance(value, BaseException) else value
    return normalized
