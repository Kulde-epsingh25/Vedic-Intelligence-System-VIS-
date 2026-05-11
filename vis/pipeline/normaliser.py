"""
pipeline/normaliser.py
======================
Normalises all Sanskrit text encodings to Unicode Devanagari.
Handles ITRANS, Harvard-Kyoto, SLP1, Velthuis, IAST, Grantha,
and strips GRETIL HTML markup.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from bs4 import BeautifulSoup
from loguru import logger
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


@dataclass
class VerseRecord:
    """A single parsed verse ready for database insertion."""
    verse_id:    str
    source_text_id: str
    book:        Optional[int]
    chapter:     Optional[int]
    verse_num:   Optional[int]
    devanagari:  str
    iast:        str
    slp1:        str
    raw_text:    str
    metre:       Optional[str] = None
    word_count:  int = 0

    def __post_init__(self):
        self.word_count = len(self.devanagari.split())


SCHEME_MAP = {
    "itrans":       sanscript.ITRANS,
    "hk":           sanscript.HK,
    "harvardkyoto": sanscript.HK,
    "slp1":         sanscript.SLP1,
    "velthuis":     sanscript.VELTHUIS,
    "iast":         sanscript.IAST,
    "devanagari":   sanscript.DEVANAGARI,
    "iso":          sanscript.IAST,
}

# GRETIL/TITUS verse markers (regex patterns)
VERSE_PATTERNS = [
    r'\{(\d+[,\.]\d+[,\.]\d+)\}',         # {1.1.1}
    r'//\s*(\d+[\.\-]\d+[\.\-]\d+)\s*//', # //1.1.1//
    r'\|\|\s*(\d+)\s*\|\|',               # ||42||
    r'<l\s+n="([^"]+)"',                  # TEI <l n="1.1">
    r'verse\s+(\d+)',                      # verse 1
]

METRE_PATTERNS = {
    "anushtubh":  32,  # 4 padas of 8 syllables
    "trishtubh":  44,  # 4 padas of 11 syllables
    "jagati":     48,  # 4 padas of 12 syllables
    "gayatri":    24,  # 3 padas of 8 syllables
    "brihati":    36,
    "pankti":     40,
}

# Cleanup patterns for GRETIL HTML
CLEANUP_PATTERNS = [
    (r'<[^>]+>',         ''),    # strip all HTML tags
    (r'&amp;',           '&'),
    (r'&lt;',            '<'),
    (r'&gt;',            '>'),
    (r'&nbsp;',          ' '),
    (r'\[.*?\]',         ''),    # remove bracketed notes
    (r'\s+',             ' '),   # normalise whitespace
]


class SanskritNormaliser:
    """
    Converts any Sanskrit encoding to clean Unicode Devanagari + IAST.

    Example:
        >>> n = SanskritNormaliser()
        >>> deva = n.to_devanagari("dharmakSetre kurukSetre", "hk")
        >>> print(deva)   # धर्मक्षेत्रे कुरुक्षेत्रे
    """

    def to_devanagari(self, text: str, source_scheme: str = "iast") -> str:
        """
        Converts text from any scheme to Devanagari.

        Args:
            text: Input Sanskrit text
            source_scheme: Encoding name (itrans/hk/slp1/iast/devanagari)

        Returns:
            str: Unicode Devanagari text
        """
        scheme = SCHEME_MAP.get(source_scheme.lower(), sanscript.IAST)
        if scheme == sanscript.DEVANAGARI:
            return text
        try:
            return transliterate(text, scheme, sanscript.DEVANAGARI)
        except Exception as e:
            logger.warning(f"Transliteration failed: {e}")
            return text

    def to_iast(self, text: str, source_scheme: str = "devanagari") -> str:
        """Converts text to IAST romanisation."""
        scheme = SCHEME_MAP.get(source_scheme.lower(), sanscript.DEVANAGARI)
        try:
            return transliterate(text, scheme, sanscript.IAST)
        except Exception as e:
            logger.warning(f"IAST conversion failed: {e}")
            return text

    def to_slp1(self, text: str, source_scheme: str = "devanagari") -> str:
        """Converts text to SLP1 (used internally by vidyut)."""
        scheme = SCHEME_MAP.get(source_scheme.lower(), sanscript.DEVANAGARI)
        try:
            return transliterate(text, scheme, sanscript.SLP1)
        except Exception as e:
            return text

    def detect_scheme(self, text: str) -> str:
        """
        Auto-detects encoding of a Sanskrit string.

        Returns:
            str: Detected scheme name
        """
        if re.search(r'[\u0900-\u097F]', text):
            return "devanagari"
        if re.search(r'[āīūṛṝḷṃḥṅñṭḍṇśṣ]', text):
            return "iast"
        if re.search(r'[AEIOURMHNYLVS]', text) and re.search(r'[kKgGcCjJwWqQpPbBdD]', text):
            return "slp1"
        if re.search(r'\^|\.\.', text):
            return "velthuis"
        if re.search(r'aa|ii|uu|\.t|\.d|\.n|~n', text):
            return "itrans"
        return "hk"  # Harvard-Kyoto as default Latin

    def clean_gretil_html(self, html: str) -> str:
        """
        Strips GRETIL HTML markup and returns clean text.

        Args:
            html: Raw GRETIL HTML content

        Returns:
            str: Clean Sanskrit text
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # Remove script, style, metadata elements
            for tag in soup(['script', 'style', 'head', 'meta', 'title']):
                tag.decompose()
            text = soup.get_text(separator='\n')
        except Exception:
            # Fallback: regex strip
            text = html

        for pattern, replacement in CLEANUP_PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text.strip()

    def detect_metre(self, devanagari: str) -> Optional[str]:
        """
        Detects Sanskrit metre based on syllable count.

        Args:
            devanagari: Verse in Devanagari

        Returns:
            str | None: Metre name or None
        """
        # Count syllables (vowels in Devanagari)
        vowels = re.findall(r'[\u0904-\u0914\u0905-\u090c\u0915]', devanagari)
        count = len(vowels)
        for metre, expected in METRE_PATTERNS.items():
            if abs(count - expected) <= 2:
                return metre
        return None

    def parse_gretil_file(self, file_path: Path, text_id: str) -> list[VerseRecord]:
        """
        Parses a GRETIL .htm file into a list of VerseRecord objects.

        Args:
            file_path: Path to the GRETIL HTML/XML file
            text_id: Source text identifier (e.g. "RV", "BG")

        Returns:
            list[VerseRecord]: All verses extracted
        """
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Cannot read {file_path}: {e}")
            return []

        clean = self.clean_gretil_html(content)
        detected_scheme = self.detect_scheme(clean[:500])
        logger.debug(f"Detected encoding for {text_id}: {detected_scheme}")

        verses = []
        lines = clean.split('\n')
        current_verse_lines = []
        current_id = None
        book, chapter, verse_n = 1, 1, 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect verse number markers
            verse_marker = None
            for pattern in VERSE_PATTERNS:
                m = re.search(pattern, line)
                if m:
                    verse_marker = m.group(1)
                    break

            if verse_marker:
                # Save previous verse if any
                if current_verse_lines and current_id:
                    raw = ' '.join(current_verse_lines).strip()
                    raw = re.sub(r'\d+[\.\-]\d+[\.\-]?\d*', '', raw).strip()
                    if len(raw) > 5:
                        deva = self.to_devanagari(raw, detected_scheme) if detected_scheme != "devanagari" else raw
                        verses.append(VerseRecord(
                            verse_id=current_id,
                            source_text_id=text_id,
                            book=book, chapter=chapter, verse_num=verse_n,
                            devanagari=deva,
                            iast=self.to_iast(deva),
                            slp1=self.to_slp1(deva),
                            raw_text=raw,
                            metre=self.detect_metre(deva)
                        ))
                # Start new verse
                parts = re.split(r'[,\.\-]', verse_marker)
                try:
                    if len(parts) >= 3:
                        book, chapter, verse_n = int(parts[0]), int(parts[1]), int(parts[2])
                    elif len(parts) == 2:
                        chapter, verse_n = int(parts[0]), int(parts[1])
                    else:
                        verse_n = int(parts[0])
                except ValueError:
                    verse_n += 1

                current_id = f"{text_id}.{book}.{chapter}.{verse_n}"
                current_verse_lines = [re.sub(r'\{.*?\}|//.*?//', '', line).strip()]
            else:
                if current_id and line:
                    current_verse_lines.append(line)

        logger.info(f"Parsed {len(verses)} verses from {text_id}")
        return verses

    def parse_dcs_xml(self, xml_path: Path, text_id: str) -> list[VerseRecord]:
        """
        Parses a DCS annotated XML file into VerseRecords.
        DCS files already have morphological annotations.

        Args:
            xml_path: Path to DCS XML file
            text_id: Source text identifier

        Returns:
            list[VerseRecord]: All verses extracted
        """
        try:
            soup = BeautifulSoup(xml_path.read_text(encoding='utf-8'), 'xml')
        except Exception as e:
            logger.error(f"Cannot parse DCS XML {xml_path}: {e}")
            return []

        verses = []
        for lg in soup.find_all('lg'):  # lg = verse group in TEI
            verse_id_attr = lg.get('n', '')
            lines = [l.get_text() for l in lg.find_all('l')]
            raw = ' '.join(lines).strip()
            if not raw:
                continue
            detected = self.detect_scheme(raw[:100])
            deva = self.to_devanagari(raw, detected) if detected != "devanagari" else raw
            verses.append(VerseRecord(
                verse_id=f"{text_id}.{verse_id_attr}",
                source_text_id=text_id,
                book=None, chapter=None, verse_num=None,
                devanagari=deva,
                iast=self.to_iast(deva),
                slp1=self.to_slp1(deva),
                raw_text=raw,
                metre=self.detect_metre(deva)
            ))

        logger.info(f"DCS: Parsed {len(verses)} verses from {xml_path.name}")
        return verses

    def process_corpus_directory(self, corpus_dir: Path) -> list[VerseRecord]:
        """
        Processes an entire corpus directory, auto-detecting file types.

        Args:
            corpus_dir: Root corpus directory

        Returns:
            list[VerseRecord]: All verses from all texts
        """
        all_verses = []
        htm_files = list(corpus_dir.rglob("*.htm")) + list(corpus_dir.rglob("*.html"))
        xml_files = list(corpus_dir.rglob("*.xml"))

        logger.info(f"Found {len(htm_files)} HTML files, {len(xml_files)} XML files")

        for f in tqdm(htm_files, desc="Parsing GRETIL HTML"):
            text_id = self._guess_text_id(f)
            verses = self.parse_gretil_file(f, text_id)
            all_verses.extend(verses)

        for f in tqdm(xml_files, desc="Parsing DCS XML"):
            text_id = self._guess_text_id(f)
            verses = self.parse_dcs_xml(f, text_id)
            all_verses.extend(verses)

        logger.success(f"Total verses parsed: {len(all_verses):,}")
        return all_verses

    def _guess_text_id(self, path: Path) -> str:
        """Guesses text_id from filename and path."""
        name = path.stem.lower()
        mapping = {
            "rv": "RV", "rigveda": "RV", "rvs": "RV",
            "sv": "SV", "samaveda": "SV",
            "av": "AV", "atharvaveda": "AV",
            "bhaggi": "BG", "gita": "BG",
            "mbh": "MBH", "mahabh": "MBH",
            "ram": "RAM", "ramayana": "RAM",
            "charaka": "CS", "carak": "CS",
            "susruta": "SS", "sushruta": "SS",
            "aryabh": "AB",
            "arthas": "ARTH",
            "yoga": "YS",
            "agni": "AGNI",
            "garuda": "GAR", "garud": "GAR",
            "vishnu": "VISH", "vishn": "VISH",
            "bhag": "BHAG",
        }
        for key, val in mapping.items():
            if key in name:
                return val
        return path.stem.upper()[:8]


try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **kwargs):
        return x
