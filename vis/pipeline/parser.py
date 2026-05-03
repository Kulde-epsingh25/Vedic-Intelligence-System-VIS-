"""
Pipeline parser module for Sanskrit word-level linguistic analysis.

This module uses the Vidyut library to parse Sanskrit verses at the word level,
extracting grammatical information like root (dhatu), case (vibhakti), number,
gender, person, and tense.
"""

from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
from loguru import logger
from tqdm import tqdm

from database.models import WordRecord


@dataclass
class ParsedWord:
    """Represents a parsed Sanskrit word."""
    surface_form: str
    dhatu: Optional[str] = None
    stem: Optional[str] = None
    vibhakti: Optional[int] = None
    vachana: Optional[str] = None
    linga: Optional[str] = None
    purusha: Optional[str] = None
    lakara: Optional[str] = None
    meaning_en: Optional[str] = None


class SanskritParser:
    """Parse Sanskrit verses using the Vidyut library."""

    def __init__(self):
        """
        Initialize SanskritParser with Vidyut.

        Example:
            >>> parser = SanskritParser()
            >>> words = parser.parse_verse("धर्मक्षेत्रे कुरुक्षेत्रे", "BG.1.1")
        """
        try:
            from vidyut.chakara import Paricheda
            self.parser = Paricheda()
            logger.info("Vidyut parser initialized")
        except ImportError:
            logger.error("Vidyut library not installed")
            raise ImportError("Install via: pip install vidyut-core")

    def parse_verse(self, devanagari: str, verse_id: str) -> List[WordRecord]:
        """
        Parse a single Sanskrit verse into word records.

        Args:
            devanagari: Verse text in Unicode Devanagari
            verse_id: Verse identifier (e.g., "BG.1.1")

        Returns:
            List of WordRecord objects

        Example:
            >>> parser = SanskritParser()
            >>> words = parser.parse_verse("धर्मक्षेत्रे कुरुक्षेत्रे", "BG.1.1")
            >>> for word in words:
            ...     print(f"{word.surface_form} → {word.dhatu}")
        """
        word_records = []

        try:
            # Parse the verse
            parsed_result = self.parser.run(devanagari)

            if not parsed_result or len(parsed_result) == 0:
                logger.warning(f"No parsing result for verse {verse_id}")
                return word_records

            # Process each word in the parsed result
            for position, word_analysis in enumerate(parsed_result):
                word_rec = self._extract_word_record(
                    word_analysis,
                    verse_id,
                    position
                )
                if word_rec:
                    word_records.append(word_rec)

            logger.debug(f"Parsed {len(word_records)} words from verse {verse_id}")
            return word_records

        except Exception as e:
            logger.error(f"Error parsing verse {verse_id}: {e}")
            return word_records

    def parse_bulk(
        self,
        verses: List[Dict[str, str]],
        batch_size: int = 10
    ) -> List[WordRecord]:
        """
        Parse multiple verses with progress tracking.

        Args:
            verses: List of dicts with 'verse_id' and 'devanagari' keys
            batch_size: Number of verses per progress update

        Returns:
            Flattened list of all WordRecords

        Example:
            >>> parser = SanskritParser()
            >>> verses = [
            ...     {"verse_id": "BG.1.1", "devanagari": "धर्मक्षेत्रे..."},
            ...     {"verse_id": "BG.1.2", "devanagari": "पाण्डवाः..."}
            ... ]
            >>> all_words = parser.parse_bulk(verses)
        """
        all_word_records = []

        with tqdm(total=len(verses), desc="Parsing verses") as pbar:
            for i, verse in enumerate(verses):
                verse_id = verse.get("verse_id", f"unknown_{i}")
                devanagari = verse.get("devanagari", "")

                if not devanagari:
                    logger.warning(f"Empty verse text for {verse_id}")
                    pbar.update(1)
                    continue

                word_records = self.parse_verse(devanagari, verse_id)
                all_word_records.extend(word_records)

                if (i + 1) % batch_size == 0:
                    pbar.update(batch_size)

            # Update remaining
            remaining = len(verses) % batch_size
            if remaining > 0:
                pbar.update(remaining)

        logger.info(f"Total words parsed: {len(all_word_records)}")
        return all_word_records

    def identify_speaker(self, verse_context: str) -> Optional[str]:
        """
        Attempt to identify the speaker of a verse from surrounding context.

        Args:
            verse_context: Extended text context around the verse

        Returns:
            Character ID if identified, None otherwise

        Example:
            >>> parser = SanskritParser()
            >>> speaker = parser.identify_speaker("अर्जुन उवाच - धर्मक्षेत्रे...")
            >>> print(speaker)  # arjuna
        """
        # Simple heuristic: look for "X उवाच" (X said) pattern
        import re

        try:
            # Match "name उवाच" pattern
            match = re.search(r'(\w+)\s+उवाच', verse_context)
            if match:
                speaker_name = match.group(1).lower()
                # Map common Sanskrit names to IDs
                speaker_map = {
                    "अर्जुन": "arjuna",
                    "कृष्ण": "krishna",
                    "युधिष्ठिर": "yudhishthira",
                    "भीम": "bhima",
                    "व्यास": "vyasa",
                    "संजय": "sanjaya",
                }
                return speaker_map.get(speaker_name)
        except Exception as e:
            logger.debug(f"Error identifying speaker: {e}")

        return None

    def identify_metre(self, devanagari: str) -> Optional[str]:
        """
        Identify the Sanskrit metre (chandas) of a verse.

        Args:
            devanagari: Verse in Devanagari

        Returns:
            Metre name (Anushtubh, Trishtubh, Jagati, etc.) or None

        Example:
            >>> parser = SanskritParser()
            >>> metre = parser.identify_metre("धर्मक्षेत्रे कुरुक्षेत्रे")
            >>> print(metre)  # Anushtubh
        """
        # Heuristic: count syllables
        # In Sanskrit, syllable count is preserved in text
        # Common metres:
        # Anushtubh: 8+8 = 16 syllables per line, 2 lines (32 total)
        # Trishtubh: 11 syllables per line
        # Jagati: 12 syllables per line
        # Gayatri: 8 syllables per line

        try:
            # Count matras (syllables) - very simplified
            # In actual Devanagari, we'd count carefully including consonant clusters
            syllable_count = len([c for c in devanagari if c.isalpha()])

            if syllable_count % 8 == 0 and syllable_count <= 16:
                return "Anushtubh"
            elif syllable_count % 11 == 0:
                return "Trishtubh"
            elif syllable_count % 12 == 0:
                return "Jagati"
            elif syllable_count % 8 == 0:
                return "Gayatri"
            else:
                return None

        except Exception as e:
            logger.debug(f"Error identifying metre: {e}")
            return None

    def _extract_word_record(
        self,
        word_analysis,
        verse_id: str,
        position: int
    ) -> Optional[WordRecord]:
        """
        Extract WordRecord from Vidyut parsing result.

        Args:
            word_analysis: Parsed word from Vidyut
            verse_id: Parent verse ID
            position: Word position in verse

        Returns:
            WordRecord or None if extraction fails
        """
        try:
            # Extract surface form
            surface_form = getattr(word_analysis, 'text', '')
            if not surface_form:
                return None

            pada_id = f"{verse_id}_{position}"

            # Try to extract grammatical info from Vidyut output
            # The exact attributes depend on Vidyut version
            dhatu = getattr(word_analysis, 'root', None)
            stem = getattr(word_analysis, 'stem', None)
            vibhakti = self._parse_case_num(getattr(word_analysis, 'case', None))
            vachana = self._parse_vachana(getattr(word_analysis, 'number', None))
            linga = self._parse_gender(getattr(word_analysis, 'gender', None))
            purusha = getattr(word_analysis, 'person', None)
            lakara = self._parse_tense(getattr(word_analysis, 'tense', None))
            meaning_en = getattr(word_analysis, 'meaning', None)

            word_rec = WordRecord(
                pada_id=pada_id,
                verse_id=verse_id,
                position=position,
                surface_form=surface_form,
                dhatu=dhatu,
                stem=stem,
                vibhakti=vibhakti,
                vachana=vachana,
                linga=linga,
                purusha=purusha,
                lakara=lakara,
                meaning_en=meaning_en,
            )

            return word_rec

        except Exception as e:
            logger.debug(f"Error extracting word record for {verse_id}_{position}: {e}")
            return None

    @staticmethod
    def _parse_case_num(case_str: Optional[str]) -> Optional[int]:
        """Convert case string to vibhakti number (1-8)."""
        if not case_str:
            return None

        case_map = {
            "nominative": 1,
            "accusative": 2,
            "instrumental": 3,
            "dative": 4,
            "ablative": 5,
            "genitive": 6,
            "locative": 7,
            "vocative": 8,
        }
        return case_map.get(case_str.lower())

    @staticmethod
    def _parse_vachana(number_str: Optional[str]) -> Optional[str]:
        """Convert number string to vachana."""
        if not number_str:
            return None

        number_map = {
            "singular": "Singular",
            "dual": "Dual",
            "plural": "Plural",
        }
        return number_map.get(number_str.lower())

    @staticmethod
    def _parse_gender(gender_str: Optional[str]) -> Optional[str]:
        """Convert gender string to linga."""
        if not gender_str:
            return None

        gender_map = {
            "masculine": "Masculine",
            "feminine": "Feminine",
            "neuter": "Neuter",
        }
        return gender_map.get(gender_str.lower())

    @staticmethod
    def _parse_tense(tense_str: Optional[str]) -> Optional[str]:
        """Convert tense string to lakara."""
        if not tense_str:
            return None

        tense_map = {
            "present": "Present",
            "past": "Past",
            "future": "Future",
            "perfect": "Perfect",
            "imperfect": "Imperfect",
        }
        return tense_map.get(tense_str.lower())
