from typing import Annotated

from fastapi import Query

from app.schemas.pagination import PaginationQuery

# Use these as the first parameters on paginated GET endpoints so Swagger
# shows page / limit / search at the top of the query params list.
# Defaults must be set with `=` on the endpoint parameter (FastAPI rule).
PageQuery = Annotated[
    int,
    Query(ge=1, description="Page number (starts at 1)"),
]
LimitQuery = Annotated[
    int,
    Query(ge=1, le=100, description="Items per page"),
]
SearchQuery = Annotated[
    str | None,
    Query(max_length=100, description="Optional search keyword"),
]


def build_pagination(
    page: int,
    limit: int,
    search: str | None = None,
) -> PaginationQuery:
    return PaginationQuery(page=page, limit=limit, search=search)
