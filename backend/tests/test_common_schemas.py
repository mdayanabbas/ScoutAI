from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams


def test_paginated_response_shape_works():
    response = PaginatedResponse[str](
        items=["a"],
        total=2,
        page=1,
        page_size=1,
        has_next=True,
        has_prev=False,
    )

    assert response.model_dump() == {
        "items": ["a"],
        "total": 2,
        "page": 1,
        "page_size": 1,
        "has_next": True,
        "has_prev": False,
    }


def test_common_schema_defaults():
    assert PaginationParams().page == 1
    assert MessageResponse(message="ok").message == "ok"
