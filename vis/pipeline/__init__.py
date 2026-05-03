"""
Pipeline __init__.py — exposes main processing classes.
"""

from .downloader import DownloadManager
from .normaliser import SanskritNormaliser
from .parser import SanskritParser
from .embedder import Embedder
from .science_linker import ScienceLinker

__all__ = [
    "DownloadManager",
    "SanskritNormaliser",
    "SanskritParser",
    "Embedder",
    "ScienceLinker",
]
