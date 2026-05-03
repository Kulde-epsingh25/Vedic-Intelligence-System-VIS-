"""
API schemas for request/response validation.

This module defines Pydantic models for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SearchRequest(BaseModel):
    """Search request schema."""

    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, description="Maximum results")
    source_text: Optional[str] = Field(None, description="Filter by source text")
    era: Optional[str] = Field(None, description="Filter by era")
    character: Optional[str] = Field(None, description="Filter by character")


class VerseResponse(BaseModel):
    """Verse response schema."""

    verse_id: str
    source_text: str
    devanagari: str
    iast: str
    translation_en: Optional[str] = None
    metre: Optional[str] = None
    era: Optional[str] = None
    speaker_id: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response schema."""

    results: List[VerseResponse]
    count: int
    query: str


class AskRequest(BaseModel):
    """Question answering request schema."""

    question: str = Field(..., description="Question about Sanskrit texts")
    language: str = Field(default="en", description="Response language (en/hi)")


class ScienceLinkResponse(BaseModel):
    """Science link response schema."""

    domain: str
    modern_title: str
    confidence: float
    url: Optional[str] = None


class AnswerResponse(BaseModel):
    """Question answering response schema."""

    answer: str
    source_verses: List[VerseResponse]
    characters_mentioned: List[str]
    science_links: List[ScienceLinkResponse]
    confidence: float


class CharacterResponse(BaseModel):
    """Character response schema."""

    char_id: str
    name_sa: str
    name_devanagari: Optional[str]
    char_type: Optional[str]
    appears_in: List[str]
    verse_count: int
    attributes: List[str]
    description_en: Optional[str]


class ConceptResponse(BaseModel):
    """Concept response schema."""

    concept_id: str
    name_sa: str
    name_devanagari: Optional[str]
    category: Optional[str]
    definition_en: Optional[str]
    frequency: int
    related_concepts: List[str]
