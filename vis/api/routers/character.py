"""
Character router for entity lookup.

This module exposes a minimal character endpoint.
"""

from fastapi import APIRouter, HTTPException

from api.schemas import CharacterResponse
from database.supabase_client import SupabaseClient

router = APIRouter(prefix="/character", tags=["character"])


@router.get("/{char_id}", response_model=CharacterResponse)
async def get_character(char_id: str) -> CharacterResponse:
    """
    Fetch a character by char_id.

    Args:
        char_id: Character identifier.

    Returns:
        CharacterResponse for the requested character.

    Example:
        >>> response = await get_character("arjuna")
    """
    client = SupabaseClient()
    character = client.get_character(char_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    return CharacterResponse(
        char_id=character.char_id,
        name_sa=character.name_sa,
        name_devanagari=character.name_devanagari,
        char_type=character.char_type,
        appears_in=character.appears_in,
        verse_count=character.verse_count,
        attributes=character.attributes,
        description_en=character.description_en,
    )