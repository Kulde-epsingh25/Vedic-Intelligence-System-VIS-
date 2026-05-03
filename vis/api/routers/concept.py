"""
Concept router for conceptual entity lookup.

This module exposes a minimal concept endpoint.
"""

from fastapi import APIRouter, HTTPException

from api.schemas import ConceptResponse
from database.supabase_client import SupabaseClient

router = APIRouter(prefix="/concept", tags=["concept"])


@router.get("/{concept_id}", response_model=ConceptResponse)
async def get_concept(concept_id: str) -> ConceptResponse:
    """
    Fetch a concept by concept_id.

    Args:
        concept_id: Concept identifier.

    Returns:
        ConceptResponse for the requested concept.

    Example:
        >>> response = await get_concept("dharma")
    """
    client = SupabaseClient()
    concept = client.get_concept(concept_id)
    if concept is None:
        raise HTTPException(status_code=404, detail="Concept not found")

    return ConceptResponse(
        concept_id=concept.concept_id,
        name_sa=concept.name_sa,
        name_devanagari=concept.name_devanagari,
        category=concept.category,
        definition_en=concept.definition_en,
        frequency=concept.frequency,
        related_concepts=concept.related_concepts,
    )