"""
pipeline/downloader.py
======================
Downloads all Sanskrit texts from GRETIL, DCS, Archive.org,
sanskritdocuments.org and backs up everything to Cloudflare R2.

All sources discovered from deep research:
- GRETIL GitHub mirror  : https://github.com/INDOLOGY/GRETIL-mirror
- GRETIL TextGrid 2025  : https://textgridrep.org/project/TGPR-2ba9cb1b...
- GRETIL DARIAH ZIP     : https://doi.org/10.20375/0000-0016-C802-4
- DCS corpus            : https://github.com/ambuda-org/dcs
- Archive.org Sanskrit  : subject:Sanskrit mediatype:texts
- sanskritdocuments.org : https://sanskritdocuments.org/Sanskrit/
"""

import os
import subprocess
import zipfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import requests
import aiohttp
import asyncio
import aiofiles
from tqdm import tqdm
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

CORPUS_DIR = Path(os.getenv("CORPUS_DIR", "./corpus"))

# ── All GRETIL direct text URLs (research-verified 2025) ──
GRETIL_TEXTS = {
    # VEDAS
    "RV":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/1_veda/1_sam/rv_samsu.htm",
    "SV":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/1_veda/1_sam/sv_samsu.htm",
    "AV":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/1_veda/1_sam/av_samsu.htm",
    # UPANISHADS
    "BU":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/1_veda/4_upa/brihadaru.htm",
    "CU":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/1_veda/4_upa/chandogu.htm",
    "KU":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/1_veda/4_upa/katu.htm",
    "MU":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/1_veda/4_upa/mundu.htm",
    "ISA":  "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/1_veda/4_upa/ishu.htm",
    # EPICS
    "BG":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/mbh/bhaggihu.htm",
    # PURANAS
    "AGNI": "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/3_purana/agnipuru.htm",
    "BHAG": "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/3_purana/bhp1u.htm",
    "GAR":  "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/3_purana/garudpuu.htm",
    "MARK": "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/3_purana/markpuru.htm",
    "VISH": "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/3_purana/vishnpuu.htm",
    # SCIENCE
    "CS":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/6_sastra/5_ayur/caraksu2.htm",
    "AB":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/6_sastra/6_astro/aryabh_u.htm",
    "YS":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/6_sastra/3_phil/yoga/ysu.htm",
    "ARTH": "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/6_sastra/7_misc/arthas_u.htm",
    "NS":   "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/6_sastra/7_misc/natyashu.htm",
}

# Mahabharata comes in 18 books
MBH_BOOKS = {f"MBH_{i:02d}": f"https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/mbh/mbh{i:02d}u.htm"
             for i in range(1, 19)}

# Ramayana comes in 7 kandas
RAM_KANDAS = {
    "RAM_01_bala":    "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/ramayana/ram01u.htm",
    "RAM_02_ayodhya": "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/ramayana/ram02u.htm",
    "RAM_03_aranya":  "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/ramayana/ram03u.htm",
    "RAM_04_kishkindha": "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/ramayana/ram04u.htm",
    "RAM_05_sundara": "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/ramayana/ram05u.htm",
    "RAM_06_yuddha":  "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/ramayana/ram06u.htm",
    "RAM_07_uttara":  "https://raw.githubusercontent.com/INDOLOGY/GRETIL-mirror/master/all-files/1_sanskr/2_epic/ramayana/ram07u.htm",
}

GRETIL_ZIP_URL = "https://doi.org/10.20375/0000-0016-C802-4"
GRETIL_CUMULATIVE_DIRECT = "https://repository.de.dariah.eu/1.0/dhrep/objects/hdl:21.11113/0000-0016-C802-4/1_sanskr.zip"
DCS_REPO = "https://github.com/ambuda-org/dcs.git"
VIDYUT_REPO = "https://github.com/ambuda-org/vidyut.git"
GRETIL_MIRROR_REPO = "https://github.com/INDOLOGY/GRETIL-mirror.git"


@dataclass
class DownloadResult:
    text_id: str
    success: bool
    local_path: Optional[Path] = None
    error: Optional[str] = None
    bytes_downloaded: int = 0


class CorpusDownloader:
    """
    Downloads the complete Sanskrit corpus from all free sources.

    Sources:
        - GRETIL GitHub mirror (most reliable, Oct 2025 snapshot)
        - DARIAH ZIP (cumulative Sanskrit ZIP, all texts)
        - ambuda-org/dcs (annotated Digital Corpus of Sanskrit)
        - Archive.org (scanned manuscripts)
        - sanskritdocuments.org (multi-encoding texts)
    """

    def __init__(self, corpus_dir: Path = CORPUS_DIR):
        self.corpus_dir = corpus_dir
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Corpus directory: {self.corpus_dir.resolve()}")

    # ─────────────────────────────────────────────────
    # METHOD 1: Clone the full GRETIL GitHub mirror
    # Fastest, most complete, Oct 2025 snapshot
    # ─────────────────────────────────────────────────
    def clone_gretil_mirror(self) -> bool:
        """
        Clones the INDOLOGY/GRETIL-mirror GitHub repository.
        Contains all Sanskrit texts as of Oct 14, 2025.
        ~500MB download. All files are Unicode UTF-8.

        Returns:
            bool: True if successful
        """
        dest = self.corpus_dir / "gretil_mirror"
        if dest.exists() and any(dest.iterdir()):
            logger.info("GRETIL mirror already cloned. Pulling updates...")
            result = subprocess.run(
                ["git", "-C", str(dest), "pull", "--depth=1"],
                capture_output=True, text=True
            )
            return result.returncode == 0

        logger.info("Cloning GRETIL mirror (all Sanskrit texts, ~500MB)...")
        result = subprocess.run([
            "git", "clone", "--depth=1",
            GRETIL_MIRROR_REPO,
            str(dest)
        ], capture_output=True, text=True)

        if result.returncode == 0:
            logger.success(f"GRETIL mirror cloned to {dest}")
            self._index_gretil_files(dest)
            return True
        else:
            logger.error(f"GRETIL clone failed: {result.stderr}")
            return False

    def _index_gretil_files(self, gretil_dir: Path) -> None:
        """Scans GRETIL mirror and logs what we have."""
        all_files = list(gretil_dir.rglob("*.htm")) + list(gretil_dir.rglob("*.xml"))
        logger.info(f"GRETIL mirror contains {len(all_files)} text files")

        # Categorise
        categories = {}
        for f in all_files:
            parts = f.parts
            if "1_veda" in parts:
                cat = "Vedas"
            elif "2_epic" in parts:
                cat = "Itihasas"
            elif "3_purana" in parts:
                cat = "Puranas"
            elif "6_sastra" in parts:
                cat = "Shastras"
            else:
                cat = "Other"
            categories[cat] = categories.get(cat, 0) + 1

        for cat, count in sorted(categories.items()):
            logger.info(f"  {cat}: {count} files")

    # ─────────────────────────────────────────────────
    # METHOD 2: Download DARIAH cumulative ZIP
    # Official GRETIL archive, all Sanskrit texts in one ZIP
    # ─────────────────────────────────────────────────
    def download_gretil_zip(self) -> bool:
        """
        Downloads the official GRETIL cumulative Sanskrit ZIP from DARIAH-DE.
        DOI: 10.20375/0000-0016-C802-4
        Contains ALL Sanskrit texts in one archive.

        Returns:
            bool: True if successful
        """
        zip_path = self.corpus_dir / "gretil_sanskrit_all.zip"
        extract_dir = self.corpus_dir / "gretil_zip"

        if extract_dir.exists() and any(extract_dir.iterdir()):
            logger.info("GRETIL ZIP already extracted.")
            return True

        logger.info("Downloading GRETIL cumulative Sanskrit ZIP from DARIAH...")
        logger.info("URL: https://doi.org/10.20375/0000-0016-C802-4")
        logger.info("Note: This is ~200MB. Using wget for reliability...")

        result = subprocess.run([
            "wget", "-O", str(zip_path),
            "--progress=bar:force",
            GRETIL_CUMULATIVE_DIRECT
        ], capture_output=False)

        if result.returncode == 0 and zip_path.exists():
            logger.info("Extracting ZIP...")
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            logger.success(f"Extracted to {extract_dir}")
            zip_path.unlink()  # remove ZIP after extraction
            return True
        else:
            logger.error("GRETIL ZIP download failed. Try METHOD 1 (git clone) instead.")
            return False

    # ─────────────────────────────────────────────────
    # METHOD 3: Clone DCS annotated corpus
    # Full morphological annotations for training
    # ─────────────────────────────────────────────────
    def clone_dcs(self) -> bool:
        """
        Clones the Digital Corpus of Sanskrit (ambuda-org/dcs).
        This is the most linguistically rich corpus:
        every word has POS tags and lemma annotations.

        Returns:
            bool: True if successful
        """
        dest = self.corpus_dir / "dcs"
        if dest.exists() and any(dest.iterdir()):
            logger.info("DCS already cloned. Pulling updates...")
            subprocess.run(["git", "-C", str(dest), "pull"], capture_output=True)
            return True

        logger.info("Cloning DCS (annotated Sanskrit corpus)...")
        result = subprocess.run([
            "git", "clone", "--depth=1",
            DCS_REPO, str(dest)
        ], capture_output=True, text=True)

        if result.returncode == 0:
            xml_files = list(dest.rglob("*.xml"))
            logger.success(f"DCS cloned: {len(xml_files)} annotated XML files")
            return True
        else:
            logger.error(f"DCS clone failed: {result.stderr}")
            return False

    # ─────────────────────────────────────────────────
    # METHOD 4: Download individual texts asynchronously
    # Used for specific texts not in mirror
    # ─────────────────────────────────────────────────
    async def _download_one(self, session: aiohttp.ClientSession,
                            text_id: str, url: str,
                            dest: Path) -> DownloadResult:
        """Downloads a single text file asynchronously."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    async with aiofiles.open(dest, 'wb') as f:
                        await f.write(content)
                    return DownloadResult(text_id, True, dest, bytes_downloaded=len(content))
                else:
                    return DownloadResult(text_id, False, error=f"HTTP {resp.status}")
        except Exception as e:
            return DownloadResult(text_id, False, error=str(e))

    async def download_all_texts_async(self) -> list[DownloadResult]:
        """
        Downloads all individual texts asynchronously (fast, concurrent).
        Used as fallback if git clone fails.

        Returns:
            list[DownloadResult]: Results for each text
        """
        all_urls = {**GRETIL_TEXTS, **MBH_BOOKS, **RAM_KANDAS}
        results = []

        async with aiohttp.ClientSession(headers={"User-Agent": "VIS-Sanskrit-AI/1.0"}) as session:
            tasks = []
            for text_id, url in all_urls.items():
                dest_dir = self.corpus_dir / "individual"
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f"{text_id}.htm"
                if dest.exists():
                    logger.debug(f"Already downloaded: {text_id}")
                    results.append(DownloadResult(text_id, True, dest))
                    continue
                tasks.append(self._download_one(session, text_id, url, dest))

            if tasks:
                logger.info(f"Downloading {len(tasks)} texts concurrently...")
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in batch_results:
                    if isinstance(r, DownloadResult):
                        results.append(r)
                        if r.success:
                            logger.debug(f"✓ {r.text_id} ({r.bytes_downloaded/1024:.0f} KB)")
                        else:
                            logger.warning(f"✗ {r.text_id}: {r.error}")

        successful = sum(1 for r in results if r.success)
        logger.info(f"Downloaded {successful}/{len(all_urls)} texts successfully")
        return results

    def download_all_texts(self) -> list[DownloadResult]:
        """Synchronous wrapper for async download."""
        return asyncio.run(self.download_all_texts_async())

    # ─────────────────────────────────────────────────
    # METHOD 5: Archive.org for scanned books
    # ─────────────────────────────────────────────────
    def download_archive_org(self, limit: int = 100) -> int:
        """
        Downloads Sanskrit texts from Archive.org using internetarchive CLI.
        Gets scanned manuscripts and rare texts not in GRETIL.

        Args:
            limit: Maximum number of items to download

        Returns:
            int: Number of items downloaded
        """
        try:
            import internetarchive as ia
        except ImportError:
            logger.warning("internetarchive not installed. Run: pip install internetarchive")
            return 0

        dest = self.corpus_dir / "archive_org"
        dest.mkdir(exist_ok=True)

        # Search queries for Sanskrit texts
        queries = [
            "subject:Sanskrit AND mediatype:texts AND language:Sanskrit",
            "subject:Vedas AND mediatype:texts",
            "subject:Upanishads AND mediatype:texts",
        ]

        downloaded = 0
        for query in queries:
            if downloaded >= limit:
                break
            logger.info(f"Searching Archive.org: {query}")
            try:
                results = ia.search_items(query)
                for item in results:
                    if downloaded >= limit:
                        break
                    item_id = item.get("identifier", "")
                    item_dir = dest / item_id
                    if item_dir.exists():
                        continue
                    try:
                        ia.download(item_id, destdir=str(dest),
                                    glob_pattern="*.txt",
                                    ignore_existing=True,
                                    silent=True)
                        downloaded += 1
                        logger.debug(f"Downloaded: {item_id}")
                    except Exception as e:
                        logger.warning(f"Failed {item_id}: {e}")
            except Exception as e:
                logger.error(f"Archive.org search failed: {e}")

        logger.info(f"Downloaded {downloaded} items from Archive.org")
        return downloaded

    # ─────────────────────────────────────────────────
    # MASTER download runner
    # ─────────────────────────────────────────────────
    def run_full_download(self) -> dict:
        """
        Runs the complete corpus download in recommended order.

        Order:
            1. Clone GRETIL mirror (most complete, fastest)
            2. Clone DCS (annotated corpus for training)
            3. Download individual texts (fallback)
            4. Archive.org supplemental

        Returns:
            dict: Summary of what was downloaded
        """
        summary = {}

        logger.info("=" * 60)
        logger.info("VIS CORPUS DOWNLOADER — Starting full acquisition")
        logger.info("=" * 60)

        # Step 1: GRETIL mirror (primary)
        logger.info("\n[1/4] Cloning GRETIL GitHub mirror...")
        summary["gretil_mirror"] = self.clone_gretil_mirror()

        # Step 2: DCS annotated corpus
        logger.info("\n[2/4] Cloning DCS annotated corpus...")
        summary["dcs"] = self.clone_dcs()

        # Step 3: Individual texts (if mirror failed)
        if not summary["gretil_mirror"]:
            logger.info("\n[3/4] Mirror failed — downloading individual texts...")
            results = self.download_all_texts()
            summary["individual"] = {r.text_id: r.success for r in results}
        else:
            logger.info("\n[3/4] GRETIL mirror succeeded — skipping individual downloads.")
            summary["individual"] = "skipped (mirror used)"

        # Step 4: Archive.org supplemental (optional)
        logger.info("\n[4/4] Downloading from Archive.org (supplemental)...")
        summary["archive_org"] = self.download_archive_org(limit=50)

        self._print_summary(summary)
        return summary

    def _print_summary(self, summary: dict) -> None:
        total_files = sum(1 for f in self.corpus_dir.rglob("*") if f.is_file())
        total_size_mb = sum(f.stat().st_size for f in self.corpus_dir.rglob("*") if f.is_file()) / 1024 / 1024
        logger.success(f"""
╔══════════════════════════════════════════╗
║  CORPUS DOWNLOAD COMPLETE                ║
║  Files: {total_files:<6}  Size: {total_size_mb:.1f} MB          ║
║  Location: {str(self.corpus_dir):<30} ║
╚══════════════════════════════════════════╝
        """)

    def verify_downloads(self) -> dict:
        """
        Checks corpus completeness. Returns list of missing texts.

        Returns:
            dict: {text_id: found (bool)} for all expected texts
        """
        status = {}
        all_files = set(f.stem for f in self.corpus_dir.rglob("*") if f.is_file())

        for text_id in list(GRETIL_TEXTS.keys()) + list(MBH_BOOKS.keys()) + list(RAM_KANDAS.keys()):
            status[text_id] = any(text_id.lower() in str(f).lower()
                                  for f in self.corpus_dir.rglob("*"))

        found = sum(status.values())
        logger.info(f"Corpus verification: {found}/{len(status)} texts found")
        return status


# ── CLI entry point ──────────────────────────────────────
if __name__ == "__main__":
    import typer
    app = typer.Typer()

    @app.command()
    def download(
        method: str = typer.Option("all", help="all | gretil | dcs | individual | archive"),
        limit: int = typer.Option(50, help="Archive.org download limit"),
        verify: bool = typer.Option(False, help="Only verify existing downloads")
    ):
        """Download the Sanskrit corpus."""
        dl = CorpusDownloader()
        if verify:
            dl.verify_downloads()
        elif method == "gretil":
            dl.clone_gretil_mirror()
        elif method == "dcs":
            dl.clone_dcs()
        elif method == "individual":
            dl.download_all_texts()
        elif method == "archive":
            dl.download_archive_org(limit=limit)
        else:
            dl.run_full_download()

    app()
