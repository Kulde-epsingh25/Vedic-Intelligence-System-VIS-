"""
Science router for science link browsing.

This module exposes a placeholder science links endpoint.
"""

from fastapi import APIRouter

from api.schemas import ScienceLinkResponse

router = APIRouter(prefix="/science-links", tags=["science"])


@router.get("", response_model=list[ScienceLinkResponse])
async def list_science_links() -> list[ScienceLinkResponse]:
    """
    Return science links.

    Args:
        None.

    Returns:
        An empty list until science-link persistence is wired up.

    Example:
        >>> response = await list_science_links()
    """
    return []