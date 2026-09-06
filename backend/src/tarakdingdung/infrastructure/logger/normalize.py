_JSON_PRIMITIVES = (str, int, float, bool, type(None))


def normalize_meta(meta: dict | None) -> dict:
    if not meta:
        return {}
    normalized: dict = {}
    for key, value in meta.items():
        if isinstance(value, BaseException):
            normalized[key] = str(value)
        elif isinstance(value, _JSON_PRIMITIVES):
            normalized[key] = value
        else:
            normalized[key] = str(value)
    return normalized
