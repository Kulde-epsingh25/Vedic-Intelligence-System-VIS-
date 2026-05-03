"""
Database Supabase client for relational queries and bulk operations.

This module provides a singleton connection to Supabase (PostgreSQL) for
storing and retrieving Sanskrit texts, concepts, characters, and science links.
"""

from typing import Optional, List
from loguru import logger
import os
from datetime import datetime

from database.models import (
    VerseRecord,
    WordRecord,
    CharacterRecord,
    ConceptRecord,
    EventRecord,
    RelationRecord,
    ScienceLinkRecord,
)


class SupabaseClient:
    """Singleton client for Supabase database operations."""

    _instance = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialize Supabase client.

        Example:
            >>> client = SupabaseClient()
            >>> verse = client.get_verse("BG.1.1")
        """
        if hasattr(self, "_initialized"):
            return

        try:
            from supabase import create_client, Client
            
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_ANON_KEY")

            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")

            self.client: Client = create_client(url, key)
            logger.info("Supabase client initialized")
            self._initialized = True

        except ImportError:
            logger.error("supabase library not installed")
            raise ImportError("Install via: pip install supabase")
        except Exception as e:
            logger.error(f"Error initializing Supabase: {e}")
            raise

    def insert_verse(self, verse: VerseRecord) -> bool:
        """
        Insert a single verse.

        Args:
            verse: VerseRecord to insert

        Returns:
            True if successful, False otherwise

        Example:
            >>> client = SupabaseClient()
            >>> verse = VerseRecord(
            ...     verse_id="BG.1.1",
            ...     source_text="Bhagavad Gita",
            ...     devanagari="धर्मक्षेत्रे",
            ...     iast="dharmakṣetre"
            ... )
            >>> success = client.insert_verse(verse)
        """
        try:
            verse.validate()

            data = {
                "verse_id": verse.verse_id,
                "source_text": verse.source_text,
                "book": verse.book,
                "chapter": verse.chapter,
                "verse_num": verse.verse_num,
                "devanagari": verse.devanagari,
                "iast": verse.iast,
                "slp1": verse.slp1,
                "translation_en": verse.translation_en,
                "translation_hi": verse.translation_hi,
                "speaker_id": verse.speaker_id,
                "addressed_to": verse.addressed_to,
                "metre": verse.metre,
                "era": verse.era,
                "topics": verse.topics,
                "embedding": verse.embedding,
            }

            self.client.table("verses").insert(data).execute()
            logger.debug(f"Inserted verse: {verse.verse_id}")
            return True

        except Exception as e:
            logger.error(f"Error inserting verse {verse.verse_id}: {e}")
            return False

    def insert_word(self, word: WordRecord) -> bool:
        """
        Insert a single word record.

        Args:
            word: WordRecord to insert

        Returns:
            True if successful
        """
        try:
            data = {
                "pada_id": word.pada_id,
                "verse_id": word.verse_id,
                "position": word.position,
                "surface_form": word.surface_form,
                "dhatu": word.dhatu,
                "stem": word.stem,
                "vibhakti": word.vibhakti,
                "vachana": word.vachana,
                "linga": word.linga,
                "purusha": word.purusha,
                "lakara": word.lakara,
                "meaning_en": word.meaning_en,
                "frequency": word.frequency,
            }

            self.client.table("words").insert(data).execute()
            logger.debug(f"Inserted word: {word.pada_id}")
            return True

        except Exception as e:
            logger.error(f"Error inserting word {word.pada_id}: {e}")
            return False

    def insert_character(self, char: CharacterRecord) -> bool:
        """
        Insert a character record.

        Args:
            char: CharacterRecord to insert

        Returns:
            True if successful
        """
        try:
            data = {
                "char_id": char.char_id,
                "name_sa": char.name_sa,
                "name_devanagari": char.name_devanagari,
                "aliases": char.aliases,
                "char_type": char.char_type,
                "gender": char.gender,
                "appears_in": char.appears_in,
                "verse_count": char.verse_count,
                "attributes": char.attributes,
                "description_en": char.description_en,
                "embedding": char.embedding,
            }

            self.client.table("characters").insert(data).execute()
            logger.debug(f"Inserted character: {char.char_id}")
            return True

        except Exception as e:
            logger.error(f"Error inserting character {char.char_id}: {e}")
            return False

    def insert_concept(self, concept: ConceptRecord) -> bool:
        """
        Insert a concept record.

        Args:
            concept: ConceptRecord to insert

        Returns:
            True if successful
        """
        try:
            data = {
                "concept_id": concept.concept_id,
                "name_sa": concept.name_sa,
                "name_devanagari": concept.name_devanagari,
                "category": concept.category,
                "definition_sa": concept.definition_sa,
                "definition_en": concept.definition_en,
                "first_occurrence": concept.first_occurrence,
                "era": concept.era,
                "frequency": concept.frequency,
                "related_concepts": concept.related_concepts,
                "modern_parallel": concept.modern_parallel,
                "embedding": concept.embedding,
            }

            self.client.table("concepts").insert(data).execute()
            logger.debug(f"Inserted concept: {concept.concept_id}")
            return True

        except Exception as e:
            logger.error(f"Error inserting concept {concept.concept_id}: {e}")
            return False

    def insert_science_link(self, link: ScienceLinkRecord) -> bool:
        """
        Insert a science link record.

        Args:
            link: ScienceLinkRecord to insert

        Returns:
            True if successful
        """
        try:
            link.validate()

            data = {
                "verse_id": link.verse_id,
                "concept_id": link.concept_id,
                "domain": link.domain,
                "modern_ref": link.modern_ref,
                "modern_title": link.modern_title,
                "confidence": link.confidence,
                "description": link.description,
                "verified": link.verified,
            }

            self.client.table("science_links").insert(data).execute()
            logger.debug(f"Inserted science link")
            return True

        except Exception as e:
            logger.error(f"Error inserting science link: {e}")
            return False

    def bulk_insert_verses(self, verses: List[VerseRecord], batch_size: int = 100) -> int:
        """
        Batch insert multiple verses.

        Args:
            verses: List of VerseRecords
            batch_size: Batch size (default: 100)

        Returns:
            Number of verses inserted

        Example:
            >>> client = SupabaseClient()
            >>> verses = [...]  # List of VerseRecords
            >>> count = client.bulk_insert_verses(verses)
            >>> print(f"Inserted {count} verses")
        """
        inserted = 0

        try:
            for i in range(0, len(verses), batch_size):
                batch = verses[i:i + batch_size]

                data = []
                for verse in batch:
                    verse.validate()
                    data.append({
                        "verse_id": verse.verse_id,
                        "source_text": verse.source_text,
                        "book": verse.book,
                        "chapter": verse.chapter,
                        "verse_num": verse.verse_num,
                        "devanagari": verse.devanagari,
                        "iast": verse.iast,
                        "slp1": verse.slp1,
                        "translation_en": verse.translation_en,
                        "translation_hi": verse.translation_hi,
                        "speaker_id": verse.speaker_id,
                        "addressed_to": verse.addressed_to,
                        "metre": verse.metre,
                        "era": verse.era,
                        "topics": verse.topics,
                        "embedding": verse.embedding,
                    })

                self.client.table("verses").insert(data).execute()
                inserted += len(batch)
                logger.info(f"Inserted batch of {len(batch)} verses ({inserted}/{len(verses)})")

            logger.info(f"Bulk insert complete: {inserted} verses")
            return inserted

        except Exception as e:
            logger.error(f"Error in bulk insert: {e}")
            return inserted

    def get_verse(self, verse_id: str) -> Optional[VerseRecord]:
        """
        Get a single verse by ID.

        Args:
            verse_id: Verse identifier

        Returns:
            VerseRecord or None

        Example:
            >>> client = SupabaseClient()
            >>> verse = client.get_verse("BG.1.1")
            >>> if verse:
            ...     print(verse.devanagari)
        """
        try:
            response = self.client.table("verses").select("*").eq("verse_id", verse_id).execute()

            if response.data and len(response.data) > 0:
                row = response.data[0]
                return VerseRecord(
                    verse_id=row["verse_id"],
                    source_text=row["source_text"],
                    devanagari=row["devanagari"],
                    iast=row["iast"],
                    slp1=row.get("slp1"),
                    translation_en=row.get("translation_en"),
                    translation_hi=row.get("translation_hi"),
                    book=row.get("book"),
                    chapter=row.get("chapter"),
                    verse_num=row.get("verse_num"),
                    speaker_id=row.get("speaker_id"),
                    addressed_to=row.get("addressed_to"),
                    metre=row.get("metre"),
                    era=row.get("era"),
                    topics=row.get("topics", []),
                    embedding=row.get("embedding"),
                    created_at=row.get("created_at"),
                )

            return None

        except Exception as e:
            logger.error(f"Error getting verse {verse_id}: {e}")
            return None

    def get_character(self, char_id: str) -> Optional[CharacterRecord]:
        """
        Get a character by ID.

        Args:
            char_id: Character identifier

        Returns:
            CharacterRecord or None
        """
        try:
            response = self.client.table("characters").select("*").eq("char_id", char_id).execute()

            if response.data and len(response.data) > 0:
                row = response.data[0]
                return CharacterRecord(
                    char_id=row["char_id"],
                    name_sa=row["name_sa"],
                    name_devanagari=row.get("name_devanagari"),
                    aliases=row.get("aliases", []),
                    char_type=row.get("char_type"),
                    gender=row.get("gender"),
                    appears_in=row.get("appears_in", []),
                    verse_count=row.get("verse_count", 0),
                    attributes=row.get("attributes", []),
                    description_en=row.get("description_en"),
                    embedding=row.get("embedding"),
                    created_at=row.get("created_at"),
                )

            return None

        except Exception as e:
            logger.error(f"Error getting character {char_id}: {e}")
            return None

    def get_concept(self, concept_id: str) -> Optional[ConceptRecord]:
        """
        Get a concept by ID.

        Args:
            concept_id: Concept identifier

        Returns:
            ConceptRecord or None
        """
        try:
            response = self.client.table("concepts").select("*").eq("concept_id", concept_id).execute()

            if response.data and len(response.data) > 0:
                row = response.data[0]
                return ConceptRecord(
                    concept_id=row["concept_id"],
                    name_sa=row["name_sa"],
                    name_devanagari=row.get("name_devanagari"),
                    category=row.get("category"),
                    definition_sa=row.get("definition_sa"),
                    definition_en=row.get("definition_en"),
                    first_occurrence=row.get("first_occurrence"),
                    era=row.get("era"),
                    frequency=row.get("frequency", 0),
                    related_concepts=row.get("related_concepts", []),
                    modern_parallel=row.get("modern_parallel"),
                    embedding=row.get("embedding"),
                    created_at=row.get("created_at"),
                )

            return None

        except Exception as e:
            logger.error(f"Error getting concept {concept_id}: {e}")
            return None

    def search_verses_by_text(
        self,
        search_text: str,
        source_text: Optional[str] = None,
        era: Optional[str] = None,
        limit: int = 10
    ) -> List[VerseRecord]:
        """
        Search verses by text content.

        Args:
            search_text: Text to search for
            source_text: Optional filter by source text
            era: Optional filter by era
            limit: Maximum results

        Returns:
            List of matching VerseRecords

        Example:
            >>> client = SupabaseClient()
            >>> results = client.search_verses_by_text("dharma", source_text="Bhagavad Gita")
        """
        try:
            query = self.client.table("verses").select("*")

            # Add filters
            if source_text:
                query = query.eq("source_text", source_text)
            if era:
                query = query.eq("era", era)

            response = query.like("devanagari", f"%{search_text}%").limit(limit).execute()

            verses = []
            for row in response.data:
                verse = VerseRecord(
                    verse_id=row["verse_id"],
                    source_text=row["source_text"],
                    devanagari=row["devanagari"],
                    iast=row["iast"],
                    slp1=row.get("slp1"),
                    translation_en=row.get("translation_en"),
                    translation_hi=row.get("translation_hi"),
                    book=row.get("book"),
                    chapter=row.get("chapter"),
                    verse_num=row.get("verse_num"),
                    speaker_id=row.get("speaker_id"),
                    addressed_to=row.get("addressed_to"),
                    metre=row.get("metre"),
                    era=row.get("era"),
                    topics=row.get("topics", []),
                    embedding=row.get("embedding"),
                    created_at=row.get("created_at"),
                )
                verses.append(verse)

            logger.debug(f"Found {len(verses)} verses matching '{search_text}'")
            return verses

        except Exception as e:
            logger.error(f"Error searching verses: {e}")
            return []

    def log_query(self, question: str, answer_verse_ids: List[str], response_time_ms: int) -> bool:
        """
        Log an API query for analytics.

        Args:
            question: User question
            answer_verse_ids: Verses cited in answer
            response_time_ms: Response time in milliseconds

        Returns:
            True if successful
        """
        try:
            import socket
            user_ip = socket.gethostbyname(socket.gethostname())

            data = {
                "question": question,
                "answered_verse_ids": answer_verse_ids,
                "response_time_ms": response_time_ms,
                "user_ip": user_ip,
            }

            self.client.table("api_queries").insert(data).execute()
            logger.debug("Query logged to analytics")
            return True

        except Exception as e:
            logger.warning(f"Could not log query: {e}")
            return False
