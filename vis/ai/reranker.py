"""
Cross-encoder reranker for retrieval candidate ordering.
"""

from typing import List

from database.models import VerseRecord


class CrossEncoderReranker:
    """Rerank candidate verses with a cross-encoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        """
        Initialize reranker.

        Args:
            model_name: Hugging Face model identifier.

        Returns:
            None.

        Example:
            >>> reranker = CrossEncoderReranker()
        """
        self.model_name = model_name

    def rerank(self, query: str, candidates: List[VerseRecord]) -> List[VerseRecord]:
        """
        Return candidates in their current order until the model is wired up.

        Args:
            query: User query.
            candidates: Candidate verses.

        Returns:
            Reranked verses.

        Example:
            >>> reranker = CrossEncoderReranker()
            >>> reranked = reranker.rerank("dharma", [])
        """
        return candidates