from tarakdingdung.presentation.http.utils.pagination import PaginationParams, page_response


def test_defaults():
    p = PaginationParams()
    assert (p.page, p.limit, p.search) == (1, 10, None)


def test_clamps_limit_and_floors_page():
    assert PaginationParams(page=0, limit=999).limit == 100
    assert PaginationParams(page=0, limit=999).page == 1
    assert PaginationParams(page=-5, limit=0).limit == 10


def test_search_blank_is_none():
    assert PaginationParams(search="   ").search is None
    assert PaginationParams(search=" grace ").search == "grace"


def test_page_response():
    pr = page_response(PaginationParams(page=2, limit=20), total=87)
    assert (pr.page, pr.limit, pr.total_items) == (2, 20, 87)
