"""
Pipeline science_linker module for linking Sanskrit concepts to modern science.

This module queries arXiv and PubMed to find modern scientific papers related to
Sanskrit concepts, and scores them based on semantic similarity.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from tqdm import tqdm
import os

from database.models import ScienceLinkRecord
from pipeline.embedder import Embedder


@dataclass
class PaperRecord:
    """Represents a scientific paper."""
    doi: Optional[str]
    title: str
    abstract: str
    url: str
    published_date: str
    domain: str  # Physics, Medicine, Astronomy, etc.


class ScienceLinker:
    """Link Sanskrit concepts to modern science papers."""

    def __init__(self):
        """
        Initialize ScienceLinker with arXiv and PubMed connectors.

        Example:
            >>> linker = ScienceLinker()
            >>> papers = linker.search_arxiv("quantum mechanics")
        """
        try:
            import arxiv
            self.arxiv = arxiv
            logger.info("arXiv API loaded")
        except ImportError:
            logger.warning("arxiv library not installed")
            self.arxiv = None

        self.embedder = Embedder()
        self.arxiv_max_results = int(os.getenv("ARXIV_MAX_RESULTS", 5))
        self.pubmed_max_results = int(os.getenv("PUBMED_MAX_RESULTS", 5))

    def search_arxiv(
        self,
        concept: str,
        max_results: int = 5,
        category: str = "physics"
    ) -> List[PaperRecord]:
        """
        Search arXiv for papers related to a concept.

        Args:
            concept: Search term (Sanskrit concept name)
            max_results: Maximum number of results
            category: arXiv category filter

        Returns:
            List of PaperRecord objects

        Example:
            >>> linker = ScienceLinker()
            >>> papers = linker.search_arxiv("quantum entanglement", max_results=5)
            >>> for paper in papers:
            ...     print(paper.title)
        """
        if not self.arxiv:
            logger.warning("arXiv library not available")
            return []

        papers = []

        try:
            logger.info(f"Searching arXiv for: {concept}")

            # Build search query
            query = f"search_query=all:{concept}&start=0&max_results={max_results}"

            # Execute search
            client = self.arxiv.Client()
            search = self.arxiv.Search(
                query=concept,
                max_results=max_results,
                sort_by=self.arxiv.SortCriterion.SubmittedDate,
                sort_order=self.arxiv.SortOrder.Descending,
            )

            for entry in client.results(search):
                paper = PaperRecord(
                    doi=entry.entry_id.split("/abs/")[-1],
                    title=entry.title,
                    abstract=entry.summary,
                    url=entry.entry_id,
                    published_date=entry.published.strftime("%Y-%m-%d"),
                    domain=category,
                )
                papers.append(paper)
                logger.debug(f"Found arXiv paper: {paper.title[:50]}...")

            logger.info(f"Found {len(papers)} papers on arXiv")
            return papers

        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            return papers

    def search_pubmed(
        self,
        concept: str,
        max_results: int = 5
    ) -> List[PaperRecord]:
        """
        Search PubMed for biomedical papers related to a concept.

        Args:
            concept: Search term
            max_results: Maximum number of results

        Returns:
            List of PaperRecord objects

        Example:
            >>> linker = ScienceLinker()
            >>> papers = linker.search_pubmed("ayurvedic medicine", max_results=5)
        """
        papers = []

        try:
            import requests
            logger.info(f"Searching PubMed for: {concept}")

            # PubMed API base URL
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

            # Search for papers
            search_params = {
                "db": "pubmed",
                "term": concept,
                "retmax": max_results,
                "rettype": "json",
            }

            search_url = base_url + "esearch.fcgi"
            search_response = requests.get(search_url, params=search_params, timeout=10)
            search_response.raise_for_status()

            search_data = search_response.json()
            pmids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                logger.info("No PubMed results found")
                return papers

            # Fetch details for each paper
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "rettype": "abstract",
                "retmode": "json",
            }

            fetch_url = base_url + "efetch.fcgi"
            fetch_response = requests.get(fetch_url, params=fetch_params, timeout=10)
            fetch_response.raise_for_status()

            fetch_data = fetch_response.json()
            articles = fetch_data.get("result", {}).get("uids", [])

            for pmid in pmids[:max_results]:
                article_data = fetch_data.get("result", {}).get(pmid, {})

                paper = PaperRecord(
                    doi=article_data.get("articleids", [{}])[0].get("value"),
                    title=article_data.get("title", "Unknown"),
                    abstract=article_data.get("abstracttext", ""),
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    published_date=article_data.get("pubdate", ""),
                    domain="Medicine",
                )
                papers.append(paper)
                logger.debug(f"Found PubMed paper: {paper.title[:50]}...")

            logger.info(f"Found {len(papers)} papers on PubMed")
            return papers

        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return papers

    def score_relevance(
        self,
        concept_embedding: List[float],
        paper_abstract: str
    ) -> float:
        """
        Score the relevance of a paper to a concept using cosine similarity.

        Args:
            concept_embedding: Embedding of the Sanskrit concept
            paper_abstract: Abstract text of the paper

        Returns:
            Similarity score (0.0-1.0)

        Example:
            >>> linker = ScienceLinker()
            >>> concept_emb = linker.embedder.embed_verse("धर्मम्")
            >>> score = linker.score_relevance(concept_emb, "This paper discusses ethics...")
            >>> print(f"Relevance: {score:.2f}")
        """
        try:
            if not paper_abstract or not concept_embedding:
                return 0.0

            # Embed the abstract
            abstract_embedding = self.embedder.embed_verse(paper_abstract[:512])

            # Compute cosine similarity
            import numpy as np

            concept_vec = np.array(concept_embedding)
            abstract_vec = np.array(abstract_embedding)

            # Normalize
            concept_vec = concept_vec / (np.linalg.norm(concept_vec) + 1e-8)
            abstract_vec = abstract_vec / (np.linalg.norm(abstract_vec) + 1e-8)

            # Cosine similarity
            similarity = float(np.dot(concept_vec, abstract_vec))

            # Clamp to [0, 1]
            similarity = max(0.0, min(1.0, (similarity + 1.0) / 2.0))

            return similarity

        except Exception as e:
            logger.error(f"Error scoring relevance: {e}")
            return 0.0

    def link_concept(
        self,
        concept_id: str,
        concept_name: str,
        concept_embedding: List[float],
        min_confidence: float = 0.5
    ) -> List[ScienceLinkRecord]:
        """
        Find and score science papers for a Sanskrit concept.

        Args:
            concept_id: Concept identifier
            concept_name: Concept name in English or Sanskrit
            concept_embedding: Pre-computed embedding
            min_confidence: Minimum relevance score to include

        Returns:
            List of ScienceLinkRecord objects

        Example:
            >>> linker = ScienceLinker()
            >>> concept_emb = linker.embedder.embed_verse("dharma")
            >>> links = linker.link_concept("dharma", "Dharma (duty)", concept_emb)
        """
        links = []

        try:
            # Search arXiv
            arxiv_papers = self.search_arxiv(concept_name, self.arxiv_max_results)

            # Search PubMed
            pubmed_papers = self.search_pubmed(concept_name, self.pubmed_max_results)

            # Combine and score all papers
            all_papers = arxiv_papers + pubmed_papers

            for paper in tqdm(all_papers, desc=f"Scoring papers for {concept_id}"):
                # Score relevance
                confidence = self.score_relevance(concept_embedding, paper.abstract)

                if confidence >= min_confidence:
                    link = ScienceLinkRecord(
                        concept_id=concept_id,
                        domain=paper.domain,
                        modern_ref=paper.doi or paper.url,
                        modern_title=paper.title,
                        confidence=confidence,
                        description=f"Semantic match with {paper.domain.lower()} paper"
                    )
                    links.append(link)
                    logger.debug(f"Created link: {concept_id} → {paper.title[:40]}... ({confidence:.2f})")

            logger.info(f"Found {len(links)} relevant papers for {concept_id}")
            return links

        except Exception as e:
            logger.error(f"Error linking concept {concept_id}: {e}")
            return links

    def run_weekly_update(self, concepts: List[dict], min_confidence: float = 0.5) -> dict:
        """
        Run weekly update to find new science links for all concepts.

        Args:
            concepts: List of concept dicts with 'concept_id', 'name_sa', 'embedding'
            min_confidence: Minimum confidence threshold

        Returns:
            Summary dict with statistics

        Example:
            >>> linker = ScienceLinker()
            >>> summary = linker.run_weekly_update(all_concepts)
            >>> print(f"Added {summary['new_links']} new science links")
        """
        stats = {
            "total_concepts": len(concepts),
            "new_links": 0,
            "domains": {},
            "avg_confidence": 0.0,
        }

        try:
            logger.info(f"Starting weekly science link update for {len(concepts)} concepts")

            all_links = []

            for concept in tqdm(concepts, desc="Processing concepts"):
                concept_id = concept.get("concept_id", "")
                concept_name = concept.get("name_sa", "")
                embedding = concept.get("embedding", [])

                if not concept_id or not embedding:
                    logger.warning(f"Skipping concept: missing id or embedding")
                    continue

                links = self.link_concept(concept_id, concept_name, embedding, min_confidence)
                all_links.extend(links)

                # Track domains
                for link in links:
                    domain = link.domain
                    stats["domains"][domain] = stats["domains"].get(domain, 0) + 1

            stats["new_links"] = len(all_links)
            if all_links:
                stats["avg_confidence"] = sum(l.confidence for l in all_links) / len(all_links)

            logger.info(f"Weekly update complete: {stats['new_links']} new links")
            logger.info(f"Domain breakdown: {stats['domains']}")

            return stats

        except Exception as e:
            logger.error(f"Error in weekly update: {e}")
            return stats
