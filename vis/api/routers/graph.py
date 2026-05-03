"""
Graph router for knowledge graph path lookups.

This module exposes a minimal graph endpoint.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/path")
async def graph_path() -> dict[str, str]:
    """
    Return a placeholder graph path payload.

    Returns:
        Placeholder graph response.

    Example:
        >>> response = await graph_path()
    """
    return {"status": "not_implemented"}