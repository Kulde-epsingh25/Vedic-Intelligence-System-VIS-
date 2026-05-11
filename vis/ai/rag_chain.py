"""
ai/rag_chain.py
===============
Retrieval-Augmented Generation (RAG) pipeline.
Ask any question about Sanskrit texts → get a cited, verse-level answer
with modern science parallel included.

Flow:
  question → embed → ChromaDB retrieve → Neo4j expand
  → rerank → LLM generate → cited AnswerRecord
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

SYSTEM_PROMPT = """You are a scholar of ancient Sanskrit texts (Vedas, Mahabharata, 
Ramayana, Puranas, Upanishads). Answer questions ONLY using the provided verse context.

Rules:
1. Always cite the exact verse ID (e.g. BG.2.47, RV.1.164.46)
2. Include the Devanagari/IAST of the verse you are citing
3. Explain the Sanskrit terms used
4. If a modern science parallel exists in context, include it
5. If the texts do not address the question, say so honestly
6. Be precise — do not add information not in the provided verses

Format your answer as:
ANSWER: [your explanation]
CITED VERSE: [verse_id] — [iast text]
MEANING: [what the verse says]
MODERN PARALLEL: [science connection if available]
"""

USER_TEMPLATE = """Sanskrit Verse Context:
{context}

Question: {question}

Provide a detailed answer citing the exact verses."""


@dataclass
class SourceVerse:
    verse_id: str
    text: str
    similarity: float
    source_text: str = ""
    iast: str = ""


@dataclass
class AnswerRecord:
    """Complete answer with citations and science links."""
    question: str
    answer: str
    source_verses: list[SourceVerse] = field(default_factory=list)
    characters_mentioned: list[str] = field(default_factory=list)
    science_links: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    model_used: str = ""
    tokens_used: int = 0


class VedicRAG:
    """
    The central question-answering engine for all Sanskrit texts.

    Uses:
        - ChromaDB semantic search (vector retrieval)
        - Neo4j graph expansion (entity-based retrieval)
        - Cross-encoder reranking (quality filter)
        - Mistral/LLaMA generation (answer synthesis)

    Example:
        >>> rag = VedicRAG()
        >>> answer = rag.ask("What does Krishna say about duty in the Gita?")
        >>> print(answer.answer)
        >>> print(answer.source_verses[0].verse_id)
    """

    def __init__(self):
        self.embedder = None
        self.graph = None
        self.reranker = None
        self.llm = None
        self._init_components()

    def _init_components(self):
        """Initialise all components (lazy loading)."""
        # Embedder + ChromaDB
        try:
            from pipeline.embedder import Embedder
            self.embedder = Embedder()
            logger.success("Embedder initialised")
        except Exception as e:
            logger.warning(f"Embedder not available: {e}")

        # Neo4j graph
        try:
            from graph.loader import GraphLoader
            self.graph = GraphLoader()
            logger.success("Graph loader initialised")
        except Exception as e:
            logger.warning(f"Graph not available: {e}")

        # Cross-encoder reranker
        try:
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder(RERANKER_MODEL)
            logger.success("Reranker loaded")
        except Exception as e:
            logger.warning(f"Reranker not available: {e}")

        # LLM (HuggingFace pipeline, free)
        try:
            import torch
            from transformers import pipeline as hf_pipeline
            logger.info(f"Loading LLM: {LLM_MODEL} (this may take a few minutes)...")
            device = 0 if torch.cuda.is_available() else -1
            self.llm = hf_pipeline(
                "text-generation",
                model=LLM_MODEL,
                device=device,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                max_new_tokens=512,
                temperature=0.3,
                do_sample=True,
                return_full_text=False,
            )
            logger.success(f"LLM loaded: {LLM_MODEL}")
        except Exception as e:
            logger.warning(f"LLM not loaded: {e}")
            logger.info("Running in retrieval-only mode (no generation)")

    def retrieve(self, question: str, k: int = 10) -> list[SourceVerse]:
        """
        Retrieves relevant verses using semantic search.

        Args:
            question: User question
            k: Number of candidates to retrieve

        Returns:
            list[SourceVerse]: Top matching verses
        """
        if self.embedder is None:
            return []

        results = self.embedder.semantic_search(question, n_results=k)
        return [
            SourceVerse(
                verse_id=r["verse_id"],
                text=r["text"],
                similarity=r["similarity"],
                source_text=r.get("metadata", {}).get("source_text_id", ""),
            )
            for r in results
        ]

    def rerank(self, question: str,
               candidates: list[SourceVerse]) -> list[SourceVerse]:
        """
        Reranks candidates using cross-encoder for better precision.

        Args:
            question: Original question
            candidates: Retrieved verses

        Returns:
            list[SourceVerse]: Reranked, best candidates first
        """
        if self.reranker is None or not candidates:
            return candidates[:5]

        pairs = [[question, c.text] for c in candidates]
        try:
            scores = self.reranker.predict(pairs)
            ranked = sorted(zip(scores, candidates),
                            key=lambda x: x[0], reverse=True)
            return [c for _, c in ranked[:5]]
        except Exception as e:
            logger.warning(f"Reranking failed: {e}")
            return candidates[:5]

    def generate(self, question: str,
                 verses: list[SourceVerse]) -> str:
        """
        Generates a cited answer from retrieved verses.

        Args:
            question: User question
            verses: Top reranked verses as context

        Returns:
            str: Generated answer text
        """
        context = "\n\n".join([
            f"[{i+1}] {v.verse_id}\n{v.text}"
            for i, v in enumerate(verses)
        ])

        prompt = f"{SYSTEM_PROMPT}\n\n{USER_TEMPLATE.format(context=context, question=question)}"

        if self.llm is None:
            # Fallback: template-based answer without LLM
            return self._template_answer(question, verses)

        try:
            result = self.llm(prompt)
            return result[0]["generated_text"].strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._template_answer(question, verses)

    def _template_answer(self, question: str,
                         verses: list[SourceVerse]) -> str:
        """Template-based answer when no LLM is available."""
        if not verses:
            return "No relevant verses found for this question."

        top = verses[0]
        lines = [
            f"Based on the Sanskrit texts, the most relevant verse is:",
            f"",
            f"CITED VERSE: {top.verse_id}",
            f"TEXT: {top.text}",
            f"",
            f"Similarity to your question: {top.similarity:.1%}",
        ]
        if len(verses) > 1:
            lines += ["", "Additional related verses:"]
            for v in verses[1:3]:
                lines.append(f"  • {v.verse_id}: {v.text[:80]}...")

        return "\n".join(lines)

    def extract_mentioned_characters(self, answer_text: str) -> list[str]:
        """Extracts character IDs mentioned in the answer."""
        known = {
            "krishna": "Krishna", "arjuna": "Arjuna",
            "rama": "Rama", "sita": "Sita",
            "hanuman": "Hanuman", "ravana": "Ravana",
            "yudhishthira": "Yudhishthira", "bhima": "Bhima",
            "drona": "Drona", "karna": "Karna",
            "bhishma": "Bhishma", "vyasa": "Vyasa",
            "vishnu": "Vishnu", "shiva": "Shiva",
            "brahma": "Brahma", "indra": "Indra",
        }
        found = []
        answer_lower = answer_text.lower()
        for char_id, name in known.items():
            if name.lower() in answer_lower or char_id in answer_lower:
                found.append(char_id)
        return found

    def ask(self, question: str, k: int = 10) -> AnswerRecord:
        """
        Full RAG pipeline: question → cited Sanskrit answer.

        Args:
            question: Any question about Sanskrit texts
            k: Number of verses to retrieve

        Returns:
            AnswerRecord: Complete answer with citations
        """
        logger.info(f"Processing question: {question[:80]}...")

        # Step 1: Retrieve
        candidates = self.retrieve(question, k=k)
        if not candidates:
            return AnswerRecord(
                question=question,
                answer="The corpus is not yet loaded. Please run: python pipeline/run_pipeline.py embed",
                confidence=0.0
            )

        # Step 2: Rerank
        top_verses = self.rerank(question, candidates)

        # Step 3: Generate
        answer_text = self.generate(question, top_verses)

        # Step 4: Extract entities
        mentioned_chars = self.extract_mentioned_characters(answer_text)

        # Step 5: Calculate confidence
        confidence = sum(v.similarity for v in top_verses) / len(top_verses) if top_verses else 0.0

        return AnswerRecord(
            question=question,
            answer=answer_text,
            source_verses=top_verses,
            characters_mentioned=mentioned_chars,
            confidence=round(confidence, 3),
            model_used=LLM_MODEL,
        )
