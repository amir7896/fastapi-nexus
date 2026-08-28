from typing import Annotated

from fastapi import Depends, Query

from app.schemas.pagination import PaginationQuery


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(
        None,
        max_length=100,
        description="Optional search keyword",
    ),
) -> PaginationQuery:
    normalized_search = search.strip() if search and search.strip() else None
    return PaginationQuery(page=page, limit=limit, search=normalized_search)


PaginationDep = Annotated[PaginationQuery, Depends(get_pagination_params)]
