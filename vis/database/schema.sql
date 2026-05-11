-- ═══════════════════════════════════════════════════════
--  VIS — Vedic Intelligence System
--  Full Database Schema for Supabase PostgreSQL
--  Run this in: Supabase → SQL Editor → Run
-- ═══════════════════════════════════════════════════════

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── SOURCE TEXTS registry ────────────────────────────────
CREATE TABLE IF NOT EXISTS source_texts (
    text_id         TEXT PRIMARY KEY,
    title_en        TEXT NOT NULL,
    title_sa        TEXT,
    title_devanagari TEXT,
    category        TEXT,       -- Veda, Purana, Itihasa, Upanishad, Science, Philosophy
    sub_category    TEXT,       -- Rigveda, Shaiva Purana, etc.
    era             TEXT,       -- Vedic, Upanishadic, Classical, Medieval
    approx_date     TEXT,       -- e.g. "1500-1000 BCE"
    author_sa       TEXT,
    verse_count     INTEGER DEFAULT 0,
    source_url      TEXT,
    local_path      TEXT,
    is_downloaded   BOOLEAN DEFAULT FALSE,
    is_processed    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── VERSES (shlokas) — core unit ─────────────────────────
CREATE TABLE IF NOT EXISTS verses (
    verse_id        TEXT PRIMARY KEY,           -- RV.1.1.1 / BG.2.47 / MBH.6.25.11
    source_text_id  TEXT REFERENCES source_texts(text_id),
    book            INTEGER,
    chapter         INTEGER,
    verse_num       INTEGER,
    sub_verse       TEXT,                       -- for half-verses (a/b)
    devanagari      TEXT,
    iast            TEXT,
    slp1            TEXT,
    harvard_kyoto   TEXT,
    translation_en  TEXT,
    translation_hi  TEXT,
    speaker_id      TEXT,                       -- references characters
    addressed_to    TEXT,                       -- references characters
    metre           TEXT,
    era             TEXT,
    word_count      INTEGER DEFAULT 0,
    topics          TEXT[],                     -- concept_ids
    embedding       vector(768),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Fast vector search index
CREATE INDEX IF NOT EXISTS verses_embedding_idx 
    ON verses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS verses_source_idx ON verses(source_text_id);
CREATE INDEX IF NOT EXISTS verses_era_idx ON verses(era);

-- ── WORDS (padas) — linguistic atoms ─────────────────────
CREATE TABLE IF NOT EXISTS words (
    pada_id         TEXT PRIMARY KEY,           -- verse_id + "_" + position
    verse_id        TEXT REFERENCES verses(verse_id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    surface_form    TEXT NOT NULL,              -- as in text
    surface_devanagari TEXT,
    dhatu           TEXT,                       -- verbal root e.g. gam
    stem            TEXT,
    vibhakti        INTEGER,                    -- 1-8 (grammatical case)
    vachana         TEXT,                       -- Singular / Dual / Plural
    linga           TEXT,                       -- Masculine / Feminine / Neuter
    purusha         TEXT,                       -- 1st / 2nd / 3rd person
    lakara          TEXT,                       -- tense/mood for verbs
    meaning_en      TEXT,
    meaning_hi      TEXT,
    corpus_frequency INTEGER DEFAULT 1,        -- how often this pada appears
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS words_verse_idx ON words(verse_id);
CREATE INDEX IF NOT EXISTS words_dhatu_idx ON words(dhatu);
CREATE INDEX IF NOT EXISTS words_surface_idx ON words(surface_form);

-- ── CHARACTERS (patras) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS characters (
    char_id         TEXT PRIMARY KEY,           -- lowercase: rama, krishna, arjuna
    name_sa         TEXT NOT NULL,              -- IAST romanisation
    name_devanagari TEXT,
    name_en         TEXT,
    aliases         TEXT[],                     -- all alternate names
    char_type       TEXT,                       -- Deva / Asura / Human / Rishi / Animal / Gandharva
    gender          TEXT,
    appears_in      TEXT[],                     -- source_text_ids
    verse_count     INTEGER DEFAULT 0,
    attributes      TEXT[],                     -- weapons, qualities, epithets
    description_en  TEXT,
    description_hi  TEXT,
    birth_verse     TEXT REFERENCES verses(verse_id),
    death_verse     TEXT REFERENCES verses(verse_id),
    embedding       vector(768),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS characters_name_idx ON characters(name_sa);
CREATE INDEX IF NOT EXISTS characters_type_idx ON characters(char_type);

-- ── RELATIONS between characters ─────────────────────────
CREATE TABLE IF NOT EXISTS relations (
    rel_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    char_a          TEXT REFERENCES characters(char_id),
    char_b          TEXT REFERENCES characters(char_id),
    relation_type   TEXT NOT NULL,
    -- SON_OF, FATHER_OF, MOTHER_OF, DAUGHTER_OF, BROTHER_OF, SISTER_OF
    -- MARRIED_TO, DISCIPLE_OF, TEACHER_OF
    -- BATTLES, ALLY_OF, ENEMY_OF
    -- CURSED_BY, BLESSED_BY, KILLED_BY, BORN_FROM
    source_text_id  TEXT REFERENCES source_texts(text_id),
    source_verse    TEXT REFERENCES verses(verse_id),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS relations_char_a_idx ON relations(char_a);
CREATE INDEX IF NOT EXISTS relations_char_b_idx ON relations(char_b);
CREATE INDEX IF NOT EXISTS relations_type_idx ON relations(relation_type);

-- ── CONCEPTS (tattvas) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS concepts (
    concept_id      TEXT PRIMARY KEY,           -- dharma / karma / atman / brahman
    name_sa         TEXT NOT NULL,
    name_devanagari TEXT,
    name_en         TEXT,
    category        TEXT,
    -- Philosophy / Science / Ritual / Social / Cosmic / Grammar / Medicine
    definition_sa   TEXT,
    definition_en   TEXT,
    first_occurrence TEXT REFERENCES verses(verse_id),
    era             TEXT,
    frequency       INTEGER DEFAULT 0,
    related_concepts TEXT[],                    -- concept_ids
    modern_parallel TEXT,
    embedding       vector(768),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS concepts_category_idx ON concepts(category);
CREATE INDEX IF NOT EXISTS concepts_name_idx ON concepts(name_sa);

-- ── EVENTS (karmas) — narrative events ───────────────────
CREATE TABLE IF NOT EXISTS events (
    event_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title_en        TEXT NOT NULL,
    title_sa        TEXT,
    participants    TEXT[],                     -- char_ids
    location_sa     TEXT,
    location_en     TEXT,
    source_text_id  TEXT REFERENCES source_texts(text_id),
    source_verse    TEXT REFERENCES verses(verse_id),
    event_type      TEXT,
    -- Battle / Teaching / Birth / Death / Curse / Boon / Marriage / Journey / Creation / Destruction
    yuga            TEXT,                       -- Satya / Treta / Dvapara / Kali
    sequence_no     INTEGER,
    description_en  TEXT,
    consequences    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS events_type_idx ON events(event_type);
CREATE INDEX IF NOT EXISTS events_yuga_idx ON events(yuga);

-- ── SCIENCE LINKS — ancient ↔ modern bridge ──────────────
CREATE TABLE IF NOT EXISTS science_links (
    link_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verse_id        TEXT REFERENCES verses(verse_id),
    concept_id      TEXT REFERENCES concepts(concept_id),
    domain          TEXT NOT NULL,
    -- Physics / Astronomy / Mathematics / Medicine / Neuroscience
    -- Linguistics / Ecology / Economics / Architecture / Music / Futurism
    modern_ref      TEXT,                       -- DOI or URL
    modern_title    TEXT,
    modern_abstract TEXT,
    confidence      FLOAT DEFAULT 0.0 CHECK (confidence >= 0 AND confidence <= 1),
    description     TEXT,
    verified        BOOLEAN DEFAULT FALSE,
    verified_by     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS science_links_domain_idx ON science_links(domain);
CREATE INDEX IF NOT EXISTS science_links_concept_idx ON science_links(concept_id);
CREATE INDEX IF NOT EXISTS science_links_confidence_idx ON science_links(confidence);

-- ── WORD FREQUENCY MAP ───────────────────────────────────
CREATE TABLE IF NOT EXISTS word_frequency (
    freq_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dhatu           TEXT,
    surface_forms   TEXT[],
    total_count     INTEGER DEFAULT 0,
    texts_appearing TEXT[],                     -- source_text_ids
    first_verse     TEXT REFERENCES verses(verse_id),
    meaning_en      TEXT,
    concept_links   TEXT[],                     -- concept_ids
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── PIPELINE STATE tracking ──────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    text_id         TEXT REFERENCES source_texts(text_id),
    stage           TEXT,   -- download / normalise / parse / embed / graph / link
    status          TEXT,   -- running / complete / failed
    verses_processed INTEGER DEFAULT 0,
    words_processed INTEGER DEFAULT 0,
    errors          TEXT[],
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    duration_secs   INTEGER
);

-- ══════════════════════════════════════════════
--  SEED: All source texts we will process
-- ══════════════════════════════════════════════
INSERT INTO source_texts (text_id, title_en, title_sa, category, sub_category, era, approx_date, verse_count, source_url) VALUES

-- 4 VEDAS
('RV',  'Rigveda',          'ṛgveda',       'Veda', 'Rigveda',    'Vedic',        '1500-1200 BCE', 10552, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/1_sam/rv_samsu.htm'),
('SV',  'Samaveda',         'sāmaveda',     'Veda', 'Samaveda',   'Vedic',        '1200-1000 BCE', 1875,  'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/1_sam/sv_samsu.htm'),
('YV',  'Yajurveda',        'yajurveda',    'Veda', 'Yajurveda',  'Vedic',        '1200-900 BCE',  1875,  'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/1_sam/tsbr1_pu.htm'),
('AV',  'Atharvaveda',      'atharvaveda',  'Veda', 'Atharvaveda','Vedic',        '900-700 BCE',   5987,  'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/1_sam/av_samsu.htm'),

-- UPANISHADS
('BU',  'Brihadaranyaka Upanishad', 'bṛhadāraṇyaka', 'Upanishad', 'Principal', 'Upanishadic', '900-700 BCE', 2300, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/4_upa/brihadaru.htm'),
('CU',  'Chandogya Upanishad',      'chāndogya',     'Upanishad', 'Principal', 'Upanishadic', '800-600 BCE', 1300, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/4_upa/chandogu.htm'),
('KU',  'Katha Upanishad',          'kaṭha',         'Upanishad', 'Principal', 'Upanishadic', '500-300 BCE', 119,  'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/4_upa/katu.htm'),
('MU',  'Mundaka Upanishad',        'muṇḍaka',       'Upanishad', 'Principal', 'Upanishadic', '500-300 BCE', 64,   'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/4_upa/mundu.htm'),
('MAN', 'Mandukya Upanishad',       'māṇḍūkya',     'Upanishad', 'Principal', 'Upanishadic', '200 BCE',     12,   'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/4_upa/mandu.htm'),
('ISA', 'Isha Upanishad',           'īśa',           'Upanishad', 'Principal', 'Vedic',       '800-600 BCE', 18,   'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/4_upa/ishu.htm'),

-- ITIHASAS (EPICS)
('RAM', 'Valmiki Ramayana',         'vālmīkirāmāyaṇa',  'Itihasa', 'Ramayana',    'Classical', '500-100 BCE', 24000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/ramayana/'),
('MBH', 'Mahabharata',              'mahābhārata',       'Itihasa', 'Mahabharata', 'Classical', '400 BCE-400 CE', 100000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/mbh/'),
('BG',  'Bhagavad Gita',            'bhagavadgītā',      'Itihasa', 'Gita',        'Classical', '200-100 BCE', 700, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/2_epic/mbh/bhaggihu.htm'),

-- 18 MAHA PURANAS
('AGNI', 'Agni Purana',     'agnipurāṇa',     'Purana', 'Maha', 'Classical', '800-900 CE', 15400, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/agnipuru.htm'),
('BHAG', 'Bhagavata Purana','bhāgavatapurāṇa', 'Purana', 'Maha', 'Classical', '800-900 CE', 18000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/bhp1u.htm'),
('BRAH', 'Brahma Purana',   'brahmapurāṇa',   'Purana', 'Maha', 'Classical', '700-800 CE', 14000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/brhmpuru.htm'),
('GAR',  'Garuda Purana',   'garuḍapurāṇa',   'Purana', 'Maha', 'Classical', '800-900 CE', 19000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/garudpuu.htm'),
('KURA', 'Kurma Purana',    'kūrmapurāṇa',    'Purana', 'Maha', 'Classical', '700-800 CE', 18000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/kurmpuru.htm'),
('LING', 'Linga Purana',    'liṅgapurāṇa',    'Purana', 'Maha', 'Classical', '600-800 CE', 11000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/lingmpuu.htm'),
('MARK', 'Markandeya Purana','mārkāṇḍeyapurāṇa','Purana','Maha', 'Classical', '300-400 CE', 9000,  'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/markpuru.htm'),
('MATS', 'Matsya Purana',   'matsyapurāṇa',   'Purana', 'Maha', 'Classical', '250-500 CE', 14000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/matsypuu.htm'),
('NARAD','Narada Purana',   'nāradapurāṇa',   'Purana', 'Maha', 'Classical', '600-800 CE', 25000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/naradpuu.htm'),
('PAD',  'Padma Purana',    'padmapurāṇa',    'Purana', 'Maha', 'Classical', '500-700 CE', 55000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/padmpuu.htm'),
('SHIV', 'Shiva Purana',    'śivapurāṇa',     'Purana', 'Maha', 'Classical', '600-800 CE', 24000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/sivapuru.htm'),
('SKAND','Skanda Purana',   'skandapurāṇa',   'Purana', 'Maha', 'Classical', '600-900 CE', 81100, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/skppuu.htm'),
('VAMA', 'Vamana Purana',   'vāmanapurāṇa',   'Purana', 'Maha', 'Classical', '500-700 CE', 10000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/vampuu.htm'),
('VARA', 'Varaha Purana',   'varāhapurāṇa',   'Purana', 'Maha', 'Classical', '500-700 CE', 24000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/varahpuu.htm'),
('VISH', 'Vishnu Purana',   'viṣṇupurāṇa',   'Purana', 'Maha', 'Classical', '400-500 CE', 23000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/3_purana/vishnpuu.htm'),

-- PHILOSOPHY & GRAMMAR
('YS',   'Yoga Sutras',     'yogasūtra',      'Philosophy', 'Yoga',     'Classical', '400 BCE',     196,  'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/6_sastra/3_phil/yoga/ysu.htm'),
('ARTH', 'Arthashastra',    'arthaśāstra',    'Philosophy', 'Politics', 'Classical', '300 BCE',     6000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/6_sastra/7_misc/arthas_u.htm'),
('ASHT', 'Ashtadhyayi',     'aṣṭādhyāyī',    'Grammar',    'Grammar',  'Vedic',     '500 BCE',     3959, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/5_kavya/'),
('NS',   'Natya Shastra',   'nāṭyaśāstra',   'Arts',       'Music',    'Classical', '200 BCE-200 CE', 6000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/6_sastra/7_misc/natyashu.htm'),

-- SCIENCE TEXTS
('CS',  'Charaka Samhita',  'carakasaṃhitā',  'Science', 'Medicine',   'Classical', '300 BCE-200 CE', 12000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/6_sastra/5_ayur/caraksu2.htm'),
('SS',  'Sushruta Samhita', 'suśrutasaṃhitā', 'Science', 'Medicine',   'Classical', '600-700 BCE', 9000, 'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/6_sastra/5_ayur/susrutsu.htm'),
('AB',  'Aryabhatiya',      'āryabhaṭīya',    'Science', 'Astronomy',  'Classical', '499 CE',       118,  'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/6_sastra/6_astro/aryabh_u.htm'),
('SUL', 'Sulba Sutras',     'śulbasūtra',     'Science', 'Mathematics','Vedic',     '800-500 BCE',  600,  'https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/6_sastra/7_misc/')

ON CONFLICT (text_id) DO NOTHING;
