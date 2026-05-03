"""
Pipeline embedder module for generating sentence embeddings.

This module uses sentence-transformers to generate semantic embeddings for
verses and concepts, storing them in vector databases for similarity search.
"""

from typing import List, Optional
from loguru import logger
from tqdm import tqdm
import os

# Get embedding model from environment
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)


class Embedder:
    """Generate and manage sentence embeddings for Sanskrit verses."""

    def __init__(self, model_name: str = EMBEDDING_MODEL, device: str = "cpu"):
        """
        Initialize Embedder with a sentence-transformer model.

        Args:
            model_name: HuggingFace model ID
            device: "cpu" or "cuda"

        Example:
            >>> embedder = Embedder()
            >>> embedding = embedder.embed_verse("धर्मक्षेत्रे कुरुक्षेत्रे")
            >>> print(f"Embedding shape: {len(embedding)}")
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise ImportError("Install via: pip install sentence-transformers")

        try:
            self.model = SentenceTransformer(model_name, device=device)
            logger.info(f"Loaded embedding model: {model_name} on {device}")
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise

    def embed_verse(self, text: str, normalize: bool = True) -> List[float]:
        """
        Generate embedding for a single verse.

        Args:
            text: Verse text in Devanagari or any language
            normalize: Whether to normalize the embedding (default: True)

        Returns:
            List of floats representing the embedding

        Example:
            >>> embedder = Embedder()
            >>> embedding = embedder.embed_verse("धर्मक्षेत्रे कुरुक्षेत्रे")
            >>> print(f"Embedding: {embedding[:5]}...")
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return [0.0] * self.embedding_dim

            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=False,
                normalize_embeddings=normalize
            )

            # Convert to list
            result = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
            logger.debug(f"Generated embedding for {len(text)} chars")
            return result

        except Exception as e:
            logger.error(f"Error embedding verse: {e}")
            return [0.0] * self.embedding_dim

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (default: 32)
            normalize: Whether to normalize embeddings
            show_progress: Whether to show progress bar

        Returns:
            List of embeddings (each is a list of floats)

        Example:
            >>> embedder = Embedder()
            >>> verses = [
            ...     "धर्मक्षेत्रे कुरुक्षेत्रे",
            ...     "पाण्डवाः शतसंख्यकाः"
            ... ]
            >>> embeddings = embedder.embed_batch(verses)
            >>> print(f"Generated {len(embeddings)} embeddings")
        """
        if not texts:
            logger.warning("Empty text list provided")
            return []

        try:
            # Filter out empty strings
            valid_texts = [t for t in texts if t and t.strip()]
            if len(valid_texts) < len(texts):
                logger.warning(f"Filtered out {len(texts) - len(valid_texts)} empty texts")

            iterator = tqdm(valid_texts, desc="Embedding", disable=not show_progress)

            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress,
                convert_to_numpy=False,
            )

            # Convert to list format
            result = [
                e.tolist() if hasattr(e, 'tolist') else list(e)
                for e in embeddings
            ]

            logger.info(f"Generated {len(result)} embeddings")
            return result

        except Exception as e:
            logger.error(f"Error embedding batch: {e}")
            return []

    def embed_and_store(
        self,
        verses: List[dict],
        batch_size: int = 32
    ) -> List[dict]:
        """
        Embed verses and prepare for storage in vector databases.

        Args:
            verses: List of verse dicts with 'verse_id' and 'devanagari' keys
            batch_size: Batch size for embedding

        Returns:
            List of verse dicts with 'embedding' key added

        Example:
            >>> embedder = Embedder()
            >>> verses = [
            ...     {"verse_id": "BG.1.1", "devanagari": "धर्मक्षेत्रे..."},
            ...     {"verse_id": "BG.1.2", "devanagari": "पाण्डवाः..."}
            ... ]
            >>> verses_with_embeddings = embedder.embed_and_store(verses)
        """
        if not verses:
            logger.warning("No verses provided for embedding")
            return []

        try:
            # Extract texts
            texts = [v.get("devanagari", "") or v.get("iast", "") for v in verses]

            # Generate embeddings
            embeddings = self.embed_batch(
                texts,
                batch_size=batch_size,
                show_progress=True
            )

            # Add embeddings to verses
            result = []
            for verse, embedding in zip(verses, embeddings):
                verse_copy = verse.copy()
                verse_copy["embedding"] = embedding
                result.append(verse_copy)

            logger.info(f"Added embeddings to {len(result)} verses")
            return result

        except Exception as e:
            logger.error(f"Error in embed_and_store: {e}")
            return verses

    def get_embedding_dim(self) -> int:
        """
        Get the dimensionality of embeddings.

        Returns:
            Embedding dimension

        Example:
            >>> embedder = Embedder()
            >>> dim = embedder.get_embedding_dim()
            >>> print(f"Dimension: {dim}")  # 768
        """
        return self.embedding_dim

    def model_info(self) -> dict:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model metadata

        Example:
            >>> embedder = Embedder()
            >>> info = embedder.model_info()
            >>> print(info)
        """
        try:
            return {
                "model_name": self.model.get_sentence_embedding_dimension(),
                "embedding_dim": self.embedding_dim,
                "max_seq_length": self.model.max_seq_length if hasattr(self.model, 'max_seq_length') else None,
                "model_class": str(type(self.model)),
            }
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {}
