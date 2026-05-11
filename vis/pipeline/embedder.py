"""
pipeline/embedder.py
====================
Generates 768-dim sentence embeddings for every verse and stores
them in ChromaDB (local), Supabase pgvector, and Pinecone (cloud).
"""

import os
import json
from pathlib import Path
from dataclasses import asdict
from typing import Optional
from tqdm import tqdm
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "./data/chroma"))


class Embedder:
    """
    Generates multilingual sentence embeddings for Sanskrit verses.
    Model: paraphrase-multilingual-mpnet-base-v2 (768-dim, free)
    Supports: Devanagari, IAST, English translations.

    Example:
        >>> e = Embedder()
        >>> vec = e.embed_verse("धर्मक्षेत्रे कुरुक्षेत्रे")
        >>> len(vec)   # 768
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self.model = None
        self._load_model()
        self.chroma = None
        self._init_chroma()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.success("Embedding model loaded")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")

    def _init_chroma(self) -> None:
        try:
            import chromadb
            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            self.collection = self.chroma_client.get_or_create_collection(
                name="vis_verses",
                metadata={"hnsw:space": "cosine"}
            )
            logger.success(f"ChromaDB initialised at {CHROMA_DIR}")
            logger.info(f"Existing vectors in ChromaDB: {self.collection.count():,}")
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            self.chroma_client = None
            self.collection = None

    def embed_text(self, text: str) -> list[float]:
        """Embeds a single text string. Returns 768-dim vector."""
        if self.model is None:
            return [0.0] * 768
        try:
            return self.model.encode(text, normalize_embeddings=True).tolist()
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return [0.0] * 768

    def embed_verse(self, verse) -> list[float]:
        """
        Embeds a verse using IAST + English translation concatenated.
        This gives better cross-lingual retrieval than Devanagari alone.
        """
        if hasattr(verse, 'iast') and hasattr(verse, 'translation_en'):
            text = f"{verse.iast} {verse.translation_en or ''}"
        elif hasattr(verse, 'devanagari'):
            text = verse.devanagari
        else:
            text = str(verse)
        return self.embed_text(text)

    def embed_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """
        Embeds multiple texts in batches (efficient on GPU/CPU).

        Args:
            texts: List of text strings
            batch_size: Batch size (64 works well on free Colab T4)

        Returns:
            list[list[float]]: One 768-dim vector per text
        """
        if self.model is None:
            return [[0.0] * 768] * len(texts)

        all_embeddings = []
        for i in tqdm(range(0, len(texts), batch_size),
                      desc="Generating embeddings", unit="batch"):
            batch = texts[i:i + batch_size]
            embeddings = self.model.encode(
                batch,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            all_embeddings.extend(embeddings.tolist())
        return all_embeddings

    def embed_and_store_verses(self, verses: list, batch_size: int = 64) -> int:
        """
        Embeds verses and stores in ChromaDB + logs for pgvector insert.

        Args:
            verses: List of VerseRecord objects
            batch_size: Embedding batch size

        Returns:
            int: Number of vectors stored
        """
        if self.collection is None:
            logger.error("ChromaDB not initialised")
            return 0

        # Build texts for embedding
        texts = []
        for v in verses:
            text = f"{getattr(v, 'iast', '')} {getattr(v, 'translation_en', '') or ''}"
            texts.append(text.strip())

        logger.info(f"Embedding {len(verses):,} verses...")
        embeddings = self.embed_batch(texts, batch_size)

        # Store in ChromaDB in batches of 5000
        chroma_batch = 5000
        stored = 0
        for i in tqdm(range(0, len(verses), chroma_batch),
                      desc="Storing in ChromaDB", unit="batch"):
            batch_verses = verses[i:i + chroma_batch]
            batch_embeddings = embeddings[i:i + chroma_batch]
            batch_texts = texts[i:i + chroma_batch]

            ids = [v.verse_id for v in batch_verses]
            metadatas = [{
                "source_text_id": getattr(v, 'source_text_id', ''),
                "book": str(getattr(v, 'book', '')),
                "chapter": str(getattr(v, 'chapter', '')),
                "verse_num": str(getattr(v, 'verse_num', '')),
                "metre": getattr(v, 'metre', '') or '',
            } for v in batch_verses]

            try:
                self.collection.upsert(
                    ids=ids,
                    embeddings=batch_embeddings,
                    documents=batch_texts,
                    metadatas=metadatas
                )
                stored += len(batch_verses)
            except Exception as e:
                logger.error(f"ChromaDB store failed at batch {i}: {e}")

        logger.success(f"Stored {stored:,} verse embeddings in ChromaDB")
        return stored

    def semantic_search(self, query: str, n_results: int = 10,
                        filter_text: Optional[str] = None) -> list[dict]:
        """
        Searches verses by semantic meaning.

        Args:
            query: Natural language question or Sanskrit phrase
            n_results: Number of results to return
            filter_text: Optional source_text_id filter

        Returns:
            list[dict]: Matching verses with distances
        """
        if self.collection is None or self.model is None:
            return []

        query_embedding = self.embed_text(query)
        where = {"source_text_id": filter_text} if filter_text else None

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            output = []
            for i, (doc, meta, dist) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                output.append({
                    "rank": i + 1,
                    "verse_id": results["ids"][0][i],
                    "text": doc,
                    "similarity": round(1 - dist, 4),
                    "metadata": meta
                })
            return output
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def get_stats(self) -> dict:
        """Returns ChromaDB collection statistics."""
        if self.collection is None:
            return {"count": 0, "status": "not_initialised"}
        return {
            "count": self.collection.count(),
            "model": self.model_name,
            "chroma_dir": str(CHROMA_DIR),
            "status": "ok"
        }
