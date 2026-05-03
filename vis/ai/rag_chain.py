"""
AI RAG (Retrieval-Augmented Generation) chain for answering Sanskrit questions.

This module combines information retrieval with LLM inference to generate
answers grounded in Sanskrit texts with source citations.
"""

from typing import Optional
from loguru import logger
import os
from datetime import datetime

from database.models import AnswerRecord, VerseRecord, ScienceLinkRecord
from vector.retriever import HybridRetriever
from database.supabase_client import SupabaseClient


class VedicRAG:
    """RAG pipeline for answering questions about Sanskrit texts."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize VedicRAG with LangChain and retriever.

        Args:
            model_name: Optional LLM model name override

        Example:
            >>> rag = VedicRAG()
            >>> answer = rag.ask("What is dharma?")
            >>> print(answer.answer)
        """
        try:
            from langchain.llms import HuggingFacePipeline
            from langchain.prompts import PromptTemplate
            from langchain.chains import LLMChain
        except ImportError:
            logger.error("LangChain not installed")
            raise ImportError("Install via: pip install langchain langchain-community")

        self.retriever = HybridRetriever()
        self.db_client = SupabaseClient()
        self.model_name = model_name or os.getenv(
            "LLM_MODEL",
            "mistralai/Mistral-7B-Instruct-v0.2"
        )

        # Initialize LLM (lazy-loaded on first use)
        self.llm = None
        self.chain = None

        logger.info(f"VedicRAG initialized with model: {self.model_name}")

    def _get_llm(self):
        """Lazy-load LLM."""
        if self.llm is None:
            try:
                from langchain.llms import HuggingFacePipeline
                from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

                logger.info(f"Loading LLM: {self.model_name}")

                # Load model and tokenizer
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    load_in_8bit=True,  # Quantized for efficiency
                    device_map="auto"
                )

                # Create text generation pipeline
                text_gen_pipeline = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    max_length=512,
                    temperature=0.7,
                    top_p=0.95,
                )

                self.llm = HuggingFacePipeline(model_id=self.model_name, pipeline=text_gen_pipeline)
                logger.info("LLM loaded successfully")

            except Exception as e:
                logger.error(f"Error loading LLM: {e}")
                logger.warning("Falling back to mock LLM for testing")
                self.llm = MockLLM()

        return self.llm

    def ask(self, question: str, language: str = "en") -> AnswerRecord:
        """
        Answer a question about Sanskrit texts.

        Args:
            question: User question in English or Sanskrit
            language: Response language ("en" or "hi")

        Returns:
            AnswerRecord with answer, sources, and science links

        Example:
            >>> rag = VedicRAG()
            >>> answer = rag.ask("What does the Bhagavad Gita teach about duty?")
            >>> print(f"Answer: {answer.answer}")
            >>> print(f"Sources: {[v.verse_id for v in answer.source_verses]}")
        """
        try:
            logger.info(f"Processing question: {question}")

            # 1. Retrieve relevant verses
            source_verses = self.retriever.retrieve(question, k=5)
            if not source_verses:
                logger.warning("No verses retrieved")
                return AnswerRecord(
                    answer="The texts do not address this directly.",
                    source_verses=[],
                    characters_mentioned=[],
                    science_links=[],
                    confidence=0.0,
                    timestamp=datetime.now()
                )

            # 2. Rerank for better relevance
            source_verses = self.retriever.rerank(question, source_verses)

            # 3. Build context from verses
            context = self._build_context(source_verses)

            # 4. Generate answer using LLM
            answer_text = self._generate_answer(question, context)

            # 5. Extract characters mentioned
            characters = self._extract_characters(source_verses)

            # 6. Find science links
            science_links = self._find_science_links(source_verses)

            # 7. Calculate confidence
            confidence = self._calculate_confidence(source_verses)

            # 8. Log query
            self.db_client.log_query(
                question=question,
                answer_verse_ids=[v.verse_id for v in source_verses],
                response_time_ms=0  # In production, measure actual time
            )

            answer_record = AnswerRecord(
                answer=answer_text,
                source_verses=source_verses,
                characters_mentioned=characters,
                science_links=science_links,
                confidence=confidence,
                timestamp=datetime.now()
            )

            logger.info(f"Answer generated with {len(source_verses)} sources")
            return answer_record

        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return AnswerRecord(
                answer="An error occurred while processing your question.",
                source_verses=[],
                characters_mentioned=[],
                science_links=[],
                confidence=0.0,
                timestamp=datetime.now()
            )

    def _build_context(self, verses: list) -> str:
        """Build context from retrieved verses."""
        context_parts = []
        for verse in verses[:5]:  # Limit to 5 for context length
            context_parts.append(f"[{verse.verse_id}] {verse.iast or verse.devanagari}")
            if verse.translation_en:
                context_parts.append(f"Translation: {verse.translation_en}")

        return "\n".join(context_parts)

    def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using LLM."""
        try:
            prompt = f"""You are a scholar of ancient Sanskrit texts. Answer ONLY based on the provided Sanskrit verses.
Always cite the exact verse ID. If you don't know, say "The texts do not address this directly."

Sanskrit Verses (context):
{context}

Question: {question}

Answer with: 1) Direct answer 2) Exact verse citation 3) Modern science parallel if available.

Answer:"""

            # For now, return a structured response
            # In production, would call self.llm.predict(prompt)
            logger.debug("Generating answer (mock LLM)")

            answer = f"Based on the retrieved verses, the question about '{question}' is addressed in the traditional texts. [Mock LLM response pending actual model deployment]"
            return answer

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Unable to generate answer at this time."

    def _extract_characters(self, verses: list) -> list:
        """Extract character IDs mentioned in verses."""
        characters = set()
        for verse in verses:
            if verse.speaker_id:
                characters.add(verse.speaker_id)
            if verse.addressed_to:
                characters.add(verse.addressed_to)
            if verse.topics:
                characters.update(verse.topics[:3])  # Limit to 3 topics
        return list(characters)

    def _find_science_links(self, verses: list) -> list:
        """Find science links related to verses and concepts."""
        science_links = []
        # In production, would query science_links table for related papers
        logger.debug(f"Found {len(science_links)} science links")
        return science_links

    def _calculate_confidence(self, verses: list) -> float:
        """Calculate confidence score based on retrieval quality."""
        if not verses:
            return 0.0
        # Simple heuristic: more sources = higher confidence
        confidence = min(1.0, len(verses) / 5.0)
        return confidence


class MockLLM:
    """Mock LLM for testing without loading actual model."""

    def predict(self, prompt: str) -> str:
        """Return mock response."""
        return "This is a mock LLM response. Deploy actual Mistral 7B for real answers."

    def __call__(self, prompt: str) -> str:
        """Allow callable interface."""
        return self.predict(prompt)
