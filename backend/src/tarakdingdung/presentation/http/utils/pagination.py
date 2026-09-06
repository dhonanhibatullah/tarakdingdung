from dataclasses import dataclass

from fastapi import Query

from tarakdingdung.presentation.http.schemas.response import PageResponse

_DEFAULT_PAGE, _DEFAULT_LIMIT, _MAX_LIMIT = 1, 10, 100


@dataclass(slots=True)
class PaginationParams:
    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    search: str | None = None

    def __post_init__(self) -> None:
        if self.page < 1:
            self.page = _DEFAULT_PAGE
        if self.limit < 1:
            self.limit = _DEFAULT_LIMIT
        elif self.limit > _MAX_LIMIT:
            self.limit = _MAX_LIMIT
        if self.search is not None:
            self.search = self.search.strip() or None


def pagination_params(
    page: int = Query(_DEFAULT_PAGE),
    limit: int = Query(_DEFAULT_LIMIT),
    search: str | None = Query(None),
) -> PaginationParams:
    return PaginationParams(page=page, limit=limit, search=search)


def page_response(params: PaginationParams, total: int) -> PageResponse:
    return PageResponse(page=params.page, limit=params.limit, total_items=total)
