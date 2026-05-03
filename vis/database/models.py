"""
Pydantic models for database schema.

These models define the structure of all data that maps to Supabase tables.
Each model corresponds to a table and includes validation logic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID


@dataclass
class VerseRecord:
    """Single Sanskrit verse with metadata."""
    
    verse_id: str                    # "RV.1.1.1", "BG.2.47"
    source_text: str                 # "Rigveda", "Bhagavad Gita"
    devanagari: str
    iast: str
    slp1: Optional[str] = None
    translation_en: Optional[str] = None
    translation_hi: Optional[str] = None
    book: Optional[int] = None
    chapter: Optional[int] = None
    verse_num: Optional[int] = None
    speaker_id: Optional[str] = None
    addressed_to: Optional[str] = None
    metre: Optional[str] = None      # Anushtubh, Trishtubh, Jagati
    era: Optional[str] = None        # Vedic, Upanishadic, Classical
    topics: List[str] = field(default_factory=list)  # concept_ids
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None

    def validate(self) -> None:
        """Validate verse record."""
        if not self.verse_id or not self.source_text:
            raise ValueError("verse_id and source_text are required")
        if not self.devanagari and not self.iast:
            raise ValueError("Either devanagari or iast must be provided")


@dataclass
class WordRecord:
    """Single word/pada with linguistic annotations."""
    
    pada_id: str                     # "RV.1.1.1_0", "BG.2.47_5"
    verse_id: str                    # Foreign key
    position: int                    # Word order in verse
    surface_form: str                # Exact text as it appears
    dhatu: Optional[str] = None      # Root (√gam)
    stem: Optional[str] = None
    vibhakti: Optional[int] = None   # 1-8 (case)
    vachana: Optional[str] = None    # Singular, Dual, Plural
    linga: Optional[str] = None      # Masculine, Feminine, Neuter
    purusha: Optional[str] = None    # 1st, 2nd, 3rd person
    lakara: Optional[str] = None     # Tense/mood for verbs
    meaning_en: Optional[str] = None
    frequency: int = 1
    created_at: Optional[datetime] = None


@dataclass
class CharacterRecord:
    """Sanskrit character/entity."""
    
    char_id: str                     # "rama", "krishna"
    name_sa: str                     # Sanskrit name (IAST)
    name_devanagari: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    char_type: Optional[str] = None  # Deva, Asura, Human, Rishi
    gender: Optional[str] = None
    appears_in: List[str] = field(default_factory=list)  # source_texts
    verse_count: int = 0
    attributes: List[str] = field(default_factory=list)  # weapons, epithets
    description_en: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None


@dataclass
class ConceptRecord:
    """Sanskrit concept/idea."""
    
    concept_id: str                  # "dharma", "karma", "atman"
    name_sa: str
    name_devanagari: Optional[str] = None
    category: Optional[str] = None   # Philosophy, Science, Ritual, Social
    definition_sa: Optional[str] = None
    definition_en: Optional[str] = None
    first_occurrence: Optional[str] = None  # verse_id
    era: Optional[str] = None
    frequency: int = 0
    related_concepts: List[str] = field(default_factory=list)
    modern_parallel: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None


@dataclass
class EventRecord:
    """Historical/narrative event from texts."""
    
    event_id: Optional[UUID] = None
    title_en: str = ""
    title_sa: Optional[str] = None
    participants: List[str] = field(default_factory=list)  # char_ids
    location: Optional[str] = None
    source_verse: Optional[str] = None  # verse_id
    event_type: Optional[str] = None    # Battle, Teaching, Birth, Death
    yuga: Optional[str] = None          # Satya, Treta, Dvapara, Kali
    sequence_no: Optional[int] = None
    description_en: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class RelationRecord:
    """Relationship between two characters."""
    
    rel_id: Optional[UUID] = None
    char_a: str                      # char_id
    char_b: str                      # char_id
    relation_type: str               # SON_OF, BATTLES, TEACHES, etc.
    source_text: Optional[str] = None
    source_verse: Optional[str] = None  # verse_id
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class ScienceLinkRecord:
    """Link between Sanskrit verse/concept and modern science paper."""
    
    link_id: Optional[UUID] = None
    verse_id: Optional[str] = None
    concept_id: Optional[str] = None
    domain: str                      # Physics, Medicine, Astronomy, etc.
    modern_ref: Optional[str] = None  # DOI or URL
    modern_title: Optional[str] = None
    confidence: float = 0.0          # 0.0-1.0
    description: Optional[str] = None
    verified: bool = False
    created_at: Optional[datetime] = None

    def validate(self) -> None:
        """Validate science link record."""
        if not self.verse_id and not self.concept_id:
            raise ValueError("Either verse_id or concept_id must be provided")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class AnswerRecord:
    """Response from RAG pipeline to a question."""
    
    answer: str
    source_verses: List[VerseRecord] = field(default_factory=list)
    characters_mentioned: List[str] = field(default_factory=list)
    science_links: List[ScienceLinkRecord] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: Optional[datetime] = None
