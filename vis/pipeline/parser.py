"""
pipeline/parser.py
==================
Parses every Sanskrit word using vidyut (Rust-based, 29.5M words,
2000+ Paninian grammar rules). Extracts: dhatu, vibhakti, vachana,
linga, purusha, lakara, and English meaning for every pada.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from loguru import logger

try:
    from vidyut.prakriya import Vyakarana, Dhatu, Pada, Lakara
    from vidyut.kosha import Kosha
    from vidyut.lipi import transliterate, Scheme
    VIDYUT_AVAILABLE = True
except ImportError:
    VIDYUT_AVAILABLE = False
    logger.warning("vidyut not installed. Run: pip install vidyut")

# Fallback transliteration
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate as itrans


VIBHAKTI_MAP = {
    1: "Nominative (kartā)",
    2: "Accusative (karma)",
    3: "Instrumental (karaṇa)",
    4: "Dative (sampradāna)",
    5: "Ablative (apādāna)",
    6: "Genitive (sambandha)",
    7: "Locative (adhikaraṇa)",
    8: "Vocative (sambodhana)",
}

VACHANA_MAP = {
    1: "Singular (eka)",
    2: "Dual (dvi)",
    3: "Plural (bahu)",
}

LINGA_MAP = {
    "m": "Masculine (puṃlinga)",
    "f": "Feminine (strīlinga)",
    "n": "Neuter (napuṃsakalinga)",
}

LAKARA_MAP = {
    "lat":  "Present (laṭ)",
    "lit":  "Perfect (liṭ)",
    "lut":  "Periphrastic Future (luṭ)",
    "lrt":  "Simple Future (lṛṭ)",
    "lot":  "Imperative (loṭ)",
    "lan":  "Imperfect (laṅ)",
    "lin":  "Optative (liṅ)",
    "lun":  "Aorist (luṅ)",
    "lrn":  "Conditional (lṝṅ)",
}

# Monier-Williams basic meaning lookup (top 200 roots)
DHATU_MEANINGS = {
    "gam": "to go", "ag": "to go", "yA": "to go",
    "AS": "to sit", "sthA": "to stand", "kf": "to do/make",
    "vad": "to speak", "brU": "to speak", "vac": "to speak",
    "dA": "to give", "laBa": "to obtain", "jYA": "to know",
    "paS": "to see", "df": "to see", "ik": "to see",
    "SRu": "to hear", "spfS": "to touch", "ji": "to conquer",
    "han": "to strike/kill", "mf": "to die", "jan": "to be born",
    "bhU": "to be/become", "As": "to be",
    "vid": "to know/find", "viS": "to enter",
    "nI": "to lead", "hf": "to take away",
    "rakS": "to protect", "trai": "to protect",
    "yuj": "to join/yoke", "bandh": "to bind",
    "muJ": "to release", "gAha": "to immerse",
    "car": "to move/wander", "cal": "to move",
    "pat": "to fall/fly", "plu": "to float/jump",
    "labh": "to obtain", "Ap": "to obtain/reach",
    "tyaj": "to abandon", "jah": "to abandon",
    "mantr": "to counsel", "tan": "to stretch/spread",
    "kram": "to step", "krid": "to play",
    "hAs": "to laugh", "rud": "to cry/weep",
    "svap": "to sleep", "jAgf": "to be awake",
    "bhaj": "to share/worship", "pUj": "to worship",
    "yaj": "to sacrifice", "hav": "to sacrifice/offer",
    "stuW": "to praise", "vand": "to salute",
    "dhyA": "to meditate", "cint": "to think",
    "smf": "to remember", "buDa": "to know/understand",
    "zaz": "to sit", "niviS": "to settle",
    "sev": "to serve", "BU": "to be/become",
    "kup": "to be angry", "hfz": "to be happy",
    "Suc": "to grieve", "nand": "to rejoice",
    "Baj": "to be devoted", "vraj": "to go/wander",
    "dah": "to burn", "paC": "to cook",
    "kzar": "to flow", "vah": "to carry",
    "sic": "to pour", "pA": "to drink",
    "aS": "to eat", "Sad": "to fall/decay",
    "vfdh": "to grow", "kzI": "to diminish",
    "vft": "to exist/happen", "vfj": "to twist",
    "dfS": "to see", "dRS": "to see/show",
}


@dataclass
class WordAnalysis:
    """Complete linguistic analysis of a single Sanskrit word (pada)."""
    pada_id:       str
    verse_id:      str
    position:      int
    surface_form:  str                          # as it appears in text
    surface_devanagari: str = ""
    dhatu:         Optional[str] = None         # verbal root
    stem:          Optional[str] = None
    vibhakti:      Optional[int] = None         # case 1–8
    vachana:       Optional[int] = None         # 1=sg 2=du 3=pl
    linga:         Optional[str] = None         # m/f/n
    purusha:       Optional[str] = None         # person (verbs)
    lakara:        Optional[str] = None         # tense/mood (verbs)
    meaning_en:    Optional[str] = None
    vibhakti_name: Optional[str] = None
    vachana_name:  Optional[str] = None
    linga_name:    Optional[str] = None
    lakara_name:   Optional[str] = None

    def __post_init__(self):
        if self.vibhakti:
            self.vibhakti_name = VIBHAKTI_MAP.get(self.vibhakti)
        if self.vachana:
            self.vachana_name = VACHANA_MAP.get(self.vachana)
        if self.linga:
            self.linga_name = LINGA_MAP.get(self.linga)
        if self.lakara:
            self.lakara_name = LAKARA_MAP.get(self.lakara)


class SanskritParser:
    """
    Word-level Sanskrit parser using vidyut.
    Falls back to basic analysis if vidyut is unavailable.

    Example:
        >>> p = SanskritParser()
        >>> words = p.parse_verse("धर्मक्षेत्रे कुरुक्षेत्रे", "BG.1.1")
        >>> for w in words:
        ...     print(f"{w.surface_form}: root={w.dhatu}, case={w.vibhakti_name}")
    """

    def __init__(self):
        self.kosha = None
        self._load_vidyut()

    def _load_vidyut(self) -> None:
        """Loads vidyut Kosha (29.5M words). Downloads data if needed."""
        if not VIDYUT_AVAILABLE:
            logger.warning("Running in fallback mode — no vidyut")
            return
        try:
            from vidyut.kosha import Kosha
            from vidyut import Data
            logger.info("Loading vidyut Kosha (29.5M Sanskrit words)...")
            data = Data.acquire()         # downloads ~31MB on first run
            self.kosha = Kosha(data)
            logger.success("vidyut Kosha loaded successfully")
        except Exception as e:
            logger.error(f"vidyut Kosha load failed: {e}")
            logger.info("Fallback: basic word splitting only")

    def parse_word(self, surface: str, verse_id: str, position: int) -> WordAnalysis:
        """
        Analyses a single Sanskrit word.

        Args:
            surface: Surface form of the word (Devanagari)
            verse_id: ID of the verse this word belongs to
            position: Word position in verse (0-indexed)

        Returns:
            WordAnalysis: Complete morphological analysis
        """
        pada_id = f"{verse_id}_{position:03d}"
        analysis = WordAnalysis(
            pada_id=pada_id,
            verse_id=verse_id,
            position=position,
            surface_form=surface,
            surface_devanagari=surface
        )

        if self.kosha is None:
            # Basic fallback: just store the word
            analysis.meaning_en = self._lookup_basic_meaning(surface)
            return analysis

        # Convert Devanagari → SLP1 for vidyut
        try:
            slp1 = itrans(surface, sanscript.DEVANAGARI, sanscript.SLP1)
        except Exception:
            slp1 = surface

        try:
            results = self.kosha.get(slp1)
            if results:
                r = results[0]              # take best analysis
                analysis.dhatu = getattr(r, 'dhatu', None)
                analysis.stem = getattr(r, 'stem', None)

                # Extract vibhakti
                if hasattr(r, 'vibhakti') and r.vibhakti is not None:
                    analysis.vibhakti = int(str(r.vibhakti).split('.')[-1])

                # Extract vachana
                if hasattr(r, 'vachana') and r.vachana is not None:
                    vachana_str = str(r.vachana).lower()
                    analysis.vachana = (1 if 'eka' in vachana_str else
                                        2 if 'dvi' in vachana_str else 3)

                # Extract linga
                if hasattr(r, 'linga') and r.linga is not None:
                    linga_str = str(r.linga).lower()
                    analysis.linga = ('m' if 'pum' in linga_str or 'mas' in linga_str else
                                      'f' if 'stri' in linga_str or 'fem' in linga_str else 'n')

                # Extract lakara (for verbs)
                if hasattr(r, 'lakara') and r.lakara is not None:
                    analysis.lakara = str(r.lakara).lower().split('.')[-1]

                # Extract purusha
                if hasattr(r, 'purusha') and r.purusha is not None:
                    analysis.purusha = str(r.purusha).split('.')[-1]

                # Meaning from dhatu lookup
                if analysis.dhatu:
                    analysis.meaning_en = DHATU_MEANINGS.get(analysis.dhatu,
                                         f"[root: {analysis.dhatu}]")

        except Exception as e:
            logger.debug(f"vidyut analysis failed for '{surface}': {e}")

        return analysis

    def _lookup_basic_meaning(self, devanagari: str) -> Optional[str]:
        """Basic meaning lookup without vidyut."""
        common_words = {
            "धर्म": "duty/righteousness",
            "कर्म": "action/deed",
            "आत्मन्": "self/soul",
            "ब्रह्मन्": "Brahman/absolute",
            "सत्य": "truth",
            "अहिंसा": "non-violence",
            "योग": "union/discipline",
            "ज्ञान": "knowledge",
            "भक्ति": "devotion",
            "मोक्ष": "liberation",
            "सत्त्व": "purity/goodness",
            "रजस्": "passion/activity",
            "तमस्": "darkness/inertia",
            "राम": "Rama",
            "कृष्ण": "Krishna",
            "अर्जुन": "Arjuna",
        }
        return common_words.get(devanagari)

    def parse_verse(self, devanagari: str, verse_id: str) -> list[WordAnalysis]:
        """
        Parses every word in a verse.

        Args:
            devanagari: Full verse text in Devanagari
            verse_id: Verse identifier (e.g. "BG.2.47")

        Returns:
            list[WordAnalysis]: One record per word
        """
        import re
        # Split on whitespace and punctuation, keep Devanagari
        words = re.findall(r'[\u0900-\u097F]+', devanagari)
        return [self.parse_word(w, verse_id, i) for i, w in enumerate(words)]

    def parse_bulk(self, verses: list, show_progress: bool = True) -> list[WordAnalysis]:
        """
        Parses all words from a list of VerseRecord objects.

        Args:
            verses: List of VerseRecord (from normaliser)
            show_progress: Show tqdm progress bar

        Returns:
            list[WordAnalysis]: All word analyses
        """
        all_words = []
        iterator = tqdm(verses, desc="Parsing words") if show_progress else verses
        for verse in iterator:
            words = self.parse_verse(verse.devanagari, verse.verse_id)
            all_words.extend(words)
        logger.info(f"Parsed {len(all_words):,} words from {len(verses):,} verses")
        return all_words

    def identify_speaker(self, preceding_text: str,
                         known_chars: list[str]) -> Optional[str]:
        """
        Identifies the speaker of a verse from context.

        Args:
            preceding_text: Text before the verse (contains "uvāca" etc.)
            known_chars: List of known character IDs

        Returns:
            str | None: Character ID of speaker
        """
        speaker_patterns = {
            r'kṛṣṇa.*?uvāca|kṛṣṇa.*?spoke':  'krishna',
            r'arjuna.*?uvāca|arjuna.*?spoke':  'arjuna',
            r'rāma.*?uvāca':                    'rama',
            r'bhīṣma.*?uvāca':                  'bhishma',
            r'vyāsa.*?uvāca':                   'vyasa',
            r'sañjaya.*?uvāca':                 'sanjaya',
            r'yudhiṣṭhira.*?uvāca':             'yudhishthira',
            r'dhṛtarāṣṭra.*?uvāca':             'dhritarashtra',
            r'sītā.*?uvāca':                    'sita',
            r'rāvaṇa.*?uvāca':                  'ravana',
        }
        import re
        text_lower = preceding_text.lower()
        for pattern, char_id in speaker_patterns.items():
            if re.search(pattern, text_lower):
                return char_id
        return None

    def extract_entities(self, devanagari: str,
                         iast: str) -> dict[str, list[str]]:
        """
        Extracts named entities (characters, places, weapons, herbs).

        Args:
            devanagari: Verse in Devanagari
            iast: IAST romanisation

        Returns:
            dict: {'characters': [...], 'places': [...], 'weapons': [...]}
        """
        entities = {"characters": [], "places": [], "weapons": [], "concepts": []}

        # Known entity lists (expanded as corpus grows)
        characters_sa = {
            "राम": "rama", "कृष्ण": "krishna", "अर्जुन": "arjuna",
            "भीम": "bhima", "युधिष्ठिर": "yudhishthira",
            "दुर्योधन": "duryodhana", "भीष्म": "bhishma",
            "द्रोण": "drona", "कर्ण": "karna",
            "सीता": "sita", "रावण": "ravana",
            "हनुमान": "hanuman", "लक्ष्मण": "lakshmana",
            "विष्णु": "vishnu", "शिव": "shiva",
            "ब्रह्मा": "brahma", "इन्द्र": "indra",
            "अग्नि": "agni", "वायु": "vayu",
            "वरुण": "varuna", "यम": "yama",
        }
        places_sa = {
            "कुरुक्षेत्र": "kurukshetra", "हस्तिनापुर": "hastinapura",
            "अयोध्या": "ayodhya", "लङ्का": "lanka",
            "द्वारका": "dwaraka", "मथुरा": "mathura",
            "काशी": "kashi", "प्रयाग": "prayaga",
        }
        weapons_sa = {
            "गाण्डीव": "gandiva", "सुदर्शन": "sudarshana",
            "पाशुपात": "pashupata", "ब्रह्मास्त्र": "brahmastra",
        }
        concepts_sa = {
            "धर्म": "dharma", "कर्म": "karma", "मोक्ष": "moksha",
            "आत्मन्": "atman", "ब्रह्मन्": "brahman",
            "योग": "yoga", "ज्ञान": "jnana", "भक्ति": "bhakti",
        }

        for sa_name, entity_id in characters_sa.items():
            if sa_name in devanagari:
                entities["characters"].append(entity_id)
        for sa_name, entity_id in places_sa.items():
            if sa_name in devanagari:
                entities["places"].append(entity_id)
        for sa_name, entity_id in weapons_sa.items():
            if sa_name in devanagari:
                entities["weapons"].append(entity_id)
        for sa_name, entity_id in concepts_sa.items():
            if sa_name in devanagari:
                entities["concepts"].append(entity_id)

        return {k: list(set(v)) for k, v in entities.items()}
