"""
Pipeline structurer for verse-level JSON record creation.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class VerseStructure:
    """Structured verse representation used by downstream pipeline steps."""

    verse_id: str
    source_text: str
    devanagari: str
    iast: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    words: List[Dict[str, Any]] = field(default_factory=list)
    speaker_id: Optional[str] = None
    metre: Optional[str] = None


class VerseStructurer:
    """Create structured verse records from normalized verse data."""

    def build_record(self, verse: Dict[str, Any]) -> VerseStructure:
        """
        Build a VerseStructure from a normalized verse dictionary.

        Args:
            verse: Input verse dictionary.

        Returns:
            Structured verse record.

        Example:
            >>> structurer = VerseStructurer()
            >>> record = structurer.build_record({"verse_id": "BG.1.1", "source_text": "Bhagavad Gita", "devanagari": "धर्मक्षेत्रे", "iast": "dharmakṣetre"})
        """
        return VerseStructure(
            verse_id=verse["verse_id"],
            source_text=verse.get("source_text", ""),
            devanagari=verse.get("devanagari", ""),
            iast=verse.get("iast", ""),
            metadata=verse.get("metadata", {}),
            speaker_id=verse.get("speaker_id"),
            metre=verse.get("metre"),
        )

    def to_dict(self, structure: VerseStructure) -> Dict[str, Any]:
        """
        Convert a VerseStructure to a dictionary.

        Args:
            structure: VerseStructure instance.

        Returns:
            Dictionary representation.

        Example:
            >>> structurer = VerseStructurer()
            >>> data = structurer.to_dict(structurer.build_record({...}))
        """
        return asdict(structure)