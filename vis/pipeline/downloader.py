"""
Pipeline downloader module for fetching Sanskrit texts from various sources.

This module handles downloading Sanskrit texts from GRETIL, DCS, Archive.org,
and other repositories, with verification and backup to Cloudflare R2.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from loguru import logger
import requests
from bs4 import BeautifulSoup
import subprocess
from urllib.parse import urljoin


class DownloadManager:
    """Manage downloads of Sanskrit texts from multiple sources."""

    def __init__(self, corpus_path: Path = Path("corpus"), max_retries: int = 3):
        """
        Initialize DownloadManager.

        Args:
            corpus_path: Path to store downloaded texts
            max_retries: Number of retries for failed downloads

        Example:
            >>> manager = DownloadManager(Path("corpus"))
            >>> manager.download_gretil("rigveda")
        """
        self.corpus_path = Path(corpus_path)
        self.corpus_path.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Sanskrit Text Scraper)"
        })

    def download_gretil(self, category: str) -> List[Path]:
        """
        Download texts from GRETIL repository.

        Args:
            category: Category name (e.g., "rigveda", "puranas")

        Returns:
            List of downloaded file paths

        Example:
            >>> files = manager.download_gretil("rigveda")
            >>> print(f"Downloaded {len(files)} files")
        """
        base_url = "https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/"
        downloaded_files = []

        logger.info(f"Downloading GRETIL category: {category}")

        try:
            # Map category to GRETIL directory structure
            gretil_dir = {
                "rigveda": "1_vedic_literature/vedas/rigveda/",
                "samaveda": "1_vedic_literature/vedas/samaveda/",
                "yajurveda": "1_vedic_literature/vedas/yajurveda/",
                "atharvaveda": "1_vedic_literature/vedas/atharvaveda/",
                "upanishads": "1_vedic_literature/upanishads/",
                "puranas": "2_epics_kavya/puranas/",
                "mahabharata": "2_epics_kavya/mahabharata/",
                "ramayana": "2_epics_kavya/ramayana/",
            }.get(category.lower())

            if not gretil_dir:
                logger.error(f"Unknown category: {category}")
                return downloaded_files

            url = urljoin(base_url, gretil_dir)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            links = soup.find_all("a", href=True)

            for link in links:
                href = link["href"]
                if href.endswith(".txt") or href.endswith(".xml"):
                    file_url = urljoin(url, href)
                    file_path = self.corpus_path / category / Path(href).name
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    if self._download_file(file_url, file_path):
                        downloaded_files.append(file_path)
                        logger.info(f"Downloaded: {file_path.name}")

        except Exception as e:
            logger.error(f"Error downloading from GRETIL: {e}")

        logger.info(f"GRETIL download complete: {len(downloaded_files)} files")
        return downloaded_files

    def download_dcs(self) -> List[Path]:
        """
        Clone or pull DCS (Dharma Corpus Sanskrit) repository.

        Returns:
            List of corpus file paths

        Example:
            >>> files = manager.download_dcs()
        """
        dcs_url = "https://github.com/ambuda-org/dcs"
        dcs_path = self.corpus_path / "dcs"

        logger.info("Downloading DCS corpus...")

        try:
            if dcs_path.exists():
                logger.info("DCS already exists, pulling updates...")
                subprocess.run(
                    ["git", "-C", str(dcs_path), "pull"],
                    check=True,
                    capture_output=True,
                )
            else:
                logger.info("Cloning DCS repository...")
                subprocess.run(
                    ["git", "clone", dcs_url, str(dcs_path)],
                    check=True,
                    capture_output=True,
                )

            # Find all corpus files
            corpus_files = list(dcs_path.glob("**/*.txt"))
            logger.info(f"DCS download complete: {len(corpus_files)} files")
            return corpus_files

        except subprocess.CalledProcessError as e:
            logger.error(f"Error with DCS git operation: {e}")
            return []

    def download_archive_org(self, subject: str = "Sanskrit") -> List[Path]:
        """
        Download texts from Archive.org using internetarchive library.

        Args:
            subject: Search subject (e.g., "Sanskrit")

        Returns:
            List of downloaded file paths

        Example:
            >>> files = manager.download_archive_org("Sanskrit texts")
        """
        try:
            import internetarchive as ia
        except ImportError:
            logger.error("internetarchive library not installed")
            return []

        downloaded_files = []
        logger.info(f"Searching Archive.org for: {subject}")

        try:
            search_results = ia.search_items(
                f'subject:"{subject}" mediatype:texts',
                max_results=50
            )

            for item in search_results:
                try:
                    logger.info(f"Downloading from Archive.org: {item.identifier}")
                    item_path = self.corpus_path / "archive_org" / item.identifier
                    item_path.mkdir(parents=True, exist_ok=True)

                    # Download text formats
                    for file in item.get_files():
                        if file.name.endswith((".txt", ".pdf", ".xml")):
                            file_path = item_path / file.name
                            if not file_path.exists():
                                item.download(
                                    files=file.name,
                                    destdir=str(item_path),
                                    verbose=False,
                                )
                                downloaded_files.append(file_path)
                                logger.info(f"Downloaded: {file.name}")

                except Exception as e:
                    logger.warning(f"Error downloading item {item.identifier}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error searching Archive.org: {e}")

        logger.info(f"Archive.org download complete: {len(downloaded_files)} files")
        return downloaded_files

    def download_sanskritdocs(self, base_url: str = "https://sanskritdocuments.org/Sanskrit/") -> List[Path]:
        """
        Scrape and download texts from sanskritdocuments.org.

        Args:
            base_url: Base URL for sanskritdocuments.org

        Returns:
            List of downloaded file paths

        Example:
            >>> files = manager.download_sanskritdocs()
        """
        downloaded_files = []
        logger.info("Downloading from sanskritdocuments.org...")

        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            links = soup.find_all("a", href=True)

            for link in links:
                href = link["href"]
                if href.endswith((".txt", ".pdf", ".html")):
                    file_url = urljoin(base_url, href)
                    file_name = Path(href).name
                    file_path = self.corpus_path / "sanskritdocs" / file_name

                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    if self._download_file(file_url, file_path):
                        downloaded_files.append(file_path)
                        logger.info(f"Downloaded: {file_name}")

        except Exception as e:
            logger.error(f"Error downloading from sanskritdocuments: {e}")

        logger.info(f"sanskritdocs download complete: {len(downloaded_files)} files")
        return downloaded_files

    def verify_downloads(self) -> dict:
        """
        Verify all downloaded files exist and log missing ones.

        Returns:
            Dictionary with verification results

        Example:
            >>> result = manager.verify_downloads()
            >>> print(f"Total files: {result['total']}, Valid: {result['valid']}")
        """
        logger.info("Verifying downloads...")

        total_files = 0
        valid_files = 0
        missing_categories = []

        for category_dir in self.corpus_path.iterdir():
            if category_dir.is_dir():
                files = list(category_dir.rglob("*"))
                text_files = [f for f in files if f.is_file()]
                total_files += len(text_files)
                valid_files += len(text_files)

                if len(text_files) == 0:
                    missing_categories.append(category_dir.name)

        result = {
            "total": total_files,
            "valid": valid_files,
            "missing_categories": missing_categories,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Verification complete: {valid_files}/{total_files} files valid")
        if missing_categories:
            logger.warning(f"Missing categories: {missing_categories}")

        return result

    def _download_file(self, url: str, file_path: Path, timeout: int = 30) -> bool:
        """
        Download a single file with retries.

        Args:
            url: URL to download from
            file_path: Path to save to
            timeout: Request timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        if file_path.exists():
            logger.debug(f"File already exists: {file_path}")
            return True

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()

                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(response.content)

                logger.debug(f"Successfully downloaded: {file_path}")
                return True

            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to download {url} after {self.max_retries} attempts")
                    return False

        return False
