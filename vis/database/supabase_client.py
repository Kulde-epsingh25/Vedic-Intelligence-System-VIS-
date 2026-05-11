"""
database/supabase_client.py
============================
Supabase PostgreSQL client — all DB operations for verses, words,
characters, concepts, events, science_links.
"""

import os
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))


class SupabaseDB:
    """
    Singleton Supabase client for all database operations.

    Example:
        >>> db = SupabaseDB()
        >>> db.insert_verse({"verse_id": "BG.1.1", "devanagari": "धर्मक्षेत्रे..."})
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.client = None
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase credentials not set — running without DB")
            return
        try:
            from supabase import create_client
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.success("Supabase connected")
        except Exception as e:
            logger.error(f"Supabase connection failed: {e}")

    # ── VERSES ──────────────────────────────────────────
    def insert_verse(self, verse: dict) -> dict | None:
        if not self.client:
            return None
        try:
            r = self.client.table("verses").upsert(verse).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"insert_verse failed: {e}")
            return None

    def bulk_insert_verses(self, verses: list[dict], batch: int = 200) -> int:
        if not self.client:
            return 0
        stored = 0
        for i in range(0, len(verses), batch):
            chunk = verses[i:i + batch]
            try:
                self.client.table("verses").upsert(chunk).execute()
                stored += len(chunk)
            except Exception as e:
                logger.error(f"bulk_insert_verses batch {i}: {e}")
        logger.info(f"Inserted {stored} verses into Supabase")
        return stored

    def get_verse(self, verse_id: str) -> dict | None:
        if not self.client:
            return None
        try:
            r = self.client.table("verses").select("*").eq("verse_id", verse_id).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_verse {verse_id}: {e}")
            return None

    def search_verses(self, source_text_id: str = None,
                      era: str = None, limit: int = 50) -> list[dict]:
        if not self.client:
            return []
        try:
            q = self.client.table("verses").select("*")
            if source_text_id:
                q = q.eq("source_text_id", source_text_id)
            if era:
                q = q.eq("era", era)
            r = q.limit(limit).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"search_verses: {e}")
            return []

    # ── WORDS ────────────────────────────────────────────
    def bulk_insert_words(self, words: list[dict], batch: int = 500) -> int:
        if not self.client:
            return 0
        stored = 0
        for i in range(0, len(words), batch):
            chunk = words[i:i + batch]
            try:
                self.client.table("words").upsert(chunk).execute()
                stored += len(chunk)
            except Exception as e:
                logger.error(f"bulk_insert_words batch {i}: {e}")
        logger.info(f"Inserted {stored} words")
        return stored

    def get_words_for_verse(self, verse_id: str) -> list[dict]:
        if not self.client:
            return []
        try:
            r = (self.client.table("words")
                 .select("*")
                 .eq("verse_id", verse_id)
                 .order("position")
                 .execute())
            return r.data or []
        except Exception as e:
            logger.error(f"get_words_for_verse {verse_id}: {e}")
            return []

    def get_word_frequency(self, dhatu: str) -> int:
        if not self.client:
            return 0
        try:
            r = (self.client.table("words")
                 .select("*", count="exact")
                 .eq("dhatu", dhatu)
                 .execute())
            return r.count or 0
        except Exception:
            return 0

    # ── CHARACTERS ───────────────────────────────────────
    def insert_character(self, char: dict) -> dict | None:
        if not self.client:
            return None
        try:
            r = self.client.table("characters").upsert(char).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"insert_character: {e}")
            return None

    def get_character(self, char_id: str) -> dict | None:
        if not self.client:
            return None
        try:
            r = (self.client.table("characters")
                 .select("*")
                 .eq("char_id", char_id)
                 .execute())
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_character {char_id}: {e}")
            return None

    def search_characters(self, name_query: str = None,
                          char_type: str = None) -> list[dict]:
        if not self.client:
            return []
        try:
            q = self.client.table("characters").select("*")
            if name_query:
                q = q.ilike("name_en", f"%{name_query}%")
            if char_type:
                q = q.eq("char_type", char_type)
            r = q.order("verse_count", desc=True).limit(50).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"search_characters: {e}")
            return []

    # ── CONCEPTS ─────────────────────────────────────────
    def insert_concept(self, concept: dict) -> dict | None:
        if not self.client:
            return None
        try:
            r = self.client.table("concepts").upsert(concept).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"insert_concept: {e}")
            return None

    def get_concept(self, concept_id: str) -> dict | None:
        if not self.client:
            return None
        try:
            r = (self.client.table("concepts")
                 .select("*")
                 .eq("concept_id", concept_id)
                 .execute())
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_concept {concept_id}: {e}")
            return None

    def get_concepts_by_category(self, category: str) -> list[dict]:
        if not self.client:
            return []
        try:
            r = (self.client.table("concepts")
                 .select("*")
                 .eq("category", category)
                 .order("frequency", desc=True)
                 .execute())
            return r.data or []
        except Exception as e:
            logger.error(f"get_concepts_by_category: {e}")
            return []

    # ── SCIENCE LINKS ─────────────────────────────────────
    def insert_science_link(self, link: dict) -> dict | None:
        if not self.client:
            return None
        try:
            r = self.client.table("science_links").insert(link).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"insert_science_link: {e}")
            return None

    def get_science_links(self, concept_id: str = None,
                          domain: str = None,
                          min_confidence: float = 0.5) -> list[dict]:
        if not self.client:
            return []
        try:
            q = self.client.table("science_links").select("*")
            if concept_id:
                q = q.eq("concept_id", concept_id)
            if domain:
                q = q.eq("domain", domain)
            q = q.gte("confidence", min_confidence).order("confidence", desc=True)
            r = q.execute()
            return r.data or []
        except Exception as e:
            logger.error(f"get_science_links: {e}")
            return []

    # ── PIPELINE STATE ────────────────────────────────────
    def log_pipeline_run(self, run: dict) -> None:
        if not self.client:
            return
        try:
            self.client.table("pipeline_runs").insert(run).execute()
        except Exception:
            pass

    def get_stats(self) -> dict:
        """Returns row counts for all tables."""
        if not self.client:
            return {"status": "no_connection"}
        stats = {}
        for table in ["verses", "words", "characters", "concepts",
                      "events", "science_links", "relations"]:
            try:
                r = self.client.table(table).select("*", count="exact").limit(1).execute()
                stats[table] = r.count or 0
            except Exception:
                stats[table] = -1
        return stats
