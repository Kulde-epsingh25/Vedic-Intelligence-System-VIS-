"""
Ask router for question answering endpoints.

This module exposes the /ask endpoint powered by the VedicRAG pipeline.
"""

from fastapi import APIRouter, HTTPException

from api.schemas import AnswerResponse, AskRequest, SearchRequest, SearchResponse
from ai.rag_chain import VedicRAG

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(request: AskRequest) -> AnswerResponse:
    """
    Answer a Sanskrit question using the RAG pipeline.

    Args:
        request: AskRequest payload.

    Returns:
        AnswerResponse with grounded answer data.

    Example:
        >>> payload = AskRequest(question="What is dharma?")
        >>> response = await ask_question(payload)
    """
    try:
        rag = VedicRAG()
        answer = rag.ask(request.question, language=request.language)
        return AnswerResponse(
            answer=answer.answer,
            source_verses=[
                {
                    "verse_id": verse.verse_id,
                    "source_text": verse.source_text,
                    "devanagari": verse.devanagari,
                    "iast": verse.iast,
                    "translation_en": verse.translation_en,
                    "metre": verse.metre,
                    "era": verse.era,
                    "speaker_id": verse.speaker_id,
                }
                for verse in answer.source_verses
            ],
            characters_mentioned=answer.characters_mentioned,
            science_links=[
                {
                    "domain": link.domain,
                    "modern_title": link.modern_title or "",
                    "confidence": link.confidence,
                    "url": link.modern_ref,
                }
                for link in answer.science_links
            ],
            confidence=answer.confidence,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/search", response_model=SearchResponse)
async def search_verses(request: SearchRequest) -> SearchResponse:
    """
    Search verses using the hybrid retriever.

    Args:
        request: SearchRequest payload.

    Returns:
        SearchResponse with matching verses.

    Example:
        >>> payload = SearchRequest(query="dharma", limit=5)
        >>> response = await search_verses(payload)
    """
    try:
        from vector.retriever import HybridRetriever

        retriever = HybridRetriever()
        verses = retriever.retrieve(
            request.query,
            k=request.limit,
            filters={
                "source_text": request.source_text,
                "era": request.era,
                "character": request.character,
            },
        )
        return SearchResponse(
            results=[
                {
                    "verse_id": verse.verse_id,
                    "source_text": verse.source_text,
                    "devanagari": verse.devanagari,
                    "iast": verse.iast,
                    "translation_en": verse.translation_en,
                    "metre": verse.metre,
                    "era": verse.era,
                    "speaker_id": verse.speaker_id,
                }
                for verse in verses
            ],
            count=len(verses),
            query=request.query,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc