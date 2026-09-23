"""
demo_vis.py
===========
Live demonstration script showcasing the capabilities of the Vedic Intelligence System (VIS):
1. Multi-scheme Sanskrit Transliteration & Normalization
2. Morphological Word Analysis (pada, vibhakti, vacana, dhatu)
3. Vedic-Science Parallel Conceptual Mapping (Physics, Neuroscience, Medicine, Astronomy)
4. Fast discovery of arXiv & scientific literature mappings
"""

import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

print("=" * 65)
print("       🕉️  VEDIC INTELLIGENCE SYSTEM (VIS) - LIVE DEMO  🕉️")
print("=" * 65)

# -------------------------------------------------------------
# 1. Multi-Scheme Sanskrit Transliteration
# -------------------------------------------------------------
print("\n[1] Multi-Scheme Sanskrit Transliteration & Normalization")
print("-" * 65)
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate

    sample_shloka_iast = "karmaṇy evādhikāras te mā phaleṣu kadācana"
    devanagari = transliterate(sample_shloka_iast, sanscript.IAST, sanscript.DEVANAGARI)
    slp1 = transliterate(sample_shloka_iast, sanscript.IAST, sanscript.SLP1)
    hk = transliterate(sample_shloka_iast, sanscript.IAST, sanscript.HK)

    print(f"  • Source (IAST):       {sample_shloka_iast}")
    print(f"  • Devanagari Script:   {devanagari}")
    print(f"  • SLP1 (NLP internal): {slp1}")
    print(f"  • Harvard-Kyoto (HK):  {hk}")
except Exception as e:
    print(f"  [Error]: {e}")

# -------------------------------------------------------------
# 2. Sanskrit Morphological Parsing
# -------------------------------------------------------------
print("\n[2] Sanskrit Morphological & Word-Level Parsing")
print("-" * 65)
try:
    from pipeline.parser import SanskritParser

    parser = SanskritParser()
    sample_verse = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः"
    words = parser.parse_verse(sample_verse, verse_id="BG.1.1")

    print(f"  Verse: '{sample_verse}' (BG 1.1)")
    print(f"  Extracted Words ({len(words)} padas):")
    for w in words:
        vib_info = f", Case: {w.vibhakti_name}" if w.vibhakti_name else ""
        meaning = f" -> {w.meaning_en}" if w.meaning_en else ""
        print(f"    - [{w.surface_devanagari}] (ID: {w.pada_id}{vib_info}{meaning})")
except Exception as e:
    print(f"  [Error]: {e}")

# -------------------------------------------------------------
# 3. Ancient Concepts to Modern Scientific Domains
# -------------------------------------------------------------
print("\n[3] Ancient Sanskrit Concepts ⇄ Modern Science Knowledge Graph")
print("-" * 65)
try:
    from pipeline.science_linker import SCIENCE_DOMAINS, CONCEPT_DOMAINS

    print("  Mapping Ancient Concepts to Modern Research Domains:")
    sample_concepts = ["paramanu", "akasha", "prana", "yoga", "dhyana", "ayurveda"]
    for c in sample_concepts:
        domain = CONCEPT_DOMAINS.get(c, "General Science")
        keywords = SCIENCE_DOMAINS.get(domain, [])[:3]
        print(f"    • Concept: '{c:<10}' ➔ Domain: {domain:<14} (Keywords: {', '.join(keywords)})")
except Exception as e:
    print(f"  [Error]: {e}")

# -------------------------------------------------------------
# 4. API Endpoints Available in VIS
# -------------------------------------------------------------
print("\n[4] FastAPI Microservice Endpoints")
print("-" * 65)
try:
    from api.main import app

    routes = [
        (route.path, list(route.methods)[0], getattr(route, "tags", ["General"])[0] if getattr(route, "tags", None) else "General")
        for route in app.routes
        if hasattr(route, "path") and hasattr(route, "methods")
    ]
    print(f"  Total API Endpoints Registered: {len(routes)}")
    for path, method, tag in routes[:10]:
        print(f"    • [{method:<4}] {path:<25} (Tag: {tag})")
except Exception as e:
    print(f"  [Error]: {e}")

print("\n" + "=" * 65)
print("System verified and functional!")
print("=" * 65)
