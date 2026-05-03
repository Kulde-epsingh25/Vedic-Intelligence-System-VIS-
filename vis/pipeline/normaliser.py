"""
Pipeline normaliser module for encoding conversions and text cleaning.

This module handles conversion of Sanskrit text between different encodings
(ITRANS, Harvard-Kyoto, SLP1, Velthuis, IAST, Grantha) to Unicode Devanagari,
with automatic scheme detection and text cleaning.
"""

from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger

try:
    from indic_transliteration import sanscript
except ImportError:
    logger.warning("indic-transliteration not installed, some features disabled")
    sanscript = None


class SanskritNormaliser:
    """Normalize Sanskrit text encodings to Unicode Devanagari and IAST."""

    def __init__(self):
        """
        Initialize SanskritNormaliser.

        Example:
            >>> normaliser = SanskritNormaliser()
            >>> devnag = normaliser.to_devanagari('namaskar', 'ITRANS')
        """
        if sanscript is None:
            logger.error("indic-transliteration library required")
            raise ImportError("Install via: pip install indic-transliteration")

    def to_devanagari(self, text: str, source_scheme: str) -> str:
        """
        Convert text from any scheme to Unicode Devanagari.

        Args:
            text: Input text
            source_scheme: Encoding scheme (ITRANS, HarvardKyoto, SLP1, Velthuis, IAST, Grantha)

        Returns:
            Text in Unicode Devanagari

        Example:
            >>> normaliser = SanskritNormaliser()
            >>> dev = normaliser.to_devanagari('dharmakSetre kurukSetre', 'HarvardKyoto')
            >>> print(dev)  # धर्मक्षेत्रे कुरुक्षेत्रे
        """
        try:
            scheme_map = {
                "ITRANS": sanscript.ITRANS,
                "HARVARDKYOTO": sanscript.HK,
                "HARVARDKYOTO_OLD": sanscript.HK,
                "SLP1": sanscript.SLP1,
                "VELTHUIS": sanscript.VELTHUIS,
                "IAST": sanscript.IAST,
                "GRANTHA": sanscript.GRANTHA,
                "DEVANAGARI": sanscript.DEVANAGARI,
            }

            from_scheme = scheme_map.get(source_scheme.upper())
            if not from_scheme:
                logger.warning(f"Unknown scheme: {source_scheme}, attempting direct conversion")
                from_scheme = source_scheme

            result = sanscript.transliterate(
                text,
                from_scheme,
                sanscript.DEVANAGARI
            )
            logger.debug(f"Converted {len(text)} chars from {source_scheme} to Devanagari")
            return result

        except Exception as e:
            logger.error(f"Error converting to Devanagari: {e}")
            return text

    def to_iast(self, devanagari_text: str) -> str:
        """
        Convert Unicode Devanagari to IAST romanisation.

        Args:
            devanagari_text: Text in Devanagari

        Returns:
            Text in IAST

        Example:
            >>> normaliser = SanskritNormaliser()
            >>> iast = normaliser.to_iast("धर्मक्षेत्रे")
            >>> print(iast)  # dharmakṣetre
        """
        try:
            result = sanscript.transliterate(
                devanagari_text,
                sanscript.DEVANAGARI,
                sanscript.IAST
            )
            logger.debug(f"Converted {len(devanagari_text)} chars to IAST")
            return result
        except Exception as e:
            logger.error(f"Error converting to IAST: {e}")
            return devanagari_text

    def detect_scheme(self, text: str) -> Optional[str]:
        """
        Auto-detect the encoding scheme of input text.

        Args:
            text: Input text

        Returns:
            Detected scheme name or None

        Example:
            >>> normaliser = SanskritNormaliser()
            >>> scheme = normaliser.detect_scheme("dharmakSetre")
            >>> print(scheme)  # HarvardKyoto
        """
        # Heuristic detection based on character patterns
        if not text:
            return None

        # Check for Devanagari Unicode range
        if any('\u0900' <= c <= '\u097F' for c in text):
            return "DEVANAGARI"

        # Check for ITRANS patterns (capital letters + diacritics)
        if any(c in text for c in "RLM"):
            return "ITRANS"

        # Check for Harvard-Kyoto patterns
        if "kS" in text or "Sq" in text:
            return "HARVARDKYOTO"

        # Check for IAST patterns (macron diacritics)
        if any(c in text for c in "āīūēōṛṝḷḹṅñṭḍṇṃḥ"):
            return "IAST"

        # Check for SLP1 patterns
        if "z" in text or "w" in text or "q" in text:
            return "SLP1"

        # Default guess
        logger.warning(f"Could not auto-detect scheme, defaulting to IAST")
        return "IAST"

    def clean_verse(self, text: str) -> str:
        """
        Clean verse text by removing metadata markers and normalizing spacing.

        Args:
            text: Raw verse text

        Returns:
            Cleaned text

        Example:
            >>> normaliser = SanskritNormaliser()
            >>> clean = normaliser.clean_verse("  धर्मक्षेत्रे    कुरुक्षेत्रे  ")
            >>> print(clean)  # धर्मक्षेत्रे कुरुक्षेत्रे
        """
        import re

        # Remove metadata markers
        text = re.sub(r'\[.*?\]', '', text)  # [notes]
        text = re.sub(r'\{.*?\}', '', text)  # {annotations}
        text = re.sub(r'\(.*?\)', '', text)  # (comments)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
        text = text.strip()

        # Remove Unicode control characters
        text = ''.join(c for c in text if not (ord(c) < 32 and c not in '\t\n\r'))

        logger.debug(f"Cleaned verse: {len(text)} chars")
        return text

    def split_verse_file(self, file_path: Path) -> List[Dict[str, str]]:
        """
        Parse a verse file (TEI-XML or plain text) into structured verses.

        Args:
            file_path: Path to verse file

        Returns:
            List of dicts with keys: verse_id, devanagari, iast, metadata

        Example:
            >>> normaliser = SanskritNormaliser()
            >>> verses = normaliser.split_verse_file(Path("rigveda.txt"))
            >>> print(f"Parsed {len(verses)} verses")
        """
        verses = []

        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return verses

            # Detect file format
            if file_path.suffix == ".xml":
                verses = self._parse_xml_verses(file_path)
            else:
                verses = self._parse_text_verses(file_path)

            logger.info(f"Parsed {len(verses)} verses from {file_path.name}")
            return verses

        except Exception as e:
            logger.error(f"Error parsing verse file {file_path}: {e}")
            return verses

    def _parse_xml_verses(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse TEI-XML verse file."""
        try:
            from xml.etree import ElementTree as ET
        except ImportError:
            logger.error("XML parsing requires ElementTree")
            return []

        verses = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Find verse elements (common tags: <l>, <verse>, <pada>)
            for verse_elem in root.findall(".//l") or root.findall(".//verse") or root.findall(".//pada"):
                text = verse_elem.text or ""
                verse_record = {
                    "verse_id": verse_elem.get("id", ""),
                    "devanagari": text,
                    "iast": self.to_iast(text) if '\u0900' <= text[0] <= '\u097F' else text,
                    "metadata": verse_elem.get("type", ""),
                }
                verses.append(verse_record)

        except Exception as e:
            logger.error(f"XML parsing error: {e}")

        return verses

    def _parse_text_verses(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse plain text verse file (one verse per line)."""
        verses = []
        verse_num = 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    verse_num += 1
                    text = self.clean_verse(line)

                    # Detect encoding and convert
                    scheme = self.detect_scheme(text)
                    if scheme != "DEVANAGARI":
                        text = self.to_devanagari(text, scheme)

                    verse_record = {
                        "verse_id": f"{file_path.stem}_{verse_num}",
                        "devanagari": text,
                        "iast": self.to_iast(text),
                        "metadata": f"line_{line_num}",
                    }
                    verses.append(verse_record)

        except Exception as e:
            logger.error(f"Text parsing error: {e}")

        return verses
