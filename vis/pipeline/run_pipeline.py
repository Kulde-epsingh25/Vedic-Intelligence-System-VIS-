"""
pipeline/run_pipeline.py
========================
Master pipeline orchestrator. Runs the full 6-stage pipeline:
  Stage 1: Download corpus
  Stage 2: Normalise encodings
  Stage 3: Parse words (vidyut)
  Stage 4: Store in Supabase
  Stage 5: Build knowledge graph (Neo4j)
  Stage 6: Generate embeddings (ChromaDB)
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
import typer

load_dotenv()

# Configure logger
logger.remove()
logger.add(sys.stdout, level=os.getenv("LOG_LEVEL", "INFO"),
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add("logs/pipeline_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days")

from pipeline.downloader import CorpusDownloader
from pipeline.normaliser import SanskritNormaliser
from pipeline.parser import SanskritParser
from pipeline.embedder import Embedder

app = typer.Typer(name="vis-pipeline", help="VIS Sanskrit corpus pipeline")
CORPUS_DIR = Path(os.getenv("CORPUS_DIR", "./corpus"))


@app.command()
def download(
    method: str = typer.Option("all", help="all | gretil | dcs | individual"),
):
    """Stage 1: Download the Sanskrit corpus."""
    dl = CorpusDownloader(CORPUS_DIR)
    if method == "gretil":
        dl.clone_gretil_mirror()
    elif method == "dcs":
        dl.clone_dcs()
    elif method == "individual":
        dl.download_all_texts()
    else:
        dl.run_full_download()


@app.command()
def normalise(
    text_id: str = typer.Option("all", help="Specific text_id or 'all'"),
    limit: int = typer.Option(0, help="Limit verses (0=all)"),
):
    """Stage 2: Normalise encodings and extract verses."""
    n = SanskritNormaliser()
    all_verses = n.process_corpus_directory(CORPUS_DIR)
    if limit > 0:
        all_verses = all_verses[:limit]
    logger.info(f"Normalised {len(all_verses):,} verses total")
    return all_verses


@app.command()
def parse(
    limit: int = typer.Option(100, help="Verses to parse (start small to test)"),
):
    """Stage 3: Parse Sanskrit words with vidyut."""
    n = SanskritNormaliser()
    p = SanskritParser()

    # Get sample verses
    verses = n.process_corpus_directory(CORPUS_DIR)
    if limit:
        verses = verses[:limit]

    words = p.parse_bulk(verses)
    logger.info(f"Parsed {len(words):,} words from {len(verses):,} verses")

    # Print sample
    for w in words[:10]:
        logger.info(
            f"  {w.surface_form} | root:{w.dhatu} | "
            f"case:{w.vibhakti_name} | {w.meaning_en}"
        )
    return words


@app.command()
def embed(
    limit: int = typer.Option(1000, help="Verses to embed (0=all)"),
    batch_size: int = typer.Option(64, help="Embedding batch size"),
):
    """Stage 4: Generate verse embeddings and store in ChromaDB."""
    n = SanskritNormaliser()
    e = Embedder()

    verses = n.process_corpus_directory(CORPUS_DIR)
    if limit > 0:
        verses = verses[:limit]

    stored = e.embed_and_store_verses(verses, batch_size=batch_size)
    logger.success(f"Stored {stored:,} embeddings")

    # Test search
    results = e.semantic_search("What is dharma and duty?", n_results=3)
    logger.info("Sample search 'What is dharma and duty?':")
    for r in results:
        logger.info(f"  [{r['similarity']:.3f}] {r['verse_id']}: {r['text'][:80]}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    n: int = typer.Option(5, help="Number of results"),
    text: str = typer.Option(None, help="Filter by source text ID"),
):
    """Search the verse embeddings semantically."""
    e = Embedder()
    results = e.semantic_search(query, n_results=n, filter_text=text)
    print(f"\nTop {n} results for: '{query}'\n{'='*60}")
    for r in results:
        print(f"[{r['rank']}] {r['verse_id']} | similarity: {r['similarity']}")
        print(f"    {r['text'][:120]}")
        print()


@app.command()
def demo():
    """Quick demo: parse BG.1.1 and show full analysis."""
    n = SanskritNormaliser()
    p = SanskritParser()
    e = Embedder()

    # Famous first verse of Bhagavad Gita
    verse_text = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः"
    iast_text = "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ"
    verse_id = "BG.1.1"

    print("\n" + "="*60)
    print("VIS DEMO — Bhagavad Gita 1.1")
    print("="*60)
    print(f"\nDevanagari: {verse_text}")
    print(f"IAST:       {iast_text}")
    print(f"\nMetre: {n.detect_metre(verse_text)}")

    words = p.parse_verse(verse_text, verse_id)
    print(f"\nWord Analysis ({len(words)} words):")
    print("-"*50)
    for w in words:
        print(f"  [{w.position}] {w.surface_form}")
        print(f"       Root (dhatu): {w.dhatu or 'N/A'}")
        print(f"       Case: {w.vibhakti_name or 'N/A'}")
        print(f"       Number: {w.vachana_name or 'N/A'}")
        print(f"       Gender: {w.linga_name or 'N/A'}")
        print(f"       Meaning: {w.meaning_en or 'N/A'}")
        print()

    entities = p.extract_entities(verse_text, iast_text)
    print(f"Entities: {entities}")

    vec = e.embed_text(f"{iast_text} In the field of dharma, in Kurukshetra")
    print(f"\nEmbedding: 768-dim vector, first 5: {vec[:5]}")
    print("\nChromaDB stats:", e.get_stats())


@app.command()
def full(
    download_corpus: bool = typer.Option(True, help="Run download stage"),
    embed_limit: int = typer.Option(5000, help="Max verses to embed"),
):
    """Run the full pipeline end-to-end."""
    start = time.time()
    logger.info("Starting full VIS pipeline...")

    if download_corpus:
        dl = CorpusDownloader(CORPUS_DIR)
        dl.run_full_download()

    n = SanskritNormaliser()
    verses = n.process_corpus_directory(CORPUS_DIR)

    if verses:
        p = SanskritParser()
        sample = verses[:min(200, len(verses))]
        words = p.parse_bulk(sample, show_progress=True)
        logger.info(f"Parsed {len(words):,} words from sample")

        e = Embedder()
        embed_verses = verses[:embed_limit]
        e.embed_and_store_verses(embed_verses)

    elapsed = time.time() - start
    logger.success(f"Pipeline complete in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    app()
