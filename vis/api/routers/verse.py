"""
Verse router for retrieving verse records.

This module exposes a minimal verse lookup endpoint.
"""

from fastapi import APIRouter, HTTPException

from api.schemas import VerseResponse
from database.supabase_client import SupabaseClient

router = APIRouter(prefix="/verse", tags=["verse"])


@router.get("/{verse_id}", response_model=VerseResponse)
async def get_verse(verse_id: str) -> VerseResponse:
    """
    Fetch a verse by verse_id.

    Args:
        verse_id: Verse identifier.

    Returns:
        VerseResponse for the requested verse.

    Example:
        >>> response = await get_verse("BG.1.1")
    """
    client = SupabaseClient()
    verse = client.get_verse(verse_id)
    if verse is None:
        raise HTTPException(status_code=404, detail="Verse not found")

    return VerseResponse(
        verse_id=verse.verse_id,
        source_text=verse.source_text,
        devanagari=verse.devanagari,
        iast=verse.iast,
        translation_en=verse.translation_en,
        metre=verse.metre,
        era=verse.era,
        speaker_id=verse.speaker_id,
    )