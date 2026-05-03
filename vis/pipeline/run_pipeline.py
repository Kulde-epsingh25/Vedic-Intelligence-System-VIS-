"""
Pipeline orchestration entry point.
"""

from pathlib import Path
from typing import List

from loguru import logger

from pipeline.downloader import DownloadManager
from pipeline.normaliser import SanskritNormaliser
from pipeline.parser import SanskritParser
from pipeline.structurer import VerseStructurer


class PipelineRunner:
    """Run the VIS ingestion pipeline end-to-end."""

    def __init__(self, corpus_path: Path = Path("corpus")) -> None:
        """
        Initialize the pipeline runner.

        Args:
            corpus_path: Location of corpus files.

        Returns:
            None.

        Example:
            >>> runner = PipelineRunner()
        """
        self.downloader = DownloadManager(corpus_path=corpus_path)
        self.normaliser = SanskritNormaliser()
        self.parser = SanskritParser()
        self.structurer = VerseStructurer()

    def run(self, category: str) -> List[dict]:
        """
        Run the minimal pipeline for a corpus category.

        Args:
            category: Corpus category to download.

        Returns:
            List of structured verse dictionaries.

        Example:
            >>> runner = PipelineRunner()
            >>> structured = runner.run("rigveda")
        """
        logger.info(f"Running pipeline for category={category}")
        downloaded = self.downloader.download_gretil(category)
        structured: List[dict] = []

        for file_path in downloaded:
            verses = self.normaliser.split_verse_file(file_path)
            for verse in verses:
                structured.append(self.structurer.to_dict(self.structurer.build_record(verse)))

        logger.info(f"Pipeline completed with {len(structured)} structured verses")
        return structured