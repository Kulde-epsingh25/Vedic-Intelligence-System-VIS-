"""
Inference helpers for VIS answer generation.
"""

from dataclasses import dataclass
from typing import List

from database.models import AnswerRecord, VerseRecord


@dataclass
class InferenceInput:
    """Simple inference input payload."""

    question: str
    context: str


class AnswerGenerator:
    """Generate answers from prompts and retrieved verses."""

    def generate(self, question: str, verses: List[VerseRecord]) -> AnswerRecord:
        """
        Generate a minimal answer record.

        Args:
            question: User question.
            verses: Supporting verses.

        Returns:
            AnswerRecord with placeholder answer text.

        Example:
            >>> generator = AnswerGenerator()
            >>> answer = generator.generate("What is dharma?", [])
        """
        return AnswerRecord(
            answer=f"The texts do not address this directly: {question}",
            source_verses=verses,
            characters_mentioned=[],
            science_links=[],
            confidence=0.0,
        )