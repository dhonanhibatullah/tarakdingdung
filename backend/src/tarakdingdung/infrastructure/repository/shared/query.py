def normalize_limit(limit: int) -> int:
    return max(limit, 0)


def normalize_offset(page: int, limit: int) -> int:
    if page <= 1 or limit <= 0:
        return 0
    return (page - 1) * limit


def search_pattern(search: str | None) -> str | None:
    if search is None or not search.strip():
        return None
    escaped = (
        search.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"
