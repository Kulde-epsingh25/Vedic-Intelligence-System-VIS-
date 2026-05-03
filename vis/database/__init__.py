"""
Database __init__.py — exposes database clients and models.
"""

from .models import (
    VerseRecord,
    WordRecord,
    CharacterRecord,
    ConceptRecord,
    EventRecord,
    RelationRecord,
    ScienceLinkRecord,
    AnswerRecord,
)
from .supabase_client import SupabaseClient

__all__ = [
    "VerseRecord",
    "WordRecord",
    "CharacterRecord",
    "ConceptRecord",
    "EventRecord",
    "RelationRecord",
    "ScienceLinkRecord",
    "AnswerRecord",
    "SupabaseClient",
]
