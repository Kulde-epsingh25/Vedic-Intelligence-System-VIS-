"""
Search router for semantic verse lookup.

This module exposes the search endpoint used by the API.
"""

from fastapi import APIRouter

from api.schemas import SearchRequest, SearchResponse

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """
    Return an empty search response placeholder.

    Args:
        request: Search request payload.

    Returns:
        SearchResponse with zero results.

    Example:
        >>> payload = SearchRequest(query="dharma")
        >>> response = await search(payload)
    """
    return SearchResponse(results=[], count=0, query=request.query)