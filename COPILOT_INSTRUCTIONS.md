# 🤖 GitHub Copilot — Full Project Instructions
## Vedic Intelligence System (VIS) — Sanskrit AI/ML Platform

> **How to use this file:** Place this as `.github/copilot-instructions.md` in your repo root.
> Copilot will read it automatically for every file you open in VS Code.
> You can also paste sections into Copilot Chat directly.

---

## 🎯 PROJECT IDENTITY

**Project Name:** Vedic Intelligence System (VIS)  
**Short Name:** `vis`  
**Goal:** Build a full AI/ML system that reads, understands, maps, and answers questions from all ancient Sanskrit texts (Vedas, Puranas, Mahabharata, Ramayana, Upanishads, and 1000+ books), then cross-references everything with modern science.  
**Language:** Python (primary), R (visualization), JavaScript (frontend/API)  
**Style:** Clean, modular, well-commented. Every function must have a docstring. Every module must have a README.

---

## 📁 EXACT FOLDER STRUCTURE

Always create files in this structure. Never deviate.

```
vis/
├── .github/
│   ├── copilot-instructions.md        ← THIS FILE
│   └── workflows/
│       ├── pipeline.yml               ← weekly corpus processing
│       ├── science_linker.yml         ← weekly arXiv/PubMed auto-link
│       └── deploy.yml                 ← deploy to HuggingFace + Render
│
├── corpus/                            ← raw downloaded texts
│   ├── vedas/
│   │   ├── rigveda/
│   │   ├── samaveda/
│   │   ├── yajurveda/
│   │   └── atharvaveda/
│   ├── puranas/
│   ├── itihasas/
│   │   ├── mahabharata/
│   │   └── ramayana/
│   ├── upanishads/
│   ├── science/                       ← Charaka, Sushruta, Aryabhatiya
│   ├── philosophy/                    ← Arthashastra, Yoga Sutras
│   └── inscriptions/
│
├── pipeline/                          ← data processing scripts
│   ├── __init__.py
│   ├── downloader.py                  ← fetch texts from GRETIL, DCS, Archive.org
│   ├── normaliser.py                  ← encoding → Unicode Devanagari
│   ├── parser.py                      ← vidyut word-level parsing
│   ├── structurer.py                  ← verse JSON record creation
│   ├── embedder.py                    ← sentence-transformer embeddings
│   ├── science_linker.py              ← arXiv + PubMed auto-linking
│   └── run_pipeline.py                ← orchestrates all steps
│
├── graph/                             ← knowledge graph
│   ├── __init__.py
│   ├── loader.py                      ← load entities into Neo4j
│   ├── queries.py                     ← Cypher query library
│   ├── entities.py                    ← Character, Place, Concept dataclasses
│   └── cross_linker.py                ← unify same entity across texts
│
├── database/                          ← relational DB layer
│   ├── __init__.py
│   ├── schema.sql                     ← all CREATE TABLE statements
│   ├── supabase_client.py             ← Supabase connection + helpers
│   ├── models.py                      ← Python dataclasses matching tables
│   └── migrations/                    ← versioned schema changes
│
├── vector/                            ← vector search layer
│   ├── __init__.py
│   ├── chroma_store.py                ← ChromaDB local vector store
│   ├── pgvector_store.py              ← Supabase pgvector hybrid search
│   ├── pinecone_store.py              ← Pinecone cloud backup index
│   └── retriever.py                   ← unified retriever abstraction
│
├── ai/                                ← AI reasoning layer
│   ├── __init__.py
│   ├── rag_chain.py                   ← LangChain RAG pipeline
│   ├── reranker.py                    ← cross-encoder reranker
│   ├── prompt_templates.py            ← all LLM prompt templates
│   ├── finetune/
│   │   ├── train_lora.py              ← LoRA fine-tuning on Colab
│   │   ├── prepare_dataset.py         ← format training data
│   │   └── evaluate.py                ← model evaluation
│   └── inference.py                   ← answer generation
│
├── api/                               ← FastAPI REST backend
│   ├── __init__.py
│   ├── main.py                        ← FastAPI app entry point
│   ├── routers/
│   │   ├── verse.py                   ← /verse/{id} GET
│   │   ├── search.py                  ← /search POST
│   │   ├── character.py               ← /character/{name} GET
│   │   ├── concept.py                 ← /concept/{name} GET
│   │   ├── science.py                 ← /science-links GET
│   │   ├── graph.py                   ← /graph/path GET
│   │   └── ask.py                     ← /ask POST (RAG endpoint)
│   ├── middleware/
│   │   ├── cache.py                   ← Upstash Redis caching
│   │   └── rate_limit.py              ← rate limiting
│   └── schemas.py                     ← Pydantic request/response models
│
├── viz/                               ← visualization scripts
│   ├── grafify_plots.R                ← R: violin, scatter, before-after plots
│   ├── network_graph.py               ← NetworkX + pyvis graph generation
│   ├── umap_clusters.py               ← UMAP semantic cluster maps
│   ├── timeline.py                    ← Plotly interactive event timeline
│   └── heatmap.py                     ← text × science domain matrix
│
├── models/                            ← saved model files (gitignored large files)
│   └── .gitkeep
│
├── tests/
│   ├── test_pipeline.py
│   ├── test_parser.py
│   ├── test_api.py
│   ├── test_graph.py
│   └── test_retriever.py
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   ├── data_schema.md
│   └── contributing.md
│
├── scripts/
│   ├── setup_supabase.py              ← run schema.sql against Supabase
│   ├── setup_neo4j.py                 ← create Neo4j indexes and constraints
│   ├── seed_science_links.py          ← insert 50 initial science links
│   └── export_sqlite.py               ← export DB to offline SQLite
│
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .env                               ← gitignored
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 🗄️ DATABASE SCHEMA — Use Exactly This

When writing any database code, use these exact table names, column names, and types.

```sql
-- ── EXTENSION ──────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;

-- ── VERSES ─────────────────────────────────────────
CREATE TABLE verses (
    verse_id        TEXT PRIMARY KEY,           -- e.g. "RV.1.1.1", "BG.2.47", "MBH.6.25.11"
    source_text     TEXT NOT NULL,              -- "Rigveda", "Bhagavad Gita", "Mahabharata"
    book            INTEGER,
    chapter         INTEGER,
    verse_num       INTEGER,
    devanagari      TEXT,                       -- Unicode Devanagari
    iast            TEXT,                       -- IAST romanisation
    slp1            TEXT,                       -- SLP1 encoding
    translation_en  TEXT,
    translation_hi  TEXT,
    speaker_id      TEXT REFERENCES characters(char_id),
    addressed_to    TEXT REFERENCES characters(char_id),
    metre           TEXT,                       -- Anushtubh, Trishtubh, Jagati, etc.
    era             TEXT,                       -- Vedic, Upanishadic, Classical, Medieval
    topics          TEXT[],                     -- array of concept_ids
    embedding       vector(768),                -- sentence-transformer embedding
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON verses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── WORDS ──────────────────────────────────────────
CREATE TABLE words (
    pada_id         TEXT PRIMARY KEY,           -- verse_id + "_" + position
    verse_id        TEXT REFERENCES verses(verse_id),
    position        INTEGER,
    surface_form    TEXT NOT NULL,              -- as it appears in text
    dhatu           TEXT,                       -- verbal root e.g. "√gam"
    stem            TEXT,
    vibhakti        INTEGER,                    -- 1-8 (Nominative to Locative + Vocative)
    vachana         TEXT,                       -- Singular, Dual, Plural
    linga           TEXT,                       -- Masculine, Feminine, Neuter
    purusha         TEXT,                       -- 1st, 2nd, 3rd person (for verbs)
    lakara          TEXT,                       -- tense/mood (for verbs)
    meaning_en      TEXT,
    frequency       INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── CHARACTERS ─────────────────────────────────────
CREATE TABLE characters (
    char_id         TEXT PRIMARY KEY,           -- e.g. "rama", "krishna", "arjuna"
    name_sa         TEXT NOT NULL,              -- Sanskrit name in IAST
    name_devanagari TEXT,
    aliases         TEXT[],                     -- all alternate names
    char_type       TEXT,                       -- Deva, Asura, Human, Rishi, Animal
    gender          TEXT,
    appears_in      TEXT[],                     -- list of source_text values
    verse_count     INTEGER DEFAULT 0,
    attributes      TEXT[],                     -- weapons, qualities, epithets
    description_en  TEXT,
    embedding       vector(768),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── CONCEPTS ───────────────────────────────────────
CREATE TABLE concepts (
    concept_id      TEXT PRIMARY KEY,           -- e.g. "dharma", "karma", "atman"
    name_sa         TEXT NOT NULL,
    name_devanagari TEXT,
    category        TEXT,                       -- Philosophy, Science, Ritual, Social, Cosmic
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

-- ── EVENTS ─────────────────────────────────────────
CREATE TABLE events (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title_en        TEXT NOT NULL,
    title_sa        TEXT,
    participants    TEXT[],                     -- char_ids
    location        TEXT,
    source_verse    TEXT REFERENCES verses(verse_id),
    event_type      TEXT,                       -- Battle, Teaching, Birth, Death, Curse, Boon
    yuga            TEXT,                       -- Satya, Treta, Dvapara, Kali
    sequence_no     INTEGER,
    description_en  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── RELATIONS ──────────────────────────────────────
CREATE TABLE relations (
    rel_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    char_a          TEXT REFERENCES characters(char_id),
    char_b          TEXT REFERENCES characters(char_id),
    relation_type   TEXT NOT NULL,             -- SON_OF, FATHER_OF, BATTLES, TEACHES, MARRIED_TO, ALLY_OF, ENEMY_OF, CURSED_BY, DISCIPLE_OF
    source_text     TEXT,
    source_verse    TEXT REFERENCES verses(verse_id),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── SCIENCE LINKS ──────────────────────────────────
CREATE TABLE science_links (
    link_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verse_id        TEXT REFERENCES verses(verse_id),
    concept_id      TEXT REFERENCES concepts(concept_id),
    domain          TEXT NOT NULL,             -- Physics, Astronomy, Mathematics, Medicine, Neuroscience, Linguistics, Ecology, Economics, Architecture, Music, Futurism
    modern_ref      TEXT,                      -- DOI or URL
    modern_title    TEXT,
    confidence      FLOAT DEFAULT 0.0,         -- 0.0 to 1.0
    description     TEXT,
    verified        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🔧 ENVIRONMENT VARIABLES

Always use these exact variable names. Never hardcode credentials.

```bash
# .env.example — copy to .env and fill in

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Neo4j Aura
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Pinecone
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=vis-verses
PINECONE_ENVIRONMENT=us-east-1

# Upstash Redis
UPSTASH_REDIS_URL=https://your-instance.upstash.io
UPSTASH_REDIS_TOKEN=your-token

# HuggingFace
HUGGINGFACE_TOKEN=hf_your-token

# Models
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.2

# App
APP_ENV=development                             # development | production
LOG_LEVEL=INFO
API_PORT=8000
```

---

## 📦 DEPENDENCIES — requirements.txt

```
# Sanskrit Processing
vidyut>=0.3.0
indic-transliteration>=2.3.0

# AI / ML
langchain>=0.2.0
langchain-community>=0.2.0
sentence-transformers>=3.0.0
transformers>=4.40.0
peft>=0.10.0
datasets>=2.19.0
torch>=2.2.0

# Vector Databases
chromadb>=0.5.0
pinecone-client>=4.0.0

# Graph Database
py2neo>=2021.2.4

# Relational Database
supabase>=2.4.0
psycopg2-binary>=2.9.9
sqlalchemy>=2.0.0

# API
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pydantic>=2.7.0
python-dotenv>=1.0.0
upstash-redis>=1.0.0

# Data
requests>=2.31.0
beautifulsoup4>=4.12.0
arxiv>=2.1.0
lxml>=5.2.0

# Visualization
plotly>=5.21.0
networkx>=3.3.0
pyvis>=0.3.2
umap-learn>=0.5.6
matplotlib>=3.8.0
seaborn>=0.13.0

# Utilities
tqdm>=4.66.0
loguru>=0.7.0
httpx>=0.27.0
internetarchive>=4.0.0
```

---

## 🧩 CODING RULES FOR COPILOT

Follow these rules for every file you write or suggest:

### General
- **Every function must have a docstring** with Args, Returns, and Example
- **Every module must have a module-level docstring** explaining its purpose
- **Use loguru for all logging** — never print() in production code
- **Use pathlib.Path** — never os.path
- **Use python-dotenv** — load `.env` at startup in every entry point
- **Use dataclasses or Pydantic models** for all data structures
- **Every file must have type hints** on all function arguments and return values
- **Handle all exceptions explicitly** — never bare `except:`
- **Write tests for every public function** in the corresponding `tests/` file

### Naming conventions
- Variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`
- Database tables: `snake_case` (plural)
- API routes: `/kebab-case`

### Sanskrit data rules
- **Always store Devanagari as Unicode** — never escape sequences
- **Always store IAST** alongside Devanagari for romanised display
- **verse_id format is always:** `{TEXT_CODE}.{book}.{chapter}.{verse}` e.g. `RV.1.1.1`, `BG.2.47`
- **TEXT_CODE values:** RV (Rigveda), SV (Samaveda), YV (Yajurveda), AV (Atharvaveda), BG (Bhagavad Gita), MBH (Mahabharata), RAM (Ramayana), CS (Charaka Samhita), SS (Sushruta Samhita), ARTH (Arthashastra)

---

## 🔨 MODULE-BY-MODULE INSTRUCTIONS

### `pipeline/downloader.py`
```
Build a DownloadManager class with these methods:
- download_gretil(category: str) → downloads all texts for that category via wget
- download_dcs() → clones or pulls ambuda-org/dcs corpus
- download_archive_org(subject: str) → uses internetarchive library to fetch Sanskrit texts
- download_sanskritdocs(url: str) → scrapes and downloads from sanskritdocuments.org
- verify_downloads() → checks all expected files exist, logs missing ones
- upload_to_r2(local_path: Path) → uploads corpus backup to Cloudflare R2

Source URLs to use:
- GRETIL: https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/
- DCS: https://github.com/ambuda-org/dcs
- Archive.org: subject:"Sanskrit" mediatype:texts
```

### `pipeline/normaliser.py`
```
Build a SanskritNormaliser class using vidyut-lipi:
- to_devanagari(text: str, source_scheme: str) → str
  Converts from any scheme: ITRANS, HarvardKyoto, SLP1, Velthuis, IAST, Grantha
  Uses: from vidyut import Lipika, Scheme
- to_iast(devanagari: str) → str
- detect_scheme(text: str) → str  — auto-detect the input encoding
- clean_verse(text: str) → str    — remove metadata markers, standardise spacing
- split_verse_file(file_path: Path) → list[dict]
  Parses a TEI-XML or plain text file into list of {verse_id, devanagari, meta} dicts
```

### `pipeline/parser.py`
```
Build a SanskritParser class using vidyut:
- parse_verse(devanagari: str, verse_id: str) → list[WordRecord]
  For each word: extract dhatu, stem, vibhakti, vachana, linga, meaning_en
  Use: from vidyut import Kosha, Data
- parse_bulk(verses: list[dict]) → list[WordRecord]  — batch processing with progress bar
- identify_speaker(verse_context: str) → str | None   — return char_id or None
- identify_metre(devanagari: str) → str               — detect Sanskrit metre

WordRecord dataclass:
  pada_id, verse_id, position, surface_form, dhatu, stem,
  vibhakti, vachana, linga, purusha, lakara, meaning_en
```

### `pipeline/embedder.py`
```
Build an Embedder class:
- __init__(model_name: str = EMBEDDING_MODEL)
  Loads sentence-transformers model once, reuses for all calls
- embed_verse(text: str) → list[float]      — single verse
- embed_batch(texts: list[str], batch_size: int = 64) → list[list[float]]
  Shows tqdm progress bar
- embed_and_store(verses: list[dict]) → None
  Embeds + stores to ChromaDB + pgvector + Pinecone in one call
  Uses batch_size=64 for efficiency on free GPU
```

### `pipeline/science_linker.py`
```
Build a ScienceLinker class:
- search_arxiv(concept: str, max_results: int = 5) → list[PaperRecord]
- search_pubmed(concept: str, max_results: int = 5) → list[PaperRecord]
- score_relevance(concept_embedding: list[float], paper_abstract: str) → float
  Returns 0.0-1.0 cosine similarity between concept and paper
- link_concept(concept_id: str) → list[ScienceLinkRecord]
  Finds papers for concept, scores them, returns top matches
- run_weekly_update() → None
  Iterates all concepts, finds new papers, inserts new science_links rows
  Only inserts if confidence > 0.5 and DOI not already in DB

PaperRecord dataclass: doi, title, abstract, url, published_date, domain
ScienceLinkRecord dataclass: verse_id, concept_id, domain, modern_ref, modern_title, confidence
```

### `database/supabase_client.py`
```
Build a SupabaseClient class (singleton pattern):
- get_client() → Client        — returns singleton supabase client
- insert_verse(verse: VerseRecord) → None
- insert_word(word: WordRecord) → None
- insert_character(char: CharacterRecord) → None
- insert_concept(concept: ConceptRecord) → None
- insert_science_link(link: ScienceLinkRecord) → None
- bulk_insert_verses(verses: list[VerseRecord], batch_size: int = 100) → None
- get_verse(verse_id: str) → VerseRecord | None
- search_verses_semantic(embedding: list[float], limit: int = 10) → list[VerseRecord]
  Uses pgvector: SELECT * FROM verses ORDER BY embedding <=> %s LIMIT %s
- get_character(char_id: str) → CharacterRecord | None
- get_concept(concept_id: str) → ConceptRecord | None
```

### `graph/loader.py`
```
Build a GraphLoader class using py2neo:
- connect() → Graph           — connects to Neo4j Aura using env vars
- load_character(char: CharacterRecord) → None
  Creates MERGE (c:Character {char_id: ...}) with all properties
- load_relation(rel: RelationRecord) → None
  Creates MERGE relationship between two character nodes
- load_concept(concept: ConceptRecord) → None
- load_event(event: EventRecord) → None
- load_verse_mention(verse_id: str, char_id: str) → None
  Creates (v:Verse)-[:MENTIONS]->(c:Character) edge
- unify_cross_text_entities() → None
  Finds characters with same name_sa across texts, merges their nodes
  Uses: MATCH (a:Character), (b:Character) WHERE a.name_sa = b.name_sa AND a <> b MERGE ...
```

### `graph/queries.py`
```
Build a GraphQuery class with Cypher queries:
- get_character_relations(char_id: str) → dict
  Returns all direct relationships for a character
- find_path(from_char: str, to_char: str) → list
  Shortest path between two characters
- get_concept_network(concept_id: str, depth: int = 2) → dict
  All concepts within N hops
- get_character_events(char_id: str) → list[EventRecord]
- get_texts_mentioning_concept(concept_id: str) → list[str]
- export_for_d3(subgraph: str = "Mahabharata") → dict
  Returns {nodes: [...], links: [...]} format for D3.js force graph
```

### `vector/retriever.py`
```
Build a HybridRetriever class:
- __init__()
  Initialises ChromaDB, pgvector, Pinecone connections
- retrieve(query: str, k: int = 10) → list[VerseRecord]
  1. Embed the query
  2. Get top-k from ChromaDB (semantic)
  3. Get top-k from pgvector (hybrid SQL+vector)
  4. Merge, deduplicate, return union
- retrieve_with_graph(query: str, k: int = 5) → list[VerseRecord]
  After semantic retrieval, expand results using Neo4j graph neighbours
- rerank(query: str, candidates: list[VerseRecord]) → list[VerseRecord]
  Uses cross-encoder to rerank candidates by relevance to query
  Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (free, small)
```

### `ai/rag_chain.py`
```
Build a VedicRAG class:
- __init__()
  Sets up LangChain chain: retriever → prompt → LLM → output parser
- ask(question: str) → AnswerRecord
  Full pipeline: question → retrieve → inject → generate → return

AnswerRecord dataclass:
  answer: str
  source_verses: list[VerseRecord]    — exact shlokas cited
  characters_mentioned: list[str]     — char_ids
  science_links: list[ScienceLinkRecord]
  confidence: float

Prompt template (always use this structure):
  You are a scholar of ancient Sanskrit texts. Answer ONLY based on the provided Sanskrit verses.
  Always cite the exact verse ID. If you don't know, say "The texts do not address this directly."

  Sanskrit Verses (context):
  {context}

  Question: {question}

  Answer with: 1) Direct answer 2) Exact verse citation 3) Modern science parallel if available.
```

### `api/main.py`
```
FastAPI app with these settings:
- title="Vedic Intelligence System API"
- description="Query all ancient Sanskrit texts with AI"
- version="1.0.0"
- CORS enabled for all origins (public API)
- Include all routers from api/routers/
- Health check endpoint: GET /health → {"status": "ok", "version": "1.0.0"}
- Add Upstash Redis middleware for caching (TTL: 3600 seconds for verses, 300 for search)
```

### `api/routers/ask.py`
```
POST /ask
Request body: {"question": str, "language": str = "en"}
Response: AnswerRecord (see above)
- Call VedicRAG.ask(question)
- Cache result in Redis for 1 hour (key: hash of question)
- Log query + response time to Supabase analytics table
- Rate limit: 10 requests/minute per IP via Upstash

POST /search
Request body: {"query": str, "filters": {"source_text": str?, "era": str?, "character": str?}, "limit": int = 10}
Response: list[VerseRecord]
- Uses HybridRetriever.retrieve() then applies SQL filters
```

---

## 🔗 NEO4J GRAPH — Node and Edge Types

Always use exactly these labels and relationship types in Cypher.

**Node labels:**
- `Character` — properties: char_id, name_sa, name_devanagari, char_type, verse_count
- `Place` — properties: place_id, name_sa, modern_name, region
- `Concept` — properties: concept_id, name_sa, category, frequency
- `Event` — properties: event_id, title_en, yuga, event_type
- `Text` — properties: text_id, title, era, verse_count
- `Deity` — (subtype of Character) — properties: aspect, primary_text
- `Weapon` — properties: weapon_id, name_sa, wielder_id

**Relationship types (always UPPERCASE_WITH_UNDERSCORES):**
- `SON_OF`, `FATHER_OF`, `MOTHER_OF`, `DAUGHTER_OF`, `BROTHER_OF`, `SISTER_OF`
- `MARRIED_TO`, `DISCIPLE_OF`, `TEACHER_OF`
- `BATTLES`, `ALLY_OF`, `ENEMY_OF`
- `CURSED_BY`, `BLESSED_BY`, `KILLED_BY`, `BORN_FROM`
- `MENTIONS` — (Text/Verse)-[:MENTIONS]->(Character/Concept)
- `PARALLELS_SCIENCE` — (Concept)-[:PARALLELS_SCIENCE {domain, confidence}]->(Concept)
- `PRECEDES`, `FOLLOWS` — for event ordering
- `LOCATED_IN` — (Character/Event)-[:LOCATED_IN]->(Place)
- `APPEARS_IN` — (Character)-[:APPEARS_IN]->(Text)

---

## 📊 VISUALIZATION INSTRUCTIONS

### `viz/grafify_plots.R`
```r
# Always load these libraries
library(grafify)
library(dplyr)
library(ggplot2)

# DATA FORMAT expected from Supabase (fetch via API or export CSV):
# df_verses: columns = source_text, era, words_per_verse, concept_density, philosophy_score
# df_concepts: columns = concept_id, concept_name, era, frequency, category
# df_cooccurrence: columns = concept_a, concept_b, cooccurrence_count, era

# PLOTS TO BUILD:
# 1. plot_violin(df_verses, x_var=source_text, y_var=words_per_verse, fill_var=era)
# 2. plot_scatter(df_concepts, x_var=era_num, y_var=frequency, size_var=cooccurrence, colour_var=category)
# 3. plot_befafter(df_concepts_wide, col_before=vedic_freq, col_after=puranic_freq, id_var=concept_id)
# 4. posthoc_Tukey(model_concepts, specs="source_text") — which texts differ significantly
```

### `viz/network_graph.py`
```python
# Build D3.js-ready JSON from Neo4j data
# Output format for D3 force graph:
# {
#   "nodes": [{"id": "rama", "name": "Rāma", "type": "Character", "size": 150}],
#   "links": [{"source": "rama", "target": "ravana", "type": "BATTLES", "weight": 1}]
# }
# Filter options: by text (Mahabharata only), by era, by character type
# Export to vis/static/graph_data.json for the frontend to load
```

---

## 🚀 GITHUB ACTIONS WORKFLOWS

### `.github/workflows/pipeline.yml`
```yaml
# Run full corpus processing pipeline
# Trigger: manual + every Sunday at 2am IST
# Steps:
# 1. Checkout repo
# 2. Install dependencies
# 3. Run pipeline/downloader.py --check-new   (only download new texts)
# 4. Run pipeline/normaliser.py
# 5. Run pipeline/parser.py
# 6. Run pipeline/embedder.py --new-only
# 7. Run graph/loader.py --new-only
# 8. Notify on success/failure via GitHub issue comment
```

### `.github/workflows/science_linker.yml`
```yaml
# Auto-discover new science papers
# Trigger: every Monday at 3am IST
# Steps:
# 1. Run pipeline/science_linker.py --run-weekly-update
# 2. Log: how many new links added, which domains, avg confidence
# 3. Commit updated science_links count to docs/science_link_stats.md
```

---

## 🧪 TESTING CONVENTIONS

```python
# Every test file structure:
import pytest
from unittest.mock import Mock, patch

# Use fixtures for DB connections (mock them in tests)
@pytest.fixture
def mock_supabase():
    return Mock()

@pytest.fixture  
def mock_neo4j():
    return Mock()

# Every test must:
# 1. Test the happy path
# 2. Test with invalid input
# 3. Test with empty data
# Example:
def test_parse_verse_returns_word_records(mock_supabase):
    parser = SanskritParser()
    result = parser.parse_verse("धर्मक्षेत्रे कुरुक्षेत्रे", "BG.1.1")
    assert len(result) > 0
    assert all(hasattr(w, 'dhatu') for w in result)
```

---

## 💬 COPILOT CHAT — QUICK COMMANDS

Paste these directly into Copilot Chat to get specific things built:

```
"Build the downloader.py module following the vis project instructions"

"Build the complete schema.sql file with all 7 tables and indexes"

"Build the SanskritParser class in pipeline/parser.py using vidyut"

"Build the HybridRetriever class combining ChromaDB and pgvector"

"Build all FastAPI routers for the vis project API"

"Build the VedicRAG class with LangChain"

"Write tests for pipeline/parser.py"

"Build the docker-compose.yml for local dev with ChromaDB, PostgreSQL, Neo4j, Redis"

"Build the GitHub Actions workflow for weekly corpus processing"

"Build the GraphLoader class in graph/loader.py using py2neo and Neo4j"

"Build the science_linker.py to query arXiv and PubMed APIs"

"Build the grafify_plots.R visualization file"

"Build the D3.js force graph exporter in viz/network_graph.py"

"Build the complete .env.example file for the vis project"

"Set up LoRA fine-tuning in ai/finetune/train_lora.py for Mistral 7B"
```

---

## 📋 FIRST COMMANDS TO RUN TODAY

```bash
# 1. Create and clone repo
mkdir vis && cd vis && git init
cp /path/to/this/file .github/copilot-instructions.md

# 2. Create Python environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Copy env template
cp .env.example .env
# Edit .env with your Supabase, Neo4j, Pinecone keys

# 4. Install vidyut data
python -c "from vidyut import Data; Data.acquire()"

# 5. Set up database
python scripts/setup_supabase.py    # runs schema.sql

# 6. Download first corpus (Rigveda only to start)
python pipeline/downloader.py --source gretil --category rigveda

# 7. Run first parse test
python -c "
from pipeline.normaliser import SanskritNormaliser
from pipeline.parser import SanskritParser
n = SanskritNormaliser()
p = SanskritParser()
text = n.to_devanagari('dharmakSetre kurukSetre', 'HarvardKyoto')
words = p.parse_verse(text, 'BG.1.1')
print(f'Parsed {len(words)} words')
for w in words:
    print(f'  {w.surface_form} → root: {w.dhatu}, case: {w.vibhakti}')
"

# 8. Start the API server
uvicorn api.main:app --reload --port 8000
# Visit http://localhost:8000/docs for interactive API docs
```

---

## 🌐 DATA SOURCES — URLs and Methods

| Source | URL | Method | What to Get |
|--------|-----|--------|-------------|
| GRETIL | https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/ | wget recursive | All .txt Sanskrit texts |
| DCS | https://github.com/ambuda-org/dcs | git clone | Annotated XML corpus |
| Archive.org | https://archive.org | internetarchive CLI | Scanned books + manuscripts |
| sanskritdocs | https://sanskritdocuments.org/Sanskrit/ | requests + BeautifulSoup | Multi-encoding texts |
| Vedabase | https://vedabase.io/en/library/ | requests | Verse-structured Puranas |
| arXiv | https://arxiv.org/search/ | arxiv Python library | Modern science papers |
| PubMed | https://eutils.ncbi.nlm.nih.gov/entrez/eutils/ | requests + XML | Medical research papers |
| NASA ADS | https://api.adsabs.harvard.edu/v1/ | requests + API key (free) | Astronomy papers |

---

## ⚠️ IMPORTANT RULES — NEVER VIOLATE THESE

1. **Never hardcode API keys or passwords** — always use `.env` + `python-dotenv`
2. **Never delete corpus files** — only append, always backup to R2 first
3. **Never store embeddings in `.env`** — they go in ChromaDB/pgvector/Pinecone only
4. **Never use `print()` in production code** — use `from loguru import logger`
5. **Never write raw SQL strings** — use SQLAlchemy ORM or parameterised queries
6. **Never skip error handling in API routes** — always return proper HTTP status codes
7. **Always use batch operations** — never insert rows one-by-one into Supabase
8. **Always include `verse_id` in every log line** — makes debugging much easier
9. **Sanskrit text is always Unicode** — never encode/decode manually
10. **science_links.confidence must be 0.0–1.0** — validate before insert

---

*This file is the single source of truth for the VIS project.*
*Every module, every class, every function should align with these specifications.*
*When in doubt: simple, modular, well-tested, well-documented.*
