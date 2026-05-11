"""
api/main.py
===========
FastAPI REST API — the public interface for the
Vedic Intelligence System. All endpoints are free to use.
"""

import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ── Lazy-loaded globals ──────────────────────────────────
_embedder = None
_rag = None
_db = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from pipeline.embedder import Embedder
        _embedder = Embedder()
    return _embedder


def get_rag():
    global _rag
    if _rag is None:
        from ai.rag_chain import VedicRAG
        _rag = VedicRAG()
    return _rag


def get_db():
    global _db
    if _db is None:
        from database.supabase_client import SupabaseDB
        _db = SupabaseDB()
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VIS API starting up...")
    yield
    logger.info("VIS API shutting down.")


# ── App ──────────────────────────────────────────────────
app = FastAPI(
    title="Vedic Intelligence System API",
    description=(
        "Query all ancient Sanskrit texts — Vedas, Puranas, Mahabharata, "
        "Ramayana, Upanishads — with AI-powered semantic search and RAG Q&A. "
        "Free and open to all."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ────────────────────────────
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.time()-start:.3f}s"
    return response


# ════════════════════════════════════════════════════════
# HEALTH
# ════════════════════════════════════════════════════════
@app.get("/health", tags=["System"])
async def health():
    """API health check. Returns status and version."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "project": "Vedic Intelligence System",
        "docs": "/docs",
    }


@app.get("/stats", tags=["System"])
async def stats():
    """Returns database row counts for all tables."""
    try:
        db = get_db()
        return {"status": "ok", "tables": db.get_stats()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ════════════════════════════════════════════════════════
# ASK  — Main RAG endpoint
# ════════════════════════════════════════════════════════
from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    language: str = "en"
    k: int = 10         # retrieval count


class SearchRequest(BaseModel):
    query: str
    source_text_id: str | None = None
    era: str | None = None
    limit: int = 10


@app.post("/ask", tags=["AI"])
async def ask(req: AskRequest):
    """
    Ask any question about Sanskrit texts.
    Returns a cited answer with exact shloka references and modern science parallel.

    Example:
        POST /ask
        {"question": "What does Krishna say about duty without attachment?"}
    """
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    try:
        rag = get_rag()
        answer = rag.ask(req.question, k=req.k)
        return {
            "question": answer.question,
            "answer": answer.answer,
            "confidence": answer.confidence,
            "source_verses": [
                {
                    "verse_id": v.verse_id,
                    "text": v.text,
                    "similarity": v.similarity,
                    "source_text": v.source_text,
                }
                for v in answer.source_verses
            ],
            "characters_mentioned": answer.characters_mentioned,
            "science_links": answer.science_links,
            "model_used": answer.model_used,
        }
    except Exception as e:
        logger.error(f"/ask error: {e}")
        raise HTTPException(500, f"RAG pipeline error: {str(e)}")


# ════════════════════════════════════════════════════════
# SEARCH  — Semantic verse search
# ════════════════════════════════════════════════════════
@app.post("/search", tags=["Search"])
async def search(req: SearchRequest):
    """
    Semantic search across all 500K+ Sanskrit verses.
    Returns ranked results by meaning similarity.

    Example:
        POST /search
        {"query": "eternal soul", "source_text_id": "BG", "limit": 5}
    """
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    try:
        embedder = get_embedder()
        results = embedder.semantic_search(
            req.query, n_results=req.limit,
            filter_text=req.source_text_id
        )
        return {"query": req.query, "total": len(results), "results": results}
    except Exception as e:
        logger.error(f"/search error: {e}")
        raise HTTPException(500, str(e))


# ════════════════════════════════════════════════════════
# VERSE
# ════════════════════════════════════════════════════════
@app.get("/verse/{verse_id}", tags=["Texts"])
async def get_verse(verse_id: str):
    """
    Get a specific verse by ID.

    Verse ID format: TEXT.book.chapter.verse
    Examples: RV.1.1.1 / BG.2.47 / MBH.6.25.11

    Returns full verse with Devanagari, IAST, translation, and word analysis.
    """
    db = get_db()
    verse = db.get_verse(verse_id)
    if not verse:
        raise HTTPException(404, f"Verse '{verse_id}' not found")
    words = db.get_words_for_verse(verse_id)
    return {"verse": verse, "words": words, "word_count": len(words)}


@app.get("/verses", tags=["Texts"])
async def list_verses(
    source_text_id: str | None = None,
    era: str | None = None,
    limit: int = 20,
):
    """
    List verses with optional filters.

    Filters: source_text_id (RV/BG/MBH...), era (Vedic/Classical...)
    """
    db = get_db()
    verses = db.search_verses(source_text_id=source_text_id,
                               era=era, limit=limit)
    return {"total": len(verses), "verses": verses}


# ════════════════════════════════════════════════════════
# CHARACTER
# ════════════════════════════════════════════════════════
@app.get("/character/{char_id}", tags=["Characters"])
async def get_character(char_id: str):
    """
    Get complete profile of a Sanskrit character.

    Returns: name, aliases, relationships, verse count, attributes.
    Also returns their graph relationships from Neo4j.

    Examples: rama / krishna / arjuna / bhishma / ravana / hanuman
    """
    db = get_db()
    char = db.get_character(char_id)
    if not char:
        raise HTTPException(404, f"Character '{char_id}' not found")

    # Try to get graph relationships
    graph_data = {}
    try:
        from graph.loader import GraphLoader
        g = GraphLoader()
        graph_data = g.get_character_graph(char_id)
        g.close()
    except Exception:
        pass

    return {"character": char, "graph": graph_data}


@app.get("/characters", tags=["Characters"])
async def list_characters(
    name: str | None = None,
    char_type: str | None = None,
):
    """
    Search characters by name or type.

    Types: Deva / Asura / Human / Rishi / Animal
    """
    db = get_db()
    chars = db.search_characters(name_query=name, char_type=char_type)
    return {"total": len(chars), "characters": chars}


# ════════════════════════════════════════════════════════
# CONCEPT
# ════════════════════════════════════════════════════════
@app.get("/concept/{concept_id}", tags=["Concepts"])
async def get_concept(concept_id: str):
    """
    Get a Vedic concept with its definition and modern science parallel.

    Examples: dharma / karma / moksha / atman / brahman / yoga / prana
    """
    db = get_db()
    concept = db.get_concept(concept_id)
    if not concept:
        raise HTTPException(404, f"Concept '{concept_id}' not found")

    links = db.get_science_links(concept_id=concept_id, min_confidence=0.5)
    return {"concept": concept, "science_links": links,
            "science_link_count": len(links)}


@app.get("/concepts", tags=["Concepts"])
async def list_concepts(
    category: str | None = None,
):
    """
    List all mapped Sanskrit concepts.

    Categories: Philosophy / Science / Ritual / Social / Cosmic / Medicine
    """
    db = get_db()
    if category:
        concepts = db.get_concepts_by_category(category)
    else:
        # Return all without filter
        concepts = db.get_concepts_by_category("Philosophy") + \
                   db.get_concepts_by_category("Science") + \
                   db.get_concepts_by_category("Medicine")
    return {"total": len(concepts), "concepts": concepts}


# ════════════════════════════════════════════════════════
# SCIENCE LINKS
# ════════════════════════════════════════════════════════
@app.get("/science-links", tags=["Science"])
async def get_science_links(
    concept_id: str | None = None,
    domain: str | None = None,
    min_confidence: float = 0.5,
):
    """
    Get ancient↔modern science cross-references.

    Domains: Physics / Astronomy / Mathematics / Medicine /
             Neuroscience / Linguistics / Ecology / Economics /
             Architecture / Music / Futurism
    """
    db = get_db()
    links = db.get_science_links(concept_id=concept_id,
                                  domain=domain,
                                  min_confidence=min_confidence)
    return {"total": len(links), "links": links}


# ════════════════════════════════════════════════════════
# GRAPH
# ════════════════════════════════════════════════════════
@app.get("/graph/character/{char_id}", tags=["Graph"])
async def get_character_graph(char_id: str):
    """
    Returns D3.js-ready force graph of a character's relationships.
    Use this to build interactive network visualisations.
    """
    try:
        from graph.loader import GraphLoader
        g = GraphLoader()
        data = g.get_character_graph(char_id)
        g.close()
        return data
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/graph/path", tags=["Graph"])
async def find_path(from_char: str, to_char: str):
    """
    Finds the shortest relationship path between two characters.

    Example: /graph/path?from_char=arjuna&to_char=brahma
    """
    try:
        from graph.loader import GraphLoader
        g = GraphLoader()
        paths = g.find_path(from_char, to_char)
        g.close()
        return {"from": from_char, "to": to_char, "paths": paths}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/graph/export", tags=["Graph"])
async def export_graph(text_id: str | None = None, limit: int = 200):
    """
    Exports character graph as D3.js force-graph JSON.
    Use text_id to filter by a specific text (e.g. MBH, RAM).
    """
    try:
        from graph.loader import GraphLoader
        g = GraphLoader()
        data = g.export_for_d3(filter_text=text_id, limit=limit)
        g.close()
        return data
    except Exception as e:
        raise HTTPException(500, str(e))


# ════════════════════════════════════════════════════════
# TEXTS CATALOGUE
# ════════════════════════════════════════════════════════
@app.get("/texts", tags=["Texts"])
async def list_texts():
    """List all Sanskrit texts in the corpus with metadata."""
    TEXTS = [
        {"text_id": "RV",   "title": "Rigveda",           "era": "Vedic",        "verses": 10552},
        {"text_id": "SV",   "title": "Samaveda",          "era": "Vedic",        "verses": 1875},
        {"text_id": "YV",   "title": "Yajurveda",         "era": "Vedic",        "verses": 1875},
        {"text_id": "AV",   "title": "Atharvaveda",       "era": "Vedic",        "verses": 5987},
        {"text_id": "BG",   "title": "Bhagavad Gita",     "era": "Classical",    "verses": 700},
        {"text_id": "MBH",  "title": "Mahabharata",       "era": "Classical",    "verses": 100000},
        {"text_id": "RAM",  "title": "Valmiki Ramayana",  "era": "Classical",    "verses": 24000},
        {"text_id": "BHAG", "title": "Bhagavata Purana",  "era": "Classical",    "verses": 18000},
        {"text_id": "GAR",  "title": "Garuda Purana",     "era": "Classical",    "verses": 19000},
        {"text_id": "SHIV", "title": "Shiva Purana",      "era": "Classical",    "verses": 24000},
        {"text_id": "CS",   "title": "Charaka Samhita",   "era": "Classical",    "verses": 12000},
        {"text_id": "SS",   "title": "Sushruta Samhita",  "era": "Classical",    "verses": 9000},
        {"text_id": "AB",   "title": "Aryabhatiya",       "era": "Classical",    "verses": 118},
        {"text_id": "YS",   "title": "Yoga Sutras",       "era": "Classical",    "verses": 196},
        {"text_id": "ARTH", "title": "Arthashastra",      "era": "Classical",    "verses": 6000},
        {"text_id": "BU",   "title": "Brihadaranyaka Upanishad", "era": "Upanishadic", "verses": 2300},
    ]
    return {"total": len(TEXTS), "texts": TEXTS}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app",
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", 8000)),
                reload=True, log_level="info")
