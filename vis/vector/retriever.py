"""
Vector retriever module for hybrid semantic search.

This module provides unified retrieval across ChromaDB (local), pgvector (Supabase),
and Pinecone (cloud) with reranking using cross-encoders.
"""

from typing import List, Optional, Set
from loguru import logger
from database.models import VerseRecord
from pipeline.embedder import Embedder
import os


class HybridRetriever:
    """Unified retriever combining multiple vector stores and hybrid search."""

    def __init__(self, embedder: Optional[Embedder] = None):
        """
        Initialize HybridRetriever with vector store connections.

        Args:
            embedder: Optional Embedder instance (creates new if not provided)

        Example:
            >>> retriever = HybridRetriever()
            >>> results = retriever.retrieve("What is dharma?")
        """
        self.embedder = embedder or Embedder()

        # Initialize vector stores (lazy loading)
        self.chroma_store = None
        self.pgvector_client = None
        self.pinecone_store = None
        self.reranker = None

        logger.info("HybridRetriever initialized")

    def _get_chroma_store(self):
        """Lazy-load ChromaDB store."""
        if self.chroma_store is None:
            try:
                import chromadb
                self.chroma_store = chromadb.Client()
                logger.info("ChromaDB connected")
            except Exception as e:
                logger.error(f"Error connecting to ChromaDB: {e}")
        return self.chroma_store

    def _get_pgvector_client(self):
        """Lazy-load Supabase/pgvector client."""
        if self.pgvector_client is None:
            try:
                from database.supabase_client import SupabaseClient
                self.pgvector_client = SupabaseClient()
                logger.info("pgvector/Supabase connected")
            except Exception as e:
                logger.error(f"Error connecting to pgvector: {e}")
        return self.pgvector_client

    def _get_reranker(self):
        """Lazy-load cross-encoder reranker."""
        if self.reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder(
                    "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    max_length=512
                )
                logger.info("Cross-encoder reranker loaded")
            except Exception as e:
                logger.error(f"Error loading reranker: {e}")
        return self.reranker

    def retrieve(
        self,
        query: str,
        k: int = 10,
        filters: Optional[dict] = None
    ) -> List[VerseRecord]:
        """
        Retrieve verses using hybrid semantic search.

        Args:
            query: Search query
            k: Number of results to retrieve
            filters: Optional filters (source_text, era, character, etc.)

        Returns:
            List of VerseRecords ranked by relevance

        Example:
            >>> retriever = HybridRetriever()
            >>> results = retriever.retrieve("dharma and duty", k=5)
            >>> for verse in results:
            ...     print(f"{verse.verse_id}: {verse.iast}")
        """
        try:
            # Embed query
            query_embedding = self.embedder.embed_verse(query)

            results_set: Set[str] = set()
            results_dict = {}

            # 1. Retrieve from ChromaDB
            chroma_results = self._retrieve_from_chroma(query, k)
            for verse_id, score in chroma_results:
                results_set.add(verse_id)
                results_dict[verse_id] = score

            # 2. Retrieve from pgvector (Supabase)
            pgvector_results = self._retrieve_from_pgvector(query_embedding, k, filters)
            for verse in pgvector_results:
                results_set.add(verse.verse_id)
                results_dict[verse.verse_id] = verse

            # Merge and deduplicate
            merged_results = []
            for verse_id in results_set:
                item = results_dict.get(verse_id)
                if isinstance(item, VerseRecord):
                    merged_results.append(item)
                elif isinstance(item, tuple):
                    # Fetch full verse from DB
                    client = self._get_pgvector_client()
                    if client:
                        verse = client.get_verse(verse_id)
                        if verse:
                            merged_results.append(verse)

            logger.info(f"Retrieved {len(merged_results)} verses from hybrid search")
            return merged_results

        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            return []

    def retrieve_with_graph(
        self,
        query: str,
        k: int = 5,
        expand_depth: int = 1
    ) -> List[VerseRecord]:
        """
        Retrieve verses and expand results using knowledge graph neighbors.

        Args:
            query: Search query
            k: Initial results to retrieve
            expand_depth: Hops in graph for expansion

        Returns:
            Expanded list of VerseRecords

        Example:
            >>> retriever = HybridRetriever()
            >>> results = retriever.retrieve_with_graph("Krishna and Arjuna", expand_depth=2)
        """
        try:
            # First, retrieve base results
            base_results = self.retrieve(query, k=k)

            # For now, return base results (graph expansion requires Neo4j)
            # In future, expand via knowledge graph relationships
            logger.info(f"Retrieved {len(base_results)} base results (graph expansion pending)")
            return base_results

        except Exception as e:
            logger.error(f"Error in graph-based retrieval: {e}")
            return self.retrieve(query, k=k)

    def rerank(self, query: str, candidates: List[VerseRecord]) -> List[VerseRecord]:
        """
        Rerank candidates using cross-encoder.

        Args:
            query: Original query
            candidates: Candidate verses to rerank

        Returns:
            Reranked verses (best matches first)

        Example:
            >>> retriever = HybridRetriever()
            >>> candidates = retriever.retrieve("dharma", k=20)
            >>> reranked = retriever.rerank("dharma and duty", candidates)
        """
        if not candidates or len(candidates) == 0:
            return candidates

        try:
            reranker = self._get_reranker()
            if not reranker:
                logger.warning("Reranker not available, returning original order")
                return candidates

            # Prepare pairs: (query, verse_text)
            pairs = [
                [query, verse.devanagari or verse.iast or ""]
                for verse in candidates
            ]

            # Score with cross-encoder
            scores = reranker.predict(pairs)

            # Sort by score
            scored_verses = list(zip(candidates, scores))
            scored_verses.sort(key=lambda x: x[1], reverse=True)

            reranked = [verse for verse, score in scored_verses]
            logger.debug(f"Reranked {len(reranked)} verses")

            return reranked

        except Exception as e:
            logger.error(f"Error reranking: {e}")
            return candidates

    def _retrieve_from_chroma(self, query: str, k: int) -> List[tuple]:
        """
        Retrieve from ChromaDB (local vector store).

        Returns:
            List of (verse_id, score) tuples
        """
        try:
            chroma = self._get_chroma_store()
            if not chroma:
                return []

            # In production, would query from indexed collection
            # For now, return empty (requires collection setup)
            logger.debug("ChromaDB retrieval (not yet indexed)")
            return []

        except Exception as e:
            logger.warning(f"ChromaDB retrieval failed: {e}")
            return []

    def _retrieve_from_pgvector(
        self,
        embedding: List[float],
        k: int,
        filters: Optional[dict]
    ) -> List[VerseRecord]:
        """
        Retrieve from Supabase pgvector.

        Returns:
            List of VerseRecords
        """
        try:
            client = self._get_pgvector_client()
            if not client:
                return []

            # In production, would use pgvector similarity operator: <=>
            # For now, return SQL-based results with optional filters
            source_text = filters.get("source_text") if filters else None
            era = filters.get("era") if filters else None

            # Placeholder: retrieve top verses by era/source
            verses = []
            logger.debug(f"pgvector retrieval (k={k}, source={source_text}, era={era})")

            return verses

        except Exception as e:
            logger.warning(f"pgvector retrieval failed: {e}")
            return []
