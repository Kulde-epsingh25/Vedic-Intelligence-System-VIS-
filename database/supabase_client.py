"""
database/supabase_client.py
============================
Hybrid Supabase / SQLite client for VIS.
Connects to Supabase if valid credentials are provided;
otherwise falls back automatically to local SQLite database (data/vis_local.db),
guaranteeing that all endpoints return rich, authentic Vedic knowledge.
"""

import os
import sqlite3
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

from database.local_db import get_connection, init_local_db

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))


class SupabaseDB:
    """
    Singleton Database client for all operations.
    Seamlessly uses Supabase in cloud, or SQLite locally.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.client = None
        init_local_db()
        # Only attempt Supabase if URL is a valid configured URL (not placeholder)
        if SUPABASE_URL and SUPABASE_KEY and "your-project" not in SUPABASE_URL:
            try:
                from supabase import create_client
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.success("Supabase connected successfully")
            except Exception as e:
                logger.warning(f"Supabase connection failed ({e}). Falling back to local SQLite.")
                self.client = None
        else:
            logger.info("Using local SQLite storage (vis_local.db)")

    # ── VERSES ──────────────────────────────────────────
    def insert_verse(self, verse: dict) -> dict | None:
        if self.client:
            try:
                r = self.client.table("verses").upsert(verse).execute()
                return r.data[0] if r.data else None
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        keys = list(verse.keys())
        placeholders = ", ".join(["?"] * len(keys))
        cols = ", ".join(keys)
        c.execute(f"INSERT OR REPLACE INTO verses ({cols}) VALUES ({placeholders})", list(verse.values()))
        conn.commit()
        conn.close()
        return verse

    def get_verse(self, verse_id: str) -> dict | None:
        if self.client:
            try:
                r = self.client.table("verses").select("*").eq("verse_id", verse_id).execute()
                if r.data:
                    return r.data[0]
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM verses WHERE verse_id = ?", (verse_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def search_verses(self, source_text_id: str = None,
                      era: str = None, limit: int = 50) -> list[dict]:
        if self.client:
            try:
                q = self.client.table("verses").select("*")
                if source_text_id:
                    q = q.eq("source_text_id", source_text_id)
                if era:
                    q = q.eq("era", era)
                r = q.limit(limit).execute()
                if r.data:
                    return r.data
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        query = "SELECT * FROM verses WHERE 1=1"
        params = []
        if source_text_id:
            query += " AND source_text_id = ?"
            params.append(source_text_id)
        if era:
            query += " AND era = ?"
            params.append(era)
        query += f" LIMIT {limit}"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── WORDS ────────────────────────────────────────────
    def get_words_for_verse(self, verse_id: str) -> list[dict]:
        if self.client:
            try:
                r = (self.client.table("words")
                     .select("*")
                     .eq("verse_id", verse_id)
                     .order("position")
                     .execute())
                if r.data:
                    return r.data
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM words WHERE verse_id = ? ORDER BY position", (verse_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_word_frequency(self, dhatu: str) -> int:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM words WHERE dhatu = ?", (dhatu,))
        count = c.fetchone()[0]
        conn.close()
        return count

    # ── CHARACTERS ───────────────────────────────────────
    def get_character(self, char_id: str) -> dict | None:
        if self.client:
            try:
                r = self.client.table("characters").select("*").eq("char_id", char_id).execute()
                if r.data:
                    return r.data[0]
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM characters WHERE char_id = ?", (char_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def search_characters(self, name_query: str = None,
                          char_type: str = None) -> list[dict]:
        if self.client:
            try:
                q = self.client.table("characters").select("*")
                if name_query:
                    q = q.ilike("name_en", f"%{name_query}%")
                if char_type:
                    q = q.eq("char_type", char_type)
                r = q.order("verse_count", desc=True).limit(50).execute()
                if r.data:
                    return r.data
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        query = "SELECT * FROM characters WHERE 1=1"
        params = []
        if name_query:
            query += " AND (name_en LIKE ? OR name_sa LIKE ?)"
            params.extend([f"%{name_query}%", f"%{name_query}%"])
        if char_type:
            query += " AND char_type = ?"
            params.append(char_type)
        query += " ORDER BY verse_count DESC LIMIT 50"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── CONCEPTS ─────────────────────────────────────────
    def get_concept(self, concept_id: str) -> dict | None:
        if self.client:
            try:
                r = self.client.table("concepts").select("*").eq("concept_id", concept_id).execute()
                if r.data:
                    return r.data[0]
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM concepts WHERE concept_id = ?", (concept_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_concepts_by_category(self, category: str = None) -> list[dict]:
        if self.client:
            try:
                q = self.client.table("concepts").select("*")
                if category:
                    q = q.eq("category", category)
                r = q.order("frequency", desc=True).execute()
                if r.data:
                    return r.data
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        if category:
            c.execute("SELECT * FROM concepts WHERE category = ? ORDER BY frequency DESC", (category,))
        else:
            c.execute("SELECT * FROM concepts ORDER BY frequency DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── SCIENCE LINKS ─────────────────────────────────────
    def get_science_links(self, concept_id: str = None,
                          verse_id: str = None,
                          domain: str = None,
                          min_confidence: float = 0.5) -> list[dict]:
        if self.client:
            try:
                q = self.client.table("science_links").select("*")
                if concept_id:
                    q = q.eq("concept_id", concept_id)
                if verse_id:
                    q = q.eq("verse_id", verse_id)
                if domain:
                    q = q.eq("domain", domain)
                q = q.gte("confidence", min_confidence)
                r = q.order("confidence", desc=True).execute()
                if r.data:
                    return r.data
            except Exception:
                pass
        conn = get_connection()
        c = conn.cursor()
        query = "SELECT * FROM science_links WHERE confidence >= ?"
        params = [min_confidence]
        if concept_id:
            query += " AND concept_id = ?"
            params.append(concept_id)
        if verse_id:
            query += " AND verse_id = ?"
            params.append(verse_id)
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        query += " ORDER BY confidence DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── STATS ────────────────────────────────────────────
    def get_stats(self) -> dict:
        conn = get_connection()
        c = conn.cursor()
        stats = {}
        for table in ["verses", "words", "characters", "concepts", "science_links"]:
            try:
                c.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = c.fetchone()[0]
            except Exception:
                stats[table] = 0
        conn.close()
        return stats
