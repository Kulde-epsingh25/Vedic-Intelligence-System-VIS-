-- Vedic Intelligence System Database Schema
-- Target: Supabase (PostgreSQL 14+)
-- This schema is the single source of truth for all data structures

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── VERSES TABLE ───────────────────────────────────────────────────────────
CREATE TABLE verses (
    verse_id        TEXT PRIMARY KEY,
    source_text     TEXT NOT NULL,              -- "Rigveda", "Bhagavad Gita", etc.
    book            INTEGER,
    chapter         INTEGER,
    verse_num       INTEGER,
    devanagari      TEXT,                       -- Unicode Devanagari
    iast            TEXT,                       -- IAST romanisation
    slp1            TEXT,                       -- SLP1 encoding
    translation_en  TEXT,
    translation_hi  TEXT,
    speaker_id      TEXT REFERENCES characters(char_id) ON DELETE SET NULL,
    addressed_to    TEXT REFERENCES characters(char_id) ON DELETE SET NULL,
    metre           TEXT,                       -- Anushtubh, Trishtubh, Jagati, etc.
    era             TEXT,                       -- Vedic, Upanishadic, Classical, Medieval
    topics          TEXT[],                     -- array of concept_ids
    embedding       vector(768),                -- sentence-transformer embedding
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_verses_source_text ON verses(source_text);
CREATE INDEX idx_verses_era ON verses(era);
CREATE INDEX idx_verses_embedding ON verses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_verses_topics ON verses USING gin(topics);

-- ── WORDS TABLE ────────────────────────────────────────────────────────────
CREATE TABLE words (
    pada_id         TEXT PRIMARY KEY,
    verse_id        TEXT NOT NULL REFERENCES verses(verse_id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    surface_form    TEXT NOT NULL,              -- as it appears in text
    dhatu           TEXT,                       -- verbal root e.g. "√gam"
    stem            TEXT,
    vibhakti        INTEGER,                    -- 1-8 (case)
    vachana         TEXT,                       -- Singular, Dual, Plural
    linga           TEXT,                       -- Masculine, Feminine, Neuter
    purusha         TEXT,                       -- 1st, 2nd, 3rd person (verbs)
    lakara          TEXT,                       -- tense/mood (verbs)
    meaning_en      TEXT,
    frequency       INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_words_verse_id ON words(verse_id);
CREATE INDEX idx_words_surface_form ON words(surface_form);
CREATE INDEX idx_words_dhatu ON words(dhatu);

-- ── CHARACTERS TABLE ───────────────────────────────────────────────────────
CREATE TABLE characters (
    char_id         TEXT PRIMARY KEY,
    name_sa         TEXT NOT NULL,              -- Sanskrit name (IAST)
    name_devanagari TEXT,
    aliases         TEXT[],                     -- alternate names
    char_type       TEXT,                       -- Deva, Asura, Human, Rishi, Animal
    gender          TEXT,
    appears_in      TEXT[],                     -- source_texts
    verse_count     INTEGER DEFAULT 0,
    attributes      TEXT[],                     -- weapons, epithets, qualities
    description_en  TEXT,
    embedding       vector(768),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_characters_name_sa ON characters(name_sa);
CREATE INDEX idx_characters_char_type ON characters(char_type);
CREATE INDEX idx_characters_embedding ON characters USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── CONCEPTS TABLE ─────────────────────────────────────────────────────────
CREATE TABLE concepts (
    concept_id      TEXT PRIMARY KEY,
    name_sa         TEXT NOT NULL,
    name_devanagari TEXT,
    category        TEXT,                       -- Philosophy, Science, Ritual, Social, Cosmic
    definition_sa   TEXT,
    definition_en   TEXT,
    first_occurrence TEXT REFERENCES verses(verse_id) ON DELETE SET NULL,
    era             TEXT,
    frequency       INTEGER DEFAULT 0,
    related_concepts TEXT[],                    -- concept_ids
    modern_parallel TEXT,
    embedding       vector(768),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_concepts_name_sa ON concepts(name_sa);
CREATE INDEX idx_concepts_category ON concepts(category);
CREATE INDEX idx_concepts_embedding ON concepts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── EVENTS TABLE ───────────────────────────────────────────────────────────
CREATE TABLE events (
    event_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title_en        TEXT NOT NULL,
    title_sa        TEXT,
    participants    TEXT[],                     -- char_ids
    location        TEXT,
    source_verse    TEXT REFERENCES verses(verse_id) ON DELETE SET NULL,
    event_type      TEXT,                       -- Battle, Teaching, Birth, Death, Curse, Boon
    yuga            TEXT,                       -- Satya, Treta, Dvapara, Kali
    sequence_no     INTEGER,
    description_en  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_participants ON events USING gin(participants);

-- ── RELATIONS TABLE ────────────────────────────────────────────────────────
CREATE TABLE relations (
    rel_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    char_a          TEXT NOT NULL REFERENCES characters(char_id) ON DELETE CASCADE,
    char_b          TEXT NOT NULL REFERENCES characters(char_id) ON DELETE CASCADE,
    relation_type   TEXT NOT NULL,
    source_text     TEXT,
    source_verse    TEXT REFERENCES verses(verse_id) ON DELETE SET NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_relations_char_a ON relations(char_a);
CREATE INDEX idx_relations_char_b ON relations(char_b);
CREATE INDEX idx_relations_type ON relations(relation_type);

-- ── SCIENCE LINKS TABLE ────────────────────────────────────────────────────
CREATE TABLE science_links (
    link_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verse_id        TEXT REFERENCES verses(verse_id) ON DELETE CASCADE,
    concept_id      TEXT REFERENCES concepts(concept_id) ON DELETE CASCADE,
    domain          TEXT NOT NULL,
    modern_ref      TEXT,                       -- DOI or URL
    modern_title    TEXT,
    confidence      FLOAT DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    description     TEXT,
    verified        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_science_links_domain ON science_links(domain);
CREATE INDEX idx_science_links_verified ON science_links(verified);
CREATE INDEX idx_science_links_confidence ON science_links(confidence);

-- ── ANALYTICS TABLE ────────────────────────────────────────────────────────
-- Track API queries for insights
CREATE TABLE api_queries (
    query_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question        TEXT,
    answered_verse_ids TEXT[],
    response_time_ms INTEGER,
    user_ip         TEXT,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_queries_timestamp ON api_queries(timestamp);

-- ── Row-Level Security (optional) ──────────────────────────────────────────
-- Uncomment if using Supabase auth
-- ALTER TABLE verses ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Enable read access for all users" ON verses FOR SELECT USING (true);
