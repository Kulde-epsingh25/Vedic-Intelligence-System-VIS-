"""
Smoke tests for the VIS scaffold.
"""

from ai.inference import AnswerGenerator
from database.models import VerseRecord
from pipeline.structurer import VerseStructurer


def test_verse_structurer_builds_record() -> None:
    """
    Verify a normalized verse dictionary can be structured.

    Returns:
        None.
    """
    structurer = VerseStructurer()
    record = structurer.build_record(
        {
            "verse_id": "BG.1.1",
            "source_text": "Bhagavad Gita",
            "devanagari": "धर्मक्षेत्रे कुरुक्षेत्रे",
            "iast": "dharmakṣetre kurukṣetre",
            "metadata": {"source": "test"},
        }
    )

    assert record.verse_id == "BG.1.1"
    assert record.source_text == "Bhagavad Gita"
    assert record.devanagari.startswith("धर्म")


def test_answer_generator_returns_answer_record() -> None:
    """
    Verify the answer generator returns a structured answer.

    Returns:
        None.
    """
    generator = AnswerGenerator()
    verse = VerseRecord(
        verse_id="BG.1.1",
        source_text="Bhagavad Gita",
        devanagari="धर्मक्षेत्रे कुरुक्षेत्रे",
        iast="dharmakṣetre kurukṣetre",
    )

    answer = generator.generate("What is dharma?", [verse])

    assert "dharma" in answer.answer.lower()
    assert answer.source_verses[0].verse_id == "BG.1.1"
    assert answer.confidence == 0.0